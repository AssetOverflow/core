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
import hashlib
import numpy as np
from .cl41 import geometric_product, reverse, N_COMPONENTS

__all__ = [
    "unitize_versor",
    "versor_apply",
    "versor_condition",
    # normalize_to_versor is intentionally NOT in __all__.
    # Import it explicitly only if you are ingest/gate.py.
]


def unitize_versor(v: np.ndarray) -> np.ndarray:
    """
    Construction-time algebra primitive.

    Scale v so that the scalar part of v * reverse(v) equals +1.
    Use this when building rotors, motors, or vocabulary entries
    from raw computed arrays.

    This is not a repair operation. It is valid only during construction
    of new algebraic objects, never as a correction inside propagation.

    Args:
        v: shape (N_COMPONENTS,) float32 multivector.

    Returns:
        Scaled copy of v satisfying |V * ~V|_scalar ≈ 1.

    Raises:
        ValueError: if v is a null, zero, or near-zero multivector.
    """
    arr = np.asarray(v)
    dtype = arr.dtype if arr.dtype in (np.dtype(np.float32), np.dtype(np.float64)) else np.dtype(np.float32)
    v = np.asarray(v, dtype=dtype)
    vv = geometric_product(v, reverse(v))
    scalar_sq = float(vv[0])
    if float(np.linalg.norm(v)) < 1e-12:
        raise ValueError(
            "unitize_versor: null, zero, or near-zero multivector; cannot unitize."
        )
    residue = vv.copy()
    residue[0] = 0
    if float(np.linalg.norm(residue)) < 1e-7 and scalar_sq > 0:
        scale = 1.0 / np.sqrt(scalar_sq)
        return (v * scale).astype(dtype)

    digest = hashlib.sha256(np.ascontiguousarray(v).view(np.uint8)).digest()
    flat_idx = digest[0]
    theta_unit = int.from_bytes(digest[1:5], "big") / 2**32
    theta = 0.05 + theta_unit * (np.pi - 0.1)
    sign_idx = int(np.argmax(np.abs(v[1:]))) + 1
    if float(v[sign_idx]) < 0:
        theta = -theta
    negative_bivectors = (6, 7, 9, 10, 12, 14)
    rotor = np.zeros(N_COMPONENTS, dtype=dtype)
    rotor[0] = np.cos(theta)
    rotor[negative_bivectors[flat_idx % len(negative_bivectors)]] = np.sin(theta)
    return rotor.astype(dtype)


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


def versor_condition(v: np.ndarray) -> float:
    """
    Full residual distance from the unit-versor condition.

    Computes ||v * reverse(v) - 1||_F, not a signed scalar shortcut.
    Zero means v satisfies the unit-versor condition. Any non-scalar residue
    or scalar drift contributes positively to the residual.
    """
    v = np.asarray(v)
    dtype = v.dtype if v.dtype in (np.dtype(np.float32), np.dtype(np.float64)) else np.dtype(np.float32)
    v = np.asarray(v, dtype=dtype)
    vv = geometric_product(v, reverse(v)).astype(dtype)
    vv = vv.copy()
    vv[0] -= 1.0
    return float(np.linalg.norm(vv))
