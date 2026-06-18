"""Gate A2i/A2j — Capability Paradigm Sprint 7 experience-guided lift."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from generate.math_candidate_graph import parse_and_solve
from generate.derivation.round_trip_trip_duration import (
    compose_round_trip_trip_duration,
    resolve_promotable_round_trip_trip_duration,
)
from generate.derivation.giveaway_target_residual import (
    compose_giveaway_target_residual,
    resolve_promotable_giveaway_target_residual,
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

CASE_0030 = (
    "Jake decides to go to the beach for a fun day.  It is a 2-hour drive each way.  "
    "He then spends 2.5 times at long at the beach as his total driving time.  "
    "How much time does the trip take?"
)

CASE_0035 = (
    "Martha has 20 apples. She decided to split them among her friends. "
    "Jane got 5 apples from her, and James got 2 more than Jane. "
    "How many more apples would Martha need to give away to be left with only 4 of them?"
)

SIBLING_ROUND_TRIP = (
    "Mia plans a lake visit. It is a 3-hour drive each way. She then spends "
    "2 times as long at the lake as her total driving time. How much time does "
    "the trip take?"
)

SIBLING_GIVEAWAY = (
    "Paul has 30 oranges. He shared them with friends. Amy got 8 oranges from him, "
    "and Ben got 3 more than Amy. How many more oranges would Paul need to give away "
    "to be left with only 6 of them?"
)

GOAL_RESIDUAL_CV0005 = (
    "Michael wants to lose 10 pounds by June. He lost 3 pounds in March and 4 pounds "
    "in April. How much weight does he have to lose in May to meet his goal?"
)

DURATION_SEGMENT_0015 = (
    "Traveling from Manhattan to the Bronx, Andrew rides the subway for 10 hours, "
    "takes the train and rides for twice as much time as the subway ride, and then "
    "bikes the remaining distance for 8 hours. What's the total time he takes to "
    "reach the Bronx from Manhattan?"
)

SEALED_WRONG_0032_SHAPE = (
    "He draws and colors 10 pictures. He draws and colors 7 pictures, but each "
    "picture takes 30% less time than the previous one."
)

SEALED_WRONG_0047_SHAPE = (
    "John bakes 12 coconut macaroons, each weighing 5 ounces. He then packs an equal "
    "number of the macaroons in 4 different brown bags, ready for delivery. When he "
    "briefly leaves the kitchen to pick the phone, his little brother Steve eats the "
    "entire contents of one of the brown bags. What is the total weight, in ounces, "
    "of the remaining coconut macaroons?"
)

PRESERVED_SOLVED = (
    "0002",
    "0003",
    "0008",
    "0014",
    "0015",
    "0018",
    "0021",
    "0024",
    "0025",
    "0029",
    "0037",
    "0038",
    "0042",
    "0045",
)


def _run(text: str):
    return parse_and_solve(text, sealed=False)


def _load_train_cases() -> list[dict]:
    return [json.loads(line) for line in _CASES_PATH.read_text().splitlines() if line.strip()]


class TestTargetCases:
    def test_train_sample_0030_end_to_end(self):
        res = _run(CASE_0030)
        assert res.answer == 14.0
        assert res.refusal_reason is None

    def test_train_sample_0035_end_to_end(self):
        res = _run(CASE_0035)
        assert res.answer == 4.0
        assert res.refusal_reason is None


class TestSiblingGeneralization:
    def test_round_trip_sibling(self):
        res = _run(SIBLING_ROUND_TRIP)
        assert res.answer == 18.0
        assert res.refusal_reason is None

    def test_giveaway_sibling(self):
        res = _run(SIBLING_GIVEAWAY)
        assert res.answer == 5.0
        assert res.refusal_reason is None


class TestConfuserRefusals:
    def test_round_trip_without_each_way_refuses(self):
        text = (
            "She drove 2 hours to the beach and spent 2.5 times that long swimming. "
            "How much time does the trip take?"
        )
        assert resolve_promotable_round_trip_trip_duration(text) is None
        assert _run(text).answer is None

    def test_round_trip_fraction_surface_refuses(self):
        text = (
            "It is a 1/2-hour drive each way. He spends 2 times as long at the park "
            "as his total driving time. How much time does the trip take?"
        )
        assert resolve_promotable_round_trip_trip_duration(text) is None

    def test_giveaway_goal_language_refuses(self):
        assert resolve_promotable_giveaway_target_residual(GOAL_RESIDUAL_CV0005) is None
        assert _run(GOAL_RESIDUAL_CV0005).answer == 3.0

    def test_giveaway_comparative_question_refuses(self):
        text = (
            "Martha has 20 apples. Jane got 5 apples from her, and James got 2 more "
            "than Jane. How many more apples did James get than Jane?"
        )
        assert resolve_promotable_giveaway_target_residual(text) is None

    def test_duration_segment_not_round_trip(self):
        assert resolve_promotable_round_trip_trip_duration(DURATION_SEGMENT_0015) is None
        res = _run(DURATION_SEGMENT_0015)
        assert res.answer == 38.0


class TestSealedWrongPatternRefusal:
    def test_0032_percent_time_not_promoted(self):
        assert resolve_promotable_round_trip_trip_duration(SEALED_WRONG_0032_SHAPE) is None
        assert _run(SEALED_WRONG_0032_SHAPE).answer is None

    def test_0047_partition_not_promoted(self):
        assert resolve_promotable_giveaway_target_residual(SEALED_WRONG_0047_SHAPE) is None
        assert _run(SEALED_WRONG_0047_SHAPE).answer is None


class TestTrainSampleScore:
    def test_full_train_sample_wrong_zero(self):
        wrong = 0
        for case in _load_train_cases():
            res = _run(case["question"])
            if res.answer is not None and res.answer != float(case["answer_numeric"]):
                wrong += 1
        assert wrong == 0

    def test_aggregate_16_34_0(self):
        correct = refused = wrong = 0
        for case in _load_train_cases():
            res = _run(case["question"])
            gold = float(case["answer_numeric"])
            if res.answer is None:
                refused += 1
            elif res.answer == gold:
                correct += 1
            else:
                wrong += 1
        assert correct == 16
        assert refused == 34
        assert wrong == 0


class TestPriorSolvedRegression:
    @pytest.mark.parametrize("case_suffix", PRESERVED_SOLVED)
    def test_prior_solved_still_correct(self, case_suffix: str):
        cases = {c["case_id"].split("-")[-1]: c for c in _load_train_cases()}
        case = cases[case_suffix]
        res = _run(case["question"])
        assert res.answer == float(case["answer_numeric"])


class TestHoldoutDevSafety:
    def test_holdout_dev_no_new_admissions(self):
        if not _HOLDOUT_PATH.exists():
            pytest.skip("holdout_dev corpus unavailable")
        admitted = 0
        for line in _HOLDOUT_PATH.read_text().splitlines():
            if not line.strip():
                continue
            case = json.loads(line)
            text = case["problem"]
            if (
                compose_round_trip_trip_duration(text) is not None
                or compose_giveaway_target_residual(text) is not None
            ):
                admitted += 1
        assert admitted == 0


class TestComposeAPI:
    def test_round_trip_compose_matches_promote(self):
        assert compose_round_trip_trip_duration(CASE_0030) is not None
        assert resolve_promotable_round_trip_trip_duration(CASE_0030) is not None

    def test_giveaway_compose_matches_promote(self):
        assert compose_giveaway_target_residual(CASE_0035) is not None
        assert resolve_promotable_giveaway_target_residual(CASE_0035) is not None