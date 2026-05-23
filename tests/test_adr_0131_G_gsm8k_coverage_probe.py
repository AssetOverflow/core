"""ADR-0131.G — GSM8K coverage probe contract tests.

Pins the invariants that every iteration (G.1, G.2, ...) must
preserve. These tests fail loudly if a future grammar expansion
relaxes the safety rail or stops emitting typed refusals.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from evals.gsm8k_math.train_sample.v1.run_coverage_probe import (
    _adapt_case,
    build_report,
    write_report,
)


_LANE_ROOT = (
    Path(__file__).resolve().parent.parent
    / "evals" / "gsm8k_math" / "train_sample" / "v1"
)
_CASES_PATH = _LANE_ROOT / "cases.jsonl"
_REPORT_PATH = _LANE_ROOT / "train_sample_coverage_report.json"


# ---------------------------------------------------------------------------
# Adapter purity
# ---------------------------------------------------------------------------


def test_adapt_case_is_pure_function() -> None:
    raw = {
        "case_id": "gsm8k-train-sample-v1-9999",
        "question": "Sam has 5 apples.",
        "answer_numeric": 5,
        "extra": "ignored",
    }
    a = _adapt_case(raw)
    b = _adapt_case(raw)
    assert a == b
    assert a == {
        "id": "gsm8k-train-sample-v1-9999",
        "problem": "Sam has 5 apples.",
        "expected_answer": 5.0,
        "expected_unit": "",
    }
    # input untouched
    assert "id" not in raw and "problem" not in raw


# ---------------------------------------------------------------------------
# Safety rail — the non-negotiable invariant
# ---------------------------------------------------------------------------


def test_admitted_wrong_is_zero() -> None:
    """``wrong == 0`` is the gate. If a future grammar expansion
    confabulates an answer rather than refusing, this test fails
    and the expansion must be reverted."""
    report = build_report()
    assert report["metrics"]["admitted_wrong"] == 0, (
        "safety rail violated: a confabulated answer reached the "
        "verifier. Revert the most recent grammar expansion."
    )
    assert report["metrics"]["safety_rail_intact"] is True


def test_every_refused_case_has_typed_reason() -> None:
    """Refusal must be first-class with a non-empty typed reason.
    Empty refusal reasons indicate a crash-shaped failure path
    that escaped typed error handling."""
    report = build_report()
    for case in report["per_case"]:
        if case["outcome"] == "refused":
            assert isinstance(case["reason"], str)
            assert case["reason"].strip(), (
                f"case {case['case_id']} refused with empty reason"
            )


def test_per_case_outcomes_are_in_closed_vocabulary() -> None:
    report = build_report()
    allowed = {"correct", "wrong", "refused"}
    for case in report["per_case"]:
        assert case["outcome"] in allowed, case


# ---------------------------------------------------------------------------
# Deterministic replay
# ---------------------------------------------------------------------------


def test_report_is_deterministic_across_runs() -> None:
    a = build_report()
    b = build_report()
    assert (
        json.dumps(a, sort_keys=True)
        == json.dumps(b, sort_keys=True)
    )


def test_committed_report_matches_current_run(tmp_path: Path) -> None:
    """The report committed to the repo must match what the script
    produces from the current cases.jsonl. If this fails, either
    re-run the probe and commit the new report, or revert the
    cases.jsonl change."""
    if not _REPORT_PATH.exists():
        pytest.skip("baseline report not committed yet")
    committed = json.loads(_REPORT_PATH.read_text(encoding="utf-8"))
    fresh = build_report()
    assert (
        json.dumps(committed, sort_keys=True)
        == json.dumps(fresh, sort_keys=True)
    )


# ---------------------------------------------------------------------------
# Schema shape
# ---------------------------------------------------------------------------


def test_report_schema_required_fields() -> None:
    report = build_report()
    required_top = {
        "schema_version", "adr", "probe", "sample_path",
        "metrics", "refused_reasons_top", "per_case",
    }
    assert required_top.issubset(report.keys())
    required_metrics = {
        "cases_total", "admitted_solved", "admitted_wrong",
        "refused", "admission_rate", "wrong_rate", "refused_rate",
        "wrong_count_is_zero", "safety_rail_intact",
    }
    assert required_metrics.issubset(report["metrics"].keys())


def test_refused_reasons_top_is_sorted_by_count_desc() -> None:
    report = build_report()
    counts = [r["count"] for r in report["refused_reasons_top"]]
    assert counts == sorted(counts, reverse=True)
