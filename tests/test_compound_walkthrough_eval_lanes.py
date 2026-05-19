"""Contract tests for compound and walkthrough articulation eval lanes."""

from __future__ import annotations

from evals.framework import get_lane, run_lane


def test_compound_intent_decomposition_public_passes() -> None:
    lane = get_lane("compound_intent_decomposition")
    result = run_lane(lane, version="v1", split="public")
    assert result.metrics["decomposition_accuracy"] == 1.0
    assert result.metrics["subject_accuracy"] == 1.0


def test_walkthrough_chain_public_passes() -> None:
    lane = get_lane("walkthrough_chain")
    result = run_lane(lane, version="v1", split="public")
    assert result.metrics["path_exact_rate"] == 1.0
    assert result.metrics["anchor_rate"] == 1.0
    assert result.metrics["bounded_rate"] == 1.0


def test_chat_spine_holdout_splits_are_runnable() -> None:
    for lane_name in (
        "multi_sentence_response",
        "cold_start_grounding",
        "conversational_thread_coherence",
        "warmed_session_consistency",
    ):
        lane = get_lane(lane_name)
        result = run_lane(lane, version="v1", split="holdout")
        assert result.metrics["cases"] >= 1

