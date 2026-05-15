"""Tests for the operator calibration replay system."""

from __future__ import annotations

from calibration.params import (
    CalibrationParams,
    DEFAULT_PARAMS,
    grid_candidates,
)
from calibration.replay import replay_with_params
from calibration.tune import calibrate, CalibrationResult
from evals.run_cognition_eval import load_cases


_SMALL_CASES = None


def _get_small_cases() -> list[dict]:
    global _SMALL_CASES
    if _SMALL_CASES is None:
        _SMALL_CASES = load_cases()[:3]
    return _SMALL_CASES


class TestCalibrationReplayIsDeterministic:
    def test_same_params_same_metrics(self) -> None:
        cases = _get_small_cases()
        r1 = replay_with_params(DEFAULT_PARAMS, cases)
        r2 = replay_with_params(DEFAULT_PARAMS, cases)
        assert r1.intent_accuracy == r2.intent_accuracy
        assert r1.versor_closure_rate == r2.versor_closure_rate
        assert r1.trace_hashes == r2.trace_hashes


class TestCalibrationCandidateParamsAreBounded:
    def test_grid_produces_bounded_candidates(self) -> None:
        candidates = grid_candidates()
        assert len(candidates) > 0
        for c in candidates:
            assert 4 <= c.salience_top_k <= 32
            assert 0.1 <= c.inhibition_threshold <= 0.9

    def test_grid_is_deterministic(self) -> None:
        c1 = grid_candidates()
        c2 = grid_candidates()
        assert c1 == c2

    def test_custom_grid(self) -> None:
        custom = {"salience_top_k": (8, 16), "inhibition_threshold": (0.2,)}
        candidates = grid_candidates(custom)
        assert len(candidates) == 2
        salience_values = {c.salience_top_k for c in candidates}
        assert salience_values == {8, 16}


class TestCalibrationReportHasBeforeAfterMetrics:
    def test_calibrate_returns_result(self) -> None:
        cases = _get_small_cases()
        tiny_grid = {"salience_top_k": (12, 16), "inhibition_threshold": (0.3,)}
        result = calibrate(cases, grid=tiny_grid)
        assert isinstance(result, CalibrationResult)
        assert result.baseline_report.total == len(cases)
        assert result.best_report.total == len(cases)

    def test_report_dict_has_required_fields(self) -> None:
        cases = _get_small_cases()
        tiny_grid = {"salience_top_k": (16,), "inhibition_threshold": (0.3,)}
        result = calibrate(cases, grid=tiny_grid)
        d = result.as_dict()
        assert "baseline_params" in d
        assert "baseline_metrics" in d
        assert "best_params" in d
        assert "best_metrics" in d
        assert "candidates_evaluated" in d
        assert "candidates_accepted" in d


class TestCalibrationRejectsInvariantRegression:
    def test_versor_closure_must_not_regress(self) -> None:
        cases = _get_small_cases()
        tiny_grid = {"salience_top_k": (8, 12, 16), "inhibition_threshold": (0.2, 0.3, 0.4)}
        result = calibrate(cases, grid=tiny_grid)
        for c in result.candidates:
            if c.accepted:
                assert c.after_report.versor_closure_rate >= result.baseline_report.versor_closure_rate


class TestCalibrationDoesNotMutateIdentityOrPacks:
    def test_params_are_frozen(self) -> None:
        params = CalibrationParams()
        try:
            params.salience_top_k = 99  # type: ignore[misc]
            raise AssertionError("CalibrationParams should be frozen")
        except AttributeError:
            pass

    def test_calibration_does_not_touch_packs(self) -> None:
        import hashlib
        from pathlib import Path

        pack_dir = Path(__file__).resolve().parent.parent / "language_packs" / "data"
        before = {}
        for f in sorted(pack_dir.rglob("*.jsonl")):
            before[str(f)] = hashlib.sha256(f.read_bytes()).hexdigest()

        cases = _get_small_cases()
        tiny_grid = {"salience_top_k": (16,), "inhibition_threshold": (0.3,)}
        calibrate(cases, grid=tiny_grid)

        for f in sorted(pack_dir.rglob("*.jsonl")):
            assert before[str(f)] == hashlib.sha256(f.read_bytes()).hexdigest()
