"""ADR-0131.1 — tests for the univariate polynomial normalizer.

Exercises every grammar rule, every algebraic identity the v1 scope
needs to cover, and every refusal criterion. The load-bearing
assertion: same algebraic content -> same canonical string,
byte-for-byte.
"""

from __future__ import annotations

import pytest

from generate.math_symbolic_normalizer import (
    Polynomial,
    SymbolicError,
    canonical_string,
    normalize,
)


# ---------------------------------------------------------------------------
# Trivial parses
# ---------------------------------------------------------------------------

class TestTrivialParse:
    def test_constant_zero(self) -> None:
        assert normalize("0").coefficients == ()

    def test_constant_positive(self) -> None:
        assert normalize("7").coefficients == (7,)

    def test_constant_negative_unary(self) -> None:
        assert normalize("-3").coefficients == (-3,)

    def test_bare_variable(self) -> None:
        assert normalize("x").coefficients == (0, 1)

    def test_simple_sum(self) -> None:
        assert normalize("x + 1").coefficients == (1, 1)

    def test_implicit_coefficient_is_one(self) -> None:
        # "x^2 + x" -> coefficients (0, 1, 1)
        assert normalize("x^2 + x").coefficients == (0, 1, 1)


# ---------------------------------------------------------------------------
# Algebraic identities (the heart of the equivalence test)
# ---------------------------------------------------------------------------

class TestAlgebraicIdentities:
    def test_distributive_basic(self) -> None:
        # 2*(x + 3) == 2x + 6
        assert canonical_string("2*(x + 3)") == canonical_string("2*x + 6")

    def test_distributive_with_variable(self) -> None:
        # x*(x + 1) == x^2 + x
        assert canonical_string("x*(x + 1)") == canonical_string("x^2 + x")

    def test_commutative_addition(self) -> None:
        assert canonical_string("3 + x") == canonical_string("x + 3")

    def test_commutative_multiplication(self) -> None:
        assert canonical_string("3*x") == canonical_string("x*3")

    def test_associative_addition(self) -> None:
        assert canonical_string("(x + 1) + 2") == canonical_string("x + (1 + 2)")

    def test_square_of_binomial(self) -> None:
        # (x + 1)^2 == x^2 + 2x + 1
        assert canonical_string("(x + 1)^2") == canonical_string("x^2 + 2*x + 1")

    def test_square_of_binomial_negative(self) -> None:
        # (x - 1)^2 == x^2 - 2x + 1
        assert canonical_string("(x - 1)^2") == canonical_string("x^2 - 2*x + 1")

    def test_difference_of_squares(self) -> None:
        # (x + 1)(x - 1) == x^2 - 1
        assert canonical_string("(x + 1)*(x - 1)") == canonical_string("x^2 - 1")

    def test_cube_of_binomial(self) -> None:
        # (x + 1)^3 == x^3 + 3x^2 + 3x + 1
        assert canonical_string("(x + 1)^3") == canonical_string(
            "x^3 + 3*x^2 + 3*x + 1"
        )

    def test_foil(self) -> None:
        # (x + 2)(x + 3) == x^2 + 5x + 6
        assert canonical_string("(x + 2)*(x + 3)") == canonical_string(
            "x^2 + 5*x + 6"
        )

    def test_collect_like_terms(self) -> None:
        # 2x + 3x == 5x
        assert canonical_string("2*x + 3*x") == canonical_string("5*x")

    def test_zero_cancellation(self) -> None:
        # x - x == 0
        assert canonical_string("x - x") == "0"

    def test_subtraction_distributes(self) -> None:
        # 2 - (x - 1) == 3 - x
        assert canonical_string("2 - (x - 1)") == canonical_string("3 - x")

    def test_x_zero_is_one(self) -> None:
        # x^0 == 1
        assert canonical_string("x^0") == canonical_string("1")

    def test_pow_caret_and_double_star_equivalent(self) -> None:
        # both spellings accepted; output identical
        assert canonical_string("x^2") == canonical_string("x**2")


# ---------------------------------------------------------------------------
# Non-equivalence: distinct polynomials canonicalize differently
# ---------------------------------------------------------------------------

class TestNonEquivalence:
    def test_different_constant(self) -> None:
        assert canonical_string("x + 1") != canonical_string("x + 2")

    def test_different_coefficient(self) -> None:
        assert canonical_string("2*x") != canonical_string("3*x")

    def test_different_degree(self) -> None:
        assert canonical_string("x^2") != canonical_string("x^3")

    def test_sign_flipped(self) -> None:
        assert canonical_string("x + 1") != canonical_string("x - 1")


# ---------------------------------------------------------------------------
# Canonical-string format
# ---------------------------------------------------------------------------

class TestCanonicalStringFormat:
    def test_zero(self) -> None:
        assert canonical_string("0") == "0"

    def test_constant(self) -> None:
        assert canonical_string("7") == "7"

    def test_x(self) -> None:
        assert canonical_string("x") == "x"

    def test_negative_constant(self) -> None:
        assert canonical_string("-3") == "-3"

    def test_x_plus_one(self) -> None:
        assert canonical_string("x + 1") == "x+1"

    def test_descending_order(self) -> None:
        assert canonical_string("1 + x + x^2") == "x^2+x+1"

    def test_coefficient_one_elided(self) -> None:
        assert canonical_string("1*x") == "x"

    def test_negative_leading_coefficient(self) -> None:
        assert canonical_string("-x + 1") == "-x+1"


# ---------------------------------------------------------------------------
# Refusals (preserve wrong == 0 for the benchmark)
# ---------------------------------------------------------------------------

class TestRefusals:
    def test_empty_input(self) -> None:
        with pytest.raises(SymbolicError, match="empty"):
            normalize("")

    def test_multivariable_now_admits(self) -> None:
        # ADR-0131.1.B scope expansion: multivariable polynomials admit.
        poly = normalize("x + y")
        assert poly.to_canonical_string() == "x+y"

    def test_negative_exponent(self) -> None:
        with pytest.raises(SymbolicError, match="non-negative"):
            normalize("x^-1")

    def test_non_constant_exponent(self) -> None:
        with pytest.raises(SymbolicError, match="constant"):
            normalize("x^x")

    def test_syntax_unbalanced_paren(self) -> None:
        with pytest.raises(SymbolicError):
            normalize("(x + 1")

    def test_syntax_trailing_op(self) -> None:
        with pytest.raises(SymbolicError):
            normalize("x +")

    def test_constant_denominator_now_admits(self) -> None:
        # ADR-0131.1.B scope expansion: constant-denominator division admits.
        poly = normalize("x / 2")
        assert poly.to_canonical_string() == "1/2*x"

    def test_symbolic_denominator_still_refused(self) -> None:
        with pytest.raises(SymbolicError):
            normalize("x / y")


# ---------------------------------------------------------------------------
# Polynomial dataclass invariants
# ---------------------------------------------------------------------------

class TestPolynomialInvariants:
    def test_zero_coefficient_terms_collapse(self) -> None:
        # Sparse multivariable repr canonicalizes by dropping zero-coef terms.
        assert (
            Polynomial(terms={(2,): 1, (1,): 2, (0,): 0}, variables=("x",)).to_canonical_string()
            == "x^2+2*x"
        )

    def test_float_rejected(self) -> None:
        with pytest.raises(SymbolicError, match="float"):
            Polynomial(terms={(0,): 1.5}, variables=("x",))  # type: ignore[dict-item]

    def test_zero_polynomial(self) -> None:
        # Zero polynomial canonical form has empty terms dict.
        assert Polynomial(terms={}, variables=("x",)).to_canonical_string() == "0"

    def test_equality(self) -> None:
        a = Polynomial(terms={(2,): 3, (1,): 2, (0,): 1}, variables=("x",))
        b = Polynomial(terms={(2,): 3, (1,): 2, (0,): 1}, variables=("x",))
        assert a == b
        c = Polynomial(terms={(2,): 4, (1,): 2, (0,): 1}, variables=("x",))
        assert a != c
