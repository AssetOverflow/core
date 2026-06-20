"""Tests for feat(kernel): route proportional-decrease through construction proposals."""
from __future__ import annotations

from generate.problem_frame_builder import build_problem_frame
from generate.construction_affordances import lookup_family


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


def test_proposal_trace_exists_for_decrease_to_fraction() -> None:
    frame = build_problem_frame(FRACTION_DECREASE_CASE)
    proposals = [p for p in frame.proposals if p.family_id == "proportional_change.decrease_to_fraction"]
    assert len(proposals) == 1
    
    proposal = proposals[0]
    assert proposal.relation_type == "decrease_to_fraction"
    assert proposal.candidate_organ == "fraction_decrease"
    assert proposal.status == "closed"


def test_proposal_trace_includes_exact_evidence_span() -> None:
    frame = build_problem_frame(FRACTION_DECREASE_CASE)
    proposal = next(p for p in frame.proposals if p.family_id == "proportional_change.decrease_to_fraction")
    
    # Verify evidence spans slice the original text exactly
    for span in proposal.evidence_spans:
        assert FRACTION_DECREASE_CASE[span.start:span.end] == span.text

    # Verify key tokens/spans are present in the evidence
    evidence_texts = {span.text for span in proposal.evidence_spans}
    assert "decrease to" in evidence_texts
    assert "3/4" in evidence_texts
    assert "84" in evidence_texts
    assert "temperature" in evidence_texts


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


def test_blocked_final_value_proportional_case_produces_proposal_but_remains_blocked() -> None:
    frame = build_problem_frame(FINAL_VALUE_CONFUSER)
    proposals = [p for p in frame.proposals if p.family_id == "proportional_change.decrease_to_fraction"]
    assert len(proposals) == 1
    
    proposal = proposals[0]
    # The final value question target is not a delta/decrease target, so contract is not runnable
    assert proposal.status != "closed"
    assert "delta_decrease_target_unbound" in proposal.missing_roles


def test_no_proposal_trace_for_affine_more_than_confuser() -> None:
    frame = build_problem_frame(AFFINE_CONFUSER)
    proposals = [p for p in frame.proposals if p.family_id == "proportional_change.decrease_to_fraction"]
    assert len(proposals) == 0
