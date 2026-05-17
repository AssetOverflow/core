"""Tests for semantic realizer integration into the cognitive pipeline.

Verifies that the semantic realizer produces structurally better surfaces
from intent + proposition graph, and that the ChatResponse contract holds.
"""

from __future__ import annotations

import pytest

from generate.intent import IntentTag, classify_intent
from generate.graph_planner import graph_from_intent, plan_articulation
from generate.realizer import realize_semantic, realize_target, RealizedPlan
from generate.semantic_templates import humanize_predicate, render_semantic


# ---------------------------------------------------------------------------
# Unit tests: semantic_templates
# ---------------------------------------------------------------------------

class TestSemanticTemplates:
    def test_humanize_known_predicate(self) -> None:
        assert humanize_predicate("is_defined_as") == "is defined as"
        assert humanize_predicate("contrasts_with") == "contrasts with"
        assert humanize_predicate("defines") == "defines"
        assert humanize_predicate("means") == "means"
        assert humanize_predicate("grounds") == "grounds"
        assert humanize_predicate("supports") == "supports"
        assert humanize_predicate("corrects") == "corrects"

    def test_humanize_unknown_predicate_uses_underscore_replacement(self) -> None:
        assert humanize_predicate("some_new_predicate") == "some new predicate"

    def test_render_definition(self) -> None:
        surface = render_semantic(
            intent=IntentTag.DEFINITION,
            subject="truth",
            predicate="is_defined_as",
            obj="coherence",
        )
        assert "truth" in surface
        assert "is defined as" in surface
        assert "coherence" in surface

    def test_render_comparison(self) -> None:
        surface = render_semantic(
            intent=IntentTag.COMPARISON,
            subject="truth",
            predicate="contrasts_with",
            obj="light",
            secondary="light",
        )
        assert "truth" in surface
        assert "light" in surface

    def test_render_correction(self) -> None:
        surface = render_semantic(
            intent=IntentTag.CORRECTION,
            subject="correction",
            predicate="corrects",
            obj="reviewed repair",
        )
        assert "correction" in surface.lower()

    def test_pending_obj_displays_as_ellipsis(self) -> None:
        surface = render_semantic(
            intent=IntentTag.DEFINITION,
            subject="truth",
            predicate="is_defined_as",
            obj="<pending>",
        )
        assert "<pending>" not in surface
        assert "..." in surface


# ---------------------------------------------------------------------------
# Unit tests: realize_semantic
# ---------------------------------------------------------------------------

class TestRealizeSemantic:
    def test_definition_prompt_uses_semantic_realizer(self) -> None:
        intent = classify_intent("What is truth?")
        assert intent.tag is IntentTag.DEFINITION
        graph = graph_from_intent(intent)
        target = plan_articulation(graph)
        plan = realize_semantic(target, graph)
        assert isinstance(plan, RealizedPlan)
        assert plan.surface
        assert "truth" in plan.surface.lower()
        assert "is defined as" in plan.surface.lower()

    def test_comparison_prompt_mentions_both_terms(self) -> None:
        intent = classify_intent("Compare truth and light")
        assert intent.tag is IntentTag.COMPARISON
        graph = graph_from_intent(intent)
        target = plan_articulation(graph)
        plan = realize_semantic(target, graph)
        assert plan.surface
        assert "truth" in plan.surface.lower()
        assert "light" in plan.surface.lower()

    def test_correction_prompt_uses_correction_template(self) -> None:
        intent = classify_intent("No, correction means reviewed repair")
        assert intent.tag is IntentTag.CORRECTION
        graph = graph_from_intent(intent)
        target = plan_articulation(graph)
        plan = realize_semantic(target, graph)
        assert plan.surface
        assert "correction" in plan.surface.lower()

    def test_cause_prompt(self) -> None:
        intent = classify_intent("Why does light exist?")
        assert intent.tag is IntentTag.CAUSE
        graph = graph_from_intent(intent)
        target = plan_articulation(graph)
        plan = realize_semantic(target, graph)
        assert plan.surface
        assert "is grounded in" in plan.surface.lower()

    def test_empty_target_returns_empty_plan(self) -> None:
        from generate.graph_planner import ArticulationTarget
        plan = realize_semantic(
            ArticulationTarget(steps=(), source_intent=IntentTag.UNKNOWN),
        )
        assert plan.surface == ""
        assert plan.fragments == ()

    def test_none_target_returns_empty_plan(self) -> None:
        plan = realize_semantic(None)
        assert plan.surface == ""

    def test_seed_relation_predicates_humanize_deterministically(self) -> None:
        seed_predicates = [
            "defines", "means", "grounds", "supports",
            "contrasts_with", "corrects", "causes", "reveals",
            "precedes", "follows", "belongs_to", "answers",
        ]
        for pred in seed_predicates:
            h = humanize_predicate(pred)
            assert "_" not in h, f"{pred} humanized to {h!r} still has underscores"
            assert h == humanize_predicate(pred), f"{pred} not deterministic"


# ---------------------------------------------------------------------------
# Integration: realize_semantic vs realize_target produce valid plans
# ---------------------------------------------------------------------------

class TestSemanticVsRhetoricalRealization:
    @pytest.mark.parametrize("prompt,expected_intent", [
        ("What is truth?", IntentTag.DEFINITION),
        ("Compare truth and light", IntentTag.COMPARISON),
        ("Why does light exist?", IntentTag.CAUSE),
        ("No, that's wrong", IntentTag.CORRECTION),
    ])
    def test_both_realizers_produce_nonempty_surface(
        self, prompt: str, expected_intent: IntentTag,
    ) -> None:
        intent = classify_intent(prompt)
        assert intent.tag is expected_intent
        graph = graph_from_intent(intent)
        target = plan_articulation(graph)

        rhetorical = realize_target(target, graph)
        semantic = realize_semantic(target, graph)

        assert rhetorical.surface, f"rhetorical plan empty for {prompt!r}"
        assert semantic.surface, f"semantic plan empty for {prompt!r}"

    def test_semantic_surfaces_are_deterministic(self) -> None:
        prompt = "What is truth?"
        results = set()
        for _ in range(5):
            intent = classify_intent(prompt)
            graph = graph_from_intent(intent)
            target = plan_articulation(graph)
            plan = realize_semantic(target, graph)
            results.add(plan.surface)
        assert len(results) == 1, f"Non-deterministic: {results}"


# ---------------------------------------------------------------------------
# Contract: ChatResponse shape still holds through the pipeline
# ---------------------------------------------------------------------------

class TestChatResponseContractStillHolds:
    def test_chat_response_has_required_fields(self) -> None:
        try:
            from chat.runtime import ChatRuntime, ChatResponse
        except Exception:
            pytest.skip("ChatRuntime not importable in this environment")

        runtime = ChatRuntime()
        response = runtime.chat("What is truth?")
        assert isinstance(response, ChatResponse)
        assert isinstance(response.surface, str)
        assert response.surface
        assert isinstance(response.versor_condition, float)
        assert response.versor_condition < 1e-6
        assert response.proposition is not None
        assert response.articulation is not None
        assert isinstance(response.articulation_surface, str)
        assert isinstance(response.walk_surface, str)
        assert isinstance(response.dialogue_role, str)
        assert isinstance(response.vault_hits, int)

    def test_pipeline_result_uses_semantic_surface(self) -> None:
        try:
            from chat.runtime import ChatRuntime
            from core.cognition.pipeline import CognitiveTurnPipeline
        except Exception:
            pytest.skip("ChatRuntime not importable in this environment")

        runtime = ChatRuntime()
        pipeline = CognitiveTurnPipeline(runtime)
        # Prime the vault so the unknown-domain gate does not fire on the
        # probe.  Without priming, ChatRuntime returns the safety stub
        # ("I don't have field coordinates for that yet.") which the
        # pipeline now honours (calibration gaps.md Finding 2 resolution).
        # The semantic-surface contract this test gates on only applies
        # when the gate does not fire; priming guarantees that.
        pipeline.run("truth is defined as the coherent ground of inquiry.")
        result = pipeline.run("What is truth?")

        assert result.surface
        assert "truth" in result.surface.lower()
        # The semantic realizer must produce a structured DEFINITION
        # surface — historically that was "is defined as ...", but
        # after the ADR-0023 ratifier wiring fix the field can demote
        # the seeded DEFINITION when the prompt versor falls outside
        # the anchor's region; the realizer's UNKNOWN-shape template
        # ("X addresses ...") is then the correct grounded surface.
        # The contract this test gates on is that *some* semantic
        # realizer template fired (surface is not the bare walk),
        # not that one specific template was selected.
        assert any(
            marker in result.surface.lower()
            for marker in ("is defined as", "addresses", "reveals", "names")
        )
        assert result.articulation_surface == result.surface
        assert result.versor_condition < 1e-6
        assert result.trace_hash

    def test_pipeline_honours_safety_stub_when_gate_fires(self) -> None:
        """When the unknown-domain gate fires, the pipeline's surface
        is the gate's safety stub — NOT the realizer's fallback
        articulation.  Closes calibration gaps.md Finding 2."""
        try:
            from chat.runtime import ChatRuntime, _UNKNOWN_DOMAIN_SURFACE
            from core.cognition.pipeline import CognitiveTurnPipeline
        except Exception:
            pytest.skip("ChatRuntime not importable in this environment")

        runtime = ChatRuntime()
        pipeline = CognitiveTurnPipeline(runtime)
        # Cold runtime: the very first probe should fire the gate.
        result = pipeline.run("What is truth?")

        assert result.vault_hits == 0, "gate-fired turn should have zero vault hits"
        assert result.surface == _UNKNOWN_DOMAIN_SURFACE
        assert result.articulation_surface == _UNKNOWN_DOMAIN_SURFACE
        # walk_surface is unaffected by the override decision — it carries
        # the realizer's evidence regardless.
        assert isinstance(result.walk_surface, str)
