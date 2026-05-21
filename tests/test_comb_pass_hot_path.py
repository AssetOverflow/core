"""Hot-path comb pass (2026-05-21).

Regression tests for the five mechanical-sympathy fixes bundled in
the perf/comb-pass-hot-path PR:

  1. ``ChatRuntime._apply_oov_policy`` consults precomputed booleans
     instead of rescanning ``self._manifests`` per OOV token.
  2. ``CognitiveTurnPipeline.run`` invokes ``classify_compound_intent``
     once per turn and takes ``compound.primary`` as the seeded intent
     (previously ``classify_intent`` ran twice per non-compound prompt).
  3. ``TeachingStore.triples()`` materializes once per turn and is
     threaded through both ``_maybe_transitive_walk`` and
     ``_maybe_compose_relations``.
  5. ``realize_semantic`` / ``realize_target`` build a node-id → obj
     map once and look up each step in O(1) instead of an O(N) linear
     scan of ``graph.nodes`` per step.

The dead-code removal (item 11) and import hoists (item 9) are
covered indirectly by every existing test still passing.
"""

from __future__ import annotations

from chat.runtime import ChatRuntime
from core.cognition import CognitiveTurnPipeline


def test_oov_policy_aggregates_precomputed() -> None:
    """Aggregates exist as boolean attributes after construction."""
    rt = ChatRuntime()
    assert isinstance(rt._all_manifests_fail_closed, bool)
    assert isinstance(rt._any_manifest_proposes_vocab, bool)


def test_classify_compound_intent_called_once_per_turn(monkeypatch) -> None:
    """``classify_intent`` must not run twice per turn.

    Pre-fix: ``pipeline.run`` called ``classify_intent(text)`` directly
    and then ``classify_compound_intent(text)`` immediately after.
    The compound classifier internally invokes ``classify_intent`` on
    the dominant fragment, so the cascade ran twice on every
    non-compound prompt.
    """
    import generate.intent as intent_mod

    n_calls = {"compound": 0, "single": 0}
    real_compound = intent_mod.classify_compound_intent
    real_single = intent_mod.classify_intent

    def counting_compound(prompt):
        n_calls["compound"] += 1
        return real_compound(prompt)

    def counting_single(prompt):
        n_calls["single"] += 1
        return real_single(prompt)

    # Patch both at the import site the pipeline uses.
    import core.cognition.pipeline as pipeline_mod
    monkeypatch.setattr(pipeline_mod, "classify_compound_intent", counting_compound)
    monkeypatch.setattr(intent_mod, "classify_intent", counting_single)

    pipeline = CognitiveTurnPipeline(runtime=ChatRuntime())
    pipeline.run("What is truth?", max_tokens=4)

    # Exactly one compound call from the pipeline, and the single
    # classifier is only re-entered through the compound classifier
    # itself (one re-entry on the dominant clause).
    assert n_calls["compound"] == 1
    assert n_calls["single"] == 1


def test_triples_materialized_once_per_turn(monkeypatch) -> None:
    """``TeachingStore.triples()`` runs at most once in the operator pair."""
    pipeline = CognitiveTurnPipeline(runtime=ChatRuntime())
    n_calls = {"triples": 0}
    real = pipeline.teaching_store.triples

    def counting():
        n_calls["triples"] += 1
        return real()

    monkeypatch.setattr(pipeline.teaching_store, "triples", counting)
    pipeline.run("What is truth?", max_tokens=4)
    # The pipeline body calls .triples() once and passes the tuple to
    # both operator helpers.  Pre-fix this was 2 (one per helper).
    assert n_calls["triples"] == 1


def test_realizer_node_map_o1_lookup() -> None:
    """The realizer builds a node_map so ``_resolve_obj`` is bypassed.

    We don't measure timing — just confirm correctness over a multi-
    step graph since the failure mode of a bad lookup is "..." in
    place of the real object slot.
    """
    from generate.graph_planner import (
        ArticulationStep,
        ArticulationTarget,
        GraphNode,
        PropositionGraph,
        RhetoricalMove,
    )
    from generate.intent import IntentTag
    from generate.realizer import realize_semantic

    nodes = tuple(
        GraphNode(
            node_id=f"p{i}",
            subject=f"subj{i}",
            predicate="is_defined_as",
            obj=f"obj{i}",
            source_intent=IntentTag.DEFINITION,
        )
        for i in range(8)
    )
    graph = PropositionGraph(nodes=nodes)
    steps = tuple(
        ArticulationStep(
            node_id=f"p{i}",
            move=RhetoricalMove.ASSERT,
            predicate="is_defined_as",
            subject=f"subj{i}",
        )
        for i in range(8)
    )
    target = ArticulationTarget(steps=steps, source_intent=IntentTag.DEFINITION)

    plan = realize_semantic(target, graph)
    # Every step's real object slot appears in the joined surface — proves
    # the per-step lookup found the right node.
    for i in range(8):
        assert f"obj{i}" in plan.surface
