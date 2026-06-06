"""Phase 2a-r3 — end-to-end: the comprehension reader scored on syllogism.

prose -> comprehend -> to_syllogism -> INDEPENDENT oracle -> answer vs gold.
The load-bearing invariant: wrong == 0 (the reader refuses rather than emit a
structure that yields a wrong answer). Coverage is allowed to be partial — a
refusal is honest, a wrong commit is not.
"""

from __future__ import annotations

from evals.comprehension.syllogism_runner import run


def test_comprehension_syllogism_wrong_is_zero() -> None:
    report = run()
    assert report["wrong"] == 0, report["wrongs"]


def test_comprehension_syllogism_has_real_coverage() -> None:
    report = run()
    assert report["correct"] > 0
    assert report["correct"] + report["refused"] == report["total"]


def test_comprehension_syllogism_pinned_counts() -> None:
    # Pins the lane: 6 read end-to-end (Barbara/Celarent/Darii/Ferio/Datisi +
    # the invalid undistributed-middle, which the oracle correctly rejects);
    # 2 refused — the existential-import conclusion and the multi-word-NP case.
    report = run()
    assert report["correct"] == 6
    assert report["refused"] == 2
    assert report["total"] == 8
