"""ADR-0141 acceptance tests — multiply as CGA dilator (positive non-zero only).

Ten assertion families per the ADR:

  Family 1  — Dilator well-formedness: versor_condition(multiply(s)) < 1e-6.
  Family 2  — Closure under sandwich: cga_inner(R, R) < 1e-5.
  Family 3  — Arithmetic correctness: decode_quantity(R, "u") == (a*s, "u") within 1e-9.
  Family 4  — Replay determinism: byte-identical across runs.
  Family 5  — Identity dilator: multiply(1.0) equals scalar identity within 1e-9.
  Family 6  — Composition into product: multiply(s1)*multiply(s2) == multiply(s1*s2) within 1e-9.
  Family 7  — Inverse composition: multiply(1/s)*multiply(s) ≈ identity within 1e-9.
  Family 8  — Round-trip closure: decode(versor_apply(multiply(1/s), versor_apply(multiply(s), X))) == a within 1e-9.
  Family 9  — Commutativity: multiply(s1)*multiply(s2) byte-equals multiply(s2)*multiply(s1).
  Family 10 — Boundary refusal: multiply(0), multiply(-1), multiply(-3.5), multiply(-100),
              multiply(-0.0001) all raise ValueError at construction time.

PRELIMINARY MEASUREMENT REPORT (empirical, this CGA implementation):
  N = n_o ∧ n_inf: single non-zero component at index 15 (blade (3,4) = e4∧e5), value = -1.0.
  N² = +1.0 (pure scalar, grade-0 only, all other components zero).
  n_o · n_inf = -1.0; n_o² = 0.0; n_inf² = 0.0.

  Because N² = +1, the exponential exp(α/2·N) = cosh(α/2) + sinh(α/2)·N is exact
  in float64.  The dilator is: D[0] = cosh(α/2), D[15] = -sinh(α/2), all others 0.

  D_s · ~D_s = cosh²(α/2) - sinh²(α/2)·N² = cosh²(α/2) - sinh²(α/2) = 1 exactly.
  So versor_condition(D_s) is at machine epsilon, not merely < 1e-6.

FALSIFICATION DISCIPLINE (read before changing any tolerance):
  DO NOT loosen any threshold below. The thresholds are the ADR contract.
  If any family fails, report the measured residual and stop; do not adjust.
"""

from __future__ import annotations

import math
import pytest
import numpy as np

from algebra.cga import cga_inner
from algebra.cl41 import geometric_product, N_COMPONENTS
from algebra.versor import versor_apply, versor_condition
from generate.math_versor_arithmetic import (
    decode_quantity,
    embed_quantity,
    multiply,
)

# ---------------------------------------------------------------------------
# Fixed test cases per ADR-0141 §Acceptance §Fixed test cases
# ---------------------------------------------------------------------------

# Scale set for families 1–5, 7, 8.  Only (a, s) pairs with s > 0.
# The ADR lists (5, -2) as "excluded" (negative s); it is tested in family 10.
SCALE_CASES: list[tuple[float, float]] = [
    (0.0,  2.0),
    (1.0,  2.0),
    (1.0,  3.0),
    (3.0,  4.0),
    (5.0,  0.5),
    (10.0, 0.25),
    (4.0,  0.75),
    (7.0,  1.0),                          # identity scale
    (2.0,  math.sqrt(2)),                 # √2
    (1.0,  math.pi),                      # π
    (100.0, 0.01),
    (0.01,  100.0),
    (-5.0,  2.0),                         # negative a, positive s
]

# Composition set for families 6, 9.
COMPOSE_CASES: list[tuple[float, float]] = [
    (1.0, 1.0),
    (2.0, 1.0),
    (1.0, 2.0),
    (2.0, 3.0),
    (3.0, 2.0),
    (0.5, 4.0),
    (math.sqrt(2), math.sqrt(2)),         # √2 × √2 → 2.0
    (math.pi,      1.0),
    (10.0,         0.1),                  # 10 × 0.1 → 1.0 (float64 drift probe)
]

# Boundary set for family 10.  All of these must raise ValueError.
INVALID_SCALES: list[float] = [0.0, -1.0, -3.5, -100.0, -0.0001]

# Tolerance constants — exactly as specified in ADR-0141.
TOL_VERSOR   = 1e-6   # versor_condition runtime contract
TOL_NULL     = 1e-5   # cga_inner(X, X) for null points
TOL_IDENTITY = 1e-9   # component-wise identity comparison
TOL_DECODE   = 1e-9   # arithmetic correctness


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _identity_versor() -> np.ndarray:
    v = np.zeros(N_COMPONENTS, dtype=np.float64)
    v[0] = 1.0
    return v


# ===========================================================================
# Family 1 — Dilator well-formedness
# ===========================================================================

@pytest.mark.parametrize("a,s", SCALE_CASES)
def test_family1_dilator_unit_versor(a: float, s: float) -> None:
    """versor_condition(multiply(s)) < 1e-6 for every scale in the test set."""
    D = multiply(s)
    cond = versor_condition(D)
    assert cond < TOL_VERSOR, (
        f"multiply({s}) not unit versor: versor_condition = {cond:.6e} (threshold 1e-6)"
    )


# ===========================================================================
# Family 2 — Closure under sandwich
# ===========================================================================

@pytest.mark.parametrize("a,s", SCALE_CASES)
def test_family2_sandwich_preserves_null(a: float, s: float) -> None:
    """versor_apply(multiply(s), embed_quantity(a)) stays on the null cone."""
    D = multiply(s)
    X = embed_quantity(a, "u")
    R = versor_apply(D, X)
    inner_R = abs(float(cga_inner(R, R)))
    assert inner_R < TOL_NULL, (
        f"sandwich result ({a} × {s}) not null: |cga_inner(R, R)| = {inner_R:.3e}"
    )


# ===========================================================================
# Family 3 — Arithmetic correctness
# ===========================================================================

@pytest.mark.parametrize("a,s", SCALE_CASES)
def test_family3_decode_matches_product(a: float, s: float) -> None:
    """decode_quantity(R, 'u') returns (a * s, 'u') within 1e-9."""
    D = multiply(s)
    X = embed_quantity(a, "u")
    R = versor_apply(D, X)
    value, unit = decode_quantity(R, "u")
    expected = a * s
    err = abs(value - expected)
    assert unit == "u", f"unit metadata lost: got {unit!r}"
    assert err < TOL_DECODE, (
        f"decode error for ({a} × {s}): got {value!r}, expected {expected!r}, "
        f"err = {err:.6e} (threshold 1e-9)"
    )


# ===========================================================================
# Family 4 — Replay determinism
# ===========================================================================

@pytest.mark.parametrize("a,s", SCALE_CASES)
def test_family4_replay_byte_identical(a: float, s: float) -> None:
    """Two independent runs produce byte-identical multivector arrays."""
    X1 = embed_quantity(a, "u")
    X2 = embed_quantity(a, "u")
    D1 = multiply(s)
    D2 = multiply(s)
    R1 = versor_apply(D1, X1)
    R2 = versor_apply(D2, X2)
    assert X1.tobytes() == X2.tobytes(), (
        f"embed_quantity({a}) not deterministic across runs"
    )
    assert D1.tobytes() == D2.tobytes(), (
        f"multiply({s}) not deterministic across runs"
    )
    assert R1.tobytes() == R2.tobytes(), (
        f"versor_apply result not deterministic across runs for (a={a}, s={s})"
    )


# ===========================================================================
# Family 5 — Identity dilator
# ===========================================================================

def test_family5_identity_dilator() -> None:
    """multiply(1.0) equals the scalar identity versor within 1e-9 component-wise."""
    D = multiply(1.0)
    identity = _identity_versor()
    err_vec = np.abs(D - identity)
    max_err = float(err_vec.max())
    assert max_err < TOL_IDENTITY, (
        f"multiply(1.0) deviates from scalar identity: "
        f"max component error = {max_err:.6e} (threshold 1e-9)\n"
        f"Non-zero diff components: "
        + str([(i, float(err_vec[i])) for i in range(len(err_vec)) if err_vec[i] > 1e-15])
    )


# ===========================================================================
# Family 6 — Composition into product
# ===========================================================================

@pytest.mark.parametrize("s1,s2", COMPOSE_CASES)
def test_family6_composition_into_product(s1: float, s2: float) -> None:
    """geometric_product(multiply(s1), multiply(s2)) == multiply(s1*s2) within 1e-9."""
    D1  = multiply(s1)
    D2  = multiply(s2)
    D12 = geometric_product(D1, D2)
    D_prod = multiply(s1 * s2)

    residual = np.abs(D12 - D_prod)
    max_err  = float(residual.max())
    assert max_err < TOL_IDENTITY, (
        f"Composition residual for ({s1}, {s2}) → s1*s2={s1*s2}: "
        f"max |D12 - D(s1*s2)| = {max_err:.6e} (threshold 1e-9)\n"
        f"Non-zero diff components: "
        + str([(i, float(residual[i])) for i in range(len(residual)) if residual[i] > 1e-15])
    )


# ===========================================================================
# Family 7 — Inverse composition
# ===========================================================================

@pytest.mark.parametrize("a,s", SCALE_CASES)
def test_family7_inverse_composition_is_identity(a: float, s: float) -> None:
    """geometric_product(multiply(1/s), multiply(s)) ≈ identity within 1e-9."""
    D_s   = multiply(s)
    D_inv = multiply(1.0 / s)
    product  = geometric_product(D_inv, D_s)
    identity = _identity_versor()

    residual = np.abs(product - identity)
    max_err  = float(residual.max())
    assert max_err < TOL_IDENTITY, (
        f"Inverse composition residual for s={s}: "
        f"max |D(1/s)*D(s) - I| = {max_err:.6e} (threshold 1e-9)\n"
        f"Non-zero diff components: "
        + str([(i, float(residual[i])) for i in range(len(residual)) if residual[i] > 1e-15])
    )


# ===========================================================================
# Family 8 — Round-trip closure
# ===========================================================================

@pytest.mark.parametrize("a,s", SCALE_CASES)
def test_family8_round_trip_closure(a: float, s: float) -> None:
    """versor_apply(multiply(1/s), versor_apply(multiply(s), X)) decodes to (a, u) within 1e-9."""
    D_s   = multiply(s)
    D_inv = multiply(1.0 / s)
    X     = embed_quantity(a, "u")

    scaled   = versor_apply(D_s,   X)
    recovered = versor_apply(D_inv, scaled)

    # Intermediate must stay on null cone.
    inner_scaled = abs(float(cga_inner(scaled, scaled)))
    assert inner_scaled < TOL_NULL, (
        f"Round-trip intermediate not null for (a={a}, s={s}): "
        f"|cga_inner| = {inner_scaled:.3e}"
    )

    # Final must stay on null cone.
    inner_recovered = abs(float(cga_inner(recovered, recovered)))
    assert inner_recovered < TOL_NULL, (
        f"Round-trip final not null for (a={a}, s={s}): "
        f"|cga_inner| = {inner_recovered:.3e}"
    )

    value, unit = decode_quantity(recovered, "u")
    err = abs(value - a)
    assert unit == "u"
    assert err < TOL_DECODE, (
        f"Round-trip decode error for (a={a}, s={s}): "
        f"got {value!r}, expected {a!r}, err = {err:.6e} (threshold 1e-9)"
    )


# ===========================================================================
# Family 9 — Commutativity
# ===========================================================================

@pytest.mark.parametrize("s1,s2", COMPOSE_CASES)
def test_family9_commutativity_byte_equal(s1: float, s2: float) -> None:
    """geometric_product(multiply(s1), multiply(s2)) byte-equals multiply(s2)*multiply(s1)."""
    D1 = multiply(s1)
    D2 = multiply(s2)
    ab = geometric_product(D1, D2)
    ba = geometric_product(D2, D1)
    assert ab.tobytes() == ba.tobytes(), (
        f"Commutativity violation for (s1={s1}, s2={s2}): "
        f"D1*D2 != D2*D1\n"
        f"Max component diff: {float(np.abs(ab - ba).max()):.6e}"
    )


# ===========================================================================
# Family 10 — Boundary refusal at construction time
# ===========================================================================

@pytest.mark.parametrize("bad_s", INVALID_SCALES)
def test_family10_invalid_scale_raises_at_construction(bad_s: float) -> None:
    """multiply(s) raises ValueError at construction for s in {0, -1, -3.5, -100, -0.0001}."""
    with pytest.raises(ValueError) as exc_info:
        multiply(bad_s)
    msg = str(exc_info.value)
    # Error must name the scale value.
    assert str(bad_s) in msg or repr(bad_s) in msg, (
        f"ValueError for scale={bad_s!r} does not name the scale in message: {msg!r}"
    )
    # Error must name the restriction.
    assert any(kw in msg.lower() for kw in ("positive", "strictly", "deferred", "> 0")), (
        f"ValueError for scale={bad_s!r} does not name the restriction in message: {msg!r}"
    )
