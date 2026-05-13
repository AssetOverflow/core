from __future__ import annotations

import numpy as np

from algebra.cga import cga_inner
from algebra.holonomy import holonomy_encode, holonomy_similarity
from language_packs import load_pack
from language_packs.compiler import compile_entries_to_manifold, load_pack_entries
from morphology.registry import load_morphology


def _encode(manifold, tokens: list[str]) -> np.ndarray:
    return holonomy_encode([manifold.get_versor(t) for t in tokens])


def test_aligned_clauses_have_higher_similarity_than_unrelated():
    _, en = load_pack("en_minimal_v1")
    _, he = load_pack("he_logos_micro_v1")
    _, grc = load_pack("grc_logos_micro_v1")

    en_clause = _encode(en, ["word", "beginning", "with", "truth"])
    he_clause = _encode(he, ["דבר", "ראשית", "אמת"])
    grc_clause = _encode(grc, ["λόγος", "ἀρχή", "ἀλήθεια"])
    grc_unrelated = _encode(grc, ["λόγος", "ἀρχή", "ζωή"])

    aligned = (np.linalg.norm(en_clause - he_clause) + np.linalg.norm(en_clause - grc_clause)) / 2.0
    unrelated = np.linalg.norm(en_clause - grc_unrelated)
    assert aligned < unrelated


def test_triple_alignment_closer_than_other_triples():
    _, en = load_pack("en_minimal_v1")
    _, he = load_pack("he_logos_micro_v1")
    _, grc = load_pack("grc_logos_micro_v1")

    aligned_score = np.mean(
        [
            cga_inner(en.get_versor("word"), he.get_versor("דבר")),
            cga_inner(en.get_versor("word"), grc.get_versor("λόγος")),
            cga_inner(he.get_versor("דבר"), grc.get_versor("λόγος")),
        ]
    )
    misaligned_score = np.mean(
        [
            cga_inner(en.get_versor("word"), he.get_versor("ראשית")),
            cga_inner(en.get_versor("word"), grc.get_versor("πνεῦμα")),
            cga_inner(he.get_versor("דבר"), grc.get_versor("ἀρχή")),
        ]
    )
    assert aligned_score > misaligned_score


def test_word_order_permutation_changes_holonomy():
    _, en = load_pack("en_minimal_v1")
    a = _encode(en, ["word", "truth", "light", "life"])
    b = _encode(en, ["life", "word", "truth", "light"])
    assert abs(holonomy_similarity(a, b) - holonomy_similarity(a, a)) > 1e-4


def test_same_root_hebrew_forms_land_closer_than_unrelated_noun():
    _, he = load_pack("he_logos_micro_v1")

    singular = he.get_versor("דבר")
    plural = he.get_versor("דברים")
    unrelated = he.get_versor("ראשית")

    assert cga_inner(singular, plural) > cga_inner(singular, unrelated)


def test_structured_morphology_improves_same_root_hebrew_resonance():
    entries = load_pack_entries("he_logos_micro_v1")
    no_morphology = compile_entries_to_manifold(entries)
    structured = compile_entries_to_manifold(entries, load_morphology("he_logos_micro_v1"))

    no_morph_score = cga_inner(no_morphology.get_versor("דבר"), no_morphology.get_versor("דברים"))
    structured_score = cga_inner(structured.get_versor("דבר"), structured.get_versor("דברים"))

    assert structured_score > no_morph_score, (
        f"Structured morphology should bring same-root forms closer: "
        f"structured={structured_score:.6f}, no_morphology={no_morph_score:.6f}"
    )
