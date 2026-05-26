"""ADR-0158 (W-024) — reboot_event audit trail entry on engine-state load.

L10 scope §Sub-question 3:
  A ``reboot_event`` analog of ``TurnEvent``, written to the audit trail,
  that lets future audit reconstruct the fact that this engine instance
  lost and regained its lifetime here.
"""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from chat.runtime import ChatRuntime
from chat.telemetry import (
    JsonlBufferSink,
    format_reboot_event_jsonl,
    serialize_reboot_event,
)
from engine_state import EngineStateStore
from recognition.anti_unifier import Constant, DerivedRecognizer, TypedSlot
from teaching.discovery import DiscoveryCandidate, EvidencePointer, SubQuestion


# ---------- fixtures ----------


def _recognizer() -> DerivedRecognizer:
    return DerivedRecognizer(
        pattern=(
            Constant("light"),
            TypedSlot(
                feature_name="object",
                slot_type="noun",
                min_width=1,
                max_width=2,
                ignored_prefix_tokens=("the",),
            ),
        ),
        teaching_set_id="set-1",
        constant_features={"intent": "definition"},
        absent_features={"negated": 0},
    )


def _candidate() -> DiscoveryCandidate:
    ev = EvidencePointer(
        source="pack",
        ref="en_core_cognition_v1:light",
        polarity="affirms",
        epistemic_status="ratified",
    )
    sq = SubQuestion(
        sub_id="sub-1",
        proposed_subject="light",
        proposed_intent="verification",
        outcome="grounded",
        evidence=(ev,),
    )
    return DiscoveryCandidate(
        candidate_id="cand-1",
        proposed_chain={"subject": "light", "intent": "verification"},
        trigger="would_have_grounded",
        source_turn_trace="trace-1",
        pack_consistent=True,
        boundary_clean=True,
        polarity="affirms",
        claim_domain="factual",
        evidence=(ev,),
        sub_questions=(sq,),
        contemplation_depth=1,
    )


def _populated_store(tmp_path, *, turn_count: int = 5, revision: str = "abc123") -> EngineStateStore:
    store = EngineStateStore(tmp_path)
    store.save_recognizers([_recognizer()])
    store.save_discovery_candidates([_candidate()])
    store.save_manifest(turn_count=turn_count)
    # Overwrite manifest to inject a controlled revision for testing.
    import json as _json
    manifest = {
        "schema_version": 1,
        "turn_count": turn_count,
        "written_at_revision": revision,
    }
    (tmp_path / "manifest.json").write_text(
        _json.dumps(manifest, sort_keys=True, indent=2), encoding="utf-8"
    )
    return store


# ---------- serializer unit tests ----------


def test_serialize_reboot_event_structure() -> None:
    payload = serialize_reboot_event(
        restored_turn_count=7,
        stored_revision="abc123",
        current_revision="abc123",
        recognizers_count=2,
        candidates_count=1,
    )

    assert payload["type"] == "reboot"
    assert payload["restored_turn_count"] == 7
    assert payload["stored_revision"] == "abc123"
    assert payload["current_revision"] == "abc123"
    assert payload["revision_matched"] is True
    assert payload["recognizers_count"] == 2
    assert payload["candidates_count"] == 1
    assert "timestamp" not in payload


def test_serialize_reboot_event_mismatch_revision() -> None:
    payload = serialize_reboot_event(
        restored_turn_count=3,
        stored_revision="old000",
        current_revision="new111",
        recognizers_count=0,
        candidates_count=0,
    )

    assert payload["revision_matched"] is False


def test_serialize_reboot_event_unknown_revision_not_matched() -> None:
    payload = serialize_reboot_event(
        restored_turn_count=1,
        stored_revision="unknown",
        current_revision="abc123",
        recognizers_count=0,
        candidates_count=0,
    )

    assert payload["revision_matched"] is False


def test_serialize_reboot_event_with_timestamp() -> None:
    payload = serialize_reboot_event(
        restored_turn_count=0,
        stored_revision="a",
        current_revision="a",
        recognizers_count=0,
        candidates_count=0,
        timestamp="2026-05-26T00:00:00Z",
    )

    assert payload["timestamp"] == "2026-05-26T00:00:00Z"


def test_format_reboot_event_jsonl_is_deterministic() -> None:
    line1 = format_reboot_event_jsonl(
        restored_turn_count=4,
        stored_revision="rev1",
        current_revision="rev2",
        recognizers_count=1,
        candidates_count=0,
    )
    line2 = format_reboot_event_jsonl(
        restored_turn_count=4,
        stored_revision="rev1",
        current_revision="rev2",
        recognizers_count=1,
        candidates_count=0,
    )

    assert line1 == line2
    parsed = json.loads(line1)
    assert parsed["type"] == "reboot"


# ---------- runtime integration tests ----------


def test_reboot_event_emitted_when_sink_attached_after_load(tmp_path) -> None:
    _populated_store(tmp_path, turn_count=5, revision="stored_rev")
    sink = JsonlBufferSink()

    with patch("engine_state._git_revision", return_value="current_rev"):
        runtime = ChatRuntime(engine_state_path=tmp_path)
        runtime.attach_telemetry_sink(sink)

    assert len(sink.lines) == 1
    event = json.loads(sink.lines[0])
    assert event["type"] == "reboot"
    assert event["restored_turn_count"] == 5
    assert event["stored_revision"] == "stored_rev"
    assert event["current_revision"] == "current_rev"
    assert event["revision_matched"] is False
    assert event["recognizers_count"] == 1
    assert event["candidates_count"] == 1


def test_reboot_event_emitted_once_not_twice(tmp_path) -> None:
    _populated_store(tmp_path)
    sink = JsonlBufferSink()

    runtime = ChatRuntime(engine_state_path=tmp_path)
    runtime.attach_telemetry_sink(sink)
    # Attaching a second sink should NOT re-emit the reboot event.
    sink2 = JsonlBufferSink()
    runtime.attach_telemetry_sink(sink2)

    assert len(sink.lines) == 1
    assert len(sink2.lines) == 0


def test_no_reboot_event_when_no_checkpoint(tmp_path) -> None:
    sink = JsonlBufferSink()

    runtime = ChatRuntime(engine_state_path=tmp_path)
    runtime.attach_telemetry_sink(sink)

    assert sink.lines == []


def test_no_reboot_event_when_no_load_state(tmp_path) -> None:
    _populated_store(tmp_path)
    sink = JsonlBufferSink()

    runtime = ChatRuntime(no_load_state=True, engine_state_path=tmp_path)
    runtime.attach_telemetry_sink(sink)

    assert sink.lines == []


def test_reboot_event_revision_matched_true(tmp_path) -> None:
    _populated_store(tmp_path, revision="matchedrev")
    sink = JsonlBufferSink()

    with patch("engine_state._git_revision", return_value="matchedrev"):
        runtime = ChatRuntime(engine_state_path=tmp_path)
        runtime.attach_telemetry_sink(sink)

    event = json.loads(sink.lines[0])
    assert event["revision_matched"] is True


def test_reboot_event_precedes_turn_events(tmp_path) -> None:
    _populated_store(tmp_path, turn_count=2)
    sink = JsonlBufferSink()

    runtime = ChatRuntime(engine_state_path=tmp_path)
    runtime.attach_telemetry_sink(sink)
    # Emit a synthetic turn event stub directly to verify ordering.
    sink.emit('{"type":"turn","turn":0}')

    assert len(sink.lines) == 2
    first = json.loads(sink.lines[0])
    assert first["type"] == "reboot"
