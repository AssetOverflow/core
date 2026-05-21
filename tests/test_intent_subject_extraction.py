"""ADR-0049 — intent classifier subject extraction tests.

Contract pinned here:

  - Articles ("a", "an", "the") are stripped from the subject phrase
    for every intent that runs through the rule table.
  - For CAUSE and VERIFICATION intents, the subject is reduced to the
    head noun: leading auxiliary verbs ("does", "is", "can", ...) are
    stripped, then the first remaining token is returned.
  - For DEFINITION / RECALL / PROCEDURE intents, multi-word noun
    phrases are preserved (only articles + trailing punctuation are
    stripped) so that proper noun phrases like "artificial
    intelligence" survive.
  - Trailing punctuation (``?``, ``.``, ``!``) is removed.
  - Empty / all-stopword inputs fall back to the original cleaned
    phrase rather than producing an empty subject.
  - The normalizer is pack-agnostic: no pack loading, no pack-keyed
    lookup; this is a pure syntactic transform.

These tests are intentionally narrow and pin only the post-processor
behaviour.  Downstream tests (``test_pack_grounding``) cover the
end-to-end lift from this change reaching the pack-grounded surface.
"""

from __future__ import annotations

import pytest

from generate.intent import (
    DialogueIntent,
    IntentTag,
    classify_intent,
)


# ---------------------------------------------------------------------------
# DEFINITION — article stripping
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "prompt,expected_subject",
    [
        ("What is a procedure?", "procedure"),
        ("What is a relation?", "relation"),
        ("What is an answer?", "answer"),
        ("What is the truth?", "truth"),
        ("What is light?", "light"),  # already single-word, no change
        ("What is artificial intelligence?", "artificial intelligence"),  # multi-word noun phrase preserved
    ],
)
def test_definition_strips_articles(prompt: str, expected_subject: str) -> None:
    intent = classify_intent(prompt)
    assert intent.tag is IntentTag.DEFINITION
    assert intent.subject == expected_subject


# ---------------------------------------------------------------------------
# CAUSE — head-noun extraction past leading aux verb
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "prompt,expected_subject",
    [
        ("Why does light exist?", "light"),
        ("Why does knowledge require evidence?", "knowledge"),
        ("Why is memory important?", "memory"),
        ("Why are categories useful?", "categories"),
        ("Why can a procedure fail?", "procedure"),  # aux 'can' then article 'a'
    ],
)
def test_cause_extracts_head_noun(prompt: str, expected_subject: str) -> None:
    intent = classify_intent(prompt)
    assert intent.tag is IntentTag.CAUSE
    assert intent.subject == expected_subject


# ---------------------------------------------------------------------------
# VERIFICATION — head-noun extraction past leading aux verb
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "prompt,expected_subject",
    [
        ("Does memory require recall?", "memory"),
        ("Is light a wave?", "light"),
        ("Can a procedure fail?", "procedure"),
        ("Are categories useful?", "categories"),
        ("Has truth been defined?", "truth"),
    ],
)
def test_verification_extracts_head_noun(prompt: str, expected_subject: str) -> None:
    intent = classify_intent(prompt)
    assert intent.tag is IntentTag.VERIFICATION
    assert intent.subject == expected_subject


# ---------------------------------------------------------------------------
# RECALL — already minimal, articles still stripped
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "prompt,expected_subject",
    [
        ("Remember light", "light"),
        ("Remember the truth", "truth"),
        ("Remember a procedure", "procedure"),
        # ``recall`` is a synonym imperative of ``remember`` and must
        # route identically.  The articulation breadth benchmark probe
        # ``"Recall truth."`` was misclassified as UNKNOWN until the
        # trigger pattern in ``_RULES`` was widened to ``(?:remember|
        # recall)\s+`` — without this case the regression silently
        # returns.
        ("Recall light", "light"),
        ("Recall the truth", "truth"),
        ("Recall a procedure", "procedure"),
        ("Recall truth.", "truth"),
    ],
)
def test_recall_strips_articles(prompt: str, expected_subject: str) -> None:
    intent = classify_intent(prompt)
    assert intent.tag is IntentTag.RECALL
    assert intent.subject == expected_subject


# ---------------------------------------------------------------------------
# CORRECTION — word-boundary discipline on the trigger pattern
# ---------------------------------------------------------------------------
#
# Until a recent fix, the CORRECTION regex matched the bare token ``no``
# without word boundaries.  Combined with ``re.match``'s start anchor,
# every prompt beginning with ``No``-as-prefix (``Notice``, ``Note``,
# ``Now``, ``Nothing``, ``Nominate``, ``Norma``, ``Notwithstanding``)
# silently routed to CORRECTION with a mangled subject like
# ``"w remember light"`` (from ``"Now remember light."``).  The same
# hazard threatened ``incorrect`` / ``incorrectly``, ``actually`` /
# ``actualization``, ``correction`` / ``corrections``.  The fix added
# ``\b`` anchors on both sides of the alternation; these parametrized
# cases pin the boundary discipline against regression.


@pytest.mark.parametrize(
    "prompt",
    [
        "No, that's wrong.",
        "No.",
        "No way.",
        "no, knowledge is wrong.",
        "Incorrect.",
        "Actually, that's false.",
        "Correction: memory is not storage.",
        "That's wrong.",
    ],
)
def test_correction_canonical_forms_still_route(prompt: str) -> None:
    """Legitimate CORRECTION pragmas must still classify after the
    word-boundary fix narrowed the alternation."""
    intent = classify_intent(prompt)
    assert intent.tag is IntentTag.CORRECTION


@pytest.mark.parametrize(
    "prompt",
    [
        # ``No``-prefixed words that previously misfired
        "Nothing matters.",
        "Notice the truth.",
        "Note that recall fires.",
        "Nominate a candidate.",
        "Now remember light.",
        "Norma is here.",
        "Notwithstanding the evidence.",
        # ``Incorrect``-prefixed / ``Correction``-prefixed words
        "Incorrectly stated.",
        "Corrections department.",
        # ``Actually`` prefix — rarer but symmetric
        "Actualization of intent.",
    ],
)
def test_correction_does_not_eat_no_prefixed_words(prompt: str) -> None:
    """Words beginning with the CORRECTION trigger letters must not
    silently route to CORRECTION via a missing word-boundary anchor."""
    intent = classify_intent(prompt)
    assert intent.tag is not IntentTag.CORRECTION


# ---------------------------------------------------------------------------
# Edge cases — degenerate inputs do not produce empty subjects
# ---------------------------------------------------------------------------


def test_definition_with_only_article_falls_back() -> None:
    """``What is the?`` is malformed; the normalizer must not empty the
    subject — it falls back to the cleaned original."""
    intent = classify_intent("What is the?")
    assert intent.tag is IntentTag.DEFINITION
    assert intent.subject != ""


def test_verification_with_only_aux_falls_back() -> None:
    """``Is is?`` is degenerate; the normalizer must not empty the subject."""
    # The rule table will match this as VERIFICATION; head-noun extraction
    # would strip all tokens, so the fallback path kicks in.
    intent = classify_intent("Is is is?")
    assert intent.tag is IntentTag.VERIFICATION
    assert intent.subject != ""


def test_empty_prompt_returns_unknown_with_empty_subject() -> None:
    intent = classify_intent("")
    assert intent.tag is IntentTag.UNKNOWN
    assert intent.subject == ""


def test_unknown_intent_preserves_raw_subject() -> None:
    """UNKNOWN-tag prompts bypass the normalizer entirely so the raw
    input survives for debugging / future-pattern detection."""
    intent = classify_intent("light logos")
    assert intent.tag is IntentTag.UNKNOWN
    assert intent.subject == "light logos"


# ---------------------------------------------------------------------------
# Trailing punctuation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "prompt",
    [
        "What is light?",
        "What is light.",
        "What is light!",
        "What is light",
    ],
)
def test_trailing_punctuation_does_not_affect_subject(prompt: str) -> None:
    intent = classify_intent(prompt)
    assert intent.tag is IntentTag.DEFINITION
    assert intent.subject == "light"


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


def test_normalization_is_deterministic() -> None:
    """Same prompt must produce byte-identical DialogueIntent on repeat
    classification — no randomness, no state."""
    prompt = "Why does memory require recall?"
    seen: set[DialogueIntent] = set()
    for _ in range(5):
        seen.add(classify_intent(prompt))
    assert len(seen) == 1


# ---------------------------------------------------------------------------
# Existing intent-test contract still holds (loose ``in subject.lower()``)
# ---------------------------------------------------------------------------


def test_legacy_loose_contract_still_holds() -> None:
    """Pre-ADR-0049 tests assert ``"field" in intent.subject.lower()``
    for ``"Why does the field diverge?"`` — ADR-0049 tightens the
    subject to ``"field"``, which still satisfies the substring check."""
    intent = classify_intent("Why does the field diverge?")
    assert intent.tag is IntentTag.CAUSE
    assert "field" in intent.subject.lower()
    assert intent.subject == "field"


# ---------------------------------------------------------------------------
# Pack-grounded path end-to-end — ADR-0049 unblocks ADR-0048 cases
# ---------------------------------------------------------------------------


def test_pack_grounded_surface_lifts_with_article_stripped() -> None:
    """``What is a procedure?`` was previously routed to the universal
    disclosure because the subject ``"a procedure"`` did not match the
    pack lemma index.  Post-ADR-0049 the article is stripped and the
    pack-grounded surface engages."""
    from chat.runtime import ChatRuntime

    rt = ChatRuntime()
    resp = rt.chat("What is a procedure?")
    assert resp.grounding_source == "pack"
    # Case-insensitive: gloss-backed surfaces capitalize the lemma
    # at sentence start (Procedure is ...).
    assert "procedure" in resp.surface.lower()
