"""Gate A2a — unit_partition recognizer-anchor injection tests."""

from __future__ import annotations

import types

import pytest

from evals.refusal_taxonomy.shape_categories import ShapeCategory
from generate.math_candidate_parser import CandidateOperation
from generate.math_problem_graph import PartitionChunk
from generate.math_roundtrip import roundtrip_admissible
from generate.recognizer_anchor_inject import inject_from_match, inject_unit_partition
from generate.recognizer_match import RecognizerMatch, match
from generate.recognizer_registry import load_ratified_registry


def _stub_recognizer(category: ShapeCategory) -> types.SimpleNamespace:
    return types.SimpleNamespace(shape_category=category, canonical_pattern={})


def _make_match(anchor: dict) -> RecognizerMatch:
    return RecognizerMatch(
        recognizer=_stub_recognizer(ShapeCategory.UNIT_PARTITION),
        category=ShapeCategory.UNIT_PARTITION,
        outcome="admissible",
        graph_intent="partition",
        parsed_anchors=(anchor,),
    )


def _anchor(
    *,
    actor: str = "Jan",
    chunk_size: str = "25",
    chunk_unit: str = "foot",
    counted_noun: str = "sections",
    verb: str = "splits",
) -> dict:
    return {
        "kind": "unit_partition",
        "actor_token": actor,
        "chunk_size_token": chunk_size,
        "chunk_unit_token": chunk_unit,
        "counted_noun_token": counted_noun,
        "partition_verb_token": verb,
        "source_span": f"{actor} {verb} it into {chunk_size}-{chunk_unit} {counted_noun}.",
    }


@pytest.mark.parametrize(
    "sentence,actor,chunk_size,chunk_unit,counted_noun,verb",
    [
        ("She splits it up into 25-foot sections.", "She", "25", "foot", "sections", "splits"),
        ("Dana cuts the ribbon into 20-inch pieces.", "Dana", "20", "inch", "pieces", "cuts"),
        ("Jan cuts the rope into 4-foot sections.", "Jan", "4", "foot", "sections", "cuts"),
        ("Mason splits the cable into 10-meter sections.", "Mason", "10", "meter", "sections", "splits"),
    ],
)
def test_positive_surfaces_emit_unit_partition(
    sentence, actor, chunk_size, chunk_unit, counted_noun, verb
):
    registry = load_ratified_registry()
    m = match(sentence, registry)
    assert m is not None
    assert m.category is ShapeCategory.UNIT_PARTITION
    emitted = inject_from_match(m, sentence, sealed=False)
    assert len(emitted) == 1
    cand = emitted[0]
    assert isinstance(cand, CandidateOperation)
    assert cand.op.kind == "unit_partition"
    assert isinstance(cand.op.operand, PartitionChunk)
    assert cand.op.operand.value == float(chunk_size)
    assert cand.matched_value_token == chunk_size
    assert cand.matched_verb == verb
    assert roundtrip_admissible(cand) is True


@pytest.mark.parametrize(
    "sentence",
    [
        "25-foot sections.",
        "She splits it into 25 sections.",
        "It is a 2-hour drive.",
        "Jan cuts the rope into 3-foot sections and 4-foot sections.",
        "She splits it into equal sections.",
        "She splits it into bags.",
        "Half of the kids go to soccer camp.",
        "She puts 48 cookies into boxes of 6.",
        "999 feet split into 25-foot sections.",
    ],
)
def test_unit_partition_confusers_never_inject(sentence: str):
    registry = load_ratified_registry()
    m = match(sentence, registry)
    if m is None:
        return
    assert inject_from_match(m, sentence, sealed=False) == ()


@pytest.mark.parametrize(
    "sentence",
    [
        "Jan buys 1000 feet of cable.",
        "Tina makes $18.00 an hour.",
        "Alice has twice as many apples as Bob.",
        "Bob can shuck 10 oysters in 5 minutes.",
    ],
)
def test_legitimate_unrelated_surfaces_do_not_emit_unit_partition(sentence: str):
    registry = load_ratified_registry()
    m = match(sentence, registry)
    if m is None:
        return
    emitted = inject_from_match(m, sentence, sealed=False)
    for candidate in emitted:
        if isinstance(candidate, CandidateOperation):
            assert candidate.op.kind != "unit_partition"


def test_pronoun_anchor_emits_with_resolution_flag():
    registry = load_ratified_registry()
    stmt = "She splits it up into 25-foot sections."
    m = match(stmt, registry)
    assert m is not None
    assert m.parsed_anchors[0].get("requires_pronoun_resolution") is True
    emitted = inject_from_match(m, stmt, sealed=False)
    assert len(emitted) == 1


def test_dispatch_table_routes_unit_partition():
    registry = load_ratified_registry()
    stmt = "Jan cuts the rope into 4-foot sections."
    m = match(stmt, registry)
    assert m is not None
    assert m.category is ShapeCategory.UNIT_PARTITION
    emitted = inject_from_match(m, stmt, sealed=False)
    assert len(emitted) == 1
    assert emitted[0].op.operand.result_unit == "sections"


def test_dcs_yields_unit_partition_not_initial_chunk_size():
    registry = load_ratified_registry()
    stmt = "She splits it up into 25-foot sections."
    m = match(stmt, registry)
    assert m is not None
    assert m.category is ShapeCategory.UNIT_PARTITION
    emitted = inject_from_match(m, stmt, sealed=False)
    assert len(emitted) == 1
    assert emitted[0].op.kind == "unit_partition"


def test_direct_injector_refuses_malformed_anchor():
    emitted = inject_unit_partition(
        _make_match(_anchor(chunk_size="two")),
        "Jan splits it into two-foot sections.",
    )
    assert emitted == ()


def test_matched_tokens_ground_in_source_sentence():
    sentence = "Dana cuts the ribbon into 20-inch pieces."
    registry = load_ratified_registry()
    m = match(sentence, registry)
    assert m is not None
    emitted = inject_from_match(m, sentence, sealed=False)
    assert len(emitted) == 1
    c = emitted[0]
    assert c.matched_actor_token in sentence
    assert c.matched_value_token in sentence
    assert c.matched_unit_token in sentence
