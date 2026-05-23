"""ADR-0131.G.1 — G1 verb-classes capability-axis runner.

Harness that loads cases.jsonl, replays them through the candidate-graph
pipeline, and writes report.json.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from evals.gsm8k_math.runner import _score_one_candidate_graph

_HERE = Path(__file__).resolve().parent
_CASES_PATH = _HERE / "cases.jsonl"
_REPORT_PATH = _HERE / "report.json"
_EXPECTED_COUNT = 20
_WRONG_MAX = 0


def _load_cases(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))
    assert len(records) == _EXPECTED_COUNT, (
        f"G1 verb-classes sample must contain exactly {_EXPECTED_COUNT} cases; "
        f"found {len(records)} at {path}"
    )
    return records


def _adapt(case: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": case["case_id"],
        "problem": case["problem"],
        "expected_answer": case["expected_answer"],
        "expected_unit": case["expected_unit"] or "",
    }


def score_case(case: dict[str, Any]) -> tuple[str, str]:
    """Map the pipeline outcome to the runner verdict based on expected outcome.

    Verdicts: "correct" | "wrong" | "refused"
    """
    expected_outcome = case["expected"]
    adapted = _adapt(case)
    pipeline_outcome = _score_one_candidate_graph(adapted)

    if expected_outcome == "solved_correct":
        if pipeline_outcome.outcome == "correct":
            return "correct", ""
        elif pipeline_outcome.outcome == "wrong":
            return "wrong", pipeline_outcome.reason
        else:
            return "refused", pipeline_outcome.reason

    elif expected_outcome == "solved_wrong":
        if pipeline_outcome.outcome == "wrong":
            # Correctly caught wrong answer
            return "correct", ""
        elif pipeline_outcome.outcome == "correct":
            # Failed to catch wrong answer
            return "wrong", "pipeline solved successfully but expected answer was deliberately wrong"
        else:
            return "refused", pipeline_outcome.reason

    elif expected_outcome == "refused":
        if pipeline_outcome.outcome == "refused":
            # Correctly refused
            return "correct", ""
        else:
            # Failed to refuse
            return "wrong", f"pipeline outcome was {pipeline_outcome.outcome!r} but expected refusal"

    else:
        return "wrong", f"unknown expected outcome: {expected_outcome!r}"


def build_report(cases: list[dict[str, Any]]) -> dict[str, Any]:
    per_case: list[dict[str, Any]] = []
    counts = {"correct": 0, "wrong": 0, "refused": 0}
    for raw in cases:
        verdict, reason = score_case(raw)
        counts[verdict] += 1
        per_case.append(
            {
                "case_id": raw["case_id"],
                "verdict": verdict,
                "reason": reason,
            }
        )
    # The exit criterion for G1 is strictly wrong == 0.
    passed = counts["wrong"] <= _WRONG_MAX
    return {
        "schema_version": 1,
        "adr": "0131.G.1",
        "sample_path": "evals/math_capability_axes/G1_verb_classes/v1/cases.jsonl",
        "sample_count": len(cases),
        "counts": counts,
        "exit_criterion": {
            "wrong_max": _WRONG_MAX,
            "passed": passed,
        },
        "per_case": per_case,
    }


def write_report(report: dict[str, Any], path: Path = _REPORT_PATH) -> None:
    path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    cases = _load_cases(_CASES_PATH)
    report = build_report(cases)
    write_report(report)
    print(f"G1 Verb Classes Evals completed. Counts: {report['counts']}")
    return 0 if report["exit_criterion"]["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
