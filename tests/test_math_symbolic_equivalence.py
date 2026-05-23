"""ADR-0131.1 — tests for the symbolic equivalence check primitive."""

from __future__ import annotations

from generate.math_symbolic_equivalence import (
    Verdict,
    check_equivalence,
)


class TestEquivalent:
    def test_identical_expressions(self) -> None:
        v = check_equivalence("x + 1", "x + 1")
        assert v.verdict == Verdict.EQUIVALENT
        assert v.canonical_a == v.canonical_b == "x+1"

    def test_distributive(self) -> None:
        v = check_equivalence("2*(x + 3)", "2*x + 6")
        assert v.verdict == Verdict.EQUIVALENT

    def test_square_of_binomial(self) -> None:
        v = check_equivalence("(x + 1)^2", "x^2 + 2*x + 1")
        assert v.verdict == Verdict.EQUIVALENT

    def test_difference_of_squares(self) -> None:
        v = check_equivalence("(x + 1)*(x - 1)", "x^2 - 1")
        assert v.verdict == Verdict.EQUIVALENT

    def test_collect_like_terms(self) -> None:
        v = check_equivalence("2*x + 3*x + x", "6*x")
        assert v.verdict == Verdict.EQUIVALENT

    def test_zero_cancellation(self) -> None:
        v = check_equivalence("x - x + 5", "5")
        assert v.verdict == Verdict.EQUIVALENT


class TestNotEquivalent:
    def test_different_constant(self) -> None:
        v = check_equivalence("x + 1", "x + 2")
        assert v.verdict == Verdict.NOT_EQUIVALENT
        assert v.canonical_a == "x+1"
        assert v.canonical_b == "x+2"

    def test_different_degree(self) -> None:
        v = check_equivalence("x^2", "x^3")
        assert v.verdict == Verdict.NOT_EQUIVALENT

    def test_sign_flipped(self) -> None:
        v = check_equivalence("(x + 1)^2", "(x - 1)^2")
        assert v.verdict == Verdict.NOT_EQUIVALENT


class TestRefused:
    def test_empty_left(self) -> None:
        v = check_equivalence("", "x + 1")
        assert v.verdict == Verdict.REFUSED
        assert "normalize(a) refused" in v.reason

    def test_out_of_scope_variable_left(self) -> None:
        v = check_equivalence("x + y", "x + 1")
        assert v.verdict == Verdict.REFUSED
        assert "single variable" in v.reason

    def test_division_refused(self) -> None:
        v = check_equivalence("x/2", "x")
        assert v.verdict == Verdict.REFUSED

    def test_a_normalizes_b_refuses(self) -> None:
        # a is fine, b uses y -> refusal with canonical_a populated
        v = check_equivalence("x + 1", "y + 1")
        assert v.verdict == Verdict.REFUSED
        assert v.canonical_a == "x+1"
        assert v.canonical_b is None
        assert "normalize(b) refused" in v.reason

    def test_refused_verdict_is_first_class(self) -> None:
        # Refusal preserves wrong == 0 — the verdict is REFUSED, never
        # silently coerced to NOT_EQUIVALENT.
        v = check_equivalence("garbage(", "x")
        assert v.verdict == Verdict.REFUSED


class TestDeterminism:
    def test_same_inputs_same_verdict(self) -> None:
        # Re-running produces byte-equal verdict.
        a, b = "(x + 2)*(x - 2)", "x^2 - 4"
        v1 = check_equivalence(a, b)
        v2 = check_equivalence(a, b)
        assert v1 == v2

    def test_canonical_strings_are_byte_equal_on_equivalence(self) -> None:
        v = check_equivalence("(x + 1)^2", "x^2 + 2*x + 1")
        assert v.canonical_a is not None
        assert v.canonical_b is not None
        assert v.canonical_a.encode("utf-8") == v.canonical_b.encode("utf-8")
