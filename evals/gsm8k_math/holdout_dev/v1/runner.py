"""Held-out dev lane — the honest iteration metric for real GSM8K capability.

**Why this lane exists.** The 50-case `train_sample` is the data CORE's grammar was
built against; it has **zero predictive validity** for real GSM8K (proven 2026-06-04:
train_sample 4/50 correct, this held-out set **0/500**, sealed test **0/1319**). Iterating
against the 50 produced overfit "lift" that committed *wrong* answers on the real exam.

This lane is the fix: **500 real GSM8K cases CORE was NOT built against** (the
`openai/gsm8k` *train* split minus the 50 train_sample, deterministically sampled by
sha256(question)). It is **open** (safe to iterate against — large enough that trivial
memorisation is not the win) while the **sealed test split (1,319) stays the final
arbiter** (never read by Claude). Standard train / dev / test discipline.

**The metric.** `wrong == 0` is the floor (refuse, never confabulate). **`correct` rising
is the goal** — "refuse everything" (the current 0/500 baseline) is the *failing*
baseline we climb off, not a pass. A capability change is real only when it moves
`correct` here AND holds `wrong=0` on the sealed test.

Scored through the canonical serving path (`_score_one_candidate_graph`), identical to
train_sample and the sealed lane, so the three numbers are directly comparable.
Deterministic; no network (reads the committed `cases.jsonl`).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from evals.gsm8k_math.runner import _score_one_candidate_graph

_HERE = Path(__file__).resolve().parent
_CASES_PATH = _HERE / "cases.jsonl"
_REPORT_PATH = _HERE / "report.json"
BASELINE_CORRECT = 0


def _load_cases() -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in _CASES_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def build_report(
    cases: list[dict[str, Any]] | None = None,
    *,
    min_correct: int | None = None,
) -> dict[str, Any]:
    cases = cases if cases is not None else _load_cases()
    counts = {"correct": 0, "wrong": 0, "refused": 0}
    per_case: list[dict[str, str]] = []
    for case in cases:
        outcome = _score_one_candidate_graph(case)
        counts[outcome.outcome] = counts.get(outcome.outcome, 0) + 1
        per_case.append({"case_id": outcome.case_id, "verdict": outcome.outcome})
    safety_pass = counts["wrong"] == 0
    capability_pass = counts["correct"] > BASELINE_CORRECT
    min_correct_pass = True if min_correct is None else counts["correct"] >= min_correct
    return {
        "schema_version": 1,
        "lane": "gsm8k_math/holdout_dev/v1",
        "source": (
            "openai/gsm8k train split, minus the 50 train_sample, "
            "deterministic sha256(question) sort, first 500"
        ),
        "n": len(cases),
        "counts": counts,
        "baseline_correct": BASELINE_CORRECT,
        "safety_pass": safety_pass,
        "capability_pass": capability_pass,
        "min_correct": min_correct,
        "min_correct_pass": min_correct_pass,
        "note": (
            "Open held-out dev metric: cases CORE was NOT built against. Iterate here; "
            "the sealed TEST (1,319) is the final arbiter. wrong=0 is the floor; correct "
            "rising is the goal (refuse-everything is the failing baseline, not a pass)."
        ),
        "per_case": per_case,
    }


def write_report(report: dict[str, Any]) -> None:
    _REPORT_PATH.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--min-correct",
        type=int,
        default=None,
        help=(
            "Optional promotion gate. Default reports safety only; when set, "
            "the process also fails unless correct >= MIN_CORRECT."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    report = build_report(min_correct=args.min_correct)
    write_report(report)
    c = report["counts"]
    print(f"holdout_dev: correct={c['correct']} wrong={c['wrong']} refused={c['refused']} (n={report['n']})")
    if not report["safety_pass"]:
        return 1
    if not report["min_correct_pass"]:
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
