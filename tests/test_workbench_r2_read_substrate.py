from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from workbench import readers
from workbench.api import WorkbenchApi
from workbench.journal import TurnJournal, TurnJournalEntry
from workbench.schemas import ChatTurnResult, TurnVerdict


def _request(api: WorkbenchApi, method: str, path: str):
    return api.handle(method, path, b"")


def _snapshot(root: Path) -> dict[str, bytes]:
    snap: dict[str, bytes] = {}
    if not root.exists():
        return snap
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        if "__pycache__" in rel.parts or rel.suffix in {".pyc", ".pyo"}:
            continue
        snap[rel.as_posix()] = path.read_bytes()
    return snap


def _chat_result(prompt: str = "What is truth?") -> ChatTurnResult:
    return ChatTurnResult(
        prompt=prompt,
        surface="Truth is coherent structure.",
        articulation_surface="Truth is coherent structure.",
        walk_surface="truth -> coherence",
        grounding_source="pack",
        epistemic_state="decoded",
        normative_clearance="cleared",
        normative_detail="",
        trace_hash="sha256:trace",
        refusal_emitted=False,
        hedge_injected=False,
        mutation_mode="runtime_turn",
        identity_verdict=TurnVerdict(outcome="cleared", runtime_detail=""),
        safety_verdict=TurnVerdict(outcome="cleared", runtime_detail=""),
        ethics_verdict=TurnVerdict(outcome="cleared", runtime_detail=""),
        proposal_candidates=[],
        turn_cost_ms=7,
        checkpoint_emitted=False,
    )


def _entry(turn_id: int, timestamp: str) -> TurnJournalEntry:
    result = replace(_chat_result(f"prompt {turn_id}"), turn_id=turn_id)
    return TurnJournalEntry.from_chat_turn(result, turn_id=turn_id, timestamp=timestamp)


def test_packs_list_get_pagination_and_checksum_verbatim() -> None:
    api = WorkbenchApi()

    first = _request(api, "GET", "/packs?limit=1&offset=0")
    second = _request(api, "GET", "/packs?limit=1&offset=1")
    detail = _request(api, "GET", "/packs/en_core_cognition_v1")

    assert first.status == 200
    assert first.payload["ok"] is True
    assert first.payload["generated_at"]
    assert len(first.payload["data"]["items"]) == 1
    assert len(second.payload["data"]["items"]) == 1
    assert first.payload["data"]["items"][0]["pack_id"] <= second.payload["data"]["items"][0]["pack_id"]
    assert detail.status == 200
    assert detail.payload["data"]["pack_id"] == "en_core_cognition_v1"
    assert detail.payload["data"]["checksum"] == detail.payload["data"]["manifest"]["checksum"]
    assert detail.payload["data"]["checksums"]["checksum"] == detail.payload["data"]["manifest"]["checksum"]


def test_pack_id_path_traversal_rejected_before_filesystem_access() -> None:
    api = WorkbenchApi()

    response = _request(api, "GET", "/packs/..%2F..%2Fpyproject.toml")

    assert response.status == 400
    assert response.payload["ok"] is False
    assert response.payload["error"]["code"] == "bad_request"


def test_unknown_pack_returns_404_not_synthetic_data() -> None:
    response = _request(WorkbenchApi(), "GET", "/packs/not_a_real_pack_v1")

    assert response.status == 404
    assert response.payload["ok"] is False
    assert response.payload["error"]["code"] == "not_found"


def test_audit_events_merge_existing_artifacts_with_stable_order(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    proposal_log = tmp_path / "proposal_events.jsonl"
    proposal_log.write_text(
        json.dumps(
            {
                "event": "transition",
                "proposal_id": "proposal-1",
                "to": "accepted",
                "timestamp": "2026-06-12T02:00:00+00:00",
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    math_log = tmp_path / "math_proposals.jsonl"
    math_log.write_text(
        json.dumps(
            {
                "proposal_id": "math-1",
                "domain": "math",
                "timestamp": "2026-06-12T01:00:00+00:00",
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    telemetry_root = tmp_path / "workbench_data"
    telemetry_root.mkdir()
    (telemetry_root / "operator_telemetry.jsonl").write_text(
        json.dumps(
            {
                "event": "operator_ratify",
                "proposal_id": "math-1",
                "timestamp": "2026-06-12T03:00:00+00:00",
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(readers, "DEFAULT_PROPOSAL_LOG_PATH", proposal_log)
    monkeypatch.setattr(readers, "MATH_PROPOSALS_JSONL", math_log)
    monkeypatch.setattr(readers, "WORKBENCH_TELEMETRY_ROOT", telemetry_root)
    monkeypatch.setattr(readers, "ENGINE_STATE_ROOT", tmp_path / "engine_state")

    api = WorkbenchApi()
    page = _request(api, "GET", "/audit/events?limit=2&offset=0")
    next_page = _request(api, "GET", "/audit/events?limit=2&offset=2")
    again = _request(api, "GET", "/audit/events?limit=2&offset=0")

    assert page.status == 200
    items = page.payload["data"]["items"]
    assert [item["source"] for item in items] == ["math_proposal_log", "teaching_proposal_log"]
    assert [item["timestamp"] for item in items] == sorted(item["timestamp"] for item in items)
    assert items[1]["mutation_boundary"] is True
    assert next_page.payload["data"]["items"][0]["source"] == "operator_telemetry"
    assert page.payload["data"] == again.payload["data"]


def test_runs_project_turn_journal_without_synthesizing_unknown_sessions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(readers, "ENGINE_STATE_ROOT", tmp_path / "engine_state")
    journal = TurnJournal(tmp_path / "workbench_data")
    journal.append(_entry(1, "2026-06-12T00:00:00+00:00"))
    journal.append(_entry(2, "2026-06-12T00:01:00+00:00"))
    api = WorkbenchApi(journal=journal)

    runs = _request(api, "GET", "/runs?limit=1&offset=0")
    detail = _request(api, "GET", f"/runs/{readers.JOURNAL_RUN_ID}?limit=1&offset=1")
    missing = _request(api, "GET", "/runs/not-a-real-session")

    assert runs.status == 200
    assert runs.payload["data"]["items"][0]["session_id"] == readers.JOURNAL_RUN_ID
    assert runs.payload["data"]["items"][0]["turn_count"] == 2
    assert detail.status == 200
    assert detail.payload["data"]["turns"][0]["turn_id"] == 2
    assert detail.payload["data"]["turns"][0]["trace_path"] == "/trace/2"
    assert missing.status == 404


def test_vault_absent_returns_typed_evidence_unavailable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(readers, "ENGINE_STATE_ROOT", tmp_path / "engine_state")

    response = _request(WorkbenchApi(), "GET", "/vault/summary")

    assert response.status == 501
    assert response.payload["ok"] is False
    assert response.payload["error"]["code"] == "evidence_unavailable"


def test_vault_summary_and_entries_read_persisted_session_state_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine_state = tmp_path / "engine_state"
    engine_state.mkdir()
    (engine_state / "session_state.json").write_text(
        json.dumps(
            {
                "vault": {
                    "versors": [{"dtype": "float32", "shape": [1], "data": "AAAAAA=="}],
                    "metadata": [
                        {
                            "id": "entry-1",
                            "epistemic_status": "coherent",
                            "epistemic_state": "decoded",
                        }
                    ],
                    "store_count": 1,
                    "reproject_interval": 20,
                    "max_entries": None,
                }
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(readers, "ENGINE_STATE_ROOT", engine_state)
    api = WorkbenchApi()

    summary = _request(api, "GET", "/vault/summary")
    entries = _request(api, "GET", "/vault/entries?limit=1&offset=0")

    assert summary.status == 200
    assert summary.payload["data"]["entry_count"] == 1
    assert summary.payload["data"]["persisted"] is True
    assert entries.status == 200
    assert entries.payload["data"]["items"][0]["metadata"]["id"] == "entry-1"
    assert entries.payload["data"]["items"][0]["versor_digest"].startswith("sha256:")


def test_r2_read_routes_do_not_mutate_guarded_roots() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    guarded = {
        "teaching": repo_root / "teaching",
        "packs": repo_root / "packs",
        "language_packs/data": repo_root / "language_packs" / "data",
        "engine_state": repo_root / "engine_state",
    }
    before = {name: _snapshot(path) for name, path in guarded.items()}
    api = WorkbenchApi()

    responses = [
        _request(api, "GET", "/packs?limit=2"),
        _request(api, "GET", "/packs/en_core_cognition_v1"),
        _request(api, "GET", "/audit/events?limit=2"),
        _request(api, "GET", "/runs?limit=2"),
        _request(api, "GET", "/vault/summary"),
        _request(api, "GET", "/vault/entries?limit=2"),
    ]

    assert [response.status for response in responses] == [200, 200, 200, 200, 501, 501]
    assert {name: _snapshot(path) for name, path in guarded.items()} == before
