"""Phase 2b — end-to-end: the comprehension reader scored on propositional_logic.

prose -> comprehend -> to_deductive_logic -> INDEPENDENT ROBDD oracle -> verdict vs
gold. The load-bearing invariant: wrong == 0 (the reader refuses rather than emit a
formula that yields a wrong verdict). This lane reads the classic propositional
argument forms (modus ponens/tollens, hypothetical & disjunctive syllogism) and the
classic fallacies (affirming the consequent, denying the antecedent), which the
oracle correctly marks ``unknown``.
"""

from __future__ import annotations

from evals.comprehension.propositional_runner import run


def test_comprehension_propositional_wrong_is_zero() -> None:
    report = run()
    assert report["wrong"] == 0, report["wrongs"]


def test_comprehension_propositional_has_real_coverage() -> None:
    report = run()
    assert report["correct"] > 0
    assert report["correct"] + report["refused"] == report["total"]


def test_comprehension_propositional_full_coverage() -> None:
    # Every staged case is read end-to-end with zero wrong commits — atoms are
    # single tokens / reserved-free multi-word NPs, so chunking is unambiguous.
    report = run()
    assert report["refused"] == 0
    assert report["correct"] == report["total"]
