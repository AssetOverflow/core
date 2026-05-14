"""core.physics.reasoning — Reasoning trajectories over BindingFrame sequences.

ADR-0009: A ReasoningTrajectory is an ordered sequence of BindingFrames
representing a chain of integrated thought. Each transition records the
pressure delta, continuity spine, and differential set between frames.
Trajectories are append-only; no in-place mutation after construction.
"""

from __future__ import annotations
import hashlib
from dataclasses import dataclass
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
        ordered = tuple(frames)
        transitions: list[TrajectoryTransition] = []
        for left, right in zip(ordered, ordered[1:]):
            left_regions = set(left.region_ids)
            right_regions = set(right.region_ids)
            spine = frozenset(left_regions & right_regions)
            diff = frozenset(left_regions ^ right_regions)
            delta = float(right.coherence_magnitude) - float(left.coherence_magnitude)
            transitions.append(
                TrajectoryTransition(
                    from_frame_id=left.frame_id,
                    to_frame_id=right.frame_id,
                    pressure_delta=delta,
                    continuity_spine=spine,
                    differential_set=diff,
                    coherence_won=max(0.0, delta),
                    coherence_lost=max(0.0, -delta),
                )
            )
        total = sum(t.pressure_delta for t in transitions)
        if ordered:
            span = (ordered[0].cycle_index, ordered[-1].cycle_index)
        else:
            span = (0, 0)
        resolved_id = trajectory_id or _trajectory_id(ordered)
        return ReasoningTrajectory(
            trajectory_id=resolved_id,
            frames=ordered,
            transitions=tuple(transitions),
            total_coherence_delta=float(total),
            cycle_span=span,
        )


def _trajectory_id(frames: tuple) -> str:
    h = hashlib.sha256()
    for frame in frames:
        h.update(frame.frame_id.encode("utf-8"))
    return h.hexdigest()
