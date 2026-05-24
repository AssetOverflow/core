"""ADR-0136.S.1 — Capability axis runner for rate/event statement parsing.

Exercises the capacity-rate and earnings-rate short-circuit paths in
:func:`generate.math_candidate_graph.parse_and_solve` against curated
coverage cases that are independent of GSM8K.

Per-case classification:

| Case category               | pass criterion                            |
|-----------------------------|-------------------------------------------|
| capacity_same_unit          | answer == expected_answer (exact float)   |
| capacity_cross_unit         | answer == expected_answer                 |
| capacity_pronoun            | answer == expected_answer                 |
| earnings_same_unit          | answer == expected_answer                 |
| refusal_verb_miss           | answer is None (question not admitted)    |

``wrong`` is non-zero only if a positive case returns the wrong numeric
answer or a refusal case emits a numeric answer.  ``wrong == 0`` is the
load-bearing gate (ADR-0114a Obligation #4).

Determinism: case order in ``cases.jsonl`` is the report order; same
input file → byte-equal report.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from generate.math_candidate_graph import parse_and_solve

_HERE = Path(__file__).resolve().parent
_CASES_PATH = _HERE / "cases.jsonl"
_REPORT_PATH = _HERE / "report.json"


def _load_cases() -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in _CASES_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _score_case(case: dict[str, Any]) -> dict[str, Any]:
    r = parse_and_solve(case["problem"])
    exp = case["expected_answer"]

    if exp is not None:
        if r.answer == exp:
            outcome, reason = "pass", ""
        elif r.answer is None:
            outcome = "wrong"
            reason = f"expected {exp} but got refusal: {r.refusal_reason}"
        else:
            outcome = "wrong"
            reason = f"expected {exp} but got {r.answer}"
    else:
        if r.answer is None:
            outcome, reason = "pass", ""
        else:
            outcome = "wrong"
            reason = f"expected refusal but got answer {r.answer}"

    return {
        "case_id": case["case_id"],
        "category": case["category"],
        "outcome": outcome,
        "reason": reason,
        "answer": r.answer,
        "expected_answer": exp,
    }


def build_report() -> dict[str, Any]:
    cases = _load_cases()
    per_case = [_score_case(c) for c in cases]
    total = len(per_case)
    passed = sum(1 for d in per_case if d["outcome"] == "pass")
    wrong = sum(1 for d in per_case if d["outcome"] == "wrong")
    by_category: dict[str, dict[str, int]] = {}
    for d in per_case:
        slot = by_category.setdefault(d["category"], {"pass": 0, "wrong": 0})
        slot[d["outcome"]] = slot.get(d["outcome"], 0) + 1
    return {
        "schema_version": 1,
        "adr": "0136.S.1",
        "axis": "rate_events",
        "cases_path": "evals/math_capability_axes/S1_rate_events/v1/cases.jsonl",
        "metrics": {
            "cases_total": total,
            "passed": passed,
            "wrong": wrong,
            "pass_rate": (passed / total) if total else 0.0,
            "wrong_rate": (wrong / total) if total else 0.0,
            "wrong_count_is_zero": wrong == 0,
        },
        "per_category": {
            k: dict(sorted(v.items())) for k, v in sorted(by_category.items())
        },
        "per_case": per_case,
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
    print(
        f"ADR-0136.S.1 rate_events: passed {m['passed']}/{m['cases_total']} "
        f"({m['pass_rate']:.1%}); wrong={m['wrong']} (gate: must be 0)"
    )
    for cat, counts in report["per_category"].items():
        print(f"  {cat:30s} {counts}")
    return 0 if m["wrong_count_is_zero"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
