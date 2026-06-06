"""Score the relational reader (#596) on binary-relation prose against independent gold.

prose -> comprehend_relational() -> committed Relation vs hand-authored gold triple.
The gold ``(predicate, subject, object)`` is authored by reading English semantics,
INDEPENDENTLY of ``relational.py`` (INV-25 / INV-27): the reader never produced it.

A refusal is a COVERAGE miss, never a wrong; only a committed relation that disagrees
with gold — or a malformed commit (≠ exactly one relation, or a query) — is wrong, and
wrong must stay 0. This is the positive-coverage lane that puts the just-landed reader
ON the capability index (breadth 8→9); the adversarial fabrication cases that must
REFUSE live in ``evals/relational/v1/refusals.jsonl`` and the dedicated lane test.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from generate.meaning_graph.reader import Refusal
from generate.meaning_graph.relational import (
    comprehend_relational,
    load_relational_pack_lemmas,
)

_CASES = Path(__file__).resolve().parent.parent / "relational" / "v1" / "cases.jsonl"


def _load_cases(path: Path = _CASES) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def run(path: Path = _CASES) -> dict[str, Any]:
    cases = _load_cases(path)
    pack = load_relational_pack_lemmas()
    correct = wrong = refused = 0
    wrongs: list[dict[str, Any]] = []

    for case in cases:
        comp = comprehend_relational(case["text"], pack)
        if isinstance(comp, Refusal):
            refused += 1  # coverage miss, not a wrong
            continue
        rels = comp.meaning_graph.relations
        if comp.queries or len(rels) != 1:
            # a declarative fact case must yield exactly one relation and no query;
            # anything else is a malformed commit, counted as wrong (must stay 0).
            wrong += 1
            wrongs.append({"id": case.get("id"), "got": "malformed_commit", "text": case["text"]})
            continue
        rel = rels[0]
        got = [rel.predicate, list(rel.arguments)]
        gold = [case["predicate"], [case["subject"], case["object"]]]
        if got == gold:
            correct += 1
        else:
            wrong += 1
            wrongs.append({"id": case.get("id"), "got": got, "gold": gold, "text": case["text"]})

    return {
        "domain": "comprehension_relational_predicate",
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
        print("WRONG > 0 — relational comprehension produced a wrong committed answer:", file=sys.stderr)
        print(json.dumps(report["wrongs"], indent=2), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
