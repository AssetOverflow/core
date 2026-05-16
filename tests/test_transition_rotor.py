from __future__ import annotations

import numpy as np
import pytest

from algebra.cl41 import geometric_product, reverse
from algebra.rotor import make_rotor_from_angle, word_transition_rotor
from algebra.versor import versor_apply, versor_condition


def test_identity_transition_returns_identity_rotor() -> None:
    A = make_rotor_from_angle(0.31, bivector_idx=6)

    R = word_transition_rotor(A, A)

    expected = np.zeros(32, dtype=R.dtype)
    expected[0] = 1.0
    np.testing.assert_allclose(R, expected, atol=1e-6)
    assert versor_condition(R) < 1e-6


def test_transition_rotor_is_exact_closed_product() -> None:
    A = make_rotor_from_angle(0.25, bivector_idx=6)
    B = make_rotor_from_angle(-0.40, bivector_idx=6)

    R = word_transition_rotor(A, B)
    expected = geometric_product(B, reverse(A))

    np.testing.assert_allclose(R, expected, atol=1e-6)
    assert versor_condition(R) < 1e-6


def test_transition_rotor_preserves_field_condition() -> None:
    A = make_rotor_from_angle(0.15, bivector_idx=6)
    B = make_rotor_from_angle(0.45, bivector_idx=6)
    field = make_rotor_from_angle(-0.20, bivector_idx=6)

    R = word_transition_rotor(A, B)
    transitioned = versor_apply(R, field)

    assert versor_condition(R) < 1e-6
    assert versor_condition(transitioned) < 1e-6


def test_transition_rotor_rejects_non_closed_candidate_instead_of_fallback() -> None:
    A = np.zeros(32, dtype=np.float64)
    A[0] = 1.0
    B = np.ones(32, dtype=np.float64)

    with pytest.raises(ValueError, match="non_closed|non_positive"):
        word_transition_rotor(A, B)


def test_transition_rotor_rejects_near_zero_input() -> None:
    A = np.zeros(32, dtype=np.float64)
    B = make_rotor_from_angle(0.25, bivector_idx=6)

    with pytest.raises(ValueError, match="near_zero"):
        word_transition_rotor(A, B)
