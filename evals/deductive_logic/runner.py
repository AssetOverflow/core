"""Deductive-logic lane runner — scores the entailment engine against the oracle gold.

The honest capability metric for CORE's deterministic deduction. For each committed
case it runs :func:`generate.proof_chain.entail.evaluate_entailment` and compares the
outcome to the gold (computed by the independent truth-table oracle at generation).

Counts:
* ``correct``  — engine outcome == gold (a right deduction, including a right
  ``unknown``).
* ``wrong``    — engine outcome != gold and engine did not refuse (a confabulated
  deduction — this MUST stay 0).
* ``refused``  — engine returned ``refused`` (should not happen on these
  well-formed, consistent, propositional cases; counted separately, never as wrong).

A breakdown by gold class (entailed / refuted / unknown) is reported so the
"sizeable numbers" are visible: how many non-trivial entailments/refutations the
engine decides correctly, not just how many ``unknown``s it passes through.

Exits non-zero if ``wrong > 0`` (the floor).
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

from generate.proof_chain.entail import Entailment, evaluate_entailment

_ROOT = Path(__file__).resolve().parent


def _load(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def build_report(cases: list[dict]) -> dict:
    counts = Counter({"correct": 0, "wrong": 0, "refused": 0})
    by_gold: Counter[str] = Counter()
    correct_by_gold: Counter[str] = Counter()
    wrong_examples: list[dict] = []

    for case in cases:
        gold = case["gold"]
        by_gold[gold] += 1
        verdict = evaluate_entailment(tuple(case["premises"]), case["query"])
        got = verdict.outcome.value
        if got == gold:
            counts["correct"] += 1
            correct_by_gold[gold] += 1
        elif verdict.outcome is Entailment.REFUSED:
            counts["refused"] += 1
        else:
            counts["wrong"] += 1
            if len(wrong_examples) < 10:
                wrong_examples.append(
                    {"id": case["id"], "gold": gold, "got": got,
                     "premises": case["premises"], "query": case["query"]}
                )

    return {
        "n": len(cases),
        "counts": dict(counts),
        "by_gold": dict(by_gold),
        "correct_by_gold": dict(correct_by_gold),
        "wrong_examples": wrong_examples,
    }


def _run(name: str, path: Path) -> dict:
    report = build_report(_load(path))
    c = report["counts"]
    bg = report["by_gold"]
    cbg = report["correct_by_gold"]
    print(f"[{name}] n={report['n']} "
          f"correct={c['correct']} wrong={c['wrong']} refused={c['refused']}")
    print(f"    gold mix: entailed={bg.get('entailed', 0)} "
          f"refuted={bg.get('refuted', 0)} unknown={bg.get('unknown', 0)}")
    print(f"    correct by class: entailed={cbg.get('entailed', 0)} "
          f"refuted={cbg.get('refuted', 0)} unknown={cbg.get('unknown', 0)}")
    if report["wrong_examples"]:
        print("    WRONG examples:")
        for w in report["wrong_examples"]:
            print(f"      {w['id']}: gold={w['gold']} got={w['got']} "
                  f"premises={w['premises']} query={w['query']}")
    return report


if __name__ == "__main__":
    reports = {
        "dev": _run("dev", _ROOT / "dev" / "cases.jsonl"),
        "holdout-v1": _run("holdout-v1", _ROOT / "holdout" / "v1" / "cases.jsonl"),
    }
    total_wrong = sum(r["counts"]["wrong"] for r in reports.values())
    sys.exit(1 if total_wrong > 0 else 0)
