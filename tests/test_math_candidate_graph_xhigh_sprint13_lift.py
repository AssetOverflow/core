"""Sprint 13 contract-backed capability bundle.

The tests are the serving license.  They pin four target chains while proving
that the selected organs remain inert on sealed-wrong, blocked-family, changed
binding, and permanent composition-validation surfaces.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from generate.derivation.bounded_rate_projection import (
    build_bounded_rate_projection,
    compose_bounded_rate_projection,
    resolve_promotable_bounded_rate_projection,
)
from generate.derivation.closed_reference_affine_aggregate import (
    build_closed_reference_affine_aggregate,
    compose_closed_reference_affine_aggregate,
    resolve_promotable_closed_reference_affine_aggregate,
)
from generate.math_candidate_graph import parse_and_solve


_ROOT = Path(__file__).resolve().parents[1]
_TRAIN_PATH = _ROOT / "evals/gsm8k_math/train_sample/v1/cases.jsonl"
_CV_PATH = _ROOT / "evals/gsm8k_math/composition_validation/v1/cases.jsonl"


def _load_train() -> dict[str, str]:
    result: dict[str, str] = {}
    for line in _TRAIN_PATH.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        result[row["case_id"].split("-")[-1]] = row["question"]
    return result


CASES = _load_train()
PRESERVED_SOLVED = {
    "0001", "0002", "0003", "0004", "0005", "0006", "0007", "0008",
    "0009", "0010", "0013", "0014", "0015", "0017", "0018", "0021",
    "0024", "0025", "0029", "0030", "0035", "0037", "0038", "0042",
    "0045", "0046",
}


class TestBoundedRateProjectionTargets:
    @pytest.mark.parametrize(("case_id", "answer"), [("0016", 2.0), ("0034", 112.0)])
    def test_target_build_compose_and_promote(self, case_id: str, answer: float) -> None:
        text = CASES[case_id]
        built = build_bounded_rate_projection(text)
        assert built is not None
        assert built.derivation.answer == pytest.approx(answer)
        assert compose_bounded_rate_projection(text).answer == pytest.approx(answer)
        assert resolve_promotable_bounded_rate_projection(text).answer == pytest.approx(answer)
        assert parse_and_solve(text).answer == pytest.approx(answer)

    @pytest.mark.parametrize(
        ("text", "answer"),
        [
            (
                "On Mira's bicycle trip across town, she traveled 4 more than 8 "
                "kilometers and encountered 6 less than 30 traffic lights. How many "
                "traffic lights per kilometer did Mira encounter on her trip across town?",
                2.0,
            ),
            (
                "Amira is a varsity player on a football team. She can run 60 meters "
                "within 6 seconds. If she can improve her speed by twenty percent, how "
                "many meters will she be able to run within 12 seconds?",
                144.0,
            ),
        ],
    )
    def test_sibling_generality(self, text: str, answer: float) -> None:
        assert resolve_promotable_bounded_rate_projection(text).answer == pytest.approx(answer)

    @pytest.mark.parametrize("case_id", ["0018", "0019", "0028", "0032", "0047"])
    def test_sealed_wrong_neighbors_refuse(self, case_id: str) -> None:
        assert resolve_promotable_bounded_rate_projection(CASES[case_id]) is None

    @pytest.mark.parametrize("case_id", ["0027", "0039"])
    def test_cross_family_refuses(self, case_id: str) -> None:
        assert resolve_promotable_bounded_rate_projection(CASES[case_id]) is None

    @pytest.mark.parametrize(
        "text",
        [
            CASES["0016"].replace("did Rudolph encounter", "did Marco encounter"),
            CASES["0016"].replace("stop signs per mile", "miles per stop sign"),
            CASES["0016"].replace("per mile", "per hour"),
            CASES["0016"].replace(
                "How many stop signs", "He passed 9 billboards. How many stop signs"
            ),
            CASES["0034"].replace("will he be able", "will Taylor be able"),
            CASES["0034"].replace("how many yards", "what speed"),
            CASES["0034"].replace("how many yards", "how many meters"),
            CASES["0034"].replace(
                "how many yards", "he rested for 7 seconds. how many yards"
            ),
            (
                "Rudolph counted 2 blue signs, 5 miles, 3 red signs, and 17 cones. "
                "How many stop signs per mile did Rudolph encounter?"
            ),
        ],
    )
    def test_binding_target_unit_and_completeness_confusers_refuse(self, text: str) -> None:
        assert resolve_promotable_bounded_rate_projection(text) is None

    @pytest.mark.parametrize(
        "text",
        [
            CASES["0016"].replace(
                "traveled 2 more than 5 miles",
                "traveled for half an hour",
            ),
            CASES["0016"].replace(
                "encountered 3 less than 17 stop signs",
                "spent a quarter on tolls and encountered 3 less than 17 stop signs",
            ),
            CASES["0034"].replace(
                "forty percent",
                "a third percent",
            ),
            CASES["0034"].replace(
                "forty percent",
                "one quarter percent",
            ),
        ],
    )
    def test_fraction_word_and_nonlicensed_percent_confusers_refuse(self, text: str) -> None:
        assert resolve_promotable_bounded_rate_projection(text) is None

    def test_affine_rate_completeness_refuses_extra_distance_obligation(self) -> None:
        """Non-vacuous: an extra mile quantity the regex binds must refuse."""
        text = (
            "On Rudolph's car trip across town, he traveled 2 more than 5 miles "
            "and also 9 more than 1 miles and encountered 3 less than 17 stop signs. "
            "How many stop signs per mile did Rudolph encounter on his trip across town?"
        )
        assert resolve_promotable_bounded_rate_projection(text) is None


class TestClosedReferenceAffineAggregateTargets:
    @pytest.mark.parametrize(("case_id", "answer"), [("0027", 3840.0), ("0039", 20.0)])
    def test_target_build_compose_and_promote(self, case_id: str, answer: float) -> None:
        text = CASES[case_id]
        built = build_closed_reference_affine_aggregate(text)
        assert built is not None
        assert built.derivation.answer == pytest.approx(answer)
        assert compose_closed_reference_affine_aggregate(text).answer == pytest.approx(answer)
        assert resolve_promotable_closed_reference_affine_aggregate(text).answer == pytest.approx(answer)
        assert parse_and_solve(text).answer == pytest.approx(answer)

    @pytest.mark.parametrize(
        ("text", "answer"),
        [
            (
                "Lena has 100 followers on Instagram and 300 followers on Facebook. "
                "The number of followers she has on Twitter is half the number of "
                "followers she has on Instagram and Facebook combined. Meanwhile, the "
                "number of followers she has on TikTok is 2 times the number of followers "
                "she has on Twitter, and she has 50 more followers on Youtube than she "
                "has on TikTok. How many followers does Lena have on all her social media?",
                1450.0,
            ),
            (
                "At the family reunion, everyone ate too much food and gained weight. "
                "Ava gained 6 pounds. Ben gained four pounds more than twice what Ava "
                "gained. Cara gained 2 pounds less than half of what Ben gained. How much "
                "weight, in pounds, did the three family members gain at their reunion?",
                28.0,
            ),
        ],
    )
    def test_sibling_generality(self, text: str, answer: float) -> None:
        assert resolve_promotable_closed_reference_affine_aggregate(text).answer == pytest.approx(answer)

    @pytest.mark.parametrize("case_id", ["0023", "0025", "0032", "0033", "0040", "0047"])
    def test_blocked_and_sealed_neighbors_refuse(self, case_id: str) -> None:
        assert resolve_promotable_closed_reference_affine_aggregate(CASES[case_id]) is None

    @pytest.mark.parametrize("case_id", ["0016", "0034"])
    def test_cross_family_refuses(self, case_id: str) -> None:
        assert resolve_promotable_closed_reference_affine_aggregate(CASES[case_id]) is None

    @pytest.mark.parametrize(
        "text",
        [
            CASES["0027"].replace("than he has on TikTok", "than he has on LinkedIn"),
            CASES["0027"].replace("all his social media", "TikTok"),
            CASES["0027"].replace("How many followers", "How many likes"),
            CASES["0027"].replace(
                "How many followers", "He has 9 followers on Mastodon. How many followers"
            ),
            CASES["0039"].replace("what Orlando gained", "what Xavier gained"),
            CASES["0039"].replace("the three family members", "Jose"),
            CASES["0039"].replace("in pounds", "in years"),
            CASES["0039"].replace(
                "How much weight", "Maria gained 7 pounds. How much weight"
            ),
            (
                "Malcolm listed 240 blue cards, 500 green cards, 3 red cards, and 510 "
                "yellow cards. How many followers does Malcolm have on all his social media?"
            ),
        ],
    )
    def test_reference_target_unit_and_completeness_confusers_refuse(self, text: str) -> None:
        assert resolve_promotable_closed_reference_affine_aggregate(text) is None

    @pytest.mark.parametrize(
        "text",
        [
            CASES["0027"].replace(
                "half the number of followers he has on Instagram and Facebook combined",
                "a third the number of followers he has on Instagram and Facebook combined",
            ),
            CASES["0027"].replace(
                "half the number of followers he has on Instagram and Facebook combined",
                "one quarter the number of followers he has on Instagram and Facebook combined",
            ),
            CASES["0027"].replace(
                "half the number of followers he has on Instagram and Facebook combined",
                "three quarters the number of followers he has on Instagram and Facebook combined",
            ),
            CASES["0039"].replace(
                "half of what Jose gained",
                "a quarter of what Jose gained",
            ),
            CASES["0039"].replace(
                "twice what Orlando gained",
                "three times what Orlando gained",
            ),
        ],
    )
    def test_fraction_word_and_nonlicensed_comparative_confusers_refuse(self, text: str) -> None:
        assert resolve_promotable_closed_reference_affine_aggregate(text) is None

    def test_weight_completeness_refuses_extra_actor_obligation(self) -> None:
        """Non-vacuous: an extra named actor gain in the same family must refuse."""
        text = (
            "At the family reunion, everyone ate too much food and gained weight. "
            "Orlando gained 5 pounds. Jose gained two pounds more than twice what "
            "Orlando gained. Maria gained 7 pounds. Fernando gained 3 pounds less than "
            "half of what Jose gained. How much weight, in pounds, did the three family "
            "members gain at their reunion?"
        )
        assert resolve_promotable_closed_reference_affine_aggregate(text) is None


def test_permanent_composition_guards_remain_refused() -> None:
    for line in _CV_PATH.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        if row["gate"] == "permanent":
            assert parse_and_solve(row["question"]).answer is None, row["case_id"]


class TestScoreAndHoldout:
    def test_train_sample_legendary_state_and_preservation(self) -> None:
        from evals.gsm8k_math.train_sample.v1.runner import _load_cases, build_report

        report = build_report(_load_cases(_TRAIN_PATH))
        counts = report["counts"]
        assert counts == {"correct": 30, "wrong": 0, "refused": 20}
        correct = {
            row["case_id"].split("-")[-1]
            for row in report["per_case"]
            if row["verdict"] == "correct"
        }
        assert PRESERVED_SOLVED <= correct
        assert {"0016", "0027", "0034", "0039"} <= correct

    def test_holdout_wrong_zero(self) -> None:
        from evals.gsm8k_math.holdout_dev.v1.runner import build_report

        report = build_report()
        assert report["counts"]["wrong"] == 0
