"""Bit-exact array codec — the foundation of Shape B+ persistence.

The whole resume-as-same-life flip depends on float arrays round-tripping with
ZERO precision loss: a versor that is valid (versor_condition < 1e-6) and a
trace_hash that is deterministic must both survive save->load unchanged. Decimal
JSON would truncate and break both, so the codec uses base64 of the raw bytes.
"""

from __future__ import annotations

import numpy as np

from core.array_codec import (
    decode_array,
    decode_optional_array,
    encode_array,
    encode_optional_array,
)


def test_float32_round_trips_bit_exact() -> None:
    a = np.array([1.0, -2.5, 3.1415927, 1e-7, 1e30, 0.0], dtype=np.float32)
    decoded = decode_array(encode_array(a))
    assert decoded.dtype == np.float32
    assert decoded.shape == a.shape
    # Bit-exact: the raw bytes are identical, not just "close".
    assert decoded.tobytes() == a.tobytes()
    assert np.array_equal(decoded, a)


def test_float64_round_trips_bit_exact_and_preserves_dtype() -> None:
    a = np.array([np.pi, np.e, 1e-300, -1e300], dtype=np.float64)
    decoded = decode_array(encode_array(a))
    assert decoded.dtype == np.float64  # float32 vs float64 must NOT be conflated
    assert decoded.tobytes() == a.tobytes()


def test_int32_2d_shape_round_trips() -> None:
    edges = np.array([[0, 1], [1, 2], [2, 0]], dtype=np.int32)
    decoded = decode_array(encode_array(edges))
    assert decoded.dtype == np.int32
    assert decoded.shape == (3, 2)
    assert np.array_equal(decoded, edges)


def test_encoding_is_not_decimal() -> None:
    # The payload must carry base64 bytes, never decimal floats (which truncate).
    payload = encode_array(np.array([0.1], dtype=np.float32))
    assert set(payload.keys()) == {"dtype", "shape", "b64"}
    assert isinstance(payload["b64"], str)
    assert "0.1" not in payload["b64"]


def test_decoded_array_is_writable_copy() -> None:
    # frombuffer returns a read-only view; the codec must hand back a copy so
    # the restored field can be composed/mutated like a fresh one.
    decoded = decode_array(encode_array(np.zeros(4, dtype=np.float32)))
    decoded[0] = 1.0  # must not raise


def test_optional_array_handles_none() -> None:
    assert encode_optional_array(None) is None
    assert decode_optional_array(None) is None
    a = np.array([1.0, 2.0], dtype=np.float32)
    assert np.array_equal(decode_optional_array(encode_optional_array(a)), a)
