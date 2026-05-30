"""Full-corpus GSM8K microscope — the standing wrong=0 + coverage instrument.

ADR-0191 follow-up. The 47-case ``train_sample`` cannot see confabulations
that only fire on rarer real-corpus shapes: ADR-0191 found 5 wrong answers
on the full 7,473-question real GSM8K train split that ``train_sample``
reported as wrong=0. This tool runs the canonical serving reader
(``generate.math_candidate_graph.parse_and_solve``) over an arbitrary GSM8K
corpus and reports, failures-first:

  - correct / wrong / refused counts (wrong MUST be 0 — the firewall);
  - every wrong answer (so a regression is named, not hidden in a count);
  - refusal families, and for the dominant "recognizer matched but produced
    no injection" family, the per-category breakdown — the coverage map
    that ranks which injector to build next by real frequency.

Run after EVERY capability PR, not just the sample: a flip is only real if
it does not also widen the confabulation surface.

Usage:
    # Default: the committed 47-case train_sample (always available).
    uv run python scripts/gsm8k_microscope.py

    # Full real corpus (download train.jsonl from openai/grade-school-math):
    uv run python scripts/gsm8k_microscope.py --corpus path/to/train.jsonl
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from generate.math_candidate_graph import parse_and_solve  # noqa: E402

_TRAIN_SAMPLE = _REPO_ROOT / "evals/gsm8k_math/train_sample/v1/cases.jsonl"
_CATEGORY_RE = re.compile(r"category=([a-z_]+)")


def _gold(record: dict) -> float | None:
    """Numeric gold answer from either GSM8K-raw or train_sample schema."""
    if "answer_numeric" in record:
        raw = str(record["answer_numeric"])
    elif "answer" in record:
        raw = record["answer"].split("####")[-1]
    else:
        return None
    raw = raw.strip().replace(",", "")
    try:
        return float(raw)
    except ValueError:
        return None


def _question(record: dict) -> str:
    return record.get("question") or record.get("problem") or record.get("text") or ""


def _refusal_family(reason: str | None) -> str:
    if not reason:
        return "(no reason)"
    if "no injection" in reason:
        m = _CATEGORY_RE.search(reason)
        return f"no_injection:{m.group(1) if m else '?'}"
    if "no admissible candidate for statement" in reason:
        return "statement_unparsed"
    if "no admissible candidate for question" in reason:
        return "question_unparsed"
    if "no branch produced" in reason:
        return "no_solvable_branch"
    if "disagree" in reason:
        return "branch_disagreement"
    if "incomplete reading" in reason:
        return "incomplete_reading"
    if "round-trip" in reason or "round trip" in reason:
        return "roundtrip_reject"
    return reason[:48]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--corpus", type=Path, default=_TRAIN_SAMPLE,
        help="JSONL of GSM8K records (default: committed train_sample).",
    )
    ap.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    args = ap.parse_args()

    rows = [json.loads(line) for line in args.corpus.read_text().splitlines() if line.strip()]
    outcome: Counter[str] = Counter()
    families: Counter[str] = Counter()
    no_injection_categories: Counter[str] = Counter()
    wrongs: list[dict] = []

    for rec in rows:
        q = _question(rec)
        gold = _gold(rec)
        res = parse_and_solve(q)
        if res.answer is None:
            outcome["refused"] += 1
            fam = _refusal_family(res.refusal_reason)
            families[fam] += 1
            if fam.startswith("no_injection:"):
                no_injection_categories[fam.split(":", 1)[1]] += 1
        elif gold is not None and abs(float(res.answer) - gold) < 1e-6:
            outcome["correct"] += 1
        else:
            outcome["wrong"] += 1
            wrongs.append({"q": q[:160], "reader": float(res.answer), "gold": gold})

    total = len(rows)
    report = {
        "corpus": str(args.corpus),
        "total": total,
        "outcome": dict(outcome),
        "wrong_is_zero": outcome["wrong"] == 0,
        "wrongs": wrongs,
        "refusal_families": dict(families.most_common()),
        "no_injection_categories": dict(no_injection_categories.most_common()),
    }

    if args.json:
        print(json.dumps(report, indent=2))
        return 0 if report["wrong_is_zero"] else 1

    print(f"=== GSM8K microscope: {args.corpus.name} ({total} questions) ===")
    for k in ("correct", "wrong", "refused"):
        print(f"  {k:9s}: {outcome[k]:6d}  ({100 * outcome[k] / total:.2f}%)")
    print(f"\nwrong==0 firewall: {'HOLDS' if report['wrong_is_zero'] else '*** BREACHED ***'}")
    for w in wrongs:
        print(f"  reader={w['reader']} gold={w['gold']}  {w['q']}")
    print("\n=== refusal families (failures-first) ===")
    for fam, n in families.most_common():
        print(f"  {n:6d}  {fam}")
    if no_injection_categories:
        print("\n=== coverage map: recognizer categories with no injector ===")
        for cat, n in no_injection_categories.most_common():
            print(f"  {n:6d}  {cat}")
    return 0 if report["wrong_is_zero"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
