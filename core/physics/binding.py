"""core.physics.binding — Temporal binding of co-activated field regions.

ADR-0009: Binding fuses co-activated regions into a BindingFrame
when cross-regional coherence exceeds threshold. Binding is triggered
by coherence threshold, not by clock tick.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import FrozenSet


@dataclass(frozen=True)
class BindingFrame:
    """Structured snapshot of co-activated field regions at binding time."""
    frame_id: str             # SHA-256 over region_ids + cycle_index
    region_ids: FrozenSet[str]
    coherence_magnitude: float
    cycle_index: int
    content_address: str     # SHA-256 over full frame for deduplication


class BindingOperator:
    """Produces a BindingFrame when co-activation reaches coherence threshold.

    Returns None if coherence threshold is not met — the cycle
    closes without a binding event in that case.
    """

    def bind(
        self,
        attention_plan,
        field_state,
        coherence_threshold: float,
        cycle_index: int,
    ) -> BindingFrame | None:
        raise NotImplementedError("BindingOperator.bind: implement co-activation fusion")
