"""ADR-0054 (Part 1) — holdout split wired into the official eval runner.

Contracts pinned here:

  - ``LaneInfo.holdout_cases_path`` resolves the holdout plaintext file
    via a fixed priority (cases.jsonl > cases_plaintext.jsonl > v1/cases.jsonl).
  - ``framework.run_lane(split="holdout")`` reads that path and runs the
    lane's runner like any other split.
  - The cognition lane reports a stable holdout metric set (case count,
    intent_accuracy, surface_groundedness, versor_closure_rate).
  - Unknown ``split`` values raise ``ValueError`` with a message naming
    all three accepted values.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from evals.framework import LaneInfo, get_lane, run_lane


# ---------------------------------------------------------------------------
# LaneInfo.holdout_cases_path resolution
# ---------------------------------------------------------------------------


def test_cognition_holdout_path_resolves_to_plaintext() -> None:
    lane = get_lane("cognition")
    path = lane.holdout_cases_path()
    assert path.exists()
    assert path.name == "cases_plaintext.jsonl"


def test_holdout_path_resolution_prefers_cases_jsonl(tmp_path: Path) -> None:
    root = tmp_path / "fake_lane"
    (root / "holdouts" / "v1").mkdir(parents=True)
    (root / "holdouts" / "cases.jsonl").write_text("{}\n")
    (root / "holdouts" / "cases_plaintext.jsonl").write_text("{}\n")
    (root / "holdouts" / "v1" / "cases.jsonl").write_text("{}\n")
    lane = LaneInfo(name="fake_lane", root=root, versions=("v1",))
    assert lane.holdout_cases_path().name == "cases.jsonl"
    assert lane.holdout_cases_path().parent.name == "holdouts"


def test_holdout_path_falls_back_to_plaintext_then_versioned(tmp_path: Path) -> None:
    root = tmp_path / "fake_lane"
    (root / "holdouts" / "v1").mkdir(parents=True)
    (root / "holdouts" / "cases_plaintext.jsonl").write_text("{}\n")
    (root / "holdouts" / "v1" / "cases.jsonl").write_text("{}\n")
    lane = LaneInfo(name="fake_lane", root=root, versions=("v1",))
    assert lane.holdout_cases_path().name == "cases_plaintext.jsonl"


def test_holdout_path_when_nothing_exists_returns_versioned_path(tmp_path: Path) -> None:
    root = tmp_path / "fake_lane"
    (root / "holdouts" / "v1").mkdir(parents=True)
    lane = LaneInfo(name="fake_lane", root=root, versions=("v1",))
    path = lane.holdout_cases_path()
    assert path.name == "cases.jsonl"
    assert path.parent.name == "v1"
    assert not path.exists()


# ---------------------------------------------------------------------------
# framework.run_lane(split="holdout")
# ---------------------------------------------------------------------------


def test_run_lane_holdout_runs_full_cognition_set() -> None:
    lane = get_lane("cognition")
    result = run_lane(lane, split="holdout")
    assert result.lane == "cognition"
    assert result.split == "holdout"
    assert result.metrics["total"] == 19


def test_run_lane_holdout_returns_expected_metric_keys() -> None:
    lane = get_lane("cognition")
    result = run_lane(lane, split="holdout")
    expected = {
        "total",
        "intent_accuracy",
        "term_capture_rate",
        "surface_groundedness",
        "versor_closure_rate",
    }
    assert expected.issubset(result.metrics.keys())


def test_run_lane_holdout_versor_closure_preserved() -> None:
    """The non-negotiable field invariant (versor_condition < 1e-6) must
    hold on every holdout case — same gate as dev/public."""
    lane = get_lane("cognition")
    result = run_lane(lane, split="holdout")
    assert result.metrics["versor_closure_rate"] == 1.0


def test_run_lane_unknown_split_lists_all_three_values() -> None:
    lane = get_lane("cognition")
    with pytest.raises(ValueError) as excinfo:
        run_lane(lane, split="train")
    msg = str(excinfo.value)
    assert "dev" in msg
    assert "public" in msg
    assert "holdout" in msg


# ---------------------------------------------------------------------------
# Holdout vs dev/public — consistent eval interface
# ---------------------------------------------------------------------------


def test_holdout_dev_public_share_metric_schema() -> None:
    lane = get_lane("cognition")
    dev = run_lane(lane, split="dev").metrics
    public = run_lane(lane, split="public").metrics
    holdout = run_lane(lane, split="holdout").metrics
    assert set(dev.keys()) == set(public.keys()) == set(holdout.keys())


def test_holdout_cases_have_required_fields() -> None:
    lane = get_lane("cognition")
    path = lane.holdout_cases_path()
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        case = json.loads(line)
        assert "id" in case
        assert "prompt" in case
        assert "expected_intent" in case
