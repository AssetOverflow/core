"""ADR-0179 — extraction richness tests."""

from __future__ import annotations

from generate.derivation import extract_quantities


class TestEX1WordNumbers:
    def test_word_number_extracts_as_quantity(self) -> None:
        quantities = extract_quantities("She picked three apples.")

        assert [(q.value, q.unit, q.source_token) for q in quantities] == [
            (3.0, "apples", "three"),
        ]

    def test_digit_and_word_numbers_extract_left_to_right(self) -> None:
        quantities = extract_quantities("She picked 2 apples and three oranges.")

        assert [(q.value, q.unit, q.source_token) for q in quantities] == [
            (2.0, "apples", "2"),
            (3.0, "oranges", "three"),
        ]

    def test_hyphenated_word_number_extracts_as_quantity(self) -> None:
        quantities = extract_quantities("The team scored twenty-four points.")

        assert [(q.value, q.unit, q.source_token) for q in quantities] == [
            (24.0, "points", "twenty-four"),
        ]

    def test_existing_digit_quantity_extraction_still_works(self) -> None:
        quantities = extract_quantities("She picked 6 apples and 4 apples.")

        assert [(q.value, q.unit, q.source_token) for q in quantities] == [
            (6.0, "apples", "6"),
            (4.0, "apples", "4"),
        ]
