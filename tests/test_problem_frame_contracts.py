from generate.problem_frame_builder import build_problem_frame
from generate.problem_frame_contracts import assess_contracts, assess_fraction_decrease, assess_percent_partition


FRACTION_DECREASE_CASE = (
    "In one hour, Addison mountain's temperature will decrease to 3/4  of its temperature. "
    "If the current temperature of the mountain is 84 degrees, what will the temperature "
    "decrease by?"
)

FRACTION_DECREASE_SIBLING = (
    "In two hours, Cedar peak's temperature will decrease to 2/3 of its temperature. "
    "If the current temperature of the peak is 60 degrees, what will the temperature "
    "decrease by?"
)

FINAL_VALUE_CONFUSER = (
    "In one hour, the lake's temperature will decrease to 3/4 of its temperature. "
    "If the current temperature of the lake is 80 degrees, what will the temperature be?"
)

AFFINE_CONFUSER = (
    "Yun had 20 paperclips initially, but then lost 12. Marion has 1/4 more than what "
    "Yun currently has, plus 7. How many paperclips does Marion have?"
)

MULTIPLE_FRACTION_CONFUSER = (
    "The reactor's temperature will decrease to 3/4 of its temperature and later decrease "
    "to 1/2 of its temperature. If the current temperature is 80 degrees, what will the "
    "temperature decrease by?"
)

PERCENT_PARTITION_CASE = (
    "A school has 100 students. Half of the students are girls, the other half are boys.  "
    "20% of the girls have dogs at home and 10% of the boys have dogs at home.  "
    "How many students own dogs?"
)

ONE_SUBGROUP_CONFUSER = (
    "There are 100 students. Half are girls. 30% of the girls own pets. "
    "How many students own pets?"
)

UNEQUAL_PARTITION_CONFUSER = (
    "A school has 100 students. 60 of the students are girls and 40 are boys. "
    "20% of the girls have dogs and 10% of the boys have dogs. "
    "How many students own dogs?"
)

INVERSE_REMAINING_CONFUSER = (
    "Yvonne brings a box of chocolates to school. Half have nuts and half do not. "
    "The students eat 80% of the ones with nuts and eat half of the ones without nuts. "
    "If there are 28 chocolates left, how many chocolates were in the box?"
)


def test_fraction_decrease_contract_is_runnable_from_problemframe() -> None:
    assessment = assess_fraction_decrease(build_problem_frame(FRACTION_DECREASE_CASE))
    assert assessment.runnable
    assert assessment.missing_bindings == ()
    assert assessment.evidence_spans


def test_fraction_decrease_sibling_is_runnable() -> None:
    assessment = assess_fraction_decrease(build_problem_frame(FRACTION_DECREASE_SIBLING))
    assert assessment.runnable


def test_final_value_question_is_not_delta_runnable() -> None:
    assessment = assess_fraction_decrease(build_problem_frame(FINAL_VALUE_CONFUSER))
    assert not assessment.runnable
    assert "delta_decrease_target_unbound" in assessment.missing_bindings


def test_affine_more_than_fraction_is_not_change_runnable() -> None:
    assessments = assess_contracts(build_problem_frame(AFFINE_CONFUSER))
    assert not any(item.candidate_organ == "fraction_decrease" for item in assessments)


def test_multiple_fraction_or_base_candidates_refuse_readiness() -> None:
    assessments = assess_contracts(build_problem_frame(MULTIPLE_FRACTION_CONFUSER))
    assert not any(item.candidate_organ == "fraction_decrease" and item.runnable for item in assessments)


def test_tightly_grounded_percent_partition_is_diagnostically_runnable() -> None:
    assessment = assess_percent_partition(build_problem_frame(PERCENT_PARTITION_CASE))
    assert assessment.runnable
    assert assessment.missing_bindings == ()
    assert assessment.evidence_spans


def test_percent_partition_requires_two_complementary_subgroups() -> None:
    assessment = assess_percent_partition(build_problem_frame(ONE_SUBGROUP_CONFUSER))
    assert not assessment.runnable
    assert "partition_subgroups_not_distinct" in assessment.missing_bindings
    assert "percent_subgroup_links_incomplete" in assessment.missing_bindings


def test_inverse_remaining_percent_case_is_not_runnable() -> None:
    assessment = assess_percent_partition(build_problem_frame(INVERSE_REMAINING_CONFUSER))
    assert not assessment.runnable
    assert "inverse_topology_unlicensed" in assessment.missing_bindings
    assert "original_whole_unbound" in assessment.missing_bindings


def test_unequal_partition_confuser_is_not_runnable() -> None:
    assessment = assess_percent_partition(build_problem_frame(UNEQUAL_PARTITION_CONFUSER))
    assert not assessment.runnable
    assert "partition_subgroups_not_distinct" in assessment.missing_bindings or "percent_subgroup_links_incomplete" in assessment.missing_bindings
