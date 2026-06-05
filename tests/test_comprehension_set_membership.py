"""Phase 2a-r2 — end-to-end: the comprehension reader scored on set_membership.

prose -> comprehend -> project -> INDEPENDENT oracle -> answer vs gold.
The load-bearing invariant: wrong == 0 (the reader refuses rather than emit a
structure that yields a wrong answer). Coverage (correct/total) is reported but
is allowed to be partial — refusal is honest, a wrong commit is not.
"""

from __future__ import annotations

from evals.comprehension.set_membership_runner import run


def test_comprehension_set_membership_wrong_is_zero() -> None:
    report = run()
    assert report["wrong"] == 0, report["wrongs"]


def test_comprehension_set_membership_has_real_coverage() -> None:
    report = run()
    # Real, non-trivial comprehension — not just refuse-everything.
    assert report["correct"] > 0
    assert report["correct"] + report["refused"] == report["total"]


def test_comprehension_set_membership_full_coverage() -> None:
    # This increment covers the whole v1 lane (member / subset / both query forms,
    # definite-NP, irregular plurals) with zero wrong commits.
    report = run()
    assert report["refused"] == 0
    assert report["correct"] == report["total"]
