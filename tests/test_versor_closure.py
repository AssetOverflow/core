"""
CRITICAL: This test must pass before any other file is extended.
It verifies the core algebraic invariant of the entire system.
"""

import numpy as np
from hypothesis import given, settings
from hypothesis import strategies as st

from algebra.versor import versor_apply, unitize_versor, versor_condition


def _positive_unit_reflector(seed=None) -> np.ndarray:
    """
    Construct a true positive-norm Cl(4,1) grade-1 versor.

    The current field action uses V * F * reverse(V), so the operator fixture
    must satisfy V * reverse(V) = +1, not -1. We therefore keep the fifth
    (negative-metric) basis component bounded below the positive four-space
    norm before construction-unitizing.
    """
    rng = np.random.default_rng(seed)
    vec4 = rng.standard_normal(4).astype(np.float32)
    norm4 = float(np.linalg.norm(vec4))
    if norm4 < 1e-6:
        vec4[0] = 1.0
        norm4 = 1.0

    vec = np.zeros(5, dtype=np.float32)
    vec[:4] = vec4
    vec[4] = 0.25 * norm4 * np.tanh(float(rng.standard_normal()))

    mv = np.zeros(32, dtype=np.float32)
    mv[1:6] = vec
    return unitize_versor(mv)


@given(st.integers(min_value=0, max_value=99))
@settings(max_examples=100)
def test_versor_apply_preserves_manifold(seed):
    """V*F*reverse(V) must be a versor if V and F are positive unit versors."""
    V = _positive_unit_reflector(seed)
    F = _positive_unit_reflector(seed + 1000)
    result = versor_apply(V, F)
    cond = versor_condition(result)
    assert cond < 1e-4, f"versor_apply broke the manifold: condition={cond:.2e}"


def test_unitize_random_multivector_constructs_versor():
    """
    unitize_versor() is the construction primitive for lifting raw
    deterministic coordinates into a valid versor.
    """
    raw = np.random.default_rng(0).standard_normal(32).astype(np.float32)
    V = unitize_versor(raw)
    assert versor_condition(V) < 1e-5


def test_composition_closed():
    """Two sequential versor_apply calls stay on the manifold."""
    V1 = _positive_unit_reflector(0)
    V2 = _positive_unit_reflector(1)
    F = _positive_unit_reflector(2)
    F2 = versor_apply(V1, F)
    F3 = versor_apply(V2, F2)
    assert versor_condition(F3) < 1e-4


def test_identity_versor():
    """Scalar 1 is a valid versor and applies as identity."""
    identity = np.zeros(32, dtype=np.float32)
    identity[0] = 1.0
    F = _positive_unit_reflector(42)
    result = versor_apply(identity, F)
    assert np.allclose(result, F, atol=1e-5)
