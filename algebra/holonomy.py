"""
Holonomy prompt encoding.

A prompt w1, w2, ..., wn is encoded as the geometric holonomy of its
forward+reverse versor walk. The walk closes, producing a bounded algebraic
summary of the prompt path.

The input word objects must already be valid construction-time versors.
Holonomy may unitize intermediate construction products to prevent float32
scale blow-up, but never repairs propagation state.
"""

from __future__ import annotations

import numpy as np

from .cl41 import geometric_product, reverse as cl_reverse
from .versor import construction_seed_versor, unitize_versor
from .cga import cga_inner


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


def _word_versor(raw: np.ndarray) -> np.ndarray:
    try:
        return unitize_versor(raw)
    except ValueError as exc:
        if "bad_residue" not in str(exc) and "bad_scalar" not in str(exc):
            raise
        return construction_seed_versor(raw)


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

    Construction-time unitization is used at the boundary and at the final
    product. A bounded Euclidean renormalization is also applied every
    `renorm_every` steps to prevent long prompt overflow in float32.
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

    dtype = np.float64

    # Forward accumulation. Each token is carried through a deterministic
    # position rotor so path order survives even for scalar/vector fixtures.
    p0 = _position_rotor(0, dtype)
    w0 = _word_versor(np.asarray(word_versors[0], dtype=dtype) * weights[0])
    F = unitize_versor(geometric_product(geometric_product(p0, w0), cl_reverse(p0)))
    for k in range(1, n):
        p = _position_rotor(k, dtype)
        w = _word_versor(np.asarray(word_versors[k], dtype=dtype) * weights[k])
        step = unitize_versor(geometric_product(geometric_product(p, w), cl_reverse(p)))
        F = geometric_product(F, step)
        F = _renorm_if_needed(F, k, renorm_every)

    return _word_versor(F)


def holonomy_similarity(H1: np.ndarray, H2: np.ndarray) -> float:
    """
    Compare two holonomies via CGA inner product.
    Used for prompt-level semantic similarity without embedding lookup.
    """
    return cga_inner(unitize_versor(H1), unitize_versor(H2))
