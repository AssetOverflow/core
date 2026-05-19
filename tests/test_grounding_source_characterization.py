"""Grounding-source characterization for future discourse planning.

These tests deliberately avoid the discourse planner contract.  They freeze
the deterministic source ordering that a future GroundingBundle adapter can
consume without re-learning the current surface composers' hidden order.
"""

from __future__ import annotations

from chat.cross_pack_grounding import (
    cross_pack_chains_for_object,
    cross_pack_chains_for_subject,
)
from chat.example_surface import example_grounded_surface
from chat.narrative_surface import narrative_grounded_surface
from chat.teaching_grounding import _all_chains_index


def test_teaching_chain_index_has_stable_key_order_for_discourse_sources() -> None:
    """The aggregated teaching view is keyed by stable subject/intent pairs.

    A future discourse adapter may sort these keys before selecting support
    and relation moves.  Pinning representative keys protects that substrate
    without depending on any new DiscoursePlan type.
    """
    chains = _all_chains_index()
    observed = [
        (key, chain.chain_id, chain.corpus_id, chain.connective, chain.object)
        for key, chain in sorted(chains.items())
        if key[0] in {"knowledge", "light", "memory", "mother", "parent", "truth"}
    ]

    assert observed == [
        (
            ("knowledge", "cause"),
            "cause_knowledge_requires_evidence",
            "cognition_chains_v1",
            "requires",
            "evidence",
        ),
        (
            ("light", "cause"),
            "cause_light_reveals_truth",
            "cognition_chains_v1",
            "reveals",
            "truth",
        ),
        (
            ("light", "verification"),
            "verification_light_reveals_truth",
            "cognition_chains_v1",
            "reveals",
            "truth",
        ),
        (
            ("memory", "verification"),
            "verification_memory_requires_recall",
            "cognition_chains_v1",
            "requires",
            "recall",
        ),
        (
            ("mother", "cause"),
            "cause_mother_precedes_daughter",
            "relations_chains_v2",
            "precedes",
            "daughter",
        ),
        (
            ("parent", "cause"),
            "cause_parent_precedes_child",
            "relations_chains_v1",
            "precedes",
            "child",
        ),
        (
            ("truth", "cause"),
            "cause_truth_grounds_knowledge",
            "cognition_chains_v1",
            "grounds",
            "knowledge",
        ),
        (
            ("truth", "verification"),
            "verification_truth_requires_evidence",
            "cognition_chains_v1",
            "requires",
            "evidence",
        ),
    ]


def test_cross_pack_subject_helpers_return_canonical_discourse_order() -> None:
    """Cross-pack subject helpers sort by ``(intent, connective, object)``."""
    family = cross_pack_chains_for_subject("family")
    parent = cross_pack_chains_for_subject("parent")

    assert [(c.chain_id, c.intent, c.connective, c.object) for c in family] == [
        ("cause_family_grounds_identity", "cause", "grounds", "identity"),
        ("cause_family_supports_memory", "cause", "supports", "memory"),
    ]
    assert [(c.chain_id, c.intent, c.connective, c.object) for c in parent] == [
        ("cause_parent_grounds_understanding", "cause", "grounds", "understanding"),
    ]


def test_cross_pack_object_helpers_return_canonical_discourse_order() -> None:
    """Cross-pack object helpers sort by ``(intent, subject, connective)``."""
    parent = cross_pack_chains_for_object("parent")
    family = cross_pack_chains_for_object("family")

    assert [(c.chain_id, c.intent, c.subject, c.connective) for c in parent] == [
        (
            "verification_understanding_requires_parent",
            "verification",
            "understanding",
            "requires",
        ),
    ]
    assert [(c.chain_id, c.intent, c.subject, c.connective) for c in family] == [
        (
            "verification_identity_requires_family",
            "verification",
            "identity",
            "requires",
        ),
    ]


def test_narrative_clause_order_is_stable_for_mixed_sources() -> None:
    """Narrative surfaces expose the order future relation moves must preserve."""
    surface = narrative_grounded_surface("family", max_clauses=8)
    assert surface is not None

    assert surface.index("family grounds identity") < surface.index(
        "family grounds parent"
    )
    assert surface.index("family grounds parent") < surface.index(
        "family supports memory"
    )
    assert "cross_pack_chains_v1 + relations_chains_v1" in surface


def test_example_clause_order_is_stable_for_mixed_sources() -> None:
    """Example surfaces expose reverse-chain order for future example moves."""
    surface = example_grounded_surface("parent", max_examples=8)
    assert surface is not None

    assert surface.index("child follows parent") < surface.index(
        "family grounds parent"
    )
    assert surface.index("family grounds parent") < surface.index(
        "understanding requires parent"
    )
    assert "cross_pack_chains_v1 + relations_chains_v1" in surface
