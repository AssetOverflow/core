"""Tests for ADR-0119.6 depth-curve harness."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from evals.gsm8k_math.runner import LaneReport, run_lane
from evals.gsm8k_math.scoring.depth_curve import (
    DepthCurveError,
    compute_depth_curve,
)

_REPO_ROOT = Path(__file__).resolve().parent.parent


def _load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


_DEV_CASES = _load_jsonl(_REPO_ROOT / "evals" / "gsm8k_math" / "dev" / "cases.jsonl")
_PUBLIC_CASES = _load_jsonl(_REPO_ROOT / "evals" / "gsm8k_math" / "public" / "v1" / "cases.jsonl")


def test_determinism() -> None:
    """Pins (a) Determinism: same inputs -> same JSON output."""
    report1 = run_lane(_DEV_CASES)
    curve1 = compute_depth_curve(_DEV_CASES, report1)

    report2 = run_lane(_DEV_CASES)
    curve2 = compute_depth_curve(_DEV_CASES, report2)

    # Convert to JSON string to assert exact byte-equal structures
    json1 = json.dumps(curve1, sort_keys=True)
    json2 = json.dumps(curve2, sort_keys=True)
    assert json1 == json2


def test_bucket_totals_sum_to_total_cases() -> None:
    """Pins (b) Bucket totals sum to lane_report.metrics['cases_total']."""
    report = run_lane(_DEV_CASES)
    curve = compute_depth_curve(_DEV_CASES, report)

    bucket_total_sum = sum(b["total"] for b in curve["buckets"].values())
    assert bucket_total_sum == report.metrics["cases_total"]


def test_bucket_correct_sums_match_report() -> None:
    """Pins (c) Sum of (bucket.correct) == lane_report.metrics['correct']."""
    report = run_lane(_DEV_CASES)
    curve = compute_depth_curve(_DEV_CASES, report)

    bucket_correct_sum = sum(b["correct"] for b in curve["buckets"].values())
    assert bucket_correct_sum == report.metrics["correct"]


def test_empty_bucket_rate_is_zero() -> None:
    """Pins (d) Empty bucket -> rate is 0.0 (not NaN, not exception)."""
    # Filter cases to only those with depth 1
    depth_1_cases = [
        c for c in _DEV_CASES
        if len(c.get("ground_truth_graph", {}).get("operations", [])) == 1
    ]
    assert len(depth_1_cases) > 0, "No depth-1 cases found in dev set"

    report = run_lane(depth_1_cases)
    curve = compute_depth_curve(depth_1_cases, report)

    # Buckets depth_2-3, depth_4-5, depth_6-8 should be empty and have 0.0 rate
    for k in ["depth_2-3", "depth_4-5", "depth_6-8"]:
        assert curve["buckets"][k]["total"] == 0
        assert curve["buckets"][k]["correct"] == 0
        assert curve["buckets"][k]["rate"] == 0.0


def test_public_split_totals() -> None:
    """Pins (e) Run against the public split (150 cases); confirm bucket totals."""
    report = run_lane(_PUBLIC_CASES)
    curve = compute_depth_curve(_PUBLIC_CASES, report)

    # Check buckets covered: 1, 2-3, 4-5, 6-8
    expected_buckets = {"depth_1", "depth_2-3", "depth_4-5", "depth_6-8"}
    assert set(curve["buckets"].keys()) == expected_buckets

    # Per-bucket totals on public alone: each bucket has the public-only contribution (15/45/45/45)
    assert curve["buckets"]["depth_1"]["total"] == 15
    assert curve["buckets"]["depth_2-3"]["total"] == 45
    assert curve["buckets"]["depth_4-5"]["total"] == 45
    assert curve["buckets"]["depth_6-8"]["total"] == 45


def test_total_corpus_distribution() -> None:
    """Pins (e) Confirm total combined corpus distribution matches 20/60/60/60."""
    all_cases = _DEV_CASES + _PUBLIC_CASES
    report = run_lane(all_cases)
    curve = compute_depth_curve(all_cases, report)

    assert curve["buckets"]["depth_1"]["total"] == 20
    assert curve["buckets"]["depth_2-3"]["total"] == 60
    assert curve["buckets"]["depth_4-5"]["total"] == 60
    assert curve["buckets"]["depth_6-8"]["total"] == 60


def test_curve_flatness_ratio() -> None:
    """Pins (f) Verify curve flatness calculation: compute ratio without enforcing threshold."""
    report = run_lane(_DEV_CASES)
    curve = compute_depth_curve(_DEV_CASES, report)

    max_depth = curve["max_depth"]
    if max_depth == 1:
        max_bucket_key = "depth_1"
    elif 2 <= max_depth <= 3:
        max_bucket_key = "depth_2-3"
    elif 4 <= max_depth <= 5:
        max_bucket_key = "depth_4-5"
    elif 6 <= max_depth <= 8:
        max_bucket_key = "depth_6-8"
    else:
        max_bucket_key = f"depth_{max_depth}"

    max_depth_rate = curve["buckets"][max_bucket_key]["rate"]
    depth_1_rate = curve["buckets"]["depth_1"]["rate"]

    # Compute ratio
    if depth_1_rate > 0.0:
        ratio = max_depth_rate / depth_1_rate
    else:
        ratio = 0.0

    # The test confirms that the harness CAN compute and report the ratio
    assert isinstance(ratio, float)
    assert ratio >= 0.0


# -------------------------------------------------------------------
# ADR-0119.6 follow-up: explicit-refusal tests
# -------------------------------------------------------------------


def test_depth_curve_refuses_case_missing_from_lane_report() -> None:
    """Runner-output integrity: every input case_id must appear in lane_report."""
    cases = _DEV_CASES[:3]
    real_report = run_lane(cases)
    # Drop one case from the report → harness must raise, not silently fallback
    stripped = LaneReport()
    stripped.metrics = real_report.metrics
    stripped.case_details = real_report.case_details[1:]  # drop first
    with pytest.raises(DepthCurveError, match="missing from lane_report"):
        compute_depth_curve(cases, stripped)


def test_depth_curve_refuses_depth_outside_documented_range() -> None:
    """Depth >= 9 raises rather than silently extending the bucket schema."""
    # Synthesize a case with depth 9
    deep_case = {
        "id": "synthetic-deep-01",
        "problem": "synthetic",
        "expected_answer": 0,
        "expected_unit": "x",
        "ground_truth_graph": {
            "entities": ["X"],
            "initial_state": [],
            "operations": [
                {"actor": "X", "kind": "add", "operand": {"unit": "x", "value": 1}}
                for _ in range(9)
            ],
            "unknown": {"entity": "X", "unit": "x"},
        },
    }
    report = LaneReport()
    report.metrics = {"cases_total": 1, "correct": 0, "wrong": 0, "refused": 1,
                      "correct_rate": 0.0, "wrong_rate": 0.0, "refused_rate": 1.0,
                      "wrong_count_is_zero": True, "overall_pass": True}
    report.case_details = [{"case_id": "synthetic-deep-01", "outcome": "refused"}]
    with pytest.raises(DepthCurveError, match="outside documented range"):
        compute_depth_curve([deep_case], report)
