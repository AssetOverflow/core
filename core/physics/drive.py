"""core.physics.drive — Drive gradients as persistent field biases.

ADR-0010: Drives are not preferences or weights. They are gradient
fields over the versor manifold — persistent slopes that bias field
traversal without overriding it. Multiple drives compose additively
into a combined gradient landscape.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Tuple


@dataclass(frozen=True)
class ValueAxis:
    """A named geometric direction in the versor manifold."""
    axis_id: str
    name: str          # human-readable (e.g., 'truthfulness', 'depth', 'reverence')
    direction: Tuple[float, ...]  # unit vector in manifold coordinate space
    theological_note: str  # explicit grounding in CORE's foundational commitments


@dataclass(frozen=True)
class GradientField:
    """A persistent gradient bias over the versor manifold for one ValueAxis."""
    axis: ValueAxis
    magnitude: float   # strength of the drive gradient (0.0 = inactive, 1.0 = maximum)
    active: bool = True


@dataclass(frozen=True)
class DriveGradientMap:
    """Composited gradient landscape from all active drives."""
    gradients: Tuple[GradientField, ...]

    def combined_bias(self, coordinates: Tuple[float, ...]) -> Tuple[float, ...]:
        """Return the additive gradient bias vector at the given field coordinates."""
        raise NotImplementedError("DriveGradientMap.combined_bias: implement gradient composition")
