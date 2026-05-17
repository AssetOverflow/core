"""Tests for ``formation.smelter`` — deterministic, pattern-based extraction.

The Smelter turns raw text spans into candidate objects suitable for the
Forge.  It is pure regex/string ops: no LLM, no network, no async, no floats
in emitted dataclasses, and emitted tuples are sorted for stable ordering.
"""

from __future__ import annotations

import pytest

from formation import (
    ConceptCandidate,
    CounterCandidate,
    OrderingHint,
    OreBundle,
    RelationCandidate,
    SourceRef,
    canonical_json,
)
from formation.course import OreEntry
from formation.smelter import SmeltedBundle, smelt


_SHA_A = "a" * 64
_SHA_B = "b" * 64
_RETRIEVED = "2026-05-16T00:00:00Z"


def _bundle(*shas: str) -> OreBundle:
    return OreBundle(
        subject_id="test",
        entries=tuple(
            OreEntry(
                source_sha=sha,
                url=f"https://example.test/{sha[:6]}",
                adapter="smelter/pattern_v1",
                retrieved_at=_RETRIEVED,
                byte_length=0,
            )
            for sha in shas
        ),
    )


@pytest.mark.unit
def test_single_concept_definition_produces_one_candidate() -> None:
    text = "Wisdom is defined as practical judgment."
    out = smelt(_bundle(_SHA_A), {_SHA_A: text}, _RETRIEVED)
    assert isinstance(out, SmeltedBundle)
    assert len(out.concepts) == 1
    concept = out.concepts[0]
    assert isinstance(concept, ConceptCandidate)
    assert concept.canonical_term == "wisdom"
    assert "practical judgment" in concept.definition
    assert len(concept.sources) == 1
    assert concept.sources[0].source_sha == _SHA_A
    assert concept.sources[0].adapter == "smelter/pattern_v1"


@pytest.mark.unit
def test_repeated_canonical_term_collapses_to_one_concept() -> None:
    text = (
        "Wisdom is defined as practical judgment. "
        "Wisdom means knowing what is good. "
        "Wisdom is a virtue."
    )
    out = smelt(_bundle(_SHA_A), {_SHA_A: text}, _RETRIEVED)
    terms = [c.canonical_term for c in out.concepts]
    assert terms.count("wisdom") == 1
    concept = out.concepts[0]
    assert len(concept.sources) >= 1


@pytest.mark.unit
def test_relation_roundtrips_through_parse_triple() -> None:
    from teaching.relation_parse import parse_triple

    text = "Wisdom is judgment. Glargle floob bloop."
    out = smelt(_bundle(_SHA_A), {_SHA_A: text}, _RETRIEVED)
    for rel in out.relations:
        assert isinstance(rel, RelationCandidate)
        parsed = parse_triple(f"{rel.head} {rel.relation} {rel.tail}")
        assert parsed is not None
    # At least one relation extracted (wisdom is judgment).
    assert any(r.head == "wisdom" and r.tail == "judgment" for r in out.relations)


@pytest.mark.unit
def test_counter_sentence_produces_counter_candidate() -> None:
    text = "It is a misconception that the earth is flat."
    out = smelt(_bundle(_SHA_A), {_SHA_A: text}, _RETRIEVED)
    assert len(out.counters) == 1
    counter = out.counters[0]
    assert isinstance(counter, CounterCandidate)
    assert counter.head == "earth"
    assert counter.relation == "is"
    assert counter.tail == "flat"


@pytest.mark.unit
def test_ordering_hint_from_requires() -> None:
    text = "Calculus requires algebra."
    out = smelt(_bundle(_SHA_A), {_SHA_A: text}, _RETRIEVED)
    assert len(out.ordering_hints) == 1
    hint = out.ordering_hints[0]
    assert isinstance(hint, OrderingHint)
    assert hint.before == "algebra"
    assert hint.after == "calculus"


@pytest.mark.unit
def test_ordering_hint_from_depends_on() -> None:
    text = "Geometry depends on logic."
    out = smelt(_bundle(_SHA_A), {_SHA_A: text}, _RETRIEVED)
    assert any(h.before == "logic" and h.after == "geometry" for h in out.ordering_hints)


@pytest.mark.unit
def test_ordering_hint_from_before() -> None:
    text = "Before calculus, algebra."
    out = smelt(_bundle(_SHA_A), {_SHA_A: text}, _RETRIEVED)
    assert any(h.before == "algebra" and h.after == "calculus" for h in out.ordering_hints)


@pytest.mark.unit
def test_determinism_byte_identical_canonical_json() -> None:
    text = (
        "Wisdom is defined as practical judgment. "
        "Calculus requires algebra. "
        "It is a misconception that the earth is flat. "
        "Wisdom is judgment."
    )
    out1 = smelt(_bundle(_SHA_A), {_SHA_A: text}, _RETRIEVED)
    out2 = smelt(_bundle(_SHA_A), {_SHA_A: text}, _RETRIEVED)
    payload1 = _to_dict(out1)
    payload2 = _to_dict(out2)
    assert canonical_json(payload1) == canonical_json(payload2)


@pytest.mark.unit
def test_empty_source_text_yields_empty_bundle() -> None:
    out = smelt(_bundle(_SHA_A), {_SHA_A: ""}, _RETRIEVED)
    assert out.concepts == ()
    assert out.relations == ()
    assert out.counters == ()
    assert out.ordering_hints == ()


@pytest.mark.unit
def test_no_source_texts_at_all() -> None:
    out = smelt(_bundle(), {}, _RETRIEVED)
    assert out.concepts == ()
    assert out.relations == ()


@pytest.mark.unit
def test_same_triple_from_two_sources_dedups_with_two_refs() -> None:
    text_a = "Wisdom is judgment."
    text_b = "Wisdom is judgment."
    out = smelt(
        _bundle(_SHA_A, _SHA_B),
        {_SHA_A: text_a, _SHA_B: text_b},
        _RETRIEVED,
    )
    rels = [r for r in out.relations if r.head == "wisdom" and r.tail == "judgment"]
    assert len(rels) == 1
    rel = rels[0]
    shas = {s.source_sha for s in rel.sources}
    assert shas == {_SHA_A, _SHA_B}


@pytest.mark.unit
def test_stable_ordering_of_emitted_tuples() -> None:
    text = (
        "Zebra is defined as a striped horse. "
        "Apple is defined as a fruit. "
        "Mango is defined as a fruit."
    )
    out = smelt(_bundle(_SHA_A), {_SHA_A: text}, _RETRIEVED)
    terms = [c.canonical_term for c in out.concepts]
    assert terms == sorted(terms)


def _to_dict(b: SmeltedBundle) -> dict:
    def _src(s: SourceRef) -> dict:
        return {
            "source_sha": s.source_sha,
            "span": s.span,
            "adapter": s.adapter,
            "retrieved_at": s.retrieved_at,
        }

    return {
        "concepts": [
            {
                "canonical_term": c.canonical_term,
                "definition": c.definition,
                "sources": [_src(s) for s in c.sources],
            }
            for c in b.concepts
        ],
        "relations": [
            {
                "head": r.head,
                "relation": r.relation,
                "tail": r.tail,
                "sources": [_src(s) for s in r.sources],
            }
            for r in b.relations
        ],
        "counters": [
            {
                "head": c.head,
                "relation": c.relation,
                "tail": c.tail,
                "sources": [_src(s) for s in c.sources],
            }
            for c in b.counters
        ],
        "ordering_hints": [
            {
                "before": h.before,
                "after": h.after,
                "sources": [_src(s) for s in h.sources],
            }
            for h in b.ordering_hints
        ],
    }
