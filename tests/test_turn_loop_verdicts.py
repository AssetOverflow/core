"""ADR-0035 — turn-loop auto-invocation of SafetyCheck and EthicsCheck.

Observational surfacing: every non-stub turn attaches a SafetyVerdict
and EthicsVerdict to both the ChatResponse and the TurnEvent.  No
behavioral change.  Tests assert presence, shape, and the few
runtime-evidence fields the turn loop actually populates today.
"""

from __future__ import annotations

from chat.runtime import (
    ChatRuntime,
    _hash_identity_manifold,
    _surface_contains_hedge,
)
from core.config import RuntimeConfig
from packs.ethics.check import EthicsVerdict
from packs.safety.check import SafetyVerdict


# ---------- ChatResponse / TurnEvent contract ----------


class TestVerdictsAttachedToResponse:
    def test_chat_response_carries_safety_verdict(self) -> None:
        rt = ChatRuntime(config=RuntimeConfig())
        resp = rt.chat("light is")
        assert isinstance(resp.safety_verdict, SafetyVerdict)
        assert resp.safety_verdict.pack_id == rt.safety_pack.pack_id

    def test_chat_response_carries_ethics_verdict(self) -> None:
        rt = ChatRuntime(config=RuntimeConfig())
        resp = rt.chat("light is")
        assert isinstance(resp.ethics_verdict, EthicsVerdict)
        assert resp.ethics_verdict.pack_id == rt.ethics_pack.pack_id

    def test_turn_event_carries_both_verdicts_when_appended(self) -> None:
        """When the turn loop appends a TurnEvent (non-stub path), the
        event carries both verdicts."""
        rt = ChatRuntime(config=RuntimeConfig())
        rt.chat("light is")
        # Stub paths bypass turn_log by design; only assert when the
        # main path was taken.
        if rt.turn_log:
            event = rt.turn_log[-1]
            assert isinstance(event.safety_verdict, SafetyVerdict)
            assert isinstance(event.ethics_verdict, EthicsVerdict)


# ---------- runtime evidence the turn loop populates ----------


class TestVersorClosureRuntimeCheckable:
    def test_versor_closure_predicate_runtime_checkable_each_turn(self) -> None:
        rt = ChatRuntime(config=RuntimeConfig())
        resp = rt.chat("light is")
        verdict = resp.safety_verdict
        result = _find_safety(verdict, "preserve_versor_closure")
        assert result.runtime_checkable
        assert result.upheld


class TestIdentityOverrideRuntimeCheckable:
    def test_identity_unchanged_upheld_each_turn(self) -> None:
        rt = ChatRuntime(config=RuntimeConfig())
        resp = rt.chat("light is")
        result = _find_safety(resp.safety_verdict, "no_identity_override")
        assert result.runtime_checkable
        assert result.upheld


class TestNoSilentCorrectionRuntimeCheckable:
    def test_default_path_typed_refusal_upheld(self) -> None:
        rt = ChatRuntime(config=RuntimeConfig())
        resp = rt.chat("light is")
        result = _find_safety(resp.safety_verdict, "no_silent_correction")
        assert result.runtime_checkable
        assert result.upheld


# ---------- ethics evidence the turn loop populates ----------


class TestGroundednessSignal:
    def test_acknowledge_uncertainty_runtime_checkable(self) -> None:
        rt = ChatRuntime(config=RuntimeConfig())
        resp = rt.chat("light is")
        result = _find_ethics(resp.ethics_verdict, "acknowledge_uncertainty")
        assert result.runtime_checkable

    def test_disclose_limitations_runtime_checkable(self) -> None:
        rt = ChatRuntime(config=RuntimeConfig())
        resp = rt.chat("light is")
        result = _find_ethics(resp.ethics_verdict, "disclose_limitations")
        assert result.runtime_checkable


# ---------- helpers exercised independently ----------


class TestHashIdentityManifold:
    def test_hash_is_deterministic(self) -> None:
        rt = ChatRuntime(config=RuntimeConfig())
        h1 = _hash_identity_manifold(rt.identity_manifold)
        h2 = _hash_identity_manifold(rt.identity_manifold)
        assert h1 == h2
        assert len(h1) == 64

    def test_pre_turn_hash_matches_post_turn_hash(self) -> None:
        rt = ChatRuntime(config=RuntimeConfig())
        before = _hash_identity_manifold(rt.identity_manifold)
        rt.chat("light is")
        after = _hash_identity_manifold(rt.identity_manifold)
        assert before == after


class TestSurfaceContainsHedge:
    def test_no_hedge_returns_false(self) -> None:
        rt = ChatRuntime(config=RuntimeConfig())
        assert not _surface_contains_hedge(
            "the cat sat on the mat", rt.identity_manifold,
        )

    def test_empty_surface_returns_false(self) -> None:
        rt = ChatRuntime(config=RuntimeConfig())
        assert not _surface_contains_hedge("", rt.identity_manifold)

    def test_known_hedge_phrase_detected(self) -> None:
        rt = ChatRuntime(config=RuntimeConfig())
        prefs = rt.identity_manifold.surface_preferences
        hedge_phrase = prefs.preferred_hedge_soft or prefs.preferred_hedge_strong
        if not hedge_phrase:
            return  # no hedge phrases configured in this pack
        text = f"the answer is {hedge_phrase} that it works"
        assert _surface_contains_hedge(text, rt.identity_manifold)


# ---------- verdict aggregation (no_manipulation always non-checkable) ----------


class TestNoManipulationStructural:
    def test_no_manipulation_runtime_checkable_false_each_turn(self) -> None:
        rt = ChatRuntime(config=RuntimeConfig())
        resp = rt.chat("light is")
        result = _find_ethics(resp.ethics_verdict, "no_manipulation")
        assert not result.runtime_checkable
        assert result.upheld


# ---------- helpers ----------


def _find_safety(verdict: SafetyVerdict, boundary_id: str):
    for r in verdict.results:
        if r.boundary_id == boundary_id:
            return r
    raise AssertionError(f"{boundary_id!r} not in safety verdict")


def _find_ethics(verdict: EthicsVerdict, commitment_id: str):
    for r in verdict.results:
        if r.commitment_id == commitment_id:
            return r
    raise AssertionError(f"{commitment_id!r} not in ethics verdict")
