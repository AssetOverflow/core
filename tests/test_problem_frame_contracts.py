from generate.problem_frame_builder import build_problem_frame
from generate.problem_frame_contracts import assess_percent_partition


def test_percent_partition_missing_bindings_is_not_runnable() -> None:
    assessment = assess_percent_partition(build_problem_frame("Mia spent 50% of her money."))
    assert not assessment.runnable
    assert "grounded_whole_entity" in assessment.missing_bindings
    assert "grounded_question_target" in assessment.missing_bindings


def test_tightly_grounded_percent_partition_is_diagnostically_runnable() -> None:
    frame = build_problem_frame(
        "There are 100 students. Half are girls. 30% of the girls own pets. "
        "How many students own pets?"
    )
    assessment = assess_percent_partition(frame)
    assert assessment.runnable
    assert assessment.missing_bindings == ()
    assert assessment.evidence_spans
