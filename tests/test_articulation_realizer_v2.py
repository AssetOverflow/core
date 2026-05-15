"""Tests for ArticulationRealizerV2 — deterministic template-based realization."""

from __future__ import annotations

from generate.graph_planner import (
    ArticulationTarget,
    graph_from_intent,
    plan_articulation,
)
from generate.intent import IntentTag, classify_intent
from generate.realizer import RealizedPlan, realize_target


def _realize_from_prompt(prompt: str, *, prior_node_id: str | None = None) -> RealizedPlan:
    intent = classify_intent(prompt)
    graph = graph_from_intent(intent, prior_node_id=prior_node_id)
    target = plan_articulation(graph)
    return realize_target(target, graph)


# ---------------------------------------------------------------------------
# 1. Definition realizer mentions subject
# ---------------------------------------------------------------------------

def test_definition_realizer_mentions_subject() -> None:
    plan = _realize_from_prompt("What is a multivector?")

    assert len(plan.fragments) == 1
    assert "multivector" in plan.surface.lower()
    assert "is defined as" in plan.surface.lower()
    assert plan.surface.endswith(".")


# ---------------------------------------------------------------------------
# 2. Comparison realizer mentions both terms
# ---------------------------------------------------------------------------

def test_comparison_realizer_mentions_both_terms() -> None:
    plan = _realize_from_prompt("Compare MLX and PyTorch")

    assert len(plan.fragments) == 2
    surface_lower = plan.surface.lower()
    assert "mlx" in surface_lower
    assert "pytorch" in surface_lower
    assert "in contrast" in surface_lower


# ---------------------------------------------------------------------------
# 3. Correction realizer mentions prior or correction
# ---------------------------------------------------------------------------

def test_correction_realizer_mentions_prior_or_correction() -> None:
    plan = _realize_from_prompt(
        "No, that's wrong — it should be grade 2",
        prior_node_id="prev_p0",
    )

    assert len(plan.fragments) == 1
    surface_lower = plan.surface.lower()
    assert "correction:" in surface_lower
    assert "corrects" in surface_lower


# ---------------------------------------------------------------------------
# 4. Unknown or empty graph is bounded
# ---------------------------------------------------------------------------

def test_unknown_or_empty_graph_is_bounded() -> None:
    empty_target = ArticulationTarget(steps=(), source_intent=IntentTag.UNKNOWN)
    plan = realize_target(empty_target, graph=None)

    assert plan.surface == ""
    assert plan.fragments == ()

    unknown_plan = _realize_from_prompt("xyzzy foobar")
    assert unknown_plan.surface
    assert len(unknown_plan.fragments) >= 1


# ---------------------------------------------------------------------------
# 5. Realizer output is deterministic
# ---------------------------------------------------------------------------

def test_realizer_output_is_deterministic() -> None:
    plan_a = _realize_from_prompt("What is light?")
    plan_b = _realize_from_prompt("What is light?")

    assert plan_a.surface == plan_b.surface
    assert len(plan_a.fragments) == len(plan_b.fragments)
    for fa, fb in zip(plan_a.fragments, plan_b.fragments):
        assert fa.surface == fb.surface
        assert fa.move == fb.move
        assert fa.node_id == fb.node_id
