"""ADR-0179 — extraction richness tests (sealed lane: generate/derivation/extract).

Integration of the EX-1 (word-numbers), EX-4 (list-unit inheritance), and EX-5
(sentence-final numbers) sub-phases. EX-3 (multi-word units) is deferred — see
the module docstring and docs/handoff/AUDIT-ADR-0179-EX-RECONCILE.md — so there
is no multi-word-unit test class here by design.

Every assertion is a plain input-string → extracted-quantity check. Over-extraction
in this lane costs refusals (the gate is refuse-preferring), never wrong answers.
"""

from __future__ import annotations

from generate.derivation import extract_quantities


def _triples(text: str) -> list[tuple[float, str, str]]:
    return [(q.value, q.unit, q.source_token) for q in extract_quantities(text)]


class TestEX1WordNumbers:
    def test_word_number_extracts_as_quantity(self) -> None:
        assert _triples("She picked three apples.") == [(3.0, "apples", "three")]

    def test_digit_and_word_numbers_extract_left_to_right(self) -> None:
        assert _triples("She picked 2 apples and three oranges.") == [
            (2.0, "apples", "2"),
            (3.0, "oranges", "three"),
        ]

    def test_hyphenated_tens_one_compound(self) -> None:
        assert _triples("The team scored twenty-four points.") == [
            (24.0, "points", "twenty-four"),
        ]

    def test_non_tens_one_compound_is_not_guessed(self) -> None:
        # "one-third" is not a tens-one compound; the resolver declines the whole
        # hyphen match rather than invent a composition rule (no fraction support,
        # no fall-back to "one" alone). Conservative: nothing extracted.
        assert _triples("He ate one-third pizza.") == []

    def test_factor_words_are_not_extracted_as_counts(self) -> None:
        # half/third/quarter read as divisors, not counts — excluded from EX-1.
        assert _triples("She drank half cup.") == []


class TestEX4ListUnitInheritance:
    def test_trailing_unit_attaches_to_every_number_in_list(self) -> None:
        qs = extract_quantities("20, 36, 40 and 50 push-ups")
        assert [q.value for q in qs] == [20.0, 36.0, 40.0, 50.0]
        assert [q.unit for q in qs] == ["push-ups"] * 4
        assert [q.source_token for q in qs] == ["20", "36", "40", "50"]

    def test_left_to_right_order_with_surrounding_quantities(self) -> None:
        assert _triples("She had 2 bags, then did 20, 36 and 40 reps.") == [
            (2.0, "bags", "2"),
            (20.0, "reps", "20"),
            (36.0, "reps", "36"),
            (40.0, "reps", "40"),
        ]

    def test_list_numbers_not_double_counted(self) -> None:
        # the trailing number's "50 push-ups" must not also surface via the
        # single-unit pass.
        qs = extract_quantities("20, 36, 40 and 50 push-ups")
        assert len(qs) == 4


class TestEX5SentenceFinalNumbers:
    def test_sentence_final_number_extracts_with_empty_unit(self) -> None:
        assert _triples("She had 5.") == [(5.0, "", "5")]

    def test_question_final_number_extracts_with_empty_unit(self) -> None:
        assert _triples("The answer is 7?") == [(7.0, "", "7")]

    def test_unit_quantity_and_final_number_extract_left_to_right(self) -> None:
        assert _triples("She picked 6 apples and had 4.") == [
            (6.0, "apples", "6"),
            (4.0, "", "4"),
        ]

    def test_number_with_unit_is_not_duplicated_as_final_number(self) -> None:
        assert _triples("She picked 6 apples.") == [(6.0, "apples", "6")]


class TestNoRegression:
    def test_simple_digit_units_still_work(self) -> None:
        assert _triples("She picked 6 apples and 4 apples.") == [
            (6.0, "apples", "6"),
            (4.0, "apples", "4"),
        ]

    def test_decimal_value_preserved(self) -> None:
        assert _triples("It costs 0.75 dollars.") == [(0.75, "dollars", "0.75")]


class TestRealCase0024StillBlocked:
    """Honest pin: the EX-4 unit-list pattern does NOT recover real case 0024.

    The actual gold text interleaves numbers with temporal phrases
    ("36 on Tuesday, 40 on Wednesday"), so the bare-list regex never fires and the
    36/40/50 do not inherit "jumping jacks". This test documents the current
    boundary so no future change silently claims 0024 is "unblocked" without
    proving the (20+36+40+50)*3 = 438 chain end-to-end.
    """

    def test_only_first_number_carries_the_unit(self) -> None:
        qs = extract_quantities(
            "Sidney does 20 jumping jacks on Monday, 36 on Tuesday, "
            "40 on Wednesday, and 50 on Thursday."
        )
        values = [q.value for q in qs]
        assert values == [20.0, 36.0, 40.0, 50.0]
        # 20 keeps a unit word; the bare 36/40/50 do not inherit "jumping" — they
        # are sentence-internal, not a bare comma-list, so EX-4 cannot reach them.
        units = [q.unit for q in qs]
        assert units[0] == "jumping"
        assert len(set(units)) > 1  # NOT a same-unit list -> compose refuses
