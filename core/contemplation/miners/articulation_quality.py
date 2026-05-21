"""Phase 5 — offline articulation-quality miner.

Consumes a JSONL stream of ``ArticulationObservation`` records (the
per-turn Phase 4 metrics + Phase 3 findings emitted by
``chat.articulation_telemetry``) and aggregates across many turns
to surface ``PACK_MUTATION_CANDIDATE`` findings.

This is the layer that closes the user-intuited "live reasoning →
memory confidence" loop.  Per CLAUDE.md doctrine the aggregation is:

* **Read-only** — never writes packs, vault, teaching corpus, or
  runtime state.  Emits findings only.
* **SPECULATIVE-only** — every emitted finding is stamped
  ``EpistemicStatus.SPECULATIVE``.  The miner proposes corpus
  expansions; the operator reviews and decides.
* **Deterministic** — same input stream → byte-identical
  findings (same ``substrate_hash``, same ``finding_id`` per
  finding).  Pinned by ``test_articulation_quality_is_deterministic``.

v1 rules
--------

* ``recurring_predicate_monotony`` — when the SAME ``(anchor_subject,
  dominant_predicate)`` pair is flagged ``WEAK_SURFACE`` in
  ``>= _MIN_RECURRENCE`` observations, propose substrate expansion
  with non-dominant predicates.

* ``recurring_planner_gap`` — when the SAME ``anchor_subject`` is
  flagged ``PLANNER_GAP`` in ``>= _MIN_RECURRENCE`` observations,
  propose substrate expansion for that subject.

* ``low_average_predicate_diversity`` — when the mean
  ``predicate_diversity_ratio`` across ``>= _MIN_RECURRENCE``
  observations on the same ``anchor_subject`` falls below
  ``_LOW_DIVERSITY_THRESHOLD``, propose substrate diversification.

The thresholds are conservative on purpose: a single noisy turn must
not produce a pack-mutation proposal.  Default ``_MIN_RECURRENCE = 3``
keeps the bar at "this pattern is the rule, not the exception".
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Iterable

from chat.articulation_telemetry import (
    ArticulationObservation,
    load_articulation_observations,
)
from core.contemplation.schema import (
    ContemplationEvidenceRef,
    ContemplationFinding,
    FindingKind,
)


_MIN_RECURRENCE = 3
"""Minimum observation count before a pattern proposes a pack
mutation.  Tightens the false-positive rate at the cost of catching
slower-burning patterns later."""


_LOW_DIVERSITY_THRESHOLD = 0.5
"""``predicate_diversity_ratio`` threshold for the
``low_average_predicate_diversity`` rule.  ``0.5`` says "on average
half of fact-bearing moves on this subject reused a predicate" —
clearly a corpus-shape signal once it persists across many turns."""


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------


def _stream_observations(
    paths: Iterable[Path],
) -> tuple[ArticulationObservation, ...]:
    """Read every JSONL path in *paths* and return all observations.

    Empty / missing paths skip silently; malformed lines drop via the
    loader's per-line try/except (see
    ``chat.articulation_telemetry.load_articulation_observations``).
    """
    out: list[ArticulationObservation] = []
    for p in paths:
        path = Path(p)
        if not path.is_file():
            continue
        with path.open(encoding="utf-8") as handle:
            out.extend(load_articulation_observations(handle))
    return tuple(out)


def _evidence_refs_for_observations(
    observations: tuple[ArticulationObservation, ...],
    *,
    summary: str,
) -> tuple[ContemplationEvidenceRef, ...]:
    """One evidence ref per source observation, plus a roll-up summary
    in the first ref so a reviewer can see the aggregation at a glance.
    """
    refs: list[ContemplationEvidenceRef] = []
    for i, obs in enumerate(observations):
        refs.append(
            ContemplationEvidenceRef(
                source_type="articulation_observation",
                source_id=obs.plan_substrate_hash,
                pointer=f"turn_id={obs.turn_id}",
                summary=summary if i == 0 else "",
            )
        )
    return tuple(refs)


# ---------------------------------------------------------------------------
# Rules
# ---------------------------------------------------------------------------


def _rule_recurring_predicate_monotony(
    observations: tuple[ArticulationObservation, ...],
    substrate_hash: str,
) -> tuple[ContemplationFinding, ...]:
    """Detect WEAK_SURFACE recurrence on the same ``(subject, predicate)``."""
    # Map (anchor_subject, dominant_predicate) → list[observation]
    buckets: dict[tuple[str, str], list[ArticulationObservation]] = (
        defaultdict(list)
    )
    for obs in observations:
        for finding in obs.findings:
            if finding.get("kind") != FindingKind.WEAK_SURFACE.value:
                continue
            subject = str(finding.get("subject") or "")
            predicate = str(finding.get("object") or "")
            if not subject or not predicate:
                continue
            buckets[(subject, predicate)].append(obs)

    findings: list[ContemplationFinding] = []
    for (subject, predicate), matched in sorted(buckets.items()):
        if len(matched) < _MIN_RECURRENCE:
            continue
        summary = (
            f"WEAK_SURFACE recurred {len(matched)}x on subject={subject!r} "
            f"with dominant predicate={predicate!r}"
        )
        findings.append(
            ContemplationFinding(
                kind=FindingKind.PACK_MUTATION_CANDIDATE,
                subject=subject,
                predicate="recurring_predicate_monotony",
                object=predicate,
                evidence_refs=_evidence_refs_for_observations(
                    tuple(matched), summary=summary,
                ),
                proposed_action=(
                    f"diversify substrate for {subject!r}: across "
                    f"{len(matched)} observations the plan repeatedly "
                    f"over-concentrated on predicate {predicate!r}. "
                    f"Candidates: add teaching chains rooted on "
                    f"{subject!r} with relations OTHER than {predicate!r} "
                    f"(grounds / requires / reveals / contrasts / "
                    f"precedes / follows) so the planner's RELATION "
                    f"selector has more variety to draw from."
                ),
                substrate_hash=substrate_hash,
            )
        )
    return tuple(findings)


def _rule_recurring_planner_gap(
    observations: tuple[ArticulationObservation, ...],
    substrate_hash: str,
) -> tuple[ContemplationFinding, ...]:
    """Detect PLANNER_GAP recurrence on the same anchor subject."""
    buckets: dict[str, list[ArticulationObservation]] = defaultdict(list)
    for obs in observations:
        for finding in obs.findings:
            if finding.get("kind") != FindingKind.PLANNER_GAP.value:
                continue
            subject = str(finding.get("subject") or "")
            if not subject:
                continue
            buckets[subject].append(obs)

    findings: list[ContemplationFinding] = []
    for subject, matched in sorted(buckets.items()):
        if len(matched) < _MIN_RECURRENCE:
            continue
        # Collect the distinct modes that hit anchor-only depth so the
        # proposed action can reference them concretely.
        distinct_modes = sorted({
            str(f.get("object") or "")
            for obs in matched
            for f in obs.findings
            if f.get("kind") == FindingKind.PLANNER_GAP.value
            and f.get("subject") == subject
            and f.get("object")
        })
        summary = (
            f"PLANNER_GAP recurred {len(matched)}x on subject={subject!r} "
            f"across modes={distinct_modes}"
        )
        findings.append(
            ContemplationFinding(
                kind=FindingKind.PACK_MUTATION_CANDIDATE,
                subject=subject,
                predicate="recurring_planner_gap",
                object=",".join(distinct_modes) if distinct_modes else None,
                evidence_refs=_evidence_refs_for_observations(
                    tuple(matched), summary=summary,
                ),
                proposed_action=(
                    f"widen substrate for {subject!r}: across "
                    f"{len(matched)} observations the planner could only "
                    f"surface an anchor (no qualifying support/relation/"
                    f"transition).  Affected modes: "
                    f"{', '.join(distinct_modes) if distinct_modes else 'unknown'}. "
                    f"Candidates: add teaching chains rooted on this "
                    f"lemma, or add pack ``belongs_to`` / ``is_defined_as`` "
                    f"facts that the SUPPORT selector can pick up."
                ),
                substrate_hash=substrate_hash,
            )
        )
    return tuple(findings)


def _rule_low_average_predicate_diversity(
    observations: tuple[ArticulationObservation, ...],
    substrate_hash: str,
) -> tuple[ContemplationFinding, ...]:
    """Detect low mean predicate_diversity_ratio across observations on
    the same anchor subject."""
    buckets: dict[str, list[ArticulationObservation]] = defaultdict(list)
    for obs in observations:
        ratio = obs.metrics.get("predicate_diversity_ratio")
        if ratio is None:
            continue
        if not obs.anchor_subject:
            continue
        buckets[obs.anchor_subject].append(obs)

    findings: list[ContemplationFinding] = []
    for subject, matched in sorted(buckets.items()):
        if len(matched) < _MIN_RECURRENCE:
            continue
        ratios = [
            float(obs.metrics["predicate_diversity_ratio"])
            for obs in matched
        ]
        avg = mean(ratios)
        if avg >= _LOW_DIVERSITY_THRESHOLD:
            continue
        summary = (
            f"mean predicate_diversity_ratio={avg:.3f} across "
            f"{len(matched)} observations on subject={subject!r}"
        )
        findings.append(
            ContemplationFinding(
                kind=FindingKind.PACK_MUTATION_CANDIDATE,
                subject=subject,
                predicate="low_average_predicate_diversity",
                object=f"{avg:.3f}",
                evidence_refs=_evidence_refs_for_observations(
                    tuple(matched), summary=summary,
                ),
                proposed_action=(
                    f"raise predicate diversity for {subject!r}: across "
                    f"{len(matched)} observations the mean "
                    f"predicate_diversity_ratio was {avg:.3f} (threshold "
                    f"{_LOW_DIVERSITY_THRESHOLD:.2f}).  Candidates: "
                    f"add teaching chains rooted on {subject!r} that "
                    f"use predicates currently under-represented in the "
                    f"corpus; consider auditing which relations the "
                    f"planner is forced to repeat."
                ),
                substrate_hash=substrate_hash,
            )
        )
    return tuple(findings)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def _substrate_hash_for_observations(
    observations: tuple[ArticulationObservation, ...],
) -> str:
    """Deterministic hash over the canonical concatenation of each
    observation's JSONL serialisation."""
    payload = json.dumps(
        [obs.as_dict() for obs in observations],
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def mine_articulation_observations(
    observations: tuple[ArticulationObservation, ...] | None = None,
    *,
    paths: Iterable[Path | str] = (),
) -> tuple[ContemplationFinding, ...]:
    """Run every articulation-quality rule across the input observations.

    Provide either *observations* directly OR *paths* (JSONL files
    that will be loaded via
    ``chat.articulation_telemetry.load_articulation_observations``).
    When BOTH are provided, the direct observations are appended
    after the loaded ones in canonical order.

    Pure deterministic function: same input → byte-identical findings.
    """
    loaded = _stream_observations(tuple(Path(p) for p in paths))
    if observations is None:
        all_observations = loaded
    else:
        all_observations = loaded + tuple(observations)

    if not all_observations:
        return ()

    substrate_hash = _substrate_hash_for_observations(all_observations)

    findings: list[ContemplationFinding] = []
    findings.extend(
        _rule_recurring_predicate_monotony(all_observations, substrate_hash)
    )
    findings.extend(
        _rule_recurring_planner_gap(all_observations, substrate_hash)
    )
    findings.extend(
        _rule_low_average_predicate_diversity(
            all_observations, substrate_hash,
        )
    )
    return tuple(findings)


__all__ = [
    "mine_articulation_observations",
]
