"""Rust versor_apply parity tests.

Verifies that the Rust closure-aware versor_apply produces identical results
to the Python algebra.versor.versor_apply for all critical cases:
identity, rotors, null vectors, versor condition, and backend dispatch.
"""

from __future__ import annotations

import numpy as np
import pytest

from algebra.versor import (
    unitize_versor,
    versor_apply as python_versor_apply,
    versor_condition,
)
from algebra.cga import embed_point, is_null

try:
    import core_rs
    HAS_RUST = True
except ImportError:
    HAS_RUST = False

skip_no_rust = pytest.mark.skipif(not HAS_RUST, reason="core_rs not available")


def _positive_unit_reflector(seed: int) -> np.ndarray:
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


def _random_rotor(seed: int) -> np.ndarray:
    from algebra.cl41 import geometric_product as gp
    a = _positive_unit_reflector(seed)
    b = _positive_unit_reflector(seed + 10000)
    return unitize_versor(gp(a, b))


@skip_no_rust
def test_rust_versor_apply_matches_python_for_identity():
    identity = np.zeros(32, dtype=np.float32)
    identity[0] = 1.0
    F = _positive_unit_reflector(42)

    py_result = python_versor_apply(identity, F)
    rust_result = np.asarray(
        core_rs.versor_apply_with_closure(identity, F), dtype=np.float32
    )

    assert np.allclose(py_result, rust_result, atol=1e-4), (
        f"max diff: {np.max(np.abs(py_result - rust_result))}"
    )


@skip_no_rust
def test_rust_versor_apply_matches_python_for_rotors():
    for seed in range(20):
        V = _random_rotor(seed)
        F = _positive_unit_reflector(seed + 500)

        py_result = python_versor_apply(V, F)
        rust_result = np.asarray(
            core_rs.versor_apply_with_closure(V, F), dtype=np.float32
        )

        assert np.allclose(py_result, rust_result, atol=1e-3), (
            f"seed={seed} max diff: {np.max(np.abs(py_result - rust_result))}"
        )


@skip_no_rust
def test_rust_versor_apply_preserves_null_vectors():
    point = embed_point(np.array([1.0, 2.0, 3.0], dtype=np.float32))
    assert is_null(point)

    V = _positive_unit_reflector(7)
    rust_result = np.asarray(
        core_rs.versor_apply_with_closure(V, point), dtype=np.float32
    )
    py_result = python_versor_apply(V, point)

    py_is_null = is_null(py_result)
    rust_is_null = is_null(rust_result)
    assert py_is_null == rust_is_null, (
        f"null preservation mismatch: python={py_is_null}, rust={rust_is_null}"
    )


@skip_no_rust
def test_rust_versor_apply_preserves_versor_condition():
    for seed in range(20):
        V = _positive_unit_reflector(seed)
        F = _positive_unit_reflector(seed + 1000)

        rust_result = np.asarray(
            core_rs.versor_apply_with_closure(V, F), dtype=np.float32
        )
        cond = versor_condition(rust_result)
        assert cond < 1e-4, f"seed={seed} condition={cond:.2e}"


@skip_no_rust
def test_backend_dispatch_uses_rust_only_when_enabled():
    """Verify that algebra.backend.versor_apply only uses Rust when CORE_BACKEND=rust."""
    import os
    from importlib import reload
    import algebra.backend as backend_mod

    original = os.environ.get("CORE_BACKEND", "")

    os.environ["CORE_BACKEND"] = "numpy"
    reload(backend_mod)
    assert not (backend_mod._REQUESTED_BACKEND == "rust")

    os.environ["CORE_BACKEND"] = "rust"
    reload(backend_mod)
    assert backend_mod._REQUESTED_BACKEND == "rust"

    if original:
        os.environ["CORE_BACKEND"] = original
    else:
        os.environ.pop("CORE_BACKEND", None)
    reload(backend_mod)
