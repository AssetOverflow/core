"""core.physics.salience — Salience as field curvature.

ADR-0008: Salience is not a scalar score on a token.
It is a curvature property of the versor field at a given region.
A region is salient when it measurably deflects the trajectories
of neighboring regions — when it bends the field around itself.
"""

from __future__ import annotations
import hashlib
from dataclasses import dataclass
from typing import Tuple

import numpy as np


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
        """Compute local curvature by pairwise pressure-gradient deflection."""
        if not regions:
            return SalienceMap(entries=(), cycle_index=cycle_index, content_address=_salience_address(()))
        coords = [np.asarray(region.coordinates, dtype=np.float64) for region in regions]
        entries: list[SalienceEntry] = []
        for idx, region in enumerate(regions):
            gradient = np.zeros_like(coords[idx], dtype=np.float64)
            curvature = 0.0
            radius_num = 0.0
            radius_den = 0.0
            for jdx, neighbor in enumerate(regions):
                if idx == jdx:
                    continue
                delta = coords[jdx] - coords[idx]
                distance = max(float(np.linalg.norm(delta)), 1e-8)
                pressure_delta = abs(float(neighbor.pressure_magnitude) - float(region.pressure_magnitude))
                contribution = pressure_delta / (distance * distance)
                direction = delta / distance
                gradient += direction * contribution
                curvature += contribution
                radius_num += distance * contribution
                radius_den += contribution
            gradient_tuple = tuple(float(v) for v in gradient)
            entries.append(
                SalienceEntry(
                    region_id=region.region_id,
                    curvature_magnitude=float(curvature),
                    gradient_vector=gradient_tuple,
                    influence_radius=float(radius_num / radius_den) if radius_den > 0.0 else 0.0,
                )
            )
        ordered = tuple(
            sorted(entries, key=lambda entry: (-entry.curvature_magnitude, entry.region_id))
        )
        return SalienceMap(
            entries=ordered,
            cycle_index=cycle_index,
            content_address=_salience_address(ordered),
        )


def _salience_address(entries: Tuple[SalienceEntry, ...]) -> str:
    h = hashlib.sha256()
    for entry in entries:
        h.update(entry.region_id.encode("utf-8"))
        h.update(f":{entry.curvature_magnitude:.12f}:".encode("ascii"))
        h.update(",".join(f"{v:.12f}" for v in entry.gradient_vector).encode("ascii"))
    return h.hexdigest()
