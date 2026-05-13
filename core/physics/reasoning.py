"""core.physics.reasoning — Reasoning trajectories over BindingFrame sequences.

ADR-0009: A ReasoningTrajectory is an ordered sequence of BindingFrames
representing a chain of integrated thought. Each transition records the
pressure delta, continuity spine, and differential set between frames.
Trajectories are append-only; no in-place mutation after construction.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import FrozenSet, Tuple


@dataclass(frozen=True)
class TrajectoryTransition:
    """Structural record of the transition between two BindingFrames."""
    from_frame_id: str
    to_frame_id: str
    pressure_delta: float
    continuity_spine: FrozenSet[str]   # region IDs stable across transition
    differential_set: FrozenSet[str]   # region IDs that entered or exited
    coherence_won: float
    coherence_lost: float


@dataclass(frozen=True)
class ReasoningTrajectory:
    """Append-only sequence of BindingFrames with transition records."""
    trajectory_id: str
    frames: Tuple  # Tuple[BindingFrame, ...]
    transitions: Tuple[TrajectoryTransition, ...]  # len == len(frames) - 1
    total_coherence_delta: float
    cycle_span: Tuple[int, int]  # (start_cycle, end_cycle)


class TrajectoryOperator:
    """Builds a ReasoningTrajectory from an ordered sequence of BindingFrames."""

    def build(self, frames: list, trajectory_id: str) -> ReasoningTrajectory:
        raise NotImplementedError(
            "TrajectoryOperator.build: implement trajectory construction"
        )
