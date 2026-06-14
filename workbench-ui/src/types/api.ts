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

export interface ChatTurnResult {
  prompt: string;
  /** Journal id stamped by the workbench API; null if journaling failed. */
  turn_id?: number | null;
  surface: string;
  articulation_surface: string | null;
  walk_surface: string | null;
  grounding_source: GroundingSource;
  epistemic_state: EpistemicState;
  normative_clearance: NormativeClearance;
  normative_detail: string;
  trace_hash: string | null;
  refusal_emitted: boolean;
  hedge_injected: boolean;
  mutation_mode: MutationMode;
  identity_verdict: TurnVerdict | null;
  safety_verdict: TurnVerdict | null;
  ethics_verdict: TurnVerdict | null;
  proposal_candidates: ProposalRef[];
  turn_cost_ms: number;
  checkpoint_emitted: boolean;
  leeway_evidence?: LeewayEvidence | null;
  pipeline_record?: CognitivePipelineRecord | null;
  field_evidence?: FieldEvidence | null;
}

export interface TurnJournalSummary {
  turn_id: number;
  timestamp: string;
  prompt_excerpt: string;
  surface_excerpt: string;
  trace_hash: string | null;
  grounding_source: GroundingSource;
  trace_integrity: TraceIntegrity;
}

export interface TurnJournalEntry {
  turn_id: number;
  timestamp: string;
  trace_hash: string | null;
  prompt: string;
  surface: string;
  articulation_surface: string | null;
  walk_surface: string | null;
  grounding_source: GroundingSource;
  epistemic_state: EpistemicState;
  normative_clearance: NormativeClearance;
  verdicts: Record<string, unknown>;
  refusal_emitted: boolean;
  hedge_injected: boolean;
  proposal_candidates: Record<string, unknown>[];
  turn_cost_ms: number;
  checkpoint_emitted: boolean;
  trace_integrity: TraceIntegrity;
  journal_digest: string;
  leeway_evidence?: LeewayEvidence | null;
  pipeline_record?: CognitivePipelineRecord | null;
  field_evidence?: FieldEvidence | null;
}

export type TurnEvidence = ChatTurnResult | TurnJournalEntry;

export type RunSource = "engine_state_manifest" | "turn_journal";
export type IdentityContinuityStatus = "verified" | "break" | "missing_evidence";
export type IdentityLineageRelation =
  | "self_parent"
  | "descends_from_parent"
  | "missing_parent"
  | "unavailable";

export interface IdentityContinuity {
  status: IdentityContinuityStatus;
  engine_identity: string | null;
  parent_engine_identity: string | null;
  current_engine_identity: string | null;
  written_at_revision: string | null;
  current_revision: string;
  lineage_relation: IdentityLineageRelation;
  verification_summary: string;
  evidence_gap: string | null;
}

export interface RunSummary {
  session_id: string;
  source: RunSource;
  turn_count: number;
  started_at: string | null;
  updated_at: string | null;
  checkpoint_present: boolean;
  checkpoint_revision: string | null;
  artifact_refs: ArtifactRef[];
  evidence_gap: string | null;
}

export interface RunTurnRef {
  turn_id: number;
  trace_hash: string | null;
  timestamp: string;
  trace_path: string;
  surface_excerpt: string;
  trace_integrity: TraceIntegrity;
}

export interface RunDetail extends RunSummary {
  turns: RunTurnRef[];
  manifest: Record<string, unknown> | null;
  identity_continuity: IdentityContinuity | null;
}

export interface AuditEvent {
  event_id: string;
  source: AuditSource;
  source_path: string;
  timestamp: string | null;
  event_type: string;
  mutation_boundary: boolean;
  summary: string;
  ref_id: string | null;
  payload_digest: string;
  payload: unknown;
}

export type PackSource = "language_pack" | "runtime_pack";

export interface PackSummary {
  pack_id: string;
  source: PackSource;
  manifest_path: string;
  version: string | null;
  language: string | null;
  modality: string | null;
  determinism_class: string | null;
  checksum: string | null;
  checksums: Record<string, string>;
}

export interface PackDetail extends PackSummary {
  manifest_digest: string;
  manifest: Record<string, unknown>;
}

export type ArtifactKind =
  | "trace"
  | "eval_result"
  | "proposal"
  | "contemplation_report"
  | "telemetry"
  | "engine_state_manifest"
  | "unknown";

export type ContentType = "json" | "jsonl" | "text" | "unknown";

export interface ArtifactRef {
  artifact_id: string;
  kind: ArtifactKind;
  path: string;
  digest: string | null;
  created_at: string | null;
}

export interface ArtifactDetail extends ArtifactRef {
  content_type: ContentType;
  content: unknown;
}

export type ProposalState =
  | "pending"
  | "accepted"
  | "rejected"
  | "withdrawn"
  | "unknown";

export type DownstreamEffect = "unknown" | "none" | "observed";

export interface ProposalSummary {
  proposal_id: string;
  state: ProposalState;
  source_kind: string;
  replay_equivalent: boolean | null;
  created_at: string | null;
  downstream_effect: DownstreamEffect;
}

export interface ProposalDetail extends ProposalSummary {
  proposed_chain: unknown;
  replay_evidence: unknown;
  source: unknown;
  evidence: unknown[];
  artifact_refs: ArtifactRef[];
  suggested_cli: string | null;
  leeway_evidence?: LeewayEvidence | null;
}

export interface EvalLaneSummary {
  lane: string;
  versions: string[];
  read_only: boolean;
  description: string | null;
}

export interface EvalRunRequest {
  lane: string;
  version?: string;
  split?: "dev" | "public" | "holdout";
}

export interface EvalRunResult {
  lane: string;
  version: string;
  split: string;
  passed: boolean | null;
  metrics: Record<string, unknown>;
  cases: unknown[];
  source_digest: string | null;
}

export type EvidenceClass =
  | "substrate_capability"
  | "interface_contract"
  | "simulation_only"
  | "proposed";
export type DemoEvidenceDagKind = "proof_carrying_promotion" | "deductive_entailment";

export interface DemoDagNode {
  node_id: string;
  label: string;
  summary: string;
  detail: Record<string, unknown>;
}

export interface DemoDagEdge {
  from_node: string;
  to_node: string;
  label: string | null;
}

export interface DemoEvidenceDag {
  graph_id: string;
  graph_kind: DemoEvidenceDagKind;
  title: string;
  source_digest: string | null;
  nodes: DemoDagNode[];
  edges: DemoDagEdge[];
}

export interface DemoScenarioSummary {
  scenario_id: string;
  title: string;
  expected_status: string;
  evidence_class: EvidenceClass;
  proposer_wrong: boolean;
  what_this_proves: string;
  what_this_does_not_prove: string;
}

export interface DemoSummary {
  demo_id: string;
  title: string;
  description: string;
  evidence_class: EvidenceClass;
  scenario_count: number;
  read_only: boolean;
  scenarios: DemoScenarioSummary[];
}

export interface DemoScenarioRunResult {
  scenario_id: string;
  status: string;
  passed: boolean;
  proposer_wrong: boolean;
  evidence_class: EvidenceClass;
  decision_reason: string | null;
  trace_hash: string | null;
  problems: string[];
  response: unknown;
  evidence_dag?: DemoEvidenceDag | null;
}

export interface DemoRunResult {
  demo_id: string;
  all_passed: boolean;
  what_this_proves: string;
  what_this_does_not_prove: string;
  scenarios: DemoScenarioRunResult[];
}

export type ContemplationStageRole =
  | "cold_attempt"
  | "engine_enrichment"
  | "engine_proposal"
  | "operator_ratifies"
  | "grounded"
  | "other";

export interface ContemplationScene {
  scene_id: string;
  claim: string;
  detail: Record<string, unknown>;
  stage_role: ContemplationStageRole;
  proposal_id: string | null;
  candidate_id: string | null;
  proposal_state: string | null;
  grounding_source: string | null;
}

export interface ContemplationRunSummary {
  run_id: string;
  source_path: string;
  source_digest: string | null;
  prompt: string | null;
  cold_subject: string | null;
  scene_count: number;
  learning_arc_closed: boolean | null;
  all_claims_supported: boolean | null;
  active_corpus_byte_identical: boolean | null;
}

export interface ContemplationRunDetail extends ContemplationRunSummary {
  before: Record<string, unknown> | null;
  after: Record<string, unknown> | null;
  engine_chain: Record<string, unknown> | null;
  scenes: ContemplationScene[];
}

// Wave R3 — sealed single-turn replay (turn-keyed; supersedes the W-026
// artifact-keyed ReplayComparison, now retired on both sides).
export type TurnReplayDivergenceSeverity = "critical" | "informational";
export type TurnReplayBasis = "sealed_fresh_runtime_single_turn";
export type TurnReplayOriginState = "unrecorded";

export interface TurnReplayDivergence {
  path: string;
  original: unknown;
  replay: unknown;
  severity: TurnReplayDivergenceSeverity;
}

export interface TurnReplayComparison {
  turn_id: number;
  comparison_basis: TurnReplayBasis;
  origin_state: TurnReplayOriginState;
  original_trace_hash: string | null;
  replay_trace_hash: string | null;
  equivalent: boolean;
  replay_turn_cost_ms: number;
  divergences: TurnReplayDivergence[];
  leeway_evidence?: LeewayEvidence | null;
}

export interface VaultSummary {
  source_path: string;
  entry_count: number;
  store_count: number;
  reproject_interval: number;
  max_entries: number | null;
  persisted: boolean;
}

export interface VaultEntry {
  entry_index: number;
  epistemic_status: string;
  epistemic_state: string;
  metadata: Record<string, unknown>;
  versor_digest: string | null;
}

// Wave M Phase B — calibrated-learning / serving-discipline read views.
// reliability_floor + the license verdicts are computed by the engine
// (core.reliability_gate), never the workbench.
export interface CalibrationClass {
  class_name: string;
  correct: number;
  wrong: number;
  refused: number;
  committed: number;
  reliability_floor: number;
  coverage: number;
  propose_required: number;
  propose_licensed: boolean;
  serve_required: number;
  serve_licensed: boolean;
  source_path: string;
  source_digest: string;
}

export interface ServingMetrics {
  lane: string;
  correct: number;
  refused: number;
  wrong: number;
  sample_count: number;
  source_path: string;
  source_digest: string;
}

// API envelope types
export interface ApiOk<T> {
  ok: true;
  generated_at: string;
  data: T;
}

export interface ApiError {
  ok: false;
  generated_at: string;
  error: {
    code: ErrorCode;
    message: string;
    detail?: unknown;
  };
}

export type ApiResponse<T> = ApiOk<T> | ApiError;

export interface MathReasoningStep {
  step_index: number;
  step_kind: string;
  claim: string;
  justification: string;
  input_pointers: string[];
  output_payload: unknown;
}

export interface MathProposalSummary {
  proposal_id: string;
  domain: "math";
  shape_category: string;
  proposed_change_kind: string;
  structural_commonality: string;
  evidence_count: number;
  replay_equivalence_hash: string;
}

export interface MathProposalDetail extends MathProposalSummary {
  wrong_zero_assertion: string;
  proposed_change_payload: unknown;
  reasoning_trace_id: string;
  reasoning_trace_steps: MathReasoningStep[];
  evidence_hashes: string[];
  handler_name: string | null;
  suggested_ratify_cli: string | null;
  leeway_evidence?: LeewayEvidence | null;
}

export interface MathRatifyResult {
  proposal_id: string;
  change_kind: string;
  handler_name: string;
  routing_status: "routed" | "not_implemented";
  message: string;
  suggested_cli: string | null;
  applied: boolean;
  target_path: string | null;
  evidence_hash: string | null;
}
