"""Tests for the R2 multiple-choice verifier (C4).

Pins the truth-discipline behavior: a proven value ties to exactly one option (else refuse),
and a disagreeing key is flagged as a CONTRADICTION (a confident verdict, not a refusal). Ties
to the C2 gold + C3 solver end-to-end: every solved fixture solves, ties to its labeled answer,
and confirms consistent.
"""

from __future__ import annotations

from evals.constraint_oracle.runner import _load_r2_gold, gold_to_problem
from generate.answer_choices.parse import parse_option_value, parse_options
from generate.answer_choices.verify import ChoiceVerdict, verify_answer_choice
from generate.constraint_comprehension.solver import answer_constraint_problem
from generate.meaning_graph.reader import Refusal


def _solved() -> list[dict]:
    return [f for f in _load_r2_gold() if f["expect"] == "solved"]


def test_parse_option_value_int_and_string() -> None:
    assert parse_option_value(11) == 11
    assert parse_option_value("11") == 11
    assert parse_option_value("11 chickens") == 11
    assert parse_option_value("$11") == 11
    assert parse_option_value("between 5 and 10") is None  # two integers -> ambiguous
    assert parse_option_value(True) is None  # a bool is not a count


def test_parse_options_refuses_empty_and_unparseable() -> None:
    assert isinstance(parse_options({}), Refusal)
    assert isinstance(parse_options({"A": "lots"}), Refusal)
    assert parse_options({"A": 2, "B": "3 buses"}) == {"A": 2, "B": 3}


def test_every_solved_gold_key_is_consistent() -> None:
    for fx in _solved():
        v = verify_answer_choice(fx["gold"], fx["options"], fx["answer"])
        assert isinstance(v, ChoiceVerdict), fx["id"]
        assert v.status == "consistent"
        assert v.computed_label == fx["answer"]


def test_solve_then_verify_end_to_end() -> None:
    # The full off-serving chain that the reader (C5+) will feed: solve -> tie to the option.
    for fx in _solved():
        computed = answer_constraint_problem(gold_to_problem(fx))
        v = verify_answer_choice(computed, fx["options"], fx["answer"], noun=fx["query"]["unit"])
        assert isinstance(v, ChoiceVerdict) and v.status == "consistent"
        assert v.computed_value == fx["gold"] and v.computed_label == fx["answer"]


def test_disagreeing_key_is_flagged_as_contradiction() -> None:
    # chickens: proven 11 == option A; a key of "D" (13) contradicts the equations.
    fx = next(f for f in _solved() if f["id"] == "r2-002-chickens")
    v = verify_answer_choice(11, fx["options"], "D", noun="animals")
    assert isinstance(v, ChoiceVerdict)
    assert v.status == "contradiction"
    assert v.computed_label == "A" and v.provided_label == "D"
    # The message names BOTH the consistent answer and the contradicted key.
    assert "A" in v.message and "11" in v.message and "D" in v.message and "13" in v.message
    assert "contradicts" in v.message


def test_no_matching_option_refuses() -> None:
    out = verify_answer_choice(99, {"A": 2, "B": 3, "C": 4}, "A")
    assert isinstance(out, Refusal) and out.reason == "no_matching_option"


def test_ambiguous_duplicate_options_refuse() -> None:
    out = verify_answer_choice(4, {"A": 4, "B": 4}, None)
    assert isinstance(out, Refusal) and out.reason == "ambiguous_options"


def test_unknown_provided_label_refuses() -> None:
    out = verify_answer_choice(4, {"A": 2, "B": 4}, "Z")
    assert isinstance(out, Refusal) and out.reason == "unknown_provided_label"


def test_consistent_without_a_provided_key_still_labels() -> None:
    v = verify_answer_choice(4, {"A": 2, "B": 4}, None, noun="buses")
    assert isinstance(v, ChoiceVerdict) and v.status == "consistent"
    assert v.computed_label == "B" and "4 buses" in v.message
