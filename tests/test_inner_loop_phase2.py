"""Phase 2 corpus-observation invariants (ADR-0024 follow-up).

These tests pin the causal-attribution and determinism contracts that
the Phase 2 runner must hold on the existing FSC corpus.  They are
intentionally *not* gated on rejection_effect or exhaustion_rate —
those are findings to be characterised in Phase 4, not invariants.

What we *do* assert:

  * ``causal_attribution_valid`` is True: the null control (inner-loop
    code path on, force-admit on) matches boundary-only exactly.  Any
    pass-rate delta between inner_loop_t0 and boundary_only is then
    attributable to rejection, not to incidental code-path effects.
  * ``code_path_residual`` is zero (within float tolerance).
  * Trace-hash stability holds for the inner-loop condition on every
    non-skipped case (5 reruns produce identical hashes).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from evals.forward_semantic_control.inner_loop_runner import run_lane

_CORPUS_PATHS = (
    Path("evals/forward_semantic_control/public/v1/cases.jsonl"),
    Path("evals/forward_semantic_control/dev/cases.jsonl"),
)


def _load_corpus() -> list[dict]:
    cases: list[dict] = []
    for path in _CORPUS_PATHS:
        if not path.exists():
            continue
        with path.open() as fh:
            cases.extend(json.loads(line) for line in fh if line.strip())
    return cases


@pytest.fixture(scope="module")
def phase2_report():
    cases = _load_corpus()
    if not cases:
        pytest.skip("FSC corpus not available")
    return run_lane(cases)


class TestCausalAttribution:
    def test_null_control_matches_boundary_only(self, phase2_report) -> None:
        """Null control must reproduce boundary-only pass-rate exactly.

        If this fails, the inner-loop code path is itself altering
        selection (call ordering, telemetry side effects), and any
        rejection_effect we measure is contaminated.  ADR-0024 proof
        depends on this invariant.
        """
        assert phase2_report.metrics["causal_attribution_valid"] is True
        assert phase2_report.metrics["code_path_residual"] == 0.0

    def test_null_control_per_condition_metrics(self, phase2_report) -> None:
        per = phase2_report.metrics["per_condition"]
        assert per["null_control"]["pass_rate"] == per["boundary_only"]["pass_rate"]
        # Null control must produce zero rejections by construction.
        assert per["null_control"]["mean_rejection_count_per_turn"] == 0
        assert per["null_control"]["non_empty_rejected_attempts_rate"] == 0.0
        assert per["null_control"]["exhaustion_rate"] == 0.0


class TestInnerLoopDeterminismOnCorpus:
    def test_inner_loop_t0_hash_stable_on_every_case(self, phase2_report) -> None:
        """Live-corpus version of the Phase 1 acceptance test.

        Stub-vocab determinism is necessary but not sufficient — the
        same property must hold on actual packs, actual field state,
        actual rejection sequences.  5 reruns per case must hash
        identically.
        """
        rate = phase2_report.metrics["per_condition"]["inner_loop_t0"][
            "trace_hash_stability_pass_rate"
        ]
        assert rate == 1.0


class TestPhase2RecordsFindings:
    """These are not gates — they record the Phase 2 finding so a
    future change that silently flips the sign of rejection_effect or
    closes the exhaustion gap is visible in test output."""

    def test_runner_emits_required_metric_keys(self, phase2_report) -> None:
        required = {
            "per_condition",
            "rejection_effect",
            "code_path_residual",
            "causal_attribution_valid",
            "exhaustion_ceiling",
            "exhaustion_gate_pass",
            "probe_threshold_positive",
            "case_count",
            "skipped_count",
        }
        assert required <= set(phase2_report.metrics.keys())

    def test_all_four_conditions_present(self, phase2_report) -> None:
        per = phase2_report.metrics["per_condition"]
        assert set(per.keys()) == {
            "boundary_only",
            "null_control",
            "inner_loop_t0",
            "inner_loop_tpos",
        }
