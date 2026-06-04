"""Dimensional-reasoning lane runner — the interlingua's unit algebra vs. the
independent dimensional oracle.

The system under test is the binding-graph interlingua (``generate.binding_graph.
units``): given two unit ids and an operation, what is the dimension of the result?
Each committed case is scored as ``correct`` (SUT == gold), ``wrong`` (SUT
committed a different dimension than gold — MUST stay 0), or ``refused`` (SUT
declined a unit outside the closed vocabulary). The gold is the independent oracle
verdict, frozen into ``cases.jsonl`` at generation (INV-25).
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from generate.binding_graph.units import (
    UnitAlgebraError,
    parse_unit,
    unit_product,
    unit_quotient,
)

_ROOT = Path(__file__).resolve().parent
_REFUSED = "refused"


def decide(op: str, left: str, right: str) -> str:
    """The SUT verdict: the canonical dimension of ``left <op> right`` via the
    interlingua's unit algebra, or ``"refused"`` for an unknown unit / op."""
    try:
        lv = parse_unit(left)
        rv = parse_unit(right)
    except UnitAlgebraError:
        return _REFUSED
    if op == "product":
        return unit_product(lv, rv).to_canonical_string()
    if op == "quotient":
        return unit_quotient(lv, rv).to_canonical_string()
    return _REFUSED


def _load(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def build_report(cases: list[dict]) -> dict:
    counts: Counter[str] = Counter({"correct": 0, "wrong": 0, "refused": 0})
    wrong_examples: list[dict] = []
    for case in cases:
        gold = case["gold"]
        got = decide(case["op"], case["left"], case["right"])
        if got == gold:
            counts["refused" if gold == _REFUSED else "correct"] += 1
        else:
            counts["wrong"] += 1
            if len(wrong_examples) < 10:
                wrong_examples.append({"id": case["id"], "gold": gold, "got": got})
    return {
        "n": len(cases),
        "counts": dict(counts),
        "all_correct": counts["wrong"] == 0,
        "wrong_examples": wrong_examples,
    }


def main() -> int:
    report = build_report(_load(_ROOT / "v1" / "cases.jsonl"))
    c = report["counts"]
    print(f"[dimensional] n={report['n']} correct={c['correct']} wrong={c['wrong']} refused={c['refused']}")
    for w in report["wrong_examples"]:
        print(f"  WRONG {w['id']}: gold={w['gold']} got={w['got']}")
    return 0 if report["all_correct"] else 1


if __name__ == "__main__":
    import sys

    sys.exit(main())
