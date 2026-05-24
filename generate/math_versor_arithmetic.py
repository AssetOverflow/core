"""ADR-0139 — Arithmetic-as-versor spike: `add` only.

Algebraic substrate for representing scalar arithmetic as closed versors
in Cl(4,1). This module proves the **load-bearing unknown** of the
Engine A lift program: that one arithmetic operation can be represented
as a closed unit versor satisfying ``versor_condition < 1e-6`` without
weakening any existing invariant.

Scope (frozen by ADR-0139):

- Single operation: ``add``.
- Single-axis embedding: quantities live on the e1 axis of the CGA
  conformal model.
- No graph wiring (no ``MathProblemGraph`` consumer).
- No pipeline wiring (no ``CognitiveTurnPipeline`` integration).
- No GSM8K case routed.
- Unit is carried as caller metadata; not encoded in the multivector.

If acceptance assertions hold for ``add``, follow-on ADRs cover
``subtract`` (inverse translator), ``multiply`` (dilator), and the lift
to ``MathProblemGraph`` consumers. If they do not, the lift program is
paused.

Determinism: float64 end-to-end. No platform-conditional code. No
randomness.

References:
- ``algebra/cga.py:embed_point`` — conformal point embedding
- ``algebra/cga.py:cga_inner`` — null-cone metric
- ``algebra/versor.py:versor_apply`` — sandwich product (null inputs
  preserved via raw sandwich)
- ``algebra/versor.py:versor_condition`` — ``|V·reverse(V) - 1|``
- ``algebra/cl41.py:geometric_product`` — Cl(4,1) geometric product
"""

from __future__ import annotations

import numpy as np

from algebra.cga import cga_inner
from algebra.cl41 import N_COMPONENTS, geometric_product

__all__ = [
    "embed_quantity",
    "translator",
    "subtract",
    "multiply",
    "decode_quantity",
    "N_INF",
]


# Conformal point at infinity: n_inf = e4 + e5 (per algebra/cga.py
# convention). Constructed as a 32-component grade-1 multivector with
# components at indices 4 (e4) and 5 (e5) both equal to 1.0.
def _n_inf() -> np.ndarray:
    v = np.zeros(N_COMPONENTS, dtype=np.float64)
    v[4] = 1.0
    v[5] = 1.0
    return v


N_INF: np.ndarray = _n_inf()


def embed_quantity(value: float, unit: str) -> np.ndarray:
    """Embed a scalar quantity as a conformal point on the e1 axis.

    The quantity ``value`` becomes a CGA null point at Euclidean
    coordinates ``[value, 0, 0]``. The ``unit`` argument is not
    encoded in the multivector — it is carried as caller metadata and
    enforced by ``decode_quantity`` returning the same unit string.

    Returns a float64 32-component multivector lying on the null cone:
    ``cga_inner(X, X) ≈ 0``.

    Args:
        value: Numeric value of the quantity.
        unit: Unit string (carried metadata; not encoded).

    Returns:
        32-component float64 multivector representing the embedded point.
    """
    if not isinstance(unit, str) or not unit:
        raise ValueError(f"embed_quantity: unit must be a non-empty string, got {unit!r}")
    # Embed directly in float64 to avoid float32 quantization error for
    # values like 0.01 that have no exact float32 representation.
    # Formula: X = v*e1 + n_o + 0.5*v²*n_inf, n_o = 0.5*(e5-e4), n_inf = e4+e5.
    v = float(value)
    v_sq = v * v
    result = np.zeros(N_COMPONENTS, dtype=np.float64)
    result[1] = v                       # e1 component
    result[4] = 0.5 * (v_sq - 1.0)     # e4: n_o contribution -0.5, n_inf contribution +0.5*v²
    result[5] = 0.5 * (v_sq + 1.0)     # e5: n_o contribution +0.5, n_inf contribution +0.5*v²
    return result


def translator(addend: float) -> np.ndarray:
    """Construct the CGA translator versor for additive shift along e1.

    Standard CGA translator construction:

        T_t = 1 - 0.5 * (t · n_inf)

    where ``t = addend * e1`` is the Euclidean translation vector lifted
    to grade-1, and ``n_inf = e4 + e5``. Since ``t`` and ``n_inf`` are
    orthogonal null/non-null vectors, their geometric product is purely
    a bivector and ``(t · n_inf)² = 0``, so the closed-form expression
    is exact (no higher-order terms in the exponential expansion).

    The construction guarantees ``T_t · reverse(T_t) = 1`` exactly in
    exact arithmetic; in float64 the residual measured by
    ``versor_condition`` should be at machine epsilon.

    Args:
        addend: Scalar to add along e1.

    Returns:
        32-component float64 unit versor satisfying
        ``versor_condition(T) < 1e-6``.
    """
    # t = addend * e1 — grade-1 vector with only e1 component
    t = np.zeros(N_COMPONENTS, dtype=np.float64)
    t[1] = float(addend)

    # B = t * n_inf — geometric product (bivector since t ⊥ n_inf)
    bivector = geometric_product(t, N_INF)

    # T = 1 - 0.5 * B
    T = np.zeros(N_COMPONENTS, dtype=np.float64)
    T[0] = 1.0  # scalar part
    T -= 0.5 * bivector
    return T


def subtract(addend: float) -> np.ndarray:
    """Construct the CGA translator versor for subtractive shift along e1.

    Delegates to ``translator(-addend)``. No new algebra.
    """
    return translator(-float(addend))


def multiply(scale: float) -> np.ndarray:
    """Construct the CGA dilator versor for multiplicative scaling along e1.

    Restricted to scale > 0 strictly.  Calls with scale <= 0 raise
    ValueError.  Negative scales (require composition with reflection)
    and multiplication by zero (degenerate) are deferred to follow-on ADRs.

    Construction: D_s = cosh(α/2) + sinh(α/2) * (n_o ∧ n_inf)
    where s = exp(α), α = ln(s).

    Measured in this CGA implementation (blade indices 0-indexed):
      N = n_o ∧ n_inf has a single non-zero component at index 15
      (blade (3,4) = e4∧e5) with value -1.0.
      N² = +1 (pure scalar, verified empirically and analytically).

    Because N² = +1 the exponential exp(α/2 · N) = cosh(α/2) + sinh(α/2)·N
    is exact in float64 — no series truncation error.

    The sandwich D_s · X · ~D_s applied to a null CGA point P(a) yields
    a null point projectively equal to P(a·s) with n_inf normalization
    factor 1/s.  decode_quantity normalizes by n_inf to recover a·s.

    Args:
        scale: Positive real multiplier.  Must satisfy scale > 0.

    Returns:
        32-component float64 unit versor satisfying
        ``versor_condition(D) < 1e-6``.

    Raises:
        ValueError: If scale <= 0.
    """
    scale = float(scale)
    if scale <= 0.0:
        raise ValueError(
            f"multiply: scale must be strictly positive, got {scale!r}. "
            f"Negative scales and zero are deferred to follow-on ADRs."
        )
    alpha = np.log(scale)
    half = alpha / 2.0
    D = np.zeros(N_COMPONENTS, dtype=np.float64)
    D[0] = np.cosh(half)
    # N = n_o ∧ n_inf has component -1 at index 15 (blade (3,4), measured).
    # D_s = cosh(α/2)·1 + sinh(α/2)·N → D[15] = sinh · (-1) = -sinh.
    D[15] = -np.sinh(half)
    return D


def decode_quantity(F: np.ndarray, unit: str) -> tuple[float, str]:
    """Decode a multivector back to a (value, unit) scalar quantity.

    CGA points are projective: D_s * P * ~D_s produces a point
    proportional to P(s·x) with scale factor 1/s.  Normalizing by the
    n_inf inner product recovers the true Euclidean coordinate regardless
    of projective scale.  For translator outputs (n_inf·X = -1) the
    normalization is 1 and the result is identical to the previous
    direct e1 read.

    Args:
        F: 32-component multivector to decode.
        unit: Unit string to attach to the returned scalar.

    Returns:
        Tuple of ``(value, unit)`` where ``value`` is the normalized
        e1 coordinate.
    """
    if not isinstance(unit, str) or not unit:
        raise ValueError(f"decode_quantity: unit must be a non-empty string, got {unit!r}")
    arr = np.asarray(F, dtype=np.float64)
    if arr.shape != (N_COMPONENTS,):
        raise ValueError(f"decode_quantity: expected shape ({N_COMPONENTS},), got {arr.shape}")
    # Normalize e1 by the n_inf inner product.  For normalized conformal
    # points (n_inf·X = -1) this divides by 1; for dilated points with
    # scale s it divides by 1/s, recovering value * s.
    n_inf_inner = float(cga_inner(N_INF, arr))
    if abs(n_inf_inner) < 1e-15:
        raise ValueError("decode_quantity: degenerate point (n_inf inner product is zero)")
    return float(arr[1]) / (-n_inf_inner), unit
