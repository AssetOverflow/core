"""ADR-0131.1 — Symbolic equivalence lane runner (v1 hardened).

Loads ``cases.jsonl`` plus deterministic generated cases, runs each case
through :func:`generate.math_symbolic_equivalence.check_equivalence`,
classifies the outcome against the expected verdict, and writes a
deterministic ``report.json``.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from evals.math_symbolic_equivalence.v1.generated_cases import build_generated_cases
from generate.math_symbolic_equivalence import (
    Verdict,
    check_equivalence,
)


_HERE = Path(__file__).resolve().parent
_CASES_PATH = _HERE / "cases.jsonl"
_REPORT_PATH = _HERE / "report.json"

# Per ADR-0131 Benchmark 1 exit criterion.
_CORRECT_RATE_MIN = 0.95
_WRONG_MAX = 0


@dataclass(frozen=True, slots=True)
class CaseOutcome:
    case_id: str
    category: str
    expected: str
    actual: str
    verdict_class: str  # "correct" | "wrong" | "refused"
    reason: str

    def as_dict(self) -> dict[str, str]:
        return {
            "case_id": self.case_id,
            "category": self.category,
            "expected": self.expected,
            "actual": self.actual,
            "verdict_class": self.verdict_class,
            "reason": self.reason,
        }


def _score_one(case: dict[str, Any]) -> CaseOutcome:
    """Score a single case against the engine's verdict."""
    expected = case["expected"]
    v = check_equivalence(case["expression_a"], case["expression_b"])
    actual = v.verdict.value

    if actual == expected:
        verdict_class = "correct"
        reason = ""
    elif actual == Verdict.REFUSED.value:
        verdict_class = "refused"
        reason = v.reason
    else:
        verdict_class = "wrong"
        reason = (
            f"engine={actual!r} expected={expected!r}; "
            f"canonical_a={v.canonical_a!r} canonical_b={v.canonical_b!r}"
        )

    return CaseOutcome(
        case_id=case["case_id"],
        category=case["category"],
        expected=expected,
        actual=actual,
        verdict_class=verdict_class,
        reason=reason,
    )


def _load_curated_cases(path: Path = _CASES_PATH) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            record["source"] = "curated"
            records.append(record)
    return records


def _load_generated_cases() -> list[dict[str, Any]]:
    records = build_generated_cases()
    for record in records:
        record["source"] = "generated"
    return records


def _load_cases(path: Path = _CASES_PATH) -> list[dict[str, Any]]:
    cases = _load_curated_cases(path) + _load_generated_cases()
    ids = [str(c["case_id"]) for c in cases]
    if len(ids) != len(set(ids)):
        duplicates = sorted({case_id for case_id in ids if ids.count(case_id) > 1})
        raise RuntimeError(f"duplicate symbolic-equivalence case_id(s): {duplicates}")
    return cases


def build_report(cases: list[dict[str, Any]]) -> dict[str, Any]:
    outcomes = [_score_one(c) for c in cases]
    counts = {"correct": 0, "wrong": 0, "refused": 0}
    for o in outcomes:
        counts[o.verdict_class] += 1

    total = len(outcomes)
    correct_rate = counts["correct"] / total if total else 0.0
    passed = (correct_rate >= _CORRECT_RATE_MIN) and (counts["wrong"] <= _WRONG_MAX)
    by_source = {"curated": 0, "generated": 0}
    for c in cases:
        by_source[str(c.get("source", "curated"))] += 1

    return {
        "schema_version": 2,
        "adr": "0131.1.B",
        "benchmark": "symbolic_equivalence_v1_hardened",
        "cases_path": str(_CASES_PATH.relative_to(_HERE.parent.parent.parent)),
        "generated_cases_module": "evals.math_symbolic_equivalence.v1.generated_cases",
        "sample_count": total,
        "by_source": by_source,
        "counts": counts,
        "correct_rate": correct_rate,
        "exit_criterion": {
            "correct_rate_min": _CORRECT_RATE_MIN,
            "wrong_max": _WRONG_MAX,
            "passed": passed,
        },
        "per_case": [o.as_dict() for o in outcomes],
    }


def write_report(report: dict[str, Any], path: Path = _REPORT_PATH) -> None:
    path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    cases = _load_cases()
    report = build_report(cases)
    write_report(report)
    return 0 if report["exit_criterion"]["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
