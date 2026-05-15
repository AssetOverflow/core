"""Core cognition seed pack smoke tests."""

from __future__ import annotations

from chat.runtime import ChatRuntime
from core.config import DEFAULT_CONFIG
from generate.intent import IntentTag, classify_intent
from generate.graph_planner import graph_from_intent, plan_articulation
from language_packs.compiler import load_mounted_packs, load_pack, load_pack_entries


_REQUIRED_CONCEPTS = frozenset({
    "word",
    "truth",
    "light",
    "life",
    "beginning",
    "creation",
    "knowledge",
    "wisdom",
    "spirit",
    "person",
    "question",
    "answer",
    "reason",
    "cause",
    "memory",
    "correction",
    "meaning",
    "definition",
    "comparison",
})

_REQUIRED_OPERATIONS = frozenset({
    "define",
    "explain",
    "compare",
    "infer",
    "remember",
    "correct",
    "verify",
    "ask",
    "mean",
    "reveal",
    "relate",
    "distinguish",
})

_REQUIRED_RELATIONS = frozenset({
    "is",
    "has",
    "causes",
    "reveals",
    "means",
    "contrasts_with",
    "precedes",
    "follows",
    "belongs_to",
    "grounds",
    "supports",
    "corrects",
})


def test_core_cognition_pack_loads() -> None:
    manifest, manifold = load_pack("en_core_cognition_v1")

    assert manifest.pack_id == "en_core_cognition_v1"
    assert manifest.language == "en"
    assert len(manifold) >= len(_REQUIRED_CONCEPTS)
    assert manifold.get_versor("definition").shape == (32,)


def test_core_cognition_pack_has_required_concepts_operations_and_relations() -> None:
    surfaces = {entry.surface for entry in load_pack_entries("en_core_cognition_v1")}

    assert _REQUIRED_CONCEPTS <= surfaces
    assert _REQUIRED_OPERATIONS <= surfaces
    assert _REQUIRED_RELATIONS <= surfaces


def test_default_runtime_mounts_core_cognition_seed_pack() -> None:
    assert "en_core_cognition_v1" in DEFAULT_CONFIG.input_packs

    mounted = load_mounted_packs(DEFAULT_CONFIG.input_packs)
    for surface in ("definition", "comparison", "infer", "grounds", "corrects"):
        assert mounted.get_versor(surface).shape == (32,)


def test_definition_prompt_uses_seed_concept() -> None:
    runtime = ChatRuntime()
    response = runtime.chat("what is definition", max_tokens=6)

    assert "definition" in runtime.tokenize("definition")
    assert response.surface
    assert response.versor_condition < 1e-6


def test_comparison_prompt_uses_seed_relation() -> None:
    intent = classify_intent("Compare truth and light")
    graph = graph_from_intent(intent)
    target = plan_articulation(graph)

    assert intent.tag is IntentTag.COMPARISON
    assert graph.nodes[0].subject.lower() == "truth"
    assert graph.nodes[1].subject.lower() == "light"
    assert any(step.subject.lower() == "light" for step in target.steps)


def test_pack_entries_are_deterministic() -> None:
    entries_a = load_pack_entries("en_core_cognition_v1")
    entries_b = load_pack_entries("en_core_cognition_v1")

    assert [entry.entry_id for entry in entries_a] == [entry.entry_id for entry in entries_b]
    assert [entry.surface for entry in entries_a] == [entry.surface for entry in entries_b]
    assert entries_a[0].entry_id == "en-core-cog-001"
    assert entries_a[-1].entry_id == "en-core-cog-055"
