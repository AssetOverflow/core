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
        """Compute local curvature by pairwise pressure-gradient deflection.

        Vectorized 2026-05-21 — pre-fix this was a nested Python loop
        over ``regions × regions`` with one ``np.linalg.norm`` call per
        pair.  For N≈500 mounted-vocab regions per turn that meant
        ~250k norm calls per turn, dominating ~64% of total turn time
        (cProfile, 2026-05-21).  The math is unchanged: pairwise
        pressure-gradient deflection.  The contract — curvature_magnitude,
        gradient_vector, influence_radius — is preserved exactly, with
        only ULP-level drift from float-sum reassociation (well below
        the 12-decimal precision used by ``_salience_address`` and
        the float32 precision used by downstream score arrays).
        """
        if not regions:
            return SalienceMap(entries=(), cycle_index=cycle_index, content_address=_salience_address(()))

        # (N, D) coordinate matrix and (N,) pressure vector.
        coords = np.stack(
            [np.asarray(region.coordinates, dtype=np.float64) for region in regions]
        )
        pressures = np.asarray(
            [region.pressure_magnitude for region in regions], dtype=np.float64
        )

        # Pairwise displacement: deltas[i, j] = coords[j] - coords[i].
        deltas = coords[None, :, :] - coords[:, None, :]  # (N, N, D)
        # Pairwise Euclidean distance, clamped to >= 1e-8 (matches the
        # historical max(..., 1e-8) per-pair guard).
        distances = np.linalg.norm(deltas, axis=-1)  # (N, N)
        np.maximum(distances, 1e-8, out=distances)
        # Avoid 0/0 on the diagonal; zero its contributions later.
        np.fill_diagonal(distances, 1.0)

        # Pairwise pressure deltas: |pressures[j] - pressures[i]|.
        pressure_deltas = np.abs(pressures[None, :] - pressures[:, None])  # (N, N)

        # contribution[i, j] = pressure_delta[i, j] / distance[i, j]^2
        contributions = pressure_deltas / (distances * distances)
        np.fill_diagonal(contributions, 0.0)  # exclude i == i

        # direction[i, j] = deltas[i, j] / distance[i, j];  diagonal direction
        # vectors are zero by construction (deltas[i, i] = 0).
        directions = deltas / distances[..., None]  # (N, N, D)

        # Per-region aggregates: sum-over-j with diagonal contributions zeroed.
        # gradient[i] = Σ_j direction[i, j] * contribution[i, j]
        gradients = np.einsum("ijd,ij->id", directions, contributions)
        curvatures = contributions.sum(axis=1)  # (N,)
        radius_num = (distances * contributions).sum(axis=1)
        radius_den = curvatures  # identical sum
        radii = np.where(radius_den > 0.0, radius_num / np.where(radius_den > 0, radius_den, 1.0), 0.0)

        entries: list[SalienceEntry] = []
        for idx, region in enumerate(regions):
            entries.append(
                SalienceEntry(
                    region_id=region.region_id,
                    curvature_magnitude=float(curvatures[idx]),
                    gradient_vector=tuple(float(v) for v in gradients[idx]),
                    influence_radius=float(radii[idx]),
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
