"""ADR-0128 sub-phase 0128.2 — loader API + compound composition.

Covers the public lookup surface plus the deterministic compound rules
(cardinal composition, compound-fraction composition, article-bound
fraction forms, case-insensitivity)."""
from __future__ import annotations

import pytest

from language_packs.numerics_loader import (
    lookup_cardinal,
    lookup_comparison_anchor,
    lookup_comparison_anchors,
    lookup_fraction,
    lookup_multiplier,
    lookup_ordinal,
    lookup_quantifier,
    parse_compound_cardinal,
)


# ---------------------------------------------------------------------------
# Cardinal lookup + compound composition
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("word,value", [
    ("zero", 0), ("seven", 7), ("seventeen", 17), ("twenty", 20),
    ("fifty", 50), ("ninety", 90), ("hundred", 100), ("thousand", 1000),
    ("million", 1_000_000),
])
def test_lookup_cardinal_simple(word, value):
    entry = lookup_cardinal(word)
    assert entry is not None and entry.numeric_value == value


def test_lookup_cardinal_case_insensitive():
    assert lookup_cardinal("Seventeen").numeric_value == 17
    assert lookup_cardinal("SEVENTEEN").numeric_value == 17


def test_lookup_cardinal_unknown_returns_none():
    assert lookup_cardinal("seventeenish") is None
    assert lookup_cardinal("") is None


@pytest.mark.parametrize("text,expected", [
    ("twenty-one", 21),
    ("twenty one", 21),
    ("ninety-nine", 99),
    ("one hundred", 100),
    ("two hundred", 200),
    ("two hundred and fifty", 250),
    ("three hundred and seventeen", 317),
    ("one thousand", 1000),
    ("two thousand five hundred", 2500),
    ("two thousand five hundred and seventeen", 2517),
    ("seventeen", 17),
    ("fifty", 50),
    ("thirty-two", 32),
    ("one million", 1_000_000),
])
def test_parse_compound_cardinal(text, expected):
    assert parse_compound_cardinal(text) == expected


def test_parse_compound_cardinal_rejects_unknown_token():
    assert parse_compound_cardinal("twenty banana") is None
    assert parse_compound_cardinal("") is None
    assert parse_compound_cardinal("    ") is None


# ---------------------------------------------------------------------------
# Ordinal lookup
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("word,pos", [
    ("first", 1), ("second", 2), ("third", 3), ("tenth", 10),
    ("twelfth", 12), ("twentieth", 20), ("twenty-first", 21),
    ("thirty-first", 31), ("hundredth", 100),
])
def test_lookup_ordinal(word, pos):
    entry = lookup_ordinal(word)
    assert entry is not None and entry.position == pos


def test_lookup_ordinal_case_insensitive():
    assert lookup_ordinal("First").position == 1


# ---------------------------------------------------------------------------
# Fraction lookup + compound + article-bound
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("token,num,den", [
    ("half", 1, 2),
    ("a half", 1, 2),
    ("third", 1, 3),
    ("a third", 1, 3),
    ("quarter", 1, 4),
    ("the quarter", 1, 4),
    ("sixteenth", 1, 16),
    ("thirty-second", 1, 32),
])
def test_lookup_fraction_named_and_article_bound(token, num, den):
    entry = lookup_fraction(token)
    assert entry is not None
    assert entry.numerator == num and entry.denominator == den


@pytest.mark.parametrize("token,num,den", [
    ("two-thirds", 2, 3),
    ("two thirds", 2, 3),
    ("three-quarters", 3, 4),
    ("three quarters", 3, 4),
    ("three-fourths", 3, 4),  # American "fourths" alias
    ("five eighths", 5, 8),
    ("seven tenths", 7, 10),
    ("nine sixteenths", 9, 16),
])
def test_lookup_fraction_compound(token, num, den):
    entry = lookup_fraction(token)
    assert entry is not None
    assert entry.numerator == num and entry.denominator == den
    assert entry.decimal_value == pytest.approx(num / den)


@pytest.mark.parametrize("symbol,num,den", [
    ("½", 1, 2), ("¼", 1, 4), ("¾", 3, 4),
    ("⅓", 1, 3), ("⅔", 2, 3), ("⅛", 1, 8),
    ("⅜", 3, 8), ("⅝", 5, 8), ("⅞", 7, 8),
])
def test_lookup_fraction_symbol(symbol, num, den):
    entry = lookup_fraction(symbol)
    assert entry is not None
    assert entry.numerator == num and entry.denominator == den


def test_lookup_fraction_unknown_returns_none():
    assert lookup_fraction("zillionth") is None
    assert lookup_fraction("") is None


# ---------------------------------------------------------------------------
# Multipliers
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("word,factor", [
    ("double", 2.0), ("triple", 3.0), ("quadruple", 4.0),
    ("quintuple", 5.0), ("twice", 2.0), ("thrice", 3.0), ("half", 0.5),
])
def test_lookup_multiplier(word, factor):
    entry = lookup_multiplier(word)
    assert entry is not None and entry.factor == factor


# ---------------------------------------------------------------------------
# Quantifiers
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("word,sem_type,det", [
    ("all", "total", None),
    ("none", "empty", 0),
    ("some", "indefinite", None),
    ("both", "paired", 2),
    ("each", "distributive", None),
    ("every", "distributive", None),
    ("many", "indefinite", None),
    ("few", "indefinite", None),
    ("several", "indefinite", None),
    ("most", "partial", None),
    ("any", "indefinite", None),
    ("no", "empty", 0),
    ("single", "total", 1),
])
def test_lookup_quantifier(word, sem_type, det):
    entry = lookup_quantifier(word)
    assert entry is not None
    assert entry.semantic_type == sem_type
    assert entry.determinate_value == det


def test_indefinite_quantifier_triggers_refusal_signal():
    # The loader doesn't refuse on its own — it surfaces the signal that
    # the parser will use to refuse. Test the signal is correctly tagged.
    assert lookup_quantifier("some").is_indefinite is True
    assert lookup_quantifier("all").is_indefinite is False


# ---------------------------------------------------------------------------
# Comparison anchors
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("word,anchor_class", [
    ("more", "additive"), ("fewer", "additive"), ("less", "additive"),
    ("additional", "additive"), ("extra", "additive"),
    ("missing", "additive"), ("remaining", "additive"),
    ("times", "multiplicative"), ("thrice", "multiplicative"),
    ("quadruple", "multiplicative"),
])
def test_lookup_comparison_anchor_single(word, anchor_class):
    entry = lookup_comparison_anchor(word)
    assert entry is not None and entry.anchor_class == anchor_class


def test_comparison_anchor_dual_class_for_half():
    # 'half' / 'double' / 'twice' / 'triple' / 'third' / 'quarter' are
    # multiplicative anchors but may also exist as multipliers/fractions.
    # The comparison-anchor table puts them in multiplicative.
    anchors = lookup_comparison_anchors("half")
    assert any(a.anchor_class == "multiplicative" for a in anchors)


def test_comparison_anchor_unknown_returns_none():
    assert lookup_comparison_anchor("zonk") is None
    assert lookup_comparison_anchors("zonk") == ()
