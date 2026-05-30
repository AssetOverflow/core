"""ADR-0192 — open the discrete_count counted-noun class.

The discrete_count matcher gated the counted noun against a CLOSED ratified
set (``observed_counted_nouns``): "Betty has 24 marbles" matched only
because "marbles" was ratified, while "Randy has 60 mango trees" / "Sam has
12 red apples" emitted no anchor purely because the noun was unseen.

This opens the single-anchor possession/acquisition path to an open
noun-phrase (adjective* + multi-word head), keeping every other narrowness
layer (proper-noun subject, possession/acquisition verb whitelist, single
numeric token, no clause-split). Wrong=0 is held downstream by the ADR-0191
completeness guard + round-trip + branch-disagreement — not by the curated
noun list.
"""
from __future__ import annotations

import pytest

from generate.recognizer_match import match as rmatch
from generate.math_candidate_graph import _load_ratified_registry_or_empty
from generate.recognizer_anchor_inject import inject_from_match

_REG = _load_ratified_registry_or_empty()


def _anchors(sentence: str) -> int:
    m = rmatch(sentence, _REG, prior_subject=None) if _REG else None
    return len(m.parsed_anchors) if m is not None else -1


# --- Now-extractable open-vocabulary possession/acquisition statements ----
@pytest.mark.parametrize("sentence", [
    "Randy has 60 mango trees.",            # multi-word head
    "Randy has 60 trees on his farm.",      # single head + trailing PP
    "Randy has 60 mango trees on his farm.",# both
    "Sam has 12 red apples.",               # adjective + head
    "Tom bought 5 green bottles.",          # acquisition + adjective
])
def test_open_noun_now_extracts(sentence: str) -> None:
    assert _anchors(sentence) == 1, f"expected one anchor for {sentence!r}"


def test_baseline_single_word_still_works() -> None:
    """The previously-working closed-set case is unchanged."""
    assert _anchors("Betty has 24 marbles.") == 1


# --- Noun phrase must NOT swallow the trailing prepositional phrase -------
def test_noun_phrase_stops_before_preposition() -> None:
    m = rmatch("Randy has 60 mango trees on his farm.", _REG, prior_subject=None)
    assert m is not None and m.parsed_anchors
    assert m.parsed_anchors[0]["counted_noun"].lower() == "mango trees"


# --- wrong=0 guards: shapes that MUST still refuse (no anchor) -------------
@pytest.mark.parametrize("sentence", [
    "Julie is reading a 120-page book.",          # verb not possession/acquisition
    "Randy has many apples.",                      # indefinite quantifier, no count
    "Randy has 60 apples and 30 oranges.",         # clause/enumeration split
])
def test_dangerous_shapes_still_refuse(sentence: str) -> None:
    assert _anchors(sentence) == 0, f"expected no anchor for {sentence!r}"
