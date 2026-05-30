"""Guards for the frontier-shift instrument (ADR-0190 follow-up)."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.frontier_shift import build_report

_REPORT = (
    Path(__file__).resolve().parent.parent
    / "evals" / "gsm8k_math" / "train_sample" / "v1" / "frontier_shift_report.json"
)


def test_report_is_deterministic() -> None:
    a = json.dumps(build_report(), sort_keys=True)
    b = json.dumps(build_report(), sort_keys=True)
    assert a == b


def test_blocked_on_partitions_all_50_cases() -> None:
    r = build_report()
    assert sum(r["blocked_on_counts"].values()) == 50
    # Solved == the committed serving metric (5/45/0 after ADR-0190).
    assert r["blocked_on_counts"].get("none", 0) == 5


def test_question_extractor_is_the_dominant_lever() -> None:
    # The instrument's load-bearing finding: question parsing gates almost
    # the whole frontier — statement injectors flip nothing on their own.
    r = build_report()
    by_cap = {lv["capability"]: lv for lv in r["leverage"]}
    q = by_cap["question_extractor"]
    assert q["flip_ready"] >= 4
    # No statement-injection capability is flip-ready alone (each is also
    # question-gated) — fails loudly if that ceases to hold.
    for lv in r["leverage"]:
        if lv["capability"].startswith("inject:"):
            assert lv["flip_ready"] == 0, lv


def test_committed_report_matches_fresh_run() -> None:
    if not _REPORT.exists():
        return
    committed = json.loads(_REPORT.read_text())
    assert committed == build_report(), (
        "frontier_shift_report.json is stale; run "
        "`python3 -m scripts.frontier_shift`"
    )
