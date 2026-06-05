"""Gold-only runner for the staged set-membership lane.

No engine reader is invoked here. The runner only checks that committed gold is
reproducible from structured cases by the independent oracle.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from evals.set_membership.oracle import OracleError, oracle_answer

_CASES = Path(__file__).resolve().parent / "v1" / "cases.jsonl"


def _load_cases(path: Path = _CASES) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def run(path: Path = _CASES) -> dict[str, Any]:
    cases = _load_cases(path)
    failures: list[str] = []
    for case in cases:
        try:
            got = oracle_answer(case["structure"], case["query"])
        except OracleError as exc:
            failures.append(f"{case.get('id', '<missing>')}: refused gold case: {exc}")
            continue
        if got != case.get("gold"):
            failures.append(f"{case['id']}: oracle={got!r} != gold={case.get('gold')!r}")

    correct = len(cases) - len(failures)
    return {
        "domain": "set_membership",
        "total": len(cases),
        "correct": correct,
        "wrong": 0,
        "refused": 0,
        "gold_integrity_failures": failures,
        "counts": {"correct": correct, "wrong": 0, "refused": 0},
    }


def main() -> int:
    report = run()
    print(json.dumps(report, indent=2, sort_keys=True))
    if report["gold_integrity_failures"]:
        print("GOLD INTEGRITY FAILURE", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

