"""Tests for algebra.rotor.rotor_power — manifold-preserving rotor scaling.

The drift-fix #2 originally used linear interpolation between a rotor and
identity, which produced multivectors with versor_condition ≈ 10⁻², violating
the non-negotiable 1e-6 invariant. ``rotor_power`` replaces that with a proper
slerp on the rotor manifold: identity -> R^α stays on the manifold for any α.
"""

from __future__ import annotations

import numpy as np
import pytest

from algebra.rotor import make_rotor_from_angle, rotor_power, word_transition_rotor
from algebra.versor import versor_condition

_TOL = 1e-6


@pytest.mark.parametrize("angle", [0.05, 0.3, 0.7, 1.2, np.pi / 2])
@pytest.mark.parametrize("alpha", [0.0, 0.1, 0.3, 0.5, 0.7, 0.9, 1.0])
def test_rotor_power_preserves_versor_closure(angle: float, alpha: float) -> None:
    """For any rotation rotor and any fractional power, output is a closed unit rotor."""
    R = make_rotor_from_angle(angle, bivector_idx=7)
    R_alpha = rotor_power(R, alpha)
    assert versor_condition(R_alpha) < _TOL, (
        f"rotor_power(R(angle={angle}), {alpha}) violates closure: "
        f"versor_condition = {versor_condition(R_alpha):.3e}"
    )


def test_rotor_power_alpha_zero_returns_identity() -> None:
    R = make_rotor_from_angle(0.7, bivector_idx=7)
    R_zero = rotor_power(R, 0.0)
    expected = np.zeros(32, dtype=R_zero.dtype)
    expected[0] = 1.0
    np.testing.assert_allclose(R_zero, expected, atol=1e-9)


def test_rotor_power_alpha_one_returns_input() -> None:
    R = make_rotor_from_angle(0.4, bivector_idx=7)
    R_one = rotor_power(R, 1.0)
    np.testing.assert_allclose(R_one, R, atol=1e-9)


def test_rotor_power_half_angle_halves_rotation() -> None:
    """R^0.5 applied twice equals R."""
    from algebra.cl41 import geometric_product

    R = make_rotor_from_angle(0.8, bivector_idx=7)
    R_half = rotor_power(R, 0.5)
    R_half_squared = geometric_product(R_half, R_half)
    np.testing.assert_allclose(R_half_squared, R, atol=1e-6)


def test_rotor_power_handles_identity_input() -> None:
    """Identity rotor under any power stays identity."""
    identity = np.zeros(32, dtype=np.float64)
    identity[0] = 1.0
    for alpha in [0.0, 0.3, 1.0, 1.5]:
        result = rotor_power(identity, alpha)
        np.testing.assert_allclose(result, identity, atol=1e-9)


def test_rotor_power_on_word_transition_preserves_closure() -> None:
    """The real-world case: rotors produced by word_transition_rotor."""
    A = np.zeros(32, dtype=np.float64)
    A[0] = 1.0
    B = np.zeros(32, dtype=np.float64)
    B[0] = np.cos(0.4)
    B[7] = np.sin(0.4)

    R = word_transition_rotor(A, B)
    for alpha in [0.05, 0.2, 0.5, 0.8, 0.95]:
        R_alpha = rotor_power(R, alpha)
        cond = versor_condition(R_alpha)
        assert cond < _TOL, f"alpha={alpha}: versor_condition = {cond:.3e}"


def test_rotor_power_rejects_wrong_shape() -> None:
    with pytest.raises(ValueError):
        rotor_power(np.zeros(16, dtype=np.float64), 0.5)
