"""Phase 2a-r3 — end-to-end: the comprehension reader scored on total_ordering.

prose -> comprehend -> to_total_ordering -> INDEPENDENT oracle -> answer vs gold.
The load-bearing invariant: wrong == 0 (the reader refuses rather than emit a
structure that yields a wrong answer). Coverage is allowed to be partial — a
refusal is honest, a wrong commit is not.
"""

from __future__ import annotations

from evals.comprehension.total_ordering_runner import run


def test_comprehension_total_ordering_wrong_is_zero() -> None:
    report = run()
    assert report["wrong"] == 0, report["wrongs"]


def test_comprehension_total_ordering_has_real_coverage() -> None:
    report = run()
    assert report["correct"] > 0
    assert report["correct"] + report["refused"] == report["total"]


def test_comprehension_total_ordering_pinned_counts() -> None:
    # Pins the lane: 7 read end-to-end — two sort chains, two transitive compares,
    # and the three multi-word cases ("North station", "Red rank", "Level one…")
    # now chunked by the canonicalization contract; 1 refused — the compare with a
    # trailing prepositional phrase ("…in the same order").
    report = run()
    assert report["correct"] == 7
    assert report["refused"] == 1
    assert report["total"] == 8
