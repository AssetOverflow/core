"""
algebra/rotor.py — Rotor construction operators for Cl(4,1).

Rotors are operators. They live here, in algebra/, not in vocab/.
A rotor between two word-versors is a contextual, field-level concern:
it describes a transformation being applied, not a property of the vocabulary.

Vocabulary manifold points are mixed-grade conformal points, not pure-grade
rotors. Normalize them to the unit sphere with _l2_unit() before any rotor
construction algebra.
"""

import numpy as np

from .cl41 import N_COMPONENTS, geometric_product, reverse
from .versor import unitize_versor, versor_condition

_TRANSITION_CONDITION_TOL = 1e-4
_SAME_POINT_TOL = 1e-6
_L2_NORM_TOL = 1e-9


def _identity(dtype: np.dtype) -> np.ndarray:
    rotor = np.zeros(N_COMPONENTS, dtype=dtype)
    rotor[0] = 1.0
    return rotor


def _l2_unit(v: np.ndarray) -> np.ndarray:
    """
    Project a mixed-grade manifold point onto the unit sphere.

    Vocabulary versors are conformal points with arbitrary Euclidean norm.
    Before using them in rotor construction (where unitize_versor enforces
    the pure-versor invariant V*~V = scalar), they must be normalized to
    unit L2 norm so that the candidate rotor 1 + B*~A has a scalar-dominant
    V*~V product.
    """
    norm = float(np.linalg.norm(v))
    if norm < _L2_NORM_TOL:
        raise ValueError("_l2_unit: zero or near-zero vector cannot be projected to unit sphere.")
    return (v / norm).astype(v.dtype)


def word_transition_rotor(A: np.ndarray, B: np.ndarray) -> np.ndarray:
    """
    Construct a transition rotor from source word-versor A to target B.

        R = unitize(1 + B_unit * reverse(A_unit))

    A and B are L2-normalized to the unit sphere first, since vocabulary
    manifold points are mixed-grade conformal points with arbitrary norm,
    not pure-grade rotors. unitize_versor() requires a rotor candidate
    with scalar-dominant V*~V — that only holds after L2 projection.

    Degenerate same-point transitions are handled explicitly as identity
    before unitization. Non-scalar or non-positive candidates fail loudly via
    unitize_versor(); no deterministic fallback rotor is fabricated.
    """
    dtype = np.result_type(A, B)
    if dtype not in (np.dtype(np.float32), np.dtype(np.float64)):
        dtype = np.dtype(np.float32)
    source = _l2_unit(np.asarray(A, dtype=dtype))
    target = _l2_unit(np.asarray(B, dtype=dtype))

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
