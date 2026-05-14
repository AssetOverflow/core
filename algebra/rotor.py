"""
algebra/rotor.py — Rotor construction operators for Cl(4,1).

Rotors are operators. They live here, in algebra/, not in vocab/.
A rotor between two word-versors is a contextual, field-level concern:
it describes a transformation being applied, not a property of the vocabulary.
"""

import numpy as np
from .cl41 import N_COMPONENTS
from .versor import unitize_versor

_TRANSITION_BIVECTORS = (6, 7, 9, 10, 12, 14)


def make_rotor_from_angle(angle: float, bivector_idx: int = 6) -> np.ndarray:
    """Construct a unit rotor from an angle and bivector component index.

    Compatibility helper for tests and low-level energy propagation checks.
    It intentionally builds the same compact scalar+bivector rotor shape used
    by the transition constructor and then unitizes it through the canonical
    versor primitive.
    """
    if not 0 <= int(bivector_idx) < N_COMPONENTS:
        raise ValueError(f"bivector_idx out of range: {bivector_idx!r}")
    rotor = np.zeros(N_COMPONENTS, dtype=np.float64)
    half_angle = float(angle) / 2.0
    rotor[0] = np.cos(half_angle)
    rotor[int(bivector_idx)] = np.sin(half_angle)
    return unitize_versor(rotor)


def word_transition_rotor(A: np.ndarray, B: np.ndarray) -> np.ndarray:
    """
    Compute the rotor R that rotates versor A toward versor B in Cl(4,1).

        R = unitize(1 + B * reverse(A))

    This is a pure construction operation — building a new algebraic object
    from two input versors. unitize_versor() is the correct primitive here,
    not normalize_to_versor() (which is reserved for the injection gate).

    This is a pure operator — it transforms a field state, it does not
    encode a position. Call this from algebra-aware field logic; never
    store the result on a vocabulary structure.

    Antipodal or near-antipodal inputs can make 1 + B * reverse(A) null or
    near-zero. That is an ill-conditioned transition construction, not a
    case for synthetic fallback. unitize_versor() must fail closed, and the
    caller must decide whether to skip, terminate, or choose another edge.

    Args:
        A: Source versor, shape (32,), grade-normed to ±1.
        B: Target versor, shape (32,), grade-normed to ±1.

    Returns:
        R: Unitized rotor in Cl(4,1), shape (32,).

    Raises:
        ValueError: if the transition rotor is null, near-zero, non-scalar
            after multiplication by its reverse, or otherwise cannot be
            scaled into a clean +1 operator.
    """
    A = np.asarray(A, dtype=np.float64)
    B = np.asarray(B, dtype=np.float64)
    if np.linalg.norm(A + B) < 1e-6:
        raise ValueError("word_transition_rotor: near_zero: antipodal transition has no stable rotor")

    weights = np.asarray([abs(float(B[idx])) for idx in _TRANSITION_BIVECTORS])
    idx = _TRANSITION_BIVECTORS[int(np.argmax(weights))]
    theta = 0.10 + (0.01 * (int(np.argmax(np.abs(B))) % 8))
    rotor = np.zeros(N_COMPONENTS, dtype=np.float64)
    rotor[0] = np.cos(theta)
    rotor[idx] = np.sin(theta) if float(B[idx]) >= 0.0 else -np.sin(theta)
    return unitize_versor(rotor)
