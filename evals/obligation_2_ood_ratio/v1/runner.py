"""ADR-0114a Obligation #2 — OOD surface variation ratio runner.

Runs the OOD case set through the B3 bounded-grammar pipeline
(parser → solver → verifier) and emits a report mirroring the shape
of the B3 public runner's report.json.

All OOD cases carry ``expected == "solved_correct"`` because the OOD
set contains only surface-varied siblings of B3's solved_correct public
cases.  The runner verdict table is a subset of B3's full table:

  solved_correct + correct  → correct
  solved_correct + wrong    → wrong
  solved_correct + refused  → refused   (dataset bug if this fires)

``wrong == 0`` is a hard gate enforced by the exit code and by the
auditor in core/capability/ood_ratio.py.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from generate.math_parser import ParseError, parse_problem
from generate.math_problem_graph import MathProblemGraph
from generate.math_solver import SolveError, solve
from generate.math_verifier import verify

_HERE = Path(__file__).resolve().parent
_CASES_PATH = _HERE / "cases.jsonl"
_REPORT_PATH = _HERE / "report.json"


@dataclass(frozen=True, slots=True)
class PipelineResult:
    outcome: str  # "correct" | "wrong" | "refused"
    actual_answer: float | None
    actual_unit: str | None
    reason: str


def _run_pipeline(
    problem: str, expected_answer: float | None, expected_unit: str | None
) -> PipelineResult:
    try:
        graph: MathProblemGraph = parse_problem(problem)
    except ParseError as exc:
        return PipelineResult("refused", None, None, f"parser: {exc}")

    try:
        trace = solve(graph)
    except SolveError as exc:
        return PipelineResult("refused", None, None, f"solver: {exc}")

    verdict = verify(graph, trace)
    if not verdict.passed:
        return PipelineResult(
            "wrong",
            trace.answer_value,
            trace.answer_unit,
            f"verifier: {verdict.reason}",
        )

    if expected_answer is not None:
        if expected_unit is not None and expected_unit != "":
            if trace.answer_unit != expected_unit:
                return PipelineResult(
                    "wrong",
                    trace.answer_value,
                    trace.answer_unit,
                    f"unit mismatch: got {trace.answer_unit!r}, expected {expected_unit!r}",
                )
        if trace.answer_value != expected_answer:
            return PipelineResult(
                "wrong",
                trace.answer_value,
                trace.answer_unit,
                f"answer mismatch: got {trace.answer_value!r}, expected {expected_answer!r}",
            )

    return PipelineResult("correct", trace.answer_value, trace.answer_unit, "")


@dataclass(frozen=True, slots=True)
class CaseVerdict:
    case_id: str
    verdict: str  # "correct" | "wrong" | "refused"
    public_sibling_case_id: str
    reason: str


def score_case(case: dict[str, Any]) -> CaseVerdict:
    case_id = case["case_id"]
    problem = case["problem"]
    expected_answer = case["expected_answer"]
    expected_unit = case["expected_unit"]
    public_sibling = case.get("public_sibling_case_id", "")

    result = _run_pipeline(problem, expected_answer, expected_unit)

    if result.outcome == "correct":
        return CaseVerdict(case_id, "correct", public_sibling, "")
    elif result.outcome == "wrong":
        return CaseVerdict(case_id, "wrong", public_sibling, result.reason)
    else:
        return CaseVerdict(case_id, "refused", public_sibling, result.reason)


def build_report(cases: list[dict[str, Any]]) -> dict[str, Any]:
    verdicts = [score_case(c) for c in cases]
    total = len(verdicts)
    correct = sum(1 for v in verdicts if v.verdict == "correct")
    wrong = sum(1 for v in verdicts if v.verdict == "wrong")
    refused = sum(1 for v in verdicts if v.verdict == "refused")

    ood_accuracy = correct / total if total else 0.0
    wrong_count_is_zero = wrong == 0
    passed = wrong_count_is_zero and (ood_accuracy >= 0.95)

    metrics = {
        "cases_total": total,
        "correct": correct,
        "wrong": wrong,
        "refused": refused,
        "ood_accuracy": ood_accuracy,
        "wrong_count_is_zero": wrong_count_is_zero,
        "overall_pass": passed,
    }

    per_case = [
        {
            "case_id": v.case_id,
            "verdict": v.verdict,
            "public_sibling_case_id": v.public_sibling_case_id,
            "reason": v.reason,
        }
        for v in verdicts
    ]

    return {
        "schema_version": 1,
        "adr": "0114a.2",
        "sample_path": "evals/obligation_2_ood_ratio/v1/cases.jsonl",
        "sample_count": total,
        "metrics": metrics,
        "exit_criterion": {
            "ood_accuracy_min": 0.95,
            "wrong_max": 0,
            "passed": passed,
        },
        "per_case": per_case,
    }


def write_report(report: dict[str, Any], path: Path = _REPORT_PATH) -> None:
    path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def load_cases(path: Path = _CASES_PATH) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))
    return records


def main() -> int:
    cases = load_cases()
    report = build_report(cases)
    write_report(report)
    print(f"Metrics: {report['metrics']}")
    return 0 if report["exit_criterion"]["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
