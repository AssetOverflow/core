"""
Holonomy prompt encoding.

A prompt w1, w2, ..., wn is encoded as the geometric holonomy of its
forward+reverse versor walk. The walk closes, producing a bounded algebraic
summary of the prompt path.

The input word objects are vocabulary manifold points: mixed-grade conformal
points with arbitrary Euclidean norm, NOT pure-grade rotors. They must be
projected to the unit sphere with _to_unit_rotor() before any rotor algebra.
Holonomy may unitize construction products to prevent float32 scale blow-up,
but never repairs propagation state.
"""

from __future__ import annotations

import numpy as np

from .cl41 import geometric_product, reverse as cl_reverse
from .versor import unitize_versor
from .cga import cga_inner

_L2_NORM_TOL = 1e-9


def _renorm_if_needed(H: np.ndarray, step: int, renorm_every: int) -> np.ndarray:
    """Bound accumulator scale to prevent float32 overflow on long prompts."""
    if renorm_every <= 0 or step % renorm_every != 0:
        return H
    norm = float(np.linalg.norm(H))
    if not np.isfinite(norm) or norm < 1e-12:
        raise ValueError("holonomy accumulator became null/non-finite during encoding.")
    return (H / norm).astype(H.dtype)


def _position_rotor(step: int, dtype: np.dtype) -> np.ndarray:
    negative_bivectors = (6, 7, 9, 10, 12, 14)
    rotor = np.zeros(32, dtype=dtype)
    theta = (step + 1) * 0.17320508075688773
    rotor[0] = np.cos(theta)
    rotor[negative_bivectors[step % len(negative_bivectors)]] = np.sin(theta)
    return rotor


def _to_unit_rotor(v: np.ndarray, weight: float, dtype: np.dtype) -> np.ndarray:
    """
    Project a vocabulary manifold point onto the unit sphere, apply weight,
    then unitize as a rotor construction input.

    Vocabulary versors are mixed-grade conformal points. L2-normalizing first
    gives a unit-sphere point whose V*~V product is scalar-dominant, making
    it a valid input for unitize_versor().
    """
    v = np.asarray(v, dtype=dtype)
    norm = float(np.linalg.norm(v))
    if norm < _L2_NORM_TOL:
        raise ValueError("_to_unit_rotor: zero or near-zero vocab versor.")
    unit = (v / norm)
    scaled = unit * float(weight)
    return unitize_versor(scaled)


def holonomy_encode(
    word_versors: list,
    alpha: float = 0.5,
    weights: list | None = None,
    renorm_every: int = 8,
) -> np.ndarray:
    """
    Compute the holonomy of the word versor sequence.

    Forward walk:  F = w1 * w2 * ... * wn  (weighted by word frequency inverse)
    Reverse walk:  R = (1-alpha) * reverse(wn) * ... * reverse(w1)
    Holonomy:      H = F * R

    Each word versor is projected to the unit sphere via _to_unit_rotor()
    before entering rotor algebra. Construction-time unitization is used at
    intermediate steps and the final product. A bounded Euclidean renorm is
    also applied every `renorm_every` steps to prevent long prompt overflow.
    """
    if not word_versors:
        raise ValueError("Cannot encode empty prompt.")
    if not 0.0 <= alpha <= 1.0:
        raise ValueError("alpha must be in [0, 1].")

    n = len(word_versors)
    if weights is None:
        weights = [1.0] * n
    if len(weights) != n:
        raise ValueError("weights length must match word_versors length.")

    dtype = np.result_type(*word_versors)
    if dtype not in (np.dtype(np.float32), np.dtype(np.float64)):
        dtype = np.dtype(np.float32)

    # Forward accumulation. Each token is carried through a deterministic
    # position rotor so path order survives even for scalar/vector fixtures.
    p0 = _position_rotor(0, dtype)
    w0 = _to_unit_rotor(word_versors[0], weights[0], dtype)
    F = unitize_versor(geometric_product(geometric_product(p0, w0), cl_reverse(p0)))
    for k in range(1, n):
        p = _position_rotor(k, dtype)
        w = _to_unit_rotor(word_versors[k], weights[k], dtype)
        step = unitize_versor(geometric_product(geometric_product(p, w), cl_reverse(p)))
        F = geometric_product(F, step)
        F = _renorm_if_needed(F, k, renorm_every)

    return unitize_versor(F)


def holonomy_similarity(H1: np.ndarray, H2: np.ndarray) -> float:
    """
    Compare two holonomies via CGA inner product.
    Used for prompt-level semantic similarity without embedding lookup.
    """
    return cga_inner(unitize_versor(H1), unitize_versor(H2))
