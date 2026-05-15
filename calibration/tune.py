"""Deterministic grid-search calibration over bounded parameter sets."""

from __future__ import annotations

from dataclasses import dataclass

from calibration.params import CalibrationParams, DEFAULT_PARAMS, grid_candidates
from calibration.replay import replay_with_params
from evals.metrics import EvalReport


@dataclass(frozen=True, slots=True)
class CalibrationCandidate:
    params: CalibrationParams
    before_report: EvalReport
    after_report: EvalReport
    accepted: bool
    rejection_reason: str | None = None

    def improvement(self) -> float:
        return self.after_report.intent_accuracy - self.before_report.intent_accuracy


@dataclass(frozen=True, slots=True)
class CalibrationResult:
    baseline_params: CalibrationParams
    baseline_report: EvalReport
    candidates: tuple[CalibrationCandidate, ...]
    best_params: CalibrationParams
    best_report: EvalReport

    def as_dict(self) -> dict:
        return {
            "baseline_params": self.baseline_params.as_dict(),
            "baseline_metrics": {
                "intent_accuracy": round(self.baseline_report.intent_accuracy, 4),
                "versor_closure_rate": round(self.baseline_report.versor_closure_rate, 4),
                "surface_groundedness": round(self.baseline_report.surface_groundedness, 4),
            },
            "best_params": self.best_params.as_dict(),
            "best_metrics": {
                "intent_accuracy": round(self.best_report.intent_accuracy, 4),
                "versor_closure_rate": round(self.best_report.versor_closure_rate, 4),
                "surface_groundedness": round(self.best_report.surface_groundedness, 4),
            },
            "candidates_evaluated": len(self.candidates),
            "candidates_accepted": sum(1 for c in self.candidates if c.accepted),
        }


def _score(report: EvalReport) -> float:
    """Composite score: intent accuracy + versor closure + surface groundedness."""
    return (
        report.intent_accuracy
        + report.versor_closure_rate
        + report.surface_groundedness
    ) / 3.0


def calibrate(
    cases: list[dict] | None = None,
    baseline: CalibrationParams = DEFAULT_PARAMS,
    grid: dict[str, tuple] | None = None,
) -> CalibrationResult:
    """Run deterministic grid-search calibration.

    1. Evaluate baseline params
    2. For each candidate in the grid, evaluate and compare
    3. Accept only if no invariant regression (versor closure stays 100%)
    4. Return the best accepted candidate
    """
    baseline_report = replay_with_params(baseline, cases)
    baseline_score = _score(baseline_report)

    candidates_list: list[CalibrationCandidate] = []
    best_params = baseline
    best_report = baseline_report
    best_score = baseline_score

    for params in grid_candidates(grid, baseline):
        report = replay_with_params(params, cases)

        rejection_reason = None
        accepted = True

        if report.versor_closure_rate < baseline_report.versor_closure_rate:
            accepted = False
            rejection_reason = "versor closure regression"

        score = _score(report)
        if accepted and score <= baseline_score:
            accepted = False
            rejection_reason = "no composite improvement"

        candidate = CalibrationCandidate(
            params=params,
            before_report=baseline_report,
            after_report=report,
            accepted=accepted,
            rejection_reason=rejection_reason,
        )
        candidates_list.append(candidate)

        if accepted and score > best_score:
            best_params = params
            best_report = report
            best_score = score

    return CalibrationResult(
        baseline_params=baseline,
        baseline_report=baseline_report,
        candidates=tuple(candidates_list),
        best_params=best_params,
        best_report=best_report,
    )
