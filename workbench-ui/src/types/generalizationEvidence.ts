export type ChecksumStatus = "verified" | "missing" | "mismatch" | "unknown";
export type GeneralizationReportKind =
  | "committed_pin"
  | "ephemeral_local"
  | "rebaseline_candidate"
  | "unknown";

export interface GeneralizationManifestSummary {
  dataset: string;
  manifest_path: string;
  split_names: string[];
  license: string | null;
  checksum_status: ChecksumStatus;
  sealed_splits: string[];
  policy_version: string;
}

export interface GeneralizationCacheStatus {
  dataset: string;
  cache_path: string;
  present: boolean;
  verified: boolean;
  reason: string | null;
}

export interface GeneralizationAuditReportView {
  policy_version: string;
  dataset: string;
  split: string;
  n_items: number;
  correct: number;
  wrong: number;
  refused: number;
  unsupported: number;
  candidate_attempts: number;
  binding_failures: number;
  replay_refusals: number;
  sealed_trace_dispositions: [string, number][];
  dominant_residual_kinds: [string, number][];
  reason_codes: string[];
  source_path: string | null;
  source_digest: string | null;
  report_kind: GeneralizationReportKind;
  audit_only: boolean;
  raw_items_exposed: boolean;
}
