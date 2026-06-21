"""Diagnostic-only contract tests for ``binding.quantity_entity``."""

from __future__ import annotations

import dataclasses

import pytest

import generate.problem_frame_contracts as problem_frame_contracts
from generate.kernel_facts import SourceSpan
from generate.problem_frame import QuantityKindDisposition
from generate.problem_frame_builder import build_problem_frame
from generate.problem_frame_contracts import assess_contracts, assess_quantity_entity


FAMILY_ID = "binding.quantity_entity"
CANDIDATE_ORGAN = "quantity_entity_binding"


def _proposal(frame):
    proposals = tuple(
        proposal
        for proposal in frame.proposals
        if proposal.family_id == FAMILY_ID
    )
    assert len(proposals) == 1
    return proposals[0]


def _assessment(frame):
    assessments = tuple(
        assessment
        for assessment in assess_contracts(frame)
        if assessment.candidate_organ == CANDIDATE_ORGAN
    )
    assert len(assessments) == 1
    return assessments[0]


@pytest.mark.parametrize(
    "problem_text",
    (
        "A school has 100 students.",
        "There are 12 apples in the basket.",
    ),
)
def test_exact_local_count_binding_is_proposed_then_assessed(
    problem_text: str,
) -> None:
    frame = build_problem_frame(problem_text)
    proposal = _proposal(frame)
    assessment = _assessment(frame)

    assert proposal.status == "proposed"
    assert proposal.diagnostic_only is True
    assert proposal.serving_allowed is False
    assert not hasattr(proposal, "runnable")
    assert assessment.runnable is True
    assert assessment.missing_bindings == ()
    assert assessment.unresolved_hazards == ()
    assert len(frame.quantity_kind_dispositions) == 1
    assert frame.quantity_kind_dispositions[0].quantity_kind == "count"
    assert frame.quantity_kind_dispositions[0].unit_mention_id is None
    assert all(
        span.text == problem_text[span.start:span.end]
        for span in (*proposal.evidence_spans, *assessment.evidence_spans)
    )


def test_builder_publishes_quantity_entity_proposal_before_assessment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed_statuses: list[str] = []
    original = problem_frame_contracts.assess_contracts

    def observe(frame):
        observed_statuses.append(_proposal(frame).status)
        return original(frame)

    monkeypatch.setattr(problem_frame_contracts, "assess_contracts", observe)

    frame = build_problem_frame("A school has 100 students.")

    assert observed_statuses == ["proposed"]
    assert _assessment(frame).runnable is True


def test_proposal_free_frame_does_not_dispatch_quantity_entity_contract() -> None:
    frame = build_problem_frame("A school has 100 students.")
    proposal_free = dataclasses.replace(frame, proposals=())

    assert CANDIDATE_ORGAN not in {
        assessment.candidate_organ
        for assessment in assess_contracts(proposal_free)
    }
    assert assess_quantity_entity(proposal_free).runnable is False
    assert (
        "quantity_entity_proposal_required"
        in assess_quantity_entity(proposal_free).missing_bindings
    )


@pytest.mark.parametrize(
    "problem_text",
    (
        "There are 12.",
        "Students wait in the hall.",
        "There are 12 apples and oranges.",
        "There are 12 and 13 apples.",
        "A school has 20% of the students.",
        "A basket holds 3 apples per child.",
        "There are 3 more than 2 apples.",
        "Tom gave Ana 3 marbles.",
        "There are 12 of them.",
        "There are 12. Apples fill the basket.",
        "There are 12 apples, oranges, and pears.",
    ),
)
def test_confusers_do_not_dispatch_quantity_entity(problem_text: str) -> None:
    frame = build_problem_frame(problem_text)

    assert FAMILY_ID not in {proposal.family_id for proposal in frame.proposals}
    assert CANDIDATE_ORGAN not in {
        assessment.candidate_organ
        for assessment in assess_contracts(frame)
    }


def test_state_change_surface_does_not_backdoor_foundational_families() -> None:
    frame = build_problem_frame("Tom gave Ana 3 marbles.")

    assert FAMILY_ID not in {proposal.family_id for proposal in frame.proposals}
    assert "state_change.transition" not in {
        proposal.family_id for proposal in frame.proposals
    }


def test_unit_entity_span_conflict_refuses_measurement_claim() -> None:
    frame = build_problem_frame("The tank has 84 degrees.")
    assessment = _assessment(frame)

    assert assessment.runnable is False
    assert "quantity_kind_unresolved" in assessment.missing_bindings
    assert "unit_kind_conflict" in assessment.missing_bindings


def test_synthetic_or_text_mismatched_proposal_evidence_refuses() -> None:
    frame = build_problem_frame("A school has 100 students.")
    proposal = _proposal(frame)
    synthetic = SourceSpan("synthetic", 0, 9)
    frame = dataclasses.replace(
        frame,
        proposals=(dataclasses.replace(proposal, evidence_spans=(synthetic,)),),
    )

    assessment = assess_quantity_entity(frame)

    assert assessment.runnable is False
    assert "provenance_span_inexact" in assessment.missing_bindings


def test_quantity_kind_disposition_rejects_illegal_unit_states() -> None:
    span = SourceSpan("12", 0, 2)

    with pytest.raises(ValueError, match="count.*must not carry a unit"):
        QuantityKindDisposition(
            "quantity",
            "entity",
            "count",
            "unit",
            (span,),
        )
    with pytest.raises(ValueError, match="measurement.*require a unit"):
        QuantityKindDisposition(
            "quantity",
            "entity",
            "measurement",
            None,
            (span,),
        )


def test_quantity_entity_replay_is_deterministic() -> None:
    problem_text = "A school has 100 students."

    first = build_problem_frame(problem_text)
    second = build_problem_frame(problem_text)

    assert first.proposals == second.proposals
    assert first.bindings == second.bindings
    assert first.quantity_kind_dispositions == second.quantity_kind_dispositions
    assert assess_contracts(first) == assess_contracts(second)


def test_existing_proposal_first_families_do_not_gain_quantity_entity_dispatch() -> None:
    percent_partition = (
        "A school has 100 students. Half of the students are girls, the other half are boys. "
        "20% of the girls have dogs and 10% of the boys have dogs. "
        "How many students own dogs?"
    )
    fraction_decrease = (
        "A tank's temperature will decrease to 3/4 of its current temperature. "
        "If the current temperature is 84 degrees, how many degrees will it decrease by?"
    )

    for problem_text in (percent_partition, fraction_decrease):
        frame = build_problem_frame(problem_text)
        assert FAMILY_ID not in {proposal.family_id for proposal in frame.proposals}
        assert CANDIDATE_ORGAN not in {
            assessment.candidate_organ
            for assessment in assess_contracts(frame)
        }