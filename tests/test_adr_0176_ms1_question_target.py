"""ADR-0176 MS-1 — question-targeting.

The Target is the multi-step search's pruning signal + stopping criterion. MS-1
extracts it from lexeme-level signals only (ADR-0165): question-stated quantities,
an aggregation hint, and asked units resolved by intersection with the body's
known units. Refuse-preferring: no signal -> empty field, never a guess.
"""

from __future__ import annotations

from generate.derivation import Target, extract_target


class TestQuestionQuantities:
    def test_extracts_quantity_stated_in_question(self) -> None:
        # 0033: "when she is 25 years old" -> 25 participates in the derivation
        t = extract_target("How old will the father be when she is 25 years old?")
        assert isinstance(t, Target)
        assert [(q.value, q.unit) for q in t.quantities] == [(25.0, "years")]

    def test_no_question_quantity(self) -> None:
        t = extract_target("How many jumping jacks did Brooke do?")
        assert t.quantities == ()


class TestAggregationHint:
    def test_total(self) -> None:
        assert extract_target("How much total weight does he move?").aggregation == "total"

    def test_altogether_and_combined(self) -> None:
        assert extract_target("How many altogether?").aggregation == "altogether"
        assert extract_target("What is the combined cost?").aggregation == "combined"

    def test_in_all_phrase(self) -> None:
        assert extract_target("How many does he have in all?").aggregation == "in all"

    def test_no_aggregation(self) -> None:
        assert extract_target("How many jumping jacks did Brooke do?").aggregation is None


class TestAskedUnits:
    def test_unit_named_in_question_intersects_body(self) -> None:
        # body has "jumping"; the question names it -> precise target unit
        t = extract_target(
            "How many jumping jacks did Brooke do?", known_units=("jumping", "reps")
        )
        assert t.units == ("jumping",)

    def test_superordinate_unit_not_faked(self) -> None:
        # question says "weight"; body unit is "pounds" -> no exact match -> empty
        # (superordinate resolution is a deferred pack, not faked here)
        t = extract_target(
            "How much total weight does he move?", known_units=("pounds", "reps", "sets")
        )
        assert t.units == ()

    def test_no_known_units_yields_empty(self) -> None:
        assert extract_target("How much money?").units == ()

    def test_units_deduped_and_ordered(self) -> None:
        t = extract_target(
            "how many apples and apples?", known_units=("apples", "apples", "oranges")
        )
        assert t.units == ("apples",)


class TestDeterminism:
    def test_deterministic(self) -> None:
        q = "How much total weight when she is 25 years old?"
        assert extract_target(q, known_units=("pounds",)) == extract_target(
            q, known_units=("pounds",)
        )

    def test_target_is_frozen(self) -> None:
        import dataclasses

        import pytest

        t = extract_target("How many?")
        with pytest.raises(dataclasses.FrozenInstanceError):
            t.aggregation = "total"  # type: ignore[misc]
