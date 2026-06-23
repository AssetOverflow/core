from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from workbench.practice_endpoint import (
    practice_evidence_response,
    practice_turn_id_from_path,
)
from workbench.practice_evidence import (
    PRACTICE_EVIDENCE_ABSENT,
    practice_evidence_from_journal_entry,
)


@dataclass(frozen=True, slots=True)
class _Entry:
    turn_id: int
    practice_evidence: Any | None = None


class _Journal:
    def __init__(self, entries: dict[int, Any]) -> None:
        self._entries = entries

    def get_entry(self, turn_id: int) -> Any:
        try:
            return self._entries[turn_id]
        except KeyError:
            raise FileNotFoundError(str(turn_id)) from None


def _sealed_payload() -> dict[str, Any]:
    return {
        "trace_id": "trace-a",
        "trace_policy_version": "sealed_practice_trace.v1",
        "input_digest": "i" * 64,
        "problem_frame_digest": "p" * 64,
        "original_contract_assessment_id": "assessment-a",
        "residual_ids": ["residual-a"],
        "search_gate_decision_id": "g" * 64,
        "compute_budget_id": "b" * 64,
        "geometric_search_run_id": "r" * 64,
        "candidate_attempt_ids": ["attempt-a"],
        "candidate_attempt_binding_ids": ["binding-a"],
        "replay_result_ids": ["replay-a"],
        "replay_refusal_ids": [],
        "upstream_identity_chain": ["p" * 64, "assessment-a", "residual-a"],
        "practice_disposition": "sealed_candidate_replay_closed",
        "trace_records": ["p" * 64, "assessment-a", "residual-a"],
        "evidence_spans": [
            {"text": "delta", "start": 0, "end": 5, "sentence_index": 0}
        ],
        "created_by_policy": "sealed_practice_trace.v1",
        "explanation": "sealed practice trace prose",
    }


def _trace_refusal_payload() -> dict[str, Any]:
    return {
        "trace_refusal_id": "refusal-a",
        "trace_policy_version": "sealed_practice_trace.v1",
        "input_digest": None,
        "practice_disposition": "trace_invalid_input",
        "reason_codes": ["invalid_run_type"],
        "explanation": "Practice trace refused.",
    }


def test_practice_evidence_from_journal_entry_returns_missing_for_legacy_turn() -> None:
    evidence = practice_evidence_from_journal_entry(_Entry(turn_id=7))

    assert evidence.schema_version == "practice_evidence_v1"
    assert evidence.turn_id == 7
    assert evidence.status == "missing_evidence"
    assert evidence.missing_reason == PRACTICE_EVIDENCE_ABSENT
    assert evidence.chain == []
    assert evidence.diagnostic_only is True
    assert evidence.serving_allowed is False
    assert evidence.mutation_allowed is False
    assert evidence.replay_execution_allowed is False
    assert evidence.replay_executed_by_workbench is False


def test_practice_evidence_projects_raw_sealed_trace_payload_read_only() -> None:
    evidence = practice_evidence_from_journal_entry(
        _Entry(turn_id=7, practice_evidence=_sealed_payload())
    )

    assert evidence.status == "recorded"
    assert evidence.record_kind == "sealed_trace"
    assert evidence.practice_disposition == "sealed_candidate_replay_closed"
    assert evidence.sealed_trace is not None
    assert evidence.sealed_trace.trace_id == "trace-a"
    assert evidence.sealed_trace.evidence_spans[0].text == "delta"
    assert evidence.trace_refusal is None
    assert evidence.serving_allowed is False
    assert evidence.mutation_allowed is False
    assert evidence.replay_execution_allowed is False
    assert [card.kind for card in evidence.chain] == [
        "problem_frame",
        "contract_assessment",
        "residuals",
        "search_gate",
        "compute_budget",
        "geometric_search_run",
        "candidate_attempts",
        "attempt_bindings",
        "replay_results",
        "replay_refusals",
        "sealed_trace",
    ]
    assert evidence.chain[5].summary == (
        "Geometric search run identity; Workbench does not execute search."
    )
    assert evidence.chain[8].refs == ["replay-a"]
    assert evidence.chain[9].status == "missing_evidence"


def test_practice_evidence_projects_raw_trace_refusal_payload_read_only() -> None:
    evidence = practice_evidence_from_journal_entry(
        _Entry(turn_id=8, practice_evidence=_trace_refusal_payload())
    )

    assert evidence.status == "recorded"
    assert evidence.record_kind == "trace_refusal"
    assert evidence.practice_disposition == "trace_invalid_input"
    assert evidence.sealed_trace is None
    assert evidence.trace_refusal is not None
    assert evidence.trace_refusal.reason_codes == ["invalid_run_type"]
    assert evidence.chain[0].kind == "trace_refusal"
    assert evidence.serving_allowed is False
    assert evidence.mutation_allowed is False


def test_practice_evidence_response_returns_missing_evidence_for_legacy_turn() -> None:
    response = practice_evidence_response(_Journal({7: _Entry(turn_id=7)}), "7")

    assert response.status == 200
    assert response.payload["ok"] is True
    data = response.payload["data"]
    assert data["schema_version"] == "practice_evidence_v1"
    assert data["turn_id"] == 7
    assert data["status"] == "missing_evidence"
    assert data["diagnostic_only"] is True
    assert data["serving_allowed"] is False
    assert data["mutation_allowed"] is False
    assert data["replay_execution_allowed"] is False


def test_practice_evidence_response_projects_recorded_payload() -> None:
    response = practice_evidence_response(
        _Journal({7: _Entry(turn_id=7, practice_evidence=_sealed_payload())}),
        "7",
    )

    assert response.status == 200
    data = response.payload["data"]
    assert data["status"] == "recorded"
    assert data["record_kind"] == "sealed_trace"
    assert data["sealed_trace"]["trace_id"] == "trace-a"
    assert data["chain"][-1]["kind"] == "sealed_trace"


def test_practice_evidence_response_returns_404_for_bad_turn_id() -> None:
    response = practice_evidence_response(_Journal({}), "not-an-int")

    assert response.status == 404
    assert response.payload["ok"] is False
    assert response.payload["error"]["code"] == "not_found"
    assert "not-an-int" in response.payload["error"]["message"]


def test_practice_evidence_response_returns_404_for_missing_turn() -> None:
    response = practice_evidence_response(_Journal({}), "8")

    assert response.status == 404
    assert response.payload["ok"] is False
    assert response.payload["error"]["code"] == "not_found"
    assert "8" in response.payload["error"]["message"]


def test_practice_turn_id_from_path_matches_only_practice_route() -> None:
    assert practice_turn_id_from_path("/trace/7/practice") == "7"
    assert practice_turn_id_from_path("/trace/7/construction") is None
    assert practice_turn_id_from_path("/trace/7/pipeline") is None
    assert practice_turn_id_from_path("/trace/7") is None
    assert practice_turn_id_from_path("/trace//practice") is None
