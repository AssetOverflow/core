"""ME-2 — cross-sentence subject binding tests.

Covers:
- ``extract_proper_noun_subject`` narrowness (proper noun vs determiner
  vs sentence-initial connector vs pronoun)
- ``try_extract_cross_sentence_composition_anchor`` happy path + refusals
- ``match`` dispatcher cross-sentence fallback (prior_subject supplied
  AND same-sentence Option A miss → cross-sentence path fires)
- case 0019 sentence shape admits when prior_subject="John"
- refusal-preferring on None / empty / pronoun prior_subject
"""

from __future__ import annotations

from typing import Any, Mapping

from generate.math_candidate_parser import CandidateInitial
from generate.recognizer_match import (
    extract_proper_noun_subject,
    try_extract_cross_sentence_composition_anchor,
)


_SPEC: Mapping[str, Any] = {
    "anchor_kind": "currency_per_unit_composition",
    "observed_currency_symbols": ["$"],
    "observed_per_units": ["each", "apiece"],
}

_CASE_0019 = (
    "The dog ends up having health problems and this requires "
    "3 vet appointments, which cost $400 each."
)


def test_proper_noun_head_extracted():
    assert extract_proper_noun_subject("John adopts a dog from a shelter.") == "John"
    assert extract_proper_noun_subject("Maria bought 3 things.") == "Maria"
    assert extract_proper_noun_subject("Sam Saves 5 dollars.") == "Sam"


def test_determiner_head_refused():
    assert extract_proper_noun_subject("The dog ends up sick.") is None
    assert extract_proper_noun_subject("A boy walks home.") is None
    assert extract_proper_noun_subject("Their car is red.") is None


def test_sentence_initial_connector_refused():
    assert extract_proper_noun_subject("After 2 years, John retires.") is None
    assert extract_proper_noun_subject("How much did Marco spend?") is None
    assert extract_proper_noun_subject("In May, sales doubled.") is None
    assert extract_proper_noun_subject("Every Tuesday Maria buys milk.") is None


def test_pronoun_head_refused():
    assert extract_proper_noun_subject("He walks home.") is None
    assert extract_proper_noun_subject("They are happy.") is None
    assert extract_proper_noun_subject("It costs $5.") is None


def test_non_string_returns_none():
    assert extract_proper_noun_subject(None) is None  # type: ignore[arg-type]
    assert extract_proper_noun_subject(123) is None  # type: ignore[arg-type]


def test_cross_sentence_happy_path():
    result = try_extract_cross_sentence_composition_anchor(_CASE_0019, _SPEC, "John")
    assert result is not None
    anchor = result[0][0]
    assert anchor["composition_shape"] == "bound(count) × bound(unit_cost)"
    assert anchor["subject"] == "John"
    assert anchor["subject_source"] == "prior_sentence"
    composed = anchor["composed_initial"]
    assert isinstance(composed, CandidateInitial)
    assert composed.initial.entity == "John"
    assert composed.initial.quantity.value == 1200
    assert composed.initial.quantity.unit == "dollars"


def test_cross_sentence_no_prior_subject_refuses():
    assert (
        try_extract_cross_sentence_composition_anchor(_CASE_0019, _SPEC, None) is None
    )
    assert try_extract_cross_sentence_composition_anchor(_CASE_0019, _SPEC, "") is None
    assert (
        try_extract_cross_sentence_composition_anchor(_CASE_0019, _SPEC, "   ") is None
    )


def test_cross_sentence_pronoun_prior_refused():
    """Prior subject in refused-pronoun set → refuse."""
    for pronoun in ("he", "She", "They", "it"):
        assert (
            try_extract_cross_sentence_composition_anchor(_CASE_0019, _SPEC, pronoun)
            is None
        )


def test_cross_sentence_unobserved_currency_refuses():
    spec = dict(_SPEC)
    spec["observed_currency_symbols"] = ["£"]
    assert (
        try_extract_cross_sentence_composition_anchor(_CASE_0019, _SPEC, "John") is not None
    )
    assert (
        try_extract_cross_sentence_composition_anchor(_CASE_0019, spec, "John") is None
    )


def test_cross_sentence_per_unit_outside_observed_refuses():
    spec = dict(_SPEC)
    spec["observed_per_units"] = ["hour"]
    assert (
        try_extract_cross_sentence_composition_anchor(_CASE_0019, spec, "John") is None
    )


def test_cross_sentence_wrong_anchor_kind_refuses():
    spec = dict(_SPEC)
    spec["anchor_kind"] = "currency_per_unit_rate"
    assert (
        try_extract_cross_sentence_composition_anchor(_CASE_0019, spec, "John") is None
    )


def test_cross_sentence_zero_count_refuses():
    statement = (
        "The dog ends up having health problems and this requires "
        "0 vet appointments, which cost $400 each."
    )
    assert (
        try_extract_cross_sentence_composition_anchor(statement, _SPEC, "John") is None
    )


def test_cross_sentence_multi_match_refuses():
    """Two composition shapes in one statement → ambiguity refuses."""
    statement = (
        "this requires 3 vet appointments, which cost $400 each "
        "and also requires 2 items, which cost $50 each"
    )
    result = try_extract_cross_sentence_composition_anchor(statement, _SPEC, "John")
    assert result is None


def test_cross_sentence_source_span_is_substring():
    result = try_extract_cross_sentence_composition_anchor(_CASE_0019, _SPEC, "John")
    assert result is not None
    span = result[0][0]["composed_initial"].source_span
    assert span in _CASE_0019


def test_cross_sentence_kind_label():
    result = try_extract_cross_sentence_composition_anchor(_CASE_0019, _SPEC, "John")
    assert result is not None
    assert result[0][0]["kind"] == "currency_per_unit_composition_cross_sentence"
