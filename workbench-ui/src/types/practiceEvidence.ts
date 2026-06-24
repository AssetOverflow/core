export type PracticeEvidenceStatus = "recorded" | "missing_evidence";
export type PracticeRecordKind = "sealed_trace" | "trace_refusal" | null;

export type PracticeCardKind =
  | "problem_frame"
  | "contract_assessment"
  | "residuals"
  | "search_gate"
  | "compute_budget"
  | "geometric_search_run"
  | "candidate_attempts"
  | "attempt_bindings"
  | "replay_results"
  | "replay_refusals"
  | "sealed_trace"
  | "trace_refusal";

export interface PracticeSourceSpanView {
  text: string;
  start: number;
  end: number;
  sentence_index: number | null;
}

export interface PracticeEvidenceCard {
  kind: PracticeCardKind;
  status: PracticeEvidenceStatus;
  refs: string[];
  summary: string;
}

export interface SealedPracticeTraceView {
  trace_id: string;
  trace_policy_version: string;
  input_digest: string;
  problem_frame_digest: string;
  original_contract_assessment_id: string;
  residual_ids: string[];
  search_gate_decision_id: string;
  compute_budget_id: string;
  geometric_search_run_id: string;
  candidate_attempt_ids: string[];
  candidate_attempt_binding_ids: string[];
  replay_result_ids: string[];
  replay_refusal_ids: string[];
  upstream_identity_chain: string[];
  practice_disposition: string;
  trace_records: string[];
  evidence_spans: PracticeSourceSpanView[];
  created_by_policy: string;
  explanation: string;
}

export interface PracticeTraceRefusalView {
  trace_refusal_id: string;
  trace_policy_version: string;
  input_digest: string | null;
  practice_disposition: string;
  reason_codes: string[];
  explanation: string;
}

export interface PracticeEvidence {
  schema_version: "practice_evidence_v1";
  turn_id: number;
  status: PracticeEvidenceStatus;
  missing_reason: string | null;
  record_kind: PracticeRecordKind;
  practice_disposition: string | null;
  chain: PracticeEvidenceCard[];
  sealed_trace: SealedPracticeTraceView | null;
  trace_refusal: PracticeTraceRefusalView | null;
  diagnostic_only: boolean;
  serving_allowed: boolean;
  mutation_allowed: boolean;
  replay_execution_allowed: boolean;
  replay_executed_by_workbench: boolean;
}
