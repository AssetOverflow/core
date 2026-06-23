from __future__ import annotations

import pytest

from workbench.proposal_artifact import (
    capability_disclosure,
    proposal_artifact_from_minimal,
    ratification_affordance_allowed,
)
from workbench.schemas import to_data


def test_inspect_only_artifact_disallows_ratification_affordance() -> None:
    artifact = proposal_artifact_from_minimal(
        proposal_id="p1",
        subject_kind="construction",
        subject_id="turn:1",
        display_name="Construction proposal preview",
        source_kind="construction_evidence",
    )

    assert artifact.capability_level == "inspect_only"
    assert ratification_affordance_allowed(artifact) is False
    assert "Inspect-only" in capability_disclosure(artifact)


def test_proposal_only_artifact_disallows_ratification_affordance() -> None:
    artifact = proposal_artifact_from_minimal(
        proposal_id="p2",
        subject_kind="logos_pack",
        subject_id="logos:demo",
        display_name="CORE-Logos draft",
        source_kind="logos_pack",
        capability_level="proposal_only",
    )

    assert ratification_affordance_allowed(artifact) is False
    assert "Proposal-only" in capability_disclosure(artifact)


def test_ratification_enabled_requires_handler_route_for_affordance() -> None:
    artifact = proposal_artifact_from_minimal(
        proposal_id="p3",
        subject_kind="math",
        subject_id="math:p3",
        display_name="Math proposal",
        source_kind="math",
        capability_level="ratification_enabled",
        handler_route="/math-proposals/p3/ratify",
    )

    assert ratification_affordance_allowed(artifact) is True
    assert "admitted handler" in capability_disclosure(artifact)


def test_handler_route_without_ratification_capability_is_rejected() -> None:
    with pytest.raises(ValueError, match="handler_route"):
        proposal_artifact_from_minimal(
            proposal_id="p4",
            subject_kind="construction",
            subject_id="turn:4",
            display_name="Invalid preview",
            source_kind="construction_evidence",
            capability_level="inspect_only",
            handler_route="/invalid",
        )


def test_proposal_artifact_serializes_as_dataclass_payload() -> None:
    payload = to_data(
        proposal_artifact_from_minimal(
            proposal_id="p5",
            subject_kind="cognition",
            subject_id="candidate:p5",
            display_name="Cognition proposal",
            source_kind="teaching_proposal_log",
            state="pending",
        )
    )

    assert payload["proposal_id"] == "p5"
    assert payload["subject"] == {
        "kind": "cognition",
        "subject_id": "candidate:p5",
        "display_name": "Cognition proposal",
    }
    assert payload["capability_level"] == "inspect_only"
    assert payload["handler_route"] is None
