"""Phase 2a-r3 — the comprehension reader scored on the syllogism gold lane.

Second reasoning domain (after set_membership), reusing the SAME categorical
templates via the neutral MeaningGraph — proof the reader generalizes across
distinct reasoning domains, not just content. wrong == 0 is the floor.
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
