"""ADR-0163 Phase D — recognizer_match tests.

Pins:
- per-category match: positive hits, negative misses
- narrowness: out-of-corpus surfaces return None
- parsed_anchors carry real extracted values for admissible categories
- parsed_anchors is empty for descriptive_setup_no_quantity
- determinism: same (statement, registry) -> same result
- module-import no-LLM-no-ML test (mirror Phase A/C)
"""

from __future__ import annotations

from pathlib import Path

import pytest

from evals.refusal_taxonomy.shape_categories import ShapeCategory
from generate.recognizer_match import RecognizerMatch, match
from generate.recognizer_registry import RatifiedRecognizer
from tests._phase_d_fixture import build_synthetic_registry


@pytest.fixture(scope="module")
def registry() -> tuple[RatifiedRecognizer, ...]:
    return build_synthetic_registry()


# ---------------------------------------------------------------------------
# Positive matches per category
# ---------------------------------------------------------------------------


def test_rate_with_currency_matches_canonical_surface(
    registry: tuple[RatifiedRecognizer, ...],
) -> None:
    m = match("Tina makes $18.00 an hour.", registry)
    assert m is not None
    assert m.category is ShapeCategory.RATE_WITH_CURRENCY
    assert m.outcome == "admissible"
    assert m.graph_intent == "rate"
    assert len(m.parsed_anchors) == 1
    a = m.parsed_anchors[0]
    assert a["currency_symbol"] == "$"
    assert a["amount"] == "18.00"
    assert a["per_unit"] == "hour"
    assert a["amount_kind"] == "decimal"


def test_rate_with_currency_matches_for_one_surface(
    registry: tuple[RatifiedRecognizer, ...],
) -> None:
    m = match("She sells lemonade for $2 for one cup.", registry)
    assert m is not None
    assert m.category is ShapeCategory.RATE_WITH_CURRENCY
    assert m.parsed_anchors[0]["per_unit"] == "cup"
    assert m.parsed_anchors[0]["amount"] == "2"
    assert m.parsed_anchors[0]["amount_kind"] == "integer"


def test_temporal_aggregation_matches_each_day(
    registry: tuple[RatifiedRecognizer, ...],
) -> None:
    m = match(
        "Allison uploads 10 videos each day to her channel.",
        registry,
    )
    assert m is not None
    assert m.category is ShapeCategory.TEMPORAL_AGGREGATION
    assert m.graph_intent == "aggregate"
    assert m.parsed_anchors[0]["window_unit"] == "day"
    assert m.parsed_anchors[0]["window_quantifier"] == "each"


def test_descriptive_setup_no_quantity_matches_setup(
    registry: tuple[RatifiedRecognizer, ...],
) -> None:
    m = match("Marnie makes bead bracelets.", registry)
    assert m is not None
    assert m.category is ShapeCategory.DESCRIPTIVE_SETUP_NO_QUANTITY
    assert m.outcome == "inadmissible_by_design"
    assert m.parsed_anchors == ()


# ---------------------------------------------------------------------------
# Narrowness — out-of-corpus surfaces must NOT match
# ---------------------------------------------------------------------------


def test_rate_with_currency_rejects_unseen_currency_bitcoin(
    registry: tuple[RatifiedRecognizer, ...],
) -> None:
    """Bitcoin sign ₿ is outside the spec's observed currency set."""
    # Verify ₿ not in observed; if it is (it isn't in current Phase B
    # corpora), fall back to any non-USD/non-GBP/non-EUR/non-JPY symbol.
    m = match("She earns ₿10 per hour.", registry)
    assert m is None or m.category is not ShapeCategory.RATE_WITH_CURRENCY


def test_temporal_aggregation_rejects_unseen_window_unit(
    registry: tuple[RatifiedRecognizer, ...],
) -> None:
    """The Phase B seeds observe a subset of window units; the matcher
    refuses statements with units outside that subset."""
    rate_recognizer = next(
        r for r in registry if r.shape_category is ShapeCategory.TEMPORAL_AGGREGATION
    )
    observed = set(rate_recognizer.canonical_pattern["observed_window_units"])
    all_units = {"day", "week", "month", "year", "hour", "minute", "second"}
    unseen = sorted(all_units - observed)
    if not unseen:
        pytest.skip("Phase B corpus already covers full window vocabulary")
    fake_unit = unseen[0]
    # Use 5 here so it can't collide with descriptive's no-quantity rule.
    m = match(f"She does 5 things each {fake_unit}.", registry)
    assert m is None or m.category is not ShapeCategory.TEMPORAL_AGGREGATION


def test_descriptive_setup_rejects_statement_with_digit(
    registry: tuple[RatifiedRecognizer, ...],
) -> None:
    """A statement carrying a digit cannot be admitted as
    descriptive_setup_no_quantity — that category's spec pins
    quantity_anchor_count=0.  Some OTHER recognizer may match
    (rate/temporal), but not descriptive."""
    m = match("Sally has 5 apples.", registry)
    if m is not None:
        assert m.category is not ShapeCategory.DESCRIPTIVE_SETUP_NO_QUANTITY


# ---------------------------------------------------------------------------
# WRONG-COUNT SAFETY — at least one negative case per category proving
# the matcher does NOT mis-admit a math-load-bearing surface that the
# Phase C synthesizer's gate would otherwise reject (ADR-0163 §The
# Load-Bearing Judgment Call).
# ---------------------------------------------------------------------------


def test_rate_with_currency_does_not_match_currency_without_per_unit(
    registry: tuple[RatifiedRecognizer, ...],
) -> None:
    """'She paid $5' carries currency but no per-unit framing — not a
    rate, must NOT match.  Mis-admitting it would lose the
    distinction between amount and rate downstream."""
    m = match("She paid $5 for the book.", registry)
    assert m is None or m.category is not ShapeCategory.RATE_WITH_CURRENCY


def test_temporal_aggregation_does_not_match_single_day_token(
    registry: tuple[RatifiedRecognizer, ...],
) -> None:
    """A single day-of-week token without enumeration must not trip
    day-windowed aggregation.  This was a Phase B author_note edge
    case ('Saturdays present but not enumerated')."""
    m = match("On Saturday she went to the store.", registry)
    assert m is None or m.category is not ShapeCategory.TEMPORAL_AGGREGATION


def test_descriptive_setup_does_not_match_indefinite_quantity(
    registry: tuple[RatifiedRecognizer, ...],
) -> None:
    """'There are some kids in camp' carries an indefinite quantifier
    — Phase A categorizes it as indefinite_quantity, NOT
    descriptive_setup_no_quantity.  The matcher must respect that
    distinction."""
    m = match("There are some kids in camp.", registry)
    assert m is None or m.category is not ShapeCategory.DESCRIPTIVE_SETUP_NO_QUANTITY


# ---------------------------------------------------------------------------
# Determinism + purity
# ---------------------------------------------------------------------------


def test_match_is_deterministic(
    registry: tuple[RatifiedRecognizer, ...],
) -> None:
    statement = "Tina makes $18.00 an hour."
    a = match(statement, registry)
    b = match(statement, registry)
    assert a is not None and b is not None
    assert a.category is b.category
    assert a.parsed_anchors == b.parsed_anchors


def test_match_returns_none_for_empty_registry() -> None:
    assert match("Tina makes $18.00 an hour.", ()) is None


def test_match_returns_none_for_empty_statement(
    registry: tuple[RatifiedRecognizer, ...],
) -> None:
    assert match("", registry) is None
    assert match("   ", registry) is None


def test_module_imports_no_llm_or_ml() -> None:
    """Phase A/C/D matchers are rules-only."""
    import generate.recognizer_match as m
    module_file = m.__file__
    assert module_file is not None
    src = Path(module_file).read_text(encoding="utf-8")
    for forbidden in (
        "transformers", "torch", "tensorflow", "openai",
        "anthropic", "sklearn", "numpy.random",
    ):
        assert forbidden not in src, (
            f"forbidden import {forbidden!r} in recognizer_match.py"
        )


_TYPE_USED = RecognizerMatch  # exported public type — silence unused import
