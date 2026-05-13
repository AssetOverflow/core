"""core.physics.salience — Salience as field curvature.

ADR-0008: Salience is not a scalar score on a token.
It is a curvature property of the versor field at a given region.
A region is salient when it measurably deflects the trajectories
of neighboring regions — when it bends the field around itself.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Tuple


@dataclass(frozen=True)
class FieldRegion:
    """A bounded region of the versor field identified by a stable key."""
    region_id: str
    # Geometric position encoded as a tuple of versor coordinates.
    # Dimensionality is determined by the active field configuration.
    coordinates: Tuple[float, ...]
    pressure_magnitude: float  # scalar magnitude of active pressure in this region

    def __post_init__(self) -> None:
        if not (0.0 <= self.pressure_magnitude):
            raise ValueError("pressure_magnitude must be non-negative")


@dataclass(frozen=True)
class SalienceEntry:
    """Curvature and directional salience for a single field region."""
    region_id: str
    curvature_magnitude: float   # how strongly this region bends the field
    gradient_vector: Tuple[float, ...]  # direction of maximum curvature
    influence_radius: float  # how far the curvature extends into neighboring regions


@dataclass(frozen=True)
class SalienceMap:
    """Structured salience result over a set of field regions."""
    entries: Tuple[SalienceEntry, ...]  # ordered high-to-low by curvature_magnitude
    cycle_index: int
    content_address: str  # SHA-256 over region_ids + curvature_magnitudes

    def top(self, n: int) -> Tuple[SalienceEntry, ...]:
        return self.entries[:n]


class SalienceOperator:
    """Computes field curvature over a set of FieldRegion objects.

    This is a pure transformation: given a set of regions,
    return a SalienceMap. No field state is mutated.

    Rust acceleration target: core_rs::physics::salience::compute_curvature
    """

    def compute(self, regions: Tuple[FieldRegion, ...], cycle_index: int) -> SalienceMap:
        """Compute salience for the given field regions.

        Stub: full curvature kernel implemented in Rust hot-path.
        Python fallback uses pairwise pressure gradient approximation.
        """
        raise NotImplementedError(
            "SalienceOperator.compute is a Rust hot-path stub. "
            "Implement in core_rs::physics::salience or provide Python fallback."
        )
