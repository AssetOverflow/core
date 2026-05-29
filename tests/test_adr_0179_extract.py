"""ADR-0179 — extraction richness tests."""

from __future__ import annotations

from generate.derivation import extract_quantities


class TestEX4ListUnitInheritance:
    def test_trailing_unit_attaches_to_every_number_in_list(self) -> None:
        quantities = extract_quantities("20, 36, 40 and 50 push-ups")

        assert [q.value for q in quantities] == [20.0, 36.0, 40.0, 50.0]
        assert [q.unit for q in quantities] == ["push-ups"] * 4
        assert [q.source_token for q in quantities] == ["20", "36", "40", "50"]

    def test_case_0024_style_list_inherits_jumping_jacks_unit(self) -> None:
        quantities = extract_quantities(
            "Sidney does 20, 36, 40 and 50 jumping-jacks. "
            "Brooke does three times as many jumping jacks as Sidney."
        )

        assert [q.value for q in quantities] == [20.0, 36.0, 40.0, 50.0]
        assert [q.unit for q in quantities] == ["jumping-jacks"] * 4

    def test_left_to_right_order_with_surrounding_quantities(self) -> None:
        quantities = extract_quantities("She had 2 bags, then did 20, 36 and 40 reps.")

        assert [(q.value, q.unit, q.source_token) for q in quantities] == [
            (2.0, "bags", "2"),
            (20.0, "reps", "20"),
            (36.0, "reps", "36"),
            (40.0, "reps", "40"),
        ]

    def test_existing_single_word_quantity_extraction_still_works(self) -> None:
        quantities = extract_quantities("She picked 6 apples and 4 apples.")

        assert [(q.value, q.unit, q.source_token) for q in quantities] == [
            (6.0, "apples", "6"),
            (4.0, "apples", "4"),
        ]
