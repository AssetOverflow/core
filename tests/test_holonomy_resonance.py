from __future__ import annotations

import numpy as np

from algebra.cga import cga_inner
from algebra.holonomy import holonomy_encode, holonomy_similarity
from language_packs import load_pack


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

    word_trip = [
        en.get_versor("word"),
        he.get_versor("דבר"),
        grc.get_versor("λόγος"),
    ]
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
