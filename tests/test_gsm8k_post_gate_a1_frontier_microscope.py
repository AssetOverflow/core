"""Tests for post-Gate-A1 live frontier microscope (docs/tooling only)."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.gsm8k_post_gate_a1_frontier_microscope import (
    build_microscope_report,
    classify_refusal,
    render_markdown,
)
from tests.gsm8k_train_sample_baseline import assert_monotonic_serving_counts

_REPO_ROOT = Path(__file__).resolve().parents[1]
_CASES_PATH = _REPO_ROOT / "evals/gsm8k_math/train_sample/v1/cases.jsonl"

_APPROVED_TOP_BUCKETS = frozenset({
    "recognized_no_injection",
    "no_admissible_statement",
    "no_admissible_question",
    "no_solvable_branch",
    "incomplete_reading",
    "other_refused",
    "other",
})

_REFUSAL_TABLE_FIELDS = frozenset({
    "case_id",
    "verdict",
    "reason",
    "top_refusal_bucket",
    "subfamily",
    "matched_recognizer_category",
    "first_blocking_layer",
    "candidate_next_primitive",
    "expected_movement",
    "evidence_snippet",
})


def _load_cases() -> list[dict]:
    return [
        json.loads(line)
        for line in _CASES_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_live_microscope_meets_monotonic_contract_and_closed_injectors():
    summary = build_microscope_report(_load_cases())

    assert_monotonic_serving_counts(summary["counts"])
    closed = summary["closed_injector_buckets"]
    assert closed["rate_with_currency_no_injection"] == 0
    assert closed["comparative_with_unit_no_injection"] == 0
    assert closed["unit_partition_no_injection"] == 0


def test_live_microscope_refusal_partition_is_complete():
    summary = build_microscope_report(_load_cases())

    refused = summary["counts"]["refused"]
    assert len(summary["refusal_table"]) == refused
    assert len(summary["per_case"]) == refused
    assert sum(summary["top_buckets"].values()) == refused
    assert set(summary["top_buckets"]) <= _APPROVED_TOP_BUCKETS
    assert summary["top_buckets"].get("recognized_no_injection", 0) >= 0

    for row in summary["refusal_table"]:
        assert _REFUSAL_TABLE_FIELDS <= set(row.keys())
        assert row["verdict"] == "refused"
        assert row["reason"]
        assert row["evidence_snippet"]


def test_live_microscope_partition_seed_case_is_tagged():
    summary = build_microscope_report(_load_cases())
    assert (
        "gsm8k-train-sample-v1-0003"
        in summary["implementation_slice_candidates"]["partition_chunking"]["case_ids"]
    )


def test_microscope_output_is_deterministic():
    cases = _load_cases()
    a = build_microscope_report(cases)
    b = build_microscope_report(cases)
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
    assert render_markdown(a) == render_markdown(b)


def test_classify_refusal_extracts_no_solvable_branch():
    rec = classify_refusal(
        case_id="gsm8k-train-sample-v1-0011",
        reason="candidate_graph: no branch produced a solvable graph",
        question="Alexa has a lemonade stand where she sells lemonade for $2 for one cup.",
    )
    assert rec.top_bucket == "no_solvable_branch"
    assert rec.subfamily == "rate_graph_unsolvable"


def test_markdown_render_surfaces_partition_candidate():
    summary = build_microscope_report(_load_cases())
    md = render_markdown(summary)
    assert "partition_chunking" in md
    assert "| 0003 |" in md
    assert "Gate A2a unit_partition" in md


def test_gate_a2_lifts_are_not_in_refusal_table():
    """Cases solved by Gate A2b/A2c/A2d/A2e must not appear among live refusals."""
    summary = build_microscope_report(_load_cases())
    refused_ids = {r["case_id"] for r in summary["refusal_table"]}
    assert "gsm8k-train-sample-v1-0002" not in refused_ids
    assert "gsm8k-train-sample-v1-0008" not in refused_ids
    assert "gsm8k-train-sample-v1-0025" not in refused_ids
    assert "gsm8k-train-sample-v1-0037" not in refused_ids
    assert summary["counts"]["correct"] >= 10
    assert summary["closed_injector_buckets"]["unit_partition_no_injection"] == 0
