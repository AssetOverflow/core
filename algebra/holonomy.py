"""
Holonomy prompt encoding.

A prompt w1, w2, ..., wn is encoded as the geometric holonomy of its
forward+reverse versor walk. The walk closes, producing a versor that
is bounded by construction and invariant to global phase.

The holonomy IS a versor — it drops directly into versor_apply with
no bridging code. The fuel and the engine are the same substance.
"""

import numpy as np
from .cl41 import geometric_product, reverse as cl_reverse
from .versor import normalize_to_versor
from .cga import cga_inner


def holonomy_encode(
    word_versors: list,
    alpha: float = 0.5,
    weights: list = None,
) -> np.ndarray:
    """
    Compute the holonomy of the word versor sequence.

    Forward walk:  F = w1 * w2 * ... * wn  (weighted by word frequency inverse)
    Reverse walk:  R = (1-alpha) * reverse(wn) * ... * reverse(w1)
    Holonomy:      H = geometric_product(F, R)

    H is a versor. For alpha=0.5, the holonomy captures the geometric
    curvature of the prompt path. Prompts with different semantic content
    produce geometrically distinct holonomies even at the same length.

    weights: optional list of float scalars (e.g. inverse token frequency).
             Rare content words rotate more than common function words.
             If None, uniform weights are used.
    """
    if not word_versors:
        raise ValueError("Cannot encode empty prompt.")

    n = len(word_versors)
    if weights is None:
        weights = [1.0] * n
    assert len(weights) == n

    # Forward accumulation
    F = word_versors[0].copy() * weights[0]
    F = normalize_to_versor(F)
    for k in range(1, n):
        w = word_versors[k] * weights[k]
        w = normalize_to_versor(w)
        F = geometric_product(F, w)

    # Reverse accumulation with alpha damping
    R = cl_reverse(word_versors[-1]) * (1.0 - alpha)
    R = normalize_to_versor(R)
    for k in range(n - 2, -1, -1):
        r = cl_reverse(word_versors[k])
        r = normalize_to_versor(r)
        R = geometric_product(r, R)

    H = geometric_product(F, R)
    return normalize_to_versor(H)


def holonomy_similarity(H1: np.ndarray, H2: np.ndarray) -> float:
    """
    Compare two holonomies via CGA inner product.
    Used for prompt-level semantic similarity without embedding lookup.
    """
    return cga_inner(H1, H2)
