"""Gate A2k/A2l — Capability Paradigm Sprint 8 R6 affine/fraction/partition lift."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from generate.math_candidate_graph import parse_and_solve
from generate.derivation.fraction_decrease import (
    compose_fraction_decrease,
    resolve_promotable_fraction_decrease,
)
from generate.derivation.percent_partition import (
    compose_percent_partition,
    resolve_promotable_percent_partition,
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

CASE_0005 = (
    "In one hour, Addison mountain's temperature will decrease to 3/4  of its temperature. "
    "If the current temperature of the mountain is 84 degrees, what will the temperature "
    "decrease by?"
)

CASE_0046 = (
    "A school has 100 students. Half of the students are girls, the other half are boys.  "
    "20% of the girls have dogs at home and 10% of the boys have dogs at home.  "
    "How many students own dogs?"
)

SIBLING_FRACTION_DECREASE = (
    "In two hours, Cedar peak's temperature will decrease to 2/3 of its temperature. "
    "If the current temperature of the peak is 60 degrees, what will the temperature "
    "decrease by?"
)

SIBLING_PERCENT_PARTITION = (
    "A club has 80 members. Half of the members are adults, the other half are teens. "
    "25% of the adults have snacks and 15% of the teens have snacks. "
    "How many members have snacks?"
)

AFFINE_CONFUSER_0010 = (
    "Yun had 20 paperclips initially, but then lost 12. Marion has 1/4 more than what "
    "Yun currently has, plus 7. How many paperclips does Marion have?"
)

FINAL_VALUE_CONFUSER = (
    "In one hour, the lake's temperature will decrease to 3/4 of its temperature. "
    "If the current temperature of the lake is 80 degrees, what will the temperature be?"
)

UNEQUAL_SPLIT_CONFUSER = (
    "A school has 100 students. 60 of the students are girls and 40 are boys. "
    "20% of the girls have dogs and 10% of the boys have dogs. "
    "How many students own dogs?"
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
    "0030",
    "0035",
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
    def test_train_sample_0005_end_to_end(self):
        res = _run(CASE_0005)
        assert res.answer == 21.0
        assert res.refusal_reason is None

    def test_train_sample_0046_end_to_end(self):
        res = _run(CASE_0046)
        assert res.answer == 15.0
        assert res.refusal_reason is None


class TestSiblingGeneralization:
    def test_fraction_decrease_sibling(self):
        res = _run(SIBLING_FRACTION_DECREASE)
        assert res.answer is not None
        assert abs(res.answer - 20.0) < 1e-6
        assert res.refusal_reason is None

    def test_percent_partition_sibling(self):
        res = _run(SIBLING_PERCENT_PARTITION)
        assert res.answer == 16.0
        assert res.refusal_reason is None


class TestConfuserRefusals:
    def test_affine_more_than_fraction_refuses_fraction_decrease(self):
        assert resolve_promotable_fraction_decrease(AFFINE_CONFUSER_0010) is None

    def test_final_value_question_refuses_fraction_decrease(self):
        assert resolve_promotable_fraction_decrease(FINAL_VALUE_CONFUSER) is None
        assert _run(FINAL_VALUE_CONFUSER).answer is None

    def test_unequal_split_refuses_percent_partition(self):
        assert resolve_promotable_percent_partition(UNEQUAL_SPLIT_CONFUSER) is None
        assert _run(UNEQUAL_SPLIT_CONFUSER).answer is None

    def test_goal_residual_not_fraction_decrease(self):
        goal = (
            "Michael wants to lose 10 pounds by June. He lost 3 pounds in March and "
            "4 pounds in April. How much weight does he have to lose in May to meet "
            "his goal?"
        )
        assert resolve_promotable_fraction_decrease(goal) is None
        assert _run(goal).answer == 3.0


class TestSealedWrongPatternRefusal:
    def test_percent_time_decrease_not_partition(self):
        assert resolve_promotable_percent_partition(SEALED_WRONG_0032_SHAPE) is None
        assert _run(SEALED_WRONG_0032_SHAPE).answer is None

    def test_dcs_partition_not_percent_partition(self):
        assert resolve_promotable_percent_partition(SEALED_WRONG_0047_SHAPE) is None
        assert _run(SEALED_WRONG_0047_SHAPE).answer is None


class TestCompositionValidationPins:
    def test_cv_0007_fraction_decrease(self):
        res = _run(CASE_0005)
        assert res.answer == 21.0

    def test_cv_0008_percent_partition(self):
        res = _run(CASE_0046)
        assert res.answer == 15.0


class TestTrainSampleScore:
    def test_full_train_sample_wrong_zero(self):
        wrong = 0
        for case in _load_train_cases():
            res = _run(case["question"])
            if res.answer is not None and res.answer != float(case["answer_numeric"]):
                wrong += 1
        assert wrong == 0

    def test_aggregate_18_32_0(self):
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
        assert wrong == 0
        assert correct >= 18
        assert refused <= 32
        assert correct + refused + wrong == 50


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
                compose_fraction_decrease(text) is not None
                or compose_percent_partition(text) is not None
            ):
                admitted += 1
        assert admitted == 0


class TestComposeAPI:
    def test_fraction_decrease_compose_matches_promote(self):
        assert compose_fraction_decrease(CASE_0005) is not None
        assert resolve_promotable_fraction_decrease(CASE_0005) is not None

    def test_percent_partition_compose_matches_promote(self):
        assert compose_percent_partition(CASE_0046) is not None
        assert resolve_promotable_percent_partition(CASE_0046) is not None