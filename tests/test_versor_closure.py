"""
CRITICAL: This test must pass before any other file is extended.
It verifies the core algebraic invariant of the entire system.
"""

import numpy as np
from hypothesis import given, settings
from hypothesis import strategies as st

from algebra.versor import versor_apply, unitize_versor, versor_condition


def _unit_reflector(seed=None) -> np.ndarray:
    """
    Construct a true Cl(4,1) versor: a unit grade-1 vector.

    Scaling an arbitrary 32D multivector does not make it a versor. A unit
    vector is a valid reflector by construction and satisfies v * ~v = ±1.
    """
    rng = np.random.default_rng(seed)
    vec = rng.standard_normal(5).astype(np.float32)
    # Avoid accidentally producing an exactly null vector under (+,+,+,+,-).
    if abs(float(np.dot(vec[:4], vec[:4]) - vec[4] * vec[4])) < 1e-4:
        vec[0] += 1.0
    mv = np.zeros(32, dtype=np.float32)
    mv[1:6] = vec
    return unitize_versor(mv)


@given(st.integers(min_value=0, max_value=99))
@settings(max_examples=100)
def test_versor_apply_preserves_manifold(seed):
    """V*F*reverse(V) must be a versor if V and F are versors."""
    V = _unit_reflector(seed)
    F = _unit_reflector(seed + 1000)
    result = versor_apply(V, F)
    cond = versor_condition(result)
    assert cond < 1e-4, f"versor_apply broke the manifold: condition={cond:.2e}"


def test_unitize_random_multivector_is_not_claimed_to_create_versor():
    """
    Unitizing arbitrary 32D garbage is not versor construction.

    unitize_versor() scales a construction product; it does not project an
    arbitrary multivector onto the versor manifold. This test prevents the
    old false fixture from returning.
    """
    raw = np.random.default_rng(0).standard_normal(32).astype(np.float32)
    V = unitize_versor(raw)
    assert versor_condition(V) > 1e-3


def test_composition_closed():
    """Two sequential versor_apply calls stay on the manifold."""
    V1 = _unit_reflector(0)
    V2 = _unit_reflector(1)
    F = _unit_reflector(2)
    F2 = versor_apply(V1, F)
    F3 = versor_apply(V2, F2)
    assert versor_condition(F3) < 1e-4


def test_identity_versor():
    """Scalar 1 is a valid versor and applies as identity."""
    identity = np.zeros(32, dtype=np.float32)
    identity[0] = 1.0
    F = _unit_reflector(42)
    result = versor_apply(identity, F)
    assert np.allclose(result, F, atol=1e-5)
