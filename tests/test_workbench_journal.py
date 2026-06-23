from __future__ import annotations

import json
from dataclasses import asdict, replace
from pathlib import Path

import pytest

from workbench import api as workbench_api
from workbench import readers
from workbench.api import MAX_CHAT_PROMPT_CHARS, WorkbenchApi
from workbench.journal import TurnJournal, TurnJournalEntry
from workbench.construction_evidence import ConstructionEvidence
from workbench.schemas import (
    ChatTurnResult,
    CognitivePipelineEdge,
    CognitivePipelineRecord,
    CognitivePipelineStage,
    TurnVerdict,
)


def _pipeline_record(trace_hash: str = "sha256:trace") -> CognitivePipelineRecord:
    stages = [
        CognitivePipelineStage(
            stage_id=stage_id,
            label=stage_id,
            status="recorded",
            summary=stage_id,
            detail={},
        )
        for stage_id in (
            "input",
            "intent",
            "proposition_graph",
            "articulation_target",
            "realizer",
            "walk_telemetry",
            "trace_hash",
        )
    ]
    edges = [
        CognitivePipelineEdge(from_stage="input", to_stage="intent"),
        CognitivePipelineEdge(from_stage="intent", to_stage="proposition_graph"),
        CognitivePipelineEdge(
            from_stage="proposition_graph", to_stage="articulation_target"
        ),
        CognitivePipelineEdge(from_stage="articulation_target", to_stage="realizer"),
        CognitivePipelineEdge(from_stage="realizer", to_stage="walk_telemetry"),
        CognitivePipelineEdge(from_stage="walk_telemetry", to_stage="trace_hash"),
    ]
    return CognitivePipelineRecord(
        schema_version="cognitive_pipeline_record_v1",
        status="recorded",
        missing_reason=None,
        trace_hash=trace_hash,
        versor_condition=0.0,
        field_digest=None,
        stages=stages,
        edges=edges,
    )


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
        pipeline_record=_pipeline_record(),
    )


def _entry(turn_id: int = 1, prompt: str = "What is truth?") -> TurnJournalEntry:
    result = replace(_chat_result(prompt), turn_id=turn_id)
    return TurnJournalEntry.from_chat_turn(
        result,
        turn_id=turn_id,
        timestamp="2026-06-12T00:00:00+00:00",
    )


def _request(api: WorkbenchApi, method: str, path: str, body: dict | None = None):
    raw = b"" if body is None else json.dumps(body).encode("utf-8")
    return api.handle(method, path, raw)


def _snapshot(root: Path) -> dict[str, bytes]:
    snap: dict[str, bytes] = {}
    if not root.exists():
        return snap
    for path in sorted(root.rglob("*")):
        if path.is_file() and "__pycache__" not in path.relative_to(root).parts:
            snap[path.relative_to(root).as_posix()] = path.read_bytes()
    return snap


def test_journal_appends_without_modifying_existing_entries(tmp_path: Path) -> None:
    journal = TurnJournal(tmp_path / "workbench_data")

    first = journal.append(_entry(1))
    first_line = journal.path.read_text(encoding="utf-8").splitlines()[0]
    second = journal.append(_entry(2, "What is memory?"))

    lines = journal.path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert lines[0] == first_line
    assert first.journal_digest
    assert second.turn_id == 2


def test_journal_ordering_and_pagination_are_sequential(tmp_path: Path) -> None:
    journal = TurnJournal(tmp_path / "workbench_data")
    for turn_id in range(1, 5):
        journal.append(_entry(turn_id, f"prompt {turn_id}"))

    assert journal.next_turn_id() == 5
    page = journal.list_summaries(limit=2, offset=1)
    assert [item.turn_id for item in page] == [2, 3]
    assert {item.trace_integrity for item in page} == {"pipeline_trace"}


def test_run_detail_projects_verified_identity_continuity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    engine_state = tmp_path / "engine_state"
    engine_state.mkdir()
    (engine_state / "manifest.json").write_text(
        json.dumps(
            {
                "schema_version": 2,
                "turn_count": 3,
                "written_at_revision": "rev-current",
                "engine_identity": "engine-abc",
                "parent_engine_identity": "engine-abc",
                "identity_scheme": 2,
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(readers, "ENGINE_STATE_ROOT", engine_state)
    monkeypatch.setattr(readers, "get_git_revision", lambda: "rev-current")
    monkeypatch.setattr(
        readers, "engine_identity_for_config", lambda _config: "engine-abc"
    )
    journal = TurnJournal(tmp_path / "workbench_data")

    detail = readers.read_run(readers.ENGINE_STATE_RUN_ID, journal)

    assert detail.identity_continuity is not None
    assert detail.identity_continuity.status == "verified"
    assert detail.identity_continuity.engine_identity == "engine-abc"
    assert detail.identity_continuity.current_engine_identity == "engine-abc"
    assert detail.identity_continuity.lineage_relation == "self_parent"
    assert detail.identity_continuity.evidence_gap is None


def test_run_detail_projects_missing_identity_evidence_honestly(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    engine_state = tmp_path / "engine_state"
    engine_state.mkdir()
    (engine_state / "manifest.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "turn_count": 2,
                "written_at_revision": "legacy-rev",
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(readers, "ENGINE_STATE_ROOT", engine_state)
    monkeypatch.setattr(readers, "get_git_revision", lambda: "rev-current")
    monkeypatch.setattr(
        readers, "engine_identity_for_config", lambda _config: "engine-current"
    )
    journal = TurnJournal(tmp_path / "workbench_data")

    detail = readers.read_run(readers.ENGINE_STATE_RUN_ID, journal)

    assert detail.identity_continuity is not None
    assert detail.identity_continuity.status == "missing_evidence"
    assert detail.identity_continuity.engine_identity is None
    assert detail.identity_continuity.current_engine_identity == "engine-current"
    assert detail.identity_continuity.lineage_relation == "unavailable"
    assert "predates L11" in (detail.identity_continuity.evidence_gap or "")


def test_journal_classifies_old_hashless_rows_as_legacy(tmp_path: Path) -> None:
    journal = TurnJournal(tmp_path / "workbench_data")
    legacy = TurnJournalEntry.from_chat_turn(
        replace(_chat_result(), trace_hash=None),
        turn_id=1,
        timestamp="2026-06-12T00:00:00+00:00",
    )
    payload = {
        key: value for key, value in asdict(legacy).items() if key != "trace_integrity"
    }
    journal.journal_dir.mkdir(parents=True, exist_ok=True)
    journal.path.write_text(
        json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8"
    )

    entry = journal.get_entry(1)
    summary = journal.list_summaries()[0]

    assert entry.trace_integrity == "legacy_unhashed"
    assert summary.trace_integrity == "legacy_unhashed"


def test_trace_turns_offset_beyond_journal_length_returns_empty_items(
    tmp_path: Path,
) -> None:
    journal = TurnJournal(tmp_path / "workbench_data")
    journal.append(_entry(1))
    api = WorkbenchApi(journal=journal)

    response = _request(api, "GET", "/trace/turns?limit=50&offset=50")

    assert response.status == 200
    assert response.payload["data"]["items"] == []


def test_empty_journal_returns_empty_items(tmp_path: Path) -> None:
    api = WorkbenchApi(journal_dir=tmp_path / "workbench_data")

    response = _request(api, "GET", "/trace/turns")

    assert response.status == 200
    assert response.payload["data"]["items"] == []


def test_prompt_size_limit_is_enforced_before_journaling(tmp_path: Path) -> None:
    api = WorkbenchApi(journal_dir=tmp_path / "workbench_data")
    prompt = "x" * (MAX_CHAT_PROMPT_CHARS + 1)

    response = _request(api, "POST", "/chat/turn", {"prompt": prompt})

    assert response.status == 400
    assert not (tmp_path / "workbench_data" / "turn_journal.jsonl").exists()


def test_hashless_chat_result_is_not_journaled(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run(prompt: str) -> ChatTurnResult:
        return replace(_chat_result(prompt), trace_hash=None)

    monkeypatch.setattr(workbench_api, "_run_chat_turn", fake_run)
    api = WorkbenchApi(journal_dir=tmp_path / "workbench_data")

    response = _request(api, "POST", "/chat/turn", {"prompt": "What is truth?"})

    assert response.status == 500
    assert response.payload["error"]["code"] == "runtime_unavailable"
    assert not api._journal.path.exists()  # noqa: SLF001 - verifies fail-closed journaling.


def test_journal_rejects_paths_outside_workbench_data(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="workbench_data"):
        TurnJournal(tmp_path / "not_workbench_data")


def test_journal_does_not_write_teaching_pack_or_engine_state_roots(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = Path(__file__).resolve().parent.parent
    guarded = {
        "teaching": repo_root / "teaching",
        "packs": repo_root / "packs",
        "language_packs/data": repo_root / "language_packs" / "data",
        "engine_state": repo_root / "engine_state",
    }
    before = {name: _snapshot(path) for name, path in guarded.items()}

    def fake_run(prompt: str) -> ChatTurnResult:
        return _chat_result(prompt)

    monkeypatch.setattr(workbench_api, "_run_chat_turn", fake_run)
    api = WorkbenchApi(journal_dir=tmp_path / "workbench_data")

    response = _request(api, "POST", "/chat/turn", {"prompt": "What is truth?"})

    assert response.status == 200
    assert {name: _snapshot(path) for name, path in guarded.items()} == before
    assert api._journal.path.exists()  # noqa: SLF001 - verifies the configured boundary.


def test_journal_digest_is_deterministic_for_identical_content(tmp_path: Path) -> None:
    journal = TurnJournal(tmp_path / "workbench_data")
    first = journal.append(_entry(1))

    other_journal = TurnJournal(tmp_path / "other" / "workbench_data")
    second = other_journal.append(_entry(1))

    assert first.journal_digest == second.journal_digest


def test_chat_turn_round_trips_through_trace_endpoint(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run(prompt: str) -> ChatTurnResult:
        return _chat_result(prompt)

    monkeypatch.setattr(workbench_api, "_run_chat_turn", fake_run)
    api = WorkbenchApi(journal_dir=tmp_path / "workbench_data")

    chat = _request(api, "POST", "/chat/turn", {"prompt": "What is truth?"})
    turn_id = chat.payload["data"]["turn_id"]
    trace = _request(api, "GET", f"/trace/{turn_id}")

    assert chat.status == 200
    assert trace.status == 200
    assert trace.payload["data"]["trace_integrity"] == "pipeline_trace"
    for field in [
        "turn_id",
        "prompt",
        "surface",
        "articulation_surface",
        "walk_surface",
        "trace_hash",
        "grounding_source",
        "epistemic_state",
        "normative_clearance",
        "refusal_emitted",
        "hedge_injected",
        "proposal_candidates",
        "turn_cost_ms",
        "checkpoint_emitted",
    ]:
        assert trace.payload["data"][field] == chat.payload["data"][field]
    assert trace.payload["data"]["pipeline_record"]["status"] == "recorded"


def test_trace_pipeline_endpoint_projects_recorded_stage_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run(prompt: str) -> ChatTurnResult:
        return _chat_result(prompt)

    monkeypatch.setattr(workbench_api, "_run_chat_turn", fake_run)
    api = WorkbenchApi(journal_dir=tmp_path / "workbench_data")

    chat = _request(api, "POST", "/chat/turn", {"prompt": "What is truth?"})
    turn_id = chat.payload["data"]["turn_id"]
    pipeline = _request(api, "GET", f"/trace/{turn_id}/pipeline")

    assert pipeline.status == 200
    data = pipeline.payload["data"]
    assert data["schema_version"] == "cognitive_pipeline_record_v1"
    assert data["status"] == "recorded"
    assert [stage["stage_id"] for stage in data["stages"]] == [
        "input",
        "intent",
        "proposition_graph",
        "articulation_target",
        "realizer",
        "walk_telemetry",
        "trace_hash",
    ]


def test_trace_pipeline_endpoint_marks_prewidening_rows_missing_evidence(
    tmp_path: Path,
) -> None:
    journal = TurnJournal(tmp_path / "workbench_data")
    legacy = replace(_entry(1), pipeline_record=None)
    journal.append(legacy)
    api = WorkbenchApi(journal=journal)

    response = _request(api, "GET", "/trace/1/pipeline")

    assert response.status == 200
    assert response.payload["data"]["status"] == "missing_evidence"
    assert response.payload["data"]["missing_reason"] == "pipeline_record_not_persisted"
    assert response.payload["data"]["trace_hash"] == legacy.trace_hash


def test_chat_turn_without_pipeline_record_is_not_journaled(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run(prompt: str) -> ChatTurnResult:
        return replace(_chat_result(prompt), pipeline_record=None)

    monkeypatch.setattr(workbench_api, "_run_chat_turn", fake_run)
    api = WorkbenchApi(journal_dir=tmp_path / "workbench_data")

    response = _request(api, "POST", "/chat/turn", {"prompt": "What is truth?"})

    assert response.status == 500
    assert response.payload["error"]["code"] == "runtime_unavailable"
    assert not api._journal.path.exists()  # noqa: SLF001 - verifies fail-closed journaling.


def test_unknown_turn_returns_404(tmp_path: Path) -> None:
    api = WorkbenchApi(journal_dir=tmp_path / "workbench_data")

    missing = _request(api, "GET", "/trace/999")
    invalid = _request(api, "GET", "/trace/not-a-real-turn")

    assert missing.status == 404
    assert invalid.status == 404


def test_trace_construction_endpoint_delivers_persisted_evidence(
    tmp_path: Path,
) -> None:
    journal = TurnJournal(tmp_path / "workbench_data")

    evidence_payload = ConstructionEvidence(
        schema_version="construction_evidence_v1",
        turn_id=1,
        status="recorded",
        missing_reason=None,
        problem_text="Lena has 3 red marbles.",
        diagnostic_only=True,
        serving_allowed=False,
    )

    entry = replace(_entry(1), construction_evidence=evidence_payload)
    journal.append(entry)

    api = WorkbenchApi(journal=journal)
    response = _request(api, "GET", "/trace/1/construction")

    assert response.status == 200
    assert response.payload["ok"] is True
    data = response.payload["data"]
    assert data["schema_version"] == "construction_evidence_v1"
    assert data["status"] == "recorded"
    assert data["problem_text"] == "Lena has 3 red marbles."
    assert data["diagnostic_only"] is True
