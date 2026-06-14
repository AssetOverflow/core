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


def test_holonomy_alignment_resonance_is_not_yet_a_robust_proof():
    """Pins the *true* state of the holonomy tri-language resonance: it does
    NOT robustly separate aligned from misaligned clauses under the current
    encoding. See docs/analysis/holonomy-resonance-proof-not-robust-2026-06-14.md.

    The prior `..._positive_closer_than_negative` test asserted a "crown proof"
    that passed only by averaging in the close Hebrew distance and comparing to a
    single cherry-picked negative (a ~1.3% margin) — decoration, not proof
    (CLAUDE.md, Schema-Defined Proof Obligations). This guard asserts the actual
    geometry so the obligation is never silently green:

      * the aligned Greek clause is itself FARTHER from the English anchor than
        the misaligned negative, and
      * the engine's own holonomy_similarity (CGA inner product) anti-correlates
        (the misaligned clause scores as *more* similar).

    A future encoding/metric that makes the resonance genuinely robust SHOULD
    make this guard fail — then replace it with a real proof and update the doc.
    Until then the Studio renders holonomy as missing_evidence.
    """
    case = HolonomyAlignmentCase(
        case_id="HAC-001",
        description=(
            "Aligned Logos clause; cross-language holonomy resonance is NOT yet a "
            "robust proof - see "
            "docs/analysis/holonomy-resonance-proof-not-robust-2026-06-14.md."
        ),
        source_refs=("Gen1:1", "John1:1", "John14:6"),
        pack_ids=("en_minimal_v1", "he_logos_micro_v1", "grc_logos_micro_v1"),
        expected_relation="cross_lang.closer_than_negative",
        negative_source_refs=("John1:4",),
        tolerance=0.0,
    )
    assert case.case_id == "HAC-001"
    assert len(case.pack_ids) == 3

    _, en = load_pack("en_minimal_v1")
    _, grc = load_pack("grc_logos_micro_v1")

    en_h = _encode(en, ["word", "beginning", "with", "truth"])
    grc_aligned = _encode(grc, ["\u03bb\u03cc\u03b3\u03bf\u03c2", "\u1f00\u03c1\u03c7\u03ae", "\u1f00\u03bb\u03ae\u03b8\u03b5\u03b9\u03b1"])
    # Negative: replace truth with vitality - different semantic domain.
    grc_negative = _encode(grc, ["\u03bb\u03cc\u03b3\u03bf\u03c2", "\u1f00\u03c1\u03c7\u03ae", "\u03b6\u03c9\u03ae"])

    # Encoding is deterministic, so this finding is structural, not noise.
    assert np.allclose(
        grc_aligned,
        _encode(grc, ["\u03bb\u03cc\u03b3\u03bf\u03c2", "\u1f00\u03c1\u03c7\u03ae", "\u1f00\u03bb\u03ae\u03b8\u03b5\u03b9\u03b1"]),
    )

    aligned_dist = float(np.linalg.norm(en_h - grc_aligned))
    negative_dist = float(np.linalg.norm(en_h - grc_negative))
    # The honest contradiction: aligned is NOT closer than the misaligned negative.
    assert aligned_dist > negative_dist, (
        "Aligned Greek clause is now closer than the misaligned negative - the "
        "resonance may have become real. Replace this guard with a proper proof "
        "and update docs/analysis/holonomy-resonance-proof-not-robust-2026-06-14.md."
    )
    # The owned similarity metric anti-correlates (misaligned scores higher).
    assert holonomy_similarity(en_h, grc_negative) > holonomy_similarity(en_h, grc_aligned)


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
