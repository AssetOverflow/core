"""Percent-partition proposal-first construction seam tests."""

from __future__ import annotations

import dataclasses

import generate.construction_affordances as construction_affordances
import generate.problem_frame_builder as problem_frame_builder
import generate.problem_frame_contracts as problem_frame_contracts
from generate.problem_frame_builder import build_problem_frame
from generate.problem_frame_contracts import assess_contracts


PERCENT_PARTITION_CASE = (
    "A school has 100 students. Half of the students are girls, the other half are boys.  "
    "20% of the girls have dogs at home and 10% of the boys have dogs at home.  "
    "How many students own dogs?"
)

ONE_SUBGROUP_CONFUSER = (
    "There are 100 students. Half are girls. 30% of the girls own pets. "
    "How many students own pets?"
)

PERCENT_CHANGE_CONFUSER = "A store spent 20% of its budget. How many dollars remain?"


def _percent_partition_proposal(frame):
    return next(
        proposal
        for proposal in frame.proposals
        if proposal.family_id == "partition.percent_partition"
    )


def _percent_partition_assessment(frame):
    return next(
        assessment
        for assessment in assess_contracts(frame)
        if assessment.candidate_organ == "percent_partition"
    )


def test_supported_case_has_diagnostic_catalog_proposal() -> None:
    proposal = _percent_partition_proposal(build_problem_frame(PERCENT_PARTITION_CASE))

    assert proposal.status == "proposed"
    assert proposal.diagnostic_only is True
    assert proposal.serving_allowed is False
    assert {role.role for role in proposal.role_obligations if role.required} == {
        "whole",
        "part",
        "scale",
    }
    assert tuple(span.text for span in proposal.evidence_spans) == (
        "20% of",
        "10% of",
    )
    assert all(
        PERCENT_PARTITION_CASE[span.start : span.end] == span.text
        for span in proposal.evidence_spans
    )


def test_proposal_precedes_role_binding_and_contract_assessment(monkeypatch) -> None:
    events: list[str] = []
    original_propose = problem_frame_builder.propose_construction
    original_assess = problem_frame_contracts.assess_contracts

    def observe_proposal(*args, **kwargs):
        proposal = original_propose(*args, **kwargs)
        if proposal.family_id == "partition.percent_partition":
            events.append("proposal")
        return proposal

    def observe_assessment(frame):
        events.append("assessment")
        assert _percent_partition_proposal(frame).status == "proposed"
        assert frame.bound_relations
        return original_assess(frame)

    monkeypatch.setattr(problem_frame_builder, "propose_construction", observe_proposal)
    monkeypatch.setattr(problem_frame_contracts, "assess_contracts", observe_assessment)

    build_problem_frame(PERCENT_PARTITION_CASE)

    assert events == ["proposal", "assessment"]


def test_migrated_family_does_not_use_legacy_assessment_adapter(monkeypatch) -> None:
    original_make_proposal = construction_affordances.make_proposal

    def reject_migrated_family(*args, **kwargs):
        family_id = kwargs.get("family_id", args[0] if args else None)
        if family_id == "partition.percent_partition":
            raise AssertionError("migrated family reached legacy make_proposal adapter")
        return original_make_proposal(*args, **kwargs)

    monkeypatch.setattr(
        construction_affordances,
        "make_proposal",
        reject_migrated_family,
    )

    assert (
        _percent_partition_proposal(build_problem_frame(PERCENT_PARTITION_CASE)).status
        == "proposed"
    )


def test_contract_assessment_remains_runnable_authority() -> None:
    frame = build_problem_frame(PERCENT_PARTITION_CASE)

    assert _percent_partition_proposal(frame).status == "proposed"
    assert _percent_partition_assessment(frame).runnable is True


def test_positive_proposal_does_not_close_missing_subgroup_bindings() -> None:
    frame = build_problem_frame(ONE_SUBGROUP_CONFUSER)
    assessment = _percent_partition_assessment(frame)

    assert _percent_partition_proposal(frame).status == "proposed"
    assert assessment.runnable is False
    assert "partition_subgroups_not_distinct" in assessment.missing_bindings
    assert "percent_subgroup_links_incomplete" in assessment.missing_bindings


def test_percent_partition_dispatch_requires_proposal_first_trace() -> None:
    frame = build_problem_frame(PERCENT_PARTITION_CASE)
    relation_only_frame = dataclasses.replace(frame, proposals=())

    assert {candidate.name for candidate in relation_only_frame.process_frames} & {
        "partition",
        "consumption",
    }
    assert any(
        relation.relation_type in {"subgroup_partition", "percent_of"}
        for relation in relation_only_frame.bound_relations
    )
    assert not any(
        assessment.candidate_organ == "percent_partition"
        for assessment in assess_contracts(relation_only_frame)
    )


def test_percent_change_confuser_is_proposed_but_not_runnable() -> None:
    frame = build_problem_frame(PERCENT_CHANGE_CONFUSER)
    assessment = _percent_partition_assessment(frame)

    assert _percent_partition_proposal(frame).status == "proposed"
    assert assessment.runnable is False
    assert "grounded_partition_subgroup" in assessment.missing_bindings
    assert "percent_change_vs_percent_of" in assessment.unresolved_hazards
