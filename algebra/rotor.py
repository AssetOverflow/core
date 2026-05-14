"""
algebra/rotor.py — Rotor construction operators for Cl(4,1).

Rotors are operators. They live here, in algebra/, not in vocab/.
A rotor between two word-versors is a contextual, field-level concern:
it describes a transformation being applied, not a property of the vocabulary.
"""

import numpy as np
from .cl41 import geometric_product, reverse
from .versor import versor_condition

_TRANSITION_CONDITION_TOL = 1e-4


def word_transition_rotor(A: np.ndarray, B: np.ndarray) -> np.ndarray:
    """
    Construct the closed transition operator from source word-versor A to B.

        R = B * reverse(A)

    VocabManifold stores grade-normed Cl(4,1) versors, not arbitrary raw
    vectors. The product of two valid versors is itself a valid versor, so the
    direct product is the closed transition operator. This avoids the unstable
    half-angle shortcut `unitize(1 + B * reverse(A))`, which can collapse into
    a deterministic fallback rotor when the candidate has non-scalar residue.

    This is construction-time algebra, not propagation repair. No
    normalization is applied here. If the returned operator fails the versor
    condition, one of the inputs is not a valid vocabulary versor and the
    caller should fail fast.
    """
    dtype = np.result_type(A, B)
    if dtype not in (np.dtype(np.float32), np.dtype(np.float64)):
        dtype = np.dtype(np.float32)
    source = np.asarray(A, dtype=dtype)
    target = np.asarray(B, dtype=dtype)
    rotor = geometric_product(target, reverse(source)).astype(dtype)
    condition = versor_condition(rotor)
    if condition > _TRANSITION_CONDITION_TOL:
        raise ValueError(
            "word_transition_rotor: transition operator is not a unit versor; "
            f"condition={condition:.3e}. Check vocabulary versor invariants."
        )
    return rotor
