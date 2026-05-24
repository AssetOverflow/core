from __future__ import annotations

import math

import numpy as np
import pytest

from evals.gsm8k_math import runner as gsm8k_runner
from generate.math_realizer import RealizerError
from language_packs.evidence import mean_pair_score, resonance_evidence


class _DummyManifold:
    def get_versor(self, token: str) -> np.ndarray:
        return np.ones(32, dtype=np.float32)


def test_mean_pair_score_empty_is_undetermined_nan() -> None:
    score = mean_pair_score(_DummyManifold(), ())

    assert math.isnan(score)


def test_resonance_evidence_empty_pairs_do_not_pass() -> None:
    evidence = resonance_evidence(
        case_id="empty",
        manifold=_DummyManifold(),
        aligned_pairs=(),
        contrast_pairs=(),
    )

    assert math.isnan(evidence.aligned_score)
    assert math.isnan(evidence.contrast_score)
    assert evidence.passes is False


def test_verified_trace_realizer_error_is_decoded_unarticulated(monkeypatch: pytest.MonkeyPatch) -> None:
    case = {
        "id": "realizer-breaks-after-verify",
        "problem": "Sam has 2 apples. How many apples does Sam have?",
        "expected_answer": 2.0,
        "expected_unit": "apples",
    }

    def fail_realize(*args, **kwargs):
        raise RealizerError("forced articulation failure")

    monkeypatch.setattr(gsm8k_runner, "realize", fail_realize)

    outcome = gsm8k_runner._score_one(case)

    assert outcome.outcome == gsm8k_runner.DECODED_UNARTICULATED_OUTCOME
    assert outcome.reason == "realizer: forced articulation failure"
    assert outcome.actual_answer == 2.0
    assert outcome.actual_unit == "apples"
    assert outcome.trace_hash is not None
    assert outcome.realized_prose is None


def test_decoded_unarticulated_does_not_increment_wrong(monkeypatch: pytest.MonkeyPatch) -> None:
    case = {
        "id": "realizer-breaks-after-verify",
        "problem": "Sam has 2 apples. How many apples does Sam have?",
        "expected_answer": 2.0,
        "expected_unit": "apples",
    }

    def fail_realize(*args, **kwargs):
        raise RealizerError("forced articulation failure")

    monkeypatch.setattr(gsm8k_runner, "realize", fail_realize)

    report = gsm8k_runner.run_lane([case])

    assert report.metrics["wrong"] == 0
    assert report.metrics["decoded_unarticulated"] == 1
    assert report.metrics["wrong_count_is_zero"] is True
    assert report.metrics["overall_pass"] is True
