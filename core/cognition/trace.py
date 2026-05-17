"""
Deterministic trace hashing for cognitive turns.

The hash captures every meaningful output of a pipeline run so that:
  - identical inputs on identical field state → identical hash
  - any output change → different hash

Only stable, semantically meaningful fields are included.  Floating-point
values are rounded to 9 decimal places before hashing so that numeric
noise from different hardware does not break determinism within a run.
"""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.cognition.result import CognitiveTurnResult


def _round_float(v: float, ndigits: int = 9) -> float:
    return round(float(v), ndigits)


def compute_trace_hash(
    input_text: str,
    filtered_tokens: tuple[str, ...],
    surface: str,
    walk_surface: str,
    articulation_surface: str,
    dialogue_role: str,
    versor_condition: float,
    vault_hits: int,
    intent_tag: str = "unknown",
    teaching_review_hash: str = "",
    teaching_proposal_id: str = "",
    teaching_epistemic_status: str = "",
    operator_invocation: str = "",
    admissibility_trace_hash: str = "",
    ratification_outcome: str = "",
    region_was_unconstrained: bool = True,
) -> str:
    """Return a deterministic SHA-256 hex digest over the turn's key outputs.

    Parameters match the subset of CognitiveTurnResult that is both
    semantically meaningful and stable across hardware.

    ``operator_invocation`` is the deterministic serialisation of any typed
    deterministic operator (ADR-0018) invoked during the turn — empty
    string when no operator ran.  Folding it explicitly makes operator
    invocation a load-bearing part of replay equality, not just an
    indirect consequence of surface-change.

    ``teaching_epistemic_status`` is the serialised EpistemicStatus of the
    pack mutation proposal load-bearing in this turn — empty string when
    no proposal was emitted.  Folded per ADR-0021 §Consequences so replay
    detects when a downstream surface was produced under a different
    epistemic frame than at the time of recall.
    """
    payload = {
        "input_text": input_text,
        "filtered_tokens": list(filtered_tokens),
        "surface": surface,
        "walk_surface": walk_surface,
        "articulation_surface": articulation_surface,
        "dialogue_role": str(dialogue_role),
        "versor_condition": _round_float(versor_condition),
        "vault_hits": int(vault_hits),
        "intent_tag": intent_tag,
        "teaching_review_hash": teaching_review_hash,
        "teaching_proposal_id": teaching_proposal_id,
        "teaching_epistemic_status": teaching_epistemic_status,
        "operator_invocation": operator_invocation,
    }
    # ADR-0023 additions are folded in only when they carry non-default
    # values, so a turn unaffected by forward semantic control keeps the
    # exact same payload bytes as before ADR-0023.  Once a turn does
    # carry admissibility evidence, those keys become load-bearing in
    # replay equality.
    if admissibility_trace_hash:
        payload["admissibility_trace_hash"] = admissibility_trace_hash
    if ratification_outcome:
        payload["ratification_outcome"] = ratification_outcome
    if not region_was_unconstrained:
        payload["region_was_unconstrained"] = False
    serialized = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def hash_admissibility_trace(trace: tuple) -> str:
    """SHA-256 over the canonical serialization of an admissibility trace.

    Returns the empty string for an empty trace so callers can
    short-circuit the ADR-0023 payload addition (preserving pre-ADR-0023
    trace_hash bytes for turns that did not run admissibility).
    """
    if not trace:
        return ""
    serialized = json.dumps(
        [step.canonical() for step in trace],
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def trace_hash_from_result(result: "CognitiveTurnResult") -> str:
    """Convenience wrapper — compute the hash directly from a result object."""
    intent_tag = result.intent.tag.value if result.intent is not None else "unknown"
    review_hash = (
        result.reviewed_teaching_example.review_hash
        if result.reviewed_teaching_example is not None
        else ""
    )
    proposal_id = (
        result.pack_mutation_proposal.proposal_id
        if result.pack_mutation_proposal is not None
        else ""
    )
    epistemic_status = (
        result.pack_mutation_proposal.epistemic_status.value
        if result.pack_mutation_proposal is not None
        else ""
    )
    return compute_trace_hash(
        input_text=result.input_text,
        filtered_tokens=result.filtered_tokens,
        surface=result.surface,
        walk_surface=result.walk_surface,
        articulation_surface=result.articulation_surface,
        dialogue_role=str(result.dialogue_role),
        versor_condition=result.versor_condition,
        vault_hits=result.vault_hits,
        intent_tag=intent_tag,
        teaching_review_hash=review_hash,
        teaching_proposal_id=proposal_id,
        teaching_epistemic_status=epistemic_status,
        operator_invocation=result.operator_invocation,
        admissibility_trace_hash=getattr(result, "admissibility_trace_hash", ""),
        ratification_outcome=getattr(result, "ratification_outcome", ""),
        region_was_unconstrained=getattr(result, "region_was_unconstrained", True),
    )
