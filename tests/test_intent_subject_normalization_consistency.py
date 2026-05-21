"""Subject normalization consistency across intent paths (comb pass 2026-05-21).

Pre-fix ``classify_intent`` applied ``_normalize_subject`` only to
DEFINITION / CAUSE / VERIFICATION paths.  COMPARISON, FRAME_TRANSFER,
TRANSITIVE_QUERY (non-"means" branch), and BELONG_QUERY returned bare
``.strip()`` subjects.  A probe like *"Compare the parent and a child"*
would carry the articles into the subject slot, breaking downstream
pack-resolver lookups that key on bare lemmas.

These tests pin the post-fix consistency: every intent path now
strips leading articles via ``_normalize_subject(..., IntentTag.DEFINITION)``
(article-strip + multi-word preservation; aux-verb stripping stays
CAUSE/VERIFICATION-only).
"""

from __future__ import annotations

from generate.intent import IntentTag, classify_intent


def test_comparison_strips_articles_from_both_subjects() -> None:
    intent = classify_intent("Compare the parent and a child")
    assert intent.tag is IntentTag.COMPARISON
    assert intent.subject == "parent"
    assert intent.secondary_subject == "child"


def test_comparison_preserves_multi_word_subjects() -> None:
    intent = classify_intent("Compare artificial intelligence and natural intelligence")
    assert intent.tag is IntentTag.COMPARISON
    # Multi-word noun phrases survive intact; only leading articles strip.
    assert intent.subject == "artificial intelligence"
    assert intent.secondary_subject == "natural intelligence"


def test_comparison_no_articles_byte_identical_to_pre_fix() -> None:
    """The cognition eval cases (no articles) must remain byte-identical."""
    intent = classify_intent("Compare memory and recall")
    assert intent.subject == "memory"
    assert intent.secondary_subject == "recall"


def test_transitive_query_strips_articles() -> None:
    """The non-"means" TRANSITIVE_QUERY branch now normalizes consistently
    with the "means" → DEFINITION redirect."""
    # TRANSITIVE_QUERY shape is "what does X R …"; the subject capture
    # is what we're testing for article-strip.
    intent = classify_intent("What does the parent require")
    assert intent.tag is IntentTag.TRANSITIVE_QUERY
    assert intent.subject == "parent"


def test_belong_query_strips_articles() -> None:
    # BELONG_QUERY shape is "where does X belong"; test that the
    # captured subject loses its article.
    intent = classify_intent("Where does the dog belong")
    assert intent.tag is IntentTag.TRANSITIVE_QUERY
    assert intent.relation == "belongs_to"
    assert intent.subject == "dog"


def test_definition_path_unchanged() -> None:
    """The DEFINITION path was already normalizing; this pins it."""
    intent = classify_intent("What is the parent?")
    assert intent.tag is IntentTag.DEFINITION
    assert intent.subject == "parent"


def test_cause_path_keeps_aux_verb_strip() -> None:
    """CAUSE / VERIFICATION normalization still strips aux verbs and
    returns the head noun — the comb-pass fix did not regress this."""
    intent = classify_intent("Why does light exist?")
    assert intent.tag is IntentTag.CAUSE
    # Aux-verb-strip + head-noun extraction → "light"
    assert intent.subject == "light"
