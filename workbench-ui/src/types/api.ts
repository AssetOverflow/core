export interface EvalRunResult {
  lane: string;
  version: string;
  split: string;
  passed: boolean | null;
  metrics: Record<string, unknown>;
  cases: unknown[];
  source_digest: string | null;
}

/**
 * ExperienceRecord
 *
 * Represents a compacted entry in the bounded GSM8K experience flywheel.
 * Used for practice-memory retention, hazard/family blocking, and promotion
 * candidate tracking (see PR #816 and capability paradigm work).
 */
export interface ExperienceRecord {
  id: string;
  case_id: string;
  candidate_family: string;
  arithmetic_chain_signature?: string;
  hazard_tags: string[];
  status: 'retained' | 'compacted' | 'promoted' | 'dropped';
  retention_reason?: string;
  count: number;
  source_report_hash?: string;
  source_run_id?: string;
  promotion_candidate?: boolean;
  created_at?: string;
  compacted_from_count?: number;
}

export interface DemoDagNode {