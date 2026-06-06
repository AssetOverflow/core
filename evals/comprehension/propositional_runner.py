"""Score the general comprehension reader on the propositional_logic gold lane.

prose -> comprehend() -> to_deductive_logic() -> independent ROBDD oracle -> verdict
vs gold. A refusal (unreadable prose, unprojectable, or an oracle "refused" because
the projected formula could not be evaluated) is NOT a wrong; only a committed
verdict that disagrees with gold is wrong (must stay 0).
"""

from __future__ import annotations

import json
import sys
from typing import Any

from evals.deductive_logic.oracle import REFUSED, oracle_entailment
from evals.propositional_logic.runner import _load_cases
from generate.meaning_graph.projectors import to_deductive_logic
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
        projected = to_deductive_logic(comp)
        if projected is None:
            refused += 1
            continue
        premises, query = projected
        got = oracle_entailment(premises, query)
        if got == REFUSED:
            # the projected formula could not be evaluated -> decline, not a wrong
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
        "domain": "comprehension_propositional",
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
