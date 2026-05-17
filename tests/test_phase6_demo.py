"""Phase 6 comparative demo contract tests.

Pins the three head-to-head deltas as CI-enforced assertions so the
demo's headline claims are not just narrative — they are contract.

The "baseline" is the same CORE codebase with inner_loop / margin /
rotor admissibility disabled (ADR-0023 boundary-only).  No external
LLM is involved; this is a within-system comparison demonstrating
what ADR-0024 + ADR-0026 + ADR-0025 actually add.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from evals.forward_semantic_control.phase6_demo import run_lane, Phase6Report
from generate.exhaustion import RefusalReason


CORPUS_PATH = Path("evals/forward_semantic_control/public/v2_phase6_demo/cases.jsonl")


@pytest.fixture(scope="module")
def corpus() -> list[dict]:
    return [
        json.loads(line)
        for line in CORPUS_PATH.read_text().splitlines()
        if line.strip()
    ]


@pytest.fixture(scope="module")
def report(corpus: list[dict]) -> Phase6Report:
    return run_lane(corpus)


class TestC1ReplayDeterminism:
    def test_all_cases_replay_stable_core(self, report: Phase6Report) -> None:
        assert report.metrics["c1_replay_stable_core"] == report.metrics["c1_eligible"]

    def test_all_cases_replay_stable_baseline(self, report: Phase6Report) -> None:
        # Baseline must also be deterministic — Phase 6 does not claim
        # CORE adds determinism, only that CORE preserves it while
        # adding rejection/refusal evidence to the trace.
        assert report.metrics["c1_replay_stable_baseline"] == report.metrics["c1_eligible"]

    def test_replay_reruns_is_five(self, report: Phase6Report) -> None:
        assert report.metrics["replay_reruns"] == 5

    def test_c1_overall_pass(self, report: Phase6Report) -> None:
        assert report.metrics["c1_pass"] is True


class TestC2TracedRejection:
    def test_c2_corpus_nonempty(self, report: Phase6Report) -> None:
        assert report.metrics["c2_case_count"] > 0

    def test_baseline_emits_forbidden_every_case(self, report: Phase6Report) -> None:
        # The case construction guarantees boundary picks the forbidden;
        # this is the in-system baseline failure mode CORE corrects.
        assert (
            report.metrics["c2_baseline_emits_forbidden"]
            == report.metrics["c2_case_count"]
        )

    def test_baseline_admits_zero_forbidden(self, report: Phase6Report) -> None:
        # Baseline emits the forbidden but its verdict says admitted=False
        # — i.e. the inadmissibility is *visible* but the walk continues
        # anyway.  This is the silent-emit failure mode.
        assert report.metrics["c2_baseline_admits_forbidden"] == 0

    def test_core_corrects_or_refuses_every_case(self, report: Phase6Report) -> None:
        assert (
            report.metrics["c2_core_corrects_or_refuses"]
            == report.metrics["c2_case_count"]
        )

    def test_core_rejection_in_trace_every_case(self, report: Phase6Report) -> None:
        # Either ``forbidden in rejected_words`` OR a typed refusal —
        # both count as "the rejection is observable evidence."
        assert (
            report.metrics["c2_core_rejection_traced"]
            == report.metrics["c2_case_count"]
        )

    def test_c2_overall_pass(self, report: Phase6Report) -> None:
        assert report.metrics["c2_pass"] is True


class TestC3CoherentRefusal:
    def test_c3_corpus_nonempty(self, report: Phase6Report) -> None:
        assert report.metrics["c3_case_count"] > 0

    def test_baseline_zero_typed_refusals(self, report: Phase6Report) -> None:
        # Baseline never raises typed refusals — it either emits a
        # candidate with admitted=False or silently fails.  This is
        # the load-bearing comparison: typed refusal is *new* in CORE.
        assert report.metrics["c3_baseline_refused_typed"] == 0

    def test_baseline_emits_inadmissible_every_case(self, report: Phase6Report) -> None:
        # On every no-admissible-path case, baseline either refused
        # (untyped ValueError) or emitted something inadmissible.
        assert (
            report.metrics["c3_baseline_emitted_inadmissible"]
            == report.metrics["c3_case_count"]
        )

    def test_core_typed_refusal_every_case(self, report: Phase6Report) -> None:
        assert (
            report.metrics["c3_core_refused_typed"]
            == report.metrics["c3_case_count"]
        )

    def test_core_refusal_reason_is_inner_loop_exhaustion(
        self, report: Phase6Report
    ) -> None:
        expected = RefusalReason.INNER_LOOP_EXHAUSTION.value
        for d in report.case_details:
            if d.get("condition") != "coherent_refusal":
                continue
            assert d.get("c3_core_refusal_reason") == expected

    def test_c3_overall_pass(self, report: Phase6Report) -> None:
        assert report.metrics["c3_pass"] is True


class TestPhase6Headline:
    def test_all_three_conditions_pass(self, report: Phase6Report) -> None:
        assert report.metrics["all_three_conditions_pass"] is True
