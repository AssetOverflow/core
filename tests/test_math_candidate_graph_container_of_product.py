"""Gate A2c — container_of_product + yield_question composition."""

from __future__ import annotations

from generate.math_candidate_graph import parse_and_solve
from generate.math_candidate_parser import (
    extract_initial_candidates,
    extract_question_candidates,
)


def _run(text: str):
    return parse_and_solve(text, sealed=False)


def test_bags_of_product_single_extracts():
    stmt = "Tom bought 3 bags of 20 marbles."
    cands = extract_initial_candidates(stmt)
    assert len(cands) == 1
    cand = cands[0]
    assert cand.initial.quantity.value == 60.0
    assert cand.initial.quantity.unit == "marbles"
    assert cand.matched_anchor == "bought"


def test_bags_of_product_conj_extracts_sum():
    stmt = "She bought 4 bags of 15 coins and 1 bag of 40 coins."
    cands = extract_initial_candidates(stmt)
    assert len(cands) == 1
    assert cands[0].initial.quantity.value == 100.0
    assert cands[0].initial.quantity.unit == "coins"


def test_yield_question_extracts_with_rate():
    full = (
        "If 10 marbles are used to make one necklace, "
        "how many necklaces will Alice be able to make?"
    )
    q = "How many necklaces will Alice be able to make?"
    cands = extract_question_candidates(q, problem_text=full)
    assert len(cands) == 1
    cand = cands[0]
    assert cand.unknown.entity == "Alice"
    assert cand.unknown.unit == "necklaces"
    assert cand.yield_chunk_value == 10.0
    assert cand.yield_chunk_unit == "marbles"
    assert cand.yield_quotient_unit == "necklaces"


def test_train_sample_0008_end_to_end():
    text = (
        "Marnie makes bead bracelets. "
        "She bought 5 bags of 50 beads and 2 bags of 100 beads. "
        "If 50 beads are used to make one bracelet, how many bracelets "
        "will Marnie be able to make out of the beads she bought?"
    )
    res = _run(text)
    assert res.answer == 9.0
    assert res.refusal_reason is None


def test_sibling_tom_marbles():
    text = (
        "Tom collects marbles. "
        "He bought 3 bags of 20 marbles. "
        "If 10 marbles are used to make one display, "
        "how many displays will Tom be able to make?"
    )
    res = _run(text)
    assert res.answer == 6.0
    assert res.refusal_reason is None


def test_sibling_alice_coins():
    text = (
        "Alice runs a craft shop. "
        "She bought 4 bags of 15 coins and 1 bag of 40 coins. "
        "If 20 coins are used to make one charm, "
        "how many charms will Alice be able to make?"
    )
    res = _run(text)
    assert res.answer == 5.0
    assert res.refusal_reason is None


def test_confuser_mismatched_units_in_conj_refuses():
    stmt = "She bought 3 bags of 20 beads and 2 boxes of 10 marbles."
    assert extract_initial_candidates(stmt) == []


def test_confuser_bags_of_without_numeric_product_refuses():
    stmt = "She bought bags of beads."
    assert extract_initial_candidates(stmt) == []


def test_confuser_yield_without_rate_clause_refuses():
    q = "How many bracelets will Marnie be able to make?"
    assert extract_question_candidates(q, problem_text=q) == []


def test_confuser_rate_product_mismatch_refuses():
    q = (
        "If 50 beads are used to make one bracelet, "
        "how many necklaces will Marnie be able to make?"
    )
    assert extract_question_candidates(q, problem_text=q) == []


def test_confuser_non_integer_quotient_refuses():
    text = (
        "Marnie makes bead bracelets. "
        "She bought 3 bags of 10 beads. "
        "If 7 beads are used to make one bracelet, "
        "how many bracelets will Marnie be able to make?"
    )
    res = _run(text)
    assert res.answer is None
    assert res.refusal_reason is not None


def test_confuser_multi_actor_pronoun_initial_refuses():
    text = (
        "Marnie makes bead bracelets. "
        "Alice sorts craft beads. "
        "She bought 5 bags of 50 beads and 2 bags of 100 beads. "
        "If 50 beads are used to make one bracelet, how many bracelets "
        "will Marnie be able to make?"
    )
    res = _run(text)
    assert res.answer is None
    assert res.refusal_reason is not None


def test_regression_0042_embedded_quantifier_still_solves():
    text = (
        "Ella has 4 bags with 20 apples in each bag and "
        "six bags with 25 apples in each bag.  "
        "If Ella sells 200 apples, how many apples does Ella has left?"
    )
    res = _run(text)
    assert res.answer == 30.0
    assert res.refusal_reason is None
