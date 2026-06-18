"""Gate A2o/A2p — Capability Paradigm Sprint 10 frontier lift."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from generate.math_candidate_graph import parse_and_solve
from generate.derivation.affine_comparative_inversion_total import (
    compose_affine_comparative_inversion_total,
    resolve_promotable_affine_comparative_inversion_total,
)
from generate.derivation.sequential_comparative_scale import (
    compose_sequential_comparative_scale,
    resolve_promotable_sequential_comparative_scale,
)

_CASES_PATH = (
    Path(__file__).resolve().parents[1]
    / "evals"
    / "gsm8k_math"
    / "train_sample"
    / "v1"
    / "cases.jsonl"
)
_HOLDOUT_PATH = (
    Path(__file__).resolve().parents[1]
    / "evals"
    / "gsm8k_math"
    / "holdout_dev"
    / "v1"
    / "cases.jsonl"
)

CASE_0006 = (
    "Mandy started reading books with only 8 pages when she was 6 years old. "
    "By the time she was twice that age, she was reading books 5 times longer, "
    "and 8 years later, she was reading books 3 times longer than that. "
    "Presently, she reads books that are 4 times the previous length. "
    "How many pages do the books she reads now have?"
)

CASE_0009 = (
    "Jen has 10 more ducks than four times the number of chickens. "
    "If Jen has 150 ducks, how many total birds does she have?"
)

CASE_0013 = (
    "Allison, a YouTuber, uploads 10 one-hour videos of food reviews each day "
    "to her channel. She uploaded videos halfway through June, at that pace, "
    "and then doubled the number of video hours she uploaded on the remaining days. "
    "What's the total number of video hours she has uploaded at the end of the month?"
)

SIBLING_SCALE = (
    "Liam started reading comics with only 12 pages when he was 8 years old. "
    "By the time he was twice that age, he was reading comics 3 times longer, "
    "and 5 years later, he was reading comics 2 times longer than that. "
    "Presently, he reads comics that are 5 times the previous length. "
    "How many pages do the comics he reads now have?"
)

SIBLING_AFFINE = (
    "Mia has 6 more apples than three times the number of oranges. "
    "If Mia has 42 apples, how many total fruits does she have?"
)

SCALE_ASKS_AGE_CONFUSER = (
    "Mandy started reading books with only 8 pages when she was 6 years old. "
    "By the time she was twice that age, she was reading books 5 times longer, "
    "and 8 years later, she was reading books 3 times longer than that. "
    "Presently, she reads books that are 4 times the previous length. "
    "How old is Mandy now?"
)

SCALE_DOUBLED_WEIGHT_CONFUSER = (
    "At 7 weeks old, the puppy weighed 6 pounds, but doubled in weight by week 9. "
    "It doubled in weight again at 3 months old, and doubled again at 5 months old. "
    "What is the dog's full adult weight, in pounds?"
)

SCALE_SINGLE_STEP_CONFUSER = (
    "Mandy started reading books with only 8 pages when she was 6 years old. "
    "Presently, she reads books that are 4 times longer. "
    "How many pages do the books she reads now have?"
)

AFFINE_ACTOR_MISMATCH = (
    "Jen has 10 more ducks than four times the number of chickens. "
    "If Sam has 150 ducks, how many total birds does she have?"
)

AFFINE_NO_CONDITIONAL = (
    "Jen has 10 more ducks than four times the number of chickens. "
    "How many total birds does she have?"
)

AFFINE_YIELD_CONFUSER = (
    "A farmer has 10 acres of corn and four times as many acres of wheat. "
    "If the farmer has 150 acres of corn, how many total acres does he have?"
)

SEALED_WRONG_0025_SHAPE = (
    "Lilibeth fills 6 baskets where each basket holds 50 strawberries. "
    "She, her brother, and 3 of her friends equally picked strawberries. "
    "How many strawberries did each person pick?"
)

SEALED_WRONG_0047_SHAPE = (
    "John bakes 12 coconut macaroons, each weighing 5 ounces. "
    "He then packs an equal number of the macaroons in 4 different brown bags, "
    "ready for delivery. One bag is eaten. What is the total weight of the "
    "remaining macaroons?"
)

PRESERVED_SOLVED = (
    "0001",
    "0002",
    "0003",
    "0005",
    "0008",
    "0010",
    "0014",
    "0015",
    "0017",
    "0018",
    "0021",
    "0024",
    "0025",
    "0029",
    "0030",
    "0035",
    "0037",
    "0038",
    "0042",
    "0045",
    "0046",
)


def _load_case(case_suffix: str) -> str:
    for line in _CASES_PATH.read_text().splitlines():
        row = json.loads(line)
        if row["case_id"].endswith(case_suffix):
            return row["question"]
    raise KeyError(case_suffix)


class TestTargetCases:
    def test_0006_solves(self) -> None:
        result = parse_and_solve(_load_case("0006"))
        assert result.answer == 480.0
        assert result.refusal_reason is None

    def test_0009_solves(self) -> None:
        result = parse_and_solve(_load_case("0009"))
        assert result.answer == 185.0
        assert result.refusal_reason is None

    def test_0013_still_refuses_calendar_grounding(self) -> None:
        result = parse_and_solve(CASE_0013)
        assert result.answer is None


class TestSiblingGeneralization:
    def test_sequential_scale_sibling(self) -> None:
        resolution = compose_sequential_comparative_scale(SIBLING_SCALE)
        assert resolution is not None
        assert resolution.answer == 12 * 3 * 2 * 5

    def test_affine_inversion_sibling(self) -> None:
        resolution = compose_affine_comparative_inversion_total(SIBLING_AFFINE)
        assert resolution is not None
        assert resolution.answer == 42 + (42 - 6) / 3


class TestConfuserRefusals:
    def test_scale_asks_age_refuses(self) -> None:
        assert compose_sequential_comparative_scale(SCALE_ASKS_AGE_CONFUSER) is None

    def test_scale_doubled_weight_refuses(self) -> None:
        assert compose_sequential_comparative_scale(SCALE_DOUBLED_WEIGHT_CONFUSER) is None

    def test_scale_single_step_refuses(self) -> None:
        assert compose_sequential_comparative_scale(SCALE_SINGLE_STEP_CONFUSER) is None

    def test_affine_actor_mismatch_refuses(self) -> None:
        assert compose_affine_comparative_inversion_total(AFFINE_ACTOR_MISMATCH) is None

    def test_affine_no_conditional_refuses(self) -> None:
        assert compose_affine_comparative_inversion_total(AFFINE_NO_CONDITIONAL) is None

    def test_affine_yield_shape_refuses(self) -> None:
        assert compose_affine_comparative_inversion_total(AFFINE_YIELD_CONFUSER) is None

    def test_ma_sealed_wrong_0025_refuses(self) -> None:
        assert compose_sequential_comparative_scale(SEALED_WRONG_0025_SHAPE) is None

    def test_ma_sealed_wrong_0047_refuses(self) -> None:
        assert compose_sequential_comparative_scale(SEALED_WRONG_0047_SHAPE) is None


class TestPromotionBridges:
    def test_resolve_promotable_affine_inversion(self) -> None:
        assert resolve_promotable_affine_comparative_inversion_total(CASE_0009) is not None

    def test_resolve_promotable_sequential_scale(self) -> None:
        assert resolve_promotable_sequential_comparative_scale(CASE_0006) is not None


class TestTrainSampleScore:
    def test_wrong_zero_and_state_a(self) -> None:
        from evals.gsm8k_math.train_sample.v1.runner import build_report, _load_cases

        report = build_report(_load_cases(_CASES_PATH))
        counts = report["counts"]
        assert counts["wrong"] == 0
        assert counts["correct"] >= 23
        assert counts["refused"] <= 27

    def test_newly_solved_ids(self) -> None:
        from evals.gsm8k_math.train_sample.v1.runner import build_report, _load_cases

        report = build_report(_load_cases(_CASES_PATH))
        correct = {
            row["case_id"].split("-")[-1]
            for row in report["per_case"]
            if row["verdict"] == "correct"
        }
        assert "0006" in correct
        assert "0009" in correct

    def test_preserved_solved_ids(self) -> None:
        from evals.gsm8k_math.train_sample.v1.runner import build_report, _load_cases

        report = build_report(_load_cases(_CASES_PATH))
        correct = {
            row["case_id"].split("-")[-1]
            for row in report["per_case"]
            if row["verdict"] == "correct"
        }
        for case_id in PRESERVED_SOLVED:
            assert case_id in correct


class TestHoldoutInert:
    def test_holdout_dev_wrong_zero(self) -> None:
        from evals.gsm8k_math.holdout_dev.v1.runner import build_report

        report = build_report()
        assert report["counts"]["wrong"] == 0