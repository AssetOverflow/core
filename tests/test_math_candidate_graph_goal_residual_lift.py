"""Gate A2e — goal_residual_question serving lift (ADR-0207 R4)."""

from __future__ import annotations

from generate.math_candidate_graph import parse_and_solve
from generate.derivation.goal_residual import compose_goal_residual

CV0005 = (
    "Michael wants to lose 10 pounds by June. He lost 3 pounds in March and 4 pounds "
    "in April. How much weight does he have to lose in May to meet his goal?"
)
SAVE_GOAL = (
    "Maria wants to earn 20 dollars for a gift. She earned 5 dollars in May and 6 dollars "
    "in June. How much more does she need to earn to reach her goal?"
)


def _run(text: str):
    return parse_and_solve(text, sealed=False)


def test_train_sample_0037_end_to_end():
    res = _run(CV0005)
    assert res.answer == 3.0
    assert res.refusal_reason is None


def test_sibling_gain_goal_divergence_firewall():
    """Must read goal-residual (9), not possession accumulation (31)."""
    res = _run(SAVE_GOAL)
    assert res.answer == 9.0
    assert res.refusal_reason is None
    assert compose_goal_residual(SAVE_GOAL) is not None


def test_confuser_no_goal_language_refuses():
    text = (
        "Sam has 14 apples. He gives away 3 apples and 2 apples. "
        "How much more does Sam need to give away to meet his goal?"
    )
    res = _run(text)
    assert res.answer is None


def test_confuser_no_residual_question_refuses():
    text = (
        "Michael wants to lose 10 pounds by June. He lost 3 pounds in March and 4 pounds "
        "in April. How much weight did he lose in total?"
    )
    res = _run(text)
    assert res.answer is None


def test_confuser_cross_referent_refuses():
    text = (
        "Michael wants to lose 10 pounds by June. Sarah lost 3 pounds in March. "
        "How much more does Michael need to lose to meet his goal?"
    )
    res = _run(text)
    assert res.answer is None


def test_product_bridge_cases_still_refuse():
    """product_bridge stays disabled — 0003/0021 must not lift via this path."""
    for text in (
        (
            "The student council sells scented erasers in the morning before school starts "
            "to help raise money for school dances. The local bookstore donated 48 boxes of "
            "erasers. There are 24 erasers in each box. If the student council sells the "
            "erasers for $0.75 each, how much money will they make?"
        ),
        (
            "John is lifting weights. He bench presses 15 pounds for 10 reps and does 3 sets. "
            "How much total weight does he move?"
        ),
    ):
        res = _run(text)
        assert res.answer is None


def test_peer_pick_regression_0025():
    text = (
        "Lilibeth and her friends go strawberry picking. "
        "Lilibeth fills 6 baskets where each basket holds 50 strawberries. "
        "If three of Lilibeth's friends pick the same amount as her, "
        "how many strawberries do Lilibeth and her friends pick in all?"
    )
    res = _run(text)
    assert res.answer == 1200.0
    assert res.refusal_reason is None