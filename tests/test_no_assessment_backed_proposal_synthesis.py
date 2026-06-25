from __future__ import annotations

import dataclasses

import generate.construction_affordances as construction_affordances
from generate.problem_frame_builder import build_problem_frame
from generate.problem_frame_contracts import assess_contracts


def test_builder_does_not_synthesize_proposals_from_assessments(monkeypatch) -> None:
    """Construction proposals must originate before ContractAssessment.

    This pins the proposal-first boundary against the stale assessment-backed
    synthesis path: even when ``make_proposal`` is monkeypatched to fail loudly,
    a normal proposal-backed frame must build without consulting it.
    """

    calls: list[dict[str, object]] = []

    def forbidden_make_proposal(**kwargs):  # type: ignore[no-untyped-def]
        calls.append(dict(kwargs))
        raise AssertionError(
            "build_problem_frame must not synthesize ConstructionProposal "
            "objects from ContractAssessment output"
        )

    monkeypatch.setattr(
        construction_affordances,
        "make_proposal",
        forbidden_make_proposal,
    )

    frame = build_problem_frame("Mia has 7 apples. How many apples does Mia have?")

    assert calls == []
    assert tuple(proposal.family_id for proposal in frame.proposals) == (
        "binding.quantity_entity",
    )
    assert all(proposal.status == "proposed" for proposal in frame.proposals)


def test_contract_assessments_do_not_create_proposal_free_fallback_source() -> None:
    """A proposal-free frame must not produce assessments for backfill synthesis."""

    frame = build_problem_frame("Mia has 7 apples. How many apples does Mia have?")
    proposal_free_frame = dataclasses.replace(frame, proposals=())

    assert assess_contracts(proposal_free_frame) == ()
