"""ADR-0131.G.4 — Capability axis runner for multi-clause composition.

Exercises the four within-sentence multi-clause extractors in
``generate.math_candidate_parser`` against curated coverage cases
independent of GSM8K.

Per-case classification (wrong == 0 is non-negotiable):

| category               | pass criterion                                 |
|------------------------|------------------------------------------------|
| conj_subject_each      | emits exactly the expected (entity,value,unit) |
|                        | tuples (set equality), all admitted            |
| conj_object            | same — for the two conjoined object NPs        |
| embedded_quantifier    | emits exactly one admitted candidate with the  |
|                        | derived product value                          |
| conj_embedded          | emits exactly one admitted SUM candidate       |
| refusal                | zero admitted multi-clause candidates          |

A pass also requires *no extraneous* multi-clause candidates beyond the
expected set; an emit-too-many is classified ``wrong``. Note: legacy
single-clause initials emitted by ``_INITIAL_HAS_RE`` are allowed
alongside multi-clause emissions on the same sentence — they're a
separate provenance path and are not counted against the multi-clause
expectation.

Determinism: cases.jsonl order is the report order; same input file →
byte-equal report.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from generate.math_candidate_graph import _initial_admissible
from generate.math_candidate_parser import (
    CandidateInitial,
    _conj_embedded_admitted,
    _conj_object_admitted,
    _conj_subject_each_admitted,
    _embedded_quantifier_admitted,
)

_HERE = Path(__file__).resolve().parent
_CASES_PATH = _HERE / "cases.jsonl"
_REPORT_PATH = _HERE / "report.json"


def _load_cases() -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in _CASES_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _tuples(cands: list[CandidateInitial]) -> list[tuple[str, float, str]]:
    return [
        (c.initial.entity, float(c.initial.quantity.value), c.initial.quantity.unit)
        for c in cands
    ]


def _expected_tuples(case: dict[str, Any]) -> list[tuple[str, float, str]]:
    return [
        (e["entity"], float(e["value"]), e["unit"])
        for e in case["expected"]["emits"]
    ]


def _admitted_for_category(category: str, sentence: str) -> list[CandidateInitial]:
    if category == "conj_subject_each":
        return _conj_subject_each_admitted(sentence)
    if category == "conj_object":
        return _conj_object_admitted(sentence)
    if category == "embedded_quantifier":
        return _embedded_quantifier_admitted(sentence)
    if category == "conj_embedded":
        return _conj_embedded_admitted(sentence)
    if category == "refusal":
        # For refusal cases we check every multi-clause extractor returns
        # empty; concatenate all admitted multi-clause outputs.
        return (
            _conj_subject_each_admitted(sentence)
            + _conj_object_admitted(sentence)
            + _embedded_quantifier_admitted(sentence)
            + _conj_embedded_admitted(sentence)
        )
    return []


def _score_case(case: dict[str, Any]) -> dict[str, Any]:
    sentence = case["sentence"]
    category = case["category"]
    admitted = _admitted_for_category(category, sentence)
    if category == "refusal":
        if admitted:
            return {
                "case_id": case["case_id"],
                "category": category,
                "outcome": "wrong",
                "reason": (
                    "refusal case admitted multi-clause candidates: "
                    f"{_tuples(admitted)}"
                ),
                "admitted_count": len(admitted),
            }
        return {
            "case_id": case["case_id"],
            "category": category,
            "outcome": "pass",
            "reason": "",
            "admitted_count": 0,
        }

    got = sorted(_tuples(admitted))
    want = sorted(_expected_tuples(case))
    # Also assert every admitted candidate passes _initial_admissible
    # (defense in depth — extractor already filters, but the runner
    # re-checks).
    if not all(_initial_admissible(c) for c in admitted):
        return {
            "case_id": case["case_id"],
            "category": category,
            "outcome": "wrong",
            "reason": "admitted candidate failed _initial_admissible re-check",
            "admitted_count": len(admitted),
        }
    if got != want:
        return {
            "case_id": case["case_id"],
            "category": category,
            "outcome": "wrong",
            "reason": f"emit mismatch: got {got}, want {want}",
            "admitted_count": len(admitted),
        }
    return {
        "case_id": case["case_id"],
        "category": category,
        "outcome": "pass",
        "reason": "",
        "admitted_count": len(admitted),
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
        "adr": "0131.G.4",
        "axis": "multi_clause",
        "cases_path": "evals/math_capability_axes/G4_multi_clause/v1/cases.jsonl",
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
        f"ADR-0131.G.4 multi-clause: passed {m['passed']}/{m['cases_total']} "
        f"({m['pass_rate']:.1%}); wrong={m['wrong']} (gate: must be 0)"
    )
    for cat, counts in report["per_category"].items():
        print(f"  {cat:24s} {counts}")
    return 0 if m["wrong_count_is_zero"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
