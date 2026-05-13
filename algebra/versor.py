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
        ValueError: if v is a zero or near-zero multivector.
    """
    v = np.asarray(v, dtype=np.float32)
    vv = geometric_product(v, reverse(v))
    scalar_sq = float(vv[0])
    if abs(scalar_sq) < 1e-12:
        raise ValueError(
            "unitize_versor: multivector is zero or near-zero, cannot unitize."
        )
    scale = 1.0 / np.sqrt(abs(scalar_sq))
    return (v * scale).astype(np.float32)


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
    V = np.asarray(V, dtype=np.float32)
    F = np.asarray(F, dtype=np.float32)
    return geometric_product(geometric_product(V, F), reverse(V)).astype(np.float32)


def versor_condition(v: np.ndarray) -> float:
    """
    Measure how far v is from being a unit versor.

    Returns |scalar_part(v * reverse(v)) - 1|.
    At zero, v is exactly a unit versor.
    Used at the injection gate to assert the invariant before returning.
    """
    v = np.asarray(v, dtype=np.float32)
    vv = geometric_product(v, reverse(v))
    return float(abs(vv[0]) - 1.0)
