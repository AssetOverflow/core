from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from workbench.api import WorkbenchApi


@dataclass(frozen=True, slots=True)
class _Entry:
    turn_id: int
    practice_evidence: Any | None = None
    construction_evidence: Any | None = None


class _Journal:
    def __init__(self, entries: dict[int, Any]) -> None:
        self._entries = entries

    def get_entry(self, turn_id: int) -> Any:
        try:
            return self._entries[turn_id]
        except KeyError:
            raise FileNotFoundError(str(turn_id)) from None


def _request(journal: _Journal, path: str):
    return WorkbenchApi(journal=journal).handle("GET", path)


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


def test_trace_practice_route_returns_missing_evidence_for_legacy_entry() -> None:
    response = _request(_Journal({7: _Entry(turn_id=7)}), "/trace/7/practice")

    assert response.status == 200
    assert response.payload["ok"] is True
    data = response.payload["data"]
    assert data["schema_version"] == "practice_evidence_v1"
    assert data["turn_id"] == 7
    assert data["status"] == "missing_evidence"
    assert data["record_kind"] is None
    assert data["diagnostic_only"] is True
    assert data["serving_allowed"] is False
    assert data["mutation_allowed"] is False
    assert data["replay_execution_allowed"] is False
    assert data["replay_executed_by_workbench"] is False


def test_trace_practice_route_projects_recorded_payload_read_only() -> None:
    response = _request(
        _Journal({7: _Entry(turn_id=7, practice_evidence=_sealed_payload())}),
        "/trace/7/practice",
    )

    assert response.status == 200
    assert response.payload["ok"] is True
    data = response.payload["data"]
    assert data["schema_version"] == "practice_evidence_v1"
    assert data["status"] == "recorded"
    assert data["record_kind"] == "sealed_trace"
    assert data["sealed_trace"]["trace_id"] == "trace-a"
    assert data["practice_disposition"] == "sealed_candidate_replay_closed"
    assert data["chain"][-1]["kind"] == "sealed_trace"
    assert data["chain"][5]["summary"] == (
        "Geometric search run identity; Workbench does not execute search."
    )
    assert data["diagnostic_only"] is True
    assert data["serving_allowed"] is False
    assert data["mutation_allowed"] is False
    assert data["replay_execution_allowed"] is False
    assert data["replay_executed_by_workbench"] is False


def test_trace_practice_route_returns_404_for_bad_or_missing_turn() -> None:
    bad = _request(_Journal({}), "/trace/not-an-int/practice")
    assert bad.status == 404
    assert bad.payload["ok"] is False
    assert bad.payload["error"]["code"] == "not_found"
    assert "trace practice not found: not-an-int" in bad.payload["error"]["message"]

    missing = _request(_Journal({}), "/trace/99/practice")
    assert missing.status == 404
    assert missing.payload["ok"] is False
    assert missing.payload["error"]["code"] == "not_found"
    assert "trace practice not found: 99" in missing.payload["error"]["message"]


def test_trace_practice_route_does_not_steal_construction_route() -> None:
    journal = _Journal({7: _Entry(turn_id=7)})

    construction = _request(journal, "/trace/7/construction")
    practice = _request(journal, "/trace/7/practice")

    assert construction.status == 200
    assert construction.payload["data"]["schema_version"] == "construction_evidence_v1"
    assert practice.status == 200
    assert practice.payload["data"]["schema_version"] == "practice_evidence_v1"
