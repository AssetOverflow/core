"""ADR-0131.G.3.1 — Numerics-extensions capability-axis runner (v1.1).

Additive sibling to ``evals/math_capability_axes/G3_numerics/v1/``.
v1 is frozen as the audit-trail artifact for PR #183; v1.1 carries the
four axes deferred from G.3:

  1. **Fractions end-to-end** — ``N/M of a <unit>`` initial possession.
  2. **Multi-currency** — ``¢``, ``€``, ``¥``, ``₱`` symbols.
     (``£`` deferred to G.3.2: question extractor's single-token unit
     slot cannot parse the two-word surface "pounds sterling".)
  3. **Multi-token space-separated cardinals** — ``one hundred``,
     ``two thousand five hundred``.
  4. **Word-number-adjective** — ``five full boxes``.

Runner interface is identical to v1 so the G3 axis lane CI check is
parameterisable over both versions.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from evals.gsm8k_math.runner import _score_one_candidate_graph

_HERE = Path(__file__).resolve().parent
_CASES_PATH = _HERE / "cases.jsonl"
_REPORT_PATH = _HERE / "report.json"


def _load_cases() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for line in _CASES_PATH.read_text(encoding="utf-8").splitlines():
        if line.strip():
            out.append(json.loads(line))
    return out


def _adapt_case(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": raw["case_id"],
        "problem": raw["problem"],
        "expected_answer": float(raw["expected_answer"]),
        "expected_unit": raw.get("expected_unit", ""),
    }


def _classify(actual_outcome: str, expected_outcome: str) -> str:
    if expected_outcome == "solved_correct" and actual_outcome == "correct":
        return "solved_correct"
    if expected_outcome == "refused" and actual_outcome == "refused":
        return "refused"
    return "solved_wrong"


def build_report() -> dict[str, Any]:
    raw_cases = _load_cases()
    case_results: list[dict[str, Any]] = []
    class_counts: Counter[str] = Counter()
    verdict_counts: Counter[str] = Counter()

    for raw in raw_cases:
        cls = raw["class"]
        expected = raw["expected_outcome"]
        class_counts[cls] += 1
        outcome = _score_one_candidate_graph(_adapt_case(raw))
        verdict = _classify(outcome.outcome, expected)
        verdict_counts[verdict] += 1
        case_results.append({
            "case_id": raw["case_id"],
            "class": cls,
            "expected_outcome": expected,
            "actual_outcome": outcome.outcome,
            "verdict": verdict,
            "expected_answer": raw["expected_answer"],
            "actual_answer": outcome.actual_answer,
            "actual_unit": outcome.actual_unit,
            "reason": outcome.reason,
            "trace_hash": outcome.trace_hash,
        })

    total = len(raw_cases)
    correct = verdict_counts.get("solved_correct", 0)
    wrong = verdict_counts.get("solved_wrong", 0)
    refused_expected = verdict_counts.get("refused", 0)
    positive_count = sum(1 for r in raw_cases if r["expected_outcome"] == "solved_correct")
    correct_rate_on_positive = (
        correct / positive_count if positive_count else 0.0
    )

    return {
        "schema_version": 1,
        "adr": "0131.G.3.1",
        "axis": "numerics_extensions",
        "cases_path": "evals/math_capability_axes/G3_numerics/v1_1/cases.jsonl",
        "metrics": {
            "cases_total": total,
            "solved_correct": correct,
            "solved_wrong": wrong,
            "refused_as_expected": refused_expected,
            "wrong_count_is_zero": wrong == 0,
            "correct_rate_on_positive_cases": correct_rate_on_positive,
            "overall_pass": wrong == 0 and (correct + refused_expected == total),
        },
        "class_counts": dict(sorted(class_counts.items())),
        "verdict_counts": dict(sorted(verdict_counts.items())),
        "per_case": case_results,
    }


def write_report(report: dict[str, Any]) -> None:
    _REPORT_PATH.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    report = build_report()
    write_report(report)
    m = report["metrics"]
    print(f"axis:                  {report['axis']}")
    print(f"cases_total:           {m['cases_total']}")
    print(f"solved_correct:        {m['solved_correct']}")
    print(f"solved_wrong:          {m['solved_wrong']} (gate: must be 0)")
    print(f"refused_as_expected:   {m['refused_as_expected']}")
    print(f"correct_rate_on_positive_cases: {m['correct_rate_on_positive_cases']:.1%}")
    print(f"overall_pass:          {m['overall_pass']}")
    return 0 if m["overall_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
