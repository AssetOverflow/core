"""Sealed single-turn replay — GET /replay/{turn_id} (Wave R3).

Proof obligations from docs/analysis/replay-moment-backend-scoping-2026-06-12.md:
each test here must MEANINGFULLY FAIL under the violation it is written to
catch (CLAUDE.md schema-defined proof obligations rule).
"""

from __future__ import annotations

from dataclasses import fields, replace
from pathlib import Path

import pytest

from chat.runtime import ChatRuntime
from workbench import api as workbench_api
from workbench.api import WorkbenchApi, _run_sealed_chat_turn, _with_turn_cost_and_id
from workbench.journal import TurnJournal, TurnJournalEntry
from workbench.replay import CRITICAL_FIELDS, INFORMATIONAL_FIELDS, replay_turn

_ENGINE_STATE_DIR = Path("engine_state")


def _snapshot(root: Path) -> dict[str, bytes]:
    snap: dict[str, bytes] = {}
    if not root.exists():
        return snap
    for path in sorted(root.rglob("*")):
        if path.is_file() and "__pycache__" not in path.relative_to(root).parts:
            snap[path.relative_to(root).as_posix()] = path.read_bytes()
    return snap


@pytest.fixture(scope="module")
def recorded() -> tuple[TurnJournalEntry, object]:
    """One sealed-origin turn, journaled — the genesis-true positive control.

    Module-scoped: the sealed runtime turn is the expensive part; every test
    derives tampered copies from this single recorded entry.
    """
    result = _run_sealed_chat_turn("What is truth?")
    result = _with_turn_cost_and_id(result, 7, 1)
    entry = TurnJournalEntry.from_chat_turn(result, turn_id=1)
    return entry, result


def _api_with_entry(tmp_path: Path, entry: TurnJournalEntry) -> WorkbenchApi:
    journal = TurnJournal(journal_dir=tmp_path / "workbench_data")
    journal.append(entry)
    return WorkbenchApi(journal=journal)


def test_field_classification_is_exhaustive() -> None:
    """A future journal field must force an explicit severity decision."""
    names = {spec.name for spec in fields(TurnJournalEntry)}
    assert CRITICAL_FIELDS | INFORMATIONAL_FIELDS == names
    assert not CRITICAL_FIELDS & INFORMATIONAL_FIELDS


def test_sealed_origin_turn_replays_equivalent(tmp_path, recorded) -> None:
    """Positive control: genesis-origin entry replays bit-equivalent."""
    entry, _ = recorded
    api = _api_with_entry(tmp_path, entry)

    response = api.handle("GET", "/replay/1", b"")

    assert response.status == 200
    data = response.payload["data"]
    assert data["equivalent"] is True
    assert data["comparison_basis"] == "sealed_fresh_runtime_single_turn"
    assert data["origin_state"] == "unrecorded"
    assert data["original_trace_hash"] == entry.trace_hash
    assert data["replay_trace_hash"] == entry.trace_hash
    assert all(d["severity"] == "informational" for d in data["divergences"])


def test_tampered_prompt_breaks_equivalence(tmp_path, recorded) -> None:
    """Obligation 1: mutating the recorded prompt flips equivalent to false."""
    entry, _ = recorded
    tampered = replace(entry, prompt="What is beauty?")
    api = _api_with_entry(tmp_path, tampered)

    response = api.handle("GET", "/replay/1", b"")

    assert response.status == 200
    data = response.payload["data"]
    assert data["equivalent"] is False
    critical_paths = {d["path"] for d in data["divergences"] if d["severity"] == "critical"}
    assert critical_paths  # the different prompt produced a different envelope


def test_tampered_surface_diverges_at_exactly_that_leaf(tmp_path, recorded) -> None:
    """Obligation 2: comparison reads the RECORDED entry, leaf-precise."""
    entry, _ = recorded
    tampered = replace(entry, surface=entry.surface + " [tampered]")
    api = _api_with_entry(tmp_path, tampered)

    response = api.handle("GET", "/replay/1", b"")

    data = response.payload["data"]
    assert data["equivalent"] is False
    critical = [d for d in data["divergences"] if d["severity"] == "critical"]
    assert [d["path"] for d in critical] == ["surface"]
    assert critical[0]["original"] == entry.surface + " [tampered]"
    assert critical[0]["replay"] == entry.surface


def test_no_comparison_without_real_execution(tmp_path, recorded, monkeypatch) -> None:
    """Obligation 3: a digest-to-itself shortcut cannot pass.

    If the runtime cannot execute, the endpoint must surface a typed error
    and never a fabricated comparison — equivalent: true is unreachable
    without a real re-execution.
    """
    entry, _ = recorded
    api = _api_with_entry(tmp_path, entry)

    def broken(prompt: str):
        raise RuntimeError("runtime unavailable in test")

    monkeypatch.setattr(workbench_api, "_run_sealed_chat_turn", broken)

    response = api.handle("GET", "/replay/1", b"")

    assert response.status == 500
    assert response.payload["error"]["code"] == "runtime_unavailable"
    assert "data" not in response.payload or not response.payload.get("data")


def test_hashless_legacy_turn_is_not_replayable(tmp_path, recorded, monkeypatch) -> None:
    """A legacy row without a canonical trace hash is audit residue, not replay proof."""
    entry, _ = recorded
    legacy = replace(entry, trace_hash=None, trace_integrity=None)
    api = _api_with_entry(tmp_path, legacy)
    executed = False

    def execute(_prompt: str):
        nonlocal executed
        executed = True
        raise AssertionError("legacy rows must fail before execution")

    monkeypatch.setattr(workbench_api, "_run_sealed_chat_turn", execute)

    response = api.handle("GET", "/replay/1", b"")

    assert response.status == 501
    assert response.payload["error"]["code"] == "evidence_unavailable"
    assert "canonical pipeline trace hash" in response.payload["error"]["message"]
    assert executed is False


def test_replay_leaves_no_trace(tmp_path, recorded) -> None:
    """Obligation 4: GET /replay writes nothing — journal and engine state."""
    entry, _ = recorded
    journal = TurnJournal(journal_dir=tmp_path / "workbench_data")
    journal.append(entry)
    api = WorkbenchApi(journal=journal)
    journal_before = _snapshot(tmp_path / "workbench_data")
    engine_state_before = _snapshot(_ENGINE_STATE_DIR)

    response = api.handle("GET", "/replay/1", b"")

    assert response.status == 200
    assert _snapshot(tmp_path / "workbench_data") == journal_before
    assert _snapshot(_ENGINE_STATE_DIR) == engine_state_before


def test_wall_clock_divergence_does_not_break_equivalence(tmp_path, recorded) -> None:
    """Obligation 5: timestamp/cost/digest differ freely; equivalence holds."""
    entry, _ = recorded
    aged = replace(
        entry,
        timestamp="1970-01-01T00:00:00+00:00",
        turn_cost_ms=999_999,
        journal_digest="sha256:not-a-real-digest",
    )
    api = _api_with_entry(tmp_path, aged)

    response = api.handle("GET", "/replay/1", b"")

    data = response.payload["data"]
    assert data["equivalent"] is True
    informational_paths = {d["path"] for d in data["divergences"]}
    assert "timestamp" in informational_paths
    assert "turn_cost_ms" in informational_paths


def test_unknown_and_malformed_turn_ids_refuse_404(tmp_path, recorded) -> None:
    entry, _ = recorded
    api = _api_with_entry(tmp_path, entry)

    for raw in ("999", "not-a-number", ""):
        response = api.handle("GET", f"/replay/{raw}", b"")
        assert response.status == 404
        assert response.payload["error"]["code"] == "not_found"


def test_sealed_runtime_construction_is_sealed() -> None:
    """The replay executor's runtime has no engine-state store at all."""
    runtime = ChatRuntime(no_load_state=True)
    assert runtime._engine_state_store is None
    # checkpoint_engine_state must be a no-op, not an error.
    runtime.checkpoint_engine_state()


def test_replay_turn_propagates_executor_failure(recorded) -> None:
    """replay_turn itself never swallows execution failure into a result."""
    entry, _ = recorded

    def broken(prompt: str):
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        replay_turn(entry, execute=broken)
