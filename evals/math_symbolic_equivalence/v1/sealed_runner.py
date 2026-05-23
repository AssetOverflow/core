"""ADR-0131.1.S — Symbolic equivalence sealed holdout runner.

Decrypts ``sealed_holdout.age`` using the identity file specified in the
``CORE_SEALED_KEY`` environment variable, runs symbolic equivalence on each
case, writes a deterministic ``sealed_report.json``, and exits 0/1.

CLI: ``python -m evals.math_symbolic_equivalence.v1.sealed_runner``
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from generate.math_symbolic_equivalence import (
    Verdict,
    check_equivalence,
)

_HERE = Path(__file__).resolve().parent
_SEALED_PATH = _HERE / "sealed_holdout.age"
_REPORT_PATH = _HERE / "sealed_report.json"

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


def decrypt_cases(sealed_path: Path = _SEALED_PATH) -> list[dict[str, Any]]:
    """Decrypt the sealed file using the key from CORE_SEALED_KEY.

    Raises EnvironmentError if the env var is missing or invalid.
    """
    key_path_str = os.environ.get("CORE_SEALED_KEY")
    if not key_path_str:
        raise EnvironmentError(
            "CORE_SEALED_KEY environment variable is not set; "
            "cannot decrypt sealed holdout."
        )

    key_path = Path(key_path_str)
    if not key_path.exists():
        raise EnvironmentError(
            f"CORE_SEALED_KEY file path does not exist: {key_path}"
        )

    try:
        import pyrage
        from pyrage.x25519 import Identity
    except ImportError as exc:
        raise RuntimeError("pyrage package is not installed.") from exc

    try:
        identity = Identity.from_str(key_path.read_text(encoding="utf-8").strip())
        plaintext = pyrage.decrypt(sealed_path.read_bytes(), [identity])
    except Exception as exc:
        raise ValueError(f"Decryption failed: {exc}") from exc

    records: list[dict[str, Any]] = []
    for line in plaintext.decode("utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        records.append(json.loads(line))
    return records


def build_report(cases: list[dict[str, Any]]) -> dict[str, Any]:
    outcomes = [_score_one(c) for c in cases]
    counts = {"correct": 0, "wrong": 0, "refused": 0}
    for o in outcomes:
        counts[o.verdict_class] += 1

    total = len(outcomes)
    correct_rate = counts["correct"] / total if total else 0.0
    passed = (correct_rate >= _CORRECT_RATE_MIN) and (counts["wrong"] <= _WRONG_MAX)

    return {
        "schema_version": 1,
        "adr": "0131.1.S",
        "benchmark": "symbolic_equivalence_holdout_v1",
        "cases_path": str(_SEALED_PATH.relative_to(_HERE.parent.parent.parent)),
        "sample_count": total,
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
    try:
        cases = decrypt_cases()
    except EnvironmentError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"error: {exc.__class__.__name__}: {exc}", file=sys.stderr)
        return 1

    report = build_report(cases)
    write_report(report)
    return 0 if report["exit_criterion"]["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
