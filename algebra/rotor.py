"""
algebra/rotor.py — Rotor construction operators for Cl(4,1).

Rotors are operators. They live here, in algebra/, not in vocab/.
A rotor between two word-versors is a contextual, field-level concern:
it describes a transformation being applied, not a property of the vocabulary.
"""

import numpy as np
from .cl41 import geometric_product, reverse
from .versor import normalize_to_versor


def word_transition_rotor(A: np.ndarray, B: np.ndarray) -> np.ndarray:
    """
    Compute the rotor R that rotates versor A toward versor B in Cl(4,1).

        R = normalize(1 + B * reverse(A))

    This is a pure operator — it transforms a field state, it does not
    encode a position. Call this from algebra-aware field logic; never
    store the result on a vocabulary structure.

    Args:
        A: Source versor, shape (32,), grade-normed to ±1.
        B: Target versor, shape (32,), grade-normed to ±1.

    Returns:
        R: Normalized rotor in Cl(4,1), shape (32,).
    """
    R = geometric_product(B, reverse(A))
    R = R.copy()
    R[0] += 1.0
    return normalize_to_versor(R)
