"""ADR-0114a Obligation #6 — depth-curve auditor tests.

Pins the invariants:
  - bucket schema is closed (depth_1, depth_2-3, depth_4-5, depth_6-8);
    depth > 8 raises rather than silently extending
  - decay-bound formula uses representative_depth = min(bucket), epsilon = 0.05
  - depth_1 is the anchor (no bound check on itself)
  - missing cases file refuses cleanly
  - coverage_sufficient distinguishes vacuous-pass from meaningful-pass
  - report is deterministic + artifact byte-equal
  - snapshot: current main's B3 lane has assertion_holds=True
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.capability.depth_curve import (
    BUCKET_SCHEMA,
    DECAY_EPSILON,
    MIN_BUCKETS_FOR_COVERAGE,
    MIN_CASES_PER_BUCKET_FOR_COVERAGE,
    DepthCurveError,
    _depth_to_bucket,
    _representative_depth,
    _required_bound,
    emit_depth_curve_report,
    evaluate_depth_curve,
)


# ---------------------------------------------------------------------------
# Bucket schema + classification
# ---------------------------------------------------------------------------


def test_bucket_schema_is_closed() -> None:
    assert BUCKET_SCHEMA == ("depth_1", "depth_2-3", "depth_4-5", "depth_6-8")


@pytest.mark.parametrize(
    "depth, bucket",
    [
        (1, "depth_1"),
        (2, "depth_2-3"),
        (3, "depth_2-3"),
        (4, "depth_4-5"),
        (5, "depth_4-5"),
        (6, "depth_6-8"),
        (7, "depth_6-8"),
        (8, "depth_6-8"),
    ],
)
def test_depth_to_bucket_classifies_correctly(depth, bucket) -> None:
    assert _depth_to_bucket(depth) == bucket


@pytest.mark.parametrize("depth", [9, 10, 100])
def test_depth_to_bucket_raises_for_depth_out_of_range(depth) -> None:
    with pytest.raises(DepthCurveError) as exc:
        _depth_to_bucket(depth)
    assert "outside documented" in str(exc.value).lower()


# ---------------------------------------------------------------------------
# Decay bound math
# ---------------------------------------------------------------------------


def test_epsilon_pinned() -> None:
    assert DECAY_EPSILON == 0.05


def test_required_bound_at_depth_1_equals_anchor() -> None:
    # depth_1 representative_depth = 1; bound = anchor * 0.95^0 = anchor.
    assert _required_bound(1.0, 1) == 1.0
    assert _required_bound(0.95, 1) == 0.95


def test_required_bound_decays_at_higher_depths() -> None:
    anchor = 1.0
    # depth_2-3 → representative 2 → bound = 0.95^1 = 0.95
    assert _required_bound(anchor, 2) == pytest.approx(0.95)
    # depth_4-5 → representative 4 → bound = 0.95^3 = 0.857375
    assert _required_bound(anchor, 4) == pytest.approx(0.857375)
    # depth_6-8 → representative 6 → bound = 0.95^5 = 0.7737809375
    assert _required_bound(anchor, 6) == pytest.approx(0.7737809375)


def test_representative_depth_uses_minimum_of_each_bucket() -> None:
    """The convention is permissive: representative depth = min of
    each bucket. Changing this requires an ADR amendment because it
    tightens the bound."""
    assert _representative_depth("depth_1") == 1
    assert _representative_depth("depth_2-3") == 2
    assert _representative_depth("depth_4-5") == 4
    assert _representative_depth("depth_6-8") == 6


# ---------------------------------------------------------------------------
# Coverage-sufficient policy
# ---------------------------------------------------------------------------


def test_coverage_thresholds_pinned() -> None:
    assert MIN_BUCKETS_FOR_COVERAGE == 2
    assert MIN_CASES_PER_BUCKET_FOR_COVERAGE == 3


# ---------------------------------------------------------------------------
# Lane evaluation
# ---------------------------------------------------------------------------


def test_evaluate_b3_assertion_holds_today() -> None:
    """The load-bearing snapshot: current main's B3 lane satisfies the
    decay bound on every populated bucket (mechanism wired + assertion
    holds, possibly vacuously)."""
    r = evaluate_depth_curve()
    assert r.obligation_6_mechanism_wired is True
    assert r.obligation_6_assertion_holds is True, (
        f"obligation #6 assertion failed: {r.refusal_reason}\n"
        f"buckets: {[(b.bucket, b.cases_total, b.accuracy, b.bound_required, b.bound_satisfied) for b in r.buckets]}"
    )


def test_evaluate_b3_populates_at_least_depth_1() -> None:
    r = evaluate_depth_curve()
    assert "depth_1" in r.populated_buckets
    by_id = {b.bucket: b for b in r.buckets}
    assert by_id["depth_1"].cases_total > 0
    # depth_1 is the anchor — its bound_required is always None.
    assert by_id["depth_1"].bound_required is None


def test_evaluate_refuses_on_missing_cases(tmp_path: Path) -> None:
    r = evaluate_depth_curve(cases_path=tmp_path / "missing.jsonl")
    assert r.obligation_6_mechanism_wired is False
    assert r.obligation_6_assertion_holds is False
    assert "not found" in r.refusal_reason.lower()


# ---------------------------------------------------------------------------
# Coverage-sufficient vs vacuous-pass distinction
# ---------------------------------------------------------------------------


def test_b3_today_is_coverage_insufficient(tmp_path: Path) -> None:
    """Current B3 v1 has 21 depth-1 cases and 1 depth-2 case. The
    assertion holds (1.0 >= 0.95) but coverage is insufficient (only
    2 buckets populated, depth_2-3 has < 3 cases). This is honest
    disclosure — the obligation's mechanism is wired and the bound
    holds wherever it's evaluated; the case set just needs deeper
    coverage to make the assertion statistically meaningful. The
    failing condition is a B3-owner concern (case authoring), not a
    depth-curve auditor concern (mechanism)."""
    r = evaluate_depth_curve()
    # The two facts that together describe the current state:
    assert r.obligation_6_assertion_holds is True
    assert r.coverage_sufficient is False
    # The refusal_reason should explain why coverage is insufficient,
    # not claim the assertion failed.
    assert "coverage insufficient" in r.refusal_reason


def test_coverage_sufficient_requires_min_buckets_and_min_cases(tmp_path: Path) -> None:
    """Synthetic fixture: 5 single-statement cases + 5 two-statement
    cases — should populate depth_1 (5 cases) and depth_2-3 (5 cases),
    both meeting the per-bucket minimum, and 2 buckets populated.
    """
    cases_file = tmp_path / "synthetic.jsonl"
    rows = []
    # depth_1: 1-op (initial + one operation)
    for i in range(5):
        rows.append(json.dumps({
            "case_id": f"d1-{i:03d}",
            "problem": f"Sam has {5 + i} apples. Sam buys 2 apples. How many apples does Sam have?",
            "expected": "solved_correct",
            "expected_answer": float(5 + i + 2),
            "expected_unit": "apples",
        }))
    # depth_2-3: 2-op (initial + two operations)
    for i in range(5):
        rows.append(json.dumps({
            "case_id": f"d2-{i:03d}",
            "problem": (
                f"Sam has {5 + i} apples. Sam buys 2 apples. "
                f"Sam loses 1 apple. How many apples does Sam have?"
            ),
            "expected": "solved_correct",
            "expected_answer": float(5 + i + 2 - 1),
            "expected_unit": "apples",
        }))
    cases_file.write_text("\n".join(rows) + "\n", encoding="utf-8")

    r = evaluate_depth_curve(lane_id="synthetic", cases_path=cases_file)
    assert r.obligation_6_mechanism_wired is True
    assert r.obligation_6_assertion_holds is True
    assert r.coverage_sufficient is True
    # depth_1 + depth_2-3 must both be populated.
    assert "depth_1" in r.populated_buckets
    assert "depth_2-3" in r.populated_buckets


# ---------------------------------------------------------------------------
# Determinism + artifact byte-equality
# ---------------------------------------------------------------------------


def test_report_is_deterministic() -> None:
    r1 = evaluate_depth_curve()
    r2 = evaluate_depth_curve()
    assert json.dumps(r1.as_dict(), sort_keys=True) == json.dumps(r2.as_dict(), sort_keys=True)


def test_artifact_emission_byte_equal(tmp_path: Path) -> None:
    r = evaluate_depth_curve()
    out1 = tmp_path / "r1.json"
    out2 = tmp_path / "r2.json"
    emit_depth_curve_report(r, out1)
    emit_depth_curve_report(r, out2)
    assert out1.read_bytes() == out2.read_bytes()
