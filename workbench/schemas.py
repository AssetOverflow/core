"""Typed UI-facing schemas for CORE Workbench v1."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal


ErrorCode = Literal[
    "bad_request",
    "evidence_unavailable",
    "not_found",
    "unsupported",
    "read_error",
    "eval_failed",
    "runtime_unavailable",
]

MutationMode = Literal["read_only", "runtime_turn"]
GroundingSource = Literal["pack", "teaching", "vault", "partial", "oov", "none"]
TraceIntegrity = Literal["pipeline_trace", "legacy_unhashed"]
PipelineEvidenceStatus = Literal["recorded", "missing_evidence"]
CognitivePipelineStageKind = Literal[
    "input",
    "intent",
    "proposition_graph",
    "articulation_target",
    "realizer",
    "walk_telemetry",
    "trace_hash",
]
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


def error(
    code: ErrorCode, message: str, *, detail: Any | None = None
) -> dict[str, Any]:
    payload: dict[str, Any] = {"code": code, "message": message}
    if detail is not None:
        payload["detail"] = to_data(detail)
    return {"ok": False, "generated_at": utc_now(), "error": payload}


@dataclass(frozen=True, slots=True)
class LeewayEvidence:
    class_name: str
    license: Literal["PROPOSE", "SERVE", "blocked", "unknown"]
    theta: float | None
    claim_disclosure: Literal["approximate", "verified", "proposal_only", "none"]
    source_digest: str | None
    calibration_evidence_ref: str | None


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
class CognitivePipelineStage:
    stage_id: CognitivePipelineStageKind
    label: str
    status: PipelineEvidenceStatus
    summary: str
    detail: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class CognitivePipelineEdge:
    from_stage: CognitivePipelineStageKind
    to_stage: CognitivePipelineStageKind
    label: str | None = None


@dataclass(frozen=True, slots=True)
class CognitivePipelineRecord:
    schema_version: Literal["cognitive_pipeline_record_v1"]
    status: PipelineEvidenceStatus
    missing_reason: str | None
    trace_hash: str | None
    versor_condition: float | None
    field_digest: str | None
    stages: list[CognitivePipelineStage] = field(default_factory=list)
    edges: list[CognitivePipelineEdge] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class FieldEvidence:
    """C3 field-substrate evidence: exact scalar invariants for a turn's field.

    Honest, read-only geometry: the engine owns the CL(4,1) field; this record
    surfaces only the EXACT scalars it computes (``versor_condition``, the
    ``cga_inner`` transition value) plus a content-addressed ``field_digest`` —
    NEVER the raw multivector (the geometry can't fake coherence, so we show the
    numbers, not a decorative blob).  ``field_valid`` is the live
    ``versor_condition < 1e-6`` assertion; it is consistency-checked against the
    ceiling at construction (see ``workbench.field_evidence.validate``).
    """

    schema_version: Literal["field_evidence_v1"]
    status: PipelineEvidenceStatus
    missing_reason: str | None
    trace_hash: str | None
    versor_condition: float | None
    versor_condition_ceiling: float
    field_valid: bool | None
    field_digest: str | None
    parent_field_digest: str | None
    transition_inner_product: float | None


@dataclass(frozen=True, slots=True)
class EvidenceBundle:
    """D3 shareable evidence bundle — a turn's deterministic evidence, citable.

    Reproducibility as a deliverable: a content-addressed export of the
    DETERMINISTIC subset of a turn (the wall-clock fields — timestamp,
    turn_cost_ms — are deliberately omitted) so the same turn always yields the
    same bytes and the same ``bundle_digest``.  Anyone can re-run the prompt
    over a sealed runtime and check the trace_hash, then recompute the bundle
    and check ``bundle_digest`` — the bundle is the citable claim, the
    reproducer is how to verify it.  It composes the Phase-C evidence
    (pipeline + field) with the trace and the calibration leeway verdict.
    """

    schema_version: Literal["evidence_bundle_v1"]
    turn_id: int
    generated_from: Literal["turn_journal"]
    trace_hash: str | None
    trace_integrity: TraceIntegrity
    prompt: str
    surface: str
    grounding_source: GroundingSource
    epistemic_state: EpistemicStateValue
    normative_clearance: NormativeClearanceValue
    refusal_emitted: bool
    journal_digest: str
    pipeline_record: CognitivePipelineRecord | None
    field_evidence: FieldEvidence | None
    leeway_evidence: LeewayEvidence | None
    replay_reproducer: str
    bundle_digest: str


TourStepKind = Literal["intro", "demo", "payoff"]


@dataclass(frozen=True, slots=True)
class TourStep:
    """One step of the guided determinism tour.

    ``headline`` / ``narrative`` are the authored, provider-agnostic framing.
    For ``kind == "demo"`` steps the honesty cards (``what_this_proves`` /
    ``what_this_does_not_prove``) and ``demo_title`` are pulled from the REAL
    demo spec at build time — never re-authored — so the tour cannot claim more
    than the demo it points at.  ``route_hint`` is where to go deeper.
    """

    step_id: str
    order: int
    kind: TourStepKind
    headline: str
    narrative: str
    demo_id: str | None
    demo_title: str | None
    what_this_proves: str | None
    what_this_does_not_prove: str | None
    route_hint: str | None


@dataclass(frozen=True, slots=True)
class DeterminismTour:
    """D1/D2 guided determinism tour — a curated narrative over real demos.

    The ``thesis`` is the provider-agnostic pitch: bring a claim from any model
    and watch the deterministic engine decide, refuse, and replay it — proposer
    authority ignored.  ``steps`` are ordered and each demo step is bound to a
    real entry in the demo registry (fail-closed if a demo id is missing).
    """

    schema_version: Literal["determinism_tour_v1"]
    title: str
    thesis: str
    steps: list[TourStep] = field(default_factory=list)


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
    leeway_evidence: LeewayEvidence | None = None
    pipeline_record: CognitivePipelineRecord | None = None
    field_evidence: FieldEvidence | None = None
    turn_id: int | None = None


@dataclass(frozen=True, slots=True)
class TurnJournalSummarySchema:
    turn_id: int
    timestamp: str
    prompt_excerpt: str
    surface_excerpt: str
    trace_hash: str | None
    grounding_source: GroundingSource
    trace_integrity: TraceIntegrity


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
    trace_integrity: TraceIntegrity
    journal_digest: str
    leeway_evidence: LeewayEvidence | None = None
    pipeline_record: CognitivePipelineRecord | None = None
    field_evidence: FieldEvidence | None = None


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
    leeway_evidence: LeewayEvidence | None = None


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


EvidenceClass = Literal[
    "substrate_capability",
    "interface_contract",
    "simulation_only",
    "proposed",
]
DemoEvidenceDagKind = Literal[
    "proof_carrying_promotion",
    "deductive_entailment",
]


@dataclass(frozen=True, slots=True)
class DemoDagNode:
    node_id: str
    label: str
    summary: str
    detail: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class DemoDagEdge:
    from_node: str
    to_node: str
    label: str | None = None


@dataclass(frozen=True, slots=True)
class DemoEvidenceDag:
    graph_id: str
    graph_kind: DemoEvidenceDagKind
    title: str
    source_digest: str | None
    nodes: list[DemoDagNode] = field(default_factory=list)
    edges: list[DemoDagEdge] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class DemoScenarioSummary:
    scenario_id: str
    title: str
    expected_status: str
    evidence_class: EvidenceClass
    proposer_wrong: bool
    what_this_proves: str
    what_this_does_not_prove: str


@dataclass(frozen=True, slots=True)
class DemoSummary:
    demo_id: str
    title: str
    description: str
    evidence_class: EvidenceClass
    scenario_count: int
    read_only: bool
    scenarios: list[DemoScenarioSummary] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class DemoScenarioRunResult:
    scenario_id: str
    status: str
    passed: bool
    proposer_wrong: bool
    evidence_class: EvidenceClass
    decision_reason: str | None
    trace_hash: str | None
    problems: list[str] = field(default_factory=list)
    response: Any = None
    evidence_dag: DemoEvidenceDag | None = None


@dataclass(frozen=True, slots=True)
class DemoRunResult:
    demo_id: str
    all_passed: bool
    what_this_proves: str
    what_this_does_not_prove: str
    scenarios: list[DemoScenarioRunResult] = field(default_factory=list)


# Canonical ADR-0172 learning-arc stages (cold attempt → engine enrichment →
# engine-authored proposal → operator ratifies → grounded). "other" is the
# explicit fallback for any scene id outside the closed arc.
ContemplationStageRole = Literal[
    "cold_attempt",
    "engine_enrichment",
    "engine_proposal",
    "operator_ratifies",
    "grounded",
    "other",
]


@dataclass(frozen=True, slots=True)
class ContemplationScene:
    scene_id: str
    claim: str
    detail: dict[str, Any] = field(default_factory=dict)
    # Typed projection of the contemplation *loop* — the role this scene plays
    # and the connective ids that thread it to the proposal / candidate
    # surfaces. ``proposal_id`` etc. are surfaced as evidence; cross-route
    # navigation lights up only when the id resolves in the live log.
    stage_role: ContemplationStageRole = "other"
    proposal_id: str | None = None
    candidate_id: str | None = None
    proposal_state: str | None = None
    grounding_source: str | None = None


@dataclass(frozen=True, slots=True)
class ContemplationRunSummary:
    run_id: str
    source_path: str
    source_digest: str | None
    prompt: str | None
    cold_subject: str | None
    scene_count: int
    learning_arc_closed: bool | None
    all_claims_supported: bool | None
    active_corpus_byte_identical: bool | None


@dataclass(frozen=True, slots=True)
class ContemplationRunDetail(ContemplationRunSummary):
    before: dict[str, Any] | None = None
    after: dict[str, Any] | None = None
    engine_chain: dict[str, Any] | None = None
    scenes: list[ContemplationScene] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Wave R3 — sealed single-turn replay over the turn journal.
# Scoping: docs/analysis/replay-moment-backend-scoping-2026-06-12.md.
# The W-026 artifact-keyed pair above has no live consumer and is retired
# when the frontend Replay Moment re-points to this turn-keyed shape.
# ---------------------------------------------------------------------------

TurnReplayDivergenceSeverity = Literal["critical", "informational"]
# The only basis implemented: a fresh ChatRuntime(no_load_state=True) —
# genesis substrate, no checkpoint load, no checkpoint write, no proposal
# lineage — re-executes the recorded prompt once.
TurnReplayBasis = Literal["sealed_fresh_runtime_single_turn"]
# The journal does not record whether an engine-state checkpoint existed
# when the original turn ran, so the origin state is honestly unrecorded:
# a divergence means nondeterminism OR origin-state influence, and the
# response must never claim to distinguish them.
TurnReplayOriginState = Literal["unrecorded"]


@dataclass(frozen=True, slots=True)
class TurnReplayDivergence:
    path: str
    original: Any
    replay: Any
    severity: TurnReplayDivergenceSeverity


@dataclass(frozen=True, slots=True)
class TurnReplayComparison:
    turn_id: int
    comparison_basis: TurnReplayBasis
    origin_state: TurnReplayOriginState
    original_trace_hash: str | None
    replay_trace_hash: str | None
    equivalent: bool
    replay_turn_cost_ms: int
    divergences: list[TurnReplayDivergence] = field(default_factory=list)
    leeway_evidence: LeewayEvidence | None = None


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
    leeway_evidence: LeewayEvidence | None = None


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


PackSource = Literal["language_pack", "runtime_pack"]


@dataclass(frozen=True, slots=True)
class PackSummary:
    pack_id: str
    source: PackSource
    manifest_path: str
    version: str | None
    language: str | None
    modality: str | None
    determinism_class: str | None
    checksum: str | None
    checksums: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class PackDetail(PackSummary):
    manifest_digest: str = ""
    manifest: dict[str, Any] = field(default_factory=dict)


AuditSource = Literal[
    "engine_state_manifest",
    "math_proposal_log",
    "operator_telemetry",
    "reboot_telemetry",
    "teaching_proposal_log",
]


@dataclass(frozen=True, slots=True)
class AuditEvent:
    event_id: str
    source: AuditSource
    source_path: str
    timestamp: str | None
    event_type: str
    mutation_boundary: bool
    summary: str
    ref_id: str | None
    payload_digest: str
    payload: Any


RunSource = Literal["engine_state_manifest", "turn_journal"]
IdentityContinuityStatus = Literal["verified", "break", "missing_evidence"]
IdentityLineageRelation = Literal[
    "self_parent",
    "descends_from_parent",
    "missing_parent",
    "unavailable",
]


@dataclass(frozen=True, slots=True)
class IdentityContinuity:
    status: IdentityContinuityStatus
    engine_identity: str | None
    parent_engine_identity: str | None
    current_engine_identity: str | None
    written_at_revision: str | None
    current_revision: str
    lineage_relation: IdentityLineageRelation
    verification_summary: str
    evidence_gap: str | None = None


@dataclass(frozen=True, slots=True)
class RunSummary:
    session_id: str
    source: RunSource
    turn_count: int
    started_at: str | None
    updated_at: str | None
    checkpoint_present: bool
    checkpoint_revision: str | None
    artifact_refs: list[ArtifactRef] = field(default_factory=list)
    evidence_gap: str | None = None


@dataclass(frozen=True, slots=True)
class RunTurnRef:
    turn_id: int
    trace_hash: str | None
    timestamp: str
    trace_path: str
    surface_excerpt: str
    trace_integrity: TraceIntegrity


@dataclass(frozen=True, slots=True)
class RunDetail(RunSummary):
    turns: list[RunTurnRef] = field(default_factory=list)
    manifest: dict[str, Any] | None = None
    identity_continuity: IdentityContinuity | None = None


@dataclass(frozen=True, slots=True)
class VaultSummary:
    source_path: str
    entry_count: int
    store_count: int
    reproject_interval: int
    max_entries: int | None
    persisted: bool


@dataclass(frozen=True, slots=True)
class VaultEntry:
    entry_index: int
    epistemic_status: str
    epistemic_state: str
    metadata: dict[str, Any]
    versor_digest: str | None


# ---------------------------------------------------------------------------
# Wave M Phase B — calibrated-learning / serving-discipline read views.
# The workbench computes none of these numbers: reliability_floor and the
# license verdicts come from core.reliability_gate's own conservative_floor /
# license_for; serving counts come from committed eval report.json artifacts.
# Read-only — no lane is re-run, no license is changed.
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CalibrationClass:
    class_name: str
    correct: int
    wrong: int
    refused: int
    committed: int
    # One-sided Wilson conservative floor (0.0 below N_MIN committed trials).
    reliability_floor: float
    coverage: float
    propose_required: float  # θ for PROPOSE (0.85)
    propose_licensed: bool
    serve_required: float  # θ for SERVE (0.99)
    serve_licensed: bool
    source_path: str
    source_digest: str


@dataclass(frozen=True, slots=True)
class ServingMetrics:
    lane: str
    correct: int
    refused: int
    wrong: int
    sample_count: int
    source_path: str
    source_digest: str
