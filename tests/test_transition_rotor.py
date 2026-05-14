from __future__ import annotations

import numpy as np
import pytest

from algebra.cl41 import N_COMPONENTS, geometric_product, reverse
from algebra.rotor import word_transition_rotor
from algebra.versor import unitize_versor, versor_apply, versor_condition


def _sample_rotor(seed: int) -> np.ndarray:
    raw = np.zeros(N_COMPONENTS, dtype=np.float32)
    raw[0] = 1.0
    raw[6 + (seed % 10)] = 0.04 + 0.01 * seed
    return unitize_versor(raw)


def test_word_transition_rotor_returns_identity_for_same_source_target() -> None:
    source = _sample_rotor(1)

    rotor = word_transition_rotor(source, source)

    expected = np.zeros(N_COMPONENTS, dtype=np.float32)
    expected[0] = 1.0
    np.testing.assert_allclose(rotor, expected, rtol=1e-6, atol=1e-6)
    assert versor_condition(rotor) < 1e-6


def test_word_transition_rotor_is_unit_for_valid_half_angle_candidate() -> None:
    source = np.zeros(N_COMPONENTS, dtype=np.float32)
    source[0] = 1.0
    target = _sample_rotor(2)

    rotor = word_transition_rotor(source, target)

    assert versor_condition(rotor) < 1e-4


def test_word_transition_rotor_uses_half_angle_candidate() -> None:
    source = np.zeros(N_COMPONENTS, dtype=np.float32)
    source[0] = 1.0
    target = _sample_rotor(3)

    rotor = word_transition_rotor(source, target)
    candidate = geometric_product(target, reverse(source)).astype(np.float32)
    candidate = candidate.copy()
    candidate[0] += 1.0
    expected = unitize_versor(candidate)

    np.testing.assert_allclose(rotor, expected, rtol=1e-6, atol=1e-6)


def test_word_transition_rotor_preserves_field_condition() -> None:
    source = np.zeros(N_COMPONENTS, dtype=np.float32)
    source[0] = 1.0
    target = _sample_rotor(4)
    field = _sample_rotor(5)

    rotor = word_transition_rotor(source, target)
    evolved = versor_apply(rotor, field)

    assert versor_condition(evolved) < 1e-4


def test_word_transition_rotor_rejects_non_unit_inputs_without_fallback() -> None:
    source = _sample_rotor(6)
    target = _sample_rotor(7) * np.float32(2.0)

    with pytest.raises(ValueError):
        word_transition_rotor(source, target)


def test_unitize_versor_rejects_non_scalar_residue_without_fallback() -> None:
    raw = np.zeros(N_COMPONENTS, dtype=np.float32)
    raw[1] = 1.0
    raw[6] = 1.0

    with pytest.raises(ValueError, match="non-scalar"):
        unitize_versor(raw)
