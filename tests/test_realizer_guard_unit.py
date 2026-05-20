"""ADR-0075 (C1) — realizer slot-type guard, pure-unit coverage.

Each test gives the guard a minimal POS lookup and asserts the
expected verdict.  No runtime, no pipeline, no fixtures.
"""

from __future__ import annotations

import pytest

from generate.realizer_guard import (
    DISCLOSURE_SURFACE,
    RealizerGuardVerdict,
    check_surface,
)


_POS: dict[str, str] = {
    # Nouns
    "Light": "NOUN", "light": "NOUN",
    "Truth": "NOUN", "truth": "NOUN",
    "Knowledge": "NOUN", "knowledge": "NOUN",
    "Right": "NOUN", "right": "NOUN",
    "thought": "NOUN", "evidence": "NOUN",
    "claim": "NOUN", "state": "NOUN",
    "source": "NOUN", "revelation": "NOUN",
    "judgment": "NOUN", "recall": "NOUN",
    "things": "NOUN", "understanding": "NOUN", "articulation": "NOUN",
    # Verbs
    "reveal": "VERB", "reveals": "VERB",
    "ground": "VERB", "grounds": "VERB",
    "make": "VERB", "makes": "VERB",
    "require": "VERB", "requires": "VERB",
    "perceive": "VERB",
    # Adjectives
    "reviewed": "ADJ", "knowable": "ADJ",
    "justified": "ADJ", "coherent": "ADJ", "grounded": "ADJ",
    # Function words / connectors (returned but not matched as VERB)
    "of": "ADP", "and": "CONJ", "in": "ADP", "or": "CONJ", "for": "ADP",
    "by": "ADP", "that": "PRON",
}


def _lookup(token: str) -> str | None:
    return _POS.get(token)


def _verdict(surface: str) -> RealizerGuardVerdict:
    return check_surface(surface, pos_lookup=_lookup)


# ---------- R1 deferred (see ADR-0075) ----------
#
# R1 ("must contain at least one finite verb") is deferred from
# active C1 scope.  These tests pin the **current** behavior — R1
# surfaces pass even when verb-less — so a future re-enablement is
# a deliberate, intentional change rather than a silent drift.


def test_R1_deferred_verbless_surface_passes():
    v = _verdict("Light right.")
    assert v.status == "ok"


def test_R1_deferred_bare_noun_phrase_passes():
    v = _verdict("Truth knowledge evidence.")
    assert v.status == "ok"


# ---------- R2 ----------


def test_R2_rejects_does_not_followed_by_noun():
    """The canonical observed bug — 'Right does not thought.'"""
    v = _verdict("Right does not thought.")
    assert v.status == "rejected"
    assert v.rule_id == "R2_aux_neg_requires_verb"
    assert "does not thought" in v.detail


def test_R2_rejects_do_not_followed_by_noun():
    v = _verdict("They do not knowledge.")
    assert v.status == "rejected"
    assert v.rule_id == "R2_aux_neg_requires_verb"


def test_R2_rejects_did_not_followed_by_noun():
    v = _verdict("Light did not truth.")
    assert v.status == "rejected"
    assert v.rule_id == "R2_aux_neg_requires_verb"


def test_R2_accepts_does_not_followed_by_verb():
    v = _verdict("Light does not reveal truth.")
    assert v.status == "ok"


def test_R2_accepts_does_not_with_adverb_then_verb():
    """Adverbs between 'not' and the verb are skipped."""
    v = _verdict("Light does not always reveal truth.")
    assert v.status == "ok"


def test_R2_rejects_does_not_with_adverb_then_noun():
    v = _verdict("Right does not always thought.")
    assert v.status == "rejected"
    assert v.rule_id == "R2_aux_neg_requires_verb"


def test_R2_rejects_does_not_at_end_of_surface():
    v = _verdict("Light does not.")
    assert v.status == "rejected"
    assert v.rule_id == "R2_aux_neg_requires_verb"
    assert "missing" in v.detail


# ---------- R3 ----------


def test_R3_accepts_is_not_followed_by_noun():
    v = _verdict("Light is not knowledge.")
    assert v.status == "ok"


def test_R3_accepts_are_not_followed_by_adjective():
    v = _verdict("Claims are not reviewed.")
    assert v.status == "ok"


def test_R3_accepts_is_not_with_determiner():
    v = _verdict("Light is not a claim.")
    assert v.status == "ok"


def test_R3_rejects_is_not_followed_by_verb():
    v = _verdict("Light is not reveal.")
    assert v.status == "rejected"
    assert v.rule_id == "R3_be_neg_requires_predicate"


def test_R3_rejects_was_not_followed_by_verb():
    v = _verdict("Light was not reveals.")
    assert v.status == "rejected"
    assert v.rule_id == "R3_be_neg_requires_predicate"


def test_R3_rejects_is_not_at_end():
    v = _verdict("Light is not.")
    assert v.status == "rejected"
    assert v.rule_id == "R3_be_neg_requires_predicate"


# ---------- DISCLOSURE_SURFACE itself must pass ----------


def test_disclosure_surface_passes_guard():
    """Critical: the fallback string must not be rejected by its own
    guard, otherwise routing on rejection would loop."""
    v = _verdict(DISCLOSURE_SURFACE)
    assert v.status == "ok"
    assert v.rule_id == ""


# ---------- Empty / whitespace surfaces ----------


def test_empty_surface_is_ok():
    v = _verdict("")
    assert v.status == "ok"


def test_whitespace_only_surface_is_ok():
    v = _verdict("   \n  \t  ")
    assert v.status == "ok"


def test_punctuation_only_surface_is_ok():
    """No alphabetic tokens ⇒ guard cannot evaluate ⇒ pass through."""
    v = _verdict("... !!! ???")
    assert v.status == "ok"


# ---------- Robustness ----------


def test_unknown_token_after_aux_neg_fails_open():
    """Unknown content tokens fall through pack lookup — R2 fails
    OPEN (does not reject) so the guard never regresses a
    currently-passing case where the realizer emits valid English
    the pack happens not to enumerate."""
    v = _verdict("Light does not xyzzy.")
    assert v.status == "ok"


def test_unknown_token_after_be_neg_fails_open():
    """R3 also fails open on unknown tokens.  Critical for cases like
    'is not yet ratified' where 'ratified' is real English not in
    the pack lexicon."""
    v = _verdict("Step-by-step guidance is not yet ratified.")
    assert v.status == "ok"


def test_known_pack_verb_after_aux_neg_passes():
    v = _verdict("Light does not perceive truth.")
    assert v.status == "ok"


def test_verdict_is_frozen():
    v = _verdict("Light reveals truth.")
    with pytest.raises(Exception):  # FrozenInstanceError
        v.status = "rejected"  # type: ignore[misc]
