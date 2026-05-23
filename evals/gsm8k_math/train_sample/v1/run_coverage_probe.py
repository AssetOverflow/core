"""ADR-0131.G — GSM8K coverage probe.

Scores the real-GSM8K train sample (case_id / question /
answer_numeric format) against the bounded grammar + binding graph
pipeline. Emits a ``train_sample_coverage_report.json`` that pins:

  - ``admission_rate`` — fraction parsed + solved + verifier-passed
    (i.e. ``correct``)
  - ``wrong`` — must always be 0 (the gate)
  - ``refused_rate`` — fraction refused with a typed reason at the
    parser or solver layer
  - per-case outcomes (audit trail)
  - top refused clauses (the work queue for grammar expansion)

The report is committed alongside this script so admission progress
across iterations (G.1, G.2, ...) is a diff-able number, not a
narrative claim.

ADR-0131.G.0 — probe-substrate fix: the probe consults the
**candidate-graph pipeline** (:func:`_score_one_candidate_graph`),
not the legacy first-match-wins parser (:func:`_score_one`). Every
ADR-0131.G.<n> iteration extends the candidate-graph parser layer;
the probe must measure that layer for the iteration discipline to
produce attributable admission deltas. The substrate swap is
zero-delta on the current main baseline (both paths produce 0/50)
but load-bearing for every subsequent iteration.

The probe is deterministic: same case set → byte-equal report.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from evals.gsm8k_math.runner import _score_one_candidate_graph


_HERE = Path(__file__).resolve().parent
_CASES_PATH = _HERE / "cases.jsonl"
_REPORT_PATH = _HERE / "train_sample_coverage_report.json"


def _adapt_case(raw: dict[str, Any]) -> dict[str, Any]:
    """Translate train_sample shape (case_id / question / answer_numeric)
    into the lane runner's expected shape (id / problem / expected_answer
    / expected_unit). Train-sample cases carry no unit annotation; the
    empty string is used so unit-mismatch verifications don't fire on
    answer-only correctness.
    """
    return {
        "id": raw["case_id"],
        "problem": raw["question"],
        "expected_answer": float(raw["answer_numeric"]),
        "expected_unit": "",
    }


def _summarize_refusal_reasons(case_details: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Bucket refused outcomes by the first 120 chars of the reason
    and count duplicates. Returns a deterministically-ordered list of
    {count, reason} dicts.
    """
    counter: Counter[str] = Counter()
    for d in case_details:
        if d["outcome"] != "refused":
            continue
        reason = d["reason"].split("\n")[0][:120]
        counter[reason] += 1
    return [
        {"count": count, "reason": reason}
        for reason, count in sorted(
            counter.items(),
            key=lambda kv: (-kv[1], kv[0]),
        )
    ]


def _score_lane(adapted_cases: list[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Run every case through the candidate-graph pipeline and aggregate.

    Mirrors :func:`evals.gsm8k_math.runner.run_lane` but uses
    :func:`_score_one_candidate_graph` so the probe measures the
    parser layer that every ADR-0131.G.<n> iteration extends.
    """
    outcomes = [_score_one_candidate_graph(c) for c in adapted_cases]
    total = len(outcomes)
    correct = sum(1 for o in outcomes if o.outcome == "correct")
    wrong = sum(1 for o in outcomes if o.outcome == "wrong")
    refused = sum(1 for o in outcomes if o.outcome == "refused")
    metrics = {
        "cases_total": total,
        "correct": correct,
        "wrong": wrong,
        "refused": refused,
        "correct_rate": (correct / total) if total else 0.0,
        "wrong_rate": (wrong / total) if total else 0.0,
        "refused_rate": (refused / total) if total else 0.0,
        "wrong_count_is_zero": wrong == 0,
    }
    return metrics, [o.as_json() for o in outcomes]


def build_report() -> dict[str, Any]:
    raw_cases = [
        json.loads(line)
        for line in _CASES_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    adapted = [_adapt_case(c) for c in raw_cases]
    metrics, case_details = _score_lane(adapted)
    total = metrics["cases_total"]
    return {
        "schema_version": 1,
        "adr": "0131.G",
        "probe": "gsm8k_train_sample_coverage",
        "substrate": "candidate_graph",
        "sample_path": str(_CASES_PATH.relative_to(_HERE.parent.parent.parent.parent)),
        "metrics": {
            "cases_total": total,
            "admitted_solved": metrics["correct"],
            "admitted_wrong": metrics["wrong"],
            "refused": metrics["refused"],
            "admission_rate": metrics["correct_rate"],
            "wrong_rate": metrics["wrong_rate"],
            "refused_rate": metrics["refused_rate"],
            "wrong_count_is_zero": metrics["wrong_count_is_zero"],
            "safety_rail_intact": metrics["wrong_count_is_zero"],
        },
        "refused_reasons_top": _summarize_refusal_reasons(case_details),
        "per_case": case_details,
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
        f"admission_rate: {m['admitted_solved']}/{m['cases_total']} "
        f"= {m['admission_rate']:.1%}"
    )
    print(f"wrong:          {m['admitted_wrong']} (gate: must be 0)")
    print(
        f"refused:        {m['refused']}/{m['cases_total']} "
        f"= {m['refused_rate']:.1%}"
    )
    print(f"safety_rail_intact: {m['safety_rail_intact']}")
    return 0 if m["wrong_count_is_zero"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
