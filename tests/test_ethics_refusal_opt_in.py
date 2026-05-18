"""ADR-0037 — per-predicate ethics refusal opt-in.

Ethics commitments remain audit-only by default.  A pack opts a
specific commitment into refusal via ``refusal_commitments`` in the
pack JSON.  The runtime then unifies safety + opted-in ethics
violations into one deterministic typed refusal surface, with each id
source-tagged (``safety:<id>`` / ``ethics:<id>``).
"""

from __future__ import annotations

from dataclasses import replace

from chat.refusal import (
    TYPED_REFUSAL_PREFIX,
    build_refusal_surface,
    is_typed_refusal,
    violated_runtime_checkable_ethics,
)
from chat.runtime import ChatRuntime
from core.config import RuntimeConfig
from packs.ethics.check import EthicsCheckResult, EthicsVerdict
from packs.ethics.loader import EthicsPack, EthicsPackError, load_ethics_pack
from packs.safety.check import SafetyCheckResult, SafetyVerdict


# ---------- pack-loader bounds ----------


class TestRefusalCommitmentsLoaderValidation:
    def test_default_pack_has_empty_refusal_commitments(self) -> None:
        pack = load_ethics_pack()
        assert pack.refusal_commitments == frozenset()

    def test_unknown_id_in_refusal_commitments_is_rejected(self, tmp_path) -> None:
        bad = tmp_path / "broken_v1.json"
        bad.write_text(
            '{"pack_id":"broken_v1","version":"1.0.0","description":"x",'
            '"schema_version":"1.0.0","domain":"custom",'
            '"commitment_ids":["a"],"refusal_commitments":["not_declared"]}'
        )
        try:
            load_ethics_pack(
                "broken_v1",
                search_paths=(tmp_path,),
                require_ratified=False,
            )
        except EthicsPackError as e:
            assert "not a declared commitment_id" in str(e)
        else:
            raise AssertionError("expected EthicsPackError")

    def test_duplicate_in_refusal_commitments_is_rejected(self, tmp_path) -> None:
        bad = tmp_path / "dup_v1.json"
        bad.write_text(
            '{"pack_id":"dup_v1","version":"1.0.0","description":"x",'
            '"schema_version":"1.0.0","domain":"custom",'
            '"commitment_ids":["a"],"refusal_commitments":["a","a"]}'
        )
        try:
            load_ethics_pack(
                "dup_v1",
                search_paths=(tmp_path,),
                require_ratified=False,
            )
        except EthicsPackError as e:
            assert "duplicate" in str(e)
        else:
            raise AssertionError("expected EthicsPackError")

    def test_non_list_refusal_commitments_is_rejected(self, tmp_path) -> None:
        bad = tmp_path / "weird_v1.json"
        bad.write_text(
            '{"pack_id":"weird_v1","version":"1.0.0","description":"x",'
            '"schema_version":"1.0.0","domain":"custom",'
            '"commitment_ids":["a"],"refusal_commitments":"not_a_list"}'
        )
        try:
            load_ethics_pack(
                "weird_v1",
                search_paths=(tmp_path,),
                require_ratified=False,
            )
        except EthicsPackError as e:
            assert "must be a list" in str(e)
        else:
            raise AssertionError("expected EthicsPackError")


# ---------- pure refusal builder, ethics path ----------


class TestEthicsRefusalBuilder:
    def test_ethics_violation_without_opt_in_does_not_refuse(self) -> None:
        ethics_verdict = _ethics_verdict(
            _ethics_result("acknowledge_uncertainty", upheld=False, rc=True),
        )
        pack = _pack(refusal_commitments=frozenset())
        assert build_refusal_surface(None, ethics_verdict, pack) is None

    def test_ethics_violation_with_opt_in_refuses(self) -> None:
        ethics_verdict = _ethics_verdict(
            _ethics_result("acknowledge_uncertainty", upheld=False, rc=True),
        )
        pack = _pack(refusal_commitments=frozenset({"acknowledge_uncertainty"}))
        out = build_refusal_surface(None, ethics_verdict, pack)
        assert out is not None
        assert out.startswith(TYPED_REFUSAL_PREFIX)
        assert "ethics:acknowledge_uncertainty" in out

    def test_ethics_violation_not_in_opt_in_subset_ignored(self) -> None:
        """Opt-in must include the specific commitment that fired.
        Other opt-ins do not generalize."""
        ethics_verdict = _ethics_verdict(
            _ethics_result("no_manipulation", upheld=False, rc=True),
        )
        pack = _pack(refusal_commitments=frozenset({"acknowledge_uncertainty"}))
        assert build_refusal_surface(None, ethics_verdict, pack) is None

    def test_ethics_non_runtime_checkable_does_not_refuse_even_with_opt_in(self) -> None:
        ethics_verdict = _ethics_verdict(
            _ethics_result("acknowledge_uncertainty", upheld=False, rc=False),
        )
        pack = _pack(refusal_commitments=frozenset({"acknowledge_uncertainty"}))
        assert build_refusal_surface(None, ethics_verdict, pack) is None

    def test_combined_safety_and_ethics_refusal_listed_lex_sorted(self) -> None:
        safety_verdict = _safety_verdict(
            _safety_result("preserve_versor_closure", upheld=False, rc=True),
        )
        ethics_verdict = _ethics_verdict(
            _ethics_result("acknowledge_uncertainty", upheld=False, rc=True),
        )
        pack = _pack(refusal_commitments=frozenset({"acknowledge_uncertainty"}))
        out = build_refusal_surface(safety_verdict, ethics_verdict, pack)
        assert out is not None
        # Both contribute; tags appear in lex order across the merged set.
        assert "ethics:acknowledge_uncertainty" in out
        assert "safety:preserve_versor_closure" in out
        # "ethics:" < "safety:" lexicographically.
        assert out.index("ethics:acknowledge_uncertainty") < out.index(
            "safety:preserve_versor_closure"
        )

    def test_safety_only_call_back_compat(self) -> None:
        """Historical ADR-0036 call signature: ``build_refusal_surface(v)``
        with no ethics still works and produces a safety-only refusal."""
        safety_verdict = _safety_verdict(
            _safety_result("preserve_versor_closure", upheld=False, rc=True),
        )
        out = build_refusal_surface(safety_verdict)
        assert out is not None
        assert "safety:preserve_versor_closure" in out


class TestViolatedRuntimeCheckableEthics:
    def test_empty_opt_in_returns_empty(self) -> None:
        verdict = _ethics_verdict(
            _ethics_result("acknowledge_uncertainty", upheld=False, rc=True),
        )
        assert violated_runtime_checkable_ethics(verdict, frozenset()) == ()

    def test_none_opt_in_returns_empty(self) -> None:
        verdict = _ethics_verdict(
            _ethics_result("acknowledge_uncertainty", upheld=False, rc=True),
        )
        assert violated_runtime_checkable_ethics(verdict, None) == ()

    def test_returns_only_opted_in_violations(self) -> None:
        verdict = _ethics_verdict(
            _ethics_result("acknowledge_uncertainty", upheld=False, rc=True),
            _ethics_result("no_manipulation", upheld=False, rc=True),
        )
        out = violated_runtime_checkable_ethics(verdict, frozenset({"no_manipulation"}))
        assert out == ("no_manipulation",)


# ---------- ChatRuntime integration ----------


class TestRuntimeEthicsRefusal:
    def test_runtime_with_default_pack_does_not_refuse_on_ethics_violation(self) -> None:
        """Default ethics pack has empty refusal_commitments — even a
        forced runtime-checkable ethics violation must not refuse."""
        rt = ChatRuntime(config=RuntimeConfig())

        def _failing(ctx):  # noqa: ANN001
            return EthicsCheckResult(
                commitment_id="acknowledge_uncertainty",
                upheld=False,
                reason="forced",
                runtime_checkable=True,
            )

        rt.ethics_check.register("acknowledge_uncertainty", _failing)
        resp = rt.chat("light is")
        assert not is_typed_refusal(resp.surface)

    def test_runtime_with_opt_in_pack_refuses_on_ethics_violation(self) -> None:
        """A pack that opts ``acknowledge_uncertainty`` into refusal
        must produce a typed refusal when that commitment fires
        runtime-checkable=True, upheld=False."""
        rt = ChatRuntime(config=RuntimeConfig())
        # Mutate the pack on the running instance — equivalent to
        # loading a deployment pack with refusal_commitments=[…].
        rt.ethics_pack = replace(
            rt.ethics_pack,
            refusal_commitments=frozenset({"acknowledge_uncertainty"}),
        )

        def _failing(ctx):  # noqa: ANN001
            return EthicsCheckResult(
                commitment_id="acknowledge_uncertainty",
                upheld=False,
                reason="forced",
                runtime_checkable=True,
            )

        rt.ethics_check.register("acknowledge_uncertainty", _failing)
        resp = rt.chat("light is")
        assert is_typed_refusal(resp.surface)
        assert "ethics:acknowledge_uncertainty" in resp.surface

    def test_runtime_combined_safety_and_ethics_refusal(self) -> None:
        rt = ChatRuntime(config=RuntimeConfig())
        rt.ethics_pack = replace(
            rt.ethics_pack,
            refusal_commitments=frozenset({"acknowledge_uncertainty"}),
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
        assert is_typed_refusal(resp.surface)
        assert "safety:preserve_versor_closure" in resp.surface
        assert "ethics:acknowledge_uncertainty" in resp.surface


# ---------- helpers ----------


def _safety_result(boundary_id: str, *, upheld: bool, rc: bool) -> SafetyCheckResult:
    return SafetyCheckResult(
        boundary_id=boundary_id,
        upheld=upheld,
        reason="test",
        runtime_checkable=rc,
    )


def _safety_verdict(*results: SafetyCheckResult) -> SafetyVerdict:
    violated = frozenset(r.boundary_id for r in results if not r.upheld)
    return SafetyVerdict(
        pack_id="test_safety",
        results=tuple(results),
        upheld=not violated,
        violated_boundaries=violated,
        runtime_checkable_count=sum(1 for r in results if r.runtime_checkable),
    )


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


def _pack(*, refusal_commitments: frozenset[str]) -> EthicsPack:
    return EthicsPack(
        pack_id="test_ethics",
        version="1.0.0",
        description="test",
        domain="custom",
        commitment_ids=frozenset({
            "acknowledge_uncertainty",
            "no_manipulation",
            "respect_user_autonomy",
        }),
        commitment_descriptions={},
        mastery_report_sha256="",
        ratified=False,
        refusal_commitments=refusal_commitments,
    )
