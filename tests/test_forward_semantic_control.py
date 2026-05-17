"""Tests for Forward Semantic Control (ADR-0022).

This is the v1 test surface for ``generate/admissibility.py``.  It
verifies the algebraic properties the ADR's acceptance criteria
depend on:

  * Composition is the neutral-element-respecting fold (TBD-2).
  * Empty-intersection token sets are preserved (must trigger
    honest refusal at the call site, not silent relaxation).
  * The admissibility check is a pure function — no IO, no state.
  * Replay determinism: same (region, candidate) → same verdict
    byte-for-byte.

The end-to-end "constrained-walk surface vs. unconstrained-walk
surface" replay test lives under
``evals/forward_semantic_control/`` — see that lane's contract.md
for the criteria the ADR's acceptance gate (1) requires.
"""

from __future__ import annotations

import numpy as np
import pytest

from algebra.cga import outer_product
from generate.admissibility import (
    AdmissibilityRegion,
    RegionSource,
    check_transition,
    filter_candidates,
    intersect,
    region_from_frame_relation,
    region_from_relation_chain,
    unconstrained,
)


_BLADE_DIM = 32


def _blade(seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.standard_normal(_BLADE_DIM).astype(np.float32)


def _versor_like(seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.standard_normal(_BLADE_DIM).astype(np.float32)


# ----------------------------------------------------------------------
# Construction & invariants
# ----------------------------------------------------------------------


class TestAdmissibilityRegion:
    def test_unconstrained_is_neutral(self) -> None:
        region = unconstrained()
        assert region.is_unconstrained()
        assert region.admits_index(0)
        assert region.admits_index(999_999)
        assert region.admits_versor(_versor_like(0))

    def test_indices_are_normalised_to_unique_sorted_int64(self) -> None:
        region = AdmissibilityRegion(allowed_indices=np.array([3, 1, 1, 2, 3]))
        assert region.allowed_indices is not None
        assert region.allowed_indices.dtype == np.int64
        np.testing.assert_array_equal(region.allowed_indices, np.array([1, 2, 3]))

    def test_blade_shape_is_validated(self) -> None:
        with pytest.raises(ValueError):
            AdmissibilityRegion(relation_blade=np.zeros(16, dtype=np.float32))

    def test_admits_index_respects_set(self) -> None:
        region = AdmissibilityRegion(allowed_indices=np.array([5, 7, 9]))
        assert region.admits_index(7)
        assert not region.admits_index(8)

    def test_admits_versor_skips_zero_blade(self) -> None:
        region = AdmissibilityRegion(allowed_indices=np.array([1, 2]))
        # zero blade → direction unconstrained
        assert region.admits_versor(_versor_like(11))

    def test_admits_versor_uses_cga_inner_against_blade(self) -> None:
        blade = _blade(3)
        region = AdmissibilityRegion(relation_blade=blade)
        # The blade itself maximally satisfies the region; a random
        # unrelated direction does not (with threshold 0 it may or may
        # not — but the *blade direction* must always satisfy).
        assert region.admits_versor(blade, threshold=-1e9)


# ----------------------------------------------------------------------
# Composition (TBD-2)
# ----------------------------------------------------------------------


class TestComposition:
    def test_unconstrained_is_left_identity(self) -> None:
        a = unconstrained()
        b = AdmissibilityRegion(
            allowed_indices=np.array([1, 2, 3]),
            relation_blade=_blade(7),
            label="b",
        )
        c = intersect(a, b)
        np.testing.assert_array_equal(c.allowed_indices, b.allowed_indices)
        np.testing.assert_array_equal(c.relation_blade, b.relation_blade)
        assert c.source is RegionSource.COMPOSED

    def test_unconstrained_is_right_identity(self) -> None:
        a = AdmissibilityRegion(
            allowed_indices=np.array([4, 5]),
            relation_blade=_blade(9),
            label="a",
        )
        b = unconstrained()
        c = intersect(a, b)
        np.testing.assert_array_equal(c.allowed_indices, a.allowed_indices)
        np.testing.assert_array_equal(c.relation_blade, a.relation_blade)

    def test_token_sets_intersect_sorted(self) -> None:
        a = AdmissibilityRegion(allowed_indices=np.array([1, 2, 3, 4]))
        b = AdmissibilityRegion(allowed_indices=np.array([3, 4, 5, 6]))
        c = intersect(a, b)
        np.testing.assert_array_equal(c.allowed_indices, np.array([3, 4]))

    def test_empty_intersection_is_preserved_not_relaxed(self) -> None:
        """ADR-0022 §2: an empty admissible set must remain empty so
        the propagate site can fail honestly.  Silently relaxing to
        ``None`` (universal) is the exact failure mode the ADR exists
        to eliminate."""
        a = AdmissibilityRegion(allowed_indices=np.array([1, 2]))
        b = AdmissibilityRegion(allowed_indices=np.array([3, 4]))
        c = intersect(a, b)
        assert c.allowed_indices is not None
        assert len(c.allowed_indices) == 0

    def test_zero_blade_is_neutral_in_blade_composition(self) -> None:
        a = AdmissibilityRegion(relation_blade=_blade(2))
        b = AdmissibilityRegion()  # zero blade default
        c = intersect(a, b)
        np.testing.assert_array_equal(c.relation_blade, a.relation_blade)

    def test_label_composes_both_sides(self) -> None:
        a = AdmissibilityRegion(label="frame[copular]")
        b = AdmissibilityRegion(label="intent[definition]")
        c = intersect(a, b)
        assert "frame[copular]" in c.label
        assert "intent[definition]" in c.label

    def test_composition_is_deterministic(self) -> None:
        a = AdmissibilityRegion(
            allowed_indices=np.array([2, 3, 5, 7]),
            relation_blade=_blade(42),
            label="a",
        )
        b = AdmissibilityRegion(
            allowed_indices=np.array([3, 5, 11]),
            relation_blade=_blade(43),
            label="b",
        )
        c1 = intersect(a, b)
        c2 = intersect(a, b)
        np.testing.assert_array_equal(c1.allowed_indices, c2.allowed_indices)
        np.testing.assert_array_equal(c1.relation_blade, c2.relation_blade)
        assert c1.label == c2.label


# ----------------------------------------------------------------------
# Admissibility check (used at the propagate site)
# ----------------------------------------------------------------------


class TestCheckTransition:
    def test_unconstrained_admits_anything(self) -> None:
        verdict = check_transition(
            unconstrained(),
            candidate_index=42,
            candidate_versor=_versor_like(0),
        )
        assert verdict.admitted is True

    def test_index_outside_set_is_rejected_with_named_reason(self) -> None:
        region = AdmissibilityRegion(
            allowed_indices=np.array([1, 2, 3]),
            label="frame[copular]",
        )
        verdict = check_transition(
            region,
            candidate_index=99,
            candidate_versor=_versor_like(0),
        )
        assert verdict.admitted is False
        assert "99" in verdict.reason
        assert verdict.region_label == "frame[copular]"

    def test_blade_threshold_is_respected(self) -> None:
        blade = _blade(5)
        region = AdmissibilityRegion(relation_blade=blade, label="rel[X]")
        # An arbitrary versor likely scores below an extreme positive threshold
        verdict = check_transition(
            region,
            candidate_index=0,
            candidate_versor=_versor_like(6),
            threshold=1e9,
        )
        assert verdict.admitted is False
        assert verdict.region_label == "rel[X]"

    def test_zero_blade_admits_with_no_blade_constraint_reason(self) -> None:
        region = AdmissibilityRegion(allowed_indices=np.array([0, 1, 2]))
        verdict = check_transition(
            region,
            candidate_index=1,
            candidate_versor=_versor_like(7),
        )
        assert verdict.admitted is True
        assert "no blade constraint" in verdict.reason

    def test_verdict_is_pure_replayable(self) -> None:
        region = AdmissibilityRegion(
            allowed_indices=np.array([1, 2, 3]),
            relation_blade=_blade(11),
            label="r",
        )
        v = _versor_like(12)
        v1 = check_transition(region, candidate_index=2, candidate_versor=v)
        v2 = check_transition(region, candidate_index=2, candidate_versor=v)
        assert v1 == v2


# ----------------------------------------------------------------------
# filter_candidates bridge
# ----------------------------------------------------------------------


class TestFilterCandidates:
    def test_none_region_passes_input_through(self) -> None:
        region = unconstrained()
        out = filter_candidates(region, np.array([1, 2, 3], dtype=np.int64))
        np.testing.assert_array_equal(out, np.array([1, 2, 3]))

    def test_none_input_returns_region_indices(self) -> None:
        region = AdmissibilityRegion(allowed_indices=np.array([4, 5, 6]))
        out = filter_candidates(region, None)
        np.testing.assert_array_equal(out, np.array([4, 5, 6]))

    def test_both_none_returns_none(self) -> None:
        assert filter_candidates(unconstrained(), None) is None

    def test_intersection_preserves_empty(self) -> None:
        region = AdmissibilityRegion(allowed_indices=np.array([1, 2]))
        out = filter_candidates(region, np.array([3, 4]))
        assert out is not None
        assert len(out) == 0


# ----------------------------------------------------------------------
# Constructors
# ----------------------------------------------------------------------


class TestConstructors:
    def test_region_from_frame_relation_tags_as_frame(self) -> None:
        blade = _blade(1)
        region = region_from_frame_relation(blade, label="frame[copular]")
        assert region.source is RegionSource.FRAME
        assert region.label == "frame[copular]"
        np.testing.assert_array_equal(region.relation_blade, blade)

    def test_region_from_relation_chain_outer_products(self) -> None:
        a = _versor_like(20)
        b = _versor_like(21)
        region = region_from_relation_chain([a, b], label="rel-chain")
        assert region.source is RegionSource.RELATION
        expected = outer_product(a, b)
        np.testing.assert_allclose(region.relation_blade, expected)

    def test_region_from_relation_chain_empty(self) -> None:
        region = region_from_relation_chain([])
        assert region.source is RegionSource.RELATION
        assert float(np.linalg.norm(region.relation_blade)) == 0.0
