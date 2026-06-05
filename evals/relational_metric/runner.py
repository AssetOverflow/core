"""Relational-metric lane runner — field reader vs the independent arithmetic gold.

For each committed case:

1. the independent oracle recomputes the gold from the STRUCTURED relations
   (gold-integrity: a committed gold that the oracle cannot reproduce is rejected,
   so the gold can never be field-derived — INV-25);
2. the geometric field reader reads the TEXT into an answer (or refuses);
3. the field's committed answer is scored against that gold.

Buckets: ``correct`` (field == gold), ``wrong`` (field committed a different
integer), ``refused`` (field declined). ``wrong`` must be 0 — the runner exits 1
otherwise. A refusal is honest coverage, not a wrong answer.

Run:  PYTHONPATH=. .venv/bin/python -m evals.relational_metric.runner
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from evals.relational_metric.oracle import OracleError, oracle_answer
from generate.relational_field_reader import read_relational

_CASES = Path(__file__).resolve().parent / "v1" / "cases.jsonl"


def _load_cases() -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for line in _CASES.read_text(encoding="utf-8").splitlines():
        if line.strip():
            cases.append(json.loads(line))
    return cases


def run() -> dict[str, Any]:
    """Run the lane and return a structured report."""
    cases = _load_cases()
    correct = 0
    wrong: list[dict[str, Any]] = []
    refused: list[str] = []
    gold_integrity_failures: list[str] = []

    for case in cases:
        cid = case["id"]
        committed_gold = case["gold"]
        # 1 — independent gold integrity (the oracle must reproduce the committed gold)
        try:
            recomputed = oracle_answer(case["relations"], case["query"])
        except OracleError:
            gold_integrity_failures.append(f"{cid}: oracle could not reproduce gold")
            continue
        if recomputed != committed_gold:
            gold_integrity_failures.append(
                f"{cid}: oracle={recomputed} != committed gold={committed_gold}"
            )
            continue

        # 2/3 — the field reads the TEXT, scored against the independent gold
        reading = read_relational(case["text"])
        if reading.refused:
            refused.append(f"{cid}: {reading.refusal_reason}")
        elif reading.answer == committed_gold:
            correct += 1
        else:
            wrong.append(
                {"id": cid, "field": reading.answer, "gold": committed_gold}
            )

    return {
        "total": len(cases),
        "correct": correct,
        "wrong": len(wrong),
        "refused": len(refused),
        "wrong_detail": wrong,
        "refused_detail": refused,
        "gold_integrity_failures": gold_integrity_failures,
    }


def main() -> int:
    report = run()
    print(json.dumps({k: v for k, v in report.items()
                      if k not in ("wrong_detail",)}, indent=2))
    if report["gold_integrity_failures"]:
        print("GOLD INTEGRITY FAILURE:", report["gold_integrity_failures"], file=sys.stderr)
        return 1
    if report["wrong"] > 0:
        print("WRONG ANSWERS (wrong!=0 breach):", report["wrong_detail"], file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
