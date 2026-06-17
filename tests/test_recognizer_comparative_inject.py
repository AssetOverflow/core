"""Gate A1 — comparative_with_unit recognizer-anchor injection tests.

Mirrors the Inc2 rate injector ladder: unit confusers, live-registry dispatch,
half/quarter/third serving proof, and DCS yield for comparative surfaces.
"""

from __future__ import annotations

import types

import pytest

from evals.refusal_taxonomy.shape_categories import ShapeCategory
from generate.math_candidate_graph import parse_and_solve
from generate.math_candidate_parser import CandidateOperation
from generate.math_problem_graph import Comparison
from generate.math_roundtrip import roundtrip_admissible
from generate.recognizer_anchor_inject import (
    inject_comparative_multiplicative,
    inject_from_match,
)
from generate.recognizer_match import RecognizerMatch, match
from generate.recognizer_registry import load_ratified_registry


def _stub_recognizer(category: ShapeCategory) -> types.SimpleNamespace:
    return types.SimpleNamespace(shape_category=category, canonical_pattern={})


def _make_match(anchor: dict) -> RecognizerMatch:
    return RecognizerMatch(
        recognizer=_stub_recognizer(ShapeCategory.COMPARATIVE_WITH_UNIT),
        category=ShapeCategory.COMPARATIVE_WITH_UNIT,
        outcome="admissible",
        graph_intent="compare",
        parsed_anchors=(anchor,),
    )


def _anchor(
    *,
    actor: str = "Alice",
    reference: str = "Bob",
    unit: str = "apples",
    factor_token: str = "twice",
    factor: float = 2.0,
    direction: str = "times",
    matched_verb: str = "twice",
) -> dict:
    return {
        "kind": "comparative_multiplicative",
        "actor_token": actor,
        "reference_actor_token": reference,
        "unit_token": unit,
        "factor_token": factor_token,
        "factor": factor,
        "direction": direction,
        "matched_verb": matched_verb,
        "comparator_phrase": f"{factor_token} as many {unit}",
    }


@pytest.mark.parametrize(
    "sentence,actor,reference,unit,factor_token,factor,direction,matched_verb",
    [
        ("Alice has twice as many apples as Bob.", "Alice", "Bob", "apples", "twice", 2.0, "times", "twice"),
        ("Jerry has thrice as many apples as Tom.", "Jerry", "Tom", "apples", "thrice", 3.0, "times", "thrice"),
        ("Dana has 4 times as many pencils as Eli.", "Dana", "Eli", "pencils", "4", 4.0, "times", "times"),
        ("Alice has half as many apples as Bob.", "Alice", "Bob", "apples", "half", 0.5, "fraction", "half"),
        ("Alice has a quarter as many apples as Bob.", "Alice", "Bob", "apples", "quarter", 0.25, "fraction", "quarter"),
        ("Alice has a third as many apples as Bob.", "Alice", "Bob", "apples", "third", 1.0 / 3.0, "fraction", "third"),
    ],
)
def test_positive_surfaces_emit_compare_multiplicative(
    sentence, actor, reference, unit, factor_token, factor, direction, matched_verb
):
    emitted = inject_comparative_multiplicative(_make_match(_anchor(
        actor=actor,
        reference=reference,
        unit=unit,
        factor_token=factor_token,
        factor=factor,
        direction=direction,
        matched_verb=matched_verb,
    )), sentence)
    assert len(emitted) == 1
    cand = emitted[0]
    assert isinstance(cand, CandidateOperation)
    assert cand.op.kind == "compare_multiplicative"
    assert isinstance(cand.op.operand, Comparison)
    assert cand.op.operand.factor == factor
    assert cand.op.operand.direction == direction
    assert cand.matched_value_token == factor_token
    assert cand.matched_verb == matched_verb
    assert roundtrip_admissible(cand) is True


@pytest.mark.parametrize(
    "sentence",
    [
        "Jerry has 3 times as many apples.",
        "Jerry has twice as many apples.",
        "Jerry has 3 times more apples than Bob.",
        "Alice has 3 more apples than Bob.",
        "He has twice as many apples as Bob.",
        "Alice lost twice as many apples as Bob.",
        "Alice has one-third as many apples as Bob.",
        "Alice has double as many apples as Bob.",
        "Jerry has 3 times",
        "Alice has $2 times as many apples as Bob.",
        "Alice has 3/4 times as many apples as Bob.",
        "Alice has some times as many apples as Bob.",
        "Alice has twenty-five times as many apples as Bob.",
    ],
)
def test_confuser_surfaces_refuse_injection(sentence: str):
    registry = load_ratified_registry()
    m = match(sentence, registry)
    if m is None:
        return
    assert inject_from_match(m, sentence, sealed=False) == ()


@pytest.mark.parametrize(
    "sentence",
    [
        "Alice has $2 times as many apples as Bob.",
        "Alice has 3/4 times as many apples as Bob.",
        "Alice has some times as many apples as Bob.",
        "Alice has twenty-five times as many apples as Bob.",
    ],
)
def test_ntimes_factor_confusers_do_not_match_comparative(sentence: str):
    registry = load_ratified_registry()
    m = match(sentence, registry)
    assert m is None or m.category is not ShapeCategory.COMPARATIVE_WITH_UNIT


@pytest.mark.parametrize(
    "text",
    [
        "Jerry has 3 times as many apples. How many apples does Jerry have?",
        "Alice has $2 times as many apples as Bob. How many apples does Alice have?",
        "Alice has 3 more apples than Bob. How many apples does Alice have?",
    ],
)
def test_graph_confusers_refuse_without_compare_lift(text: str):
    res = parse_and_solve(text, sealed=False)
    assert res.answer is None
    assert res.refusal_reason is not None


def test_unknown_actor_refuses():
    emitted = inject_comparative_multiplicative(
        _make_match(_anchor(actor="fish")),
        "fish have twice as many apples as Bob.",
    )
    assert emitted == ()


def test_dispatch_table_routes_comparative_with_unit():
    registry = load_ratified_registry()
    stmt = "Alice has twice as many apples as Bob."
    m = match(stmt, registry)
    assert m is not None
    assert m.category is ShapeCategory.COMPARATIVE_WITH_UNIT
    emitted = inject_from_match(m, stmt, sealed=False)
    assert len(emitted) == 1
    assert roundtrip_admissible(emitted[0]) is True


def test_dcs_yields_comparative_not_initial_times():
    registry = load_ratified_registry()
    stmt = "Jerry has 3 times as many apples as Tom."
    m = match(stmt, registry)
    assert m is not None
    assert m.category is ShapeCategory.COMPARATIVE_WITH_UNIT
    emitted = inject_from_match(m, stmt, sealed=False)
    assert len(emitted) == 1
    assert emitted[0].op.kind == "compare_multiplicative"


def test_matched_tokens_ground_in_source_sentence():
    sentence = "Nina studied three times as many pages as Omar."
    registry = load_ratified_registry()
    m = match(sentence, registry)
    assert m is not None
    emitted = inject_from_match(m, sentence, sealed=False)
    assert len(emitted) == 1
    c = emitted[0]
    assert c.matched_actor_token in sentence
    assert c.matched_reference_actor_token in sentence
    assert c.matched_unit_token in sentence
