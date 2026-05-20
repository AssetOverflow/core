"""Anchor-lens telemetry — TurnEvent + serialize_turn_event carry
anchor_lens_id and anchor_lens_mode_label (ADR-0073d / L1.4).
"""

from __future__ import annotations

import json

from chat.runtime import (
    ChatRuntime,
    _extract_anchor_lens_mode_label,
)
from chat.telemetry import JsonlBufferSink, serialize_turn_event
from core.config import RuntimeConfig
from core.physics.identity import TurnEvent


def _decode(line: str) -> dict:
    return json.loads(line)


# ---------- TurnEvent shape ----------


def test_turn_event_defaults_anchor_lens_fields_empty():
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
    assert event.anchor_lens_id == ""
    assert event.anchor_lens_mode_label == ""


def test_serialize_turn_event_emits_anchor_lens_fields():
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
        anchor_lens_id="grc_logos_v1",
        anchor_lens_mode_label="systematic",
    )
    payload = serialize_turn_event(event)
    assert payload["anchor_lens_id"] == "grc_logos_v1"
    assert payload["anchor_lens_mode_label"] == "systematic"


# ---------- end-to-end runtime ----------


def test_unanchored_runtime_emits_empty_anchor_lens_fields():
    runtime = ChatRuntime(config=RuntimeConfig())
    sink = JsonlBufferSink()
    runtime.attach_telemetry_sink(sink)
    runtime.chat("What is knowledge?")
    last = _decode(sink.lines[-1])
    assert last["anchor_lens_id"] == ""
    assert last["anchor_lens_mode_label"] == ""


def test_grc_logos_engaged_turn_emits_mode_label():
    runtime = ChatRuntime(
        config=RuntimeConfig(anchor_lens_id="grc_logos_v1")
    )
    sink = JsonlBufferSink()
    runtime.attach_telemetry_sink(sink)
    runtime.chat("What is knowledge?")
    last = _decode(sink.lines[-1])
    assert last["anchor_lens_id"] == "grc_logos_v1"
    assert last["anchor_lens_mode_label"] == "systematic"


def test_he_logos_engaged_turn_emits_mode_label():
    runtime = ChatRuntime(
        config=RuntimeConfig(anchor_lens_id="he_logos_v1")
    )
    sink = JsonlBufferSink()
    runtime.attach_telemetry_sink(sink)
    runtime.chat("What is truth?")
    last = _decode(sink.lines[-1])
    assert last["anchor_lens_id"] == "he_logos_v1"
    assert last["anchor_lens_mode_label"] == "covenant-verity"


def test_lens_loaded_but_not_engaged_emits_empty_mode_label():
    """grc_logos_v1 doesn't engage on the en lemma 'truth' — lens_id
    is recorded but mode_label stays empty."""
    runtime = ChatRuntime(
        config=RuntimeConfig(anchor_lens_id="grc_logos_v1")
    )
    sink = JsonlBufferSink()
    runtime.attach_telemetry_sink(sink)
    runtime.chat("What is truth?")
    last = _decode(sink.lines[-1])
    assert last["anchor_lens_id"] == "grc_logos_v1"
    assert last["anchor_lens_mode_label"] == ""


def test_chat_response_mirrors_event_anchor_lens_fields():
    runtime = ChatRuntime(
        config=RuntimeConfig(anchor_lens_id="grc_logos_v1")
    )
    response = runtime.chat("What is knowledge?")
    event = runtime.turn_log[-1]
    assert response.anchor_lens_id == event.anchor_lens_id == "grc_logos_v1"
    assert (
        response.anchor_lens_mode_label
        == event.anchor_lens_mode_label
        == "systematic"
    )


def test_default_unanchored_pack_emits_pack_id_and_empty_mode():
    runtime = ChatRuntime(
        config=RuntimeConfig(anchor_lens_id="default_unanchored_v1")
    )
    sink = JsonlBufferSink()
    runtime.attach_telemetry_sink(sink)
    runtime.chat("What is knowledge?")
    last = _decode(sink.lines[-1])
    assert last["anchor_lens_id"] == "default_unanchored_v1"
    assert last["anchor_lens_mode_label"] == ""


# ---------- mode-label extractor unit ----------


def test_extractor_returns_empty_for_empty_surface():
    assert _extract_anchor_lens_mode_label("", "grc_logos_v1") == ""


def test_extractor_returns_empty_for_empty_lens_id():
    assert _extract_anchor_lens_mode_label(
        "X [lens(grc_logos_v1):systematic].", "",
    ) == ""


def test_extractor_returns_empty_when_no_annotation_present():
    assert _extract_anchor_lens_mode_label(
        "Plain surface no lens.", "grc_logos_v1",
    ) == ""


def test_extractor_finds_annotation():
    out = _extract_anchor_lens_mode_label(
        "X. pack-grounded (Y) [lens(grc_logos_v1):systematic].",
        "grc_logos_v1",
    )
    assert out == "systematic"


def test_extractor_ignores_annotation_for_different_lens_id():
    """Defensive: a surface might carry an annotation for a different
    lens (composer bug, future multi-lens compositions).  Extractor
    only returns mode_label for the requested lens_id."""
    out = _extract_anchor_lens_mode_label(
        "X. [lens(he_logos_v1):covenant-verity].",
        "grc_logos_v1",
    )
    assert out == ""
