"""ADR-0128 sub-phase 0128.1 — number-format regex corpora.

Each format rule has ≥10 positive + ≥10 negative cases. Ambiguous
strings (e.g., ``1.000`` — could be ``1`` or ``1000``) are refused via
``match_number_format`` returning ``None`` when multiple rules match.
The "wrong == 0" invariant is preserved by never guessing.
"""
from __future__ import annotations

from fractions import Fraction

import pytest

from language_packs.numerics_loader import match_number_format


# ---------------------------------------------------------------------------
# thousand_separated  —  e.g.,  1,000   12,345
# ---------------------------------------------------------------------------
THOUSAND_SEP_POS = [
    ("1,000", 1000), ("10,000", 10_000), ("100,000", 100_000),
    ("1,000,000", 1_000_000), ("12,345", 12_345), ("999,999", 999_999),
    ("1,234,567", 1_234_567), ("23,000", 23_000), ("5,000", 5_000),
    ("987,654,321", 987_654_321),
]
THOUSAND_SEP_NEG = [
    "1000",       # no separator
    "1,00",       # malformed group
    "1,0000",     # malformed group
    "1,000.5",    # extra suffix
    "1,000,",     # trailing comma
    ",1,000",     # leading comma
    "abc",        # non-numeric
    "1,000a",     # trailing letter
    "1.000",      # decimal not separator (per current locale rule)
    "1, 000",     # space inside
]


@pytest.mark.parametrize("raw,expected", THOUSAND_SEP_POS)
def test_thousand_separated_positive(raw, expected):
    parsed = match_number_format(raw)
    assert parsed is not None and parsed.format_id == "thousand_separated"
    assert parsed.value == expected


@pytest.mark.parametrize("raw", THOUSAND_SEP_NEG)
def test_thousand_separated_negative(raw):
    parsed = match_number_format(raw)
    if parsed is not None:
        assert parsed.format_id != "thousand_separated"


# ---------------------------------------------------------------------------
# decimal — 1.5, 3.14, 0.25, -0.5
# ---------------------------------------------------------------------------
DECIMAL_POS = [
    ("1.5", 1.5), ("3.14", 3.14), ("0.25", 0.25), ("100.001", 100.001),
    ("-0.5", -0.5), ("-1.25", -1.25), ("10.0", 10.0), ("0.0", 0.0),
    ("999.999", 999.999), ("1.0001", 1.0001),
]
DECIMAL_NEG = [
    "1",          # no fractional part
    ".5",         # no leading digit
    "1.",         # trailing dot
    "1.5.0",      # two dots
    "1,5",        # wrong separator
    "abc.def",    # non-numeric
    "1e5",        # scientific
    "1.5%",       # percentage, different format
    "1/2",        # slash form
    "--1.5",      # double minus
]


@pytest.mark.parametrize("raw,expected", DECIMAL_POS)
def test_decimal_positive(raw, expected):
    parsed = match_number_format(raw)
    assert parsed is not None and parsed.format_id == "decimal"
    assert parsed.value == pytest.approx(expected)


@pytest.mark.parametrize("raw", DECIMAL_NEG)
def test_decimal_negative(raw):
    parsed = match_number_format(raw)
    if parsed is not None:
        assert parsed.format_id != "decimal"


# ---------------------------------------------------------------------------
# slash_fraction — 1/2, 3/4, 7/8
# ---------------------------------------------------------------------------
SLASH_POS = [
    ("1/2", Fraction(1, 2)), ("3/4", Fraction(3, 4)), ("7/8", Fraction(7, 8)),
    ("5/6", Fraction(5, 6)), ("1/3", Fraction(1, 3)), ("2/3", Fraction(2, 3)),
    ("11/16", Fraction(11, 16)), ("100/101", Fraction(100, 101)),
    ("9/10", Fraction(9, 10)), ("-1/2", Fraction(-1, 2)),
]
SLASH_NEG = [
    "1/0",          # zero denominator — parser refuses
    "1/",           # malformed
    "/2",           # malformed
    "1 / 2",        # spaces around slash
    "1.5/2",        # decimal numerator
    "1/2/3",        # double slash
    "abc/def",      # non-numeric
    "1//2",         # double slash
    "1\\2",         # wrong slash
    "1 1/2",        # mixed number — different format
]


@pytest.mark.parametrize("raw,expected", SLASH_POS)
def test_slash_fraction_positive(raw, expected):
    parsed = match_number_format(raw)
    assert parsed is not None and parsed.format_id == "slash_fraction"
    assert parsed.value == expected


@pytest.mark.parametrize("raw", SLASH_NEG)
def test_slash_fraction_negative(raw):
    parsed = match_number_format(raw)
    if parsed is not None:
        assert parsed.format_id != "slash_fraction"


# ---------------------------------------------------------------------------
# mixed_number — 1 1/2, 2 3/4
# ---------------------------------------------------------------------------
MIXED_POS = [
    ("1 1/2", Fraction(3, 2)), ("2 3/4", Fraction(11, 4)),
    ("3 1/3", Fraction(10, 3)), ("5 7/8", Fraction(47, 8)),
    ("10 1/4", Fraction(41, 4)), ("0 1/2", Fraction(1, 2)),
    ("100 1/100", Fraction(10001, 100)), ("1 9/10", Fraction(19, 10)),
    ("4 5/6", Fraction(29, 6)), ("-1 1/2", Fraction(-3, 2)),
]
MIXED_NEG = [
    "1/2",          # bare fraction, no whole part
    "1  1/2",       # double space
    "1.5 1/2",      # decimal whole
    "1 1.5",        # decimal fraction
    "1 1/0",        # zero denom — refused at parse
    "1 -1/2",       # internal sign
    "abc 1/2",      # non-numeric
    "1 1 / 2",      # spaces in fraction part
    "1",            # whole only
    "one 1/2",      # word number
]


@pytest.mark.parametrize("raw,expected", MIXED_POS)
def test_mixed_number_positive(raw, expected):
    parsed = match_number_format(raw)
    assert parsed is not None and parsed.format_id == "mixed_number"
    assert parsed.value == expected


@pytest.mark.parametrize("raw", MIXED_NEG)
def test_mixed_number_negative(raw):
    parsed = match_number_format(raw)
    if parsed is not None:
        assert parsed.format_id != "mixed_number"


# ---------------------------------------------------------------------------
# percentage — 75%, 1.5%, 100%
# ---------------------------------------------------------------------------
PERCENT_POS = [
    ("75%", 0.75), ("1.5%", 0.015), ("100%", 1.0), ("0%", 0.0),
    ("50%", 0.5), ("99.9%", 0.999), ("12.5%", 0.125), ("200%", 2.0),
    ("0.5%", 0.005), ("-25%", -0.25),
]
PERCENT_NEG = [
    "75",           # no percent sign
    "%75",          # leading percent
    "75 %",         # space before percent
    "75%%",         # double percent
    "abc%",         # non-numeric
    "1.5.0%",       # bad decimal
    "75/100",       # different format
    "75.%",         # trailing dot before percent
    ".5%",          # no leading digit
    "1,000%",       # separator inside percent
]


@pytest.mark.parametrize("raw,expected", PERCENT_POS)
def test_percentage_positive(raw, expected):
    parsed = match_number_format(raw)
    assert parsed is not None and parsed.format_id == "percentage"
    assert parsed.value == pytest.approx(expected)


@pytest.mark.parametrize("raw", PERCENT_NEG)
def test_percentage_negative(raw):
    parsed = match_number_format(raw)
    if parsed is not None:
        assert parsed.format_id != "percentage"


# ---------------------------------------------------------------------------
# signed_integer — -3, 42, -0
# ---------------------------------------------------------------------------
SIGNED_INT_POS = [
    ("0", 0), ("1", 1), ("42", 42), ("-3", -3), ("-1", -1),
    ("100", 100), ("999", 999), ("-999", -999), ("7", 7), ("-7", -7),
]
SIGNED_INT_NEG = [
    "1.5",          # decimal — owned by decimal rule
    "1,000",        # owned by thousand_separated
    "1/2",          # owned by slash_fraction
    "1 1/2",        # owned by mixed_number
    "75%",          # owned by percentage
    "abc",          # non-numeric
    "--3",          # double minus
    "+3",           # leading plus — out of spec
    "3a",           # trailing letter
    " 3",           # leading space
]


@pytest.mark.parametrize("raw,expected", SIGNED_INT_POS)
def test_signed_integer_positive(raw, expected):
    parsed = match_number_format(raw)
    assert parsed is not None and parsed.format_id == "signed_integer"
    assert parsed.value == expected


@pytest.mark.parametrize("raw", SIGNED_INT_NEG)
def test_signed_integer_negative(raw):
    parsed = match_number_format(raw)
    if parsed is not None:
        assert parsed.format_id != "signed_integer"


# ---------------------------------------------------------------------------
# Ambiguity refusal — preserves wrong == 0
# ---------------------------------------------------------------------------
def test_empty_string_refused():
    assert match_number_format("") is None


def test_pure_text_refused():
    assert match_number_format("seventeen") is None


def test_zero_denominator_slash_refused():
    # Regex matches, but parser raises ZeroDivisionError → None
    assert match_number_format("1/0") is None


def test_zero_denominator_mixed_refused():
    assert match_number_format("1 1/0") is None
