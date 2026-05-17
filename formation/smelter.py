"""Deterministic pattern-based Smelter (Phase 8a).

Turns raw text in an ``OreBundle`` into candidate dataclasses suitable for
the Forge.  Strictly pure: no LLM, no network, no async, no floats.

Extraction strategy:

1. *Concepts* - sentences of the form ``"X is defined as Y"``, ``"X means
   Y"``, ``"X is a Y"`` where ``X`` is a 1-3 token canonical term.
2. *Relations* - sentences whose normalized form parses cleanly through
   ``teaching.relation_parse.parse_triple``.  We only emit triples that
   survive the round-trip.
3. *Counters* - sentences prefixed with a negation marker
   (``"It is a misconception that"``, ``"Contrary to common belief,"``,
   ``"Not"`` ...).  The remainder is parsed as a triple.
4. *Ordering hints* - ``"X requires Y"``, ``"X depends on Y"``,
   ``"before X, Y"`` -> ``OrderingHint(before=Y, after=X)``.

Stable ordering: concepts sorted by ``canonical_term``; relations and
counters by ``(head, relation, tail)``; ordering hints by ``(before, after)``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final

from formation.candidate import (
    ConceptCandidate,
    CounterCandidate,
    OrderingHint,
    RelationCandidate,
    SourceRef,
)
from formation.course import OreBundle
from teaching.relation_parse import _RELATIONS, parse_triple


@dataclass(frozen=True, slots=True)
class SmeltedBundle:
    """Output of the Smelter — candidates pending Forge validation."""

    concepts: tuple[ConceptCandidate, ...]
    relations: tuple[RelationCandidate, ...]
    counters: tuple[CounterCandidate, ...]
    ordering_hints: tuple[OrderingHint, ...]


_ADAPTER: Final[str] = "smelter/pattern_v1"

# Sentence splitter — keeps things deterministic without external NLP.
_SENTENCE_SPLIT = re.compile(r"(?<=[\.\?!])\s+")
_WS = re.compile(r"\s+")

# Concept definition patterns. Group 1 = canonical term, group 2 = definition.
_CONCEPT_PATTERNS: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(r"^\s*([a-z][a-z\- ]{0,40}?)\s+is\s+defined\s+as\s+(.+?)\s*$", re.IGNORECASE),
    re.compile(r"^\s*([a-z][a-z\- ]{0,40}?)\s+means\s+(.+?)\s*$", re.IGNORECASE),
    re.compile(r"^\s*([a-z][a-z\- ]{0,40}?)\s+is\s+an?\s+(.+?)\s*$", re.IGNORECASE),
)

# Negation markers — case-insensitive prefix match.
_COUNTER_MARKERS: Final[tuple[str, ...]] = (
    "it is a misconception that ",
    "it is a common misconception that ",
    "contrary to common belief, ",
    "contrary to popular belief, ",
    "contrary to belief, ",
    "it is not true that ",
    "not ",
)

# Ordering patterns. Each yields (after, before).
_ORDERING_PATTERNS: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(r"^\s*([a-z][a-z\- ]{0,40}?)\s+requires\s+([a-z][a-z\- ]{0,40}?)\s*$", re.IGNORECASE),
    re.compile(r"^\s*([a-z][a-z\- ]{0,40}?)\s+depends\s+on\s+([a-z][a-z\- ]{0,40}?)\s*$", re.IGNORECASE),
)
_ORDERING_BEFORE = re.compile(
    r"^\s*before\s+([a-z][a-z\- ]{0,40}?)\s*,\s*([a-z][a-z\- ]{0,40}?)\s*$",
    re.IGNORECASE,
)


def smelt(
    ore_bundle: OreBundle,
    source_texts: dict[str, str],
    retrieved_at: str,
) -> SmeltedBundle:
    """Extract candidate triples/concepts from ``source_texts``.

    ``source_texts`` maps ``source_sha`` to the full text body of the
    corresponding ``OreEntry``.  Sources absent from the map are skipped
    silently (they contribute no candidates).  ``retrieved_at`` is stamped
    on every emitted ``SourceRef``.
    """
    concepts_by_term: dict[str, _ConceptAccum] = {}
    relations_by_triple: dict[tuple[str, str, str], _TripleAccum] = {}
    counters_by_triple: dict[tuple[str, str, str], _TripleAccum] = {}
    orderings_by_pair: dict[tuple[str, str], _OrderingAccum] = {}

    # Iterate ore entries in their bundle order, but emit in sorted order
    # later.  Sources missing from ``source_texts`` are simply ignored.
    for entry in ore_bundle.entries:
        text = source_texts.get(entry.source_sha)
        if not text:
            continue
        for sentence in _split_sentences(text):
            if not sentence.strip():
                continue
            src = SourceRef(
                source_sha=entry.source_sha,
                span=sentence.strip(),
                adapter=_ADAPTER,
                retrieved_at=retrieved_at,
            )
            _extract_concepts(sentence, src, concepts_by_term)
            _extract_counters(sentence, src, counters_by_triple)
            _extract_ordering_hints(sentence, src, orderings_by_pair)
            _extract_relations(sentence, src, relations_by_triple)

    concepts = tuple(
        ConceptCandidate(
            canonical_term=term,
            definition=accum.definition,
            sources=accum.sources_tuple(),
        )
        for term, accum in sorted(concepts_by_term.items())
    )
    relations = tuple(
        RelationCandidate(
            head=key[0],
            relation=key[1],
            tail=key[2],
            sources=accum.sources_tuple(),
        )
        for key, accum in sorted(relations_by_triple.items())
    )
    counters = tuple(
        CounterCandidate(
            head=key[0],
            relation=key[1],
            tail=key[2],
            sources=accum.sources_tuple(),
        )
        for key, accum in sorted(counters_by_triple.items())
    )
    ordering_hints = tuple(
        OrderingHint(before=key[0], after=key[1], sources=accum.sources_tuple())
        for key, accum in sorted(orderings_by_pair.items())
    )
    return SmeltedBundle(
        concepts=concepts,
        relations=relations,
        counters=counters,
        ordering_hints=ordering_hints,
    )


# ---------- accumulators ----------


class _SourceSet:
    """Order-preserving, dedup-by-source-sha collector of SourceRefs."""

    __slots__ = ("_seen", "_refs")

    def __init__(self) -> None:
        self._seen: set[str] = set()
        self._refs: list[SourceRef] = []

    def add(self, src: SourceRef) -> None:
        if src.source_sha in self._seen:
            return
        self._seen.add(src.source_sha)
        self._refs.append(src)

    def sources_tuple(self) -> tuple[SourceRef, ...]:
        # Sort by source_sha for stable ordering across runs.
        return tuple(sorted(self._refs, key=lambda s: s.source_sha))


class _ConceptAccum(_SourceSet):
    __slots__ = ("definition",)

    def __init__(self, definition: str) -> None:
        super().__init__()
        self.definition = definition


class _TripleAccum(_SourceSet):
    __slots__ = ()


class _OrderingAccum(_SourceSet):
    __slots__ = ()


# ---------- helpers ----------


def _split_sentences(text: str) -> list[str]:
    # Normalize newlines to spaces before splitting so multi-line ore text
    # is handled identically to single-line text.
    flat = _WS.sub(" ", text.strip())
    if not flat:
        return []
    return _SENTENCE_SPLIT.split(flat)


def _clean_sentence(sentence: str) -> str:
    s = sentence.strip()
    while s and s[-1] in ".?!":
        s = s[:-1].rstrip()
    return s


def _valid_term(token: str) -> bool:
    """Canonical term: 1-3 alphabetic tokens, all lowercase after .lower()."""
    if not token:
        return False
    parts = token.split()
    if not 1 <= len(parts) <= 3:
        return False
    return all(re.fullmatch(r"[a-z][a-z\-]*", p) for p in parts)


def _extract_concepts(
    sentence: str,
    src: SourceRef,
    out: dict[str, _ConceptAccum],
) -> None:
    cleaned = _clean_sentence(sentence)
    if not cleaned:
        return
    for pattern in _CONCEPT_PATTERNS:
        match = pattern.match(cleaned)
        if match is None:
            continue
        term = match.group(1).strip().lower()
        definition = match.group(2).strip().lower()
        if not _valid_term(term):
            continue
        if not definition:
            continue
        accum = out.get(term)
        if accum is None:
            out[term] = accum = _ConceptAccum(definition=definition)
        accum.add(src)
        return  # First matching pattern wins.


def _extract_relations(
    sentence: str,
    src: SourceRef,
    out: dict[tuple[str, str, str], _TripleAccum],
) -> None:
    cleaned = _clean_sentence(sentence).lower()
    if not cleaned:
        return
    triple = parse_triple(cleaned)
    if triple is None:
        return
    head, relation, tail = triple
    if relation not in _RELATIONS:
        return
    key = (head, relation, tail)
    accum = out.get(key)
    if accum is None:
        out[key] = accum = _TripleAccum()
    accum.add(src)


def _extract_counters(
    sentence: str,
    src: SourceRef,
    out: dict[tuple[str, str, str], _TripleAccum],
) -> None:
    cleaned = _clean_sentence(sentence)
    if not cleaned:
        return
    lower = cleaned.lower()
    remainder: str | None = None
    for marker in _COUNTER_MARKERS:
        if lower.startswith(marker):
            remainder = cleaned[len(marker):].strip()
            break
    if remainder is None:
        return
    triple = parse_triple(remainder)
    if triple is None:
        return
    head, relation, tail = triple
    if relation not in _RELATIONS:
        return
    key = (head, relation, tail)
    accum = out.get(key)
    if accum is None:
        out[key] = accum = _TripleAccum()
    accum.add(src)


def _extract_ordering_hints(
    sentence: str,
    src: SourceRef,
    out: dict[tuple[str, str], _OrderingAccum],
) -> None:
    cleaned = _clean_sentence(sentence)
    if not cleaned:
        return

    before_match = _ORDERING_BEFORE.match(cleaned)
    if before_match is not None:
        after = before_match.group(1).strip().lower()
        before = before_match.group(2).strip().lower()
        _record_ordering(before, after, src, out)
        return

    for pattern in _ORDERING_PATTERNS:
        match = pattern.match(cleaned)
        if match is None:
            continue
        after = match.group(1).strip().lower()
        before = match.group(2).strip().lower()
        _record_ordering(before, after, src, out)
        return


def _record_ordering(
    before: str,
    after: str,
    src: SourceRef,
    out: dict[tuple[str, str], _OrderingAccum],
) -> None:
    if not _valid_term(before) or not _valid_term(after):
        return
    if before == after:
        return
    key = (before, after)
    accum = out.get(key)
    if accum is None:
        out[key] = accum = _OrderingAccum()
    accum.add(src)
