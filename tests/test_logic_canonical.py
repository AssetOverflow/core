"""ADR-0201 — standalone tests for the propositional canonicalizer keystone.

Exercised in isolation, with no binding-graph wiring and no inference rules — the
same way :mod:`generate.math_symbolic_equivalence` is tested standalone. The point
is to prove the keystone holds ALONE before anything depends on it: equivalent
formulas collapse to one canonical key, non-equivalent ones don't, the form is
byte-deterministic, and out-of-regime / oversized inputs refuse rather than guess.
"""

from __future__ import annotations

import pytest

from generate.logic_canonical import (
    DEFAULT_MAX_NODES,
    LogicBudgetError,
    LogicError,
    canonicalize,
)
from generate.logic_equivalence import Verdict, check_equivalence


def _key(formula: str) -> str:
    return canonicalize(formula).canonical_key


# ---------------------------------------------------------------------------
# Canonicity: logically-equivalent formulas produce IDENTICAL keys.
# Each pair would FAIL if the diagram were not reduced/canonical.
# ---------------------------------------------------------------------------

EQUIVALENT_PAIRS = [
    ("P & Q", "Q & P"),                       # ∧ commutativity
    ("P | Q", "Q | P"),                       # ∨ commutativity
    ("~~P", "P"),                             # double negation
    ("P -> Q", "~P | Q"),                     # implication rewrite
    ("~(P & Q)", "~P | ~Q"),                  # De Morgan
    ("~(P | Q)", "~P & ~Q"),                  # De Morgan
    ("P <-> Q", "(P -> Q) & (Q -> P)"),       # iff definition
    ("P & (Q | R)", "(P & Q) | (P & R)"),     # distributivity
    ("P & P", "P"),                           # idempotence
    ("P", "P & (Q | ~Q)"),                    # irrelevant variable reduces out
    ("P | (P & Q)", "P"),                     # absorption
]


@pytest.mark.parametrize("a,b", EQUIVALENT_PAIRS)
def test_equivalent_formulas_share_canonical_key(a: str, b: str) -> None:
    assert _key(a) == _key(b)
    assert check_equivalence(a, b).verdict is Verdict.EQUIVALENT


# ---------------------------------------------------------------------------
# Discrimination: non-equivalent formulas produce DISTINCT keys.
# These guard against a degenerate canonicalizer that collapses everything.
# ---------------------------------------------------------------------------

NON_EQUIVALENT_PAIRS = [
    ("P & Q", "P | Q"),
    ("P", "Q"),               # distinct atoms must not collide
    ("P -> Q", "Q -> P"),     # implication is not symmetric
    ("P", "~P"),
    ("P & Q", "P"),
]


@pytest.mark.parametrize("a,b", NON_EQUIVALENT_PAIRS)
def test_non_equivalent_formulas_have_distinct_keys(a: str, b: str) -> None:
    assert _key(a) != _key(b)
    assert check_equivalence(a, b).verdict is Verdict.NOT_EQUIVALENT


# ---------------------------------------------------------------------------
# Terminals: tautologies and contradictions collapse to fixed keys.
# ---------------------------------------------------------------------------


def test_tautologies_collapse_to_true_terminal() -> None:
    for taut in ("P | ~P", "true", "P -> P", "(P -> Q) | (Q -> P)"):
        c = canonicalize(taut)
        assert c.is_tautology, taut
        assert c.canonical_key == "T"
        assert c.atoms == ()  # no variable survives a constant


def test_contradictions_collapse_to_false_terminal() -> None:
    for contra in ("P & ~P", "false", "P <-> ~P"):
        c = canonicalize(contra)
        assert c.is_contradiction, contra
        assert c.canonical_key == "F"
        assert c.atoms == ()


def test_distinct_tautologies_are_the_same_truth_value() -> None:
    # All tautologies are the constant-true function regardless of atoms.
    assert _key("P | ~P") == _key("Q | ~Q") == _key("true")


# ---------------------------------------------------------------------------
# Surviving atoms: irrelevant variables are dropped from the support.
# ---------------------------------------------------------------------------


def test_irrelevant_variable_is_dropped_from_support() -> None:
    c = canonicalize("P & (Q | ~Q)")
    assert c.atoms == ("P",)  # Q is logically irrelevant
    assert c.canonical_key == canonicalize("P").canonical_key


def test_substring_atoms_do_not_alias() -> None:
    # Regression guard: atom 'a' must not be confused with atom 'ba'.
    assert canonicalize("a & ba").atoms == ("a", "ba")
    assert _key("a") != _key("ba")


# ---------------------------------------------------------------------------
# Determinism: same formula -> byte-identical key (the trace-hash discipline).
# ---------------------------------------------------------------------------


def test_canonical_key_is_byte_deterministic() -> None:
    formula = "(P -> Q) & (R | ~S)"
    assert canonicalize(formula).canonical_key == canonicalize(formula).canonical_key


def test_operator_spellings_are_equivalent() -> None:
    assert _key("P and Q") == _key("P & Q") == _key("P ∧ Q") == _key("P && Q")
    assert _key("P or Q") == _key("P | Q") == _key("P ∨ Q")
    assert _key("not P") == _key("~P") == _key("¬P") == _key("!P")
    assert _key("P implies Q") == _key("P -> Q") == _key("P → Q")
    assert _key("P iff Q") == _key("P <-> Q") == _key("P ↔ Q")


# ---------------------------------------------------------------------------
# Refusal: out-of-grammar input and budget blowup REFUSE (wrong=0 discipline).
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("bad", ["", "P &", "P Q", "(P", "P)", "P @ Q", "& P"])
def test_malformed_formula_refuses(bad: str) -> None:
    with pytest.raises(LogicError):
        canonicalize(bad)
    v = check_equivalence(bad, "P")
    assert v.verdict is Verdict.REFUSED
    assert v.canonical_a is None and v.canonical_b is None


def test_budget_exceeded_refuses_rather_than_churns() -> None:
    # A wide XOR-chain is the classic ROBDD blowup case; a tiny budget must
    # trigger a typed refusal, not an unbounded build.
    formula = " <-> ".join(f"v{i}" for i in range(40))
    with pytest.raises(LogicBudgetError):
        canonicalize(formula, max_nodes=8)
    v = check_equivalence(formula, "true", max_nodes=8)
    assert v.verdict is Verdict.REFUSED
    assert "budget" in v.reason.lower()


def test_budget_error_is_a_logic_error_subclass() -> None:
    # Callers that refuse on LogicError must also refuse on budget-exceeded.
    assert issubclass(LogicBudgetError, LogicError)


def test_bounded_formula_stays_within_default_budget() -> None:
    # A realistic proof-step proposition canonicalizes well within budget.
    c = canonicalize("(P -> Q) & (Q -> R) & P", max_nodes=DEFAULT_MAX_NODES)
    assert c.canonical_key  # non-empty, did not refuse
