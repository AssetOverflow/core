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
from .versor import unitize_versor
from .cga import cga_inner


def _renorm_if_needed(H: np.ndarray, step: int, renorm_every: int) -> np.ndarray:
    """Bound accumulator scale to prevent float32 overflow on long prompts."""
    if renorm_every <= 0 or step % renorm_every != 0:
        return H
    norm = float(np.linalg.norm(H))
    if not np.isfinite(norm) or norm < 1e-12:
        raise ValueError("holonomy accumulator became null/non-finite during encoding.")
    return (H / norm).astype(np.float32)


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

    # Forward accumulation.
    F = unitize_versor(np.asarray(word_versors[0], dtype=np.float32) * weights[0])
    for k in range(1, n):
        w = unitize_versor(np.asarray(word_versors[k], dtype=np.float32) * weights[k])
        F = geometric_product(F, w)
        F = _renorm_if_needed(F, k, renorm_every)

    # Reverse accumulation with alpha damping.
    R = unitize_versor(cl_reverse(word_versors[-1]) * (1.0 - alpha))
    for k in range(n - 2, -1, -1):
        r = unitize_versor(cl_reverse(word_versors[k]))
        R = geometric_product(r, R)
        R = _renorm_if_needed(R, n - 1 - k, renorm_every)

    H = geometric_product(F, R)
    return unitize_versor(H)


def holonomy_similarity(H1: np.ndarray, H2: np.ndarray) -> float:
    """
    Compare two holonomies via CGA inner product.
    Used for prompt-level semantic similarity without embedding lookup.
    """
    return cga_inner(unitize_versor(H1), unitize_versor(H2))
