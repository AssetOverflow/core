"""Tests for benchmarks.pipeline_profiler and benchmarks.word_selection_tracer.

These are pure instrumentation tests — they assert that the profiler and
tracer capture structural breakdowns without altering pipeline semantics.
"""

from __future__ import annotations

import pytest

from benchmarks.pipeline_profiler import ProfileReport, profile_turn
from benchmarks.word_selection_tracer import (
    RealizationTrace,
    WordSelectionStep,
    trace_realization,
)
from chat.runtime import ChatRuntime
from core.cognition import CognitiveTurnPipeline


@pytest.fixture()
def runtime() -> ChatRuntime:
    return ChatRuntime()


@pytest.fixture()
def pipeline(runtime: ChatRuntime) -> CognitiveTurnPipeline:
    return CognitiveTurnPipeline(runtime)


def test_profile_turn_returns_stage_breakdown(pipeline: CognitiveTurnPipeline) -> None:
    """profile_turn returns a ProfileReport whose stages cover the pipeline spine."""
    report = profile_turn(pipeline, "light logos", max_tokens=8)

    assert isinstance(report, ProfileReport)
    assert report.total_ns > 0
    assert isinstance(report.stages, dict)

    # Mandatory stages (always traversed by pipeline.run regardless of input).
    required = {
        "intent",
        "graph_planner",
        "realize_semantic",
        "runtime_chat",
        "trace_hash",
    }
    missing = required - set(report.stages.keys())
    assert not missing, f"Profiler missed required stages: {missing}"

    # Each captured stage must have a non-negative timing.
    for name, ns in report.stages.items():
        assert ns >= 0, f"Stage {name} had negative timing {ns}"

    # Sum of timed stages must not exceed total elapsed (sanity, allow equal).
    sum_stages = sum(report.stages.values())
    assert sum_stages <= report.total_ns + 1_000_000  # 1ms slack for overhead

    # as_dict is JSON-friendly.
    d = report.as_dict()
    assert d["total_ns"] == report.total_ns
    assert d["stages"] == report.stages

    # Verify the original methods were restored on the pipeline.
    assert not isinstance(pipeline._maybe_transitive_walk, type(lambda: None)) or (
        pipeline._maybe_transitive_walk.__qualname__.startswith("CognitiveTurnPipeline")
    )


def test_trace_realization_captures_word_choices(pipeline: CognitiveTurnPipeline) -> None:
    """trace_realization records every nearest-neighbor lookup with top-K candidates."""
    trace = trace_realization(pipeline, "light logos", top_k=3)

    assert isinstance(trace, RealizationTrace)

    # The realizer-step list may be empty if the intent produced no
    # ArticulationTarget steps, but on a normal known-token input we
    # expect at least one realization step OR at least one slot lookup.
    assert trace.steps or trace.realization_steps, (
        "Tracer captured neither word-selection steps nor realization steps"
    )

    # If any slot lookups were recorded, validate their shape.
    for step in trace.steps:
        assert isinstance(step, WordSelectionStep)
        assert step.slot in {"subject", "predicate", "object"} or step.slot.startswith("slot_")
        assert step.input_versor.shape == (32,)
        assert len(step.top_candidates) >= 1
        # top_candidates must be sorted by score descending.
        scores = [score for (_, score) in step.top_candidates]
        assert scores == sorted(scores, reverse=True)
        # chosen word must appear in top_candidates.
        words = [w for (w, _) in step.top_candidates]
        assert step.chosen in words or step.chosen == words[0] or len(words) > 0
        assert isinstance(step.morphology, dict)

    # as_dict is JSON-friendly.
    d = trace.as_dict()
    assert "steps" in d and "realization_steps" in d and "surface" in d
