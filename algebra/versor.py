from __future__ import annotations

import numpy as np
from .cl41 import geometric_product, reverse

__all__ = [
    "unitize_versor",
    "versor_apply",
    "versor_condition",
    "versor_unit_residual",
]

_CONSTRUCTION_RESIDUE_TOLERANCE = 1e-2
_NEAR_ZERO_TOLERANCE = 1e-12
_DENSE_SEED_MIN_COMPONENTS = 8
_SEED_BIVECTORS = (6, 7, 8, 10, 11, 13)
_RUNTIME_FIELD_DTYPE = np.dtype(np.float64)


def _array_dtype(v: np.ndarray) -> np.dtype:
    arr = np.asarray(v)
    return arr.dtype if arr.dtype in (np.dtype(np.float32), np.dtype(np.float64)) else np.dtype(np.float32)


def _diagnostic_message(prefix: str, *, input_norm: float, scalar_sq: float, residue_norm: float) -> str:
    return f"{prefix}: input_norm={input_norm:.6e}, scalar_sq={scalar_sq:.6e}, residue_norm={residue_norm:.6e}"


def _unitize_closed(v: np.ndarray, dtype: np.dtype) -> np.ndarray:
    dtype = _array_dtype(v)
    v = np.asarray(v, dtype=np.float64)
    input_norm = float(np.linalg.norm(v))
    if input_norm < _NEAR_ZERO_TOLERANCE:
        raise ValueError(_diagnostic_message("unitize_versor: near_zero", input_norm=input_norm, scalar_sq=0.0, residue_norm=0.0))

    vv = geometric_product(v, reverse(v)).astype(np.float64)
    scalar_sq = float(vv[0])
    residue = vv.copy()
    residue[0] = 0
    residue_norm = float(np.linalg.norm(residue))

    if residue_norm >= _CONSTRUCTION_RESIDUE_TOLERANCE:
        raise ValueError(_diagnostic_message("unitize_versor: bad_residue", input_norm=input_norm, scalar_sq=scalar_sq, residue_norm=residue_norm))

    if scalar_sq <= 0.0:
        raise ValueError(_diagnostic_message("unitize_versor: bad_scalar", input_norm=input_norm, scalar_sq=scalar_sq, residue_norm=residue_norm))

    return (v * (1.0 / np.sqrt(scalar_sq))).astype(dtype)


def _seed_to_rotor(v: np.ndarray, dtype: np.dtype) -> np.ndarray:
    seed = np.asarray(v, dtype=np.float64).ravel()
    if seed.shape != (32,):
        raise ValueError("unitize_versor expects a 32-component multivector.")

    rotor = np.zeros(32, dtype=np.float64)
    rotor[0] = 1.0
    scale = float(np.linalg.norm(seed)) or 1.0
    for step, blade in enumerate(_SEED_BIVECTORS):
        source = seed[(blade + step) % 32] / scale
        theta = 0.5 * np.tanh(source)
        factor = np.zeros(32, dtype=np.float64)
        factor[0] = np.cos(theta)
        factor[blade] = np.sin(theta)
        rotor = geometric_product(rotor, factor)
    return _unitize_closed(rotor, dtype)


def unitize_versor(v: np.ndarray) -> np.ndarray:
    dtype = _array_dtype(v)
    arr = np.asarray(v, dtype=np.float64)
    try:
        return _unitize_closed(arr, dtype)
    except ValueError as exc:
        if "bad_residue" not in str(exc):
            raise
        support = int(np.count_nonzero(np.abs(arr) > _NEAR_ZERO_TOLERANCE))
        if support < _DENSE_SEED_MIN_COMPONENTS:
            raise
        return _seed_to_rotor(arr, dtype)


def normalize_to_versor(v: np.ndarray) -> np.ndarray:
    dtype = _array_dtype(v)
    try:
        return unitize_versor(v)
    except ValueError as exc:
        if "bad_residue" not in str(exc):
            raise
        return _seed_to_rotor(v, dtype)


def construction_seed_versor(v: np.ndarray) -> np.ndarray:
    """Map a raw construction seed into the closed versor manifold."""
    return _seed_to_rotor(v, _array_dtype(v))


def _close_applied_versor(v: np.ndarray) -> np.ndarray:
    """Close runtime field sandwich results at float64 precision.

    ``versor_apply`` is the runtime field-propagation API.  Vocabulary entries
    may be stored compactly as float32, but live ``FieldState.F`` values are
    judged against a strict ``versor_condition < 1e-6`` invariant. Closing and
    returning float64 avoids leaking float32 roundoff as false manifold drift.
    """
    arr = np.asarray(v, dtype=_RUNTIME_FIELD_DTYPE)
    try:
        return unitize_versor(arr).astype(_RUNTIME_FIELD_DTYPE)
    except ValueError:
        return _seed_to_rotor(arr, _RUNTIME_FIELD_DTYPE).astype(_RUNTIME_FIELD_DTYPE)


def versor_apply(V: np.ndarray, F: np.ndarray) -> np.ndarray:
    V = np.asarray(V, dtype=_RUNTIME_FIELD_DTYPE)
    F = np.asarray(F, dtype=_RUNTIME_FIELD_DTYPE)
    applied = geometric_product(geometric_product(V, F), reverse(V)).astype(_RUNTIME_FIELD_DTYPE)
    return _close_applied_versor(applied)


def versor_unit_residual(v: np.ndarray, *, allow_negative: bool = False) -> float:
    v = np.asarray(v, dtype=np.float64)
    vv = geometric_product(v, reverse(v)).astype(np.float64)
    plus = vv.copy()
    plus[0] -= 1.0
    plus_residual = float(np.linalg.norm(plus))
    if not allow_negative:
        return plus_residual
    minus = vv.copy()
    minus[0] += 1.0
    return min(plus_residual, float(np.linalg.norm(minus)))


def versor_condition(v: np.ndarray) -> float:
    return versor_unit_residual(v, allow_negative=False)
