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
        raise NotImplementedError(
            "InhibitionOperator.mask: implement interference suppression"
        )
