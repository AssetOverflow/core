from __future__ import annotations

import pytest

from workbench.generalization_evidence import (
    contains_forbidden_raw_item_keys,
    generalization_audit_banner,
    generalization_report_view_from_payload,
)
from workbench.schemas import to_data


def test_generalization_report_view_is_aggregate_only() -> None:
    view = generalization_report_view_from_payload(
        {
            "policy_version": "generalization_benchmark_policy_v1",
            "dataset": "gsm1k",
            "split": "local_audit",
            "n_items": 10,
            "correct": 4,
            "wrong": 0,
            "refused": 6,
            "unsupported": 0,
            "candidate_attempts": 3,
            "binding_failures": 2,
            "replay_refusals": 1,
            "sealed_trace_dispositions": {"sealed": 7, "refused": 3},
            "dominant_residual_kinds": {"missing_binding": 5},
            "reason_codes": ["ok", "binding_missing"],
        },
        source_path="evals/generalization/reports/gsm1k.json",
        source_digest="sha256:abc",
        report_kind="committed_pin",
    )

    assert view.policy_version == "generalization_benchmark_policy_v1"
    assert view.dataset == "gsm1k"
    assert view.split == "local_audit"
    assert view.correct == 4
    assert view.wrong == 0
    assert view.refused == 6
    assert view.audit_only is True
    assert view.raw_items_exposed is False
    assert view.report_kind == "committed_pin"
    assert view.sealed_trace_dispositions == [("refused", 3), ("sealed", 7)]
    assert view.dominant_residual_kinds == [("missing_binding", 5)]


def test_generalization_report_rejects_raw_item_fields() -> None:
    with pytest.raises(ValueError, match="raw item"):
        generalization_report_view_from_payload(
            {
                "dataset": "bad",
                "split": "sealed",
                "n_items": 1,
                "items": [{"question": "secret", "answer": "secret"}],
            }
        )


def test_contains_forbidden_raw_item_keys_recurses() -> None:
    assert contains_forbidden_raw_item_keys({"nested": {"gold_answer": "42"}}) is True
    assert contains_forbidden_raw_item_keys({"aggregate": {"correct": 1}}) is False


def test_generalization_report_serializes_as_safe_dataclass() -> None:
    payload = to_data(
        generalization_report_view_from_payload(
            {
                "dataset": "asdiv",
                "split": "public",
                "n_items": 0,
            }
        )
    )

    assert payload["dataset"] == "asdiv"
    assert payload["split"] == "public"
    assert payload["audit_only"] is True
    assert payload["raw_items_exposed"] is False
    assert "items" not in payload
    assert "question" not in payload
    assert "answer" not in payload


def test_generalization_audit_banner_states_governance_boundary() -> None:
    banner = generalization_audit_banner()

    assert "Audit-only" in banner
    assert "No raw sealed items" in banner
    assert "not direct mutation targets" in banner
