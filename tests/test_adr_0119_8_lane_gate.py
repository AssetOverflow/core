"""ADR-0119.8 — gsm8k_math overall lane gate invariants.

Pins six load-bearing invariants:

1. **Registry mapping.** ``LANE_SHAPE_REGISTRY["gsm8k_math"] ==
   "gsm8k_capability_shape"``.

2. **Shape checker registered.** ``SHAPE_CHECKERS`` contains the
   ``gsm8k_capability_shape`` checker.

3. **Live lane runner output passes the gate** on dev + public splits
   (today: 50/50 + 150/150 correct, 0 wrong, 0 refused).

4. **Nonzero wrong refuses the gate.** ADR-0114a Obligation #4 enforced.

5. **Outcome-accounting incompleteness refuses the gate.** If
   correct + refused != total, the gate refuses.

6. **Substrate artifacts exist** for Phase 5.1..5.6 (sealed holdout,
   corpus + verify.py, runner, frontier baseline, adversarial
   generator, depth-curve harness). Phase 5.7 (sealed GSM8K test)
   is documented as pending but not gated here — that's its own
   future ADR's job to flip on.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.capability.expert_demo import (
    LANE_SHAPE_REGISTRY,
    SHAPE_CHECKERS,
    _check_gsm8k_capability_shape,
    resolve_lane_shape,
)
from evals.gsm8k_math.runner import run_lane


_REPO_ROOT = Path(__file__).resolve().parent.parent


def _load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


class TestRegistryMapping:
    def test_gsm8k_math_maps_to_capability_shape(self) -> None:
        assert LANE_SHAPE_REGISTRY["gsm8k_math"] == "gsm8k_capability_shape"

    def test_resolve_lane_shape_returns_capability_shape(self) -> None:
        assert resolve_lane_shape("gsm8k_math") == "gsm8k_capability_shape"

    def test_shape_checkers_includes_capability_shape(self) -> None:
        assert "gsm8k_capability_shape" in SHAPE_CHECKERS


class TestLiveLaneRunnerPassesGate:
    def test_dev_split_metrics_pass(self) -> None:
        cases = _load_jsonl(_REPO_ROOT / "evals/gsm8k_math/dev/cases.jsonl")
        report = run_lane(cases)
        ok, reason = _check_gsm8k_capability_shape("gsm8k_math", report.metrics)
        assert ok, f"dev split gate failed: {reason}"

    def test_public_split_metrics_pass(self) -> None:
        cases = _load_jsonl(_REPO_ROOT / "evals/gsm8k_math/public/v1/cases.jsonl")
        report = run_lane(cases)
        ok, reason = _check_gsm8k_capability_shape("gsm8k_math", report.metrics)
        assert ok, f"public split gate failed: {reason}"


class TestGateRefusesNonzeroWrong:
    def test_wrong_one_refuses(self) -> None:
        metrics = {
            "cases_total": 10,
            "correct": 9,
            "wrong": 1,
            "refused": 0,
        }
        ok, reason = _check_gsm8k_capability_shape("gsm8k_math", metrics)
        assert ok is False
        assert "wrong=1" in reason
        assert "Obligation #4" in reason


class TestGateRefusesIncompleteAccounting:
    def test_correct_plus_refused_not_total(self) -> None:
        metrics = {
            "cases_total": 10,
            "correct": 7,
            "wrong": 0,
            "refused": 2,  # 7 + 2 = 9, not 10
        }
        ok, reason = _check_gsm8k_capability_shape("gsm8k_math", metrics)
        assert ok is False
        assert "outcome accounting incomplete" in reason


class TestGateRefusesMissingFields:
    @pytest.mark.parametrize(
        "missing", ["cases_total", "correct", "wrong", "refused"]
    )
    def test_missing_field_refuses(self, missing: str) -> None:
        metrics = {
            "cases_total": 10,
            "correct": 10,
            "wrong": 0,
            "refused": 0,
        }
        del metrics[missing]
        ok, reason = _check_gsm8k_capability_shape("gsm8k_math", metrics)
        assert ok is False
        assert missing in reason


class TestGateRefusesZeroTotal:
    def test_zero_total_refuses(self) -> None:
        metrics = {
            "cases_total": 0,
            "correct": 0,
            "wrong": 0,
            "refused": 0,
        }
        ok, reason = _check_gsm8k_capability_shape("gsm8k_math", metrics)
        assert ok is False
        assert "cases_total=0" in reason


class TestGateAcceptsCleanMetrics:
    def test_clean_balanced_metrics_pass(self) -> None:
        metrics = {
            "cases_total": 100,
            "correct": 95,
            "wrong": 0,
            "refused": 5,
            "overall_pass": True,
        }
        ok, reason = _check_gsm8k_capability_shape("gsm8k_math", metrics)
        assert ok is True
        assert reason == ""

    def test_all_refused_balanced_passes(self) -> None:
        """Edge case: 0 correct, 0 wrong, all refused — still passes the
        shape gate. (This means CORE refused every case; whether that's
        acceptable for ``expert`` promotion is ADR-0120's job, not this
        layer's.)"""
        metrics = {
            "cases_total": 50,
            "correct": 0,
            "wrong": 0,
            "refused": 50,
            "overall_pass": True,
        }
        ok, reason = _check_gsm8k_capability_shape("gsm8k_math", metrics)
        assert ok is True


class TestSubstrateArtifactsExist:
    """Verify Phase 5.1..5.6 substrate is in place on disk."""

    def test_phase_5_1_sealed_holdout_artifact(self) -> None:
        """ADR-0119.1 — fabrication_control holdout is age-encrypted."""
        sealed = _REPO_ROOT / "evals/fabrication_control/holdouts/v1/cases.jsonl.age"
        assert sealed.exists() and sealed.is_file()
        # age header starts with "age-encryption.org/"
        assert sealed.read_bytes().startswith(b"age-encryption.org/")

    def test_phase_5_2_corpus_and_verify(self) -> None:
        """ADR-0119.2 — dev + public + verify.py."""
        dev = _REPO_ROOT / "evals/gsm8k_math/dev/cases.jsonl"
        public = _REPO_ROOT / "evals/gsm8k_math/public/v1/cases.jsonl"
        verify_py = _REPO_ROOT / "evals/gsm8k_math/verify.py"
        for p in (dev, public, verify_py):
            assert p.exists(), f"missing Phase 5.2 artifact: {p}"
        assert len(_load_jsonl(dev)) == 50
        assert len(_load_jsonl(public)) == 150

    def test_phase_5_3_runner(self) -> None:
        runner_py = _REPO_ROOT / "evals/gsm8k_math/runner.py"
        assert runner_py.exists()

    def test_phase_5_4_frontier_baseline(self) -> None:
        frontier = _REPO_ROOT / "evals/gsm8k_math/baselines/frontier.json"
        comparison = _REPO_ROOT / "evals/gsm8k_math/baselines/comparison_v1.json"
        assert frontier.exists()
        assert comparison.exists()

    def test_phase_5_5_adversarial(self) -> None:
        gen = _REPO_ROOT / "evals/gsm8k_math/adversarial/generator.py"
        score = _REPO_ROOT / "evals/gsm8k_math/adversarial/score.py"
        assert gen.exists()
        assert score.exists()

    def test_phase_5_6_depth_curve(self) -> None:
        harness = _REPO_ROOT / "evals/gsm8k_math/scoring/depth_curve.py"
        assert harness.exists()


class TestPhase5_7PendingDocumented:
    """Phase 5.7 (sealed GSM8K test) is the one remaining sub-phase.

    This test pins that it's NOT yet a hard gate — that's the future
    ADR-0119.7's job. Here we just confirm the placeholder is in place
    and the gate doesn't already fire on a nonexistent sealed test.
    """

    def test_placeholder_present_or_documented(self) -> None:
        # The placeholder may be either an empty cases.jsonl or a missing
        # cases.jsonl.age file; both shapes are acceptable at this stage.
        sealed = _REPO_ROOT / "evals/gsm8k_math/holdouts/v1/cases.jsonl.age"
        plaintext = _REPO_ROOT / "evals/gsm8k_math/holdouts/v1/cases.jsonl"
        plaintext_fallback = _REPO_ROOT / "evals/gsm8k_math/holdouts/v1/cases_plaintext.jsonl"
        assert sealed.exists() or plaintext.exists() or plaintext_fallback.exists(), (
            "Phase 5.7 placeholder missing — expected at least one of "
            "cases.jsonl.age / cases.jsonl / cases_plaintext.jsonl"
        )
