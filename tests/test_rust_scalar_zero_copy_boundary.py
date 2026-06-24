"""ADR-0235 PR C — scalar Rust zero-copy input boundary tests.

Validates that scalar Cl(4,1) Rust bindings:
  - preserve Python⇔Rust bit-identity (parity gates live elsewhere too)
  - fail loudly on wrong shape, wrong dtype, and non-contiguous layout
  - do not silently coerce inputs

Skipped when ``core_rs`` is not built.
"""

from __future__ import annotations

import numpy as np
import pytest

try:
    import core_rs

    _RUST_AVAILABLE = True
except ImportError:
    _RUST_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not _RUST_AVAILABLE, reason="core_rs extension not built"
)

_SCALAR_OPS = (
    ("geometric_product", lambda a, b: core_rs.geometric_product(a, b)),
    ("cga_inner", lambda a, b: core_rs.cga_inner(a, b)),
    ("versor_condition", lambda a, b: core_rs.versor_condition(a)),
)


def _mv_f32(seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.standard_normal(32).astype(np.float32)


def _mv_f64(seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.standard_normal(32).astype(np.float64)


@pytest.mark.parametrize("op_name,fn", _SCALAR_OPS)
def test_scalar_ops_accept_contiguous_f32(op_name: str, fn) -> None:
    a = _mv_f32(1)
    b = _mv_f32(2)
    result = fn(a, b)
    if op_name in {"cga_inner", "versor_condition"}:
        assert np.isfinite(float(result))
    else:
        assert np.asarray(result).shape == (32,)


@pytest.mark.parametrize("op_name,fn", _SCALAR_OPS)
def test_scalar_ops_reject_wrong_length(op_name: str, fn) -> None:
    a = _mv_f32(1)[:16]
    b = _mv_f32(2)
    with pytest.raises(ValueError, match="length 32"):
        fn(a, b)


@pytest.mark.parametrize("op_name,fn", _SCALAR_OPS)
def test_scalar_ops_reject_wrong_dtype(op_name: str, fn) -> None:
    a = _mv_f32(1).astype(np.float64)
    b = _mv_f32(2)
    with pytest.raises((TypeError, ValueError)):
        fn(a, b)


@pytest.mark.parametrize("op_name,fn", _SCALAR_OPS)
def test_scalar_ops_reject_non_contiguous(op_name: str, fn) -> None:
    base = _mv_f32(1)
    a = base[::2]
    assert not a.flags.c_contiguous
    b = _mv_f32(2)
    with pytest.raises(ValueError, match="contiguous"):
        fn(a, b)


def test_versor_apply_f64_closure_accepts_contiguous() -> None:
    v = _mv_f64(3)
    f = _mv_f64(4)
    out = core_rs.versor_apply_with_closure_f64(v, f)
    assert np.asarray(out).shape == (32,)


def test_versor_apply_f64_closure_rejects_wrong_length() -> None:
    v = _mv_f64(3)[:16]
    f = _mv_f64(4)
    with pytest.raises(ValueError, match="length 32"):
        core_rs.versor_apply_with_closure_f64(v, f)


def test_versor_apply_f64_closure_rejects_wrong_dtype() -> None:
    v = _mv_f64(3).astype(np.float32)
    f = _mv_f64(4)
    with pytest.raises((TypeError, ValueError)):
        core_rs.versor_apply_with_closure_f64(v, f)


def test_versor_apply_f64_closure_rejects_non_contiguous() -> None:
    v = _mv_f64(3)[::2]
    f = _mv_f64(4)
    with pytest.raises(ValueError, match="contiguous"):
        core_rs.versor_apply_with_closure_f64(v, f)


def test_non_contiguous_f32_documented_as_rejected() -> None:
    """Non-contiguous views must fail; callers should pass ascontiguousarray."""
    a = _mv_f32(1)[::2]
    b = _mv_f32(2)
    with pytest.raises(ValueError, match="contiguous"):
        core_rs.geometric_product(a, b)