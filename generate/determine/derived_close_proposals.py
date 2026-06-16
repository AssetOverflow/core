"""PR-2: deterministic proposal bridge from proof-gated derived CLOSE facts.

Collects realized derived facts (member/subset + TRANSITIVE_PREDICATES) that carry
a Derivation with verdict="entailed" and are SPECULATIVE. Emits reviewable proposal-only
artifacts (source="derived_close_fact") to a dedicated sink.

- Default-off via RuntimeConfig.review_derived_close_proposals
- Review-gated, proposal-only (never ratification or corpus mutation)
- Deterministic dedupe by stable key (predicate + args + derivation + structure_key)
- Skips non-derived, malformed, unsupported, non-entailed safely
- Best-effort; failures do not corrupt state or set did_work on engine checkpoint

Intended to be called from idle_tick *after* consolidation (Step D) so that newly
derived facts can immediately surface as proposals.
"""

from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
from typing import Any

from generate.meaning_graph.relational import TRANSITIVE_PREDICATES
from generate.realize import RealizedRecord, recall_realized

#: Dedicated sink for derived CLOSE proposals (distinct from comprehension-failures
#: to keep families clean while still reviewable by the same HITL tooling).
DEFAULT_SINK = (
    Path(__file__).resolve().parents[3]
    / "teaching"
    / "proposals"
    / "derived_close_facts"
)


def _stable_dedupe_key(rec: RealizedRecord) -> str:
    """Stable dedupe key for a derived record. Includes derivation provenance so that
    a re-derived fact with different proof chain is treated as distinct if premises differ."""
    if rec.derivation is None:
        return ""
    key = (
        rec.relation_predicate,
        rec.relation_arguments[0] if len(rec.relation_arguments) > 0 else "",
        rec.relation_arguments[1] if len(rec.relation_arguments) > 1 else "",
        rec.derivation.rule,
        tuple(rec.derivation.premise_structure_keys),
        rec.structure_key,
    )
    return sha256(repr(key).encode("utf-8")).hexdigest()


def _is_eligible(rec: RealizedRecord) -> bool:
    if not rec.derived or rec.derivation is None:
        return False
    if rec.derivation.verdict != "entailed":
        return False
    if getattr(rec, "epistemic_status", None) != "speculative":
        return False
    p = rec.relation_predicate
    if p not in {"member", "subset"} and p not in TRANSITIVE_PREDICATES:
        return False
    if len(getattr(rec, "relation_arguments", ())) != 2:
        return False
    return True


def emit_derived_close_proposals(
    ctx: "SessionContext",
    *,
    sink: Path | None = None,
    max_emissions: int = 100,
) -> dict[str, int]:
    """Scan realized facts for eligible derived CLOSE conclusions and emit proposal artifacts.

    Returns counts:
      considered, eligible, emitted, duplicate, skipped

    Artifacts are written only for first sighting (deduped by stable key).
    Order is deterministic (sorted by (predicate, subject, object)).
    """
    sink = sink or DEFAULT_SINK
    sink.mkdir(parents=True, exist_ok=True)

    considered = 0
    eligible = 0
    emitted = 0
    duplicate = 0
    skipped = 0

    candidates: list[tuple[str, str, str, RealizedRecord]] = []

    # member and subset first (from PR-1 is-a), then the relational transitive
    for p in ["member", "subset"] + sorted(TRANSITIVE_PREDICATES):
        for rec in recall_realized(ctx, predicate=p):
            considered += 1
            if _is_eligible(rec):
                eligible += 1
                candidates.append(
                    (p, rec.relation_arguments[0], rec.relation_arguments[1], rec)
                )

    # deterministic global order
    candidates.sort(key=lambda t: (t[0], t[1], t[2]))

    for p, subj, obj, rec in candidates:
        if emitted >= max_emissions:
            break
        dkey = _stable_dedupe_key(rec)
        path = sink / f"{dkey}.json"
        if path.exists():
            duplicate += 1
            continue

        artifact: dict[str, Any] = {
            "source": "derived_close_fact",
            "predicate": rec.relation_predicate,
            "subject": subj,
            "object": obj,
            "relation_arguments": list(rec.relation_arguments),
            "derivation": {
                "rule": rec.derivation.rule,
                "verdict": rec.derivation.verdict,
                "premise_structure_keys": list(rec.derivation.premise_structure_keys),
            },
            "epistemic_status": rec.epistemic_status,
            "structure_key": rec.structure_key,
            "dedupe_key": dkey,
            "status": "proposal_only",
            "requires_review": True,
            "mounted": False,
        }
        path.write_text(
            json.dumps(artifact, indent=2, sort_keys=True), encoding="utf-8"
        )
        emitted += 1

    return {
        "considered": considered,
        "eligible": eligible,
        "emitted": emitted,
        "duplicate": duplicate,
        "skipped": skipped,
    }


__all__ = ["emit_derived_close_proposals", "DEFAULT_SINK"]