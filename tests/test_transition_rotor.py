from __future__ import annotations

import numpy as np
import pytest

from algebra.cl41 import geometric_product, reverse
from algebra.rotor import word_transition_rotor
from algebra.versor import unitize_versor, versor_apply, versor_condition


def _sample_versor(seed: int) -> np.ndarray:
    raw = np.zeros(32, dtype=np.float32)
    raw[0] = 1.0
    raw[6 + (seed % 10)] = 0.1 + 0.03 * seed
    raw[16 + (seed % 10)] = 0.02 * (seed + 1)
    return unitize_versor(raw)


def test_word_transition_rotor_is_closed_unit_versor() -> None:
    source = _sample_versor(1)
    target = _sample_versor(2)

    rotor = word_transition_rotor(source, target)

    assert versor_condition(rotor) < 1e-4


def test_word_transition_rotor_matches_closed_product() -> None:
    source = _sample_versor(3)
    target = _sample_versor(4)

    rotor = word_transition_rotor(source, target)
    expected = geometric_product(target, reverse(source)).astype(np.float32)

    np.testing.assert_allclose(rotor, expected, rtol=1e-6, atol=1e-6)


def test_word_transition_rotor_identity_for_same_source_target() -> None:
    source = _sample_versor(5)

    rotor = word_transition_rotor(source, source)

    assert versor_condition(rotor) < 1e-4
    np.testing.assert_allclose(rotor[1:], np.zeros(31, dtype=np.float32), rtol=1e-5, atol=1e-5)
    assert abs(float(rotor[0]) - 1.0) < 1e-5


def test_word_transition_rotor_preserves_field_condition() -> None:
    source = _sample_versor(6)
    target = _sample_versor(7)
    field = _sample_versor(8)

    rotor = word_transition_rotor(source, target)
    evolved = versor_apply(rotor, field)

    assert versor_condition(evolved) < 1e-4


def test_word_transition_rotor_rejects_non_unit_inputs() -> None:
    source = _sample_versor(9)
    target = _sample_versor(10) * np.float32(2.0)

    with pytest.raises(ValueError, match="not a unit versor"):
        word_transition_rotor(source, target)
