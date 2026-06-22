"""Cross-family invariants for the proposal-first construction seam."""

from __future__ import annotations

import dataclasses
import inspect

import pytest

import generate.construction_affordances as construction_affordances
import generate.problem_frame_contracts as problem_frame_contracts
from generate.construction_affordances import (
    all_diagnostic_families,
    propose_construction,
)
from generate.kernel_facts import SourceSpan
from generate.problem_frame_builder import build_problem_frame
from generate.problem_frame_contracts import assess_contracts


FRACTION_DECREASE_CASE = (
    "In one hour, Addison mountain's temperature will decrease to 3/4  of its temperature. "
    "If the current temperature of the mountain is 84 degrees, what will the temperature "
    "decrease by?"
)

TANK_EVIDENCE_CASE = (
    "A tank's temperature will decrease to 3/4  of its current temperature. "
    "If the current temperature is 84 degrees, how many degrees will it decrease by?"
)

PERCENT_PARTITION_CASE = (
    "A school has 100 students. Half of the students are girls, the other half are boys.  "
    "20% of the girls have dogs at home and 10% of the boys have dogs at home.  "
    "How many students own dogs?"
)

QUANTITY_ENTITY_CASE = "A school has 100 students."
UNARY_DELTA_CASE = "Ana gained 3 marbles."

MIGRATED_CASES = (
    (
        QUANTITY_ENTITY_CASE,
        "binding.quantity_entity",
        "quantity_entity_binding",
    ),
    (
        FRACTION_DECREASE_CASE,
        "proportional_change.decrease_to_fraction",
        "fraction_decrease",
    ),
    (
        PERCENT_PARTITION_CASE,
        "partition.percent_partition",
        "percent_partition",
    ),
    (
        UNARY_DELTA_CASE,
        "state_change.unary_delta",
        "unary_delta_transition",
    ),
)


def _proposal(frame, family_id: str):
    proposals = [item for item in frame.proposals if item.family_id == family_id]
    assert len(proposals) == 1
    return proposals[0]


def test_proposal_factory_accepts_only_hypothesis_inputs() -> None:
    parameters = inspect.signature(propose_construction).parameters

    assert tuple(parameters) == ("family_id", "evidence_spans")
    assert not {
        "assessment",
        "runnable",
        "verdict",
        "score",
        "missing_roles",
        "active_hazards",
    } & parameters.keys()


def test_every_catalog_family_starts_as_diagnostic_proposal() -> None:
    evidence = (SourceSpan("surface cue", 0, 11),)

    for family in all_diagnostic_families():
        assert family.diagnostic_only is True
        assert family.serving_allowed is False

        proposal = propose_construction(family.family_id, evidence)

        assert proposal.status == "proposed"
        assert proposal.missing_roles == ()
        assert proposal.active_hazards == ()
        assert proposal.diagnostic_only is True
        assert proposal.serving_allowed is False


@pytest.mark.parametrize(("problem_text", "family_id", "candidate_organ"), MIGRATED_CASES)
def test_migrated_families_keep_assessment_authority(
    problem_text: str,
    family_id: str,
    candidate_organ: str,
) -> None:
    frame = build_problem_frame(problem_text)
    proposal = _proposal(frame, family_id)

    assert proposal.status == "proposed"
    assessments = assess_contracts(frame)
    assessment = next(
        item for item in assessments if item.candidate_organ == candidate_organ
    )

    assert _proposal(frame, family_id).status == "proposed"
    assert not hasattr(proposal, "runnable")
    assert assessment.runnable is True
    assert assessment.missing_bindings == ()
    assert assessment.unresolved_hazards == ()


@pytest.mark.parametrize(("problem_text", "family_id", "candidate_organ"), MIGRATED_CASES)
def test_migrated_contract_dispatch_requires_a_proposal(
    problem_text: str,
    family_id: str,
    candidate_organ: str,
) -> None:
    frame = build_problem_frame(problem_text)
    assert _proposal(frame, family_id).status == "proposed"

    proposal_free_frame = dataclasses.replace(frame, proposals=())

    assert candidate_organ not in {
        assessment.candidate_organ
        for assessment in assess_contracts(proposal_free_frame)
    }


@pytest.mark.parametrize(("problem_text", "family_id", "candidate_organ"), MIGRATED_CASES)
def test_builder_publishes_proposal_before_assessment(
    monkeypatch: pytest.MonkeyPatch,
    problem_text: str,
    family_id: str,
    candidate_organ: str,
) -> None:
    observed_statuses: list[str] = []
    original_assess_contracts = problem_frame_contracts.assess_contracts

    def observe_assessment(frame):
        observed_statuses.append(_proposal(frame, family_id).status)
        return original_assess_contracts(frame)

    monkeypatch.setattr(
        problem_frame_contracts,
        "assess_contracts",
        observe_assessment,
    )

    frame = build_problem_frame(problem_text)

    assert observed_statuses == ["proposed"]
    assert any(
        assessment.candidate_organ == candidate_organ
        for assessment in assess_contracts(frame)
    )


def test_migrated_families_bypass_legacy_make_proposal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    migrated_family_ids = {family_id for _, family_id, _ in MIGRATED_CASES}
    observed_family_ids: list[str] = []
    original_make_proposal = construction_affordances.make_proposal

    def observe_make_proposal(*args, **kwargs):
        family_id = kwargs.get("family_id", args[0] if args else None)
        observed_family_ids.append(family_id)
        return original_make_proposal(*args, **kwargs)

    monkeypatch.setattr(
        construction_affordances,
        "make_proposal",
        observe_make_proposal,
    )

    for problem_text, family_id, _ in MIGRATED_CASES:
        assert _proposal(build_problem_frame(problem_text), family_id)

    assert migrated_family_ids.isdisjoint(observed_family_ids)


@pytest.mark.parametrize(
    ("problem_text", "family_id", "expected_evidence"),
    (
        (
            QUANTITY_ENTITY_CASE,
            "binding.quantity_entity",
            ("100 students",),
        ),
        (
            TANK_EVIDENCE_CASE,
            "proportional_change.decrease_to_fraction",
            ("decrease to 3/4  of",),
        ),
        (
            PERCENT_PARTITION_CASE,
            "partition.percent_partition",
            ("20% of", "10% of"),
        ),
        (
            UNARY_DELTA_CASE,
            "state_change.unary_delta",
            ("gained",),
        ),
    ),
)
def test_migrated_proposals_contain_only_exact_motivating_surface_evidence(
    problem_text: str,
    family_id: str,
    expected_evidence: tuple[str, ...],
) -> None:
    proposal = _proposal(build_problem_frame(problem_text), family_id)

    assert tuple(span.text for span in proposal.evidence_spans) == expected_evidence
    assert all(
        span.text == problem_text[span.start : span.end]
        for span in proposal.evidence_spans
    )
