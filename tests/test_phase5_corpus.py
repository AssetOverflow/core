"""Phase 5 stratified mechanism-isolation contract tests.

Exercises the Phase 5 corpus end-to-end across all five failure-mode
families and pins:

  - Per-family pass_rate = 1.0 under both threshold and margin modes.
  - Family C ⇒ honest refusal with RefusalReason.INNER_LOOP_EXHAUSTION
    in both modes.
  - Family B ⇒ refusal under margin mode (diff < δ by construction).
  - Replay determinism: 3 reruns produce byte-identical per-case
    selections under margin mode.

These tests are the contract for ADR-0024 Phase 5 and gate against
silent regressions in the inner-loop / margin / refusal pipeline.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from evals.forward_semantic_control.phase5_runner import (
    run_lane,
    Phase5Report,
)
from generate.exhaustion import RefusalReason


CORPUS_PATH = Path("evals/forward_semantic_control/public/v2_phase5/cases.jsonl")


@pytest.fixture(scope="module")
def corpus() -> list[dict]:
    return [
        json.loads(line)
        for line in CORPUS_PATH.read_text().splitlines()
        if line.strip()
    ]


@pytest.fixture(scope="module")
def report(corpus: list[dict]) -> Phase5Report:
    return run_lane(corpus)


class TestOverallContract:
    def test_no_skipped_cases(self, report: Phase5Report) -> None:
        assert report.metrics["skipped_count"] == 0

    def test_all_five_families_present(self, report: Phase5Report) -> None:
        expected = {
            "near_forbidden_correct_endpoint",
            "near_equal_admissible",
            "no_admissible_path",
            "multi_step_admissibility",
            "heterogeneous_relation",
        }
        assert set(report.per_family.keys()) == expected

    def test_mechanism_isolated_threshold(self, report: Phase5Report) -> None:
        assert report.metrics["pass_rate_threshold"] == 1.0
        assert report.metrics["mechanism_isolated_threshold"] is True

    def test_mechanism_isolated_margin(self, report: Phase5Report) -> None:
        assert report.metrics["pass_rate_margin"] == 1.0
        assert report.metrics["mechanism_isolated_margin"] is True


class TestPerFamilyPassRates:
    @pytest.mark.parametrize(
        "family",
        [
            "near_forbidden_correct_endpoint",
            "near_equal_admissible",
            "no_admissible_path",
            "multi_step_admissibility",
            "heterogeneous_relation",
        ],
    )
    def test_pass_rate_threshold(self, report: Phase5Report, family: str) -> None:
        assert report.per_family[family]["pass_rate_threshold"] == 1.0

    @pytest.mark.parametrize(
        "family",
        [
            "near_forbidden_correct_endpoint",
            "near_equal_admissible",
            "no_admissible_path",
            "multi_step_admissibility",
            "heterogeneous_relation",
        ],
    )
    def test_pass_rate_margin(self, report: Phase5Report, family: str) -> None:
        assert report.per_family[family]["pass_rate_margin"] == 1.0


class TestRefusalContract:
    def test_no_admissible_path_refuses_both_modes(
        self, report: Phase5Report
    ) -> None:
        fam = report.per_family["no_admissible_path"]
        assert fam["refusal_rate_threshold"] == 1.0
        assert fam["refusal_rate_margin"] == 1.0

    def test_no_admissible_path_reason_is_inner_loop_exhaustion(
        self, report: Phase5Report
    ) -> None:
        expected = RefusalReason.INNER_LOOP_EXHAUSTION.value
        for detail in report.case_details:
            if detail.get("family") != "no_admissible_path":
                continue
            t_leg = detail["threshold_leg"]
            m_leg = detail["margin_leg"]
            assert t_leg["refused"] is True
            assert m_leg["refused"] is True
            assert t_leg["refusal_reason"] == expected
            assert m_leg["refusal_reason"] == expected

    def test_near_equal_refuses_under_margin(self, report: Phase5Report) -> None:
        fam = report.per_family["near_equal_admissible"]
        assert fam["refusal_rate_margin"] == 1.0

    def test_near_equal_admits_under_threshold(self, report: Phase5Report) -> None:
        fam = report.per_family["near_equal_admissible"]
        assert fam["refusal_rate_threshold"] == 0.0


class TestRejectionEvidence:
    def test_near_forbidden_traces_rejection_when_overriding_boundary(
        self, report: Phase5Report
    ) -> None:
        # When inner-loop overrides boundary's selection, the rejected
        # token must appear in the trace.  These rates may be < 1.0
        # because some cases have boundary already aligned with
        # expected, but the floor signal must be positive.
        fam = report.per_family["near_forbidden_correct_endpoint"]
        assert fam["rejection_traced_rate_threshold"] > 0.0
        # rejection_traced ⇒ boundary_overridden by construction.
        assert (
            fam["boundary_overridden_rate_threshold"]
            >= fam["rejection_traced_rate_threshold"]
        )


class TestReplayDeterminism:
    def test_margin_mode_three_run_byte_identity(
        self, corpus: list[dict]
    ) -> None:
        report1 = run_lane(corpus)
        report2 = run_lane(corpus)
        report3 = run_lane(corpus)
        # Compare per-case margin-leg outcomes across all 3 runs.
        for d1, d2, d3 in zip(
            report1.case_details, report2.case_details, report3.case_details
        ):
            assert d1.get("passed_margin") == d2.get("passed_margin") == d3.get("passed_margin")
            # Single-step cases: margin_leg structural equality.
            for key in ("threshold_leg", "margin_leg"):
                leg1 = d1.get(key)
                leg2 = d2.get(key)
                leg3 = d3.get(key)
                if leg1 is None:
                    continue
                assert leg1.get("refused") == leg2.get("refused") == leg3.get("refused")
                assert leg1.get("selected") == leg2.get("selected") == leg3.get("selected")
