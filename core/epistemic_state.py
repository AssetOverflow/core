"""First-class epistemic-state and normative-clearance enums.

Phase 3 of the epistemic-state program makes the ratified taxonomy
queryable from runtime artifacts without entangling callers with the
scope document.  The values are intentionally lower_snake_case so they
serialize stably into JSONL, metadata dictionaries, and test fixtures.
"""

from __future__ import annotations

from enum import Enum, unique
from typing import Any


@unique
class EpistemicState(str, Enum):
    PERCEIVED = "perceived"
    EVIDENCED = "evidenced"
    EVIDENCED_INCOMPLETE = "evidenced_incomplete"
    VERIFIED = "verified"
    DECODED = "decoded"
    DECODED_UNARTICULATED = "decoded_unarticulated"
    INFERRED = "inferred"
    UNVERIFIED_POSSIBLE = "unverified_possible"
    UNVERIFIED_NOVEL = "unverified_novel"
    CONTRADICTED = "contradicted"
    AMBIGUOUS = "ambiguous"
    UNDETERMINED = "undetermined"
    SCOPE_BOUNDARY = "scope_boundary"
    COMPUTATIONALLY_BOUNDED = "computationally_bounded"
    EPISTEMIC_STATE_NEEDED = "epistemic_state_needed"


@unique
class NormativeClearance(str, Enum):
    CLEARED = "cleared"
    VIOLATED = "violated"
    UNASSESSABLE = "unassessable"
    SUPPRESSED = "suppressed"


def coerce_epistemic_state(value: object | None, *, default: EpistemicState = EpistemicState.UNDETERMINED) -> EpistemicState:
    if isinstance(value, EpistemicState):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower().replace("-", "_")
        for state in EpistemicState:
            if normalized in {state.value, state.name.lower()}:
                return state
    return default


def coerce_normative_clearance(value: object | None, *, default: NormativeClearance = NormativeClearance.UNASSESSABLE) -> NormativeClearance:
    if isinstance(value, NormativeClearance):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower().replace("-", "_")
        for clearance in NormativeClearance:
            if normalized in {clearance.value, clearance.name.lower()}:
                return clearance
    return default


def clearance_from_verdicts(verdicts: Any = None, *, safety_verdict: Any = None, ethics_verdict: Any = None) -> NormativeClearance:
    """Derive the orthogonal normative-clearance state for a turn.

    Refusal replacement is a SUPPRESSED surface.  Otherwise any failed
    safety/ethics verdict is VIOLATED.  If every available verdict is
    upheld but at least one result was not runtime-checkable, the turn is
    UNASSESSABLE rather than positively CLEARED.  Only fully upheld and
    fully runtime-checkable verdicts are CLEARED.
    """
    if verdicts is not None:
        if bool(getattr(verdicts, "refusal_emitted", False)):
            return NormativeClearance.SUPPRESSED
        safety_verdict = safety_verdict if safety_verdict is not None else getattr(verdicts, "safety_verdict", None)
        ethics_verdict = ethics_verdict if ethics_verdict is not None else getattr(verdicts, "ethics_verdict", None)

    saw_unassessable = False
    saw_verdict = False
    for verdict in (safety_verdict, ethics_verdict):
        if verdict is None:
            continue
        saw_verdict = True
        if not bool(getattr(verdict, "upheld", True)):
            return NormativeClearance.VIOLATED
        results = tuple(getattr(verdict, "results", ()) or ())
        if any(not bool(getattr(result, "runtime_checkable", True)) for result in results):
            saw_unassessable = True
        elif int(getattr(verdict, "runtime_checkable_count", 0) or 0) == 0:
            saw_unassessable = True
    if not saw_verdict or saw_unassessable:
        return NormativeClearance.UNASSESSABLE
    return NormativeClearance.CLEARED


def epistemic_state_for_grounding_source(source: str | None) -> EpistemicState:
    """Default runtime mapping for existing grounding-source labels."""
    normalized = (source or "none").strip().lower()
    if normalized in {"pack", "teaching", "vault"}:
        return EpistemicState.DECODED
    if normalized == "partial":
        return EpistemicState.EVIDENCED_INCOMPLETE
    if normalized == "oov":
        return EpistemicState.UNVERIFIED_NOVEL
    if normalized == "none":
        return EpistemicState.UNDETERMINED
    return EpistemicState.EPISTEMIC_STATE_NEEDED


__all__ = [
    "EpistemicState",
    "NormativeClearance",
    "clearance_from_verdicts",
    "coerce_epistemic_state",
    "coerce_normative_clearance",
    "epistemic_state_for_grounding_source",
]
