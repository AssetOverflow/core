"""Read-only construction evidence projection helpers for Workbench.

This module is intentionally inert: it defines the Workbench-facing construction
read model and the honest missing-evidence constructor for legacy turns. It does
not parse problem text, execute candidate operators, run replay, mutate journals,
or grant serving authority.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

PipelineEvidenceStatus = Literal["recorded", "missing_evidence"]


@dataclass(frozen=True, slots=True)
class SourceSpanView:
    """Exact source span projected to the Workbench.

    The caller owns validation against the source string. This record must not be
    normalized or repaired by the UI.
    """

    start: int
    end: int
    text: str


@dataclass(frozen=True, slots=True)
class RoleObligationView:
    role: str
    required: bool
    description: str


@dataclass(frozen=True, slots=True)
class ConstructionProposalView:
    """Diagnostic construction proposal.

    A proposal is a hypothesis only. Runnable/refused authority belongs to the
    corresponding ContractAssessmentView.
    """

    family_id: str
    relation_type: str
    candidate_organ: str
    status: Literal["proposed"]
    evidence_spans: list[SourceSpanView] = field(default_factory=list)
    role_obligations: list[RoleObligationView] = field(default_factory=list)
    diagnostic_only: bool = True
    serving_allowed: bool = False


@dataclass(frozen=True, slots=True)
class MentionView:
    mention_id: str
    kind: str
    surface: str
    span: SourceSpanView
    fact_id: str | None = None


@dataclass(frozen=True, slots=True)
class MentionBindingView:
    binding_type: str
    source_mention_id: str
    target_mention_id: str
    evidence_spans: list[SourceSpanView] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class BoundRelationRoleView:
    role: str
    target_id: str
    evidence_spans: list[SourceSpanView] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class BoundRelationView:
    relation_type: str
    roles: list[BoundRelationRoleView] = field(default_factory=list)
    evidence_spans: list[SourceSpanView] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class ContractAssessmentView:
    """Read-only projection of generate.problem_frame_contracts.ContractAssessment."""

    candidate_organ: str
    family_id: str | None
    missing_bindings: list[str] = field(default_factory=list)
    unresolved_hazards: list[str] = field(default_factory=list)
    runnable: bool = False
    explanation: str = ""
    evidence_spans: list[SourceSpanView] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class ConstructionEvidence:
    """Workbench-facing construction evidence for one turn.

    This record is a projection, not an executor. `diagnostic_only=True` and
    `serving_allowed=False` are load-bearing disclosure fields.
    """

    schema_version: Literal["construction_evidence_v1"]
    turn_id: int
    status: PipelineEvidenceStatus
    missing_reason: str | None
    problem_text: str | None
    proposals: list[ConstructionProposalView] = field(default_factory=list)
    mentions: list[MentionView] = field(default_factory=list)
    bindings: list[MentionBindingView] = field(default_factory=list)
    bound_relations: list[BoundRelationView] = field(default_factory=list)
    contract_assessments: list[ContractAssessmentView] = field(default_factory=list)
    diagnostic_only: bool = True
    serving_allowed: bool = False


def missing_construction_evidence(turn_id: int, reason: str) -> ConstructionEvidence:
    """Return the honest absence state for legacy turns.

    Absence is not an error and not a failed proof. It means the selected turn has
    no persisted construction evidence to project.
    """

    return ConstructionEvidence(
        schema_version="construction_evidence_v1",
        turn_id=turn_id,
        status="missing_evidence",
        missing_reason=reason,
        problem_text=None,
        proposals=[],
        mentions=[],
        bindings=[],
        bound_relations=[],
        contract_assessments=[],
        diagnostic_only=True,
        serving_allowed=False,
    )


def span_is_exact(problem_text: str, span: SourceSpanView) -> bool:
    """Return whether a span exactly matches its source text slice."""

    return (
        0 <= span.start <= span.end <= len(problem_text)
        and bool(span.text)
        and problem_text[span.start : span.end] == span.text
    )
