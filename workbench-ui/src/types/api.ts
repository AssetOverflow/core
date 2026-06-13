// TypeScript mirror of workbench/schemas.py
// Field names are byte-identical to the Python dataclasses.

export type ErrorCode =
  | "bad_request"
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
}

export interface TurnJournalSummary {
  turn_id: number;
  timestamp: string;
  prompt_excerpt: string;
  surface_excerpt: string;
  trace_hash: string | null;
  grounding_source: GroundingSource;
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
  journal_digest: string;
}

export type TurnEvidence = ChatTurnResult | TurnJournalEntry;

export type RunSource = "engine_state_manifest" | "turn_journal";

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
}

export interface RunDetail extends RunSummary {
  turns: RunTurnRef[];
  manifest: Record<string, unknown> | null;
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

export type ReplayDivergenceSeverity = "info" | "warning" | "failure";

export interface ReplayDivergence {
  path: string;
  original: unknown;
  replay: unknown;
  severity: ReplayDivergenceSeverity;
}

export interface ReplayComparison {
  artifact_id: string;
  original_hash: string | null;
  replay_hash: string | null;
  equivalent: boolean;
  divergences: ReplayDivergence[];
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
