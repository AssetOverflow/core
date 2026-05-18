"""ADR-0034 — EthicsCheck structural surface.

Mirrors ``tests/test_safety_check.py``.  Each of the five default
predicates is exercised on its positive and negative paths plus the
"caller didn't supply evidence" path; unknown-commitment fallback,
custom predicate registration, defensive id rebinding, and
``ChatRuntime`` integration are covered.
"""

from __future__ import annotations

import pytest

from chat.runtime import ChatRuntime
from core.config import RuntimeConfig
from packs.ethics.check import (
    EthicsCheck,
    EthicsCheckResult,
    EthicsContext,
    EthicsVerdict,
)
from packs.ethics.loader import EthicsPack, load_ethics_pack


# ---------- acknowledge_uncertainty ----------


class TestAcknowledgeUncertainty:
    def test_low_alignment_unhedged_violates(self) -> None:
        ctx = EthicsContext(
            alignment_score=0.3,
            hedge_threshold_soft=0.65,
            hedge_emitted=False,
        )
        result = _find(_check(ctx), "acknowledge_uncertainty")
        assert not result.upheld
        assert result.runtime_checkable

    def test_low_alignment_hedged_upheld(self) -> None:
        ctx = EthicsContext(
            alignment_score=0.3,
            hedge_threshold_soft=0.65,
            hedge_emitted=True,
        )
        result = _find(_check(ctx), "acknowledge_uncertainty")
        assert result.upheld
        assert result.runtime_checkable

    def test_high_alignment_unhedged_upheld(self) -> None:
        ctx = EthicsContext(
            alignment_score=0.9,
            hedge_threshold_soft=0.65,
            hedge_emitted=False,
        )
        result = _find(_check(ctx), "acknowledge_uncertainty")
        assert result.upheld

    def test_missing_fields_not_runtime_checkable(self) -> None:
        result = _find(_check(EthicsContext()), "acknowledge_uncertainty")
        assert result.upheld
        assert not result.runtime_checkable


# ---------- defer_high_stakes_to_human_review ----------


class TestDeferHighStakes:
    def test_high_stakes_with_review_upheld(self) -> None:
        ctx = EthicsContext(
            high_stakes_topic=True, recommended_human_review=True,
        )
        result = _find(_check(ctx), "defer_high_stakes_to_human_review")
        assert result.upheld
        assert result.runtime_checkable

    def test_high_stakes_without_review_violates(self) -> None:
        ctx = EthicsContext(
            high_stakes_topic=True, recommended_human_review=False,
        )
        result = _find(_check(ctx), "defer_high_stakes_to_human_review")
        assert not result.upheld

    def test_low_stakes_dormant(self) -> None:
        ctx = EthicsContext(high_stakes_topic=False)
        result = _find(_check(ctx), "defer_high_stakes_to_human_review")
        assert result.upheld
        assert result.runtime_checkable
        assert "dormant" in result.reason

    def test_high_stakes_unspecified_review_not_checkable(self) -> None:
        ctx = EthicsContext(high_stakes_topic=True)
        result = _find(_check(ctx), "defer_high_stakes_to_human_review")
        assert result.upheld
        assert not result.runtime_checkable

    def test_missing_flag_not_checkable(self) -> None:
        result = _find(
            _check(EthicsContext()), "defer_high_stakes_to_human_review",
        )
        assert result.upheld
        assert not result.runtime_checkable


# ---------- disclose_limitations ----------


class TestDiscloseLimitations:
    def test_grounded_no_obligation(self) -> None:
        ctx = EthicsContext(grounded_in_evidence=True)
        result = _find(_check(ctx), "disclose_limitations")
        assert result.upheld
        assert result.runtime_checkable

    def test_ungrounded_disclosed_upheld(self) -> None:
        ctx = EthicsContext(
            grounded_in_evidence=False, disclosure_emitted=True,
        )
        result = _find(_check(ctx), "disclose_limitations")
        assert result.upheld

    def test_ungrounded_silent_violates(self) -> None:
        ctx = EthicsContext(
            grounded_in_evidence=False, disclosure_emitted=False,
        )
        result = _find(_check(ctx), "disclose_limitations")
        assert not result.upheld
        assert result.runtime_checkable

    def test_missing_flag_not_checkable(self) -> None:
        result = _find(_check(EthicsContext()), "disclose_limitations")
        assert result.upheld
        assert not result.runtime_checkable


# ---------- no_manipulation ----------


class TestNoManipulation:
    def test_always_upheld_never_runtime_checkable(self) -> None:
        result = _find(_check(EthicsContext()), "no_manipulation")
        assert result.upheld
        assert not result.runtime_checkable
        assert (
            "realizer design" in result.reason
            or "review" in result.reason
        )


# ---------- respect_user_autonomy ----------


class TestRespectUserAutonomy:
    def test_non_prescriptive_upheld(self) -> None:
        ctx = EthicsContext(prescribed_single_answer=False)
        result = _find(_check(ctx), "respect_user_autonomy")
        assert result.upheld
        assert result.runtime_checkable

    def test_prescribed_with_alternatives_upheld(self) -> None:
        ctx = EthicsContext(
            prescribed_single_answer=True, presented_options_count=3,
        )
        result = _find(_check(ctx), "respect_user_autonomy")
        assert result.upheld

    def test_prescribed_without_alternatives_violates(self) -> None:
        ctx = EthicsContext(
            prescribed_single_answer=True, presented_options_count=1,
        )
        result = _find(_check(ctx), "respect_user_autonomy")
        assert not result.upheld
        assert result.runtime_checkable

    def test_missing_options_count_not_checkable(self) -> None:
        ctx = EthicsContext(prescribed_single_answer=True)
        result = _find(_check(ctx), "respect_user_autonomy")
        assert result.upheld
        assert not result.runtime_checkable


# ---------- unknown-commitment fallback ----------


class TestUnknownCommitment:
    def test_unknown_commitment_defaults_upheld_not_runtime_checkable(
        self,
    ) -> None:
        check = EthicsCheck(predicates={})
        verdict = check.check(EthicsContext(), load_ethics_pack())
        assert verdict.upheld
        assert verdict.runtime_checkable_count == 0
        for r in verdict.results:
            assert r.upheld
            assert not r.runtime_checkable
            assert "no predicate registered" in r.reason


# ---------- custom predicate registration ----------


class TestCustomPredicateRegistration:
    def test_register_custom_predicate(self) -> None:
        def my_pred(ctx: EthicsContext) -> EthicsCheckResult:
            return EthicsCheckResult(
                commitment_id="domain_specific_pledge",
                upheld=False,
                reason="custom predicate violation for test",
                runtime_checkable=True,
            )
        check = EthicsCheck()
        check.register("domain_specific_pledge", my_pred)
        custom = EthicsPack(
            pack_id="custom_test",
            version="1.0.0",
            description="test",
            domain="custom",
            commitment_ids=frozenset({"domain_specific_pledge"}),
            commitment_descriptions={"domain_specific_pledge": "test"},
            mastery_report_sha256="",
            ratified=False,
        )
        verdict = check.check(EthicsContext(), custom)
        assert not verdict.upheld
        assert "domain_specific_pledge" in verdict.violated_commitments

    def test_misreporting_predicate_id_is_rebound(self) -> None:
        def lying_pred(ctx: EthicsContext) -> EthicsCheckResult:
            return EthicsCheckResult(
                commitment_id="WRONG",
                upheld=True,
                reason="defensive test",
                runtime_checkable=False,
            )
        check = EthicsCheck()
        check.register("no_manipulation", lying_pred)
        verdict = check.check(EthicsContext(), load_ethics_pack())
        result = _find(verdict, "no_manipulation")
        assert result.commitment_id == "no_manipulation"


# ---------- verdict aggregation ----------


class TestVerdictAggregation:
    def test_pack_id_recorded(self) -> None:
        verdict = EthicsCheck().check(EthicsContext(), load_ethics_pack())
        assert verdict.pack_id == "default_general_ethics_v1"

    def test_results_in_lex_order(self) -> None:
        verdict = EthicsCheck().check(EthicsContext(), load_ethics_pack())
        ids = [r.commitment_id for r in verdict.results]
        assert ids == sorted(ids)

    def test_empty_context_no_violations(self) -> None:
        # With an empty EthicsContext, every default predicate either
        # reports runtime_checkable=False or upholds.
        verdict = EthicsCheck().check(EthicsContext(), load_ethics_pack())
        assert verdict.upheld

    def test_violation_aggregated_into_verdict(self) -> None:
        ctx = EthicsContext(
            alignment_score=0.2,
            hedge_threshold_soft=0.65,
            hedge_emitted=False,
            high_stakes_topic=True,
            recommended_human_review=False,
        )
        verdict = EthicsCheck().check(ctx, load_ethics_pack())
        assert not verdict.upheld
        assert "acknowledge_uncertainty" in verdict.violated_commitments
        assert (
            "defer_high_stakes_to_human_review" in verdict.violated_commitments
        )


# ---------- ChatRuntime integration ----------


class TestChatRuntimeIntegration:
    def test_runtime_exposes_ethics_check(self) -> None:
        rt = ChatRuntime(config=RuntimeConfig())
        assert isinstance(rt.ethics_check, EthicsCheck)

    def test_runtime_ethics_check_evaluates_loaded_pack(self) -> None:
        rt = ChatRuntime(config=RuntimeConfig())
        verdict = rt.ethics_check.check(EthicsContext(), rt.ethics_pack)
        assert isinstance(verdict, EthicsVerdict)
        assert verdict.pack_id == rt.ethics_pack.pack_id
        assert verdict.upheld  # empty ctx → no violations observed


# ---------- helpers ----------


def _check(ctx: EthicsContext) -> EthicsVerdict:
    return EthicsCheck().check(ctx, load_ethics_pack())


def _find(verdict: EthicsVerdict, commitment_id: str) -> EthicsCheckResult:
    for r in verdict.results:
        if r.commitment_id == commitment_id:
            return r
    raise AssertionError(f"commitment {commitment_id!r} not in verdict")


# Suppress an unused-import lint warning in environments where pytest
# decorators aren't applied — the import stays useful for typing.
_ = pytest
