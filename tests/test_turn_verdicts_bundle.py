"""ADR-0039 — audit completeness: TurnVerdicts bundle, stub-path
TurnEvent emission, hedge_injected signal.

The bundle replaces the per-field correlation pattern downstream
audit consumers had to do (read identity_score, safety_verdict,
ethics_verdict, then infer remediation from surface text).  The
remediation flags ``refusal_emitted`` and ``hedge_injected`` make
the runtime's decisions auditable without text inspection.
"""

from __future__ import annotations

from dataclasses import replace

from chat.runtime import ChatRuntime, _UNKNOWN_DOMAIN_SURFACE
from chat.verdicts import TurnVerdicts
from core.config import RuntimeConfig
from packs.ethics.check import EthicsCheckResult, EthicsVerdict
from packs.safety.check import SafetyCheckResult, SafetyVerdict


# ---------- TurnVerdicts shape ----------


class TestTurnVerdictsShape:
    def test_construct_with_required_fields(self) -> None:
        v = TurnVerdicts(
            identity_score=None,
            safety_verdict=None,
            ethics_verdict=None,
            refusal_emitted=False,
            hedge_injected=False,
        )
        assert v.refusal_emitted is False
        assert v.hedge_injected is False

    def test_is_frozen(self) -> None:
        v = TurnVerdicts(
            identity_score=None,
            safety_verdict=None,
            ethics_verdict=None,
            refusal_emitted=False,
            hedge_injected=False,
        )
        try:
            v.refusal_emitted = True  # type: ignore[misc]
        except (AttributeError, Exception):
            return
        else:
            raise AssertionError("TurnVerdicts should be frozen")


# ---------- ChatResponse and TurnEvent carry the bundle ----------


class TestBundleAttachment:
    def test_chat_response_carries_verdicts_bundle(self) -> None:
        rt = ChatRuntime(config=RuntimeConfig())
        resp = rt.chat("light is")
        assert isinstance(resp.verdicts, TurnVerdicts)
        # Bundle's individual verdicts match the per-field versions.
        assert resp.verdicts.safety_verdict is resp.safety_verdict
        assert resp.verdicts.ethics_verdict is resp.ethics_verdict

    def test_turn_event_carries_verdicts_bundle(self) -> None:
        rt = ChatRuntime(config=RuntimeConfig())
        rt.chat("light is")
        assert rt.turn_log, "stub path should now append TurnEvent (ADR-0039)"
        event = rt.turn_log[-1]
        assert isinstance(event.verdicts, TurnVerdicts)


# ---------- stub-path TurnEvent emission (ADR-0039) ----------


class TestStubPathTurnEvent:
    def test_stub_path_appends_turn_event(self) -> None:
        rt = ChatRuntime(config=RuntimeConfig())
        before = len(rt.turn_log)
        resp = rt.chat("light is")
        # Cold start with no vault hits → stub path fires.
        assert resp.walk_surface == _UNKNOWN_DOMAIN_SURFACE
        assert len(rt.turn_log) == before + 1

    def test_stub_event_records_unknown_walk_surface(self) -> None:
        rt = ChatRuntime(config=RuntimeConfig())
        rt.chat("light is")
        event = rt.turn_log[-1]
        assert event.walk_surface == _UNKNOWN_DOMAIN_SURFACE
        assert event.articulation_surface == _UNKNOWN_DOMAIN_SURFACE

    def test_stub_event_carries_input_tokens(self) -> None:
        rt = ChatRuntime(config=RuntimeConfig())
        rt.chat("light is")
        event = rt.turn_log[-1]
        assert event.input_tokens, "stub TurnEvent must record input tokens"

    def test_stub_event_identity_score_is_none(self) -> None:
        """No reasoning trajectory ran on stub path, so no
        IdentityScore is computed."""
        rt = ChatRuntime(config=RuntimeConfig())
        rt.chat("light is")
        event = rt.turn_log[-1]
        assert event.identity_score is None

    def test_stub_event_versor_condition_recorded(self) -> None:
        rt = ChatRuntime(config=RuntimeConfig())
        rt.chat("light is")
        event = rt.turn_log[-1]
        assert isinstance(event.versor_condition, float)


# ---------- refusal_emitted flag ----------


class TestRefusalEmittedFlag:
    def test_no_violation_flag_is_false(self) -> None:
        rt = ChatRuntime(config=RuntimeConfig())
        resp = rt.chat("light is")
        assert resp.verdicts.refusal_emitted is False

    def test_safety_violation_sets_flag(self) -> None:
        rt = ChatRuntime(config=RuntimeConfig())

        def _failing(ctx):  # noqa: ANN001
            return SafetyCheckResult(
                boundary_id="preserve_versor_closure",
                upheld=False,
                reason="forced",
                runtime_checkable=True,
            )

        rt.safety_check.register("preserve_versor_closure", _failing)
        resp = rt.chat("light is")
        assert resp.verdicts.refusal_emitted is True
        # And the flag matches the surface state.
        assert resp.verdicts.refusal_emitted == (resp.surface != resp.walk_surface)

    def test_flag_appears_on_turn_event_too(self) -> None:
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
        assert event.verdicts.refusal_emitted is True


# ---------- hedge_injected flag ----------


class TestHedgeInjectedFlag:
    def test_no_opt_in_flag_is_false(self) -> None:
        rt = ChatRuntime(config=RuntimeConfig())
        resp = rt.chat("light is")
        assert resp.verdicts.hedge_injected is False

    def test_stub_path_never_sets_hedge_injected(self) -> None:
        """Even with opted-in hedge_commitments and a forced
        violation, the stub path must report hedge_injected=False
        (stub never hedges — the unknown-domain marker is already
        a disclosure)."""
        rt = ChatRuntime(config=RuntimeConfig())
        rt.ethics_pack = replace(
            rt.ethics_pack,
            hedge_commitments=frozenset({"acknowledge_uncertainty"}),
        )

        def _failing_ethics(ctx):  # noqa: ANN001
            return EthicsCheckResult(
                commitment_id="acknowledge_uncertainty",
                upheld=False,
                reason="forced",
                runtime_checkable=True,
            )

        rt.ethics_check.register("acknowledge_uncertainty", _failing_ethics)
        resp = rt.chat("light is")
        if resp.walk_surface == _UNKNOWN_DOMAIN_SURFACE:
            assert resp.verdicts.hedge_injected is False


# ---------- mutual exclusion refusal vs hedge in the bundle ----------


class TestRemediationMutualExclusion:
    def test_refusal_and_hedge_never_both_true(self) -> None:
        """The runtime contract: refusal supersedes hedge.  When both
        a runtime-checkable safety violation AND an opted-in ethics
        hedge would fire, refusal wins and hedge_injected stays
        False."""
        rt = ChatRuntime(config=RuntimeConfig())
        rt.ethics_pack = replace(
            rt.ethics_pack,
            hedge_commitments=frozenset({"acknowledge_uncertainty"}),
        )

        def _failing_safety(ctx):  # noqa: ANN001
            return SafetyCheckResult(
                boundary_id="preserve_versor_closure",
                upheld=False,
                reason="forced",
                runtime_checkable=True,
            )

        def _failing_ethics(ctx):  # noqa: ANN001
            return EthicsCheckResult(
                commitment_id="acknowledge_uncertainty",
                upheld=False,
                reason="forced",
                runtime_checkable=True,
            )

        rt.safety_check.register("preserve_versor_closure", _failing_safety)
        rt.ethics_check.register("acknowledge_uncertainty", _failing_ethics)
        resp = rt.chat("light is")
        assert resp.verdicts.refusal_emitted is True
        assert resp.verdicts.hedge_injected is False


# ---------- response and event bundles agree ----------


class TestBundleConsistency:
    def test_response_and_event_bundle_are_consistent(self) -> None:
        """The TurnVerdicts on ChatResponse and TurnEvent for the same
        turn carry the same remediation flags and reference the same
        underlying verdicts."""
        rt = ChatRuntime(config=RuntimeConfig())
        resp = rt.chat("light is")
        event = rt.turn_log[-1]
        assert resp.verdicts.refusal_emitted == event.verdicts.refusal_emitted
        assert resp.verdicts.hedge_injected == event.verdicts.hedge_injected
        assert resp.verdicts.safety_verdict is event.verdicts.safety_verdict
        assert resp.verdicts.ethics_verdict is event.verdicts.ethics_verdict
