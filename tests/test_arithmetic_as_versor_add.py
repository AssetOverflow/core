"""ADR-0139 acceptance tests — arithmetic-as-versor spike for `add`.

Six assertion families per the ADR:

1. Embedding well-formedness — embedded quantity is on the null cone.
2. Translator well-formedness — versor_condition < 1e-6.
3. Closure — sandwiched result is still on the null cone.
4. Arithmetic correctness — decoded value equals a + b within 1e-9.
5. Replay determinism — running twice produces byte-identical arrays.
6. Composability — two consecutive translators decode to a + b + c.

If any test fails, ADR-0139 is falsified; the lift program is paused.
DO NOT loosen tolerances to make tests pass.
"""

from __future__ import annotations

import pytest
import numpy as np

from algebra.cga import cga_inner
from algebra.versor import versor_apply, versor_condition
from generate.math_versor_arithmetic import (
    decode_quantity,
    embed_quantity,
    translator,
)


# Fixed test cases per ADR-0139 acceptance.
ADD_CASES: list[tuple[float, float]] = [
    (0.0, 0.0),
    (0.0, 1.0),
    (1.0, 0.0),
    (3.0, 4.0),
    (7.0, -3.0),
    (0.25, 0.75),
    (1.5, 2.5),
    (-5.0, 5.0),
    (-2.0, -3.0),
    (100.0, 1.0),
    (1.0, 100.0),
]

# Composability case per ADR-0139.
COMPOSE_CASE: tuple[float, float, float] = (2.0, 3.0, 5.0)

# Tolerance constants — exactly as specified in the ADR.
TOL_NULL = 1e-5  # cga_inner(X, X) for null points (f32 sandwich noise floor)
TOL_VERSOR = 1e-6  # versor_condition runtime contract
TOL_DECODE = 1e-9  # arithmetic correctness


# ----- Assertion family 1: embedding well-formedness -----


@pytest.mark.parametrize("a,b", ADD_CASES)
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


# ----- Assertion family 2: translator well-formedness -----


@pytest.mark.parametrize("a,b", ADD_CASES)
def test_family2_translator_unit_versor(a: float, b: float) -> None:
    """translator(b) satisfies versor_condition < 1e-6."""
    T = translator(b)
    cond = versor_condition(T)
    assert cond < TOL_VERSOR, (
        f"translator({b}) not unit versor: versor_condition = {cond:.3e}"
    )


# ----- Assertion family 3: closure -----


@pytest.mark.parametrize("a,b", ADD_CASES)
def test_family3_sandwich_preserves_null(a: float, b: float) -> None:
    """versor_apply(translator(b), embed_quantity(a, _)) is still on the null cone."""
    X = embed_quantity(a, "u")
    T = translator(b)
    R = versor_apply(T, X)
    inner_R = abs(float(cga_inner(R, R)))
    assert inner_R < TOL_NULL, (
        f"sandwich result ({a} + {b}) not null: |cga_inner(R, R)| = {inner_R:.3e}"
    )


# ----- Assertion family 4: arithmetic correctness -----


@pytest.mark.parametrize("a,b", ADD_CASES)
def test_family4_decode_matches_sum(a: float, b: float) -> None:
    """decode_quantity(R, _) returns (a + b, _) within 1e-9."""
    X = embed_quantity(a, "u")
    T = translator(b)
    R = versor_apply(T, X)
    value, unit = decode_quantity(R, "u")
    expected = a + b
    err = abs(value - expected)
    assert unit == "u", f"unit metadata lost: got {unit!r}"
    assert err < TOL_DECODE, (
        f"decode error for ({a} + {b}): got {value}, expected {expected}, err = {err:.3e}"
    )


# ----- Assertion family 5: replay determinism -----


@pytest.mark.parametrize("a,b", ADD_CASES)
def test_family5_replay_byte_identical(a: float, b: float) -> None:
    """Two independent runs produce byte-identical multivector arrays."""
    X1 = embed_quantity(a, "u")
    X2 = embed_quantity(a, "u")
    T1 = translator(b)
    T2 = translator(b)
    R1 = versor_apply(T1, X1)
    R2 = versor_apply(T2, X2)
    assert X1.tobytes() == X2.tobytes(), (
        f"embed_quantity({a}) not deterministic across runs"
    )
    assert T1.tobytes() == T2.tobytes(), (
        f"translator({b}) not deterministic across runs"
    )
    assert R1.tobytes() == R2.tobytes(), (
        f"versor_apply result not deterministic across runs for ({a}, {b})"
    )


# ----- Assertion family 6: composability -----


def test_family6_two_translators_compose() -> None:
    """T_c · T_b · X decodes to a + b + c."""
    a, b, c = COMPOSE_CASE
    X = embed_quantity(a, "u")
    T_b = translator(b)
    T_c = translator(c)

    # Apply T_b first, then T_c.
    R1 = versor_apply(T_b, X)
    R2 = versor_apply(T_c, R1)

    # Each intermediate result must remain on the null cone.
    inner_R1 = abs(float(cga_inner(R1, R1)))
    inner_R2 = abs(float(cga_inner(R2, R2)))
    assert inner_R1 < TOL_NULL, (
        f"intermediate (a + b = {a + b}) not null: |cga_inner| = {inner_R1:.3e}"
    )
    assert inner_R2 < TOL_NULL, (
        f"final (a + b + c = {a + b + c}) not null: |cga_inner| = {inner_R2:.3e}"
    )

    value, unit = decode_quantity(R2, "u")
    expected = a + b + c
    err = abs(value - expected)
    assert unit == "u"
    assert err < TOL_DECODE, (
        f"compose decode error: got {value}, expected {expected}, err = {err:.3e}"
    )
