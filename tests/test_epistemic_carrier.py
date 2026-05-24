"""Acceptance tests for ADR-0144 — PropositionGraph epistemic carrier.

Three phases:
  Phase 1 — admitted recognition produces a carrier with full provenance.
  Phase 2 — refused recognition produces no carrier; pipeline is unaffected.
  Phase 3 — connector derives a valid articulation GraphNode from the carrier.
"""

from __future__ import annotations

import json

import pytest

from generate.graph_planner import PropositionGraph, plan_articulation
from generate.intent import IntentTag
from recognition.anti_unifier import DerivedRecognizer, derive_recognizer, recognize
from recognition.carrier import EpistemicGraph, EpistemicNode, EpistemicTransition
from recognition.connector import epistemic_node_to_graph_node
from recognition.outcome import (
    AMBIGUOUS,
    CONTRADICTED,
    EVIDENCED,
    UNDETERMINED,
    BoundFeature,
    EvidenceSpan,
    FeatureBundle,
    NegativeEvidence,
)


# ---------------------------------------------------------------------------
# Shared fixture — Phase 1 teaching examples and recognizer
# ---------------------------------------------------------------------------

def _make_phase1_examples() -> list[tuple[tuple[str, ...], FeatureBundle]]:
    def span(tokens: tuple[str, ...], s: int, e: int) -> EvidenceSpan:
        return EvidenceSpan(start=s, end=e, text=" ".join(tokens[s:e]))

    rows = [
        ("John", "has", "5", "apples"),
        ("Mary", "has", "3", "books"),
        ("A", "school", "has", "100", "students"),
        ("The", "library", "has", "12", "chairs"),
    ]
    examples = []
    for tokens in rows:
        t = tokens
        # agent is the last token(s) before "has"; count and unit follow it
        has_idx = t.index("has")
        agent_start = 1 if t[0].lower() in {"a", "the"} else 0
        bundle = FeatureBundle.from_mapping({
            "agent": (
                " ".join(t[agent_start:has_idx]),
                span(t, agent_start, has_idx),
            ),
            "count": (int(t[has_idx + 1]), span(t, has_idx + 1, has_idx + 2)),
            "intentionality": (
                "possession",
                NegativeEvidence(0, len(t), "lexical content of 'has'"),
            ),
            "modality": (
                "actual",
                NegativeEvidence(0, len(t), "no modal counter-marker present"),
            ),
            "polarity": (
                "+",
                NegativeEvidence(0, len(t), "no negator present"),
            ),
            "relation": ("has", span(t, has_idx, has_idx + 1)),
            "tense": ("present", span(t, has_idx, has_idx + 1)),
            "unit": (t[has_idx + 2].rstrip("s"), span(t, has_idx + 2, has_idx + 3)),
        })
        examples.append((t, bundle))
    return examples


@pytest.fixture(scope="module")
def phase1_recognizer() -> DerivedRecognizer:
    return derive_recognizer(_make_phase1_examples())


# ---------------------------------------------------------------------------
# Phase 1 — admitted recognition produces a carrier
# ---------------------------------------------------------------------------

class TestPhase1AdmittedCarrier:
    def test_epistemic_graph_is_not_none_on_admit(
        self, phase1_recognizer: DerivedRecognizer
    ) -> None:
        tokens = ("A", "baker", "has", "24", "loaves")
        outcome = recognize(phase1_recognizer, tokens)
        assert outcome.admitted

        node = EpistemicNode(
            node_id=f"{phase1_recognizer.teaching_set_id}:0",
            recognition_outcome=outcome,
        )
        graph = EpistemicGraph(
            nodes=(node,),
            recognizer_id=phase1_recognizer.teaching_set_id,
        )
        assert graph is not None
        assert len(graph.nodes) == 1

    def test_node_epistemic_state_is_evidenced(
        self, phase1_recognizer: DerivedRecognizer
    ) -> None:
        tokens = ("A", "baker", "has", "24", "loaves")
        outcome = recognize(phase1_recognizer, tokens)
        node = EpistemicNode(
            node_id=f"{phase1_recognizer.teaching_set_id}:0",
            recognition_outcome=outcome,
        )
        assert node.epistemic_state == EVIDENCED

    def test_feature_bundle_preserved_in_node(
        self, phase1_recognizer: DerivedRecognizer
    ) -> None:
        tokens = ("A", "baker", "has", "24", "loaves")
        outcome = recognize(phase1_recognizer, tokens)
        node = EpistemicNode(
            node_id=f"{phase1_recognizer.teaching_set_id}:0",
            recognition_outcome=outcome,
        )
        bundle = node.recognition_outcome.proposition
        assert bundle is not None
        assert bundle.get("count") is not None
        assert bundle.get("count").value == 24
        assert bundle.get("agent") is not None

    def test_recognizer_id_matches_teaching_set_id(
        self, phase1_recognizer: DerivedRecognizer
    ) -> None:
        tokens = ("A", "baker", "has", "24", "loaves")
        outcome = recognize(phase1_recognizer, tokens)
        node = EpistemicNode(
            node_id=f"{phase1_recognizer.teaching_set_id}:0",
            recognition_outcome=outcome,
        )
        graph = EpistemicGraph(nodes=(node,), recognizer_id=phase1_recognizer.teaching_set_id)
        assert graph.recognizer_id == phase1_recognizer.teaching_set_id
        assert graph.recognizer_id == outcome.provenance.teaching_set_id

    def test_to_json_is_byte_identical_across_runs(
        self, phase1_recognizer: DerivedRecognizer
    ) -> None:
        tokens = ("A", "baker", "has", "24", "loaves")

        def make_graph() -> EpistemicGraph:
            outcome = recognize(phase1_recognizer, tokens)
            node = EpistemicNode(
                node_id=f"{phase1_recognizer.teaching_set_id}:0",
                recognition_outcome=outcome,
            )
            return EpistemicGraph(
                nodes=(node,), recognizer_id=phase1_recognizer.teaching_set_id
            )

        g1 = make_graph()
        g2 = make_graph()
        assert g1 == g2
        assert g1.to_json() == g2.to_json()

    def test_no_transitions_on_construction(
        self, phase1_recognizer: DerivedRecognizer
    ) -> None:
        tokens = ("A", "baker", "has", "24", "loaves")
        outcome = recognize(phase1_recognizer, tokens)
        node = EpistemicNode(
            node_id=f"{phase1_recognizer.teaching_set_id}:0",
            recognition_outcome=outcome,
        )
        assert node.transitions == ()

    def test_with_transition_appends_and_updates_state(
        self, phase1_recognizer: DerivedRecognizer
    ) -> None:
        tokens = ("A", "baker", "has", "24", "loaves")
        outcome = recognize(phase1_recognizer, tokens)
        node = EpistemicNode(
            node_id=f"{phase1_recognizer.teaching_set_id}:0",
            recognition_outcome=outcome,
        )
        transition = EpistemicTransition(
            from_state=EVIDENCED,
            to_state="verified",
            source="verifier",
            reason="pack cross-reference matched",
        )
        updated = node.with_transition(transition)

        assert updated.epistemic_state == "verified"
        assert len(updated.transitions) == 1
        assert updated.transitions[0] is transition
        # Original node is unchanged (immutable)
        assert node.epistemic_state == EVIDENCED
        assert node.transitions == ()


# ---------------------------------------------------------------------------
# Phase 2 — refused recognition produces no carrier; pipeline unaffected
# ---------------------------------------------------------------------------

class TestPhase2RefusedNoCarrier:
    def test_shape_refusal_yields_none_carrier(
        self, phase1_recognizer: DerivedRecognizer
    ) -> None:
        tokens = ("John", "gave", "5", "apples", "to", "Mary")
        outcome = recognize(phase1_recognizer, tokens)
        assert outcome.state == UNDETERMINED
        assert not outcome.admitted

        # No carrier created on refusal
        epistemic_graph = None
        if outcome.admitted:
            node = EpistemicNode(
                node_id=f"{phase1_recognizer.teaching_set_id}:0",
                recognition_outcome=outcome,
            )
            epistemic_graph = EpistemicGraph(
                nodes=(node,), recognizer_id=phase1_recognizer.teaching_set_id
            )
        assert epistemic_graph is None

    def test_refusal_outcome_carries_typed_reason(
        self, phase1_recognizer: DerivedRecognizer
    ) -> None:
        tokens = ("John", "gave", "5", "apples", "to", "Mary")
        outcome = recognize(phase1_recognizer, tokens)
        assert outcome.refusal_reason is not None
        d = outcome.refusal_reason.as_dict()
        assert d["type"] == "shape"

    def test_graph_get_returns_none_for_missing_id(
        self, phase1_recognizer: DerivedRecognizer
    ) -> None:
        tokens = ("A", "baker", "has", "24", "loaves")
        outcome = recognize(phase1_recognizer, tokens)
        node = EpistemicNode(
            node_id="n0", recognition_outcome=outcome
        )
        graph = EpistemicGraph(nodes=(node,), recognizer_id="x")
        assert graph.get("n0") is node
        assert graph.get("missing") is None


# ---------------------------------------------------------------------------
# Phase 3 — connector derives a valid articulation GraphNode
# ---------------------------------------------------------------------------

class TestPhase3Connector:
    def test_connector_produces_graph_node(
        self, phase1_recognizer: DerivedRecognizer
    ) -> None:
        tokens = ("A", "baker", "has", "24", "loaves")
        outcome = recognize(phase1_recognizer, tokens)
        node = EpistemicNode(
            node_id=f"{phase1_recognizer.teaching_set_id}:0",
            recognition_outcome=outcome,
        )
        gn = epistemic_node_to_graph_node(node, source_intent=IntentTag.RECALL)
        assert gn.subject != ""
        assert gn.predicate != ""
        assert gn.obj != ""
        assert gn.source_intent is IntentTag.RECALL

    def test_connector_agent_and_relation_lifted(
        self, phase1_recognizer: DerivedRecognizer
    ) -> None:
        tokens = ("A", "baker", "has", "24", "loaves")
        outcome = recognize(phase1_recognizer, tokens)
        node = EpistemicNode(
            node_id=f"{phase1_recognizer.teaching_set_id}:0",
            recognition_outcome=outcome,
        )
        gn = epistemic_node_to_graph_node(node, source_intent=IntentTag.RECALL)
        assert gn.subject == "baker"
        assert gn.predicate == "has"
        assert "24" in gn.obj

    def test_connector_raises_on_non_evidenced_node(
        self, phase1_recognizer: DerivedRecognizer
    ) -> None:
        tokens = ("John", "gave", "5", "apples", "to", "Mary")
        outcome = recognize(phase1_recognizer, tokens)
        assert not outcome.admitted
        node = EpistemicNode(
            node_id="n0", recognition_outcome=outcome
        )
        with pytest.raises(ValueError, match="non-EVIDENCED"):
            epistemic_node_to_graph_node(node, source_intent=IntentTag.RECALL)

    def test_derived_graph_node_passes_plan_articulation(
        self, phase1_recognizer: DerivedRecognizer
    ) -> None:
        tokens = ("A", "baker", "has", "24", "loaves")
        outcome = recognize(phase1_recognizer, tokens)
        node = EpistemicNode(
            node_id=f"{phase1_recognizer.teaching_set_id}:0",
            recognition_outcome=outcome,
        )
        gn = epistemic_node_to_graph_node(node, source_intent=IntentTag.RECALL)
        graph = PropositionGraph().add_node(gn)
        target = plan_articulation(graph)
        assert len(target.steps) == 1
        assert target.steps[0].subject == "baker"

    def test_node_id_override(
        self, phase1_recognizer: DerivedRecognizer
    ) -> None:
        tokens = ("A", "baker", "has", "24", "loaves")
        outcome = recognize(phase1_recognizer, tokens)
        node = EpistemicNode(node_id="original", recognition_outcome=outcome)
        gn = epistemic_node_to_graph_node(
            node, source_intent=IntentTag.RECALL, node_id="override"
        )
        assert gn.node_id == "override"

    def test_connector_is_deterministic(
        self, phase1_recognizer: DerivedRecognizer
    ) -> None:
        tokens = ("A", "baker", "has", "24", "loaves")

        def make_gn():
            outcome = recognize(phase1_recognizer, tokens)
            node = EpistemicNode(
                node_id=f"{phase1_recognizer.teaching_set_id}:0",
                recognition_outcome=outcome,
            )
            return epistemic_node_to_graph_node(node, source_intent=IntentTag.RECALL)

        gn1 = make_gn()
        gn2 = make_gn()
        assert gn1 == gn2
