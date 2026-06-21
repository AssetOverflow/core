"""Tests for feat(kernel): route proportional-decrease through construction proposals."""
from __future__ import annotations

import dataclasses

import generate.problem_frame_builder as problem_frame_builder
import generate.problem_frame_contracts as problem_frame_contracts
from generate.problem_frame_builder import build_problem_frame
from generate.construction_affordances import lookup_family
from generate.problem_frame_contracts import assess_contracts


FRACTION_DECREASE_CASE = (
    "In one hour, Addison mountain's temperature will decrease to 3/4  of its temperature. "
    "If the current temperature of the mountain is 84 degrees, what will the temperature "
    "decrease by?"
)

FINAL_VALUE_CONFUSER = (
    "In one hour, the lake's temperature will decrease to 3/4 of its temperature. "
    "If the current temperature of the lake is 80 degrees, what will the temperature be?"
)

AFFINE_CONFUSER = (
    "Marion has 1/4 more than what Yun currently has, plus 7. How many paperclips does Marion have?"
)

MULTIPLE_FRACTION_CONFUSER = (
    "The reactor's temperature will decrease to 3/4 of its temperature and later decrease "
    "to 1/2 of its temperature. If the current temperature is 80 degrees, what will the "
    "temperature decrease by?"
)


def test_proposal_precedes_role_binding_and_contract_assessment(monkeypatch) -> None:
    events: list[str] = []
    original_propose = problem_frame_builder.propose_construction
    original_assess = problem_frame_contracts.assess_contracts

    def observe_proposal(*args, **kwargs):
        events.append("proposal")
        return original_propose(*args, **kwargs)

    def observe_assessment(frame):
        events.append("assessment")
        proposal = next(
            item
            for item in frame.proposals
            if item.family_id == "proportional_change.decrease_to_fraction"
        )
        assert proposal.status == "proposed"
        return original_assess(frame)

    monkeypatch.setattr(problem_frame_builder, "propose_construction", observe_proposal)
    monkeypatch.setattr(problem_frame_contracts, "assess_contracts", observe_assessment)

    frame = build_problem_frame(FRACTION_DECREASE_CASE)

    assert events == ["proposal", "assessment"]
    assert any(
        relation.relation_type == "decrease_to_fraction"
        for relation in frame.bound_relations
    )


def test_proposal_trace_exists_for_decrease_to_fraction() -> None:
    frame = build_problem_frame(FRACTION_DECREASE_CASE)
    proposals = [p for p in frame.proposals if p.family_id == "proportional_change.decrease_to_fraction"]
    assert len(proposals) == 1
    
    proposal = proposals[0]
    assert proposal.relation_type == "decrease_to_fraction"
    assert proposal.candidate_organ == "fraction_decrease"
    assert proposal.status == "proposed"
    assert proposal.missing_roles == ()
    assert proposal.active_hazards == ()
    assert {role.role for role in proposal.role_obligations if role.required} == {
        "base_quantity",
        "scale",
        "state_entity",
        "transition",
    }


def test_proposal_trace_includes_exact_evidence_span() -> None:
    frame = build_problem_frame(FRACTION_DECREASE_CASE)
    proposal = next(p for p in frame.proposals if p.family_id == "proportional_change.decrease_to_fraction")
    
    # Verify evidence spans slice the original text exactly
    for span in proposal.evidence_spans:
        assert FRACTION_DECREASE_CASE[span.start:span.end] == span.text

    assert len(proposal.evidence_spans) == 1
    assert proposal.evidence_spans[0].text == "decrease to 3/4  of"


def test_proposal_family_is_catalog_backed() -> None:
    frame = build_problem_frame(FRACTION_DECREASE_CASE)
    proposal = next(p for p in frame.proposals if p.family_id == "proportional_change.decrease_to_fraction")
    
    # Use public catalog accessor to look up the family
    family = lookup_family(proposal.family_id)
    assert family is not None
    assert family.family_id == "proportional_change.decrease_to_fraction"
    assert family.signature.relation_type == proposal.relation_type
    assert family.signature.candidate_organ == proposal.candidate_organ


def test_proposal_is_diagnostic_only_serving_disallowed() -> None:
    frame = build_problem_frame(FRACTION_DECREASE_CASE)
    proposal = next(p for p in frame.proposals if p.family_id == "proportional_change.decrease_to_fraction")
    
    family = lookup_family(proposal.family_id)
    assert family is not None
    assert family.diagnostic_only is True
    assert family.serving_allowed is False
    assert proposal.diagnostic_only is True
    assert proposal.serving_allowed is False


def test_blocked_final_value_proportional_case_produces_proposal_but_remains_blocked() -> None:
    frame = build_problem_frame(FINAL_VALUE_CONFUSER)
    proposals = [p for p in frame.proposals if p.family_id == "proportional_change.decrease_to_fraction"]
    assert len(proposals) == 1
    
    proposal = proposals[0]
    assessment = next(
        item for item in assess_contracts(frame)
        if item.candidate_organ == "fraction_decrease"
    )

    # The proposal remains a hypothesis; ContractAssessment alone determines closure.
    assert proposal.status == "proposed"
    assert not assessment.runnable
    assert "delta_decrease_target_unbound" in assessment.missing_bindings


def test_no_proposal_trace_for_affine_more_than_confuser() -> None:
    frame = build_problem_frame(AFFINE_CONFUSER)
    proposals = [p for p in frame.proposals if p.family_id == "proportional_change.decrease_to_fraction"]
    assert len(proposals) == 0


def test_multiple_fraction_confuser_is_not_proposed_or_assessed() -> None:
    frame = build_problem_frame(MULTIPLE_FRACTION_CONFUSER)

    assert not any(
        proposal.family_id == "proportional_change.decrease_to_fraction"
        for proposal in frame.proposals
    )
    assert not any(
        assessment.candidate_organ == "fraction_decrease"
        for assessment in assess_contracts(frame)
    )


def test_fraction_contract_dispatch_requires_the_proposal_first_trace() -> None:
    frame = build_problem_frame(FRACTION_DECREASE_CASE)
    relation_only_frame = dataclasses.replace(frame, proposals=())

    assert any(
        relation.relation_type == "decrease_to_fraction"
        for relation in relation_only_frame.bound_relations
    )
    assert not any(
        assessment.candidate_organ == "fraction_decrease"
        for assessment in assess_contracts(relation_only_frame)
    )
