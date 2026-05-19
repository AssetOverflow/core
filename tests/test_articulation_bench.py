"""Smoke + contract tests for the articulation benchmark suite.

These are tests for the **bench itself** — not the underlying runtime
behaviour, which is exercised by the cognition lane.  The bench is
load-bearing for the post-Phase-4 capability claims, so each sub-
bench gets a focused test that pins the shape of its report.
"""

from __future__ import annotations

import pytest

from benchmarks.articulation import (
    INTENT_PROBE_PROMPTS,
    CROSS_TOPIC_PROMPTS,
    DISCOURSE_PLANNER_PROMPTS,
    bench_breadth,
    bench_cross_topic,
    bench_determinism,
    bench_discourse_planner,
    bench_footprint,
    bench_ollama_compare,
    run_articulation_suite,
)


# ---------------------------------------------------------------------------
# Breadth
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def breadth_report():
    return bench_breadth()


def test_breadth_covers_every_supported_intent_shape(breadth_report) -> None:
    labels = [p.label for p in breadth_report]
    expected = [label for label, _ in INTENT_PROBE_PROMPTS]
    assert labels == expected


def test_breadth_emits_per_prompt_grounding_tag(breadth_report) -> None:
    for p in breadth_report:
        assert p.grounding_source in {
            "vault", "teaching", "pack", "partial", "oov", "none",
        }


def test_breadth_oov_prompt_routes_oov(breadth_report) -> None:
    oov = next(p for p in breadth_report if p.label == "OOV_FALLBACK")
    assert oov.grounding_source == "oov"
    # The OOV invitation always names the unfamiliar token; the
    # ``PackMutationProposal`` callout follows but may be truncated
    # by the snippet limit.
    assert "photosynthesis" in oov.surface_snippet
    assert "haven't learned" in oov.surface_snippet


def test_breadth_cross_pack_verification_routes_teaching(breadth_report) -> None:
    cp = next(
        p for p in breadth_report
        if p.label == "CROSS_PACK_VERIFICATION"
    )
    assert cp.grounding_source == "teaching"
    assert "cross-pack-grounded" in cp.surface_snippet


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


def test_determinism_byte_identical_across_runs() -> None:
    cases, all_identical = bench_determinism(runs=5)
    assert all_identical is True
    for c in cases:
        assert c.unique_surfaces == 1, (
            f"prompt {c.prompt!r} produced {c.unique_surfaces} unique "
            f"surfaces across {c.runs} runs"
        )


# ---------------------------------------------------------------------------
# Footprint
# ---------------------------------------------------------------------------


def test_footprint_emits_samples_and_bounds() -> None:
    pytest.importorskip("psutil")
    samples, start, peak, end, per_turn = bench_footprint(
        turns=20, sample_every=10,
    )
    assert len(samples) >= 2  # start + at least one mid/end sample
    assert peak >= start
    assert end >= 0
    # Per-turn ΔRSS must be a small number; if it's huge we have a leak.
    # 1 MiB / turn is a hard ceiling for the smoke test.
    assert abs(per_turn) < 1_048_576, (
        f"per-turn ΔRSS too large ({per_turn} bytes); possible leak"
    )


# ---------------------------------------------------------------------------
# Cross-topic
# ---------------------------------------------------------------------------


def test_cross_topic_visits_every_prompt() -> None:
    turns, _fires = bench_cross_topic()
    assert len(turns) == len(CROSS_TOPIC_PROMPTS)
    for i, t in enumerate(turns):
        assert t.turn == i
        assert t.prompt == CROSS_TOPIC_PROMPTS[i]
        # Every cross-topic turn either grounds via a recognised tier
        # or returns ``none`` — never a raw exception escape.
        assert t.grounding_source in {
            "vault", "teaching", "pack", "partial", "oov", "none",
        }


# ---------------------------------------------------------------------------
# Discourse planner
# ---------------------------------------------------------------------------


def test_discourse_planner_bench_covers_new_prompt_shapes() -> None:
    probes, metrics = bench_discourse_planner()
    assert [p.label for p in probes] == [label for label, _ in DISCOURSE_PLANNER_PROMPTS]
    assert metrics["cases"] == len(DISCOURSE_PLANNER_PROMPTS)
    assert "articulate_sentence_rate" in metrics
    labels = {p.label for p in probes}
    assert {"COMPOUND", "WALKTHROUGH"} <= labels


# ---------------------------------------------------------------------------
# Ollama (skipped when binary absent)
# ---------------------------------------------------------------------------


def test_ollama_compare_skips_cleanly_when_no_model_specified() -> None:
    """Calling without ``model`` argument is the documented opt-out."""
    result = bench_ollama_compare(model=None)
    assert result["status"] == "skipped"


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


def test_run_articulation_suite_emits_shaped_report() -> None:
    pytest.importorskip("psutil")
    report = run_articulation_suite(
        determinism_runs=3, footprint_turns=10,
        footprint_sample_every=5, ollama_model=None,
    )
    d = report.as_dict()
    assert isinstance(d["breadth"], list) and len(d["breadth"]) > 0
    assert isinstance(d["determinism"], list)
    assert d["determinism_all_identical"] is True
    assert isinstance(d["footprint_samples"], list)
    assert d["ollama"]["status"] == "skipped"
    assert isinstance(d["discourse_planner"], list)
    assert d["discourse_planner_metrics"]["cases"] == len(DISCOURSE_PLANNER_PROMPTS)
    # Cross-topic walk runs every entry.
    assert len(d["cross_topic"]) == len(CROSS_TOPIC_PROMPTS)
