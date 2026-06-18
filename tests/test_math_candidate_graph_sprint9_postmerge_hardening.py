"""Post-merge wrong=0 hardening for Sprint 9 Gates A2m/A2n (#820)."""

from __future__ import annotations

from generate.math_candidate_graph import parse_and_solve
from generate.derivation.affine_fraction_delta import (
    compose_affine_fraction_delta,
    resolve_promotable_affine_fraction_delta,
)
from generate.derivation.temporal_tariff import (
    compose_bundle_overflow_tariff,
    compose_overtime_shift_earnings,
    compose_temporal_tariff,
    resolve_promotable_temporal_tariff,
)
from generate.derivation.percent_partition import (
    compose_percent_partition,
    resolve_promotable_percent_partition,
)

_AFFINE_BODY = (
    "Yun had 20 paperclips initially, but then lost 12. Marion has 1/4 more than what "
    "Yun currently has, plus 7."
)

_OVERTIME_BODY = (
    "Tina makes $18.00 an hour. If she works more than 8 hours per shift, she is "
    "eligible for overtime, which is paid by your hourly wage + 1/2 your hourly wage. "
    "If she works 10 hours every day for 5 days,"
)

_BUNDLE_BODY = (
    "Jason has a carriage house that he rents out. He's charging $50.00 per day or "
    "$500.00 for 14 days. Eric wants to rent the house for 20 days."
)

_PERCENT_GROUP_OF_100 = (
    "A group of 100 students. Half of the students are girls, the other half are boys. "
    "20% of the girls have dogs and 10% of the boys have dogs. "
    "How many students own dogs?"
)

_PERCENT_SUBGROUP_CONFUSER = (
    "Half of the students are girls, the other half are boys. The girls group has 50 students. "
    "20% of the girls have dogs and 10% of the boys have dogs. How many students own dogs?"
)


def _run(text: str):
    return parse_and_solve(text, sealed=False)


class TestAffineSubjectBinding:
    def test_question_subject_mismatch_refuses(self):
        text = f"{_AFFINE_BODY} How many paperclips does Alice have?"
        assert resolve_promotable_affine_fraction_delta(text) is None
        assert _run(text).answer is None

    def test_question_reference_subject_refuses(self):
        text = f"{_AFFINE_BODY} How many paperclips does Yun have?"
        assert resolve_promotable_affine_fraction_delta(text) is None
        assert _run(text).answer is None


class TestAffineCompletenessGuard:
    def test_duplicate_offset_distractor_refuses(self):
        text = (
            "Yun had 20 paperclips initially, but then lost 12. There are 7 boxes on the shelf. "
            "Marion has 1/4 more than what Yun currently has, plus 7. "
            "How many paperclips does Marion have?"
        )
        assert compose_affine_fraction_delta(text) is None
        assert _run(text).answer is None


class TestTemporalActorBinding:
    def test_overtime_question_actor_mismatch_refuses(self):
        text = f"{_OVERTIME_BODY} how much money does Bob make?"
        assert resolve_promotable_temporal_tariff(text) is None
        assert _run(text).answer is None

    def test_bundle_question_renter_mismatch_refuses(self):
        text = f"{_BUNDLE_BODY} What does it cost Alice?"
        assert resolve_promotable_temporal_tariff(text) is None
        assert _run(text).answer is None


class TestTemporalThresholdAnchoring:
    def test_non_shift_threshold_refuses(self):
        text = (
            "Tina makes $18.00 an hour. If she works more than 8 hours per week, she is "
            "eligible for overtime, which is paid by your hourly wage + 1/2 your hourly wage. "
            "If she works 10 hours every day for 5 days, how much money does she make?"
        )
        assert compose_overtime_shift_earnings(text) is None
        assert _run(text).answer is None


class TestTemporalRentalVerbVariants:
    def test_rented_still_admits(self):
        text = (
            "Jason has a carriage house that he rents out. He's charging $50.00 per day or "
            "$500.00 for 14 days. Eric rented the house for 20 days. "
            "How much will it cost him?"
        )
        res = compose_bundle_overflow_tariff(text)
        assert res is not None
        assert res.answer == 800.0

    def test_renting_still_admits(self):
        text = (
            "Jason has a carriage house that he rents out. He's charging $50.00 per day or "
            "$500.00 for 14 days. Eric is renting the house for 20 days. "
            "How much will it cost him?"
        )
        res = compose_bundle_overflow_tariff(text)
        assert res is not None
        assert res.answer == 800.0


class TestTemporalQuestionRobustness:
    def test_how_much_does_she_earn_admits(self):
        text = f"{_OVERTIME_BODY} how much does she earn?"
        res = compose_overtime_shift_earnings(text)
        assert res is not None
        assert res.answer == 990.0

    def test_what_is_total_cost_admits(self):
        text = f"{_BUNDLE_BODY} What is the total cost?"
        res = compose_bundle_overflow_tariff(text)
        assert res is not None
        assert res.answer == 800.0


class TestPercentPartitionGroupOf:
    def test_group_of_total_still_admits(self):
        res = compose_percent_partition(_PERCENT_GROUP_OF_100)
        assert res is not None
        assert res.answer == 15.0
        assert _run(_PERCENT_GROUP_OF_100).answer == 15.0

    def test_subgroup_group_still_refuses(self):
        assert resolve_promotable_percent_partition(_PERCENT_SUBGROUP_CONFUSER) is None
        assert _run(_PERCENT_SUBGROUP_CONFUSER).answer is None