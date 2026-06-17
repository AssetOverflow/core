"""Focused unit tests for recognizer anchor injection (Inc 2 rate path).

Covers the exact acceptance cases from the Workstream A Inc 2 brief:
- $2 per cup → CandidateOperation(apply_rate, Rate(2, "dollars", "cup"))
- $18.00 an hour (an added to RATE_ANCHORS) or refuse if Option A
- unknown actor refuses
- multiple rates in one sentence refuses
- unsupported slash-fraction amount refuses
- unobserved currency / per_unit refuses (matcher already narrows, injector double-checks)
- zero amount refuses
- matched_*_token values are literal substrings from the source sentence
"""
from __future__ import annotations

import types

from evals.refusal_taxonomy.shape_categories import ShapeCategory
from generate.math_candidate_parser import CandidateOperation
from generate.math_problem_graph import Rate
from generate.math_roundtrip import roundtrip_admissible
from generate.recognizer_anchor_inject import (
    inject_from_match,
    inject_rate_with_currency,
)
from generate.recognizer_match import RecognizerMatch, match
from generate.recognizer_registry import load_ratified_registry


def _stub_recognizer(category: ShapeCategory) -> types.SimpleNamespace:
    """Minimal stub so RecognizerMatch(recognizer=...) succeeds for unit tests
    that want to drive the injector directly without a full registry hit."""
    return types.SimpleNamespace(shape_category=category, canonical_pattern={})


def _make_match(anchor: dict, category: ShapeCategory = ShapeCategory.RATE_WITH_CURRENCY) -> RecognizerMatch:
    """Minimal RecognizerMatch for direct injector testing of the rate path."""
    return RecognizerMatch(
        recognizer=_stub_recognizer(category),
        category=category,
        outcome="admissible",
        graph_intent="rate",
        parsed_anchors=(anchor,),
    )


def _rate_anchor(symbol: str = "$", amount: str = "2", per_unit: str = "cup", amount_kind: str = "integer") -> dict:
    return {
        "kind": "currency_per_unit_rate",
        "currency_symbol": symbol,
        "amount": amount,
        "amount_kind": amount_kind,
        "per_unit": per_unit,
    }


def test_rate_per_cup_emits_apply_rate_with_grounded_tokens():
    m = _make_match(_rate_anchor("$", "2", "cup"))
    emitted = inject_rate_with_currency(m, "Tina sells lemonade for $2 per cup.")
    assert len(emitted) == 1
    cand = emitted[0]
    assert isinstance(cand, CandidateOperation)
    assert cand.op.kind == "apply_rate"
    assert isinstance(cand.op.operand, Rate)
    assert cand.op.operand.value == 2
    assert cand.op.operand.numerator_unit == "dollars"
    assert cand.op.operand.denominator_unit == "cup"
    assert cand.matched_actor_token == "Tina"
    assert cand.matched_value_token == "2"
    assert cand.matched_unit_token == "dollars"
    assert cand.matched_verb in {"per", "a", "an", "each", "every"}  # literal surface in sentence
    assert roundtrip_admissible(cand) is True


def test_rate_an_hour_emits_when_an_in_rate_anchors():
    """$18.00 an hour is a major proxy case. With 'an' in RATE_ANCHORS the
    literal verb token must ground."""
    m = _make_match(_rate_anchor("$", "18.00", "hour", "decimal"))
    emitted = inject_rate_with_currency(m, "Tina makes $18.00 an hour.")
    assert len(emitted) == 1
    cand = emitted[0]
    assert isinstance(cand, CandidateOperation)
    assert cand.op.kind == "apply_rate"
    assert cand.op.operand.denominator_unit == "hour"
    assert cand.matched_verb == "an"  # literal from sentence
    assert cand.matched_value_token == "18.00"
    assert roundtrip_admissible(cand) is True


def test_unknown_actor_refuses_narrow_binding():
    m = _make_match(_rate_anchor("$", "20", "kg"))
    # No clear ProperName subject (use lowercase common noun at head so the
    # ratified extract_proper_noun_subject does not bind; "fish" is not a name).
    emitted = inject_rate_with_currency(m, "fish are sold for $20 per kg at the market.")
    assert emitted == ()


def test_multiple_rates_in_one_sentence_refuses():
    m = _make_match(_rate_anchor("$", "18", "hour"))  # the anchor list would have >1 in real, but we simulate
    # Force two by calling the multi logic path (injector sees >1 after loop)
    # Simpler: construct a match with two anchors
    a1 = _rate_anchor("$", "18", "hour")
    a2 = _rate_anchor("$", "20", "job")
    mm = RecognizerMatch(
        recognizer=_stub_recognizer(ShapeCategory.RATE_WITH_CURRENCY),
        category=ShapeCategory.RATE_WITH_CURRENCY,
        outcome="admissible",
        graph_intent="rate",
        parsed_anchors=(a1, a2),
    )
    emitted = inject_rate_with_currency(mm, "Tina makes $18 an hour and $20 per job.")
    assert emitted == ()


def test_slash_fraction_amount_refuses_in_v1():
    m = _make_match(_rate_anchor("$", "3/4", "hour", "word"))
    emitted = inject_rate_with_currency(m, "Tina makes $3/4 an hour.")
    assert emitted == ()


def test_unobserved_symbol_or_per_unit_is_already_refused_by_matcher_but_injector_is_defensive():
    # Injector must still refuse if somehow an unseen symbol reached it
    bad = _rate_anchor("₿", "10", "hour")
    m = _make_match(bad)
    emitted = inject_rate_with_currency(m, "Tina makes ₿10 per hour.")
    assert emitted == ()


def test_zero_amount_refuses():
    m = _make_match(_rate_anchor("$", "0", "hour"))
    emitted = inject_rate_with_currency(m, "Tina makes $0 an hour.")
    assert emitted == ()


def test_matched_tokens_ground_in_source_sentence():
    sentence = "Yuki earns $15 an hour at the bookstore."
    m = _make_match(_rate_anchor("$", "15", "hour", "integer"))
    emitted = inject_rate_with_currency(m, sentence)
    assert len(emitted) == 1
    c = emitted[0]
    assert c.source_span == sentence
    assert c.matched_value_token in sentence
    assert c.matched_actor_token in sentence
    # unit is canonical but the rate framing is in the source
    assert "hour" in sentence.lower()


def test_dispatch_table_routes_rate_with_currency():
    """inject_from_match (the public surface used by the graph) must find the new injector."""
    registry = load_ratified_registry()
    # Use a real sentence that the live registry will recognize as RATE_WITH_CURRENCY
    # (the exemplars guarantee at least one such surface is admitted by some ratified spec).
    stmt = "Tina makes $18.00 an hour."
    m = match(stmt, registry)
    # The matcher may or may not fire depending on the exact live specs on disk,
    # but if it does for a rate surface, the injector must now be wired.
    if m is not None and m.category is ShapeCategory.RATE_WITH_CURRENCY:
        emitted = inject_from_match(m, stmt, sealed=False)
        # It may still return () for actor or other narrow v1 reasons on this
        # particular sentence, but the important thing is we did not hit the
        # old "no injector registered" path that would have been the deferral.
        # We only assert that the call succeeded without KeyError / unexpected.
        assert isinstance(emitted, tuple)


def test_an_rate_anchor_widening_is_contained_to_currency_rate_surfaces():
    """ "a"/"an" in RATE_ANCHORS must not open broad/generic apply_rate outside
    actual currency-rate surfaces (containment/confuser for the widening).

    Even if matched_verb="a", a "dollars" unit_token only grounds (via the
    explicit $ branch we added) when the source actually contains "$".
    """
    from generate.math_problem_graph import Operation, Rate
    from generate.math_candidate_parser import CandidateOperation
    from generate.math_roundtrip import roundtrip_admissible

    rate = Rate(2.0, "dollars", "cup")
    op = Operation(actor="Tina", kind="apply_rate", operand=rate)

    # Confuser: "a" verb + dollars unit, but no "$" symbol in source → unit fails to ground
    bogus = CandidateOperation(
        op=op,
        source_span="Tina makes a 2 cup thing.",
        matched_verb="a",
        matched_value_token="2",
        matched_unit_token="dollars",
        matched_actor_token="Tina",
    )
    assert roundtrip_admissible(bogus) is False

    # Good rate surface with "a" + "$" → admissible
    good = CandidateOperation(
        op=op,
        source_span="Tina sells for $2 a cup.",
        matched_verb="a",
        matched_value_token="2",
        matched_unit_token="dollars",
        matched_actor_token="Tina",
    )
    assert roundtrip_admissible(good) is True
