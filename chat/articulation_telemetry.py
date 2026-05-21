"""Phase 5 — per-turn articulation observation schema + sink.

The runtime emits one structured observation per engaged turn
(``discourse_contemplation=True`` AND planner produced a multi-move
plan).  Each observation bundles Phase 4 metrics and Phase 3 findings
plus identity context (turn_id, anchor subject, plan substrate hash)
so the offline contemplation miner (Phase 5) can aggregate across
many turns and emit reviewable pack-mutation candidates.

Doctrine alignment (ADR-0080 + ADR-0040):

* Read-only — observations are PROJECTIONS of plan state; nothing
  is mutated when they emit.
* Append-only — sinks ONLY accept JSONL lines; observations never
  rewrite or overwrite prior records.
* Deterministic — same plan + same metrics + same findings →
  byte-identical JSONL line.  Pinned by the
  ``test_observation_is_deterministic`` test.
* SPECULATIVE-only by transitivity — the findings carried inside
  each observation are themselves SPECULATIVE (enforced by the
  ContemplationFinding schema's __post_init__).

The sink protocol mirrors ``chat.telemetry.TurnEventSink``: any
object with ``def emit(line: str) -> None`` satisfies the contract.
Articulation observations flow through a SEPARATE sink (not the
turn-event sink) so consumers can subscribe to one stream without
the other, and the two streams' wire formats stay independent.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Iterable, Protocol


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ArticulationObservation:
    """One per-turn articulation observation.

    Carries the Phase 4 metrics dict + the Phase 3 findings (compacted
    to (kind, subject, predicate, object) tuples) plus identity fields.
    Both inner payloads are pre-serialised via ``as_dict()`` so the
    observation itself owns no live references — safe to log, archive,
    or stream without keeping the runtime alive.
    """

    turn_id: int
    """Sequential turn index within the emitting session (0-based)."""

    anchor_subject: str
    """The plan's anchor subject lemma — the most stable aggregation
    key.  For a typical EXPLAIN/PARAGRAPH plan this is the prompt's
    head noun; for compound prompts it is the primary part's
    subject."""

    prompt_hash: str
    """SHA-256-16 of the (lowercased, stripped) raw prompt text.
    Lets the miner detect repeated prompts without storing raw
    user input."""

    plan_substrate_hash: str
    """SHA-256-16 of the plan's canonical JSON.  Joins this
    observation to the Phase 3 contemplation findings that share
    the same substrate hash."""

    metrics: dict[str, Any]
    """Phase 4 ``PlanMetrics.as_dict()`` — see
    ``core.contemplation.plan_metrics`` for field list and
    semantics."""

    findings: tuple[dict[str, str | None], ...]
    """Phase 3 finding summaries — each is
    ``{"kind": <FindingKind.value>, "subject": <str>,
       "predicate": <str>, "object": <str|None>}``.  Compacted form;
    the full finding objects (with substrate_hash, finding_id,
    proposed_action, evidence_refs) are recoverable from a separate
    findings stream that emits via the existing
    ``DiscoveryCandidateSink``."""

    def as_dict(self) -> dict[str, Any]:
        return {
            "turn_id": self.turn_id,
            "anchor_subject": self.anchor_subject,
            "prompt_hash": self.prompt_hash,
            "plan_substrate_hash": self.plan_substrate_hash,
            "metrics": dict(self.metrics),
            "findings": [dict(f) for f in self.findings],
        }


# ---------------------------------------------------------------------------
# Serialisation
# ---------------------------------------------------------------------------


def serialize_articulation_observation(
    observation: ArticulationObservation,
) -> dict[str, Any]:
    """Return a JSON-safe deterministic dict.  Field order alphabetised
    by the sort_keys=True at the JSONL boundary."""
    return observation.as_dict()


def format_articulation_observation_jsonl(
    observation: ArticulationObservation,
) -> str:
    """One deterministic JSONL line (sort_keys; no trailing newline)."""
    return json.dumps(
        observation.as_dict(),
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )


def prompt_hash(prompt: str) -> str:
    """Stable 16-char prompt fingerprint.

    Lowercased + whitespace-collapsed so two presentations of the
    same logical prompt collapse to one hash.  Hashing means the
    raw prompt never has to be persisted — privacy-respecting and
    storage-cheap.
    """
    canonical = " ".join((prompt or "").strip().lower().split())
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Sink protocol
# ---------------------------------------------------------------------------


class ArticulationObservationSink(Protocol):
    """Append-only JSONL sink.  Structurally identical to
    ``chat.telemetry.TurnEventSink`` but kept as a distinct named
    type so consumers can subscribe to articulation observations
    without seeing the broader turn-event stream."""

    def emit(self, line: str) -> None: ...


# ---------------------------------------------------------------------------
# Loader (for the offline miner)
# ---------------------------------------------------------------------------


def load_articulation_observations(
    lines: Iterable[str],
) -> tuple[ArticulationObservation, ...]:
    """Parse a JSONL stream back into ``ArticulationObservation``s.

    Lines that fail to parse are SKIPPED — a malformed line in the
    middle of a long stream must not bring down the miner.  Caller
    can re-parse manually if strict parsing is needed.
    """
    out: list[ArticulationObservation] = []
    for raw in lines:
        raw = raw.strip()
        if not raw:
            continue
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            continue
        try:
            out.append(
                ArticulationObservation(
                    turn_id=int(payload["turn_id"]),
                    anchor_subject=str(payload["anchor_subject"]),
                    prompt_hash=str(payload["prompt_hash"]),
                    plan_substrate_hash=str(payload["plan_substrate_hash"]),
                    metrics=dict(payload["metrics"]),
                    findings=tuple(
                        dict(f) for f in payload["findings"]
                    ),
                )
            )
        except (KeyError, TypeError, ValueError):
            # Schema drift / partial record — skip rather than abort.
            continue
    return tuple(out)


__all__ = [
    "ArticulationObservation",
    "ArticulationObservationSink",
    "format_articulation_observation_jsonl",
    "load_articulation_observations",
    "prompt_hash",
    "serialize_articulation_observation",
]
