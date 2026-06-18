"""Gate A2f — question_bound_product_aggregate serving lift (Paradigm Sprint 5)."""

from __future__ import annotations

import json
from pathlib import Path

from generate.math_candidate_graph import parse_and_solve
from generate.derivation.question_bound_product import (
    compose_question_bound_product,
    resolve_promotable_question_bound_product,
)

_CASES_PATH = (
    Path(__file__).resolve().parents[1]
    / "evals"
    / "gsm8k_math"
    / "train_sample"
    / "v1"
    / "cases.jsonl"
)

CASE_0003 = (
    "The student council sells scented erasers in the morning before school starts to help "
    "raise money for school dances. The local bookstore donated 48 boxes of erasers. "
    "There are 24 erasers in each box. If the student council sells the erasers for "
    "$0.75 each, how much money will they make?"
)

CASE_0021 = (
    "John is lifting weights. He bench presses 15 pounds for 10 reps and does 3 sets. "
    "How much total weight does he move?"
)

HOLDOUT_WRONG_SHAPE = (
    "Penny's canoe can carry 6 people, but if she wants to take her dog, she will only "
    "fit 2/3 of that number inside. If every person in a trip where Penny had her dog "
    "inside the canoe weighed 140 pounds, and the dog 1/4 as much weight, calculate the "
    "total weight the canoe was carrying?"
)


def _run(text: str):
    return parse_and_solve(text, sealed=False)


def test_train_sample_0003_end_to_end():
    res = _run(CASE_0003)
    assert res.answer == 864.0
    assert res.refusal_reason is None


def test_train_sample_0021_end_to_end():
    res = _run(CASE_0021)
    assert res.answer == 450.0
    assert res.refusal_reason is None


def test_sibling_revenue_chain_varied_surface():
    text = (
        "The library donated 12 cartons of markers for a fundraiser. "
        "There are 30 markers in each carton. "
        "If the club sells every marker for $1.25 each, how much money will they raise?"
    )
    res = _run(text)
    assert res.answer == 450.0
    assert res.refusal_reason is None


def test_sibling_weight_chain_varied_surface():
    text = (
        "Ana is training. She squats 20 kilograms for 8 reps and completes 4 sets. "
        "How much total weight does she lift?"
    )
    res = _run(text)
    assert res.answer == 640.0
    assert res.refusal_reason is None


def test_confuser_fraction_surface_refuses():
    assert resolve_promotable_question_bound_product(HOLDOUT_WRONG_SHAPE) is None
    assert _run(HOLDOUT_WRONG_SHAPE).answer is None


def test_confuser_ambiguous_actor_refuses():
    text = (
        "Tom donated 10 crates of books. There are 5 books in each crate. "
        "If Sam sells the books for $2 each, how much money will they make?"
    )
    assert _run(text).answer is None


def test_confuser_additive_distractor_refuses():
    text = (
        "The shop has 20 boxes of pens and 3 loose pens. "
        "There are 10 pens in each box. "
        "If pens sell for $1 each, how much money will they make?"
    )
    assert _run(text).answer is None


def test_confuser_rate_without_target_refuses():
    text = (
        "She runs 6 miles per hour for 2 hours. "
        "How many miles does she run?"
    )
    assert _run(text).answer is None


def test_confuser_reversed_relation_more_than_refuses():
    text = (
        "Lisa has 5 more boxes than Tom. Tom has 10 boxes. "
        "There are 8 toys in each box. "
        "If toys sell for $3 each, how much money will they make?"
    )
    assert _run(text).answer is None


def test_confuser_money_without_in_each_refuses():
    text = (
        "The store has 40 items. Items sell for $2 each. "
        "How much money will they make?"
    )
    assert _run(text).answer is None


def test_confuser_weight_without_for_cue_refuses():
    text = (
        "Kai lifts 12 pounds, 8 reps, and 2 sets during practice. "
        "How much total weight does he move?"
    )
    assert _run(text).answer is None


def test_product_bridge_stays_disabled():
    """Broad product_bridge is not re-wired; this organ is narrower."""
    from generate.derivation.product_bridge import resolve_promotable_product

    assert resolve_promotable_product(CASE_0003) is not None
    assert resolve_promotable_product(CASE_0021) is not None
    assert compose_question_bound_product(CASE_0003) is not None
    assert compose_question_bound_product(CASE_0021) is not None


def test_goal_residual_and_peer_partition_regressions():
    goal = (
        "Michael wants to lose 10 pounds by June. He lost 3 pounds in March and 4 pounds "
        "in April. How much weight does he have to lose in May to meet his goal?"
    )
    peer = (
        "Lilibeth and her friends go strawberry picking. "
        "Lilibeth fills 6 baskets where each basket holds 50 strawberries. "
        "If three of Lilibeth's friends pick the same amount as her, "
        "how many strawberries do Lilibeth and her friends pick in all?"
    )
    assert _run(goal).answer == 3.0
    assert _run(peer).answer == 1200.0


def test_full_train_sample_wrong_zero_and_chunk_lift():
    from evals.gsm8k_math.train_sample.v1.runner import build_report, _load_cases

    report = build_report(_load_cases(_CASES_PATH))
    counts = report["counts"]
    assert counts["wrong"] == 0
    assert counts["correct"] == 16
    assert counts["refused"] == 34
    by_case = {row["case_id"]: row for row in report["per_case"]}
    assert by_case["gsm8k-train-sample-v1-0003"]["verdict"] == "correct"
    assert by_case["gsm8k-train-sample-v1-0021"]["verdict"] == "correct"
    for case_id in (
        "gsm8k-train-sample-v1-0002",
        "gsm8k-train-sample-v1-0008",
        "gsm8k-train-sample-v1-0014",
        "gsm8k-train-sample-v1-0018",
        "gsm8k-train-sample-v1-0024",
        "gsm8k-train-sample-v1-0025",
        "gsm8k-train-sample-v1-0029",
        "gsm8k-train-sample-v1-0037",
        "gsm8k-train-sample-v1-0038",
        "gsm8k-train-sample-v1-0042",
    ):
        assert by_case[case_id]["verdict"] == "correct", case_id