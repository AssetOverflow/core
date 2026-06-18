"""Tests for GSM8K train-sample sealed attempt scout (ADR-0175 S1)."""

from __future__ import annotations

import json
from pathlib import Path

from evals.gsm8k_math.runner import CaseOutcome
from evals.gsm8k_math.train_sample.v1.scout import (
    SealedAttemptScoutRow,
    build_scout_row,
    build_scout_summary,
    classify_delta_kind,
    classify_failure_family,
    render_markdown,
    score_case_dual,
)

_REPO_ROOT = Path(__file__).resolve().parents[1]
_REPORT = _REPO_ROOT / "evals/gsm8k_math/train_sample/v1/report.json"


def _outcome(
    *,
    case_id: str,
    outcome: str,
    reason: str = "",
    actual: float | None = None,
    expected: float = 0.0,
) -> CaseOutcome:
    return CaseOutcome(
        case_id=case_id,
        outcome=outcome,  # type: ignore[arg-type]
        reason=reason,
        expected_answer=expected,
        expected_unit="",
        actual_answer=actual,
        actual_unit=None,
        trace_hash=None,
        realized_prose=None,
    )


def test_delta_kind_partition():
    assert classify_delta_kind("correct", "correct") == "already_served"
    assert classify_delta_kind("correct", "refused") == "serving_conservative_win"
    assert classify_delta_kind("wrong", "correct") == "serving_wrong_sealed_correct"
    assert classify_delta_kind("wrong", "wrong") == "serving_wrong_other"
    assert classify_delta_kind("refused", "correct") == "lift_refused_to_correct"
    assert classify_delta_kind("refused", "wrong") == "elimination_refused_to_wrong"
    assert classify_delta_kind("refused", "refused") == "joint_refusal"


def test_failure_family_conservative_defaults():
    family = classify_failure_family(
        delta_kind="joint_refusal",
        served_status="refused",
        served_reason="candidate_graph: no admissible candidate for statement",
        served_bucket="no_admissible_statement",
        served_category=None,
        sealed_reason="resolve_pooled: no resolution",
    )
    assert "joint" in family


def test_lift_candidate_row_fields():
    raw = {
        "case_id": "gsm8k-train-sample-v1-0001",
        "question": "How many apples?",
        "answer_numeric": 5,
        "answer_expression": "#### 5",
    }
    served = _outcome(
        case_id=raw["case_id"],
        outcome="refused",
        reason="candidate_graph: recognizer matched but produced no injection (category=discrete_count_statement)",
        expected=5.0,
    )
    sealed = _outcome(
        case_id=raw["case_id"],
        outcome="correct",
        reason="resolve_pooled",
        actual=5.0,
        expected=5.0,
    )
    row = build_scout_row(raw, served, sealed)
    assert row.served_status == "refused"
    assert row.aggressive_status == "correct"
    assert row.candidate_lift_family is not None
    assert row.trace_key


def test_serving_wrong_boundary_family():
    family = classify_failure_family(
        delta_kind="serving_wrong_sealed_correct",
        served_status="wrong",
        served_reason="wrong answer",
        served_bucket="wrong",
        served_category=None,
        sealed_reason="resolve_pooled",
    )
    assert family == "serving_wrong_boundary"


def test_scout_summary_determinism_small_fixture():
    cases = [
        {
            "case_id": "gsm8k-train-sample-v1-9001",
            "question": "Tom has 2 apples. How many apples does Tom have?",
            "answer_numeric": 2,
            "answer_expression": "#### 2",
        }
    ]

    def serving(_adapted: dict) -> CaseOutcome:
        return _outcome(
            case_id=_adapted["id"],
            outcome="refused",
            reason="no admissible candidate for question",
            expected=float(_adapted["expected_answer"]),
        )

    def sealed(_adapted: dict) -> CaseOutcome:
        return _outcome(
            case_id=_adapted["id"],
            outcome="refused",
            reason="resolve_pooled: no resolution",
            expected=float(_adapted["expected_answer"]),
        )

    a = build_scout_summary(cases, serving_scorer=serving, sealed_scorer=sealed)
    b = build_scout_summary(cases, serving_scorer=serving, sealed_scorer=sealed)
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def test_markdown_render_is_stable():
    summary = {
        "sample_count": 1,
        "cases_source": "fixture",
        "serving_counts": {"correct": 0, "wrong": 0, "refused": 1},
        "sealed_counts": {"correct": 0, "wrong": 0, "refused": 1},
        "delta_counts": {"joint_refusal": 1},
        "lift_recommendations": [],
    }
    assert render_markdown(summary) == render_markdown(summary)


def test_live_train_sample_serving_wrong_is_zero():
    summary = build_scout_summary()
    assert summary["serving_counts"]["wrong"] == 0
    assert summary["sample_count"] == 50


def test_live_scout_summary_determinism():
    a = build_scout_summary(include_rows=False)
    b = build_scout_summary(include_rows=False)
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def test_report_json_mtime_unchanged_by_scout_import():
    before = _REPORT.stat().st_mtime_ns
    _ = SealedAttemptScoutRow
    after = _REPORT.stat().st_mtime_ns
    assert before == after


def test_injected_scorers_without_heavy_reader():
    cases = [
        {
            "case_id": "gsm8k-train-sample-v1-9002",
            "question": "A",
            "answer_numeric": 10,
            "answer_expression": "#### 10",
        }
    ]

    def serving(_adapted: dict) -> CaseOutcome:
        return _outcome(case_id=_adapted["id"], outcome="refused", expected=10.0)

    def sealed(_adapted: dict) -> CaseOutcome:
        return _outcome(
            case_id=_adapted["id"],
            outcome="correct",
            actual=10.0,
            expected=10.0,
        )

    served, sealed_out = score_case_dual(
        cases[0], serving_scorer=serving, sealed_scorer=sealed
    )
    assert served.outcome == "refused"
    assert sealed_out.outcome == "correct"