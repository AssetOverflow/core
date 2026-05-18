"""ADR-0038 — hedge injection as a runtime-level affordance.

Distinct from refusal:

* Refusal *replaces* the surface (ADR-0036/0037).
* Hedge injection *prepends* the manifold's hedge phrase, preserving
  the original surface content.

Opt-in is per-commitment via ``EthicsPack.hedge_commitments``.
Mutually exclusive with ``refusal_commitments`` at load time.
"""

from __future__ import annotations

from dataclasses import replace

from chat.refusal import (
    build_hedge_prefix,
    inject_hedge,
    is_typed_refusal,
    should_inject_hedge,
)
from chat.runtime import ChatRuntime
from core.config import RuntimeConfig
from packs.ethics.check import EthicsCheckResult, EthicsVerdict
from packs.ethics.loader import EthicsPack, EthicsPackError, load_ethics_pack
from packs.safety.check import SafetyCheckResult


# ---------- loader bounds ----------


class TestHedgeCommitmentsLoaderValidation:
    def test_default_pack_has_empty_hedge_commitments(self) -> None:
        pack = load_ethics_pack()
        assert pack.hedge_commitments == frozenset()

    def test_unknown_id_in_hedge_commitments_is_rejected(self, tmp_path) -> None:
        bad = tmp_path / "bad_hedge_v1.json"
        bad.write_text(
            '{"pack_id":"bad_hedge_v1","version":"1.0.0","description":"x",'
            '"schema_version":"1.0.0","domain":"custom",'
            '"commitment_ids":["a"],"hedge_commitments":["not_declared"]}'
        )
        try:
            load_ethics_pack(
                "bad_hedge_v1",
                search_paths=(tmp_path,),
                require_ratified=False,
            )
        except EthicsPackError as e:
            assert "not a declared commitment_id" in str(e)
        else:
            raise AssertionError("expected EthicsPackError")

    def test_mutual_exclusion_refusal_and_hedge_rejected(self, tmp_path) -> None:
        """A commitment cannot be in both refusal_commitments and
        hedge_commitments — the two remediations are mutually
        exclusive per commitment."""
        bad = tmp_path / "both_v1.json"
        bad.write_text(
            '{"pack_id":"both_v1","version":"1.0.0","description":"x",'
            '"schema_version":"1.0.0","domain":"custom",'
            '"commitment_ids":["a","b"],'
            '"refusal_commitments":["a"],"hedge_commitments":["a"]}'
        )
        try:
            load_ethics_pack(
                "both_v1",
                search_paths=(tmp_path,),
                require_ratified=False,
            )
        except EthicsPackError as e:
            assert "cannot appear in both" in str(e)
        else:
            raise AssertionError("expected EthicsPackError")

    def test_refusal_and_hedge_on_different_commitments_ok(self, tmp_path) -> None:
        good = tmp_path / "split_v1.json"
        good.write_text(
            '{"pack_id":"split_v1","version":"1.0.0","description":"x",'
            '"schema_version":"1.0.0","domain":"custom",'
            '"commitment_ids":["a","b"],'
            '"refusal_commitments":["a"],"hedge_commitments":["b"]}'
        )
        pack = load_ethics_pack(
            "split_v1",
            search_paths=(tmp_path,),
            require_ratified=False,
        )
        assert pack.refusal_commitments == frozenset({"a"})
        assert pack.hedge_commitments == frozenset({"b"})


# ---------- pure helper functions ----------


class TestShouldInjectHedge:
    def test_no_pack_returns_false(self) -> None:
        verdict = _ethics_verdict(
            _ethics_result("acknowledge_uncertainty", upheld=False, rc=True),
        )
        assert not should_inject_hedge(verdict, None)

    def test_no_verdict_returns_false(self) -> None:
        pack = _pack(hedge_commitments=frozenset({"acknowledge_uncertainty"}))
        assert not should_inject_hedge(None, pack)

    def test_empty_opt_in_returns_false(self) -> None:
        verdict = _ethics_verdict(
            _ethics_result("acknowledge_uncertainty", upheld=False, rc=True),
        )
        pack = _pack(hedge_commitments=frozenset())
        assert not should_inject_hedge(verdict, pack)

    def test_opt_in_with_runtime_checkable_violation_returns_true(self) -> None:
        verdict = _ethics_verdict(
            _ethics_result("acknowledge_uncertainty", upheld=False, rc=True),
        )
        pack = _pack(hedge_commitments=frozenset({"acknowledge_uncertainty"}))
        assert should_inject_hedge(verdict, pack)

    def test_opt_in_with_no_evidence_does_not_inject(self) -> None:
        verdict = _ethics_verdict(
            _ethics_result("acknowledge_uncertainty", upheld=False, rc=False),
        )
        pack = _pack(hedge_commitments=frozenset({"acknowledge_uncertainty"}))
        assert not should_inject_hedge(verdict, pack)

    def test_violation_outside_opt_in_does_not_inject(self) -> None:
        verdict = _ethics_verdict(
            _ethics_result("no_manipulation", upheld=False, rc=True),
        )
        pack = _pack(hedge_commitments=frozenset({"acknowledge_uncertainty"}))
        assert not should_inject_hedge(verdict, pack)


class TestBuildHedgePrefix:
    def test_default_manifold_returns_soft_hedge(self) -> None:
        rt = ChatRuntime(config=RuntimeConfig())
        prefix = build_hedge_prefix(rt.identity_manifold)
        # The default identity pack carries a soft hedge phrase.
        soft = rt.identity_manifold.surface_preferences.preferred_hedge_soft
        if soft:
            assert prefix == soft

    def test_none_manifold_returns_empty(self) -> None:
        assert build_hedge_prefix(None) == ""


class TestInjectHedge:
    def test_prepends_with_space(self) -> None:
        assert inject_hedge("the answer", "Perhaps") == "Perhaps the answer"

    def test_empty_prefix_returns_surface_unchanged(self) -> None:
        assert inject_hedge("the answer", "") == "the answer"

    def test_empty_surface_returns_unchanged(self) -> None:
        assert inject_hedge("", "Perhaps") == ""

    def test_idempotent_on_existing_prefix(self) -> None:
        """If the surface already starts with the hedge, don't
        double-prepend.  Idempotent on prefix is a useful property
        for callers that may chain remediations."""
        assert inject_hedge("Perhaps the answer", "Perhaps") == "Perhaps the answer"

    def test_idempotent_case_insensitive(self) -> None:
        assert inject_hedge("perhaps the answer", "Perhaps") == "perhaps the answer"


# ---------- ChatRuntime integration ----------


class TestRuntimeHedgeInjection:
    def test_default_pack_does_not_inject_hedge(self) -> None:
        """Default ethics pack has empty hedge_commitments — surface
        is not hedge-prefixed even when a hedge phrase is available."""
        rt = ChatRuntime(config=RuntimeConfig())
        # Force a runtime-checkable violation on
        # acknowledge_uncertainty but do NOT opt it into hedging.
        rt.ethics_check.register(
            "acknowledge_uncertainty",
            _failing_ethics("acknowledge_uncertainty"),
        )
        resp = rt.chat("light is")
        prefix = build_hedge_prefix(rt.identity_manifold)
        if prefix:
            assert not resp.surface.startswith(prefix)

    def test_opt_in_pack_injects_hedge_on_violation(self) -> None:
        rt = ChatRuntime(config=RuntimeConfig())
        rt.ethics_pack = replace(
            rt.ethics_pack,
            hedge_commitments=frozenset({"acknowledge_uncertainty"}),
        )
        rt.ethics_check.register(
            "acknowledge_uncertainty",
            _failing_ethics("acknowledge_uncertainty"),
        )
        resp = rt.chat("light is")
        prefix = build_hedge_prefix(rt.identity_manifold)
        if not prefix:
            return  # nothing to inject in this pack
        # Hedge injection is a main-path-only affordance — the stub
        # path's unknown-domain marker is already a disclosure surface
        # and is intentionally not hedge-prefixed.  Detect stub path
        # by walk_surface (ADR-0039 now emits stub TurnEvents too, so
        # ``rt.turn_log`` is no longer a stub/main discriminator).
        if resp.walk_surface == "I don't know — insufficient grounding for that yet.":
            return
        assert resp.surface.startswith(prefix)

    def test_hedge_preserves_walk_surface(self) -> None:
        """walk_surface retains the original token-walk evidence even
        when ChatResponse.surface is hedge-prefixed."""
        rt = ChatRuntime(config=RuntimeConfig())
        rt.ethics_pack = replace(
            rt.ethics_pack,
            hedge_commitments=frozenset({"acknowledge_uncertainty"}),
        )
        rt.ethics_check.register(
            "acknowledge_uncertainty",
            _failing_ethics("acknowledge_uncertainty"),
        )
        resp = rt.chat("light is")
        prefix = build_hedge_prefix(rt.identity_manifold)
        if not prefix or not resp.surface.startswith(prefix):
            return
        assert not resp.walk_surface.startswith(prefix)

    def test_refusal_supersedes_hedge(self) -> None:
        """When both safety refusal and hedge injection would fire,
        refusal wins.  The surface is a typed refusal, not a
        hedge-prefixed token walk."""
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

        rt.safety_check.register("preserve_versor_closure", _failing_safety)
        rt.ethics_check.register(
            "acknowledge_uncertainty",
            _failing_ethics("acknowledge_uncertainty"),
        )
        resp = rt.chat("light is")
        assert is_typed_refusal(resp.surface)
        prefix = build_hedge_prefix(rt.identity_manifold)
        if prefix:
            # Refusal text begins with the typed-refusal prefix, not the hedge.
            assert not resp.surface.startswith(prefix)

    def test_hedge_does_not_set_last_refusal_was_typed(self) -> None:
        """Hedge injection is not a refusal — the bookkeeping flag
        that tracks typed refusals must not be flipped by hedging."""
        rt = ChatRuntime(config=RuntimeConfig())
        rt.ethics_pack = replace(
            rt.ethics_pack,
            hedge_commitments=frozenset({"acknowledge_uncertainty"}),
        )
        rt.ethics_check.register(
            "acknowledge_uncertainty",
            _failing_ethics("acknowledge_uncertainty"),
        )
        # Default value is True; hedge injection should NOT flip it.
        # (It only ever gets set to True; the predicate's job is to
        # spot a False setting from an untyped refusal path.)
        before = rt._last_refusal_was_typed
        rt.chat("light is")
        # The flag stays at its prior value — hedge injection does
        # not touch refusal bookkeeping.
        assert rt._last_refusal_was_typed == before


# ---------- helpers ----------


def _failing_ethics(commitment_id: str):
    def _impl(ctx):  # noqa: ANN001
        return EthicsCheckResult(
            commitment_id=commitment_id,
            upheld=False,
            reason="forced",
            runtime_checkable=True,
        )

    return _impl


def _ethics_result(commitment_id: str, *, upheld: bool, rc: bool) -> EthicsCheckResult:
    return EthicsCheckResult(
        commitment_id=commitment_id,
        upheld=upheld,
        reason="test",
        runtime_checkable=rc,
    )


def _ethics_verdict(*results: EthicsCheckResult) -> EthicsVerdict:
    violated = frozenset(r.commitment_id for r in results if not r.upheld)
    return EthicsVerdict(
        pack_id="test_ethics",
        results=tuple(results),
        upheld=not violated,
        violated_commitments=violated,
        runtime_checkable_count=sum(1 for r in results if r.runtime_checkable),
    )


def _pack(*, hedge_commitments: frozenset[str]) -> EthicsPack:
    return EthicsPack(
        pack_id="test_ethics",
        version="1.0.0",
        description="test",
        domain="custom",
        commitment_ids=frozenset({
            "acknowledge_uncertainty",
            "no_manipulation",
        }),
        commitment_descriptions={},
        mastery_report_sha256="",
        ratified=False,
        refusal_commitments=frozenset(),
        hedge_commitments=hedge_commitments,
    )
