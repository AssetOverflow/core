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

from algebra.cga import embed_point
from algebra.cl41 import N_COMPONENTS, geometric_product

__all__ = [
    "embed_quantity",
    "translator",
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
    point_float32 = embed_point(np.array([value, 0.0, 0.0], dtype=np.float32))
    # Upcast to float64 for the runtime field-state path.
    return point_float32.astype(np.float64)


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


def decode_quantity(F: np.ndarray, unit: str) -> tuple[float, str]:
    """Decode a multivector back to a (value, unit) scalar quantity.

    For a CGA point on the e1 axis, the e1 component directly carries
    the Euclidean coordinate (and thus the encoded scalar value). The
    unit string is passed through from the caller — this function does
    not infer or change the unit.

    The decoder reads only the e1 component (index 1). It does not
    cross-check the e4/e5 components for consistency with the null
    property; that check is the test layer's job (assertion family 1
    and 3 in the ADR).

    Args:
        F: 32-component multivector to decode.
        unit: Unit string to attach to the returned scalar.

    Returns:
        Tuple of ``(value, unit)`` where ``value`` is the e1 coordinate.
    """
    if not isinstance(unit, str) or not unit:
        raise ValueError(f"decode_quantity: unit must be a non-empty string, got {unit!r}")
    arr = np.asarray(F, dtype=np.float64)
    if arr.shape != (N_COMPONENTS,):
        raise ValueError(f"decode_quantity: expected shape ({N_COMPONENTS},), got {arr.shape}")
    return float(arr[1]), unit
