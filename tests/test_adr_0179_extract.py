"""ADR-0179 extraction richness tests."""

from __future__ import annotations

from generate.derivation import extract_quantities


class TestEX3MultiWordUnits:
    def test_multi_word_unit_extracts_full_span(self) -> None:
        quantities = extract_quantities("The log has 12 jumping jacks.")

        assert [(q.value, q.unit, q.source_token) for q in quantities] == [
            (12.0, "jumping jacks", "12"),
        ]

    def test_lowercase_unit_span_can_include_multiple_words(self) -> None:
        quantities = extract_quantities("The set has 5 practice math problems.")

        assert [(q.value, q.unit, q.source_token) for q in quantities] == [
            (5.0, "practice math problems", "5"),
        ]

    def test_single_word_quantity_extraction_still_works(self) -> None:
        quantities = extract_quantities("The set has 6 apples.")

        assert [(q.value, q.unit, q.source_token) for q in quantities] == [
            (6.0, "apples", "6"),
        ]
