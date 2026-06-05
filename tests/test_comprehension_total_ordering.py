"""Phase 2a-r3 — the comprehension reader scored on the total_ordering gold lane.

Third reasoning domain. Comparatives carry DIRECTION; a reversed direction would
flip the sort, so wrong==0 here also proves the direction map is correct on every
committed answer.
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
