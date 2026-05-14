"""
algebra/versor.py — Versor operations for Cl(4,1).

Normalization doctrine:

  unitize_versor(v)      — CONSTRUCTION primitive.
                           Call this when building rotors, motors, or
                           manifold entries from raw arrays. It is the
                           algebra layer's legitimate construction operation.
                           May be called in: algebra/, persona/, vocab/ (pre-add).

  normalize_to_versor(v) — GATE primitive. Internal to ingest/gate.py.
                           Normalizes raw holonomy output to a versor at
                           the injection boundary. Do not call this anywhere
                           else in production code. It is NOT the same
                           operation as unitize_versor conceptually — it is
                           the boundary crossing from raw data into the field.

  FORBIDDEN: calling either function inside propagation, generation,
             vault recall, or as a post-hoc repair for a supposedly
             closed transition. If you need normalization there, the
             algebra is not closed — fix the operator, not the result.
"""

from __future__ import annotations

import numpy as np
from .cl41 import geometric_product, reverse

__all__ = [
    "unitize_versor",
    "versor_apply",
    "versor_condition",
    "versor_unit_residual",
    # normalize_to_versor is intentionally NOT in __all__.
    # Import it explicitly only if you are ingest/gate.py.
]

_CONSTRUCTION_RESIDUE_TOLERANCE = 1e-7
_NEAR_ZERO_TOLERANCE = 1e-12


def _array_dtype(v: np.ndarray) -> np.dtype:
    arr = np.asarray(v)
    return (
        arr.dtype
        if arr.dtype in (np.dtype(np.float32), np.dtype(np.float64))
        else np.dtype(np.float32)
    )


def _diagnostic_message(
    prefix: str,
    *,
    input_norm: float,
    scalar_sq: float,
    residue_norm: float,
) -> str:
    return (
        f"{prefix}: input_norm={input_norm:.6e}, "
        f"scalar_sq={scalar_sq:.6e}, residue_norm={residue_norm:.6e}"
    )


def unitize_versor(v: np.ndarray) -> np.ndarray:
    """
    Construction-time algebra primitive.

    Scale v so that v * reverse(v) is scalar +1. Use this only when
    building rotors, motors, or vocabulary entries from already-clean
    algebraic construction formulas.

    This is not a repair operation. If v * reverse(v) has non-scalar
    residue, construction is ill-formed and fails closed with diagnostics.
    It must never synthesize a replacement rotor unrelated to the input.

    Args:
        v: shape (N_COMPONENTS,) float32/float64 multivector.

    Returns:
        Scaled copy of v satisfying V * reverse(V) ≈ +1.

    Raises:
        ValueError: if v is near-zero, has non-positive scalar norm, or
            carries non-scalar residue in v * reverse(v).
    """
    dtype = _array_dtype(v)
    v = np.asarray(v, dtype=dtype)
    input_norm = float(np.linalg.norm(v))
    if input_norm < _NEAR_ZERO_TOLERANCE:
        raise ValueError(
            _diagnostic_message(
                "unitize_versor: null, zero, or near-zero multivector; cannot unitize",
                input_norm=input_norm,
                scalar_sq=0.0,
                residue_norm=0.0,
            )
        )

    vv = geometric_product(v, reverse(v)).astype(dtype)
    scalar_sq = float(vv[0])
    residue = vv.copy()
    residue[0] = 0
    residue_norm = float(np.linalg.norm(residue))

    if residue_norm >= _CONSTRUCTION_RESIDUE_TOLERANCE:
        raise ValueError(
            _diagnostic_message(
                "unitize_versor: non-scalar construction residue; operator is not a clean versor candidate",
                input_norm=input_norm,
                scalar_sq=scalar_sq,
                residue_norm=residue_norm,
            )
        )

    if scalar_sq <= 0.0:
        raise ValueError(
            _diagnostic_message(
                "unitize_versor: non-positive scalar norm; cannot scale to +1 over real Cl(4,1)",
                input_norm=input_norm,
                scalar_sq=scalar_sq,
                residue_norm=residue_norm,
            )
        )

    scale = 1.0 / np.sqrt(scalar_sq)
    return (v * scale).astype(dtype)


def normalize_to_versor(v: np.ndarray) -> np.ndarray:
    """
    Gate-only injection primitive. Reserved for ingest/gate.py.

    Do not call this function outside the injection gate.
    For construction of algebraic objects, use unitize_versor() instead.
    """
    # Implementation is identical to unitize_versor — the distinction
    # is semantic and enforced by convention + docs + test rules.
    return unitize_versor(v)


def versor_apply(V: np.ndarray, F: np.ndarray) -> np.ndarray:
    """
    Apply versor V to field state F via the sandwich product.

        F' = V * F * reverse(V)

    This is the ONLY way field state changes in production code.
    No normalization is applied here. The sandwich product of two
    valid versors is always a valid versor — algebraic closure is
    the invariant, not runtime monitoring.

    Args:
        V: versor operator, shape (N_COMPONENTS,).
        F: field state, shape (N_COMPONENTS,).

    Returns:
        F': transformed field state, shape (N_COMPONENTS,).
    """
    dtype = np.result_type(V, F)
    if dtype not in (np.dtype(np.float32), np.dtype(np.float64)):
        dtype = np.dtype(np.float32)
    V = np.asarray(V, dtype=dtype)
    F = np.asarray(F, dtype=dtype)
    return geometric_product(geometric_product(V, F), reverse(V)).astype(dtype)


def versor_unit_residual(v: np.ndarray, *, allow_negative: bool = False) -> float:
    """
    Full residual from the unit-versor condition.

    Field states use the stricter +1 convention. Manifold entries may opt
    into ±1 by passing allow_negative=True, matching the mathematical versor
    condition while still rejecting non-scalar residue.
    """
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
    minus_residual = float(np.linalg.norm(minus))
    return min(plus_residual, minus_residual)


def versor_condition(v: np.ndarray) -> float:
    """
    Full residual distance from the positive unit-versor condition.

    Computes ||v * reverse(v) - 1||_F, not a signed scalar shortcut.
    Zero means v satisfies the +1 field-state condition. Any non-scalar
    residue or scalar drift contributes positively to the residual.
    """
    return versor_unit_residual(v, allow_negative=False)
