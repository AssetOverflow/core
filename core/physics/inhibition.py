"""core.physics.inhibition — Inhibition as dual correction.

ADR-0008: Inhibition is not the absence of attention.
It is an active structural force that prevents interference
between competing pressure regions. Every AttentionPlan
has a conjugate InhibitionMask applied before traversal begins.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import FrozenSet


@dataclass(frozen=True)
class InhibitionMask:
    """Set of region IDs suppressed before the current traversal cycle."""
    suppressed_region_ids: FrozenSet[str]
    suppression_reason: str   # human-readable rationale for the suppression set
    coherence_delta: float    # estimated coherence gain from applying this mask
    cycle_index: int


class InhibitionOperator:
    """Computes the InhibitionMask conjugate to a given AttentionPlan.

    Consumes from CoherenceBudget.reserve, not from committed units.
    Must run before field traversal begins.
    """

    def mask(self, attention_plan, field_state, cycle_index: int) -> InhibitionMask:
        active = _active_regions(attention_plan)
        suppressed = _candidate_regions(field_state) - active
        coherence_delta = min(1.0, 0.05 * len(suppressed))
        return InhibitionMask(
            suppressed_region_ids=frozenset(sorted(suppressed)),
            suppression_reason="outside_attention_plan",
            coherence_delta=coherence_delta,
            cycle_index=cycle_index,
        )


def _active_regions(attention_plan) -> set[str]:
    if hasattr(attention_plan, "steps"):
        return {str(step.region_id) for step in attention_plan.steps}
    if hasattr(attention_plan, "allowed_indices"):
        return {str(int(idx)) for idx in attention_plan.allowed_indices}
    return set()


def _candidate_regions(field_state) -> set[str]:
    candidates = getattr(field_state, "candidate_region_ids", None)
    if candidates is None:
        return set()
    return {str(region_id) for region_id in candidates}
