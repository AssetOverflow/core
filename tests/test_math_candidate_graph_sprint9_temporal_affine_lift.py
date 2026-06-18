"""Gate A2m/A2n — Capability Paradigm Sprint 9 temporal tariff + affine lift."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from generate.math_candidate_graph import parse_and_solve
from generate.derivation.temporal_tariff import (
    compose_bundle_overflow_tariff,
    compose_overtime_shift_earnings,
    compose_temporal_tariff,
    resolve_promotable_temporal_tariff,
)
from generate.derivation.affine_fraction_delta import (
    compose_affine_fraction_delta,
    resolve_promotable_affine_fraction_delta,
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

CASE_0001 = (
    "Tina makes $18.00 an hour.  If she works more than 8 hours per shift, she is "
    "eligible for overtime, which is paid by your hourly wage + 1/2 your hourly wage.  "
    "If she works 10 hours every day for 5 days, how much money does she make?"
)

CASE_0017 = (
    "Jason has a carriage house that he rents out.  He's charging $50.00 per day or "
    "$500.00 for 14 days.  Eric wants to rent the house for 20 days.  "
    "How much will it cost him?"
)

CASE_0010 = (
    "Yun had 20 paperclips initially, but then lost 12. Marion has 1/4 more than what "
    "Yun currently has, plus 7. How many paperclips does Marion have?"
)

SIBLING_OVERTIME = (
    "Rosa makes $20.00 an hour. If she works more than 6 hours per shift, she is "
    "eligible for overtime, which is paid by your hourly wage + 1/2 your hourly wage. "
    "If she works 9 hours every day for 4 days, how much money does she make?"
)

SIBLING_BUNDLE = (
    "Mia owns a guest cottage. She's charging $40.00 per day or $300.00 for 10 days. "
    "Leo wants to rent the cottage for 15 days. How much will it cost him?"
)

SIBLING_AFFINE = (
    "Sam had 20 marbles initially, but then lost 4. Riley has 1/4 more than what Sam "
    "currently has, plus 3. How many marbles does Riley have?"
)

FRACTION_DECREASE_CONFUSER = (
    "In one hour, Addison mountain's temperature will decrease to 3/4 of its temperature. "
    "If the current temperature of the mountain is 84 degrees, what will the temperature "
    "decrease by?"
)

CURRENCY_AMOUNT_0019_SHAPE = (
    "John adopts a dog from a shelter.  The dog ends up having health problems and this "
    "requires 3 vet appointments,  which cost $400 each.  After the first appointment, "
    "John paid $100 for pet insurance that covers 80% of the subsequent visits.  "
    "How much did he pay in total?"
)

CURRENCY_AMOUNT_0028_SHAPE = (
    "Tom opens an amusement park.  It cost $100,000 to open initially.  It also cost 1% "
    "of that to run per day.  He sells 150  tickets a day for $10 each.  "
    "How long will it take to make back his money?"
)

SEALED_WRONG_0032_SHAPE = (
    "He draws and colors 10 pictures. He draws and colors 7 pictures, but each "
    "picture takes 30% less time than the previous one."
)

OT_ASKS_HOURS_CONFUSER = (
    "Tina makes $18.00 an hour. If she works more than 8 hours per shift, she is "
    "eligible for overtime, which is paid by your hourly wage + 1/2 your hourly wage. "
    "If she works 10 hours every day for 5 days, how many hours does she work in total?"
)

BUNDLE_UNDER_PERIOD_CONFUSER = (
    "Mia owns a guest cottage. She's charging $40.00 per day or $300.00 for 10 days. "
    "Leo wants to rent the cottage for 8 days. How much will it cost him?"
)

AFFINE_TWICE_CONFUSER = (
    "Yun had 20 paperclips initially, but then lost 12. Marion has twice as many "
    "paperclips as Yun currently has. How many paperclips does Marion have?"
)

PRESERVED_SOLVED = (
    "0002",
    "0003",
    "0005",
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
    "0046",
)


def _run(text: str):
    return parse_and_solve(text, sealed=False)


def _load_train_cases() -> list[dict]:
    return [json.loads(line) for line in _CASES_PATH.read_text().splitlines() if line.strip()]


class TestTargetCases:
    def test_train_sample_0001_overtime(self):
        res = _run(CASE_0001)
        assert res.answer == 990.0
        assert res.refusal_reason is None

    def test_train_sample_0017_bundle_tariff(self):
        res = _run(CASE_0017)
        assert res.answer == 800.0
        assert res.refusal_reason is None

    def test_train_sample_0010_affine_fraction_delta(self):
        res = _run(CASE_0010)
        assert res.answer == 9.0
        assert res.refusal_reason is None


class TestSiblingGeneralization:
    def test_overtime_sibling(self):
        res = _run(SIBLING_OVERTIME)
        assert res.answer is not None
        assert abs(res.answer - 840.0) < 1e-6
        assert res.refusal_reason is None

    def test_bundle_sibling(self):
        res = _run(SIBLING_BUNDLE)
        assert res.answer == 500.0
        assert res.refusal_reason is None

    def test_affine_sibling(self):
        res = _run(SIBLING_AFFINE)
        assert res.answer == 7.0
        assert res.refusal_reason is None


class TestConfuserRefusals:
    def test_fraction_decrease_not_affine(self):
        assert resolve_promotable_affine_fraction_delta(FRACTION_DECREASE_CONFUSER) is None
        assert _run(FRACTION_DECREASE_CONFUSER).answer == 21.0

    def test_currency_amount_vet_not_tariff(self):
        assert resolve_promotable_temporal_tariff(CURRENCY_AMOUNT_0019_SHAPE) is None
        assert _run(CURRENCY_AMOUNT_0019_SHAPE).answer is None

    def test_currency_amount_amusement_not_tariff(self):
        assert resolve_promotable_temporal_tariff(CURRENCY_AMOUNT_0028_SHAPE) is None
        assert _run(CURRENCY_AMOUNT_0028_SHAPE).answer is None

    def test_overtime_asks_hours_refuses(self):
        assert resolve_promotable_temporal_tariff(OT_ASKS_HOURS_CONFUSER) is None
        assert _run(OT_ASKS_HOURS_CONFUSER).answer is None

    def test_bundle_under_period_refuses(self):
        assert resolve_promotable_temporal_tariff(BUNDLE_UNDER_PERIOD_CONFUSER) is None
        assert _run(BUNDLE_UNDER_PERIOD_CONFUSER).answer is None

    def test_twice_as_many_not_affine_fraction(self):
        assert resolve_promotable_affine_fraction_delta(AFFINE_TWICE_CONFUSER) is None
        assert _run(AFFINE_TWICE_CONFUSER).answer is None


class TestSealedWrongPatternRefusal:
    def test_percent_decrease_not_temporal_tariff(self):
        assert resolve_promotable_temporal_tariff(SEALED_WRONG_0032_SHAPE) is None
        assert _run(SEALED_WRONG_0032_SHAPE).answer is None


class TestTrainSampleScore:
    def test_full_train_sample_wrong_zero(self):
        wrong = 0
        for case in _load_train_cases():
            res = _run(case["question"])
            if res.answer is not None and res.answer != float(case["answer_numeric"]):
                wrong += 1
        assert wrong == 0

    def test_aggregate_21_29_0(self):
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
        assert correct == 21
        assert refused == 29
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
                compose_temporal_tariff(text) is not None
                or compose_affine_fraction_delta(text) is not None
            ):
                admitted += 1
        assert admitted == 0


class TestComposeAPI:
    def test_overtime_compose_matches_promote(self):
        assert compose_overtime_shift_earnings(CASE_0001) is not None
        assert resolve_promotable_temporal_tariff(CASE_0001) is not None

    def test_bundle_compose_matches_promote(self):
        assert compose_bundle_overflow_tariff(CASE_0017) is not None
        assert resolve_promotable_temporal_tariff(CASE_0017) is not None

    def test_affine_compose_matches_promote(self):
        assert compose_affine_fraction_delta(CASE_0010) is not None
        assert resolve_promotable_affine_fraction_delta(CASE_0010) is not None