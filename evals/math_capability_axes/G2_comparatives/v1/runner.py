"""ADR-0131.G.2 — Capability axis runner for comparative operations.

Exercises the ``compare_additive`` / ``compare_multiplicative`` extractors
in :mod:`generate.math_candidate_parser` against curated coverage cases
that are independent of GSM8K.

Per-case classification:

| Case category   | pass criterion                                          |
|-----------------|---------------------------------------------------------|
| additive        | ≥1 admitted candidate with kind=compare_additive whose  |
|                 | direction, actor, reference, delta_value, unit match    |
| multiplicative  | ≥1 admitted candidate with kind=compare_multiplicative  |
|                 | whose direction, actor, reference, factor, unit match   |
| nested          | both compare_additive AND compare_multiplicative flat   |
|                 | candidates emitted + admitted (binding-graph picks)     |
| refusal         | zero admitted comparative candidates                    |

``wrong`` is non-zero only if a refusal-case emits an admitted comparative
or a positive-case emits a comparative with the wrong shape. ``wrong == 0``
is the load-bearing gate (ADR-0114a Obligation #4).

Determinism: case order in ``cases.jsonl`` is the report order; same
input file → byte-equal report.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from generate.math_candidate_parser import extract_operation_candidates
from generate.math_roundtrip import roundtrip_admissible

_HERE = Path(__file__).resolve().parent
_CASES_PATH = _HERE / "cases.jsonl"
_REPORT_PATH = _HERE / "report.json"


def _load_cases() -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in _CASES_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _admitted(sentence: str) -> list[Any]:
    cands = extract_operation_candidates(sentence)
    return [
        c for c in cands
        if c.op.kind in ("compare_additive", "compare_multiplicative")
        and roundtrip_admissible(c)
    ]


def _score_positive_additive(case: dict[str, Any], admitted: list[Any]) -> tuple[str, str]:
    exp = case["expected"]
    matches = [
        c for c in admitted
        if c.op.kind == "compare_additive"
        and c.op.operand.direction == case["direction"]
        and c.op.actor == exp["actor"]
        and c.op.operand.reference_actor == exp["reference"]
        and c.op.operand.delta is not None
        and c.op.operand.delta.value == exp["delta_value"]
        and c.op.operand.delta.unit == exp["unit"]
        and c.matched_verb == exp["matched_verb"]
    ]
    if matches:
        return "pass", ""
    if not admitted:
        return "wrong", "no admissible comparative candidate emitted"
    return (
        "wrong",
        f"admitted comparative did not match expected additive shape; got {[(c.op.kind, c.op.operand.as_json()) for c in admitted]}",
    )


def _score_positive_multiplicative(case: dict[str, Any], admitted: list[Any]) -> tuple[str, str]:
    exp = case["expected"]
    matches = [
        c for c in admitted
        if c.op.kind == "compare_multiplicative"
        and c.op.operand.direction == case["direction"]
        and c.op.actor == exp["actor"]
        and c.op.operand.reference_actor == exp["reference"]
        and c.op.operand.factor is not None
        and float(c.op.operand.factor) == float(exp["factor"])
        and c.matched_verb == exp["matched_verb"]
    ]
    if matches:
        return "pass", ""
    if not admitted:
        return "wrong", "no admissible comparative candidate emitted"
    return (
        "wrong",
        f"admitted comparative did not match expected multiplicative shape; got {[(c.op.kind, c.op.operand.as_json()) for c in admitted]}",
    )


def _score_nested(_case: dict[str, Any], admitted: list[Any]) -> tuple[str, str]:
    kinds = {c.op.kind for c in admitted}
    if kinds == {"compare_additive", "compare_multiplicative"}:
        return "pass", ""
    return (
        "wrong",
        f"nested case must emit both flat candidate kinds; got {sorted(kinds)}",
    )


def _score_refusal(_case: dict[str, Any], admitted: list[Any]) -> tuple[str, str]:
    if not admitted:
        return "pass", ""
    return (
        "wrong",
        f"refusal case admitted a comparative candidate ({[c.op.kind for c in admitted]}); "
        f"closed-set boundary breached",
    )


def _score_case(case: dict[str, Any]) -> dict[str, Any]:
    sentence = case["sentence"]
    admitted = _admitted(sentence)
    category = case["category"]
    if category == "additive":
        outcome, reason = _score_positive_additive(case, admitted)
    elif category == "multiplicative":
        outcome, reason = _score_positive_multiplicative(case, admitted)
    elif category == "nested":
        outcome, reason = _score_nested(case, admitted)
    elif category == "refusal":
        outcome, reason = _score_refusal(case, admitted)
    else:
        outcome, reason = "wrong", f"unknown case category {category!r}"
    return {
        "case_id": case["case_id"],
        "category": category,
        "outcome": outcome,
        "reason": reason,
        "admitted_count": len(admitted),
        "admitted_kinds": sorted({c.op.kind for c in admitted}),
    }


def build_report() -> dict[str, Any]:
    cases = _load_cases()
    per_case = [_score_case(c) for c in cases]
    total = len(per_case)
    passed = sum(1 for d in per_case if d["outcome"] == "pass")
    wrong = sum(1 for d in per_case if d["outcome"] == "wrong")
    by_category: dict[str, dict[str, int]] = {}
    for d in per_case:
        slot = by_category.setdefault(d["category"], {"passed": 0, "wrong": 0})
        slot[d["outcome"] if d["outcome"] == "passed" else d["outcome"]] = (
            slot.get(d["outcome"], 0) + 1
        )
    # Rebuild by_category with normalized keys.
    by_category = {}
    for d in per_case:
        slot = by_category.setdefault(d["category"], {"pass": 0, "wrong": 0})
        slot[d["outcome"]] = slot.get(d["outcome"], 0) + 1
    return {
        "schema_version": 1,
        "adr": "0131.G.2",
        "axis": "comparatives",
        "cases_path": "evals/math_capability_axes/G2_comparatives/v1/cases.jsonl",
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
        f"ADR-0131.G.2 comparatives: passed {m['passed']}/{m['cases_total']} "
        f"({m['pass_rate']:.1%}); wrong={m['wrong']} (gate: must be 0)"
    )
    for cat, counts in report["per_category"].items():
        print(f"  {cat:14s} {counts}")
    return 0 if m["wrong_count_is_zero"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
