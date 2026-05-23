"""ADR-0131.G.3 — Numeric-literals capability-axis runner.

First sibling under ``evals/math_capability_axes/`` — the iteration
pattern from ADR-0131.G ("each ADR-0131.G.<n> extends a single
capability axis with its own curated coverage cases, independent of
GSM8K"). G.3's axis is numeric-literal recognition: money symbols
(``$N`` / ``$N.NN``), the word forms ``N dollars`` / ``N cents``, and
hyphenated multi-word cardinals (``twenty-five``).

The runner wraps :func:`evals.gsm8k_math.runner._score_one_candidate_graph`
(the candidate-graph pipeline ADR-0126 introduced) so that any future
G.<n> axis extending the same parser layer shows up on the same lane
without parallel infrastructure.

Outcome classification mirrors the GSM8K runner:

  | Pipeline result        | Outcome   |
  |------------------------|-----------|
  | parser+solver+verifier OK and answer/unit match | ``solved_correct`` |
  | parser+solver OK but verifier fails or answer mismatches | ``solved_wrong`` (gate: must be 0) |
  | parser/solver refuses with typed reason | ``refused`` |

Cases ship with an ``expected_outcome`` so the runner can score
positive-coverage cases (``solved_correct``) AND adversarial-refusal
probes (``refused``) on the same axis. ``wrong == 0`` is preserved as
the load-bearing invariant per ADR-0114a Obligation #4.

The runner is pure / deterministic: same case set → byte-equal
``report.json`` across runs.
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
    """Translate axis-case shape to the candidate-graph runner's expected
    shape. Refusal cases pass ``expected_unit=""`` so the unit-mismatch
    branch doesn't fire on cases that never reach the answer comparison.
    """
    return {
        "id": raw["case_id"],
        "problem": raw["problem"],
        "expected_answer": float(raw["expected_answer"]),
        "expected_unit": raw.get("expected_unit", ""),
    }


def _classify(actual_outcome: str, expected_outcome: str) -> str:
    """Map the candidate-graph runner's outcome + the case's expected
    outcome into a unified axis-lane verdict.

    - ``solved_correct``: pipeline returned ``correct`` AND expected was
      ``solved_correct``.
    - ``refused``: pipeline returned ``refused`` AND expected was
      ``refused``.
    - ``solved_wrong``: any disagreement — either ``correct`` for a
      ``refused`` case, ``wrong`` ever, or ``refused`` for a
      ``solved_correct`` case. All map to ``solved_wrong``, which the
      lane gate requires to be zero.
    """
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
        "adr": "0131.G.3",
        "axis": "numeric_literals",
        "cases_path": "evals/math_capability_axes/G3_numerics/v1/cases.jsonl",
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
