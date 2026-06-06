"""Gold-only runner for the staged propositional-logic lane.

The independent arbiter is ``evals.deductive_logic.oracle.oracle_entailment`` (the
ROBDD-matched brute-force entailment checker). This runner verifies the committed
gold is exactly that oracle's verdict on each case's ``premises``/``query`` formula
strings — so the gold cannot drift from the independent oracle.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from evals.deductive_logic.oracle import oracle_entailment

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
        got = oracle_entailment(tuple(case["premises"]), case["query"])
        if got != case.get("gold"):
            failures.append(f"{case['id']}: oracle={got!r} != gold={case.get('gold')!r}")

    correct = len(cases) - len(failures)
    return {
        "domain": "propositional_logic",
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
