"""Typed UI-facing schemas for CORE Workbench v1."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal


ErrorCode = Literal[
    "bad_request",
    "not_found",
    "unsupported",
    "read_error",
    "eval_failed",
    "runtime_unavailable",
]

MutationMode = Literal["read_only", "runtime_turn"]
GroundingSource = Literal["pack", "teaching", "vault", "partial", "oov", "none"]
EpistemicStateValue = Literal[
    "perceived",
    "evidenced",
    "evidenced_incomplete",
    "verified",
    "decoded",
    "decoded_unarticulated",
    "inferred",
    "unverified_possible",
    "unverified_novel",
    "contradicted",
    "ambiguous",
    "undetermined",
    "scope_boundary",
    "computationally_bounded",
    "epistemic_state_needed",
]
NormativeClearanceValue = Literal[
    "cleared",
    "violated",
    "unassessable",
    "suppressed",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def to_data(value: Any) -> Any:
    if hasattr(value, "as_dict") and callable(value.as_dict):
        return value.as_dict()
    if hasattr(value, "__dataclass_fields__"):
        return asdict(value)
    if isinstance(value, dict):
        return {str(k): to_data(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_data(v) for v in value]
    return value


def ok(data: Any) -> dict[str, Any]:
    return {"ok": True, "generated_at": utc_now(), "data": to_data(data)}


def error(code: ErrorCode, message: str, *, detail: Any | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {"code": code, "message": message}
    if detail is not None:
        payload["detail"] = to_data(detail)
    return {"ok": False, "generated_at": utc_now(), "error": payload}


@dataclass(frozen=True, slots=True)
class RuntimeStatus:
    backend: Literal["numpy", "mlx", "rust", "unknown"]
    git_revision: str
    engine_state_present: bool
    checkpoint_revision: str
    revision_warning: bool
    active_session_id: str | None
    mutation_mode: MutationMode = "read_only"


@dataclass(frozen=True, slots=True)
class TurnVerdict:
    outcome: Literal["cleared", "violated", "unassessable"]
    runtime_detail: str


@dataclass(frozen=True, slots=True)
class ProposalRef:
    candidate_id: str
    source_kind: str


@dataclass(frozen=True, slots=True)
class ChatTurnResult:
    prompt: str
    surface: str
    articulation_surface: str | None
    walk_surface: str | None
    grounding_source: GroundingSource
    epistemic_state: EpistemicStateValue
    normative_clearance: NormativeClearanceValue
    normative_detail: str
    trace_hash: str | None
    refusal_emitted: bool
    hedge_injected: bool
    mutation_mode: MutationMode
    identity_verdict: TurnVerdict | None
    safety_verdict: TurnVerdict | None
    ethics_verdict: TurnVerdict | None
    proposal_candidates: list[ProposalRef]
    turn_cost_ms: int
    checkpoint_emitted: bool
    turn_id: int | None = None


@dataclass(frozen=True, slots=True)
class TurnJournalSummarySchema:
    turn_id: int
    timestamp: str
    prompt_excerpt: str
    surface_excerpt: str
    trace_hash: str | None
    grounding_source: GroundingSource


@dataclass(frozen=True, slots=True)
class TurnJournalEntrySchema:
    turn_id: int
    timestamp: str
    trace_hash: str | None
    prompt: str
    surface: str
    articulation_surface: str | None
    walk_surface: str | None
    grounding_source: GroundingSource
    epistemic_state: EpistemicStateValue
    normative_clearance: NormativeClearanceValue
    verdicts: dict[str, Any]
    refusal_emitted: bool
    hedge_injected: bool
    proposal_candidates: list[dict[str, Any]]
    turn_cost_ms: int
    checkpoint_emitted: bool
    journal_digest: str


@dataclass(frozen=True, slots=True)
class ArtifactRef:
    artifact_id: str
    kind: Literal[
        "trace",
        "eval_result",
        "proposal",
        "contemplation_report",
        "telemetry",
        "engine_state_manifest",
        "unknown",
    ]
    path: str
    digest: str | None
    created_at: str | None


@dataclass(frozen=True, slots=True)
class ArtifactDetail(ArtifactRef):
    content_type: Literal["json", "jsonl", "text", "unknown"]
    content: Any


@dataclass(frozen=True, slots=True)
class ProposalSummary:
    proposal_id: str
    state: Literal["pending", "accepted", "rejected", "withdrawn", "unknown"]
    source_kind: str
    replay_equivalent: bool | None
    created_at: str | None
    downstream_effect: Literal["unknown", "none", "observed"]


@dataclass(frozen=True, slots=True)
class ProposalDetail(ProposalSummary):
    proposed_chain: Any
    replay_evidence: Any
    source: Any
    evidence: list[Any] = field(default_factory=list)
    artifact_refs: list[ArtifactRef] = field(default_factory=list)
    suggested_cli: str | None = None


@dataclass(frozen=True, slots=True)
class EvalLaneSummary:
    lane: str
    versions: list[str]
    read_only: bool
    description: str | None


@dataclass(frozen=True, slots=True)
class EvalRunResult:
    lane: str
    version: str
    split: str
    passed: bool | None
    metrics: dict[str, Any]
    cases: list[Any]
    source_digest: str | None = None


ReplayDivergenceSeverity = Literal["info", "warning", "failure"]
ReplayStatus = Literal["equivalent", "not_yet_replayed", "diverged", "evidence_unavailable"]


@dataclass(frozen=True, slots=True)
class ReplayDivergence:
    path: str
    original: Any
    replay: Any
    severity: ReplayDivergenceSeverity


@dataclass(frozen=True, slots=True)
class ReplayComparison:
    artifact_id: str
    original_hash: str | None
    replay_hash: str | None
    equivalent: bool
    divergences: list[ReplayDivergence] = field(default_factory=list)


# ---------------------------------------------------------------------------
# ADR-0172 W4 — Math proposal schemas
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class MathReasoningStep:
    step_index: int
    step_kind: str
    claim: str
    justification: str
    input_pointers: list[str]
    output_payload: Any


@dataclass(frozen=True, slots=True)
class MathProposalSummary:
    proposal_id: str
    domain: Literal["math"]
    shape_category: str
    proposed_change_kind: str
    structural_commonality: str
    evidence_count: int
    replay_equivalence_hash: str


@dataclass(frozen=True, slots=True)
class MathProposalDetail(MathProposalSummary):
    wrong_zero_assertion: str
    proposed_change_payload: Any
    reasoning_trace_id: str
    reasoning_trace_steps: list[MathReasoningStep]
    evidence_hashes: list[str]
    handler_name: str | None
    suggested_ratify_cli: str | None


@dataclass(frozen=True, slots=True)
class MathRatifyResult:
    proposal_id: str
    change_kind: str
    handler_name: str
    routing_status: Literal["routed", "not_implemented"]
    message: str
    suggested_cli: str | None = None
    applied: bool = False
    target_path: str | None = None
    evidence_hash: str | None = None
