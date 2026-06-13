from __future__ import annotations

import json
from dataclasses import asdict, replace
from pathlib import Path

import pytest

from workbench import api as workbench_api
from workbench.api import MAX_CHAT_PROMPT_CHARS, WorkbenchApi
from workbench.journal import TurnJournal, TurnJournalEntry
from workbench.schemas import ChatTurnResult, TurnVerdict


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


def test_journal_classifies_old_hashless_rows_as_legacy(tmp_path: Path) -> None:
    journal = TurnJournal(tmp_path / "workbench_data")
    legacy = TurnJournalEntry.from_chat_turn(
        replace(_chat_result(), trace_hash=None),
        turn_id=1,
        timestamp="2026-06-12T00:00:00+00:00",
    )
    payload = {key: value for key, value in asdict(legacy).items() if key != "trace_integrity"}
    journal.journal_dir.mkdir(parents=True, exist_ok=True)
    journal.path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")

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


def test_unknown_turn_returns_404(tmp_path: Path) -> None:
    api = WorkbenchApi(journal_dir=tmp_path / "workbench_data")

    missing = _request(api, "GET", "/trace/999")
    invalid = _request(api, "GET", "/trace/not-a-real-turn")

    assert missing.status == 404
    assert invalid.status == 404
