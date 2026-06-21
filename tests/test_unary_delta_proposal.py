"""Diagnostic-only contract tests for ``state_change.unary_delta``."""

from __future__ import annotations

import ast
import dataclasses
from pathlib import Path

import generate.problem_frame_contracts as problem_frame_contracts
import pytest

from generate.kernel_facts import SourceSpan
from generate.problem_frame_builder import build_problem_frame
from generate.problem_frame_contracts import assess_contracts, assess_unary_delta


FAMILY_ID = "state_change.unary_delta"
CANDIDATE_ORGAN = "unary_delta"


def _proposal(frame):
    proposals = tuple(
        proposal
        for proposal in frame.proposals
        if proposal.family_id == FAMILY_ID
    )
    assert len(proposals) == 1
    return proposals[0]


def _relation(frame):
    relations = tuple(
        relation
        for relation in frame.bound_relations
        if relation.relation_type == "unary_delta"
    )
    assert len(relations) == 1
    return relations[0]


def _assessment(frame):
    assessments = tuple(
        assessment
        for assessment in assess_contracts(frame)
        if assessment.candidate_organ == CANDIDATE_ORGAN
    )
    assert len(assessments) == 1
    return assessments[0]


@pytest.mark.parametrize(
    ("problem_text", "cue", "direction"),
    (
        ("Ana gained 3 marbles.", "gained", "increase"),
        ("The jar lost 2 cookies.", "lost", "decrease"),
    ),
)
def test_exact_local_gained_lost_event_is_proposed_bound_and_assessed(
    problem_text: str,
    cue: str,
    direction: str,
) -> None:
    frame = build_problem_frame(problem_text)
    proposal = _proposal(frame)
    relation = _relation(frame)
    assessment = _assessment(frame)

    assert proposal.status == "proposed"
    assert proposal.diagnostic_only is True
    assert proposal.serving_allowed is False
    assert not hasattr(proposal, "runnable")

    roles = {role.role: role for role in relation.roles}
    assert set(roles) == {"action_cue", "delta_quantity", "changed_object", "direction"}
    assert roles["direction"].target_id == direction
    assert roles["action_cue"].evidence_spans[0].text == cue

    assert assessment.runnable is True
    assert assessment.missing_bindings == ()
    assert assessment.unresolved_hazards == ()
    assert all(
        span.text == problem_text[span.start:span.end]
        for span in (*proposal.evidence_spans, *relation.evidence_spans, *assessment.evidence_spans)
    )


def test_builder_publishes_unary_delta_proposal_before_assessment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed_statuses: list[str] = []
    original = problem_frame_contracts.assess_contracts

    def observe(frame):
        observed_statuses.append(_proposal(frame).status)
        return original(frame)

    monkeypatch.setattr(problem_frame_contracts, "assess_contracts", observe)

    frame = build_problem_frame("Ana gained 3 marbles.")

    assert observed_statuses == ["proposed"]
    assert _assessment(frame).runnable is True


def test_proposal_free_frame_does_not_dispatch_unary_delta_contract() -> None:
    frame = build_problem_frame("Ana gained 3 marbles.")
    proposal_free = dataclasses.replace(frame, proposals=())

    assert CANDIDATE_ORGAN not in {
        assessment.candidate_organ
        for assessment in assess_contracts(proposal_free)
    }
    assessment = assess_unary_delta(proposal_free)
    assert assessment.runnable is False
    assert "unary_delta_proposal_required" in assessment.missing_bindings


@pytest.mark.parametrize(
    "problem_text",
    (
        "There are 12 apples.",
        "Tom has 12 apples.",
        "Tom gave Ana 3 apples.",
        "Tom sent Ana 3 apples.",
        "Tom received 3 apples.",
        "Tom bought 3 apples.",
        "Tom put 3 apples in the box.",
        "Tom took 3 apples from the box.",
        "Tom had 12 apples and lost 3.",
        "There are 12 apples. Tom lost 3.",
        "She gained 3 apples.",
        "Tom gained apples.",
        "Tom gained 3 apples and oranges.",
        "Tom gained 3 and 4 apples.",
        "Tom gained 3 more apples than Ana.",
        "20% of apples were gained.",
        "3 apples per child were gained.",
        "Tom did not gain 3 apples.",
        "Tom may have gained 3 apples.",
        "Tom gained 3 apples and lost 2 apples.",
    ),
)
def test_confusers_do_not_dispatch_unary_delta(problem_text: str) -> None:
    frame = build_problem_frame(problem_text)

    assert FAMILY_ID not in {proposal.family_id for proposal in frame.proposals}
    assert not any(
        relation.relation_type == "unary_delta"
        for relation in frame.bound_relations
    )
    assert CANDIDATE_ORGAN not in {
        assessment.candidate_organ
        for assessment in assess_contracts(frame)
    }


def test_missing_object_literal_surface_stays_unbound_and_non_runnable() -> None:
    frame = build_problem_frame("Tom gained 3.")

    assert FAMILY_ID not in {proposal.family_id for proposal in frame.proposals}
    assert not any(
        relation.relation_type == "unary_delta"
        for relation in frame.bound_relations
    )
    assert CANDIDATE_ORGAN not in {
        assessment.candidate_organ
        for assessment in assess_contracts(frame)
    }


def test_missing_quantity_blocks_runnable_unary_delta() -> None:
    frame = build_problem_frame("Tom gained 3 apples.")
    relation = _relation(frame)
    stripped_roles = tuple(role for role in relation.roles if role.role != "delta_quantity")
    broken = dataclasses.replace(frame, bound_relations=(dataclasses.replace(relation, roles=stripped_roles),))

    assessment = assess_unary_delta(broken)

    assert assessment.runnable is False
    assert "delta_quantity_unbound" in assessment.missing_bindings


def test_quantity_kind_conflict_blocks_runnable_unary_delta() -> None:
    frame = build_problem_frame("Tom gained 3 degrees.")
    assessment = _assessment(frame)

    assert assessment.runnable is False
    assert "quantity_kind_unresolved" in assessment.missing_bindings


def test_synthetic_or_mismatched_unary_delta_evidence_refuses() -> None:
    frame = build_problem_frame("Ana gained 3 marbles.")
    proposal = _proposal(frame)
    relation = _relation(frame)
    synthetic = SourceSpan("synthetic", 0, 9)
    cue = SourceSpan("Ana gained", 0, 10)
    bad_relation = dataclasses.replace(
        relation,
        roles=tuple(
            dataclasses.replace(role, evidence_spans=(synthetic,))
            if role.role == "action_cue"
            else role
            for role in relation.roles
        ),
        evidence_spans=(cue, *relation.evidence_spans[1:]),
    )
    broken = dataclasses.replace(
        frame,
        proposals=(dataclasses.replace(proposal, evidence_spans=(synthetic,)),),
        bound_relations=(bad_relation,),
    )

    assessment = assess_unary_delta(broken)

    assert assessment.runnable is False
    assert "provenance_span_inexact" in assessment.missing_bindings


def test_unary_delta_replay_is_deterministic() -> None:
    problem_text = "Ana gained 3 marbles."

    first = build_problem_frame(problem_text)
    second = build_problem_frame(problem_text)

    assert first.proposals == second.proposals
    assert first.bound_relations == second.bound_relations
    assert assess_contracts(first) == assess_contracts(second)


def test_existing_proposal_first_families_do_not_gain_unary_delta_dispatch() -> None:
    percent_partition = (
        "A school has 100 students. Half of the students are girls, the other half are boys. "
        "20% of the girls have dogs and 10% of the boys have dogs. "
        "How many students own dogs?"
    )
    fraction_decrease = (
        "A tank's temperature will decrease to 3/4 of its current temperature. "
        "If the current temperature is 84 degrees, how many degrees will it decrease by?"
    )
    quantity_entity = "A school has 100 students."

    for problem_text in (percent_partition, fraction_decrease, quantity_entity):
        frame = build_problem_frame(problem_text)
        assert FAMILY_ID not in {proposal.family_id for proposal in frame.proposals}
        assert CANDIDATE_ORGAN not in {
            assessment.candidate_organ
            for assessment in assess_contracts(frame)
        }


def test_unary_delta_path_does_not_import_legacy_semantic_state() -> None:
    for module in (
        "generate.problem_frame_builder",
        "generate.problem_frame_contracts",
    ):
        path = Path(__import__(module, fromlist=["__file__"]).__file__)
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imported = {
            node.module
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module is not None
        }
        assert "generate.derivation.state" not in imported
