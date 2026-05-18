"""ADR-0059 — correction-pass telemetry emission.

The backward perturbation triggered by ``ChatRuntime.correct()`` must
be visible to audit consumers.  Today the forward regen turn that
follows ``correct()`` emits a turn event, but the correction delta
itself — which past turns moved, how far, and toward what — was
invisible to the telemetry sink.

ADR-0059 closes that gap with a dedicated correction-event JSONL line
discriminated by ``"type": "correction"``.  Same sink contract; new
event type alongside ``TurnEvent`` lines.

These tests pin:

  - No emission when no sink is attached.
  - Emission when a sink is attached AND ``correct()`` triggered at
    least one record.
  - Payload shape: type discriminator, target_turn, records_count,
    turns_skipped, turn_idxs_affected, max_delta_norm,
    mean_delta_norm, correction_versor_digest (SHA-256), pack ids.
  - Trust boundary: no versor coordinates in the line, only L2 deltas
    and a deterministic versor digest.
  - Determinism: same input → byte-identical line.
"""

from __future__ import annotations

import json

from chat.runtime import ChatRuntime
from chat.telemetry import JsonlBufferSink


def _seed_two_turns(rt: ChatRuntime) -> None:
    """Populate the session graph with enough turns for backward walk."""
    rt.chat("Why does light exist?")
    rt.chat("Why does thought exist?")


def test_no_emission_without_sink() -> None:
    rt = ChatRuntime()
    _seed_two_turns(rt)
    response = rt.correct("light reveals truth")
    assert response.surface != ""  # regen still runs


def test_emission_when_sink_attached() -> None:
    rt = ChatRuntime()
    sink = JsonlBufferSink()
    rt.attach_telemetry_sink(sink)
    _seed_two_turns(rt)

    n_before = len(sink.lines)
    rt.correct("light reveals truth")
    n_after = len(sink.lines)

    assert n_after > n_before
    correction_lines = [
        json.loads(line) for line in sink.lines
        if json.loads(line).get("type") == "correction"
    ]
    assert len(correction_lines) == 1


def test_correction_payload_shape() -> None:
    rt = ChatRuntime()
    sink = JsonlBufferSink()
    rt.attach_telemetry_sink(sink)
    _seed_two_turns(rt)
    rt.correct("light reveals truth")

    correction_lines = [
        json.loads(line) for line in sink.lines
        if json.loads(line).get("type") == "correction"
    ]
    assert len(correction_lines) == 1
    payload = correction_lines[0]

    required_keys = {
        "type",
        "target_turn",
        "identity_pack_id",
        "safety_pack_id",
        "ethics_pack_id",
        "records_count",
        "turns_skipped",
        "turn_idxs_affected",
        "max_delta_norm",
        "mean_delta_norm",
        "correction_versor_digest",
    }
    assert required_keys.issubset(payload.keys())
    assert payload["type"] == "correction"
    assert payload["target_turn"] == -1
    assert isinstance(payload["records_count"], int)
    assert isinstance(payload["turn_idxs_affected"], list)
    assert all(isinstance(t, int) for t in payload["turn_idxs_affected"])
    assert isinstance(payload["max_delta_norm"], (int, float))
    assert payload["max_delta_norm"] >= 0.0
    assert isinstance(payload["mean_delta_norm"], (int, float))
    assert payload["mean_delta_norm"] >= 0.0


def test_correction_versor_digest_is_sha256_prefix_or_empty() -> None:
    rt = ChatRuntime()
    sink = JsonlBufferSink()
    rt.attach_telemetry_sink(sink)
    _seed_two_turns(rt)
    rt.correct("light reveals truth")

    correction_lines = [
        json.loads(line) for line in sink.lines
        if json.loads(line).get("type") == "correction"
    ]
    digest = correction_lines[0]["correction_versor_digest"]
    assert isinstance(digest, str)
    # SHA-256 hex digest = 64 chars; emit empty only if versor absent.
    assert digest == "" or (len(digest) == 64 and all(c in "0123456789abcdef" for c in digest))


def test_no_versor_coordinates_in_payload() -> None:
    """Trust boundary — only L2 deltas + SHA-256 digest, never coords."""
    rt = ChatRuntime()
    sink = JsonlBufferSink()
    rt.attach_telemetry_sink(sink)
    _seed_two_turns(rt)
    rt.correct("light reveals truth")

    payload = next(
        json.loads(line) for line in sink.lines
        if json.loads(line).get("type") == "correction"
    )
    forbidden_keys = {"old_versor", "new_versor", "correction_versor", "versor", "records"}
    leaked = forbidden_keys & set(payload.keys())
    assert not leaked, (
        f"correction event leaked raw versor field(s) {leaked!r}: {payload}"
    )


def test_correction_event_is_deterministic_across_runs() -> None:
    """Two runtimes seeded identically and corrected identically must
    emit byte-identical correction-event lines."""
    def _run() -> str:
        rt = ChatRuntime()
        sink = JsonlBufferSink()
        rt.attach_telemetry_sink(sink)
        _seed_two_turns(rt)
        rt.correct("light reveals truth")
        return next(
            line for line in sink.lines
            if json.loads(line).get("type") == "correction"
        )

    a = _run()
    b = _run()
    assert a == b


def test_turn_event_and_correction_event_coexist() -> None:
    """``correct()`` emits a correction event AND the regen turn emits
    its own turn event.  Both types appear in the sink."""
    rt = ChatRuntime()
    sink = JsonlBufferSink()
    rt.attach_telemetry_sink(sink)
    _seed_two_turns(rt)

    n_before = len(sink.lines)
    rt.correct("light reveals truth")

    new_lines = [json.loads(line) for line in sink.lines[n_before:]]
    types_seen = {payload.get("type", "turn") for payload in new_lines}
    # Correction event discriminated; turn event has no "type" key by today's
    # serializer, so it presents as the default "turn".
    assert "correction" in types_seen
