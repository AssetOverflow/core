"""
CRITICAL: This test must pass before any other file is extended.
It verifies the core algebraic invariant of the entire system.
"""

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from algebra.versor import versor_apply, normalize_to_versor, versor_condition


def _random_versor(seed=None) -> np.ndarray:
    rng = np.random.default_rng(seed)
    raw = rng.standard_normal(32).astype(np.float32)
    return normalize_to_versor(raw)


@given(st.integers(min_value=0, max_value=99))
@settings(max_examples=100)
def test_versor_apply_preserves_manifold(seed):
    """V*F*reverse(V) must be a versor if V and F are versors."""
    V = _random_versor(seed)
    F = _random_versor(seed + 1000)
    result = versor_apply(V, F)
    cond = versor_condition(result)
    assert cond < 1e-4, f"versor_apply broke the manifold: condition={cond:.2e}"


def test_normalize_produces_versor():
    raw = np.random.randn(32).astype(np.float32)
    V = normalize_to_versor(raw)
    assert versor_condition(V) < 1e-6


def test_composition_closed():
    """Two sequential versor_apply calls stay on the manifold."""
    V1 = _random_versor(0)
    V2 = _random_versor(1)
    F = _random_versor(2)
    F2 = versor_apply(V1, F)
    F3 = versor_apply(V2, F2)
    assert versor_condition(F3) < 1e-4


def test_identity_versor():
    """Scalar 1 is a valid versor and applies as identity."""
    identity = np.zeros(32, dtype=np.float32)
    identity[0] = 1.0
    F = _random_versor(42)
    result = versor_apply(identity, F)
    assert np.allclose(result, F, atol=1e-5)
