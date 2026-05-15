"""Tests for the intent -> proposition graph -> articulation target pipeline."""

from __future__ import annotations

import json

from generate.graph_planner import (
    Relation,
    RhetoricalMove,
    graph_from_intent,
    plan_articulation,
)
from generate.intent import IntentTag, classify_intent


def test_what_is_definition_intent() -> None:
    intent = classify_intent("What is a multivector?")

    assert intent.tag is IntentTag.DEFINITION
    assert "multivector" in intent.subject.lower()

    graph = graph_from_intent(intent)
    assert len(graph.nodes) == 1
    assert graph.nodes[0].predicate == "is_defined_as"
    assert graph.nodes[0].source_intent is IntentTag.DEFINITION


def test_why_cause_intent() -> None:
    intent = classify_intent("Why does the field diverge?")

    assert intent.tag is IntentTag.CAUSE
    assert "field" in intent.subject.lower()

    graph = graph_from_intent(intent)
    assert len(graph.nodes) == 1
    assert graph.nodes[0].predicate == "is_caused_by"


def test_compare_intent() -> None:
    intent = classify_intent("Compare MLX and PyTorch")

    assert intent.tag is IntentTag.COMPARISON
    assert intent.subject.lower() == "mlx"
    assert intent.secondary_subject is not None
    assert intent.secondary_subject.lower() == "pytorch"

    graph = graph_from_intent(intent)
    assert len(graph.nodes) == 2
    assert len(graph.edges) == 1
    assert graph.edges[0].relation is Relation.CONTRAST

    target = plan_articulation(graph)
    assert target.source_intent is IntentTag.COMPARISON
    moves = [s.move for s in target.steps]
    assert RhetoricalMove.CONTRAST in moves


def test_correction_intent_links_prior_turn() -> None:
    intent = classify_intent("No, that's wrong — it should be grade 2")

    assert intent.tag is IntentTag.CORRECTION
    assert intent.requires_prior_turn()

    prior_id = "prev_p0"
    graph = graph_from_intent(intent, prior_node_id=prior_id)
    assert len(graph.nodes) == 1
    assert graph.nodes[0].predicate == "corrects"
    assert graph.nodes[0].obj == prior_id

    assert len(graph.edges) == 1
    assert graph.edges[0].relation is Relation.CORRECTION
    assert graph.edges[0].target == prior_id


def test_graph_serialization_is_deterministic() -> None:
    intent = classify_intent("Compare cats and dogs")
    graph = graph_from_intent(intent)

    json_a = graph.to_json()
    json_b = graph.to_json()
    assert json_a == json_b

    parsed = json.loads(json_a)
    assert "nodes" in parsed
    assert "edges" in parsed
    assert len(parsed["nodes"]) == 2
    assert len(parsed["edges"]) == 1
