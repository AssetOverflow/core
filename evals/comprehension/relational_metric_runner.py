"""Score the general comprehension reader on the relational_metric gold lane.

prose -> comprehend_quantitative() -> binding_graph -> to_relational_metric() ->
independent arithmetic oracle -> answer vs gold. This is the binding-graph's first
comprehension consumer: quantities live in the binding-graph (admissibility-checked,
never stamped), then project to the relational_metric oracle for the verdict.

A refusal (unreadable prose, admissibility refusal, unprojectable, or an
OracleError on the projection) is NOT a wrong; only a committed integer answer that
disagrees with gold is wrong (must stay 0).
"""

from __future__ import annotations

import json
import sys
from typing import Any

from evals.relational_metric.oracle import OracleError, oracle_answer
from evals.relational_metric.runner import _load_cases
from generate.meaning_graph.reader import Refusal
from generate.quantitative_comprehension import comprehend_quantitative, to_relational_metric


def run() -> dict[str, Any]:
    cases = _load_cases()
    correct = wrong = refused = 0
    wrongs: list[dict[str, Any]] = []

    for case in cases:
        comp = comprehend_quantitative(case["text"])
        if isinstance(comp, Refusal):
            refused += 1
            continue
        projected = to_relational_metric(comp)
        if projected is None:
            refused += 1
            continue
        relations, query = projected
        try:
            got = oracle_answer(relations, query)
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
        "domain": "comprehension_relational_metric",
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
