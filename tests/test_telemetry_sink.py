"""ADR-0040 — structured-logging sink for turn-event audit.

Verifies:

* deterministic JSONL serialisation (same event → byte-identical line);
* redact-by-default trust boundary (no surfaces or tokens unless
  caller opts in);
* sink protocol via in-memory and file-backed implementations;
* runtime attachment auto-emits on both main and stub paths;
* mutual exclusion / hedge / refusal flags ride the wire correctly.
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from chat.runtime import ChatRuntime
from chat.telemetry import (
    JsonlBufferSink,
    JsonlFileSink,
    format_turn_event_jsonl,
    serialize_turn_event,
)
from chat.verdicts import TurnVerdicts
from core.config import RuntimeConfig
from core.physics.identity import TurnEvent
from packs.ethics.check import EthicsCheckResult
from packs.safety.check import SafetyCheckResult


# ---------- pure serializer ----------


class TestSerializeTurnEvent:
    def test_metadata_only_by_default(self) -> None:
        rt = ChatRuntime(config=RuntimeConfig())
        rt.chat("light is")
        event = rt.turn_log[-1]
        out = serialize_turn_event(event)
        # No content fields by default.
        assert "input_tokens" not in out
        assert "surface" not in out
        assert "walk_surface" not in out
        assert "articulation_surface" not in out

    def test_include_content_opts_in(self) -> None:
        rt = ChatRuntime(config=RuntimeConfig())
        rt.chat("light is")
        event = rt.turn_log[-1]
        out = serialize_turn_event(event, include_content=True)
        assert "input_tokens" in out
        assert "surface" in out
        assert "walk_surface" in out
        assert "articulation_surface" in out

    def test_pack_ids_emitted(self) -> None:
        rt = ChatRuntime(config=RuntimeConfig())
        rt.chat("light is")
        event = rt.turn_log[-1]
        out = serialize_turn_event(
            event,
            safety_pack_id="my_safety",
            ethics_pack_id="my_ethics",
            identity_pack_id="my_identity",
        )
        assert out["safety_pack_id"] == "my_safety"
        assert out["ethics_pack_id"] == "my_ethics"
        assert out["identity_pack_id"] == "my_identity"

    def test_remediation_flags_default_false(self) -> None:
        rt = ChatRuntime(config=RuntimeConfig())
        rt.chat("light is")
        event = rt.turn_log[-1]
        out = serialize_turn_event(event)
        assert out["refusal_emitted"] is False
        assert out["hedge_injected"] is False

    def test_refusal_flag_rides_the_wire(self) -> None:
        rt = ChatRuntime(config=RuntimeConfig())

        def _failing(ctx):  # noqa: ANN001
            return SafetyCheckResult(
                boundary_id="preserve_versor_closure",
                upheld=False,
                reason="forced",
                runtime_checkable=True,
            )

        rt.safety_check.register("preserve_versor_closure", _failing)
        rt.chat("light is")
        event = rt.turn_log[-1]
        out = serialize_turn_event(event)
        assert out["refusal_emitted"] is True
        assert "preserve_versor_closure" in out["safety_violated"]
        assert out["safety_upheld"] is False

    def test_stub_path_flag(self) -> None:
        rt = ChatRuntime(config=RuntimeConfig())
        rt.chat("light is")
        event = rt.turn_log[-1]
        out = serialize_turn_event(event)
        assert out["stub_path"] is True

    def test_timestamp_opt_in(self) -> None:
        rt = ChatRuntime(config=RuntimeConfig())
        rt.chat("light is")
        event = rt.turn_log[-1]
        without = serialize_turn_event(event)
        assert "timestamp" not in without
        withts = serialize_turn_event(event, timestamp="2026-05-17T00:00:00Z")
        assert withts["timestamp"] == "2026-05-17T00:00:00Z"


# ---------- deterministic JSONL ----------


class TestFormatTurnEventJsonl:
    def test_deterministic_output(self) -> None:
        rt = ChatRuntime(config=RuntimeConfig())
        rt.chat("light is")
        event = rt.turn_log[-1]
        a = format_turn_event_jsonl(event, safety_pack_id="x", ethics_pack_id="y")
        b = format_turn_event_jsonl(event, safety_pack_id="x", ethics_pack_id="y")
        assert a == b

    def test_keys_alphabetised(self) -> None:
        rt = ChatRuntime(config=RuntimeConfig())
        rt.chat("light is")
        event = rt.turn_log[-1]
        line = format_turn_event_jsonl(event)
        parsed = json.loads(line)
        keys = list(parsed.keys())
        assert keys == sorted(keys)

    def test_no_trailing_newline(self) -> None:
        rt = ChatRuntime(config=RuntimeConfig())
        rt.chat("light is")
        event = rt.turn_log[-1]
        line = format_turn_event_jsonl(event)
        assert not line.endswith("\n")


# ---------- sink protocol implementations ----------


class TestJsonlBufferSink:
    def test_emit_captures_lines(self) -> None:
        sink = JsonlBufferSink()
        sink.emit('{"a":1}')
        sink.emit('{"b":2}')
        assert sink.lines == ['{"a":1}', '{"b":2}']

    def test_default_lines_empty(self) -> None:
        assert JsonlBufferSink().lines == []


class TestJsonlFileSink:
    def test_appends_with_newlines(self, tmp_path: Path) -> None:
        target = tmp_path / "turns.jsonl"
        sink = JsonlFileSink(target)
        sink.emit('{"a":1}')
        sink.emit('{"b":2}')
        sink.close()
        content = target.read_text(encoding="utf-8")
        assert content == '{"a":1}\n{"b":2}\n'

    def test_creates_parent_directory(self, tmp_path: Path) -> None:
        target = tmp_path / "nested" / "dir" / "turns.jsonl"
        sink = JsonlFileSink(target)
        sink.emit('{"a":1}')
        sink.close()
        assert target.is_file()

    def test_context_manager_closes_handle(self, tmp_path: Path) -> None:
        target = tmp_path / "turns.jsonl"
        with JsonlFileSink(target) as sink:
            sink.emit('{"a":1}')
        # Re-open in append mode — verifies the prior handle closed.
        sink2 = JsonlFileSink(target)
        sink2.emit('{"b":2}')
        sink2.close()
        assert target.read_text(encoding="utf-8") == '{"a":1}\n{"b":2}\n'

    def test_emit_flushes_each_line(self, tmp_path: Path) -> None:
        """Eager flush — a crashed runtime should still have prior
        turns durable on disk."""
        target = tmp_path / "turns.jsonl"
        sink = JsonlFileSink(target)
        sink.emit('{"a":1}')
        # Read while the sink is still open; flush should have made
        # the line visible.
        assert target.read_text(encoding="utf-8") == '{"a":1}\n'
        sink.close()


# ---------- runtime auto-emission ----------


class TestRuntimeAutoEmit:
    def test_no_sink_attached_is_noop(self) -> None:
        rt = ChatRuntime(config=RuntimeConfig())
        # No sink attached — chat() should not raise and turn_log
        # should still be populated.
        rt.chat("light is")
        assert rt.turn_log

    def test_attached_sink_receives_one_line_per_turn(self) -> None:
        rt = ChatRuntime(config=RuntimeConfig())
        sink = JsonlBufferSink()
        rt.attach_telemetry_sink(sink)
        rt.chat("light is")
        rt.chat("light is")
        assert len(sink.lines) == 2

    def test_emitted_line_is_parseable_jsonl(self) -> None:
        rt = ChatRuntime(config=RuntimeConfig())
        sink = JsonlBufferSink()
        rt.attach_telemetry_sink(sink)
        rt.chat("light is")
        parsed = json.loads(sink.lines[-1])
        assert "turn" in parsed
        assert "refusal_emitted" in parsed
        assert "hedge_injected" in parsed
        assert "stub_path" in parsed

    def test_default_attach_redacts_content(self) -> None:
        rt = ChatRuntime(config=RuntimeConfig())
        sink = JsonlBufferSink()
        rt.attach_telemetry_sink(sink)
        rt.chat("light is")
        parsed = json.loads(sink.lines[-1])
        assert "input_tokens" not in parsed
        assert "surface" not in parsed
        assert "walk_surface" not in parsed

    def test_include_content_opt_in_at_attach(self) -> None:
        rt = ChatRuntime(config=RuntimeConfig())
        sink = JsonlBufferSink()
        rt.attach_telemetry_sink(sink, include_content=True)
        rt.chat("light is")
        parsed = json.loads(sink.lines[-1])
        assert "input_tokens" in parsed
        assert "surface" in parsed

    def test_detach_via_none_stops_emission(self) -> None:
        rt = ChatRuntime(config=RuntimeConfig())
        sink = JsonlBufferSink()
        rt.attach_telemetry_sink(sink)
        rt.chat("light is")
        rt.attach_telemetry_sink(None)
        rt.chat("light is")
        assert len(sink.lines) == 1

    def test_pack_ids_in_emitted_line(self) -> None:
        rt = ChatRuntime(config=RuntimeConfig())
        sink = JsonlBufferSink()
        rt.attach_telemetry_sink(sink)
        rt.chat("light is")
        parsed = json.loads(sink.lines[-1])
        assert parsed["safety_pack_id"] == rt.safety_pack.pack_id
        assert parsed["ethics_pack_id"] == rt.ethics_pack_id
        assert parsed["identity_pack_id"] == rt.identity_pack_id

    def test_stub_path_also_emits(self) -> None:
        """ADR-0039 made stub paths populate turn_log; ADR-0040's
        sink must emit for stub turns too."""
        rt = ChatRuntime(config=RuntimeConfig())
        sink = JsonlBufferSink()
        rt.attach_telemetry_sink(sink)
        rt.chat("light is")
        parsed = json.loads(sink.lines[-1])
        assert parsed["stub_path"] is True

    def test_refusal_visible_via_sink(self) -> None:
        rt = ChatRuntime(config=RuntimeConfig())

        def _failing(ctx):  # noqa: ANN001
            return SafetyCheckResult(
                boundary_id="preserve_versor_closure",
                upheld=False,
                reason="forced",
                runtime_checkable=True,
            )

        rt.safety_check.register("preserve_versor_closure", _failing)
        sink = JsonlBufferSink()
        rt.attach_telemetry_sink(sink)
        rt.chat("light is")
        parsed = json.loads(sink.lines[-1])
        assert parsed["refusal_emitted"] is True
        assert "preserve_versor_closure" in parsed["safety_violated"]

    def test_sink_errors_are_not_swallowed(self) -> None:
        """Telemetry failures should surface, not silently drop the
        audit signal."""
        rt = ChatRuntime(config=RuntimeConfig())

        class _ExplodingSink:
            def emit(self, line: str) -> None:
                raise RuntimeError("sink down")

        rt.attach_telemetry_sink(_ExplodingSink())
        try:
            rt.chat("light is")
        except RuntimeError as e:
            assert "sink down" in str(e)
        else:
            raise AssertionError("expected sink error to propagate")


# ---------- file-sink round trip ----------


class TestFileSinkRoundTrip:
    def test_full_session_round_trips(self, tmp_path: Path) -> None:
        target = tmp_path / "session.jsonl"
        rt = ChatRuntime(config=RuntimeConfig())
        with JsonlFileSink(target) as sink:
            rt.attach_telemetry_sink(sink)
            rt.chat("light is")
            rt.chat("light is")
        lines = target.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 2
        parsed = [json.loads(line) for line in lines]
        # Each line is a complete audit record regardless of which
        # turn path produced it (cold-start may seed enough vault
        # state that later turns leave the stub path).
        for p in parsed:
            assert "stub_path" in p
            assert isinstance(p["stub_path"], bool)
            assert "safety_upheld" in p
            assert "ethics_upheld" in p
            assert "refusal_emitted" in p
            assert "hedge_injected" in p


# ---------- ad-hoc event serialisation (no runtime needed) ----------


class TestStandaloneEventSerialisation:
    def test_minimal_event_serialises(self) -> None:
        """A bare TurnEvent (no verdicts) should still serialise
        cleanly — the boundary copes with sparse data."""
        event = TurnEvent(
            turn=0,
            input_tokens=("x",),
            surface="s",
            walk_surface="w",
            articulation_surface="a",
            dialogue_role="assert",
            identity_score=None,
            cycle_cost_total=0.0,
            vault_hits=0,
            versor_condition=0.0,
            flagged=False,
        )
        out = serialize_turn_event(event)
        assert out["turn"] == 0
        assert out["refusal_emitted"] is False
        assert out["hedge_injected"] is False

    def test_hedge_flag_from_bundle(self) -> None:
        bundle = TurnVerdicts(
            identity_score=None,
            safety_verdict=None,
            ethics_verdict=None,
            refusal_emitted=False,
            hedge_injected=True,
        )
        event = TurnEvent(
            turn=1,
            input_tokens=("x",),
            surface="s",
            walk_surface="w",
            articulation_surface="a",
            dialogue_role="assert",
            identity_score=None,
            cycle_cost_total=0.0,
            vault_hits=0,
            versor_condition=0.0,
            flagged=False,
            verdicts=bundle,
        )
        out = serialize_turn_event(event)
        assert out["hedge_injected"] is True
