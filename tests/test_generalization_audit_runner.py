"""Tests for the generalization audit runner skeleton."""

from __future__ import annotations

import json
import subprocess
import sys
import pytest

from evals.generalization.audit_runner import run_generalization_audit
from evals.generalization.item_schema import (
    GENERALIZATION_AUDIT_RUNNER_POLICY_VERSION,
    GeneralizationAuditItem,
    GeneralizationAuditOutcome,
)


def test_aggregates_counts_and_metrics() -> None:
    """Ensure run_generalization_audit aggregates dispositions, counts, and reasons correctly."""
    items = (
        GeneralizationAuditItem(
            dataset="TEST_DATA",
            split="test",
            item_id="id_1",
            prompt_ref="test:test:id_1",
            answer_kind="numeric",
            metadata=(("tag", "a"),),
        ),
        GeneralizationAuditItem(
            dataset="TEST_DATA",
            split="test",
            item_id="id_2",
            prompt_ref="test:test:id_2",
            answer_kind="numeric",
            metadata=(("tag", "b"),),
        ),
        GeneralizationAuditItem(
            dataset="TEST_DATA",
            split="test",
            item_id="id_3",
            prompt_ref="test:test:id_3",
            answer_kind="numeric",
            metadata=(("tag", "c"),),
        ),
        GeneralizationAuditItem(
            dataset="TEST_DATA",
            split="test",
            item_id="id_4",
            prompt_ref="test:test:id_4",
            answer_kind="numeric",
            metadata=(("tag", "d"),),
        ),
    )

    def mock_evaluator(
        item: GeneralizationAuditItem,
    ) -> GeneralizationAuditOutcome:
        if item.item_id == "id_1":
            return GeneralizationAuditOutcome(
                item_id=item.item_id,
                disposition="correct",
                residual_kinds=("none",),
                candidate_attempt_count=1,
                binding_failure_count=0,
                replay_refusal_count=0,
                sealed_trace_dispositions=("success",),
                reason_codes=(),
            )
        elif item.item_id == "id_2":
            return GeneralizationAuditOutcome(
                item_id=item.item_id,
                disposition="wrong",
                residual_kinds=("precision",),
                candidate_attempt_count=3,
                binding_failure_count=0,
                replay_refusal_count=0,
                sealed_trace_dispositions=("fail", "fail", "success"),
                reason_codes=("precision_error",),
            )
        elif item.item_id == "id_3":
            return GeneralizationAuditOutcome(
                item_id=item.item_id,
                disposition="refused",
                residual_kinds=(),
                candidate_attempt_count=1,
                binding_failure_count=1,
                replay_refusal_count=1,
                sealed_trace_dispositions=("refused",),
                reason_codes=("safety_policy",),
            )
        else:
            return GeneralizationAuditOutcome(
                item_id=item.item_id,
                disposition="unsupported",
                residual_kinds=(),
                candidate_attempt_count=0,
                binding_failure_count=0,
                replay_refusal_count=0,
                sealed_trace_dispositions=(),
                reason_codes=("unsupported_format",),
            )

    report = run_generalization_audit(
        dataset="TEST_DATA",
        split="test",
        items=items,
        evaluator=mock_evaluator,
    )

    # Core disposition counts
    assert report.correct == 1
    assert report.wrong == 1
    assert report.refused == 1
    assert report.unsupported == 1
    assert report.n_items == 4

    # Direct additions of metrics
    assert report.candidate_attempts == 5  # 1 + 3 + 1 + 0
    assert report.binding_failures == 1  # 0 + 0 + 1 + 0
    assert report.replay_refusals == 1  # 0 + 0 + 1 + 0

    # Histograms
    # "success" -> 2 times, "fail" -> 2 times, "refused" -> 1 time
    # Sorted by count descending, then by key ascending:
    # (('fail', 2), ('success', 2), ('refused', 1))
    assert report.sealed_trace_dispositions == (
        ("fail", 2),
        ("success", 2),
        ("refused", 1),
    )

    # residual kinds: "none" -> 1, "precision" -> 1
    # Sorted by count descending, then key:
    # (('none', 1), ('precision', 1))
    assert report.dominant_residual_kinds == (
        ("none", 1),
        ("precision", 1),
    )

    # Reason codes: sorted union of all codes
    assert report.reason_codes == (
        "precision_error",
        "safety_policy",
        "unsupported_format",
    )


def test_empty_item_set_refuses() -> None:
    """Ensure run_generalization_audit refuses (raises ValueError) if items tuple is empty."""
    with pytest.raises(ValueError, match="requires a non-empty sequence"):
        run_generalization_audit(
            dataset="TEST_DATA",
            split="test",
            items=(),
            evaluator=lambda x: None,
        )


def test_evaluator_exception_fail_closed() -> None:
    """Ensure run_generalization_audit catches evaluator exceptions and fails closed."""
    items = (
        GeneralizationAuditItem(
            dataset="TEST_DATA",
            split="test",
            item_id="id_1",
            prompt_ref="test:test:id_1",
            answer_kind="numeric",
            metadata=(),
        ),
    )

    def exploding_evaluator(
        item: GeneralizationAuditItem,
    ) -> GeneralizationAuditOutcome:
        raise RuntimeError("Something exploded!")

    report = run_generalization_audit(
        dataset="TEST_DATA",
        split="test",
        items=items,
        evaluator=exploding_evaluator,
    )

    assert report.n_items == 1
    assert report.refused == 1
    assert report.correct == 0
    assert report.wrong == 0
    assert "evaluator_exception" in report.reason_codes
    assert "RuntimeError" in report.reason_codes


def test_json_output_deterministic_and_no_raw_prompts() -> None:
    """Ensure serialized report is deterministic and does not contain raw prompt/answer fields."""
    items = (
        GeneralizationAuditItem(
            dataset="TEST_DATA",
            split="test",
            item_id="id_1",
            prompt_ref="test:test:id_1",
            answer_kind="numeric",
            metadata=(),
        ),
    )
    report = run_generalization_audit(
        dataset="TEST_DATA",
        split="test",
        items=items,
        evaluator=lambda x: GeneralizationAuditOutcome(
            item_id=x.item_id,
            disposition="correct",
            residual_kinds=(),
            candidate_attempt_count=1,
            binding_failure_count=0,
            replay_refusal_count=0,
            sealed_trace_dispositions=(),
            reason_codes=(),
        ),
    )

    from dataclasses import asdict

    report_dict = asdict(report)

    # 1. Deterministic check
    json1 = json.dumps(report_dict, indent=2, sort_keys=True)
    json2 = json.dumps(report_dict, indent=2, sort_keys=True)
    assert json1 == json2

    # 2. Check no raw prompt/answer leakages in the report
    serialized_str = json1.lower()
    assert "prompt" not in report_dict
    assert "answer" not in report_dict

    # Check that common prompt/answer related strings are absent
    assert "raw_prompt" not in serialized_str
    assert "raw_answer" not in serialized_str
    assert "chain_of_thought" not in serialized_str
    assert "example_text" not in serialized_str


def test_cli_synthetic_smoke() -> None:
    """Verify that --synthetic-smoke runs and produces expected report structure."""
    result = subprocess.run(
        [
            sys.executable,
            "scripts/benchmarks/run_generalization_audit.py",
            "--synthetic-smoke",
            "--json",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.returncode == 0
    report = json.loads(result.stdout)
    assert report["dataset"] == "SYNTHETIC_SMOKE"
    assert report["policy_version"] == GENERALIZATION_AUDIT_RUNNER_POLICY_VERSION
    assert report["n_items"] == 3
    assert report["correct"] == 1
    assert report["wrong"] == 1
    assert report["refused"] == 1


def test_cli_real_dataset_refuses() -> None:
    """Verify that requesting a dataset with no adapter fails with dataset_adapter_unavailable."""
    result = subprocess.run(
        [
            sys.executable,
            "scripts/benchmarks/run_generalization_audit.py",
            "--dataset",
            "asdiv",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "dataset_adapter_unavailable" in result.stderr
