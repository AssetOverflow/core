"""Deductive-logic lane runner — scores the entailment engine against the oracle gold.

The honest capability metric for CORE's deterministic deduction. For each committed
case it runs :func:`generate.proof_chain.entail.evaluate_entailment` and compares the
outcome to the gold (computed by the independent truth-table oracle at generation).

Counts:
* ``correct``  — engine outcome == gold (a right deduction, including a right
  ``unknown``).
* ``wrong``    — engine outcome != gold and engine did not refuse (a confabulated
  deduction — this MUST stay 0).
* ``refused``  — engine returned ``refused`` on a committed in-regime case. This
  is a capability failure for this lane, not a safety success.

A breakdown by gold class (entailed / refuted / unknown) is reported so the
"sizeable numbers" are visible: how many non-trivial entailments/refutations the
engine decides correctly, not just how many ``unknown``s it passes through.

Exits non-zero unless every committed in-regime case is correct. Refusal-boundary
cases live in unit tests, not in these dev/holdout formula splits.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from generate.proof_chain.entail import Entailment, evaluate_entailment

_ROOT = Path(__file__).resolve().parent

# The committed splits this lane scores (refusal-boundary cases live in unit
# tests, not here). Order is fixed for deterministic report bytes.
_SPLITS: tuple[tuple[str, Path], ...] = (
    ("dev", _ROOT / "dev" / "cases.jsonl"),
    ("holdout_v1", _ROOT / "holdout" / "v1" / "cases.jsonl"),
    ("external_v1", _ROOT / "external" / "v1" / "cases.jsonl"),
)


def _load(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def build_report(cases: list[dict]) -> dict:
    counts = Counter({"correct": 0, "wrong": 0, "refused": 0})
    by_gold: Counter[str] = Counter()
    correct_by_gold: Counter[str] = Counter()
    wrong_examples: list[dict] = []
    refused_examples: list[dict] = []

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
            if len(refused_examples) < 10:
                refused_examples.append(
                    {"id": case["id"], "gold": gold, "reason": verdict.reason,
                     "premises": case["premises"], "query": case["query"]}
                )
        else:
            counts["wrong"] += 1
            if len(wrong_examples) < 10:
                wrong_examples.append(
                    {"id": case["id"], "gold": gold, "got": got,
                     "premises": case["premises"], "query": case["query"]}
                )

    all_cases_correct = counts["correct"] == len(cases)
    return {
        "n": len(cases),
        "counts": dict(counts),
        "by_gold": dict(by_gold),
        "correct_by_gold": dict(correct_by_gold),
        "all_cases_correct": all_cases_correct,
        "wrong_examples": wrong_examples,
        "refused_examples": refused_examples,
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
    if report["refused_examples"]:
        print("    REFUSED examples:")
        for r in report["refused_examples"]:
            print(f"      {r['id']}: gold={r['gold']} reason={r['reason']} "
                  f"premises={r['premises']} query={r['query']}")
    return report


def build_combined_report() -> dict:
    """Deterministic per-split + aggregate report over the committed splits.

    Pure over the committed ``cases.jsonl`` files: same inputs → byte-identical
    JSON (no examples lists, no timestamps), so it is safe to SHA-pin
    (``scripts/verify_lane_shas.py``). The human-facing ``_run`` stdout view
    keeps the example breakdowns; the pinned artifact carries only the counts
    that constitute the capability claim.
    """
    splits: dict[str, dict] = {}
    aggregate = {"n": 0, "correct": 0, "wrong": 0, "refused": 0}
    for name, path in _SPLITS:
        report = build_report(_load(path))
        splits[name] = {
            "n": report["n"],
            "counts": report["counts"],
            "by_gold": report["by_gold"],
            "correct_by_gold": report["correct_by_gold"],
            "all_cases_correct": report["all_cases_correct"],
        }
        aggregate["n"] += report["n"]
        for key in ("correct", "wrong", "refused"):
            aggregate[key] += report["counts"][key]
    return {
        "schema_version": 1,
        "lane": "deductive_logic",
        "adr": "ADR-0206",
        "splits": splits,
        "aggregate": aggregate,
        "wrong_is_zero": aggregate["wrong"] == 0,
        "refused_is_zero": aggregate["refused"] == 0,
        "all_correct": all(s["all_cases_correct"] for s in splits.values()),
    }


def write_combined_report(path: Path) -> dict:
    report = build_combined_report()
    path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--report",
        type=Path,
        default=None,
        help=(
            "write the deterministic combined JSON report to this path "
            "(used by scripts/verify_lane_shas.py); default prints the "
            "human-facing per-split breakdown to stdout"
        ),
    )
    args = parser.parse_args(argv)

    if args.report is not None:
        report = write_combined_report(args.report)
        gate_ok = (
            report["wrong_is_zero"]
            and report["refused_is_zero"]
            and report["all_correct"]
        )
        return 0 if gate_ok else 1

    reports = {
        "dev": _run("dev", _ROOT / "dev" / "cases.jsonl"),
        "holdout-v1": _run("holdout-v1", _ROOT / "holdout" / "v1" / "cases.jsonl"),
        "external-v1": _run("external-v1", _ROOT / "external" / "v1" / "cases.jsonl"),
    }
    total_wrong = sum(r["counts"]["wrong"] for r in reports.values())
    total_refused = sum(r["counts"]["refused"] for r in reports.values())
    all_correct = all(r["all_cases_correct"] for r in reports.values())
    return 0 if total_wrong == 0 and total_refused == 0 and all_correct else 1


if __name__ == "__main__":
    sys.exit(main())
