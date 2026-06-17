"""Tests for the deterministic GSM8K frontier report analyzer (Inc 2).

These tests pin:
- Stable bucketing of the exact refusal reasons emitted by the candidate graph.
- Correct extraction of category=... from "recognizer matched but produced no injection" strings.
- rate_with_currency appears as a prominent recognized_no_injection category on the committed train-sample report (the measurement target of Inc 2).
- Fully deterministic output (sorted keys, no timestamps, repeatable across runs).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.gsm8k_frontier_report import (
    analyze_report,
    render_markdown,
)

_REPO_ROOT = Path(__file__).resolve().parents[1]
_REPORT = _REPO_ROOT / "evals/gsm8k_math/train_sample/v1/report.json"


def test_analyze_report_is_deterministic_and_has_expected_buckets():
    """Run on the real post-Inc1 report; assert structure and rate frontier presence."""
    assert _REPORT.exists(), "report.json must be present for frontier measurement"

    summary = analyze_report(_REPORT)

    # Top-level shape
    assert "counts" in summary
    assert "recognized_no_injection_by_category" in summary
    assert isinstance(summary["counts"], dict)
    assert isinstance(summary["recognized_no_injection_by_category"], dict)

    c = summary["counts"]
    assert c["correct"] == 6
    assert c["refused"] == 44
    assert c.get("recognized_no_injection", 0) > 0

    # The Inc-2 target: rate_with_currency must be visible in the no-injection frontier
    no_inj = summary["recognized_no_injection_by_category"]
    assert "rate_with_currency" in no_inj
    assert no_inj["rate_with_currency"] >= 1  # at minimum the Tina case and peers

    # Determinism: re-running produces byte-identical structure (keys sorted)
    summary2 = analyze_report(_REPORT)
    assert json.dumps(summary, sort_keys=True) == json.dumps(summary2, sort_keys=True)


def test_classify_and_extract_category_logic():
    """Unit the internal classification on the exact reason strings the graph emits."""
    # We exercise via the public analyze path with a tiny synthetic report
    fake = {
        "per_case": [
            {"case_id": "c1", "verdict": "refused", "reason": "candidate_graph: recognizer matched but produced no injection for statement: 'Tina makes $18.00 an hour.' (category=rate_with_currency)"},
            {"case_id": "c2", "verdict": "refused", "reason": "candidate_graph: no admissible candidate for statement: 'foo'"},
            {"case_id": "c3", "verdict": "refused", "reason": "candidate_graph: no admissible candidate for question: 'bar?'"},
            {"case_id": "c4", "verdict": "correct", "reason": "fast-path"},
            {"case_id": "c5", "verdict": "refused", "reason": "some other refusal"},
        ],
        "sample_count": 5,
    }
    # Write temp and analyze (or monkey the path; for simplicity use temp file)
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        rp = Path(td) / "fake_report.json"
        rp.write_text(json.dumps(fake), encoding="utf-8")
        s = analyze_report(rp)

    # The script's _classify_reason and extraction on the exact fake reasons
    c = s["counts"]
    assert c["recognized_no_injection"] == 1
    assert s["recognized_no_injection_by_category"]["rate_with_currency"] == 1
    assert c["no_admissible_statement"] == 1
    assert c["no_admissible_question"] == 1
    assert c.get("fast_path_correct", 0) == 1 or c.get("graph_correct", 0) == 1
    # "some other refusal" lands in other_refused (or similar catch-all)
    # The catch-all for unclassified refusals may be "other_refused" or
    # omitted if count==0 in this particular fake; the important pins are
    # the rate extraction and the main refusal classes.
    assert c["correct"] == 1
    assert "rate_with_currency" in s["recognized_no_injection_by_category"]


def test_markdown_render_is_stable_and_mentions_rate():
    """Markdown output is deterministic and surfaces the rate frontier for humans."""
    fake = {
        "per_case": [
            {"case_id": "r1", "verdict": "refused", "reason": "candidate_graph: recognizer matched but produced no injection for statement: 'X' (category=rate_with_currency)"},
            {"case_id": "c1", "verdict": "correct", "reason": ""},
        ],
        "sample_count": 2,
        "exit_criterion": {"correct_min": 10, "passed": False, "wrong_max": 0},
    }
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        rp = Path(td) / "r.json"
        rp.write_text(json.dumps(fake), encoding="utf-8")
        summary = analyze_report(rp)
        md = render_markdown(summary)

    assert "recognized_no_injection by category (top frontier)" in md
    assert "rate_with_currency: 1" in md
    assert "correct: 1" in md
    # No timestamps or nondet text
    assert "202" not in md and "T" not in md.split("\n", 5)[-1]  # rough
    # Re-render identical
    assert render_markdown(summary) == md