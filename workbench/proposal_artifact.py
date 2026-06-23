"""ProposalArtifact authority scaffolding for Workbench.

This module defines a shared proposal-review envelope without admitting any new
ratification handler. It is safe, inert UI/read-model substrate: capability level
controls what the Workbench may display as an affordance.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

ProposalCapabilityLevel = Literal[
    "inspect_only",
    "proposal_only",
    "ratification_enabled",
]

ProposalArtifactState = Literal[
    "pending",
    "accepted",
    "rejected",
    "withdrawn",
    "deferred",
    "unknown",
]


@dataclass(frozen=True, slots=True)
class ProposalSubject:
    kind: str
    subject_id: str
    display_name: str


@dataclass(frozen=True, slots=True)
class EvidencePointer:
    kind: str
    ref: str
    label: str
    digest: str | None = None


@dataclass(frozen=True, slots=True)
class ProposalValidationReport:
    status: Literal["valid", "blocked", "unknown"]
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class ProposalSafetyReport:
    status: Literal["clear", "warning", "failed", "unknown"]
    disclosures: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class ProposalArtifact:
    proposal_id: str
    subject: ProposalSubject
    state: ProposalArtifactState
    capability_level: ProposalCapabilityLevel
    source_kind: str
    proposed_change: Any = None
    reasoning_trace: Any = None
    evidence_pointers: list[EvidencePointer] = field(default_factory=list)
    validation: ProposalValidationReport | None = None
    replay_evidence: Any = None
    safety_report: ProposalSafetyReport | None = None
    affected_artifacts: list[EvidencePointer] = field(default_factory=list)
    handler_route: str | None = None
    suggested_cli: str | None = None
    audit_refs: list[EvidencePointer] = field(default_factory=list)
    ui_disclosure: str = "Proposal artifact is inspect-only unless an admitted handler exists."


def ratification_affordance_allowed(artifact: ProposalArtifact) -> bool:
    """Return whether UI may show ratify/reject/defer controls."""

    return artifact.capability_level == "ratification_enabled" and bool(
        artifact.handler_route
    )


def capability_disclosure(artifact: ProposalArtifact) -> str:
    if artifact.capability_level == "ratification_enabled":
        if artifact.handler_route:
            return "Ratification controls may render through the admitted handler route."
        return "Ratification is disabled because no handler route is present."
    if artifact.capability_level == "proposal_only":
        return "Proposal-only artifact: review/export/copy are allowed; apply is not."
    return "Inspect-only artifact: no apply, ratify, promote, or mutation affordance is allowed."


def proposal_artifact_from_minimal(
    *,
    proposal_id: str,
    subject_kind: str,
    subject_id: str,
    display_name: str,
    source_kind: str,
    capability_level: ProposalCapabilityLevel = "inspect_only",
    state: ProposalArtifactState = "unknown",
    handler_route: str | None = None,
) -> ProposalArtifact:
    """Build a minimal shared proposal review envelope."""

    artifact = ProposalArtifact(
        proposal_id=proposal_id,
        subject=ProposalSubject(
            kind=subject_kind,
            subject_id=subject_id,
            display_name=display_name,
        ),
        state=state,
        capability_level=capability_level,
        source_kind=source_kind,
        handler_route=handler_route,
    )
    if capability_level != "ratification_enabled" and handler_route is not None:
        raise ValueError("handler_route requires ratification_enabled capability")
    return artifact
