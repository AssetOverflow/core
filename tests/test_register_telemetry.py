"""Register telemetry — TurnEvent + serialize_turn_event carry
register_id and register_variant_id (ADR-0072 / Plan Phase R5).
"""

from __future__ import annotations

import json

from chat.runtime import ChatRuntime
from chat.telemetry import JsonlBufferSink, serialize_turn_event
from core.config import RuntimeConfig
from core.physics.identity import TurnEvent


def _decode(line: str) -> dict:
    return json.loads(line)


def test_turn_event_defaults_register_fields_empty():
    """Pre-R5 callers constructing TurnEvent without the new fields
    see empty strings — preserves byte-identity."""
    event = TurnEvent(
        turn=0,
        input_tokens=(),
        surface="",
        walk_surface="",
        articulation_surface="",
        dialogue_role="assert",
        identity_score=None,
        cycle_cost_total=0.0,
        vault_hits=0,
        versor_condition=0.0,
        flagged=False,
    )
    assert event.register_id == ""
    assert event.register_variant_id == ""


def test_serialize_turn_event_emits_register_fields():
    """The JSONL audit line carries register_id / register_variant_id."""
    event = TurnEvent(
        turn=0,
        input_tokens=(),
        surface="",
        walk_surface="",
        articulation_surface="",
        dialogue_role="assert",
        identity_score=None,
        cycle_cost_total=0.0,
        vault_hits=0,
        versor_condition=0.0,
        flagged=False,
        register_id="convivial_v1",
        register_variant_id="abcdef012345",
    )
    payload = serialize_turn_event(event)
    assert payload["register_id"] == "convivial_v1"
    assert payload["register_variant_id"] == "abcdef012345"


def test_runtime_chat_emits_register_id_when_set():
    """Convivial-loaded runtime ⇒ every TurnEvent carries register_id."""
    runtime = ChatRuntime(
        config=RuntimeConfig(register_pack_id="convivial_v1")
    )
    sink = JsonlBufferSink()
    runtime.attach_telemetry_sink(sink)
    runtime.chat("What is light?")
    assert sink.lines, "expected at least one telemetry line"
    last = _decode(sink.lines[-1])
    assert last["register_id"] == "convivial_v1"
    # convivial_v1 always emits a non-empty opening on non-empty
    # surfaces, so variant_id is a 12-char hex.
    variant_id = last["register_variant_id"]
    assert variant_id != ""
    assert len(variant_id) == 12
    int(variant_id, 16)


def test_runtime_chat_empty_register_id_for_unregistered():
    """Default runtime (no --register) ⇒ empty register_id / variant_id."""
    runtime = ChatRuntime(config=RuntimeConfig())
    sink = JsonlBufferSink()
    runtime.attach_telemetry_sink(sink)
    runtime.chat("What is light?")
    last = _decode(sink.lines[-1])
    assert last["register_id"] == ""
    assert last["register_variant_id"] == ""


def test_runtime_chat_empty_variant_id_for_terse():
    """terse_v1 has empty marker buckets ⇒ variant_id stays empty even
    though register_id is set."""
    runtime = ChatRuntime(
        config=RuntimeConfig(register_pack_id="terse_v1")
    )
    sink = JsonlBufferSink()
    runtime.attach_telemetry_sink(sink)
    runtime.chat("What is light?")
    last = _decode(sink.lines[-1])
    assert last["register_id"] == "terse_v1"
    assert last["register_variant_id"] == ""


def test_chat_response_mirrors_register_fields():
    """ChatResponse exposes the same register fields as TurnEvent."""
    runtime = ChatRuntime(
        config=RuntimeConfig(register_pack_id="convivial_v1")
    )
    response = runtime.chat("What is light?")
    event = runtime.turn_log[-1]
    assert response.register_id == event.register_id == "convivial_v1"
    assert response.register_variant_id == event.register_variant_id
