// TypeScript mirror of workbench/schemas.py
// Field names are byte-identical to the Python dataclasses.

export type ErrorCode =
  | "bad_request"
  | "not_found"
  | "unsupported"
  | "read_error"
  | "eval_failed"
  | "runtime_unavailable";

export type Backend = "numpy" | "mlx" | "rust" | "unknown";
export type MutationMode = "read_only" | "runtime_turn";

export interface RuntimeStatus {
  backend: Backend;
  git_revision: string;
  engine_state_present: boolean;
  checkpoint_revision: string;
  revision_warning: boolean;
  active_session_id: string | null;
  mutation_mode: MutationMode;
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
