"""Tests for generate/graph_constraint.py — PropositionGraph as AdmissibilityRegion.

ADR-0046.
"""

from __future__ import annotations

import pytest
import numpy as np

from generate.graph_planner import GraphEdge, GraphNode, PropositionGraph, Relation
from generate.graph_constraint import build_graph_constraint
from generate.admissibility import AdmissibilityRegion
from generate.intent import IntentTag


@pytest.fixture()
def vocab():
    from language_packs import load_pack
    _manifest, manifold = load_pack("en")
    return manifold


def _node(node_id, subject, obj):
    return GraphNode(
        node_id=node_id,
        subject=subject,
        predicate="addresses",
        obj=obj,
        source_intent=IntentTag.DEFINITION,
    )


class TestBuildGraphConstraint:
    def test_returns_admissibility_region(self, vocab):
        graph = PropositionGraph().add_node(_node("p0", "light", "truth"))
        region = build_graph_constraint(graph, vocab)
        assert isinstance(region, AdmissibilityRegion)

    def test_non_trivial_constraint(self, vocab):
        """allowed_indices must be a strict subset of the full vocabulary."""
        graph = PropositionGraph().add_node(_node("p0", "light", "truth"))
        region = build_graph_constraint(graph, vocab, top_k=8)
        assert region.allowed_indices is not None
        assert len(region.allowed_indices) < len(vocab)

    def test_allowed_indices_positive_cga_inner(self, vocab):
        """Every allowed index must score positive cga_inner against at least one anchor."""
        from algebra.cga import cga_inner
        graph = PropositionGraph().add_node(_node("p0", "light", "truth"))
        region = build_graph_constraint(graph, vocab, top_k=8)
        assert region.allowed_indices is not None
        light_v = np.asarray(vocab.get_versor("light"), dtype=np.float32)
        truth_v = np.asarray(vocab.get_versor("truth"), dtype=np.float32)
        anchors = [light_v, truth_v]
        for idx in region.allowed_indices:
            scores = [
                float(cga_inner(np.asarray(vocab.get_versor_at(int(idx)), dtype=np.float32), a))
                for a in anchors
            ]
            assert max(scores) > 0.0, f"Index {idx} has non-positive CGA score against all anchors"

    def test_empty_graph_returns_unconstrained(self, vocab):
        """An empty graph degrades gracefully to an unconstrained region."""
        region = build_graph_constraint(PropositionGraph(), vocab)
        assert region.allowed_indices is None
        assert "unconstrained" in region.label

    def test_two_node_graph_unions_neighbourhoods(self, vocab):
        """A two-node graph produces a larger allowed set than a one-node graph."""
        graph_one = PropositionGraph().add_node(_node("p0", "light", "truth"))
        graph_two = (
            PropositionGraph()
            .add_node(_node("p0", "light", "truth"))
            .add_node(_node("p1", "word", "life"))
        )
        region_one = build_graph_constraint(graph_one, vocab, top_k=4)
        region_two = build_graph_constraint(graph_two, vocab, top_k=4)
        count_one = len(region_one.allowed_indices) if region_one.allowed_indices is not None else len(vocab)
        count_two = len(region_two.allowed_indices) if region_two.allowed_indices is not None else len(vocab)
        assert count_two >= count_one

    def test_label_encodes_root_node_ids(self, vocab):
        """The region label must encode the graph's root node IDs."""
        graph = PropositionGraph().add_node(_node("p0", "light", "truth"))
        region = build_graph_constraint(graph, vocab)
        assert "p0" in region.label

    def test_round_trip_with_generate(self, vocab):
        """The region produced by build_graph_constraint can be fed to generate() without raising."""
        from field.state import FieldState
        from generate.stream import generate
        from persona.motor import PersonaMotor

        graph = PropositionGraph().add_node(_node("p0", "light", "truth"))
        region = build_graph_constraint(graph, vocab, top_k=8)

        F0 = np.asarray(vocab.get_versor("light"), dtype=np.float64)
        state = FieldState(F=F0, node=vocab.index_of("light"), step=0)
        persona = PersonaMotor.identity()

        result = generate(
            state,
            vocab,
            persona,
            max_tokens=4,
            region=region,
        )
        assert result.tokens is not None

    def test_oov_nodes_degrade_gracefully(self, vocab):
        """A graph whose nodes are all OOV returns an unconstrained region."""
        graph = PropositionGraph().add_node(
            GraphNode(
                node_id="p0",
                subject="xyzzy_not_a_word",
                predicate="quux",
                obj="zork_also_not_a_word",
                source_intent=IntentTag.UNKNOWN,
            )
        )
        region = build_graph_constraint(graph, vocab)
        assert region.allowed_indices is None
