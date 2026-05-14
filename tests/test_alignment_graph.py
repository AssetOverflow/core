"""Tests for the alignment graph and HolonomyAlignmentCase formal proof."""

from __future__ import annotations

import numpy as np
import pytest

from alignment.graph import load_alignment
from language_packs.schema import AlignmentEdge, HolonomyAlignmentCase
from algebra.holonomy import holonomy_encode, holonomy_similarity
from language_packs import load_pack


# ---------------------------------------------------------------------------
# Alignment graph loading
# ---------------------------------------------------------------------------

def test_load_he_alignment_returns_depth_and_english_anchor_edges():
    graph = load_alignment("he_logos_micro_v1")
    assert len(graph) == 11
    for edge in graph.edges:
        assert isinstance(edge, AlignmentEdge)
        assert 0.0 <= edge.weight <= 1.0
        assert edge.relation.startswith("cross_lang.")


def test_load_grc_alignment_returns_depth_and_english_anchor_edges():
    graph = load_alignment("grc_logos_micro_v1")
    assert len(graph) == 9


def test_load_en_alignment_returns_empty_graph():
    """Operational base packs carry no cross-language edges yet."""
    graph = load_alignment("en_minimal_v1")
    assert len(graph) == 0


def test_davar_logos_edge_weight_above_threshold():
    """דבר ↔ λόγος edge weight must be >= 0.9 (logos.utterance canonical pair)."""
    graph = load_alignment("he_logos_micro_v1")
    edge = graph.get_edge("he-001", "grc-001")
    assert edge is not None, "he-001 → grc-001 edge missing"
    assert edge.weight >= 0.9
    assert edge.relation == "cross_lang.logos.utterance"


def test_aligned_pairs_by_relation_prefix():
    """aligned_pairs() should filter by relation prefix correctly."""
    graph = load_alignment("he_logos_micro_v1")
    all_cross = graph.aligned_pairs("cross_lang.logos")
    assert len(all_cross) == 11

    logos_only = graph.aligned_pairs("cross_lang.logos.utterance")
    assert {edge.target_id for edge in logos_only} == {"grc-001", "en-024"}
    assert all(edge.source_id == "he-001" for edge in logos_only)


def test_edges_from_source():
    graph = load_alignment("grc_logos_micro_v1")
    edges = graph.edges_from("grc-001")
    assert {edge.target_id for edge in edges} == {"he-001", "en-024"}


# ---------------------------------------------------------------------------
# HolonomyAlignmentCase formal proof
# ---------------------------------------------------------------------------

def _encode(manifold, tokens: list[str]) -> np.ndarray:
    return holonomy_encode([manifold.get_versor(t) for t in tokens])


def test_holonomy_alignment_case_positive_closer_than_negative():
    """
    Crown proof case: positive aligned triple must be geometrically closer
    than the negative (misaligned) triple.

    This wraps the geometry proven in test_holonomy_resonance.py into the
    formal HolonomyAlignmentCase schema type, so the proof is both
    machine-checkable and linked to the schema's contract.
    """
    case = HolonomyAlignmentCase(
        case_id="HAC-001",
        description=(
            "Aligned Logos clause (word/דבר/λόγος + beginning/ראשית/ἀρχή + truth/אמת/ἀλήθεια) "
            "produces closer holonomies across three languages than a misaligned clause "
            "substituting ζωή (vitality) for ἀλήθεια (truth)."
        ),
        source_refs=("Gen1:1", "John1:1", "John14:6"),
        pack_ids=("en_minimal_v1", "he_logos_micro_v1", "grc_logos_micro_v1"),
        expected_relation="cross_lang.closer_than_negative",
        negative_source_refs=("John1:4",),
        tolerance=0.0,
    )

    # Validate the case schema itself
    assert case.case_id == "HAC-001"
    assert len(case.pack_ids) == 3
    assert len(case.source_refs) >= 2

    # Load packs
    _, en = load_pack("en_minimal_v1")
    _, he = load_pack("he_logos_micro_v1")
    _, grc = load_pack("grc_logos_micro_v1")

    # Positive triple: aligned canonical clause across all three languages
    en_h = _encode(en, ["word", "beginning", "with", "truth"])
    he_h = _encode(he, ["\u05d3\u05d1\u05e8", "\u05e8\u05d0\u05e9\u05d9\u05ea", "\u05d0\u05de\u05ea"])
    grc_h = _encode(grc, ["\u03bb\u03cc\u03b3\u03bf\u03c2", "\u1f00\u03c1\u03c7\u03ae", "\u1f00\u03bb\u03ae\u03b8\u03b5\u03b9\u03b1"])

    # Negative: replace ἀλήθεια with ζωή — different semantic domain
    grc_neg_h = _encode(grc, ["\u03bb\u03cc\u03b3\u03bf\u03c2", "\u1f00\u03c1\u03c7\u03ae", "\u03b6\u03c9\u03ae"])

    # Positive score: distance from the English anchor to aligned clauses.
    positive_dist = (
        np.linalg.norm(en_h - he_h) +
        np.linalg.norm(en_h - grc_h)
    ) / 2.0

    # Negative score: distance from the English anchor to a Greek clause with
    # the misaligned token.
    negative_dist = np.linalg.norm(en_h - grc_neg_h)

    # The formal case assertion: aligned closer than misaligned
    assert positive_dist < negative_dist, (
        f"HolonomyAlignmentCase {case.case_id} failed: "
        f"positive_dist={positive_dist:.6f} >= negative_dist={negative_dist:.6f}. "
        f"Case: {case.description}"
    )


def test_holonomy_alignment_case_schema_validation():
    """HolonomyAlignmentCase must reject under-specified instances."""
    with pytest.raises(ValueError, match="at least two source_refs"):
        HolonomyAlignmentCase(
            case_id="BAD-001",
            description="missing refs",
            source_refs=("Gen1:1",),  # only one
            pack_ids=("en_minimal_v1", "he_logos_micro_v1"),
            expected_relation="cross_lang.closer_than_negative",
        )

    with pytest.raises(ValueError, match="at least two pack_ids"):
        HolonomyAlignmentCase(
            case_id="BAD-002",
            description="missing packs",
            source_refs=("Gen1:1", "John1:1"),
            pack_ids=("en_minimal_v1",),  # only one
            expected_relation="cross_lang.closer_than_negative",
        )
