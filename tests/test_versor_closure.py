"""
CRITICAL: This test must pass before any other file is extended.
It verifies the core algebraic invariant of the entire system.
"""

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from algebra.rotor import word_transition_rotor
from algebra.versor import (
    unitize_versor,
    versor_apply,
    versor_condition,
    versor_unit_residual,
)


def _positive_unit_reflector(seed=None) -> np.ndarray:
    """
    Construct a true positive-norm Cl(4,1) grade-1 versor.

    The current field action uses V * F * reverse(V), so the operator fixture
    must satisfy V * reverse(V) = +1, not -1. We therefore keep the fifth
    basis component bounded below the positive four-space norm.
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
    V = _positive_unit_reflector(seed)
    F = _positive_unit_reflector(seed + 1000)
    result = versor_apply(V, F)
    cond = versor_condition(result)
    assert cond < 1e-4, f"versor_apply broke the manifold: condition={cond:.2e}"


def test_unitize_clean_scalar_constructs_positive_unit_versor():
    raw = np.zeros(32, dtype=np.float32)
    raw[0] = 2.0
    V = unitize_versor(raw)
    assert np.allclose(V[0], 1.0, atol=1e-7)
    assert versor_condition(V) < 1e-7


def test_unitize_rejects_non_scalar_residue_instead_of_hash_fallback():
    dirty = np.zeros(32, dtype=np.float32)
    dirty[0] = np.sqrt(0.5)
    dirty[1] = np.sqrt(0.5)

    with pytest.raises(ValueError, match="bad_residue"):
        unitize_versor(dirty)


def test_unitize_rejects_non_positive_scalar_norm():
    negative_norm = np.zeros(32, dtype=np.float32)
    negative_norm[5] = 1.0

    with pytest.raises(ValueError, match="bad_scalar"):
        unitize_versor(negative_norm)


def test_versor_unit_residual_can_accept_signed_manifold_versors():
    negative_norm = np.zeros(32, dtype=np.float32)
    negative_norm[5] = 1.0

    assert versor_condition(negative_norm) > 1.0
    assert versor_unit_residual(negative_norm, allow_negative=True) < 1e-7


def test_word_transition_rotor_handles_antipodal_scalar_inputs_as_closed_transition():
    A = np.zeros(32, dtype=np.float32)
    A[0] = 1.0
    B = np.zeros(32, dtype=np.float32)
    B[0] = -1.0

    R = word_transition_rotor(A, B)

    assert np.allclose(R[0], -1.0, atol=1e-7)
    assert versor_condition(R) < 1e-6


def test_composition_closed():
    V1 = _positive_unit_reflector(0)
    V2 = _positive_unit_reflector(1)
    F = _positive_unit_reflector(2)
    F2 = versor_apply(V1, F)
    F3 = versor_apply(V2, F2)
    assert versor_condition(F3) < 1e-4


def test_versor_apply_closes_null_like_field_results_for_runtime_contract():
    identity = np.zeros(32, dtype=np.float32)
    identity[0] = 1.0
    null_like = np.zeros(32, dtype=np.float32)
    null_like[1] = 1.0
    null_like[5] = 1.0

    result = versor_apply(identity, null_like)

    assert versor_condition(result) < 1e-6


def test_identity_versor():
    identity = np.zeros(32, dtype=np.float32)
    identity[0] = 1.0
    F = _positive_unit_reflector(42)
    result = versor_apply(identity, F)
    assert np.allclose(result, F, atol=1e-5)
