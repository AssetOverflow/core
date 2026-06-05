"""Score the general comprehension reader on the set_membership gold lane.

prose -> comprehend() -> to_set_membership() -> independent oracle -> answer vs gold.
A refusal (unreadable prose, unprojectable, or oracle-refused projection) is NOT a
wrong; only a committed answer that disagrees with gold is wrong (must stay 0).
"""

from __future__ import annotations

import json
import sys
from typing import Any

from evals.set_membership.oracle import OracleError, oracle_answer
from evals.set_membership.runner import _load_cases
from generate.meaning_graph.projectors import to_set_membership
from generate.meaning_graph.reader import Refusal, comprehend


def run() -> dict[str, Any]:
    cases = _load_cases()
    correct = wrong = refused = 0
    wrongs: list[dict[str, Any]] = []

    for case in cases:
        comp = comprehend(case["text"])
        if isinstance(comp, Refusal):
            refused += 1
            continue
        projected = to_set_membership(comp)
        if projected is None:
            refused += 1
            continue
        structure, query = projected
        try:
            got = oracle_answer(structure, query)
        except OracleError:
            refused += 1
            continue
        if got == case.get("gold"):
            correct += 1
        else:
            wrong += 1
            wrongs.append(
                {"id": case.get("id"), "got": got, "gold": case.get("gold"), "text": case["text"]}
            )

    return {
        "domain": "comprehension_set_membership",
        "total": len(cases),
        "correct": correct,
        "wrong": wrong,
        "refused": refused,
        "wrongs": wrongs,
        "counts": {"correct": correct, "wrong": wrong, "refused": refused},
    }


def main() -> int:
    report = run()
    print(json.dumps({k: v for k, v in report.items() if k != "wrongs"}, indent=2, sort_keys=True))
    if report["wrong"]:
        print("WRONG > 0 — comprehension produced a wrong committed answer:", file=sys.stderr)
        print(json.dumps(report["wrongs"], indent=2), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
