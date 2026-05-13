"""core.physics.exertion — Exertion tracking and fatigue modeling.

ADR-0010: Identity is not infinitely elastic. Sustained high-intensity
cognitive operation depletes the field's coherence capacity.
The ExertionMeter tracks cumulative activation cost and computes
a FatigueIndex that modulates available CoherenceBudget.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Tuple


@dataclass(frozen=True)
class CycleCost:
    """Resource consumption record for a single cognitive cycle."""
    cycle_index: int
    attention_cost: float
    inhibition_cost: float
    digest_cost: float
    trajectory_cost: float

    @property
    def total(self) -> float:
        return self.attention_cost + self.inhibition_cost + self.digest_cost + self.trajectory_cost


@dataclass(frozen=True)
class FatigueIndex:
    """Scalar fatigue state in [0.0, 1.0].

    0.0 = fully rested, full coherence capacity available.
    1.0 = fully depleted, minimum coherence capacity available.
    Values between 0.0 and 1.0 compress CoherenceBudget proportionally.
    """
    value: float
    computed_at_cycle: int

    def __post_init__(self) -> None:
        if not (0.0 <= self.value <= 1.0):
            raise ValueError("FatigueIndex.value must be in [0.0, 1.0]")

    def apply_to_budget(self, total_capacity: float) -> float:
        """Return the available capacity after fatigue compression."""
        return total_capacity * (1.0 - self.value)


class ExertionMeter:
    """Tracks cumulative activation cost and computes FatigueIndex.

    rest() resets accumulated cost to zero (end of a deliberate rest point).
    fatigue() returns the current FatigueIndex without modifying state.
    """

    def __init__(self, capacity_ceiling: float) -> None:
        self._capacity_ceiling = capacity_ceiling
        self._cycle_costs: list[CycleCost] = []

    def record(self, cost: CycleCost) -> None:
        self._cycle_costs.append(cost)

    def fatigue(self, at_cycle: int) -> FatigueIndex:
        total_spent = sum(c.total for c in self._cycle_costs)
        ratio = min(total_spent / self._capacity_ceiling, 1.0)
        return FatigueIndex(value=ratio, computed_at_cycle=at_cycle)

    def rest(self) -> None:
        self._cycle_costs.clear()
