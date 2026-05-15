"""deterministic_hash_versor tests — determinism, uniqueness, closure."""

import numpy as np

from algebra.backend import versor_condition
from sensorium.adapters.text import deterministic_hash_versor


class TestDeterministicHash:
    def test_deterministic(self) -> None:
        a = deterministic_hash_versor("hello")
        b = deterministic_hash_versor("hello")
        np.testing.assert_array_equal(a, b)

    def test_different_inputs_differ(self) -> None:
        a = deterministic_hash_versor("alpha")
        b = deterministic_hash_versor("beta")
        assert not np.array_equal(a, b)

    def test_versor_condition(self) -> None:
        v = deterministic_hash_versor("test string")
        assert versor_condition(v) < 1e-6

    def test_output_shape_and_dtype(self) -> None:
        v = deterministic_hash_versor("shape check")
        assert v.shape == (32,)
        assert v.dtype == np.float32

    def test_empty_string(self) -> None:
        v = deterministic_hash_versor("")
        assert versor_condition(v) < 1e-6
