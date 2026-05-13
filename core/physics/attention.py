"""core.physics.attention — Attention as controlled field traversal.

ADR-0008: Attention is the act of directing cognitive traversal
along high-salience curvature gradients. The AttentionOperator
produces a traversal schedule (AttentionPlan), not a weight distribution.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class CoherenceBudget:
    """Explicit resource envelope for a single cognitive cycle."""
    total_capacity: float
    committed: float    # units allocated to active traversal
    reserve: float      # units held for inhibition / correction passes
    spent: float = 0.0  # units consumed so far this cycle

    def __post_init__(self) -> None:
        if self.committed + self.reserve > self.total_capacity:
            raise ValueError("committed + reserve must not exceed total_capacity")

    @property
    def available(self) -> float:
        return self.committed - self.spent


@dataclass(frozen=True)
class TraversalStep:
    """A single step in the attention traversal schedule."""
    region_id: str
    depth: float        # how deeply to activate this region (0.0–1.0)
    duration: float     # how many sub-cycles to hold activation
    cost: float         # CoherenceBudget units consumed by this step


@dataclass(frozen=True)
class AttentionPlan:
    """Ordered traversal schedule produced by AttentionOperator."""
    steps: Tuple[TraversalStep, ...]
    total_cost: float
    cycle_index: int


class AttentionOperator:
    """Produces an AttentionPlan from a SalienceMap and CoherenceBudget."""

    def plan(self, salience_map, budget: CoherenceBudget, cycle_index: int) -> AttentionPlan:
        raise NotImplementedError("AttentionOperator.plan: implement traversal scheduling")
