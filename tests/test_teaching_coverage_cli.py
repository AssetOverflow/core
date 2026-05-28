"""Brief D — coverage report aggregator tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from teaching.coverage import (
    CoverageCounts,
    _classify_refusal,
    build_coverage_report,
)


def _write_report(path: Path, *, correct: int, refused: int, wrong: int, per_case: list[dict]) -> None:
    path.write_text(
        json.dumps({
            "counts": {"correct": correct, "refused": refused, "wrong": wrong},
            "per_case": per_case,
        }),
        encoding="utf-8",
    )


def test_classify_recognizer_empty_injection():
    r = ("candidate_graph: recognizer matched but produced no injection "
         "for statement: 'X.' (category=multiplicative_aggregation)")
    assert _classify_refusal(r) == "recognizer_empty_injection(multiplicative_aggregation)"


def test_classify_no_admissible_question():
    assert _classify_refusal("candidate_graph: no admissible candidate for question: 'X?'") == "no_admissible_question"


def test_classify_no_admissible_statement():
    assert _classify_refusal("candidate_graph: no admissible candidate for statement: 'X.'") == "no_admissible_statement"


def test_classify_unknown_falls_back_to_other():
    assert _classify_refusal("some new failure mode") == "other"


def test_classify_empty_returns_other():
    assert _classify_refusal("") == "other"


def test_build_coverage_report_basic(tmp_path: Path):
    report_path = tmp_path / "report.json"
    _write_report(
        report_path,
        correct=2,
        refused=3,
        wrong=0,
        per_case=[
            {"case_id": "x-0001", "verdict": "correct"},
            {"case_id": "x-0002", "verdict": "correct"},
            {"case_id": "x-0003", "verdict": "refused", "reason": "candidate_graph: recognizer matched but produced no injection for statement: 'A.' (category=currency_amount)"},
            {"case_id": "x-0004", "verdict": "refused", "reason": "candidate_graph: recognizer matched but produced no injection for statement: 'B.' (category=currency_amount)"},
            {"case_id": "x-0005", "verdict": "refused", "reason": "candidate_graph: no admissible candidate for question: 'How?'"},
        ],
    )
    r = build_coverage_report(
        report_path, lane="t", split="s", version="v1", use_reader=True,
    )
    assert r.counts == CoverageCounts(correct=2, refused=3, wrong=0)
    assert r.counts.total() == 5
    assert dict(r.refusal_taxonomy) == {
        "recognizer_empty_injection(currency_amount)": 2,
        "no_admissible_question": 1,
    }
    assert r.case_0050_verdict is None


def test_case_0050_verdict_captured(tmp_path: Path):
    report_path = tmp_path / "report.json"
    _write_report(
        report_path,
        correct=0,
        refused=1,
        wrong=0,
        per_case=[
            {"case_id": "gsm8k-train-sample-v1-0050", "verdict": "refused", "reason": "x"},
        ],
    )
    r = build_coverage_report(
        report_path, lane="gsm8k_math", split="train_sample", version="v1", use_reader=True,
    )
    assert r.case_0050_verdict == "refused"


def test_delta_computation(tmp_path: Path):
    report_path = tmp_path / "report.json"
    baseline_path = tmp_path / "baseline.json"
    _write_report(report_path, correct=4, refused=46, wrong=0, per_case=[])
    _write_report(baseline_path, correct=3, refused=47, wrong=0, per_case=[])
    r = build_coverage_report(
        report_path,
        lane="t", split="s", version="v1", use_reader=True,
        baseline_path=baseline_path,
    )
    assert r.delta == {"correct": 1, "refused": -1, "wrong": 0}


def test_no_baseline_means_empty_delta(tmp_path: Path):
    report_path = tmp_path / "report.json"
    _write_report(report_path, correct=3, refused=47, wrong=0, per_case=[])
    r = build_coverage_report(
        report_path,
        lane="t", split="s", version="v1", use_reader=False,
        baseline_path=None,
    )
    assert r.delta == {}


def test_missing_report_raises(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        build_coverage_report(
            tmp_path / "nope.json",
            lane="t", split="s", version="v1", use_reader=False,
        )


def test_as_dict_round_trip(tmp_path: Path):
    report_path = tmp_path / "report.json"
    _write_report(report_path, correct=1, refused=1, wrong=0, per_case=[
        {"case_id": "x-0001", "verdict": "correct"},
        {"case_id": "x-0002", "verdict": "refused", "reason": "candidate_graph: recognizer matched but produced no injection for statement: 'X.' (category=discrete_count_statement)"},
    ])
    r = build_coverage_report(report_path, lane="t", split="s", version="v1", use_reader=True)
    d = r.as_dict()
    assert d["counts"]["total"] == 2
    assert "recognizer_empty_injection(discrete_count_statement)" in d["refusal_taxonomy"]
    assert d["use_reader"] is True


def test_taxonomy_sorted_by_count_desc(tmp_path: Path):
    report_path = tmp_path / "report.json"
    _write_report(report_path, correct=0, refused=4, wrong=0, per_case=[
        {"case_id": f"x-{i:04d}", "verdict": "refused", "reason": "candidate_graph: no admissible candidate for question: '?'" if i < 1 else "candidate_graph: recognizer matched but produced no injection for statement: 'X.' (category=multiplicative_aggregation)"}
        for i in range(4)
    ])
    r = build_coverage_report(report_path, lane="t", split="s", version="v1", use_reader=False)
    keys = list(r.refusal_taxonomy.keys())
    assert keys[0] == "recognizer_empty_injection(multiplicative_aggregation)"  # 3 > 1
    assert keys[1] == "no_admissible_question"


def test_wrong_zero_invariant_visible_via_as_dict(tmp_path: Path):
    report_path = tmp_path / "report.json"
    _write_report(report_path, correct=0, refused=0, wrong=2, per_case=[])
    r = build_coverage_report(report_path, lane="t", split="s", version="v1", use_reader=False)
    assert r.as_dict()["counts"]["wrong"] == 2
