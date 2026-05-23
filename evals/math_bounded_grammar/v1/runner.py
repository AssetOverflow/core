"""ADR-0131.3 — Bounded-grammar word-problem runner.

Feeds curated cases from cases.jsonl through the parser → solver → verifier
pipeline, mapping the pipeline outcomes to runner verdicts:

| Case expected | Pipeline outcome | Runner verdict | Reason |
|---|---|---|---|
| solved_correct | correct | correct | Matches expectation |
| solved_correct | wrong | wrong | Pipeline produced wrong answer |
| solved_correct | refused | refused | Pipeline refused valid grammar case |
| solved_wrong | wrong | correct | Pipeline correctly caught deliberately wrong expected answer |
| solved_wrong | correct | wrong | Pipeline failed to catch wrong expected answer |
| solved_wrong | refused | refused | Pipeline refused valid grammar case |
| refused | refused | correct | Pipeline correctly refused out-of-grammar case |
| refused | correct | wrong | Pipeline failed to refuse out-of-grammar case (silently solved) |
| refused | wrong | wrong | Pipeline failed to refuse out-of-grammar case (silently wrong) |

Ensures wrong == 0 is preserved as a hard correctness firewall.
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
    # 1. Parse
    try:
        graph: MathProblemGraph = parse_problem(problem)
    except ParseError as exc:
        return PipelineResult("refused", None, None, f"parser: {exc}")

    # 2. Solve
    try:
        trace = solve(graph)
    except SolveError as exc:
        return PipelineResult("refused", None, None, f"solver: {exc}")

    # 3. Verify
    verdict = verify(graph, trace)
    if not verdict.passed:
        return PipelineResult(
            "wrong",
            trace.answer_value,
            trace.answer_unit,
            f"verifier: {verdict.reason}",
        )

    # 4. Compare against expected (if expected values are present)
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

    return PipelineResult(
        "correct", trace.answer_value, trace.answer_unit, ""
    )


@dataclass(frozen=True, slots=True)
class CaseVerdict:
    case_id: str
    verdict: str  # "correct" | "wrong" | "refused"
    reason: str


def score_case(case: dict[str, Any]) -> CaseVerdict:
    case_id = case["case_id"]
    problem = case["problem"]
    expected_outcome = case["expected"]
    expected_answer = case["expected_answer"]
    expected_unit = case["expected_unit"]

    result = _run_pipeline(problem, expected_answer, expected_unit)

    if expected_outcome == "solved_correct":
        if result.outcome == "correct":
            return CaseVerdict(case_id, "correct", "")
        elif result.outcome == "wrong":
            return CaseVerdict(case_id, "wrong", result.reason)
        else:
            return CaseVerdict(case_id, "refused", result.reason)

    elif expected_outcome == "solved_wrong":
        if result.outcome == "wrong":
            # Correctly caught wrong answer
            return CaseVerdict(case_id, "correct", "")
        elif result.outcome == "correct":
            # Failed to catch wrong answer
            return CaseVerdict(
                case_id,
                "wrong",
                "pipeline solved successfully but expected answer was deliberately wrong",
            )
        else:
            return CaseVerdict(case_id, "refused", result.reason)

    elif expected_outcome == "refused":
        if result.outcome == "refused":
            # Correctly refused
            return CaseVerdict(case_id, "correct", "")
        else:
            # Failed to refuse
            return CaseVerdict(
                case_id,
                "wrong",
                f"pipeline outcome was {result.outcome!r} but expected refusal",
            )

    else:
        return CaseVerdict(
            case_id, "wrong", f"unknown expected outcome: {expected_outcome!r}"
        )


def build_report(cases: list[dict[str, Any]]) -> dict[str, Any]:
    verdicts = [score_case(c) for c in cases]
    total = len(verdicts)
    correct = sum(1 for v in verdicts if v.verdict == "correct")
    wrong = sum(1 for v in verdicts if v.verdict == "wrong")
    refused = sum(1 for v in verdicts if v.verdict == "refused")

    correct_rate = correct / total if total else 0.0
    wrong_count_is_zero = wrong == 0
    passed = wrong_count_is_zero and (correct_rate >= 0.95)

    metrics = {
        "cases_total": total,
        "correct": correct,
        "wrong": wrong,
        "refused": refused,
        "correct_rate": correct_rate,
        "wrong_count_is_zero": wrong_count_is_zero,
        "overall_pass": passed,
    }

    per_case = [
        {"case_id": v.case_id, "verdict": v.verdict, "reason": v.reason}
        for v in verdicts
    ]

    return {
        "schema_version": 1,
        "adr": "0131.3",
        "sample_path": "evals/math_bounded_grammar/v1/cases.jsonl",
        "sample_count": total,
        "metrics": metrics,
        "exit_criterion": {
            "correct_min_rate": 0.95,
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
