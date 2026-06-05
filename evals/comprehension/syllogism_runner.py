"""Score the general comprehension reader on the syllogism gold lane.

prose -> comprehend() -> to_syllogism() -> INDEPENDENT oracle -> validity vs gold.
A refusal (unreadable prose, unprojectable, or oracle-refused) is NOT a wrong;
only a committed validity verdict that disagrees with gold is wrong (must be 0).
"""

from __future__ import annotations

import json
import sys
from typing import Any

from evals.syllogism.oracle import OracleError, oracle_answer
from evals.syllogism.runner import _load_cases
from generate.meaning_graph.projectors import to_syllogism
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
        projected = to_syllogism(comp)
        if projected is None:
            refused += 1
            continue
        structure, query = projected
        try:
            got = oracle_answer(structure, query)
        except OracleError:
            refused += 1
            continue
        gold = case.get("gold", {})
        if got.get("valid") == gold.get("valid"):
            correct += 1
        else:
            wrong += 1
            wrongs.append(
                {"id": case.get("id"), "got": got, "gold": gold, "text": case["text"]}
            )

    return {
        "domain": "comprehension_syllogism",
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
        print("WRONG > 0 — comprehension produced a wrong validity verdict:", file=sys.stderr)
        print(json.dumps(report["wrongs"], indent=2), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
