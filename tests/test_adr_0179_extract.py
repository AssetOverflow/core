"""ADR-0179 extraction richness tests."""

from __future__ import annotations

from generate.derivation import extract_quantities


class TestEX5SentenceFinalNumbers:
    def test_sentence_final_number_extracts_with_empty_unit(self) -> None:
        quantities = extract_quantities("She had 5.")

        assert [(q.value, q.unit, q.source_token) for q in quantities] == [
            (5.0, "", "5"),
        ]

    def test_question_final_number_extracts_with_empty_unit(self) -> None:
        quantities = extract_quantities("The answer is 7?")

        assert [(q.value, q.unit, q.source_token) for q in quantities] == [
            (7.0, "", "7"),
        ]

    def test_unit_quantity_and_final_number_extract_left_to_right(self) -> None:
        quantities = extract_quantities("She picked 6 apples and had 4.")

        assert [(q.value, q.unit, q.source_token) for q in quantities] == [
            (6.0, "apples", "6"),
            (4.0, "", "4"),
        ]

    def test_number_with_unit_is_not_duplicated_as_final_number(self) -> None:
        quantities = extract_quantities("She picked 6 apples.")

        assert [(q.value, q.unit, q.source_token) for q in quantities] == [
            (6.0, "apples", "6"),
        ]
