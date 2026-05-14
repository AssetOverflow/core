"""core.physics.binding — Temporal binding of co-activated field regions.

ADR-0009: Binding fuses co-activated regions into a BindingFrame
when cross-regional coherence exceeds threshold. Binding is triggered
by coherence threshold, not by clock tick.
"""

from __future__ import annotations
import hashlib
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
        region_ids = _region_ids(attention_plan)
        if not region_ids:
            return None
        coherence = _coherence(attention_plan, field_state)
        if coherence < coherence_threshold:
            return None
        ordered = tuple(sorted(region_ids))
        frame_id = _hash_parts(("frame", str(cycle_index), *ordered))
        content_address = _hash_parts((frame_id, f"{coherence:.12f}", *ordered))
        return BindingFrame(
            frame_id=frame_id,
            region_ids=frozenset(ordered),
            coherence_magnitude=coherence,
            cycle_index=cycle_index,
            content_address=content_address,
        )


def _region_ids(attention_plan) -> frozenset[str]:
    if hasattr(attention_plan, "steps"):
        return frozenset(str(step.region_id) for step in attention_plan.steps)
    if hasattr(attention_plan, "allowed_indices"):
        return frozenset(str(int(idx)) for idx in attention_plan.allowed_indices)
    return frozenset()


def _coherence(attention_plan, field_state) -> float:
    if hasattr(attention_plan, "steps") and attention_plan.steps:
        depths = [float(step.depth) for step in attention_plan.steps]
        return max(0.0, min(1.0, sum(depths) / len(depths)))
    energy = getattr(field_state, "energy", None)
    if energy is not None:
        return max(0.0, min(1.0, float(energy.raw)))
    return 1.0 if _region_ids(attention_plan) else 0.0


def _hash_parts(parts: tuple[str, ...]) -> str:
    h = hashlib.sha256()
    for part in parts:
        h.update(part.encode("utf-8"))
        h.update(b"\0")
    return h.hexdigest()
