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


def _array_dtype(v: np.ndarray) -> np.dtype:
    arr = np.asarray(v)
    return arr.dtype if arr.dtype in (np.dtype(np.float32), np.dtype(np.float64)) else np.dtype(np.float32)


def _diagnostic_message(prefix: str, *, input_norm: float, scalar_sq: float, residue_norm: float) -> str:
    return f"{prefix}: input_norm={input_norm:.6e}, scalar_sq={scalar_sq:.6e}, residue_norm={residue_norm:.6e}"


def unitize_versor(v: np.ndarray) -> np.ndarray:
    dtype = _array_dtype(v)
    v = np.asarray(v, dtype=dtype)
    input_norm = float(np.linalg.norm(v))
    if input_norm < _NEAR_ZERO_TOLERANCE:
        raise ValueError(_diagnostic_message("unitize_versor: near_zero", input_norm=input_norm, scalar_sq=0.0, residue_norm=0.0))

    vv = geometric_product(v, reverse(v)).astype(dtype)
    scalar_sq = float(vv[0])
    residue = vv.copy()
    residue[0] = 0
    residue_norm = float(np.linalg.norm(residue))

    if residue_norm >= _CONSTRUCTION_RESIDUE_TOLERANCE:
        raise ValueError(_diagnostic_message("unitize_versor: bad_residue", input_norm=input_norm, scalar_sq=scalar_sq, residue_norm=residue_norm))

    if scalar_sq <= 0.0:
        raise ValueError(_diagnostic_message("unitize_versor: bad_scalar", input_norm=input_norm, scalar_sq=scalar_sq, residue_norm=residue_norm))

    return (v * (1.0 / np.sqrt(scalar_sq))).astype(dtype)


def normalize_to_versor(v: np.ndarray) -> np.ndarray:
    return unitize_versor(v)


def versor_apply(V: np.ndarray, F: np.ndarray) -> np.ndarray:
    dtype = np.result_type(V, F)
    if dtype not in (np.dtype(np.float32), np.dtype(np.float64)):
        dtype = np.dtype(np.float32)
    V = np.asarray(V, dtype=dtype)
    F = np.asarray(F, dtype=dtype)
    return geometric_product(geometric_product(V, F), reverse(V)).astype(dtype)


def versor_unit_residual(v: np.ndarray, *, allow_negative: bool = False) -> float:
    dtype = _array_dtype(v)
    v = np.asarray(v, dtype=dtype)
    vv = geometric_product(v, reverse(v)).astype(dtype)
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
