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
        steps: list[TraversalStep] = []
        spent = 0.0
        max_curvature = max(
            (float(entry.curvature_magnitude) for entry in salience_map.entries),
            default=0.0,
        )
        if max_curvature <= 0.0:
            return AttentionPlan(steps=(), total_cost=0.0, cycle_index=cycle_index)
        for entry in salience_map.entries:
            depth = max(0.0, min(1.0, float(entry.curvature_magnitude) / max_curvature))
            duration = max(1.0, float(entry.influence_radius))
            cost = depth * duration
            if spent + cost > budget.available:
                break
            steps.append(
                TraversalStep(
                    region_id=entry.region_id,
                    depth=depth,
                    duration=duration,
                    cost=cost,
                )
            )
            spent += cost
        return AttentionPlan(steps=tuple(steps), total_cost=spent, cycle_index=cycle_index)
