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
_NEAR_ZERO_TOL = 1e-12
_SAME_POINT_TOL = 1e-6
_STRICT_RESIDUE_TOL = 1e-2


def _identity(dtype: np.dtype) -> np.ndarray:
    rotor = np.zeros(N_COMPONENTS, dtype=dtype)
    rotor[0] = 1.0
    return rotor


def _result_dtype(*arrays: np.ndarray) -> np.dtype:
    dtype = np.result_type(*arrays)
    return dtype if dtype in (np.dtype(np.float32), np.dtype(np.float64)) else np.dtype(np.float32)


def _strict_unitize_versor(v: np.ndarray, dtype: np.dtype) -> np.ndarray:
    """Unitize only already-closed versor candidates.

    ``unitize_versor`` intentionally supports dense construction seeds for
    ingest/compiler boundaries. Transition construction is not such a boundary:
    if the product candidate is not already a closed versor, fabricating a
    deterministic fallback rotor would sever the transition from its source and
    target. This helper therefore fails closed instead of using construction
    seed fallback semantics.
    """
    arr = np.asarray(v, dtype=np.float64)
    input_norm = float(np.linalg.norm(arr))
    if input_norm < _NEAR_ZERO_TOL:
        raise ValueError("word_transition_rotor: near_zero candidate")

    product = geometric_product(arr, reverse(arr)).astype(np.float64)
    scalar_sq = float(product[0])
    residue = product.copy()
    residue[0] = 0.0
    residue_norm = float(np.linalg.norm(residue))
    if residue_norm >= _STRICT_RESIDUE_TOL:
        raise ValueError(
            "word_transition_rotor: non_closed candidate; "
            f"residue_norm={residue_norm:.6e}"
        )
    if scalar_sq <= 0.0:
        raise ValueError(
            "word_transition_rotor: non_positive candidate; "
            f"scalar_sq={scalar_sq:.6e}"
        )
    return (arr * (1.0 / np.sqrt(scalar_sq))).astype(dtype)


def make_rotor_from_angle(angle: float, bivector_idx: int = 6) -> np.ndarray:
    """Construct a scalar+bivector unit rotor from an angle."""
    if not 0 <= int(bivector_idx) < N_COMPONENTS:
        raise ValueError(f"bivector_idx out of range: {bivector_idx!r}")
    rotor = np.zeros(N_COMPONENTS, dtype=np.float64)
    half_angle = float(angle) / 2.0
    rotor[0] = np.cos(half_angle)
    rotor[int(bivector_idx)] = np.sin(half_angle)
    return unitize_versor(rotor)


def rotor_power(R: np.ndarray, alpha: float) -> np.ndarray:
    """Return R^alpha — the rotor on the manifold path from identity to R by alpha.

    For a simple unit rotor decomposed as ``R = a + B`` (scalar + bivector):

    - rotation plane (``B² < 0``):  ``R^α = cos(α·θ/2) + (sin(α·θ/2)/|B|) · B``
      where ``θ/2 = atan2(|B|, a)``.
    - boost plane (``B² > 0``):     ``R^α = cosh(α·η/2) + (sinh(α·η/2)/|B|) · B``
      where ``η/2 = atanh(|B|/a)``.

    This is the proper slerp on the rotor manifold: it stays on the manifold
    by construction, so ``versor_condition(rotor_power(R, α)) < 1e-6`` for any
    α whenever ``R`` is itself a closed unit rotor.

    Falls back to the identity rotor when ``R`` is not a closed scalar+bivector
    rotor (e.g. carries higher-grade components or a non-simple bivector) so
    callers never receive a manifold-violating output.
    """
    R_arr = np.asarray(R, dtype=np.float64)
    if R_arr.shape != (N_COMPONENTS,):
        raise ValueError(
            f"rotor_power expects a {N_COMPONENTS}-component rotor; got {R_arr.shape}."
        )

    dtype = _result_dtype(R_arr)
    a = float(R_arr[0])
    B = R_arr.copy()
    B[0] = 0.0

    # Quick guard: bivector must be a simple bivector (B² is grade-0 only).
    B_sq_full = geometric_product(B, B).astype(np.float64)
    bsq_scalar = float(B_sq_full[0])
    B_sq_higher = B_sq_full.copy()
    B_sq_higher[0] = 0.0
    if float(np.linalg.norm(B_sq_higher)) > 1e-6:
        # Non-simple bivector — return identity to avoid drift.
        return _identity(dtype)

    # Near-identity: nothing to scale.
    bivector_norm = float(np.linalg.norm(B))
    if bivector_norm < _NEAR_ZERO_TOL:
        return _identity(dtype)

    if bsq_scalar < 0.0:
        # Rotation plane. B² = -|B|² under signature, so the effective
        # magnitude is the Euclidean norm of the bivector coefficients.
        b_mag = float(np.sqrt(-bsq_scalar))
        theta_half = float(np.arctan2(b_mag, a))
        new_a = float(np.cos(alpha * theta_half))
        new_b_mag = float(np.sin(alpha * theta_half))
    elif bsq_scalar > 0.0:
        # Boost plane.
        b_mag = float(np.sqrt(bsq_scalar))
        # atanh requires |b_mag/a| < 1; for closed rotors a² - B² = 1 means
        # |b_mag| < |a|, so this is safe when a > 0.
        if a == 0.0:
            return _identity(dtype)
        eta_half = float(np.arctanh(b_mag / a))
        new_a = float(np.cosh(alpha * eta_half))
        new_b_mag = float(np.sinh(alpha * eta_half))
    else:
        # B² = 0: null bivector. Cannot interpolate on the manifold;
        # return identity to fail safely.
        return _identity(dtype)

    result = np.zeros(N_COMPONENTS, dtype=np.float64)
    result[0] = new_a
    if b_mag > _NEAR_ZERO_TOL:
        result += (new_b_mag / b_mag) * B
    return result.astype(dtype, copy=False)


def word_transition_rotor(A: np.ndarray, B: np.ndarray) -> np.ndarray:
    """
    Compute the closed transition operator from source versor A to target B.

        R = B * reverse(A)

    Vocabulary coordinates are expected to already be grade-normalized versors.
    The transition between two such states is their closed product. This path
    must never synthesize an unrelated fallback rotor from target components;
    invalid inputs fail loudly so generation can preserve its field invariant.
    """
    dtype = _result_dtype(A, B)
    source = np.asarray(A, dtype=dtype)
    target = np.asarray(B, dtype=dtype)
    if source.shape != (N_COMPONENTS,) or target.shape != (N_COMPONENTS,):
        raise ValueError(
            "word_transition_rotor expects two 32-component multivectors; "
            f"got {source.shape} and {target.shape}."
        )
    if float(np.linalg.norm(source)) < _NEAR_ZERO_TOL or float(np.linalg.norm(target)) < _NEAR_ZERO_TOL:
        raise ValueError("word_transition_rotor: near_zero input")
    if float(np.linalg.norm(target - source)) < _SAME_POINT_TOL:
        return _identity(dtype)

    candidate = geometric_product(target, reverse(source)).astype(dtype)
    rotor = _strict_unitize_versor(candidate, dtype)
    condition = versor_condition(rotor)
    if condition > _TRANSITION_CONDITION_TOL:
        raise ValueError(
            "word_transition_rotor: transition rotor is not a unit versor; "
            f"condition={condition:.3e}"
        )
    return rotor.astype(dtype, copy=False)
