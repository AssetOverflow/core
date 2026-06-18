"""Gate A2q — Capability Paradigm Sprint 11 cluster-contract calendar lift."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from generate.derivation.calendar_grounding import (
    CIVIL_MONTH_DAY_COUNT,
    PROVENANCE_CALENDAR_TABLE,
    allows_halfway_split,
    resolve_month_grounding,
)
from generate.derivation.piecewise_daily_hours_total import (
    compose_piecewise_daily_hours_total,
    resolve_promotable_piecewise_daily_hours_total,
)
from generate.math_candidate_graph import parse_and_solve

_CASES_PATH = (
    Path(__file__).resolve().parents[1]
    / "evals"
    / "gsm8k_math"
    / "train_sample"
    / "v1"
    / "cases.jsonl"
)

CASE_0013 = (
    "Allison, a YouTuber, uploads 10 one-hour videos of food reviews each day "
    "to her channel. She uploaded videos halfway through June,  at that pace,  "
    "and then doubled the number of video hours she uploaded on the remaining days. "
    "What's the total number of video hours she has uploaded at the end of the month?"
)

SIBLING_SEPTEMBER = (
    "Morgan, a podcaster, uploads 6 one-hour episodes of book reviews each day "
    "to her feed. She uploaded episodes halfway through September, at that pace, "
    "and then doubled the number of episode hours she uploaded on the remaining days. "
    "What's the total number of episode hours she has uploaded at the end of the month?"
)

FEBRUARY_CONFUSER = (
    "Nina, a creator, uploads 5 one-hour clips each day to her channel. "
    "She uploaded clips halfway through February, at that pace, "
    "and then doubled the number of video hours she uploaded on the remaining days. "
    "What's the total number of video hours she has uploaded at the end of the month?"
)

JANUARY_ODD_MONTH_CONFUSER = (
    "Riley, a creator, uploads 4 one-hour vlogs each day to her channel. "
    "She uploaded vlogs halfway through January, at that pace, "
    "and then doubled the number of video hours she uploaded on the remaining days. "
    "What's the total number of video hours she has uploaded at the end of the month?"
)

ASKS_DAILY_RATE_CONFUSER = (
    "Allison, a YouTuber, uploads 10 one-hour videos of food reviews each day "
    "to her channel. She uploaded videos halfway through June, at that pace, "
    "and then doubled the number of video hours she uploaded on the remaining days. "
    "What is her daily upload rate at the end of the month?"
)

FIRST_PERIOD_ONLY_CONFUSER = (
    "Allison, a YouTuber, uploads 10 one-hour videos of food reviews each day "
    "to her channel. She uploaded videos halfway through June, at that pace. "
    "How many video hours did she upload in the first half of the month?"
)

NO_MONTH_CONFUSER = (
    "Allison, a YouTuber, uploads 10 one-hour videos of food reviews each day "
    "to her channel. She uploaded videos halfway through the project, at that pace, "
    "and then doubled the number of video hours she uploaded on the remaining days. "
    "What's the total number of video hours she has uploaded at the end of the month?"
)

VAGUE_MONTH_CONFUSER = (
    "Allison, a YouTuber, uploads 10 one-hour videos of food reviews each day. "
    "She uploaded videos for about a month at that pace. "
    "What's the total number of video hours she has uploaded at the end of the month?"
)

TEMPORAL_TARIFF_0001_SHAPE = (
    "A construction worker who works 8 hours a day and makes $20 per hour "
    "works 5 days a week. If he works more than 8 hours a day he makes time "
    "and a half for every extra hour. Last week he worked 10 hours a day for 5 days. "
    "How much money did he make last week?"
)

TEMPORAL_TARIFF_0017_SHAPE = (
    "Jason has a carriage house that he rents out.  He's charging $50.00 per day "
    "or $500.00 for 14 days.  Eric wants to rent the house for 20 days.  "
    "How much will it cost him?"
)

DURATION_SEGMENT_0015_SHAPE = (
    "A fog bank rolls in from the ocean to cover a city. It takes 10 minutes "
    "to cover every 3 miles of the city. If the city is 42 miles across from "
    "the oceanfront to the opposite inland edge, how long will it take for the "
    "fog bank to cover the whole city?"
)

RATE_CONVERSION_0014_SHAPE = (
    "Bob can shuck 10 oysters in 5 minutes.  How many oysters can he shuck in 2 hours?"
)

MA_0025_SHAPE = (
    "Lilibeth fills 6 baskets where each basket holds 50 strawberries. "
    "She, her brother, and 3 of her friends equally picked strawberries. "
    "How many strawberries did each person pick?"
)

PRESERVED_SOLVED = (
    "0001",
    "0002",
    "0003",
    "0005",
    "0006",
    "0008",
    "0009",
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


class TestClusterContractPolicy:
    def test_civil_month_table_is_deterministic(self) -> None:
        assert CIVIL_MONTH_DAY_COUNT["june"] == 30
        assert CIVIL_MONTH_DAY_COUNT["february"] == 28
        assert len(CIVIL_MONTH_DAY_COUNT) == 12

    def test_june_grounding_provenance(self) -> None:
        grounding = resolve_month_grounding(CASE_0013)
        assert grounding is not None
        assert grounding.month_name == "june"
        assert grounding.day_count == 30
        assert grounding.provenance == PROVENANCE_CALENDAR_TABLE

    def test_february_serving_blocked(self) -> None:
        assert resolve_month_grounding(FEBRUARY_CONFUSER) is None

    def test_halfway_split_requires_even_month(self) -> None:
        assert allows_halfway_split(30) is True
        assert allows_halfway_split(31) is False


class TestTargetCase:
    def test_0013_solves(self) -> None:
        result = parse_and_solve(_load_case("0013"))
        assert result.answer == 450.0
        assert result.refusal_reason is None


class TestSiblingGeneralization:
    def test_september_sibling(self) -> None:
        resolution = compose_piecewise_daily_hours_total(SIBLING_SEPTEMBER)
        assert resolution is not None
        # 6 hrs/day × 15 days + 12 hrs/day × 15 days = 90 + 180 = 270
        assert resolution.answer == 270.0


class TestCalendarConfuserRefusals:
    def test_february_refuses(self) -> None:
        assert compose_piecewise_daily_hours_total(FEBRUARY_CONFUSER) is None

    def test_january_odd_month_refuses(self) -> None:
        assert compose_piecewise_daily_hours_total(JANUARY_ODD_MONTH_CONFUSER) is None

    def test_no_named_month_refuses(self) -> None:
        assert compose_piecewise_daily_hours_total(NO_MONTH_CONFUSER) is None

    def test_vague_month_refuses(self) -> None:
        assert compose_piecewise_daily_hours_total(VAGUE_MONTH_CONFUSER) is None

    def test_asks_daily_rate_refuses(self) -> None:
        assert compose_piecewise_daily_hours_total(ASKS_DAILY_RATE_CONFUSER) is None

    def test_first_period_only_refuses(self) -> None:
        assert compose_piecewise_daily_hours_total(FIRST_PERIOD_ONLY_CONFUSER) is None


class TestNeighborRefusals:
    def test_temporal_tariff_0001_refuses(self) -> None:
        assert compose_piecewise_daily_hours_total(TEMPORAL_TARIFF_0001_SHAPE) is None

    def test_temporal_tariff_0017_refuses(self) -> None:
        assert compose_piecewise_daily_hours_total(TEMPORAL_TARIFF_0017_SHAPE) is None

    def test_duration_segment_0015_refuses(self) -> None:
        assert compose_piecewise_daily_hours_total(DURATION_SEGMENT_0015_SHAPE) is None

    def test_rate_conversion_0014_refuses(self) -> None:
        assert compose_piecewise_daily_hours_total(RATE_CONVERSION_0014_SHAPE) is None

    def test_ma_0025_shape_refuses(self) -> None:
        assert compose_piecewise_daily_hours_total(MA_0025_SHAPE) is None


class TestPromotionBridge:
    def test_resolve_promotable_piecewise(self) -> None:
        assert resolve_promotable_piecewise_daily_hours_total(CASE_0013) is not None


class TestTrainSampleScore:
    def test_wrong_zero_and_fallback_state(self) -> None:
        from evals.gsm8k_math.train_sample.v1.runner import build_report, _load_cases

        report = build_report(_load_cases(_CASES_PATH))
        counts = report["counts"]
        assert counts["wrong"] == 0
        assert counts["correct"] >= 24
        assert counts["refused"] <= 26

    def test_newly_solved_0013(self) -> None:
        from evals.gsm8k_math.train_sample.v1.runner import build_report, _load_cases

        report = build_report(_load_cases(_CASES_PATH))
        correct = {
            row["case_id"].split("-")[-1]
            for row in report["per_case"]
            if row["verdict"] == "correct"
        }
        assert "0013" in correct

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


class TestTemporalRegressions:
    @pytest.mark.parametrize("case_id,expected", [("0001", 990.0), ("0017", 800.0)])
    def test_temporal_tariff_preserved(self, case_id: str, expected: float) -> None:
        result = parse_and_solve(_load_case(case_id))
        assert result.answer == expected
        assert result.refusal_reason is None

    def test_duration_segment_0015_preserved(self) -> None:
        result = parse_and_solve(_load_case("0015"))
        assert result.answer == 38.0
        assert result.refusal_reason is None