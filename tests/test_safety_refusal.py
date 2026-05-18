"""ADR-0036 — typed refusal on runtime-checkable safety violation.

The refusal surface:

* replaces ``ChatResponse.surface`` with a deterministic typed string,
* leaves ``walk_surface`` and ``articulation_surface`` intact (audit),
* fires only on safety violations (ethics is observational at v1),
* fires only on ``runtime_checkable=True`` results
  (no-evidence predicates never refuse),
* sets ``runtime._last_refusal_was_typed = True`` so the next turn's
  ``no_silent_correction`` predicate has live evidence.
"""

from __future__ import annotations

from chat.refusal import (
    TYPED_REFUSAL_PREFIX,
    build_refusal_surface,
    is_typed_refusal,
    violated_runtime_checkable,
)
from chat.runtime import ChatRuntime
from core.config import RuntimeConfig
from packs.safety.check import SafetyCheckResult, SafetyVerdict


# ---------- pure-function refusal builder ----------


class TestBuildRefusalSurface:
    def test_none_verdict_returns_none(self) -> None:
        assert build_refusal_surface(None) is None

    def test_all_upheld_returns_none(self) -> None:
        verdict = _verdict(
            _result("preserve_versor_closure", upheld=True, runtime_checkable=True),
            _result("no_silent_correction", upheld=True, runtime_checkable=True),
        )
        assert build_refusal_surface(verdict) is None

    def test_non_runtime_checkable_violation_does_not_refuse(self) -> None:
        """A predicate that lacks evidence (runtime_checkable=False) and
        reports upheld=False must NOT trigger refusal — by design,
        no-evidence predicates default to ``upheld=True`` in the
        check loop, but even if a deployment forces ``upheld=False``
        without evidence, refusal should not fire."""
        verdict = _verdict(
            _result("no_fabricated_source", upheld=False, runtime_checkable=False),
        )
        assert build_refusal_surface(verdict) is None

    def test_runtime_checkable_violation_returns_typed_surface(self) -> None:
        verdict = _verdict(
            _result("preserve_versor_closure", upheld=False, runtime_checkable=True),
        )
        out = build_refusal_surface(verdict)
        assert out is not None
        assert out.startswith(TYPED_REFUSAL_PREFIX)
        assert "preserve_versor_closure" in out

    def test_refusal_is_deterministic(self) -> None:
        verdict = _verdict(
            _result("preserve_versor_closure", upheld=False, runtime_checkable=True),
            _result("no_silent_correction", upheld=False, runtime_checkable=True),
        )
        first = build_refusal_surface(verdict)
        second = build_refusal_surface(verdict)
        assert first == second

    def test_refusal_lists_boundaries_in_lex_order(self) -> None:
        verdict = _verdict(
            _result("zzz_late", upheld=False, runtime_checkable=True),
            _result("aaa_early", upheld=False, runtime_checkable=True),
        )
        out = build_refusal_surface(verdict)
        assert out is not None
        assert out.index("aaa_early") < out.index("zzz_late")


class TestViolatedRuntimeCheckable:
    def test_filters_non_checkable(self) -> None:
        verdict = _verdict(
            _result("a", upheld=False, runtime_checkable=False),
            _result("b", upheld=False, runtime_checkable=True),
        )
        assert violated_runtime_checkable(verdict) == ("b",)

    def test_filters_upheld(self) -> None:
        verdict = _verdict(
            _result("a", upheld=True, runtime_checkable=True),
            _result("b", upheld=False, runtime_checkable=True),
        )
        assert violated_runtime_checkable(verdict) == ("b",)

    def test_empty_verdict_returns_empty(self) -> None:
        verdict = _verdict()
        assert violated_runtime_checkable(verdict) == ()


class TestIsTypedRefusal:
    def test_typed_refusal_detected(self) -> None:
        surface = TYPED_REFUSAL_PREFIX + "preserve_versor_closure"
        assert is_typed_refusal(surface)

    def test_ordinary_surface_not_a_refusal(self) -> None:
        assert not is_typed_refusal("light is")
        assert not is_typed_refusal("")


# ---------- ChatRuntime integration ----------


class TestRuntimeRefusalMainPath:
    def test_no_violation_returns_ordinary_surface(self) -> None:
        rt = ChatRuntime(config=RuntimeConfig())
        resp = rt.chat("light is")
        # No predicate forced to fail, so surface should NOT be a
        # typed refusal.  (Stub path may produce the unknown-domain
        # surface; both are non-refusal.)
        assert not is_typed_refusal(resp.surface)

    def test_forced_violation_emits_typed_refusal(self) -> None:
        rt = ChatRuntime(config=RuntimeConfig())
        _force_violation(rt, "preserve_versor_closure")
        resp = rt.chat("light is")
        assert is_typed_refusal(resp.surface)
        assert "preserve_versor_closure" in resp.surface

    def test_refusal_preserves_walk_surface(self) -> None:
        """walk_surface retains the original token-walk evidence even
        when the user-facing surface is replaced by a refusal."""
        rt = ChatRuntime(config=RuntimeConfig())
        _force_violation(rt, "preserve_versor_closure")
        resp = rt.chat("light is")
        if not is_typed_refusal(resp.surface):
            return  # stub path; tested separately
        assert not is_typed_refusal(resp.walk_surface)

    def test_refusal_preserves_articulation_surface(self) -> None:
        rt = ChatRuntime(config=RuntimeConfig())
        _force_violation(rt, "preserve_versor_closure")
        resp = rt.chat("light is")
        if not is_typed_refusal(resp.surface):
            return
        assert not is_typed_refusal(resp.articulation_surface)

    def test_refusal_still_attaches_verdicts(self) -> None:
        rt = ChatRuntime(config=RuntimeConfig())
        _force_violation(rt, "preserve_versor_closure")
        resp = rt.chat("light is")
        assert resp.safety_verdict is not None
        assert resp.ethics_verdict is not None

    def test_refusal_sets_last_refusal_was_typed(self) -> None:
        rt = ChatRuntime(config=RuntimeConfig())
        # Sanity: default is True before any refusal.
        assert rt._last_refusal_was_typed is True
        _force_violation(rt, "preserve_versor_closure")
        rt.chat("light is")
        # After a typed refusal, the flag remains True so the
        # ``no_silent_correction`` predicate has live evidence next turn.
        assert rt._last_refusal_was_typed is True

    def test_turn_event_surface_is_refusal_when_refused(self) -> None:
        rt = ChatRuntime(config=RuntimeConfig())
        _force_violation(rt, "preserve_versor_closure")
        rt.chat("light is")
        if not rt.turn_log:
            return  # stub path; bypasses turn_log
        event = rt.turn_log[-1]
        assert is_typed_refusal(event.surface)
        # And walk_surface is retained on the event for audit.
        assert not is_typed_refusal(event.walk_surface)


# ---------- Ethics violations must NOT trigger refusal ----------


class TestEthicsViolationDoesNotRefuse:
    def test_ethics_violation_audit_only(self) -> None:
        """Ethics is observational at v1.  Even a runtime-checkable
        ethics violation must NOT produce a typed refusal surface —
        the audit verdict still attaches but the user-facing surface
        is unchanged."""
        rt = ChatRuntime(config=RuntimeConfig())
        # Force an ethics predicate to fail with runtime_checkable=True.
        from packs.ethics.check import EthicsCheckResult

        def _failing_ethics(ctx):  # noqa: ANN001 — predicate signature
            return EthicsCheckResult(
                commitment_id="acknowledge_uncertainty",
                upheld=False,
                reason="forced for test",
                runtime_checkable=True,
            )

        rt.ethics_check.register("acknowledge_uncertainty", _failing_ethics)
        resp = rt.chat("light is")
        assert not is_typed_refusal(resp.surface)


# ---------- Stub path refusal ----------


class TestStubPathRefusal:
    def test_stub_path_refusal_replaces_unknown_domain_surface(self) -> None:
        """When the stub path triggers AND safety violation fires, the
        typed refusal replaces the unknown-domain surface."""
        rt = ChatRuntime(config=RuntimeConfig())
        _force_violation(rt, "preserve_versor_closure")
        # ``light is`` may or may not hit the stub path depending on
        # vault state; regardless, if a violation is forced, the
        # response surface must be a typed refusal.
        resp = rt.chat("light is")
        assert is_typed_refusal(resp.surface)


# ---------- helpers ----------


def _result(
    boundary_id: str,
    *,
    upheld: bool,
    runtime_checkable: bool,
) -> SafetyCheckResult:
    return SafetyCheckResult(
        boundary_id=boundary_id,
        upheld=upheld,
        reason="test",
        runtime_checkable=runtime_checkable,
    )


def _verdict(*results: SafetyCheckResult) -> SafetyVerdict:
    violated = frozenset(r.boundary_id for r in results if not r.upheld)
    return SafetyVerdict(
        pack_id="test_pack",
        results=tuple(results),
        upheld=not violated,
        violated_boundaries=violated,
        runtime_checkable_count=sum(1 for r in results if r.runtime_checkable),
    )


def _force_violation(rt: ChatRuntime, boundary_id: str) -> None:
    """Register a synthetic predicate that always fails for ``boundary_id``."""

    def _failing(ctx):  # noqa: ANN001 — predicate signature
        return SafetyCheckResult(
            boundary_id=boundary_id,
            upheld=False,
            reason="forced for test",
            runtime_checkable=True,
        )

    rt.safety_check.register(boundary_id, _failing)
