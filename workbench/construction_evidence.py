"""Read-only construction evidence projection helpers for Workbench.

This module is intentionally inert: it defines the Workbench-facing construction
read model and the honest missing-evidence constructor for legacy turns. It does
not parse problem text, execute candidate operators, run replay, mutate journals,
or grant serving authority.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

PipelineEvidenceStatus = Literal["recorded", "missing_evidence"]
CONSTRUCTION_EVIDENCE_ABSENT = "construction evidence was not persisted for this turn"


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


def construction_evidence_from_journal_entry(entry: Any) -> ConstructionEvidence:
    """Project persisted construction evidence from a journal entry if present.

    Current turn journals do not yet persist a construction evidence payload. This
    helper is deliberately fail-closed and returns a typed missing-evidence record
    rather than reconstructing a ProblemFrame from prose. When a later PR starts
    persisting `construction_evidence`, this function is the narrow projection
    seam to extend.
    """

    turn_id = int(getattr(entry, "turn_id"))
    payload = getattr(entry, "construction_evidence", None)
    if payload is None:
        return missing_construction_evidence(turn_id, CONSTRUCTION_EVIDENCE_ABSENT)

    if isinstance(payload, ConstructionEvidence):
        return payload

    if not isinstance(payload, dict):
        return missing_construction_evidence(
            turn_id,
            "construction evidence payload has unsupported shape",
        )

    try:
        schema_version = payload.get("schema_version")
        if schema_version != "construction_evidence_v1":
            return missing_construction_evidence(
                turn_id, f"unsupported schema version: {schema_version}"
            )

        status = payload.get("status")
        if status == "missing_evidence":
            return missing_construction_evidence(
                turn_id, payload.get("missing_reason") or CONSTRUCTION_EVIDENCE_ABSENT
            )

        if status != "recorded":
            return missing_construction_evidence(
                turn_id, f"unsupported status: {status}"
            )

        problem_text = payload.get("problem_text")
        if problem_text is None:
            return missing_construction_evidence(
                turn_id, "recorded construction evidence missing problem_text"
            )
        if not isinstance(problem_text, str):
            return missing_construction_evidence(
                turn_id, "problem_text must be a string"
            )

        def parse_span(s: Any) -> SourceSpanView:
            if not isinstance(s, dict):
                raise TypeError("span must be a dict")
            span = SourceSpanView(
                start=int(s["start"]),
                end=int(s["end"]),
                text=str(s["text"]),
            )
            if not span_is_exact(problem_text, span):
                raise ValueError(f"exact span validation failed: {span}")
            return span

        def parse_spans(lst: Any) -> list[SourceSpanView]:
            if not isinstance(lst, list):
                return []
            return [parse_span(s) for s in lst]

        proposals: list[ConstructionProposalView] = []
        for prop in payload.get("proposals") or []:
            role_obligations = [
                RoleObligationView(
                    role=str(r["role"]),
                    required=bool(r["required"]),
                    description=str(r["description"]),
                )
                for r in prop.get("role_obligations") or []
            ]
            proposals.append(
                ConstructionProposalView(
                    family_id=str(prop["family_id"]),
                    relation_type=str(prop["relation_type"]),
                    candidate_organ=str(prop["candidate_organ"]),
                    status=prop["status"],
                    evidence_spans=parse_spans(prop.get("evidence_spans")),
                    role_obligations=role_obligations,
                    diagnostic_only=bool(prop.get("diagnostic_only", True)),
                    serving_allowed=bool(prop.get("serving_allowed", False)),
                )
            )

        mentions: list[MentionView] = []
        for m in payload.get("mentions") or []:
            mentions.append(
                MentionView(
                    mention_id=str(m["mention_id"]),
                    kind=str(m["kind"]),
                    surface=str(m["surface"]),
                    span=parse_span(m["span"]),
                    fact_id=m.get("fact_id"),
                )
            )

        bindings: list[MentionBindingView] = []
        for b in payload.get("bindings") or []:
            bindings.append(
                MentionBindingView(
                    binding_type=str(b["binding_type"]),
                    source_mention_id=str(b["source_mention_id"]),
                    target_mention_id=str(b["target_mention_id"]),
                    evidence_spans=parse_spans(b.get("evidence_spans")),
                )
            )

        bound_relations: list[BoundRelationView] = []
        for br in payload.get("bound_relations") or []:
            roles = [
                BoundRelationRoleView(
                    role=str(r["role"]),
                    target_id=str(r["target_id"]),
                    evidence_spans=parse_spans(r.get("evidence_spans")),
                )
                for r in br.get("roles") or []
            ]
            bound_relations.append(
                BoundRelationView(
                    relation_type=str(br["relation_type"]),
                    roles=roles,
                    evidence_spans=parse_spans(br.get("evidence_spans")),
                )
            )

        contract_assessments: list[ContractAssessmentView] = []
        for ca in payload.get("contract_assessments") or []:
            contract_assessments.append(
                ContractAssessmentView(
                    candidate_organ=str(ca["candidate_organ"]),
                    family_id=ca.get("family_id"),
                    missing_bindings=[str(mb) for mb in ca.get("missing_bindings") or []],
                    unresolved_hazards=[str(uh) for uh in ca.get("unresolved_hazards") or []],
                    runnable=bool(ca.get("runnable", False)),
                    explanation=str(ca.get("explanation", "")),
                    evidence_spans=parse_spans(ca.get("evidence_spans")),
                )
            )

        return ConstructionEvidence(
            schema_version="construction_evidence_v1",
            turn_id=turn_id,
            status="recorded",
            missing_reason=None,
            problem_text=problem_text,
            proposals=proposals,
            mentions=mentions,
            bindings=bindings,
            bound_relations=bound_relations,
            contract_assessments=contract_assessments,
            diagnostic_only=bool(payload.get("diagnostic_only", True)),
            serving_allowed=bool(payload.get("serving_allowed", False)),
        )

    except (KeyError, TypeError, ValueError) as exc:
        return missing_construction_evidence(
            turn_id,
            f"construction evidence payload projection failed: {exc}",
        )


def span_is_exact(problem_text: str, span: SourceSpanView) -> bool:
    """Return whether a span exactly matches its source text slice."""

    return (
        0 <= span.start <= span.end <= len(problem_text)
        and bool(span.text)
        and problem_text[span.start : span.end] == span.text
    )
