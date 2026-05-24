"""ADR-0140 acceptance tests — subtract as inverse translator + additive group closure.

Nine assertion families per the ADR:

Families 1-6 (inherited from ADR-0139, applied to subtract):
  1. Embedding well-formedness — subtract cases lie on null cone.
  2. Translator-of-negative well-formedness — versor_condition(subtract(b)) < 1e-6.
  3. Closure under sandwich — sandwich result stays on null cone.
  4. Arithmetic correctness — decoded value equals a − b within 1e-9.
  5. Replay determinism — byte-identical across runs.
  6. Composability — subtract(c) ∘ subtract(b) decodes to a − b − c.

New group-property families:
  7. Inverse composition — geometric_product(translator(-b), translator(b)) ≈ identity.
  8. Round-trip closure — versor_apply(T_{-b}, versor_apply(T_b, X)) decodes to (a, u).
  9. Commutativity / composition into sum:
       a) translator(a) * translator(b) ≈ translator(a+b) component-wise.
       b) translator(a) * translator(b) == translator(b) * translator(a) byte-equal.

If family 7 or 9 fails, ADR-0139's algebraic claim is invalidated retroactively.
The lift program is paused — see ADR-0140 §Falsification Discipline.
DO NOT loosen tolerances to make tests pass.
"""

from __future__ import annotations

import pytest
import numpy as np

from algebra.cga import cga_inner
from algebra.cl41 import geometric_product
from algebra.versor import versor_apply, versor_condition
from generate.math_versor_arithmetic import (
    decode_quantity,
    embed_quantity,
    subtract,
    translator,
)


# ---------------------------------------------------------------------------
# Fixed test cases per ADR-0140 §Acceptance
# ---------------------------------------------------------------------------

SUBTRACT_CASES: list[tuple[float, float]] = [
    (0.0, 0.0),
    (5.0, 0.0),
    (0.0, 5.0),
    (10.0, 3.0),
    (3.0, 10.0),
    (1.5, 0.5),
    (0.25, 0.75),
    (-5.0, 3.0),
    (5.0, -3.0),
    (-2.0, -3.0),
    (100.0, 1.0),
]

GROUP_CASES: list[tuple[float, float]] = [
    (0.0, 0.0),
    (1.0, 0.0),
    (0.0, 1.0),
    (1.0, 1.0),
    (-1.0, 1.0),
    (3.0, 4.0),
    (0.5, 0.5),
    (-2.5, 2.5),
    (100.0, 1.0),
    (1.0, 100.0),
]

# Composability case for family 6 (subtract twice).
COMPOSE_CASE: tuple[float, float, float] = (20.0, 3.0, 5.0)

# Tolerance constants — exactly as specified in the ADR.
TOL_NULL = 1e-5     # cga_inner(X, X) for null points
TOL_VERSOR = 1e-6   # versor_condition runtime contract
TOL_DECODE = 1e-9   # arithmetic correctness / round-trip / group properties


# ---------------------------------------------------------------------------
# Identity versor (scalar 1): component 0 = 1, all others 0.
# ---------------------------------------------------------------------------

def _identity_versor() -> np.ndarray:
    from algebra.cl41 import N_COMPONENTS
    v = np.zeros(N_COMPONENTS, dtype=np.float64)
    v[0] = 1.0
    return v


# ===========================================================================
# Families 1-6: ADR-0139 assertion families applied to subtract
# ===========================================================================


# ----- Family 1: embedding well-formedness -----

@pytest.mark.parametrize("a,b", SUBTRACT_CASES)
def test_family1_embedding_is_null(a: float, b: float) -> None:
    """embed_quantity(a, _) and embed_quantity(b, _) both lie on the null cone."""
    X_a = embed_quantity(a, "u")
    X_b = embed_quantity(b, "u")
    inner_a = abs(float(cga_inner(X_a, X_a)))
    inner_b = abs(float(cga_inner(X_b, X_b)))
    assert inner_a < TOL_NULL, (
        f"embed_quantity({a}) not null: |cga_inner| = {inner_a:.3e}"
    )
    assert inner_b < TOL_NULL, (
        f"embed_quantity({b}) not null: |cga_inner| = {inner_b:.3e}"
    )


# ----- Family 2: translator-of-negative well-formedness -----

@pytest.mark.parametrize("a,b", SUBTRACT_CASES)
def test_family2_subtract_unit_versor(a: float, b: float) -> None:
    """subtract(b) satisfies versor_condition < 1e-6."""
    S = subtract(b)
    cond = versor_condition(S)
    assert cond < TOL_VERSOR, (
        f"subtract({b}) not unit versor: versor_condition = {cond:.3e}"
    )


# ----- Family 3: closure under sandwich -----

@pytest.mark.parametrize("a,b", SUBTRACT_CASES)
def test_family3_sandwich_preserves_null(a: float, b: float) -> None:
    """versor_apply(subtract(b), embed_quantity(a, _)) stays on the null cone."""
    X = embed_quantity(a, "u")
    S = subtract(b)
    R = versor_apply(S, X)
    inner_R = abs(float(cga_inner(R, R)))
    assert inner_R < TOL_NULL, (
        f"sandwich result ({a} − {b}) not null: |cga_inner(R, R)| = {inner_R:.3e}"
    )


# ----- Family 4: arithmetic correctness -----

@pytest.mark.parametrize("a,b", SUBTRACT_CASES)
def test_family4_decode_matches_difference(a: float, b: float) -> None:
    """decode_quantity(R, _) returns (a − b, _) within 1e-9."""
    X = embed_quantity(a, "u")
    S = subtract(b)
    R = versor_apply(S, X)
    value, unit = decode_quantity(R, "u")
    expected = a - b
    err = abs(value - expected)
    assert unit == "u", f"unit metadata lost: got {unit!r}"
    assert err < TOL_DECODE, (
        f"decode error for ({a} − {b}): got {value}, expected {expected}, err = {err:.3e}"
    )


# ----- Family 5: replay determinism -----

@pytest.mark.parametrize("a,b", SUBTRACT_CASES)
def test_family5_replay_byte_identical(a: float, b: float) -> None:
    """Two independent runs produce byte-identical multivector arrays."""
    X1 = embed_quantity(a, "u")
    X2 = embed_quantity(a, "u")
    S1 = subtract(b)
    S2 = subtract(b)
    R1 = versor_apply(S1, X1)
    R2 = versor_apply(S2, X2)
    assert X1.tobytes() == X2.tobytes(), (
        f"embed_quantity({a}) not deterministic across runs"
    )
    assert S1.tobytes() == S2.tobytes(), (
        f"subtract({b}) not deterministic across runs"
    )
    assert R1.tobytes() == R2.tobytes(), (
        f"versor_apply result not deterministic across runs for ({a}, {b})"
    )


# ----- Family 6: composability -----

def test_family6_two_subtracts_compose() -> None:
    """subtract(c) ∘ subtract(b) applied to embed_quantity(a) decodes to a − b − c."""
    a, b, c = COMPOSE_CASE
    X = embed_quantity(a, "u")
    S_b = subtract(b)
    S_c = subtract(c)

    R1 = versor_apply(S_b, X)
    R2 = versor_apply(S_c, R1)

    inner_R1 = abs(float(cga_inner(R1, R1)))
    inner_R2 = abs(float(cga_inner(R2, R2)))
    assert inner_R1 < TOL_NULL, (
        f"intermediate (a − b = {a - b}) not null: |cga_inner| = {inner_R1:.3e}"
    )
    assert inner_R2 < TOL_NULL, (
        f"final (a − b − c = {a - b - c}) not null: |cga_inner| = {inner_R2:.3e}"
    )

    value, unit = decode_quantity(R2, "u")
    expected = a - b - c
    err = abs(value - expected)
    assert unit == "u"
    assert err < TOL_DECODE, (
        f"compose decode error: got {value}, expected {expected}, err = {err:.3e}"
    )


# ===========================================================================
# Families 7-9: Additive group structure verification
# ===========================================================================


# ----- Family 7: inverse composition -----
#
# geometric_product(translator(-b), translator(b)) must equal the identity
# versor (component 0 = 1, all others 0) within 1e-9 component-wise.
#
# If this fails, the algebra is not decoding exact addition — it is decoding
# something that resembles addition on point-pairs but does not form a group.
# That invalidates ADR-0139 retroactively. STOP; do not loosen 1e-9.

@pytest.mark.parametrize("a,b", GROUP_CASES)
def test_family7_inverse_composition_is_identity(a: float, b: float) -> None:
    """geometric_product(translator(-b), translator(b)) ≈ identity within 1e-9."""
    T_pos = translator(b)
    T_neg = translator(-b)
    product = geometric_product(T_neg, T_pos)
    identity = _identity_versor()

    residual = np.abs(product - identity)
    max_residual = float(residual.max())
    assert max_residual < TOL_DECODE, (
        f"Inverse composition residual for b={b}: max |product - identity| = {max_residual:.6e}\n"
        f"Component residuals (non-zero): "
        + str([(i, float(residual[i])) for i in range(len(residual)) if residual[i] > 1e-15])
    )


# ----- Family 8: round-trip closure -----
#
# versor_apply(T_{-b}, versor_apply(T_b, embed_quantity(a))) must decode
# back to (a, "u") within 1e-9. Includes the b=0 edge case.

@pytest.mark.parametrize("a,b", GROUP_CASES)
def test_family8_round_trip_closure(a: float, b: float) -> None:
    """versor_apply(T_{{-b}}, versor_apply(T_b, X)) decodes to (a, u) within 1e-9."""
    X = embed_quantity(a, "u")
    T_pos = translator(b)
    T_neg = translator(-b)

    shifted = versor_apply(T_pos, X)
    recovered = versor_apply(T_neg, shifted)

    # Intermediate must stay on null cone.
    inner_shifted = abs(float(cga_inner(shifted, shifted)))
    assert inner_shifted < TOL_NULL, (
        f"Round-trip intermediate not null for (a={a}, b={b}): "
        f"|cga_inner| = {inner_shifted:.3e}"
    )

    # Final must stay on null cone.
    inner_recovered = abs(float(cga_inner(recovered, recovered)))
    assert inner_recovered < TOL_NULL, (
        f"Round-trip result not null for (a={a}, b={b}): "
        f"|cga_inner| = {inner_recovered:.3e}"
    )

    value, unit = decode_quantity(recovered, "u")
    err = abs(value - a)
    assert unit == "u"
    assert err < TOL_DECODE, (
        f"Round-trip decode error for (a={a}, b={b}): "
        f"got {value}, expected {a}, err = {err:.3e}"
    )


# ----- Family 9a: composition into sum -----
#
# geometric_product(translator(a), translator(b)) must equal translator(a+b)
# component-wise within 1e-9.

@pytest.mark.parametrize("a,b", GROUP_CASES)
def test_family9a_composition_equals_sum_translator(a: float, b: float) -> None:
    """geometric_product(translator(a), translator(b)) == translator(a+b) within 1e-9."""
    T_a = translator(a)
    T_b = translator(b)
    T_sum = translator(a + b)

    product = geometric_product(T_a, T_b)
    residual = np.abs(product - T_sum)
    max_residual = float(residual.max())
    assert max_residual < TOL_DECODE, (
        f"Sum-composition residual for (a={a}, b={b}): "
        f"max |T_a*T_b - T_{{a+b}}| = {max_residual:.6e}\n"
        f"Component residuals (non-zero): "
        + str([(i, float(residual[i])) for i in range(len(residual)) if residual[i] > 1e-15])
    )


# ----- Family 9b: commutativity -----
#
# geometric_product(translator(a), translator(b)) must equal
# geometric_product(translator(b), translator(a)) byte-exactly.
# If this fails, the algebra decodes a non-abelian operation.

@pytest.mark.parametrize("a,b", GROUP_CASES)
def test_family9b_commutativity_byte_equal(a: float, b: float) -> None:
    """geometric_product(translator(a), translator(b)) byte-equals geometric_product(translator(b), translator(a))."""
    T_a = translator(a)
    T_b = translator(b)

    ab = geometric_product(T_a, T_b)
    ba = geometric_product(T_b, T_a)

    assert ab.tobytes() == ba.tobytes(), (
        f"Commutativity violation for (a={a}, b={b}): "
        f"T_a*T_b != T_b*T_a\n"
        f"Max component diff: {float(np.abs(ab - ba).max()):.6e}"
    )
