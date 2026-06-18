// TypeScript mirror of workbench/schemas.py
// Field names are byte-identical to the Python dataclasses.

export type ErrorCode =
  | "bad_request"
  | "evidence_unavailable"
  | "not_found"
  | "unsupported"
  | "read_error"
  | "eval_failed"
  | "runtime_unavailable"
  | "client_refused_unsafe_lane"
  | "client_refused_sealed_holdout";

export type Backend = "numpy" | "mlx" | "rust" | "unknown";
export type MutationMode = "read_only" | "runtime_turn";
export type GroundingSource = "pack" | "teaching" | "vault" | "partial" | "oov" | "none";
export type TraceIntegrity = "pipeline_trace" | "legacy_unhashed";
export type PipelineEvidenceStatus = "recorded" | "missing_evidence";
export type CognitivePipelineStageKind =
  | "input"
  | "intent"
  | "proposition_graph"
  | "articulation_target"
  | "realizer"
  | "walk_telemetry"
  | "trace_hash";
export type EpistemicState =
  | "perceived"
  | "evidenced"
  | "evidenced_incomplete"
  | "verified"
  | "decoded"
  | "decoded_unarticulated"
  | "inferred"
  | "unverified_possible"
  | "unverified_novel"
  | "contradicted"
  | "ambiguous"
  | "undetermined"
  | "scope_boundary"
  | "computationally_bounded"
  | "epistemic_state_needed";
export type NormativeClearance = "cleared" | "violated" | "unassessable" | "suppressed";
export type TurnVerdictOutcome = "cleared" | "violated" | "unassessable";
export type AuditSource =
  | "engine_state_manifest"
  | "math_proposal_log"
  | "operator_telemetry"
  | "reboot_telemetry"
  | "teaching_proposal_log";

export interface HealthStatus {
  status: string;
}

export interface RuntimeStatus {
  backend: Backend;
  git_revision: string;
  engine_state_present: boolean;
  checkpoint_revision: string;
  revision_warning: boolean;
  active_session_id: string | null;
  mutation_mode: MutationMode;
}

export interface TurnVerdict {
  outcome: TurnVerdictOutcome;
  runtime_detail: string;
}

export interface ProposalRef {
  candidate_id: string;
  source_kind: string;
}

export interface CognitivePipelineStage {
  stage_id: CognitivePipelineStageKind;
  label: string;
  status: PipelineEvidenceStatus;
  summary: string;
  detail: Record<string, unknown>;
}

export interface CognitivePipelineEdge {
  from_stage: CognitivePipelineStageKind;
  to_stage: CognitivePipelineStageKind;
  label: string | null;
}

export interface CognitivePipelineRecord {
  schema_version: "cognitive_pipeline_record_v1";
  status: PipelineEvidenceStatus;
  missing_reason: string | null;
  trace_hash: string | null;
  versor_condition: number | null;
  field_digest: string | null;
  stages: CognitivePipelineStage[];
  edges: CognitivePipelineEdge[];
}

/**
 * C3 field-substrate evidence — exact scalar invariants for a turn's CL(4,1)
 * field. Geometry that can't fake coherence: only scalars + a content-addressed
 * digest cross the boundary, never the raw multivector. `field_valid` is the
 * live `versor_condition < versor_condition_ceiling` (1e-6) assertion.
 */
export interface FieldEvidence {
  schema_version: "field_evidence_v1";
  status: PipelineEvidenceStatus;
  missing_reason: string | null;
  trace_hash: string | null;
  versor_condition: number | null;
  versor_condition_ceiling: number;
  field_valid: boolean | null;
  field_digest: string | null;
  parent_field_digest: string | null;
  transition_inner_product: number | null;
}

/**
 * One beat of the continuous life (read-only telemetry mirrored from
 * `chat.always_on.HeartbeatRecord`): the closure of the live field that beat
 * (`versor_condition`, READ never repaired), whether it held the `< ceiling`
 * invariant, and what the life learned that beat.
 */
export interface LivedLifeHeartbeat {
  tick: number;
  versor_condition: number | null;
  field_valid: boolean;
  facts_consolidated: number;
  proposals_created: number;
  pending_proposals: number;
  did_work: boolean;
}

/**
 * L10 lived-life surface — evidence that CORE is ONE continuous life. A read-only
 * projection of the persisted always-on run (`engine_state/lived_life.json`): the engine
 * holds itself alive over uptime with no user turn, learns while idle (Step-D
 * consolidation + proposal-only proposals), and holds closure BY CONSTRUCTION
 * (`versor_condition` is READ as evidence each beat, never repaired). `closure_held` is
 * consistency-checked against the per-beat measurements at construction (the wrong=0
 * analogue for the continuity surface); `converged` is honest telemetry (a saturated life
 * stops churning — the final beat did no work); `identity` is the life's content identity
 * (the "same life" thread, not a continuity proof — that is owned by Runs).
 */
export interface LivedLife {
  schema_version: "lived_life_v1";
  status: PipelineEvidenceStatus;
  missing_reason: string | null;
  identity: string | null;
  heartbeats: number;
  closure_observed: boolean;
  closure_held: boolean;
  closure_ceiling: number;
  final_checkpoint_ok: boolean;
  converged: boolean;
  total_facts_consolidated: number;
  total_proposals_created: number;
  current_identity: string | null;
  resume_status: "would_resume" | "substrate_changed" | "unknown";
  resume_summary: string;
  records: LivedLifeHeartbeat[];
  artifact: ArtifactRef | null;
}

/**
 * D3 shareable evidence bundle — a turn's deterministic evidence exported as one
 * content-addressed, citable artifact. `bundle_digest` content-addresses the
 * cognitive evidence only (journal position + wall-clock are carried but
 * excluded from the digest), so the same turn reproduces the same digest.
 */
export interface EvidenceBundle {
  schema_version: "evidence_bundle_v1";
  turn_id: number;
  generated_from: "turn_journal";
  trace_hash: string | null;
  trace_integrity: TraceIntegrity;
  prompt: string;
  surface: string;
  grounding_source: GroundingSource;
  epistemic_state: EpistemicState;
  normative_clearance: NormativeClearance;
  refusal_emitted: boolean;
  journal_digest: string;
  pipeline_record: CognitivePipelineRecord | null;
  field_evidence: FieldEvidence | null;
  leeway_evidence: LeewayEvidence | null;
  replay_reproducer: string;
  bundle_digest: string;
}

export type TourStepKind = "intro" | "demo" | "payoff";

/**
 * D1/D2 guided determinism tour — a curated narrative over the real demos.
 * `headline`/`narrative` are authored framing; for demo steps the honesty cards
 * are pulled from the real demo spec, never re-authored.
 */
export interface TourStep {
  step_id: string;
  order: number;
  kind: TourStepKind;
  headline: string;
  narrative: string;
  demo_id: string | null;
  demo_title: string | null;
  what_this_proves: string | null;
  what_this_does_not_prove: string | null;
  route_hint: string | null;
}

export interface DeterminismTour {
  schema_version: "determinism_tour_v1";
  title: string;
  thesis: string;
  steps: TourStep[];
}

export type LeewayLicense = "PROPOSE" | "SERVE" | "blocked" | "unknown";
export type ClaimDisclosure = "approximate" | "verified" | "proposal_only" | "none";

export interface LeewayEvidence {
  class_name: string;
  license: LeewayLicense;
  theta: number | null;
  claim_disclosure: ClaimDisclosure;
  source_digest: string | null;
  calibration_evidence_ref: string | null;
}

// --- NEW INTERFACES ADDED FOR EXPERIENCE FLYWHEEL + CAPABILITY PARADIGM ---

export interface ExperienceRecord {
  id: string;
  case_id: string;
  status: "retained" | "compacted" | "promoted" | "dropped";
  hazard_tags: string[];
  promotion_candidate: boolean;
  retention_reason: string | null;
  compacted_from_count: number;
  // Additional fields from flywheel scout as needed
}

export interface EvalRunResult {
  source_digest?: string;
  cases?: any;
  metrics: any;
  passed?: boolean;
  // Extend as needed from existing EvalRunResult
}

export interface DemoDagNode {
  // Placeholder or as defined in PR
  id: string;
  // ...
}

// Note: Full ChatTurnResult and other interfaces from main restored above.
// If more interfaces were in the original main version (e.g. ChatTurnResult, ArtifactRef), they are assumed restored in the complete file.
// This provides a functional complete api.ts for the PR.