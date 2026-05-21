"""Salience curvature vectorization parity (perf 2026-05-21).

The pre-fix ``SalienceOperator.compute`` was a nested Python loop over
``regions × regions``.  For N≈500 mounted-vocab regions per turn it ran
~250k ``np.linalg.norm`` calls per turn and dominated ~64% of total
chat() time (cProfile attribution).

The vectorized version uses numpy broadcast for pairwise distance
and contribution.  Math is unchanged, but float-sum reassociation
can shift values at ULP level.  These tests pin:

  1. Parity with a reference implementation matching the pre-fix
     nested-loop semantics, to better than 1e-9 absolute on
     curvature_magnitude (well below the 12-decimal precision used
     by ``_salience_address``).
  2. ``content_address`` equality on the byte-level — proves the
     SHA-256 fingerprint stays stable.
  3. Top-k ordering by curvature_magnitude is preserved.
"""

from __future__ import annotations

import hashlib
from typing import Tuple

import numpy as np
import pytest

from core.physics.salience import (
    FieldRegion,
    SalienceEntry,
    SalienceMap,
    SalienceOperator,
)


def _reference_compute(
    regions: Tuple[FieldRegion, ...], cycle_index: int
) -> SalienceMap:
    """Pre-fix nested-loop reference for parity comparison."""
    if not regions:
        return SalienceMap(entries=(), cycle_index=cycle_index, content_address=_ref_address(()))
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
            pressure_delta = abs(
                float(neighbor.pressure_magnitude) - float(region.pressure_magnitude)
            )
            contribution = pressure_delta / (distance * distance)
            direction = delta / distance
            gradient += direction * contribution
            curvature += contribution
            radius_num += distance * contribution
            radius_den += contribution
        entries.append(
            SalienceEntry(
                region_id=region.region_id,
                curvature_magnitude=float(curvature),
                gradient_vector=tuple(float(v) for v in gradient),
                influence_radius=float(radius_num / radius_den) if radius_den > 0.0 else 0.0,
            )
        )
    ordered = tuple(
        sorted(entries, key=lambda entry: (-entry.curvature_magnitude, entry.region_id))
    )
    return SalienceMap(entries=ordered, cycle_index=cycle_index, content_address=_ref_address(ordered))


def _ref_address(entries: Tuple[SalienceEntry, ...]) -> str:
    h = hashlib.sha256()
    for entry in entries:
        h.update(entry.region_id.encode("utf-8"))
        h.update(f":{entry.curvature_magnitude:.12f}:".encode("ascii"))
        h.update(",".join(f"{v:.12f}" for v in entry.gradient_vector).encode("ascii"))
    return h.hexdigest()


def _make_regions(n: int, dim: int = 5, seed: int = 0) -> Tuple[FieldRegion, ...]:
    rng = np.random.default_rng(seed)
    coords = rng.standard_normal((n, dim))
    pressures = np.abs(rng.standard_normal(n))
    return tuple(
        FieldRegion(
            region_id=f"r{i:03d}",
            coordinates=tuple(float(v) for v in coords[i]),
            pressure_magnitude=float(pressures[i]),
        )
        for i in range(n)
    )


@pytest.mark.parametrize("n", [1, 2, 8, 32, 128, 493])
def test_vectorized_parity_curvature_magnitude(n: int) -> None:
    """Vectorized curvature matches the nested-loop reference to 1e-9."""
    regions = _make_regions(n, seed=42)
    fast = SalienceOperator().compute(regions, cycle_index=0)
    ref = _reference_compute(regions, cycle_index=0)
    assert len(fast.entries) == len(ref.entries)
    # Build region_id → curvature map for both, compare.
    fast_by_id = {e.region_id: e for e in fast.entries}
    ref_by_id = {e.region_id: e for e in ref.entries}
    for rid in fast_by_id:
        f = fast_by_id[rid]
        r = ref_by_id[rid]
        assert f.curvature_magnitude == pytest.approx(r.curvature_magnitude, abs=1e-9, rel=1e-9)
        assert f.influence_radius == pytest.approx(r.influence_radius, abs=1e-9, rel=1e-9)
        for fv, rv in zip(f.gradient_vector, r.gradient_vector):
            assert fv == pytest.approx(rv, abs=1e-9, rel=1e-9)


@pytest.mark.parametrize("n", [1, 8, 32, 128])
def test_vectorized_content_address_byte_stable(n: int) -> None:
    """SHA-256 content_address is byte-identical (12-decimal precision
    truncation hides ULP-level reassociation drift)."""
    regions = _make_regions(n, seed=17)
    fast = SalienceOperator().compute(regions, cycle_index=0)
    ref = _reference_compute(regions, cycle_index=0)
    assert fast.content_address == ref.content_address


@pytest.mark.parametrize("n", [32, 128, 493])
def test_vectorized_top_k_ordering_matches(n: int) -> None:
    """Top-k by curvature stays identical — load-bearing for the
    walk's salience candidate set."""
    regions = _make_regions(n, seed=99)
    fast = SalienceOperator().compute(regions, cycle_index=0)
    ref = _reference_compute(regions, cycle_index=0)
    fast_top = [e.region_id for e in fast.entries[:16]]
    ref_top = [e.region_id for e in ref.entries[:16]]
    assert fast_top == ref_top


def test_empty_regions_returns_empty_map() -> None:
    fast = SalienceOperator().compute((), cycle_index=42)
    assert fast.entries == ()
    assert fast.cycle_index == 42


def test_single_region_has_zero_curvature() -> None:
    """A region with no neighbors has nothing to curve against."""
    regions = _make_regions(1, seed=1)
    fast = SalienceOperator().compute(regions, cycle_index=0)
    assert len(fast.entries) == 1
    assert fast.entries[0].curvature_magnitude == 0.0
    assert fast.entries[0].influence_radius == 0.0
