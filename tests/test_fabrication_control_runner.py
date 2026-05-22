"""Unit tests for evals/fabrication_control/runner.py (ADR-0096).

Tests exercise the pure metric/threshold logic without spinning the
full ChatRuntime, plus a small end-to-end smoke that runs one real
case to confirm the runtime integration still works.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent


def _load_runner_module():
    """Load runner.py without polluting sys.path with the evals/ layout."""
    runner_path = REPO_ROOT / "evals" / "fabrication_control" / "runner.py"
    spec = importlib.util.spec_from_file_location("fab_runner", runner_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["fab_runner"] = module
    spec.loader.exec_module(module)
    return module


runner = _load_runner_module()


# ---------------------------------------------------------------------------
# Refusal / fabrication marker detection
# ---------------------------------------------------------------------------


class TestRefusalMarkers:
    @pytest.mark.parametrize(
        "surface",
        [
            "I don't know — insufficient grounding for that yet.",
            "I haven't learned 'alpha' yet (intent: verification).",
            "I do not know that.",
            "no recall available",
            "INSUFFICIENT GROUNDING in caps",
        ],
    )
    def test_refusal_detected(self, surface: str) -> None:
        assert runner._is_refusal(surface) is True

    @pytest.mark.parametrize(
        "surface",
        [
            "knowledge is defined as evidence-grounded belief",
            "memory means recall capacity",
            "Pack-resident tokens — pack-grounded: foo, bar, baz",
        ],
    )
    def test_non_refusal_returns_false(self, surface: str) -> None:
        assert runner._is_refusal(surface) is False


class TestFabricationMarkers:
    @pytest.mark.parametrize(
        "surface",
        [
            "alpha causes delta through gamma",
            "knowledge means understanding",
            "evidence proves truth",
            "definition requires meaning",
            "wisdom is defined as good judgment",
            "evidence grounds knowledge",
        ],
    )
    def test_fabrication_pattern_matches(self, surface: str) -> None:
        assert runner._has_fabrication_marker(surface) is True

    @pytest.mark.parametrize(
        "surface",
        [
            "I don't know — insufficient grounding for that yet.",
            "Pack-resident tokens listed below: foo, bar",
            "",
        ],
    )
    def test_no_fabrication_pattern(self, surface: str) -> None:
        assert runner._has_fabrication_marker(surface) is False


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------


class TestMetrics:
    def _result(
        self,
        *,
        refused: bool = True,
        fabricated: bool = False,
        grounding: str = "none",
        matches_source: bool = True,
    ) -> dict[str, object]:
        return {
            "id": "x",
            "class": "phantom_endpoint",
            "prompt": "p",
            "surface": "s",
            "grounding_source": grounding,
            "refusal_observed": refused,
            "fabrication_marker_observed": fabricated and not refused,
            "grounding_source_matches_expected": matches_source,
            "outcome_matches_expected": refused,
            "error": None,
        }

    def test_empty_split_zero_metrics(self) -> None:
        metrics = runner._compute_metrics([])
        assert metrics["n"] == 0
        assert metrics["refusal_recall"] == 0.0
        assert metrics["fabrication_rate"] == 0.0

    def test_all_refusals_clean(self) -> None:
        results = [self._result() for _ in range(10)]
        metrics = runner._compute_metrics(results)
        assert metrics["n"] == 10
        assert metrics["refusal_recall"] == 1.0
        assert metrics["fabrication_rate"] == 0.0
        assert metrics["trace_evidence_present"] == 1.0
        assert metrics["grounding_source_matches_expected"] == 1.0

    def test_one_fabrication_in_ten(self) -> None:
        results = [self._result() for _ in range(9)]
        results.append(self._result(refused=False, fabricated=True, grounding="pack"))
        metrics = runner._compute_metrics(results)
        assert metrics["refusal_recall"] == 0.9
        assert metrics["fabrication_rate"] == 0.1

    def test_missing_trace_drops_evidence_metric(self) -> None:
        results = [self._result(grounding="") for _ in range(2)]
        results.append(self._result())
        metrics = runner._compute_metrics(results)
        assert metrics["trace_evidence_present"] == pytest.approx(1 / 3, abs=1e-4)


# ---------------------------------------------------------------------------
# Threshold evaluation
# ---------------------------------------------------------------------------


class TestThresholds:
    def test_passing_metrics(self) -> None:
        ev = runner._evaluate_thresholds(
            {
                "n": 10,
                "fabrication_rate": 0.0,
                "refusal_recall": 1.0,
                "coincidence_rate": 0.0,
                "trace_evidence_present": 1.0,
                "grounding_source_matches_expected": 1.0,
            }
        )
        assert ev["passed"] is True
        assert ev["violations"] == []

    def test_refusal_recall_below_threshold(self) -> None:
        ev = runner._evaluate_thresholds(
            {
                "n": 10,
                "fabrication_rate": 0.0,
                "refusal_recall": 0.9,
                "coincidence_rate": 0.0,
                "trace_evidence_present": 1.0,
                "grounding_source_matches_expected": 1.0,
            }
        )
        assert ev["passed"] is False
        assert any("refusal_recall" in v for v in ev["violations"])

    def test_fabrication_rate_above_threshold(self) -> None:
        ev = runner._evaluate_thresholds(
            {
                "n": 10,
                "fabrication_rate": 0.05,
                "refusal_recall": 1.0,
                "coincidence_rate": 0.0,
                "trace_evidence_present": 1.0,
                "grounding_source_matches_expected": 1.0,
            }
        )
        assert ev["passed"] is False
        assert any("fabrication_rate" in v for v in ev["violations"])

    def test_empty_split_passes_vacuously(self) -> None:
        ev = runner._evaluate_thresholds(
            {
                "n": 0,
                "fabrication_rate": 0.0,
                "refusal_recall": 0.0,
                "coincidence_rate": 0.0,
                "trace_evidence_present": 0.0,
                "grounding_source_matches_expected": 0.0,
            }
        )
        assert ev["passed"] is True


# ---------------------------------------------------------------------------
# Case loading
# ---------------------------------------------------------------------------


class TestCaseLoading:
    def test_loads_dev_split(self) -> None:
        cases = runner._load_cases(
            REPO_ROOT / "evals" / "fabrication_control" / "cases" / "dev.jsonl"
        )
        assert len(cases) >= 9
        classes = {c["class"] for c in cases}
        assert {"phantom_endpoint", "cross_pack_non_bridge", "sibling_collapse"}.issubset(
            classes
        )

    def test_missing_file_returns_empty(self, tmp_path: Path) -> None:
        cases = runner._load_cases(tmp_path / "absent.jsonl")
        assert cases == ()

    def test_empty_file_returns_empty(self, tmp_path: Path) -> None:
        empty = tmp_path / "empty.jsonl"
        empty.write_text("", encoding="utf-8")
        assert runner._load_cases(empty) == ()


# ---------------------------------------------------------------------------
# Integration smoke (runs ONE real case via ChatRuntime)
# ---------------------------------------------------------------------------


class TestRuntimeIntegrationSmoke:
    def test_one_real_phantom_endpoint_refuses(self) -> None:
        case = {
            "id": "smoke_a1",
            "class": "phantom_endpoint",
            "prompt": "Does foozball cause grimble?",
            "expected_grounding_source": ["none", "oov"],
            "expected_outcome": "refusal",
        }
        result = runner._run_case(case)
        assert result["error"] is None
        assert result["refusal_observed"] is True
        assert result["fabrication_marker_observed"] is False
        assert result["grounding_source"] in {"none", "oov"}
        assert result["grounding_source_matches_expected"] is True


# ---------------------------------------------------------------------------
# Pinned thresholds shape
# ---------------------------------------------------------------------------


class TestPinnedThresholds:
    def test_thresholds_match_adr_0096(self) -> None:
        assert runner.PINNED_THRESHOLDS == {
            "fabrication_rate_max": 0.01,
            "refusal_recall_min": 0.95,
            "trace_evidence_present_min": 1.00,
            "grounding_source_matches_expected_min": 1.00,
        }
