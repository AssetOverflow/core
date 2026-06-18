"""Gate A2r/A2s — Capability Paradigm Sprint 12 singleton ClusterContract lift."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from generate.math_candidate_graph import parse_and_solve
from generate.derivation.nested_fraction_remainder_total import (
    compose_nested_fraction_remainder_total,
    resolve_promotable_nested_fraction_remainder_total,
)
from generate.derivation.loose_crayon_box_capacity import (
    compose_loose_crayon_box_capacity,
    resolve_promotable_loose_crayon_box_capacity,
)

_CASES_PATH = (
    Path(__file__).resolve().parents[1]
    / "evals"
    / "gsm8k_math"
    / "train_sample"
    / "v1"
    / "cases.jsonl"
)

CASE_0004 = (
    "There are some kids in camp. Half of the kids are going to soccer camp, "
    "and 1/4 of the kids going to soccer camp are going to soccer camp in the morning. "
    "750 kids are going to soccer camp in the afternoon. "
    "How many kids there in camp altogether?"
)

CASE_0007 = (
    "Francine has five full boxes of crayons and 5 loose crayons, and her friend "
    "has 27 loose crayons. They need to put all of their loose crayons in a box. "
    "How many more boxes do they need if Francine has a total of 85 crayons?"
)

SIBLING_CAMP = (
    "There are some students in camp. Half of the students are going to music camp, "
    "and 1/4 of the students going to music camp are going to music camp in the morning. "
    "600 students are going to music camp in the afternoon. "
    "How many students there in camp altogether?"
)

SIBLING_BOXES = (
    "Jordan has four full boxes of markers and 3 loose markers, and her friend "
    "has 21 loose markers. They need to put all of their loose markers in a box. "
    "How many more boxes do they need if Jordan has a total of 19 markers?"
)

SEALED_ELIMINATION_0026 = (
    "Aaron and his brother Carson each saved up $40 to go to dinner. "
    "The bill is 3/4 of their total money. After, they go out for ice cream. "
    "Each scoop costs $1.5 and they get the same amount as each other. "
    "If they leave with $1 in change each, how many scoops did they each buy?"
)

SEALED_WRONG_0047_SHAPE = (
    "John bakes 12 coconut macaroons, each weighing 5 ounces. "
    "He then packs an equal number of the macaroons in 4 different brown bags, "
    "ready for delivery. When he briefly leaves the kitchen to pick the phone, "
    "his little brother Steve eats the entire contents of one of the brown bags. "
    "What is the total weight, in ounces, of the remaining coconut macaroons?"
)

ASKS_SUBGROUP_ONLY_CONFUSER = (
    "There are some kids in camp. Half of the kids are going to soccer camp, "
    "and 1/4 of the kids going to soccer camp are going to soccer camp in the morning. "
    "750 kids are going to soccer camp in the afternoon. "
    "How many kids are going to soccer camp?"
)

OUTER_CAMP_MISMATCH_CONFUSER = (
    "There are some kids in camp. Half of the kids are going to baseball camp, "
    "and 1/4 of the kids going to soccer camp are going to soccer camp in the morning. "
    "750 kids are going to soccer camp in the afternoon. "
    "How many kids there in camp altogether?"
)

ASKS_PER_BOX_CONFUSER = (
    "Francine has five full boxes of crayons and 5 loose crayons, and her friend "
    "has 27 loose crayons. They need to put all of their loose crayons in a box. "
    "How many crayons are in each full box if Francine has a total of 85 crayons?"
)

BOX_ITEM_MISMATCH_CONFUSER = (
    "Francine has five full boxes of crayons and 5 loose markers, and her friend "
    "has 27 loose markers. They need to put all of their loose markers in a box. "
    "How many more boxes do they need if Francine has a total of 85 markers?"
)

FRIEND_ITEM_MISMATCH_CONFUSER = (
    "Francine has five full boxes of crayons and 5 loose crayons, and her friend "
    "has 27 loose markers. They need to put all of their loose crayons in a box. "
    "How many more boxes do they need if Francine has a total of 85 crayons?"
)

TOTAL_ACTOR_MISMATCH_CONFUSER = (
    "Francine has five full boxes of crayons and 5 loose crayons, and her friend "
    "has 27 loose crayons. They need to put all of their loose crayons in a box. "
    "How many more boxes do they need if Sam has a total of 85 crayons?"
)

MISSING_ALL_LOOSE_ITEM_CONFUSER = (
    "Francine has five full boxes of crayons and 5 loose crayons, and her friend "
    "has 27 loose crayons. They need to put all of their loose things in a box. "
    "How many more boxes do they need if Francine has a total of 85 crayons?"
)

MULTIPLE_FRACTION_CONFUSER = (
    "Half of the kids are going to soccer camp, and 1/4 of the kids going to soccer camp "
    "are going in the morning. 1/2 of the afternoon group brought lunch. "
    "750 kids are going to soccer camp in the afternoon. "
    "How many kids there in camp altogether?"
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
    "0013",
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
    def test_nested_fraction_contract_admits_0004_shape(self) -> None:
        assert compose_nested_fraction_remainder_total(CASE_0004) is not None

    def test_box_capacity_contract_admits_0007_shape(self) -> None:
        assert compose_loose_crayon_box_capacity(CASE_0007) is not None


class TestTargetCases:
    def test_0004_solves(self) -> None:
        result = parse_and_solve(CASE_0004)
        assert result.answer == 2000.0
        assert result.refusal_reason is None

    def test_0007_solves(self) -> None:
        result = parse_and_solve(CASE_0007)
        assert result.answer == 2.0
        assert result.refusal_reason is None


class TestSiblingGeneralization:
    def test_music_camp_sibling(self) -> None:
        resolution = compose_nested_fraction_remainder_total(SIBLING_CAMP)
        assert resolution is not None
        assert resolution.answer == 1600.0

    def test_marker_box_sibling(self) -> None:
        resolution = compose_loose_crayon_box_capacity(SIBLING_BOXES)
        assert resolution is not None
        # (3+21)*4/(19-3) = 96/16 = 6
        assert resolution.answer == 6.0


class TestNeighborConfuserRefusals:
    def test_sealed_elimination_0026_refuses(self) -> None:
        assert compose_nested_fraction_remainder_total(SEALED_ELIMINATION_0026) is None

    def test_dcs_0047_refuses(self) -> None:
        assert compose_loose_crayon_box_capacity(SEALED_WRONG_0047_SHAPE) is None

    def test_asks_subgroup_only_refuses(self) -> None:
        assert compose_nested_fraction_remainder_total(ASKS_SUBGROUP_ONLY_CONFUSER) is None

    def test_outer_camp_mismatch_refuses(self) -> None:
        assert compose_nested_fraction_remainder_total(OUTER_CAMP_MISMATCH_CONFUSER) is None

    def test_asks_per_box_refuses(self) -> None:
        assert compose_loose_crayon_box_capacity(ASKS_PER_BOX_CONFUSER) is None

    def test_box_item_mismatch_refuses(self) -> None:
        assert compose_loose_crayon_box_capacity(BOX_ITEM_MISMATCH_CONFUSER) is None

    def test_friend_item_mismatch_refuses(self) -> None:
        assert compose_loose_crayon_box_capacity(FRIEND_ITEM_MISMATCH_CONFUSER) is None

    def test_total_actor_mismatch_refuses(self) -> None:
        assert compose_loose_crayon_box_capacity(TOTAL_ACTOR_MISMATCH_CONFUSER) is None

    def test_missing_all_loose_item_refuses(self) -> None:
        assert compose_loose_crayon_box_capacity(MISSING_ALL_LOOSE_ITEM_CONFUSER) is None

    def test_multiple_fraction_refuses(self) -> None:
        assert compose_nested_fraction_remainder_total(MULTIPLE_FRACTION_CONFUSER) is None


class TestPromotionBridges:
    def test_resolve_promotable_nested_fraction(self) -> None:
        assert resolve_promotable_nested_fraction_remainder_total(CASE_0004) is not None

    def test_resolve_promotable_box_capacity(self) -> None:
        assert resolve_promotable_loose_crayon_box_capacity(CASE_0007) is not None


class TestTrainSampleScore:
    def test_wrong_zero_and_state_a(self) -> None:
        from evals.gsm8k_math.train_sample.v1.runner import build_report, _load_cases

        report = build_report(_load_cases(_CASES_PATH))
        counts = report["counts"]
        assert counts["wrong"] == 0
        assert counts["correct"] >= 26
        assert counts["refused"] <= 24

    def test_newly_solved_ids(self) -> None:
        from evals.gsm8k_math.train_sample.v1.runner import build_report, _load_cases

        report = build_report(_load_cases(_CASES_PATH))
        correct = {
            row["case_id"].split("-")[-1]
            for row in report["per_case"]
            if row["verdict"] == "correct"
        }
        assert "0004" in correct
        assert "0007" in correct

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


class TestPriorOrganRegressions:
    def test_piecewise_0013_preserved(self) -> None:
        result = parse_and_solve(_load_case("0013"))
        assert result.answer == 450.0
        assert result.refusal_reason is None
