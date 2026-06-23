from __future__ import annotations

from workbench.demo_narrative import (
    DemoEvidenceLink,
    DemoNarrative,
    DemoNarrativeStep,
    demo_partner_blurb,
    validate_demo_narrative,
)
from workbench.schemas import to_data


def test_demo_narrative_requires_proof_and_non_proof_claims() -> None:
    narrative = DemoNarrative(
        narrative_id="bad",
        title="Bad demo",
        summary="missing honesty cards",
        steps=[
            DemoNarrativeStep(
                step_id="s1",
                order=1,
                kind="evidence",
                title="Trace",
                claim="trace exists",
                what_this_proves="",
                what_this_does_not_prove="",
            )
        ],
    )

    assert validate_demo_narrative(narrative) == [
        "step s1 is missing what_this_proves",
        "step s1 is missing what_this_does_not_prove",
    ]


def test_demo_narrative_requires_route_evidence_links() -> None:
    narrative = DemoNarrative(
        narrative_id="bad-route",
        title="Bad route",
        summary="bad evidence link",
        steps=[
            DemoNarrativeStep(
                step_id="s1",
                order=1,
                kind="evidence",
                title="Trace",
                claim="trace exists",
                what_this_proves="a trace route can be opened",
                what_this_does_not_prove="that the answer is correct",
                evidence_links=[DemoEvidenceLink(label="bad", route="trace/1")],
            )
        ],
    )

    assert validate_demo_narrative(narrative) == [
        "step s1 has non-route evidence link: trace/1"
    ]


def test_demo_narrative_detects_duplicate_steps_and_order() -> None:
    narrative = DemoNarrative(
        narrative_id="bad-order",
        title="Bad order",
        summary="duplicate ids and unsorted order",
        steps=[
            DemoNarrativeStep(
                step_id="s1",
                order=2,
                kind="evidence",
                title="Trace B",
                claim="claim",
                what_this_proves="proof",
                what_this_does_not_prove="non-proof",
            ),
            DemoNarrativeStep(
                step_id="s1",
                order=1,
                kind="audit",
                title="Audit A",
                claim="claim",
                what_this_proves="proof",
                what_this_does_not_prove="non-proof",
            ),
        ],
    )

    assert validate_demo_narrative(narrative) == [
        "duplicate step_id: s1",
        "steps must be sorted by order",
    ]


def test_valid_demo_narrative_serializes() -> None:
    narrative = DemoNarrative(
        narrative_id="deterministic-turn",
        title="Deterministic Turn Evidence",
        summary="Chat to Trace to Replay",
        steps=[
            DemoNarrativeStep(
                step_id="trace",
                order=1,
                kind="evidence",
                title="Open Trace",
                claim="The journaled turn has trace evidence.",
                what_this_proves="The selected turn has recorded evidence.",
                what_this_does_not_prove="It does not prove answer correctness by itself.",
                evidence_links=[
                    DemoEvidenceLink(
                        label="Trace",
                        route="/trace/1",
                        artifact_id="turn:1",
                        digest="sha256:abc",
                        reproducer="curl /trace/1",
                    )
                ],
            )
        ],
    )

    assert validate_demo_narrative(narrative) == []
    payload = to_data(narrative)
    assert payload["narrative_id"] == "deterministic-turn"
    assert payload["steps"][0]["evidence_links"][0]["route"] == "/trace/1"


def test_partner_blurb_states_core_demo_thesis() -> None:
    blurb = demo_partner_blurb()

    assert "frontier model can propose" in blurb
    assert "CORE can govern" in blurb
    assert "Workbench can prove" in blurb
