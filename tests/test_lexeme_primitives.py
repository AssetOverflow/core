"""Tests for generate.comprehension.lexeme_primitives (ADR-0164.1)."""

from __future__ import annotations

import re

import pytest

from generate.comprehension.lexeme_primitives import (
    PRIMITIVE_REGISTRY,
    LexemeMatch,
    LexemePrimitive,
    scan,
)


# ---------------------------------------------------------------------------
# Construction invariants
# ---------------------------------------------------------------------------

class TestRegistryConstruction:
    def test_has_eight_primitives(self) -> None:
        assert len(PRIMITIVE_REGISTRY) == 8

    def test_sorted_by_priority_ascending(self) -> None:
        priorities = [p.priority for p in PRIMITIVE_REGISTRY]
        assert priorities == sorted(priorities)

    def test_names_are_unique(self) -> None:
        names = [p.name for p in PRIMITIVE_REGISTRY]
        assert len(names) == len(set(names))

    def test_all_patterns_compile(self) -> None:
        for p in PRIMITIVE_REGISTRY:
            assert isinstance(p.pattern, re.Pattern), f"{p.name}: pattern not compiled"

    def test_all_priorities_non_negative(self) -> None:
        for p in PRIMITIVE_REGISTRY:
            assert p.priority >= 0, f"{p.name}: negative priority"

    def test_all_fields_populated(self) -> None:
        for p in PRIMITIVE_REGISTRY:
            assert p.name, f"empty name: {p!r}"
            assert p.emits, f"{p.name}: empty emits"
            assert p.provenance, f"{p.name}: empty provenance"
            # extracts may be empty tuple only for primitives with no capture groups
            assert isinstance(p.extracts, tuple)

    def test_all_names_kebab_case(self) -> None:
        for p in PRIMITIVE_REGISTRY:
            assert "_" not in p.name, f"{p.name}: use hyphens, not underscores"

    def test_emits_valid_enum(self) -> None:
        valid = {"QUANTITY", "ORDINAL", "UNIT_CATEGORY_TOKEN"}
        for p in PRIMITIVE_REGISTRY:
            assert p.emits in valid, f"{p.name}: unknown emits={p.emits!r}"

    def test_primitive_is_immutable(self) -> None:
        p = PRIMITIVE_REGISTRY[0]
        with pytest.raises((AttributeError, TypeError)):
            p.name = "tampered"  # type: ignore[misc]

    def test_registry_is_tuple(self) -> None:
        assert isinstance(PRIMITIVE_REGISTRY, tuple)


# ---------------------------------------------------------------------------
# Canonical fires — each primitive matches its canonical example
# ---------------------------------------------------------------------------

class TestCanonicalFires:
    def test_decimal_currency_literal(self) -> None:
        m = scan("$18.00")
        assert m is not None
        assert m.primitive_name == "decimal-currency-literal"
        assert m.emit_category == "QUANTITY"
        assert m.extracted_values["whole"] == "18"
        assert m.extracted_values["cents"] == "00"
        assert m.extracted_values["unit_class"] == "currency"

    def test_currency_literal(self) -> None:
        m = scan("$18")
        assert m is not None
        assert m.primitive_name == "currency-literal"
        assert m.emit_category == "QUANTITY"
        assert m.extracted_values["value"] == "18"
        assert m.extracted_values["unit_class"] == "currency"

    def test_currency_literal_decimal(self) -> None:
        m = scan("$1.5")
        assert m is not None
        assert m.primitive_name == "currency-literal"
        assert m.extracted_values["value"] == "1.5"

    def test_percentage_literal(self) -> None:
        m = scan("25%")
        assert m is not None
        assert m.primitive_name == "percentage-literal"
        assert m.emit_category == "QUANTITY"
        assert m.extracted_values["value"] == "25"
        assert m.extracted_values["unit_class"] == "ratio"

    def test_fraction_literal(self) -> None:
        m = scan("1/2")
        assert m is not None
        assert m.primitive_name == "fraction-literal"
        assert m.emit_category == "QUANTITY"
        assert m.extracted_values["numerator"] == "1"
        assert m.extracted_values["denominator"] == "2"
        assert m.extracted_values["unit_class"] == "fraction"

    def test_time_amount_literal(self) -> None:
        m = scan("3hours")
        assert m is not None
        assert m.primitive_name == "time-amount-literal"
        assert m.emit_category == "QUANTITY"
        assert m.extracted_values["value"] == "3"
        assert m.extracted_values["unit"] == "hour"
        assert m.extracted_values["unit_class"] == "time"

    def test_time_amount_literal_with_space(self) -> None:
        m = scan("3 hours")
        assert m is not None
        assert m.primitive_name == "time-amount-literal"
        assert m.extracted_values["value"] == "3"
        assert m.extracted_values["unit"] == "hour"

    def test_ordinal_literal(self) -> None:
        m = scan("first")
        assert m is not None
        assert m.primitive_name == "ordinal-literal"
        assert m.emit_category == "ORDINAL"
        assert m.extracted_values["rank"] == "1"

    def test_ordinal_literal_second(self) -> None:
        m = scan("second")
        assert m is not None
        assert m.extracted_values["rank"] == "2"

    def test_ordinal_literal_tenth(self) -> None:
        m = scan("tenth")
        assert m is not None
        assert m.extracted_values["rank"] == "10"

    def test_mass_noun_token(self) -> None:
        m = scan("money")
        assert m is not None
        assert m.primitive_name == "mass-noun-token"
        assert m.emit_category == "UNIT_CATEGORY_TOKEN"
        assert m.extracted_values["lemma"] == "money"
        assert m.extracted_values["unit_class"] == "currency-mass"

    def test_numeric_literal(self) -> None:
        m = scan("18")
        assert m is not None
        assert m.primitive_name == "numeric-literal"
        assert m.emit_category == "QUANTITY"
        assert m.extracted_values["value"] == "18"
        assert m.extracted_values["unit_class"] == "pending"


# ---------------------------------------------------------------------------
# Overlap precedence (ADR-0164.1 §Overlap precedence)
# ---------------------------------------------------------------------------

class TestOverlapPrecedence:
    def test_dollar_18_00_decimal_currency_wins_over_currency(self) -> None:
        m = scan("$18.00")
        assert m is not None
        assert m.primitive_name == "decimal-currency-literal", (
            f"expected decimal-currency-literal, got {m.primitive_name}"
        )

    def test_dollar_18_currency_wins_over_numeric(self) -> None:
        m = scan("$18")
        assert m is not None
        assert m.primitive_name == "currency-literal"

    def test_dollar_18_00_not_numeric(self) -> None:
        m = scan("$18.00")
        assert m is not None
        assert m.primitive_name != "numeric-literal"

    def test_fraction_wins_over_numeric(self) -> None:
        m = scan("1/2")
        assert m is not None
        assert m.primitive_name == "fraction-literal"

    def test_percentage_wins_over_numeric(self) -> None:
        m = scan("50%")
        assert m is not None
        assert m.primitive_name == "percentage-literal"

    def test_25_percent_not_numeric(self) -> None:
        m = scan("25%")
        assert m is not None
        assert m.primitive_name != "numeric-literal"


# ---------------------------------------------------------------------------
# Refusal — scan returns None when no primitive matches
# ---------------------------------------------------------------------------

class TestRefusal:
    def test_proper_noun_entity(self) -> None:
        assert scan("Tina") is None

    def test_empty_string(self) -> None:
        assert scan("") is None

    def test_plain_verb(self) -> None:
        assert scan("earn") is None

    def test_question_word(self) -> None:
        assert scan("how") is None

    def test_article(self) -> None:
        assert scan("the") is None

    def test_preposition(self) -> None:
        assert scan("for") is None


# ---------------------------------------------------------------------------
# Determinism — identical inputs produce byte-equal results
# ---------------------------------------------------------------------------

class TestDeterminism:
    @pytest.mark.parametrize("token", [
        "$18.00", "$18", "25%", "1/2", "3hours", "first", "money", "18",
    ])
    def test_byte_equal_on_repeat(self, token: str) -> None:
        a = scan(token)
        b = scan(token)
        assert a == b

    def test_none_is_none(self) -> None:
        assert scan("Tina") == scan("Tina")

    def test_lexeme_match_eq_semantics(self) -> None:
        a = scan("$18.00")
        b = scan("$18.00")
        assert a is not None and b is not None
        assert a == b
        # LexemeMatch is frozen dataclass — equality is field-wise
        assert a.primitive_name == b.primitive_name
        assert a.emit_category == b.emit_category
        assert dict(a.extracted_values) == dict(b.extracted_values)
        assert a.source_text == b.source_text
        assert a.source_span == b.source_span


# ---------------------------------------------------------------------------
# ADR-0165 compliance — no primitive pattern contains \s (whitespace class)
# ---------------------------------------------------------------------------

class TestADR0165Compliance:
    def test_no_multi_whitespace_in_patterns(self) -> None:
        # ADR-0165 forbids \s+ grammar-template patterns. Single \s? is explicitly
        # sanctioned in ADR-0164.1 §Seed primitive set for percentage-literal,
        # fraction-literal, and time-amount-literal (single optional space within
        # one orthographic form — not a cross-token span).
        for p in PRIMITIVE_REGISTRY:
            src = p.pattern.pattern
            assert r"\s+" not in src, (
                f"{p.name}: pattern contains \\s+ — multi-whitespace spans cross "
                f"token boundaries (ADR-0165 §Rule). Pattern: {src!r}"
            )

    def test_no_star_wildcard_spanning_patterns(self) -> None:
        for p in PRIMITIVE_REGISTRY:
            src = p.pattern.pattern
            assert r".*" not in src, (
                f"{p.name}: pattern contains .* — forbidden grammar-template indicator"
            )


# ---------------------------------------------------------------------------
# extracted_values sorted-key stability (canonical bytes)
# ---------------------------------------------------------------------------

class TestExtractedValuesSortedKeys:
    @pytest.mark.parametrize("token", [
        "$18.00", "$18", "25%", "1/2", "3hours", "first", "money", "18",
    ])
    def test_keys_are_sorted(self, token: str) -> None:
        m = scan(token)
        assert m is not None
        keys = list(m.extracted_values.keys())
        assert keys == sorted(keys), f"keys not sorted for token {token!r}: {keys}"

    def test_extracted_values_immutable(self) -> None:
        m = scan("$18.00")
        assert m is not None
        with pytest.raises((TypeError, AttributeError)):
            m.extracted_values["tampered"] = "x"  # type: ignore[index]
