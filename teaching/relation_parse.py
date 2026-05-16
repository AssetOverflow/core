"""Typed relation parser — extract (head, relation, tail) triples from corrections.

A correction utterance like "Actually wisdom is judgment." carries a typed
proposition that until now was kept only as opaque text in the teaching
store.  This module lifts the proposition into a typed triple so the
inference operators in ``generate/operators.py`` can walk the typed
relation graph that the teaching store represents.

Determinism: pure regex-driven extraction; no learned classifier; no
external IO.  The relation vocabulary is drawn from the cognition pack's
relation predicates (see ``language_packs/data/en_core_cognition_v1``).
"""

from __future__ import annotations

import re
from typing import Final

# Relation predicates drawn from en_core_cognition_v1 (entries with
# semantic_domains containing "relation.*" or "predicate.*").  Order matters:
# multi-token forms must be tried before single-token forms so "belongs_to"
# is not split into "belongs" + "to".
_RELATIONS: Final[tuple[str, ...]] = (
    "belongs_to",
    "contrasts_with",
    "is_caused_by",
    "is_defined_as",
    "is_verified_as",
    "has_steps",
    "corrects",
    "recalls",
    "grounds",
    "reveals",
    "precedes",
    "follows",
    "produces",
    "causes",
    "means",
    "is",
    "has",
)

# Sentence-leading discourse markers that may prefix the proposition.
_LEADING_MARKERS: Final[tuple[str, ...]] = (
    "actually",
    "no,",
    "no",
    "indeed",
    "really",
    "in fact",
    "rather",
    "instead",
)

_WHITESPACE = re.compile(r"\s+")
_PUNCT_TAIL = re.compile(r"[\.\?!,;:]+$")


def _strip_leading_marker(text: str) -> str:
    lower = text.lower()
    for marker in _LEADING_MARKERS:
        prefix = marker + " "
        if lower.startswith(prefix):
            return text[len(prefix):]
        if lower.startswith(marker + ",") or lower.startswith(marker + ";"):
            return text[len(marker) + 1:].lstrip()
    return text


def _normalize(text: str) -> str:
    text = _strip_leading_marker(text.strip())
    text = _WHITESPACE.sub(" ", text)
    text = _PUNCT_TAIL.sub("", text)
    return text.lower().strip()


def _split_head_relation_tail(text: str) -> tuple[str, str, str] | None:
    """Find the first matching relation predicate; split around it."""
    # Word-boundary form for each relation so "is" does not match inside
    # "wisdom" or similar.  Multi-token relations are matched literally with
    # surrounding spaces.
    for relation in _RELATIONS:
        if "_" in relation or " " in relation:
            # Compound predicates use underscore in the lexicon but appear
            # with underscores in correction text (per test corpus).
            pattern = rf"\b{re.escape(relation)}\b"
        else:
            pattern = rf"\b{re.escape(relation)}\b"
        match = re.search(pattern, text)
        if match is None:
            continue
        head = text[: match.start()].strip()
        tail = text[match.end():].strip()
        if not head or not tail:
            continue
        # Drop trailing/leading articles ("a", "an", "the") from head/tail.
        head = _strip_articles(head)
        tail = _strip_articles(tail)
        if not head or not tail:
            continue
        return head, relation, tail
    return None


_ARTICLES: Final[frozenset[str]] = frozenset({"a", "an", "the"})


def _strip_articles(phrase: str) -> str:
    tokens = phrase.split()
    if tokens and tokens[0] in _ARTICLES:
        tokens = tokens[1:]
    if tokens and tokens[-1] in _ARTICLES:
        tokens = tokens[:-1]
    return " ".join(tokens)


def parse_triple(correction_text: str) -> tuple[str, str, str] | None:
    """Return (head, relation, tail) if the text parses cleanly, else None.

    Pure function; deterministic.  Returns None when no relation predicate
    is found or when either side of the predicate is empty.  Callers may
    treat None as "this correction has no typed-graph content" and fall
    back to the existing opaque-text storage path.
    """
    if not correction_text:
        return None
    normalized = _normalize(correction_text)
    return _split_head_relation_tail(normalized)
