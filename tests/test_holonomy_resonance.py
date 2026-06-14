from __future__ import annotations

import numpy as np

from algebra.cga import cga_inner
from algebra.holonomy import holonomy_encode, holonomy_similarity
from language_packs import load_pack
from language_packs.compiler import compile_entries_to_manifold, load_mounted_packs, load_pack_entries
from morphology.registry import load_morphology


def _encode(manifold, tokens: list[str]) -> np.ndarray:
    return holonomy_encode([manifold.get_versor(t) for t in tokens])


def test_aligned_clause_holonomy_does_not_robustly_beat_misaligned():
    """Honest sibling of the HolonomyAlignmentCase guard in
    tests/test_alignment_graph.py: the cross-language holonomy-CLAUSE resonance
    is NOT robust. The aligned Greek clause is itself FARTHER from the English
    anchor than the misaligned (vitality) negative; the prior assertion passed
    only by averaging in the close Hebrew distance (~1.3% margin) — decoration,
    not proof. See docs/analysis/holonomy-resonance-proof-not-robust-2026-06-14.md.

    NOTE: this is the holonomy-clause claim only. The token-pair cga_inner
    resonance tests below assert a different, narrower property and are not
    covered by that finding.
    """
    _, en = load_pack("en_minimal_v1")
    _, grc = load_pack("grc_logos_micro_v1")

    en_clause = _encode(en, ["word", "beginning", "with", "truth"])
    grc_aligned = _encode(grc, ["\u03bb\u03cc\u03b3\u03bf\u03c2", "\u1f00\u03c1\u03c7\u03ae", "\u1f00\u03bb\u03ae\u03b8\u03b5\u03b9\u03b1"])
    grc_misaligned = _encode(grc, ["\u03bb\u03cc\u03b3\u03bf\u03c2", "\u1f00\u03c1\u03c7\u03ae", "\u03b6\u03c9\u03ae"])

    aligned_dist = float(np.linalg.norm(en_clause - grc_aligned))
    misaligned_dist = float(np.linalg.norm(en_clause - grc_misaligned))
    assert aligned_dist > misaligned_dist, (
        "Aligned Greek clause is now closer than the misaligned negative - the "
        "holonomy-clause resonance may have become real; replace this guard with a "
        "proof and update docs/analysis/holonomy-resonance-proof-not-robust-2026-06-14.md."
    )


def test_triple_alignment_closer_than_other_triples():
    _, en = load_pack("en_minimal_v1")
    _, he = load_pack("he_logos_micro_v1")
    _, grc = load_pack("grc_logos_micro_v1")

    aligned_score = np.mean(
        [
            cga_inner(en.get_versor("word"), he.get_versor("\u05d3\u05d1\u05e8")),
            cga_inner(en.get_versor("word"), grc.get_versor("\u03bb\u03cc\u03b3\u03bf\u03c2")),
            cga_inner(he.get_versor("\u05d3\u05d1\u05e8"), grc.get_versor("\u03bb\u03cc\u03b3\u03bf\u03c2")),
        ]
    )
    misaligned_score = np.mean(
        [
            cga_inner(en.get_versor("word"), he.get_versor("\u05e8\u05d0\u05e9\u05d9\u05ea")),
            cga_inner(en.get_versor("word"), grc.get_versor("\u03c0\u03bd\u03b5\u1fe6\u03bc\u03b1")),
            cga_inner(he.get_versor("\u05d3\u05d1\u05e8"), grc.get_versor("\u1f00\u03c1\u03c7\u03ae")),
        ]
    )
    assert aligned_score > misaligned_score


def test_light_alignment_clusters_across_mounted_trilingual_field():
    manifold = load_mounted_packs(("en_minimal_v1", "he_logos_micro_v1", "grc_logos_micro_v1"))

    aligned_score = np.mean(
        [
            cga_inner(manifold.get_versor("light"), manifold.get_versor("אוֹר")),
            cga_inner(manifold.get_versor("light"), manifold.get_versor("φῶς")),
            cga_inner(manifold.get_versor("אוֹר"), manifold.get_versor("φῶς")),
        ]
    )
    unrelated_score = np.mean(
        [
            cga_inner(manifold.get_versor("light"), manifold.get_versor("דבר")),
            cga_inner(manifold.get_versor("light"), manifold.get_versor("ἀρχή")),
            cga_inner(manifold.get_versor("אוֹר"), manifold.get_versor("ζωή")),
        ]
    )

    assert aligned_score > unrelated_score


def test_word_order_permutation_changes_holonomy():
    _, en = load_pack("en_minimal_v1")
    a = _encode(en, ["word", "truth", "light", "life"])
    b = _encode(en, ["life", "word", "truth", "light"])
    assert abs(holonomy_similarity(a, b) - holonomy_similarity(a, a)) > 1e-4


def test_same_root_hebrew_forms_land_closer_than_unrelated_noun():
    _, he = load_pack("he_logos_micro_v1")

    singular = he.get_versor("\u05d3\u05d1\u05e8")
    plural = he.get_versor("\u05d3\u05d1\u05e8\u05d9\u05dd")
    unrelated = he.get_versor("\u05e8\u05d0\u05e9\u05d9\u05ea")

    assert cga_inner(singular, plural) > cga_inner(singular, unrelated)


def test_structured_morphology_improves_same_root_hebrew_resonance():
    entries = load_pack_entries("he_logos_micro_v1")
    no_morphology, _ = compile_entries_to_manifold(entries)
    structured, _ = compile_entries_to_manifold(entries, load_morphology("he_logos_micro_v1"))

    no_morph_score = cga_inner(no_morphology.get_versor("\u05d3\u05d1\u05e8"), no_morphology.get_versor("\u05d3\u05d1\u05e8\u05d9\u05dd"))
    structured_score = cga_inner(structured.get_versor("\u05d3\u05d1\u05e8"), structured.get_versor("\u05d3\u05d1\u05e8\u05d9\u05dd"))

    assert structured_score > no_morph_score, (
        f"Structured morphology should bring same-root forms closer: "
        f"structured={structured_score:.6f}, no_morphology={no_morph_score:.6f}"
    )
