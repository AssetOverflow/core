"""Gate A2d — peer_partition_question composition."""

from __future__ import annotations

from generate.math_candidate_graph import parse_and_solve
from generate.math_candidate_parser import (
    extract_initial_candidates,
    extract_question_candidates,
)


def _run(text: str):
    return parse_and_solve(text, sealed=False)


def test_peer_pick_question_extracts_with_conditional():
    full = (
        "Lilibeth fills 6 baskets where each basket holds 50 strawberries. "
        "If three of Lilibeth's friends pick the same amount as her, "
        "how many strawberries do Lilibeth and her friends pick in all?"
    )
    q = "How many strawberries do Lilibeth and her friends pick in all?"
    cands = extract_question_candidates(q, problem_text=full)
    assert len(cands) == 1
    cand = cands[0]
    assert cand.unknown.entity is None
    assert cand.unknown.unit == "strawberries"
    assert cand.peer_count == 3
    assert cand.peer_reference_entity == "Lilibeth"
    assert cand.consumed_value_tokens == ("three",)


def test_train_sample_0025_end_to_end():
    text = (
        "Lilibeth and her friends go strawberry picking. "
        "Lilibeth fills 6 baskets where each basket holds 50 strawberries. "
        "If three of Lilibeth's friends pick the same amount as her, "
        "how many strawberries do Lilibeth and her friends pick in all?"
    )
    res = _run(text)
    assert res.answer == 1200.0
    assert res.refusal_reason is None


def test_sibling_tom_apples():
    text = (
        "Tom picks apples. "
        "Tom fills 4 baskets where each basket holds 25 apples. "
        "If two of Tom's friends pick the same amount as him, "
        "how many apples do Tom and his friends pick in all?"
    )
    res = _run(text)
    assert res.answer == 300.0
    assert res.refusal_reason is None


def test_sibling_alice_strawberries():
    text = (
        "Alice and her crew go picking. "
        "Alice fills 3 baskets where each basket holds 40 strawberries. "
        "If 1 of Alice's friends pick the same amount as her, "
        "how many strawberries do Alice and her friends pick in all?"
    )
    res = _run(text)
    assert res.answer == 240.0
    assert res.refusal_reason is None


def test_confuser_missing_conditional_refuses():
    text = (
        "Lilibeth fills 6 baskets where each basket holds 50 strawberries. "
        "How many strawberries do Lilibeth and her friends pick in all?"
    )
    res = _run(text)
    assert res.answer is None


def test_confuser_no_prior_initial_refuses():
    text = (
        "If three of Lilibeth's friends pick the same amount as her, "
        "how many strawberries do Lilibeth and her friends pick in all?"
    )
    res = _run(text)
    assert res.answer is None


def test_confuser_entity_mismatch_refuses():
    text = (
        "Lilibeth fills 6 baskets where each basket holds 50 strawberries. "
        "If three of Tom's friends pick the same amount as him, "
        "how many strawberries do Lilibeth and her friends pick in all?"
    )
    res = _run(text)
    assert res.answer is None


def test_confuser_friends_without_count_refuses():
    text = (
        "Lilibeth fills 6 baskets where each basket holds 50 strawberries. "
        "If some of Lilibeth's friends pick the same amount as her, "
        "how many strawberries do Lilibeth and her friends pick in all?"
    )
    res = _run(text)
    assert res.answer is None


def test_comparative_question_still_refuses():
    text = (
        "Francine has five full boxes of crayons and 5 loose crayons, "
        "and her friend has 27 loose crayons. "
        "They need to put all of their loose crayons in a box. "
        "How many more boxes do they need if Francine has a total of 85 crayons?"
    )
    res = _run(text)
    assert res.answer is None


def test_yield_regression_0008():
    text = (
        "Marnie makes bead bracelets. "
        "She bought 5 bags of 50 beads and 2 bags of 100 beads. "
        "If 50 beads are used to make one bracelet, how many bracelets "
        "will Marnie be able to make out of the beads she bought?"
    )
    res = _run(text)
    assert res.answer == 9.0
    assert res.refusal_reason is None


def test_bags_of_product_statement_not_peer_pick():
    stmt = "She bought 4 bags of 15 coins and 1 bag of 40 coins."
    cands = extract_initial_candidates(stmt)
    assert len(cands) == 1
    assert cands[0].initial.quantity.value == 100.0
