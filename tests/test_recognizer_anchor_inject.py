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


def _make_match(
    anchor: dict, category: ShapeCategory = ShapeCategory.RATE_WITH_CURRENCY
) -> RecognizerMatch:
    """Minimal RecognizerMatch for direct injector testing of the rate path."""
    return RecognizerMatch(
        recognizer=_stub_recognizer(category),
        category=category,
        outcome="admissible",
        graph_intent="rate",
        parsed_anchors=(anchor,),
    )


def _rate_anchor(
    symbol: str = "$",
    amount: str = "2",
    per_unit: str = "cup",
    amount_kind: str = "integer",
    rate_anchor_token: str = "per",
) -> dict:
    return {
        "kind": "currency_per_unit_rate",
        "currency_symbol": symbol,
        "amount": amount,
        "amount_kind": amount_kind,
        "per_unit": per_unit,
        "rate_anchor_token": rate_anchor_token,
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
    assert cand.matched_verb in {
        "per",
        "a",
        "an",
        "each",
        "every",
    }  # literal surface in sentence
    assert roundtrip_admissible(cand) is True


def test_rate_an_hour_emits_when_an_in_rate_anchors():
    """$18.00 an hour is a major proxy case. With 'an' in RATE_ANCHORS the
    literal verb token must ground."""
    m = _make_match(
        _rate_anchor("$", "18.00", "hour", "decimal", rate_anchor_token="an")
    )
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
    emitted = inject_rate_with_currency(
        m, "fish are sold for $20 per kg at the market."
    )
    assert emitted == ()


def test_multiple_rates_in_one_sentence_refuses():
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
    m = _make_match(_rate_anchor("$", "3/4", "hour", "word", rate_anchor_token="an"))
    emitted = inject_rate_with_currency(m, "Tina makes $3/4 an hour.")
    assert emitted == ()


def test_unobserved_symbol_or_per_unit_is_already_refused_by_matcher_but_injector_is_defensive():
    # Injector must still refuse if somehow an unseen symbol reached it
    bad = _rate_anchor("₿", "10", "hour")
    m = _make_match(bad)
    emitted = inject_rate_with_currency(m, "Tina makes ₿10 per hour.")
    assert emitted == ()


def test_zero_amount_refuses():
    m = _make_match(_rate_anchor("$", "0", "hour", rate_anchor_token="an"))
    emitted = inject_rate_with_currency(m, "Tina makes $0 an hour.")
    assert emitted == ()


def test_matched_tokens_ground_in_source_sentence():
    sentence = "Yuki earns $15 an hour at the bookstore."
    m = _make_match(_rate_anchor("$", "15", "hour", "integer", rate_anchor_token="an"))
    emitted = inject_rate_with_currency(m, sentence)
    assert len(emitted) == 1
    c = emitted[0]
    assert c.source_span == sentence
    assert c.matched_value_token in sentence
    assert c.matched_actor_token in sentence
    # unit is canonical but the rate framing is in the source
    assert "hour" in sentence.lower()


def test_dispatch_table_routes_rate_with_currency():
    """The public dispatch (live registry + inject_from_match(sealed=False))
    must emit a non-empty, roundtrip-admissible CandidateOperation for a
    canonical rate surface. This proves the serving path is wired, not just
    the direct unit tests.
    """
    registry = load_ratified_registry()
    stmt = "Tina makes $18.00 an hour."
    m = match(stmt, registry)
    assert m is not None
    assert m.category is ShapeCategory.RATE_WITH_CURRENCY
    emitted = inject_from_match(m, stmt, sealed=False)
    assert len(emitted) == 1
    from generate.math_roundtrip import roundtrip_admissible

    assert roundtrip_admissible(emitted[0]) is True


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


def test_rate_anchor_token_from_matcher_not_whole_sentence_scan():
    """The connector used for matched_verb must come from the rate surface match
    in the anchor (provided by the updated _CURRENCY_AMOUNT_RE), not from a
    global sentence scan that could pick an unrelated article "a" earlier in
    the text (e.g. "a lemonade stand").

    Uses a real registry match + public inject_from_match path on a sentence
    that has a distracting "a" before the actual rate "$2 per cup".
    Must unconditionally emit exactly one admissible candidate using "per".
    """
    registry = load_ratified_registry()
    stmt = "Alexa has a lemonade stand where she sells lemonade for $2 per cup."
    m = match(stmt, registry)
    assert m is not None
    assert m.category is ShapeCategory.RATE_WITH_CURRENCY
    emitted = inject_from_match(m, stmt, sealed=False)
    assert len(emitted) == 1
    from generate.math_roundtrip import roundtrip_admissible

    cand = emitted[0]
    assert isinstance(cand, CandidateOperation)
    assert cand.op.kind == "apply_rate"
    assert cand.matched_verb == "per"
    assert roundtrip_admissible(cand) is True


def test_rate_for_one_cup_emits_apply_rate_with_matched_verb_one():
    """Positive coverage for Inc3 "for one cup" connector support (rate_with_currency).

    "Alexa has a lemonade stand where she sells lemonade for $2 for one cup."
    The live registry matches as RATE_WITH_CURRENCY.
    rate_anchor_token == "one" (from the "for one X" group) is now allowed.
    Injector must emit exactly one CandidateOperation with matched_verb="one",
    using the rate surface (not falling back to earlier "a" from "a lemonade stand").
    roundtrip_admissible must hold. This makes the rate no-injection bucket
    actionable (downstream refusal for missing denom state, not injector ()).
    """
    registry = load_ratified_registry()
    stmt = "Alexa has a lemonade stand where she sells lemonade for $2 for one cup."
    m = match(stmt, registry)
    assert m is not None
    assert m.category is ShapeCategory.RATE_WITH_CURRENCY
    emitted = inject_from_match(m, stmt, sealed=False)
    assert len(emitted) == 1
    from generate.math_roundtrip import roundtrip_admissible

    cand = emitted[0]
    assert isinstance(cand, CandidateOperation)
    assert cand.op.kind == "apply_rate"
    assert cand.matched_verb == "one"
    assert cand.matched_actor_token == "Alexa"
    assert roundtrip_admissible(cand) is True
    # Explicitly no fallback to the distracting earlier "a"
    assert "one" in stmt.lower()  # the token came from the rate span
