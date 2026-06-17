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


def test_live_microscope_refusal_partition_is_complete():
    summary = build_microscope_report(_load_cases())

    assert summary["counts"]["refused"] == 44
    assert len(summary["per_case"]) == 44
    assert len(summary["refusal_table"]) == 44
    assert sum(summary["top_buckets"].values()) == 44

    required = {
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
    }
    for row in summary["refusal_table"]:
        assert required <= set(row.keys())

    # Post-Gate-A1 stable top-level buckets (ephemeral main @ bb083004 family)
    assert summary["top_buckets"]["recognized_no_injection"] == 31
    assert summary["top_buckets"]["no_admissible_statement"] == 7
    assert summary["top_buckets"]["no_admissible_question"] == 5
    assert summary["top_buckets"]["no_solvable_branch"] == 1


def test_live_microscope_dcs_and_slice_candidate_pins():
    summary = build_microscope_report(_load_cases())

    assert summary["recognized_no_injection_by_category"]["discrete_count_statement"] == 19
    assert summary["dcs_no_injection_subfamilies"]["dcs_misroute_unit_partition"] == 1
    assert (
        "gsm8k-train-sample-v1-0002"
        in summary["implementation_slice_candidates"]["partition_chunking"]["case_ids"]
    )
    assert summary["no_solvable_branch_subfamilies"]["rate_graph_unsolvable"] == 1


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
    assert "| 0002 |" in md
    assert "Gate A2a unit_partition" in md


def test_case_0002_ratification_candidate_fields():
    summary = build_microscope_report(_load_cases())
    row = next(
        r for r in summary["refusal_table"] if r["case_id"].endswith("0002")
    )
    assert row["subfamily"] == "dcs_misroute_unit_partition"
    assert row["candidate_next_primitive"] == "unit_partition"
    assert row["expected_movement"] == "downstream_reclassification"
    assert (
        summary["recommended_next_ratification_candidate"]
        == "Gate A2a unit_partition / chunking primitive"
    )