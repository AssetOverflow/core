"""
algebra/rotor.py — Rotor construction operators for Cl(4,1).

Rotors are operators. They live here, in algebra/, not in vocab/.
A rotor between two word-versors is a contextual, field-level concern:
it describes a transformation being applied, not a property of the vocabulary.
"""

import numpy as np

from .cl41 import N_COMPONENTS, geometric_product, reverse
from .versor import unitize_versor, versor_condition

_TRANSITION_CONDITION_TOL = 1e-4
_SAME_POINT_TOL = 1e-6


def _identity(dtype: np.dtype) -> np.ndarray:
    rotor = np.zeros(N_COMPONENTS, dtype=dtype)
    rotor[0] = 1.0
    return rotor


def word_transition_rotor(A: np.ndarray, B: np.ndarray) -> np.ndarray:
    """
    Construct a transition rotor from source word-versor A to target B.

        R = unitize(1 + B * reverse(A))

    Degenerate same-point transitions are handled explicitly as identity
    before unitization. Non-scalar or non-positive candidates fail loudly via
    unitize_versor(); no deterministic fallback rotor is fabricated.
    """
    dtype = np.result_type(A, B)
    if dtype not in (np.dtype(np.float32), np.dtype(np.float64)):
        dtype = np.dtype(np.float32)
    source = np.asarray(A, dtype=dtype)
    target = np.asarray(B, dtype=dtype)

    if float(np.linalg.norm(target - source)) < _SAME_POINT_TOL:
        return _identity(dtype)

    candidate = geometric_product(target, reverse(source)).astype(dtype)
    candidate = candidate.copy()
    candidate[0] += 1.0
    rotor = unitize_versor(candidate)

    condition = versor_condition(rotor)
    if condition > _TRANSITION_CONDITION_TOL:
        raise ValueError(
            "word_transition_rotor: transition rotor is not a unit versor; "
            f"condition={condition:.3e}. Check vocabulary versor invariants."
        )
    return rotor.astype(dtype)
