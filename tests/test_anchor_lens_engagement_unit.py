"""Unit coverage for the anchor-lens engagement resolver (ADR-0073c).

Tests :func:`chat.pack_grounding._resolve_anchor_lens_mode` and
:func:`chat.pack_grounding._maybe_append_anchor_lens_annotation` in
isolation, separate from the full chat() round-trip.
"""

from __future__ import annotations

from chat.pack_grounding import (
    _maybe_append_anchor_lens_annotation,
    _resolve_anchor_lens_mode,
)
from packs.anchor_lens import AnchorLens, UNANCHORED, load_anchor_lens


def test_unanchored_sentinel_returns_none_for_every_lemma():
    for lemma in ("knowledge", "truth", "light", "word"):
        assert _resolve_anchor_lens_mode(lemma, UNANCHORED) is None


def test_default_unanchored_pack_returns_none_for_every_lemma():
    lens = load_anchor_lens("default_unanchored_v1")
    for lemma in ("knowledge", "truth", "light", "word"):
        assert _resolve_anchor_lens_mode(lemma, lens) is None


def test_grc_logos_v1_engages_on_knowledge_only():
    lens = load_anchor_lens("grc_logos_v1")
    assert _resolve_anchor_lens_mode("knowledge", lens) == "systematic"


def test_grc_logos_v1_does_not_engage_on_truth():
    lens = load_anchor_lens("grc_logos_v1")
    assert _resolve_anchor_lens_mode("truth", lens) is None


def test_grc_logos_v1_does_not_engage_on_unaligned_lemma():
    lens = load_anchor_lens("grc_logos_v1")
    assert _resolve_anchor_lens_mode("polarity", lens) is None


def test_he_logos_v1_engages_on_truth_only():
    lens = load_anchor_lens("he_logos_v1")
    assert _resolve_anchor_lens_mode("truth", lens) == "covenant-verity"


def test_he_logos_v1_does_not_engage_on_knowledge():
    lens = load_anchor_lens("he_logos_v1")
    assert _resolve_anchor_lens_mode("knowledge", lens) is None


def test_engagement_case_insensitive():
    lens = load_anchor_lens("grc_logos_v1")
    assert _resolve_anchor_lens_mode("KNOWLEDGE", lens) == "systematic"
    assert _resolve_anchor_lens_mode("  knowledge  ", lens) == "systematic"


def test_annotation_appended_before_trailing_period():
    surface = "Knowledge is X. pack-grounded (en_core_cognition_v1)."
    lens = load_anchor_lens("grc_logos_v1")
    out = _maybe_append_anchor_lens_annotation(surface, "knowledge", lens)
    assert out == (
        "Knowledge is X. pack-grounded (en_core_cognition_v1) "
        "[lens(grc_logos_v1):systematic]."
    )


def test_annotation_appended_without_trailing_period():
    surface = "Knowledge is X. pack-grounded (en_core_cognition_v1)"
    lens = load_anchor_lens("grc_logos_v1")
    out = _maybe_append_anchor_lens_annotation(surface, "knowledge", lens)
    assert out == (
        "Knowledge is X. pack-grounded (en_core_cognition_v1) "
        "[lens(grc_logos_v1):systematic]"
    )


def test_annotation_noop_when_lens_does_not_engage():
    surface = "Truth is X. pack-grounded (en_core_cognition_v1)."
    lens = load_anchor_lens("grc_logos_v1")
    assert _maybe_append_anchor_lens_annotation(surface, "truth", lens) == surface


def test_annotation_noop_under_unanchored():
    surface = "Knowledge is X. pack-grounded (en_core_cognition_v1)."
    out = _maybe_append_anchor_lens_annotation(surface, "knowledge", UNANCHORED)
    assert out == surface


def test_annotation_is_pure_ascii():
    """Hard glyph-leak gate at the helper level: annotation must
    never carry non-ASCII even when the lens substrate is grc/he."""
    surface = "Truth is X. pack-grounded (en_core_cognition_v1)."
    lens = load_anchor_lens("he_logos_v1")
    out = _maybe_append_anchor_lens_annotation(surface, "truth", lens)
    out.encode("ascii")  # raises if any non-ASCII slipped through


def test_synthetic_lens_with_atom_not_in_substrate_returns_none():
    """A lens with preferences that don't match any substrate lemma
    is structurally engagement-incapable; the resolver returns None
    even if the lens is otherwise well-formed."""
    fake = AnchorLens(
        lens_id="synthetic_v1",
        version="0.0.0",
        description="test only",
        substrate="grc",
        atom="logos.nonexistent.atom",
        cognitive_mode="phantom",
    )
    for lemma in ("knowledge", "truth", "light", "word"):
        assert _resolve_anchor_lens_mode(lemma, fake) is None
