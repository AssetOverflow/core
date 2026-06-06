"""Phase 2b — end-to-end: the comprehension reader scored on relational_metric.

prose -> comprehend_quantitative -> binding_graph -> to_relational_metric ->
INDEPENDENT arithmetic oracle -> answer vs gold. The load-bearing invariant:
wrong == 0. This is the binding-graph's first comprehension consumer; quantities
are admissibility-checked (never stamped), then projected to the oracle.
"""

from __future__ import annotations

from evals.comprehension.relational_metric_runner import run


def test_comprehension_relational_metric_wrong_is_zero() -> None:
    report = run()
    assert report["wrong"] == 0, report["wrongs"]


def test_comprehension_relational_metric_has_real_coverage() -> None:
    report = run()
    assert report["correct"] > 0
    assert report["correct"] + report["refused"] == report["total"]


def test_comprehension_relational_metric_full_coverage() -> None:
    # The whole 15-case lane reads end-to-end (fact / more_than / fewer_than /
    # sum_of, single + chained, count nouns -> item dimension, dollars -> money).
    report = run()
    assert report["refused"] == 0
    assert report["correct"] == report["total"]
