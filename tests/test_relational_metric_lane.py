"""Relational-metric gold lane — the field reader is wrong==0 vs an independent gold.

This is measurement #1 of the field-reasoner wedge falsifiable experiment: does the
geometric field reader, reading problem TEXT, commit answers that match an
independent arithmetic oracle (computed from the STRUCTURE) with zero wrong? The
oracle shares no code with the reader (enforced structurally by INV-25's
INDEPENDENT_GOLD_LANES registration).
"""

from __future__ import annotations

from evals.relational_metric.runner import run


def test_lane_is_wrong_zero_with_independent_gold():
    report = run()
    # The committed gold is reproducible by the independent oracle (never field-derived).
    assert report["gold_integrity_failures"] == [], report["gold_integrity_failures"]
    # wrong==0 is the prime directive on this lane.
    assert report["wrong"] == 0, report["wrong_detail"]
    # Buckets account for every case.
    assert report["total"] == report["correct"] + report["wrong"] + report["refused"]


def test_field_actually_commits_not_a_refusal_floor():
    """A refusal floor (refuse everything) would be wrong==0 too — and worthless.
    The capability claim is COVERAGE with wrong==0: the field must commit real cases."""
    report = run()
    assert report["correct"] >= 10


def test_over_ceiling_is_refused_not_wrong():
    """The precision ceiling is honest coverage (a refusal), never a wrong commit."""
    report = run()
    assert any("over_ceiling" in r for r in report["refused_detail"])
