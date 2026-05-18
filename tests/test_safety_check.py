"""ADR-0032 — SafetyCheck structural surface.

These tests cover the five default predicates (positive + negative
paths), the unknown-boundary fallback, custom predicate registration,
and integration with ``ChatRuntime``.

Mechanics intentionally mirror ``tests/test_identity_packs.py`` /
``tests/test_safety_pack.py`` patterns: small, deterministic, no
fixtures that go through the full cognitive pipeline.  SafetyCheck is
observational; every test asserts on the verdict, not on runtime
behavior.
"""

from __future__ import annotations

from dataclasses import dataclass

from chat.runtime import ChatRuntime
from core.config import RuntimeConfig
from packs.safety.check import (
    SafetyCheck,
    SafetyCheckResult,
    SafetyContext,
    SafetyVerdict,
)
from packs.safety.loader import load_safety_pack


@dataclass(frozen=True)
class _FakeFieldState:
    """Stand-in for FieldState — only ``versor_condition`` is checked."""
    versor_condition: float


# ---------- preserve_versor_closure ----------


class TestVersorClosurePredicate:
    def test_under_threshold_upheld(self) -> None:
        check = SafetyCheck()
        pack = load_safety_pack()
        ctx = SafetyContext(field_state=_FakeFieldState(versor_condition=1.0e-9))
        verdict = check.check(ctx, pack)
        result = _find(verdict, "preserve_versor_closure")
        assert result.upheld
        assert result.runtime_checkable

    def test_at_or_above_threshold_violated(self) -> None:
        check = SafetyCheck()
        pack = load_safety_pack()
        ctx = SafetyContext(field_state=_FakeFieldState(versor_condition=1.0e-3))
        verdict = check.check(ctx, pack)
        result = _find(verdict, "preserve_versor_closure")
        assert not result.upheld
        assert result.runtime_checkable
        assert "preserve_versor_closure" in verdict.violated_boundaries

    def test_missing_field_state_not_runtime_checkable(self) -> None:
        check = SafetyCheck()
        pack = load_safety_pack()
        verdict = check.check(SafetyContext(), pack)
        result = _find(verdict, "preserve_versor_closure")
        assert result.upheld
        assert not result.runtime_checkable


# ---------- no_fabricated_source ----------


class TestNoFabricatedSourcePredicate:
    def test_all_citations_in_allowlist_upheld(self) -> None:
        check = SafetyCheck()
        pack = load_safety_pack()
        allowed = frozenset({"a" * 64, "b" * 64})
        ctx = SafetyContext(
            cited_source_shas=frozenset({"a" * 64}),
            allowed_source_shas=allowed,
        )
        result = _find(check.check(ctx, pack), "no_fabricated_source")
        assert result.upheld
        assert result.runtime_checkable

    def test_unknown_citation_violates(self) -> None:
        check = SafetyCheck()
        pack = load_safety_pack()
        ctx = SafetyContext(
            cited_source_shas=frozenset({"c" * 64}),
            allowed_source_shas=frozenset({"a" * 64}),
        )
        result = _find(check.check(ctx, pack), "no_fabricated_source")
        assert not result.upheld
        assert result.runtime_checkable

    def test_empty_allowlist_not_runtime_checkable(self) -> None:
        check = SafetyCheck()
        pack = load_safety_pack()
        ctx = SafetyContext(
            cited_source_shas=frozenset({"a" * 64}),
            allowed_source_shas=frozenset(),
        )
        result = _find(check.check(ctx, pack), "no_fabricated_source")
        # Empty allowlist → not in use → predicate cannot judge.
        assert result.upheld
        assert not result.runtime_checkable


# ---------- no_silent_correction ----------


class TestNoSilentCorrectionPredicate:
    def test_typed_refusal_upheld(self) -> None:
        check = SafetyCheck()
        pack = load_safety_pack()
        verdict = check.check(SafetyContext(last_refusal_was_typed=True), pack)
        result = _find(verdict, "no_silent_correction")
        assert result.upheld
        assert result.runtime_checkable

    def test_swallowed_refusal_violates(self) -> None:
        check = SafetyCheck()
        pack = load_safety_pack()
        ctx = SafetyContext(last_refusal_was_typed=False)
        result = _find(check.check(ctx, pack), "no_silent_correction")
        assert not result.upheld
        assert result.runtime_checkable


# ---------- no_identity_override ----------


class TestNoIdentityOverridePredicate:
    def test_unchanged_manifold_upheld(self) -> None:
        check = SafetyCheck()
        pack = load_safety_pack()
        h = "a" * 64
        ctx = SafetyContext(
            identity_manifold_hash_before=h,
            identity_manifold_hash_after=h,
        )
        result = _find(check.check(ctx, pack), "no_identity_override")
        assert result.upheld
        assert result.runtime_checkable

    def test_mutated_manifold_violates(self) -> None:
        check = SafetyCheck()
        pack = load_safety_pack()
        ctx = SafetyContext(
            identity_manifold_hash_before="a" * 64,
            identity_manifold_hash_after="b" * 64,
        )
        result = _find(check.check(ctx, pack), "no_identity_override")
        assert not result.upheld
        assert result.runtime_checkable

    def test_missing_hashes_not_runtime_checkable(self) -> None:
        check = SafetyCheck()
        pack = load_safety_pack()
        result = _find(check.check(SafetyContext(), pack), "no_identity_override")
        assert result.upheld
        assert not result.runtime_checkable


# ---------- no_hot_path_repair ----------


class TestNoHotPathRepairPredicate:
    def test_always_upheld_never_runtime_checkable(self) -> None:
        """``no_hot_path_repair`` is structural; runtime cannot judge it.

        The honest answer: enforcement lives in static analysis + code
        review.  SafetyCheck reports this transparently.
        """
        check = SafetyCheck()
        pack = load_safety_pack()
        result = _find(check.check(SafetyContext(), pack), "no_hot_path_repair")
        assert result.upheld
        assert not result.runtime_checkable
        assert "static analysis" in result.reason


# ---------- unknown-boundary fallback ----------


class TestUnknownBoundary:
    def test_unknown_boundary_defaults_to_upheld_not_runtime_checkable(
        self,
    ) -> None:
        # Build a SafetyCheck with NO predicates, then check against the
        # real safety pack.  Every boundary becomes "unknown".
        check = SafetyCheck(predicates={})
        pack = load_safety_pack()
        verdict = check.check(SafetyContext(), pack)
        assert verdict.upheld
        assert verdict.runtime_checkable_count == 0
        for r in verdict.results:
            assert r.upheld
            assert not r.runtime_checkable
            assert "no predicate registered" in r.reason


# ---------- custom predicate registration ----------


class TestCustomPredicateRegistration:
    def test_register_custom_predicate(self) -> None:
        def my_pred(ctx: SafetyContext) -> SafetyCheckResult:
            return SafetyCheckResult(
                boundary_id="my_custom_boundary",
                upheld=False,
                reason="always fails for testing",
                runtime_checkable=True,
            )
        check = SafetyCheck()
        check.register("my_custom_boundary", my_pred)
        # Build a pack-like object with our custom boundary.
        from packs.safety.loader import SafetyPack
        custom_pack = SafetyPack(
            pack_id="custom_test",
            version="1.0.0",
            description="test",
            boundary_ids=frozenset({"my_custom_boundary"}),
            boundary_descriptions={"my_custom_boundary": "test"},
            mastery_report_sha256="",
            ratified=False,
        )
        verdict = check.check(SafetyContext(), custom_pack)
        assert not verdict.upheld
        assert "my_custom_boundary" in verdict.violated_boundaries

    def test_predicate_misreporting_boundary_id_is_corrected(self) -> None:
        # Defensive behavior: if a registered predicate returns a result
        # with the wrong boundary_id, SafetyCheck rebinds it.
        def lying_pred(ctx: SafetyContext) -> SafetyCheckResult:
            return SafetyCheckResult(
                boundary_id="WRONG",
                upheld=True,
                reason="defensive test",
                runtime_checkable=False,
            )
        check = SafetyCheck()
        check.register("no_silent_correction", lying_pred)
        verdict = check.check(SafetyContext(), load_safety_pack())
        result = _find(verdict, "no_silent_correction")
        assert result.boundary_id == "no_silent_correction"


# ---------- verdict aggregation ----------


class TestVerdictAggregation:
    def test_pack_id_recorded(self) -> None:
        verdict = SafetyCheck().check(SafetyContext(), load_safety_pack())
        assert verdict.pack_id == "core_safety_axes_v1"

    def test_results_in_lex_order_on_boundary_id(self) -> None:
        verdict = SafetyCheck().check(SafetyContext(), load_safety_pack())
        ids = [r.boundary_id for r in verdict.results]
        assert ids == sorted(ids)

    def test_runtime_checkable_count_under_default_context(self) -> None:
        verdict = SafetyCheck().check(SafetyContext(), load_safety_pack())
        # With an empty SafetyContext, only ``no_silent_correction`` is
        # runtime-checkable (default last_refusal_was_typed=True).
        assert verdict.runtime_checkable_count == 1


# ---------- ChatRuntime integration ----------


class TestChatRuntimeIntegration:
    def test_runtime_exposes_safety_check(self) -> None:
        rt = ChatRuntime(config=RuntimeConfig())
        assert isinstance(rt.safety_check, SafetyCheck)

    def test_runtime_safety_check_can_evaluate_loaded_pack(self) -> None:
        rt = ChatRuntime(config=RuntimeConfig())
        verdict = rt.safety_check.check(SafetyContext(), rt.safety_pack)
        assert isinstance(verdict, SafetyVerdict)
        assert verdict.pack_id == rt.safety_pack.pack_id
        assert verdict.upheld  # empty ctx → no violations observed


# ---------- helpers ----------


def _find(verdict: SafetyVerdict, boundary_id: str) -> SafetyCheckResult:
    for r in verdict.results:
        if r.boundary_id == boundary_id:
            return r
    raise AssertionError(f"boundary {boundary_id!r} not in verdict")
