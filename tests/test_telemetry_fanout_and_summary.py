"""ADR-0041 — sink fan-out and operator-facing verdict summary.

Two sibling additions:

* ``FanOutSink`` — forwards every emitted line to N sinks; fail-fast
  on the first sink that raises (same error contract as a single
  sink).
* ``format_verdict_summary`` — one-line operator-facing readout of a
  ``TurnVerdicts`` bundle.  Used by ``core chat --show-verdicts``.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from chat.runtime import ChatRuntime
from chat.telemetry import (
    FanOutSink,
    JsonlBufferSink,
    JsonlFileSink,
    format_verdict_summary,
)
from chat.verdicts import TurnVerdicts
from core.config import RuntimeConfig
from core.physics.identity import IdentityScore
from packs.ethics.check import EthicsCheckResult, EthicsVerdict
from packs.safety.check import SafetyCheckResult, SafetyVerdict


# ---------- FanOutSink ----------


class TestFanOutSink:
    def test_forwards_to_all_sinks(self) -> None:
        a = JsonlBufferSink()
        b = JsonlBufferSink()
        fan = FanOutSink(sinks=(a, b))
        fan.emit('{"x":1}')
        fan.emit('{"y":2}')
        assert a.lines == ['{"x":1}', '{"y":2}']
        assert b.lines == ['{"x":1}', '{"y":2}']

    def test_preserves_emission_order(self) -> None:
        a = JsonlBufferSink()
        fan = FanOutSink(sinks=(a,))
        for i in range(5):
            fan.emit(f'{{"i":{i}}}')
        assert a.lines == [f'{{"i":{i}}}' for i in range(5)]

    def test_empty_sinks_tuple_is_noop(self) -> None:
        fan = FanOutSink(sinks=())
        # Must not raise.
        fan.emit('{"x":1}')

    def test_fail_fast_on_first_sink_error(self) -> None:
        """First-error semantics: when sink i raises, sinks i+1..
        do not receive the line.  This preserves audit-signal
        visibility — telemetry failures surface."""
        a = JsonlBufferSink()
        b = JsonlBufferSink()

        class _Boom:
            def emit(self, line: str) -> None:
                raise RuntimeError("boom")

        fan = FanOutSink(sinks=(a, _Boom(), b))
        try:
            fan.emit('{"x":1}')
        except RuntimeError as e:
            assert "boom" in str(e)
        else:
            raise AssertionError("expected RuntimeError to propagate")
        # First sink saw the line; downstream sink after the failure
        # did NOT.
        assert a.lines == ['{"x":1}']
        assert b.lines == []

    def test_composes_with_file_sink(self, tmp_path: Path) -> None:
        target = tmp_path / "audit.jsonl"
        buf = JsonlBufferSink()
        with JsonlFileSink(target) as fsink:
            fan = FanOutSink(sinks=(buf, fsink))
            fan.emit('{"x":1}')
            fan.emit('{"y":2}')
        assert buf.lines == ['{"x":1}', '{"y":2}']
        assert target.read_text(encoding="utf-8") == '{"x":1}\n{"y":2}\n'


# ---------- FanOutSink integrated with runtime ----------


class TestRuntimeWithFanOut:
    def test_runtime_attached_fanout_distributes(self, tmp_path: Path) -> None:
        rt = ChatRuntime(config=RuntimeConfig(), no_load_state=True)
        buf = JsonlBufferSink()
        target = tmp_path / "session.jsonl"
        with JsonlFileSink(target) as fsink:
            rt.attach_telemetry_sink(FanOutSink(sinks=(buf, fsink)))
            rt.chat("light is")
            rt.chat("light is")
        assert len(buf.lines) == 2
        assert len(target.read_text(encoding="utf-8").splitlines()) == 2


# ---------- format_verdict_summary ----------


class TestFormatVerdictSummary:
    def test_none_returns_empty_string(self) -> None:
        assert format_verdict_summary(None) == ""

    def test_clean_turn_summary(self) -> None:
        bundle = _bundle(
            identity_alignment=0.83,
            refusal_emitted=False,
            hedge_injected=False,
        )
        out = format_verdict_summary(bundle)
        assert out.startswith("[") and out.endswith("]")
        assert "identity=0.83" in out
        assert "safety=ok" in out
        assert "ethics=ok" in out
        assert "refusal=-" in out
        assert "hedge=-" in out

    def test_safety_violation_summary(self) -> None:
        bundle = _bundle(
            safety_violated=("preserve_versor_closure",),
            refusal_emitted=True,
        )
        out = format_verdict_summary(bundle)
        assert "safety=VIOLATED:preserve_versor_closure" in out
        assert "refusal=YES" in out

    def test_ethics_violation_summary(self) -> None:
        bundle = _bundle(
            ethics_violated=("acknowledge_uncertainty",),
            hedge_injected=True,
        )
        out = format_verdict_summary(bundle)
        assert "ethics=VIOLATED:acknowledge_uncertainty" in out
        assert "hedge=YES" in out

    def test_multiple_violations_lex_sorted(self) -> None:
        bundle = _bundle(
            safety_violated=("zzz_late", "aaa_early"),
        )
        out = format_verdict_summary(bundle)
        assert "safety=VIOLATED:aaa_early,zzz_late" in out

    def test_no_identity_score_shows_dash(self) -> None:
        bundle = TurnVerdicts(
            identity_score=None,
            safety_verdict=None,
            ethics_verdict=None,
            refusal_emitted=False,
            hedge_injected=False,
        )
        out = format_verdict_summary(bundle)
        assert "identity=-" in out

    def test_response_from_runtime_formats(self) -> None:
        """End-to-end: a real ChatResponse.verdicts bundle formats
        without error."""
        rt = ChatRuntime(config=RuntimeConfig(), no_load_state=True)
        resp = rt.chat("light is")
        out = format_verdict_summary(resp.verdicts)
        # Stub-path turn has no identity_score but valid verdicts.
        assert out.startswith("[") and out.endswith("]")
        assert "refusal=" in out
        assert "hedge=" in out


# ---------- helpers ----------


def _bundle(
    *,
    identity_alignment: float | None = 1.0,
    safety_violated: tuple = (),
    ethics_violated: tuple = (),
    refusal_emitted: bool = False,
    hedge_injected: bool = False,
) -> TurnVerdicts:
    identity_score = None
    if identity_alignment is not None:
        # IdentityScore.alignment forces 1.0 when deviation_axes is
        # empty; pass a non-empty set so the formatter sees the
        # requested alignment value.
        deviation = (
            frozenset() if identity_alignment >= 1.0 else frozenset({"_test_axis"})
        )
        identity_score = IdentityScore(
            score=identity_alignment,
            flagged=False,
            deviation_axes=deviation,
            trajectory_id="test",
        )
    safety = SafetyVerdict(
        pack_id="test_safety",
        results=(),
        upheld=not safety_violated,
        violated_boundaries=frozenset(safety_violated),
        runtime_checkable_count=0,
    )
    ethics = EthicsVerdict(
        pack_id="test_ethics",
        results=(),
        upheld=not ethics_violated,
        violated_commitments=frozenset(ethics_violated),
        runtime_checkable_count=0,
    )
    return TurnVerdicts(
        identity_score=identity_score,
        safety_verdict=safety,
        ethics_verdict=ethics,
        refusal_emitted=refusal_emitted,
        hedge_injected=hedge_injected,
    )
