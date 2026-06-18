"""Gate A2g/A2h — Capability Paradigm Sprint 6 experience-guided lift."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from generate.math_candidate_graph import parse_and_solve
from generate.derivation.duration_segment_total import (
    compose_duration_segment_total,
    resolve_promotable_duration_segment_total,
)
from generate.derivation.survey_rate_earnings import (
    compose_survey_rate_earnings,
    resolve_promotable_survey_rate_earnings,
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

CASE_0015 = (
    "Traveling from Manhattan to the Bronx, Andrew rides the subway for 10 hours, "
    "takes the train and rides for twice as much time as the subway ride, and then "
    "bikes the remaining distance for 8 hours. What's the total time he takes to "
    "reach the Bronx from Manhattan?"
)

CASE_0045 = (
    "Bart fills out surveys to earn money. He receives $0.2 for every question he "
    "answers in the survey. Each survey has 10 questions. On Monday he finished "
    "3 surveys, and on Tuesday 4 surveys. How much money did he earn during these "
    "two days?"
)

SIBLING_DURATION = (
    "Crossing the city, Maria rides the bus for 5 hours, then the ferry for twice "
    "as much time as the bus ride, then walks the remaining distance for 3 hours. "
    "What's the total time for her journey?"
)

SIBLING_SURVEY = (
    "Lisa completes surveys for cash. She gets $0.50 per question. Every survey has "
    "8 questions. On Wednesday she finished 2 surveys, and on Thursday 5 surveys. "
    "How much money did she earn?"
)

SEALED_WRONG_0047_SHAPE = (
    "John bakes 12 coconut macaroons, each weighing 5 ounces. He then packs an equal "
    "number of the macaroons in 4 different brown bags, ready for delivery. When he "
    "briefly leaves the kitchen to pick the phone, his little brother Steve eats the "
    "entire contents of one of the brown bags. What is the total weight, in ounces, "
    "of the remaining coconut macaroons?"
)

SEALED_WRONG_0032_SHAPE = (
    "He draws and colors 10 pictures. He draws and colors 7 pictures, but each "
    "picture takes 30% less time than the previous one."
)

PRESERVED_SOLVED = (
    "0002",
    "0003",
    "0008",
    "0014",
    "0018",
    "0021",
    "0024",
    "0025",
    "0029",
    "0037",
    "0038",
    "0042",
)


def _run(text: str):
    return parse_and_solve(text, sealed=False)


def _load_train_cases() -> list[dict]:
    return [json.loads(line) for line in _CASES_PATH.read_text().splitlines() if line.strip()]


class TestTargetCases:
    def test_train_sample_0015_end_to_end(self):
        res = _run(CASE_0015)
        assert res.answer == 38.0
        assert res.refusal_reason is None

    def test_train_sample_0045_end_to_end(self):
        res = _run(CASE_0045)
        assert res.answer == 14.0
        assert res.refusal_reason is None


class TestSiblingGeneralization:
    def test_duration_segment_sibling(self):
        res = _run(SIBLING_DURATION)
        assert res.answer == 18.0
        assert res.refusal_reason is None

    def test_survey_earnings_sibling(self):
        res = _run(SIBLING_SURVEY)
        assert res.answer == 28.0
        assert res.refusal_reason is None


class TestConfuserRefusals:
    def test_duration_without_total_time_question_refuses(self):
        text = (
            "Andrew rides the subway for 10 hours, then the train for twice as much "
            "time as the subway ride, then bikes for 8 hours. How many hours on the train?"
        )
        assert resolve_promotable_duration_segment_total(text) is None
        assert _run(text).answer is None

    def test_survey_without_rate_refuses(self):
        text = (
            "Each survey has 10 questions. On Monday 3 surveys and Tuesday 4 surveys. "
            "How much money did he earn?"
        )
        assert resolve_promotable_survey_rate_earnings(text) is None

    def test_survey_comparative_distractor_refuses(self):
        text = (
            "He gets $0.20 per question. Each survey has 10 questions. "
            "On Monday 3 surveys and on Tuesday twice as many surveys as Monday. "
            "How much money did he earn?"
        )
        assert _run(text).answer is None

    def test_duration_fraction_surface_refuses(self):
        text = (
            "She rode 1/2 hour on the bus, then twice as much time as that on the train, "
            "then 2 hours walking. What's the total time?"
        )
        assert resolve_promotable_duration_segment_total(text) is None


class TestSealedWrongPatternRefusal:
    def test_0047_partition_weight_not_promoted(self):
        assert resolve_promotable_duration_segment_total(SEALED_WRONG_0047_SHAPE) is None
        assert resolve_promotable_survey_rate_earnings(SEALED_WRONG_0047_SHAPE) is None
        assert _run(SEALED_WRONG_0047_SHAPE).answer is None

    def test_0032_percent_time_not_promoted(self):
        assert resolve_promotable_duration_segment_total(SEALED_WRONG_0032_SHAPE) is None
        assert _run(SEALED_WRONG_0032_SHAPE).answer is None


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
                compose_duration_segment_total(text) is not None
                or compose_survey_rate_earnings(text) is not None
            ):
                admitted += 1
        assert admitted == 0


class TestComposeAPI:
    def test_duration_compose_matches_promote(self):
        assert compose_duration_segment_total(CASE_0015) is not None
        assert resolve_promotable_duration_segment_total(CASE_0015) is not None

    def test_survey_compose_matches_promote(self):
        assert compose_survey_rate_earnings(CASE_0045) is not None
        assert resolve_promotable_survey_rate_earnings(CASE_0045) is not None