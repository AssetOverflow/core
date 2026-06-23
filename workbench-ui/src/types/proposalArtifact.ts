export type ProposalCapabilityLevel =
  | "inspect_only"
  | "proposal_only"
  | "ratification_enabled";

export type ProposalArtifactState =
  | "pending"
  | "accepted"
  | "rejected"
  | "withdrawn"
  | "deferred"
  | "unknown";

export interface ProposalSubject {
  kind: string;
  subject_id: string;
  display_name: string;
}

export interface EvidencePointer {
  kind: string;
  ref: string;
  label: string;
  digest: string | null;
}

export interface ProposalValidationReport {
  status: "valid" | "blocked" | "unknown";
  blockers: string[];
  warnings: string[];
}

export interface ProposalSafetyReport {
  status: "clear" | "warning" | "failed" | "unknown";
  disclosures: string[];
}

export interface ProposalArtifact {
  proposal_id: string;
  subject: ProposalSubject;
  state: ProposalArtifactState;
  capability_level: ProposalCapabilityLevel;
  source_kind: string;
  proposed_change: unknown;
  reasoning_trace: unknown;
  evidence_pointers: EvidencePointer[];
  validation: ProposalValidationReport | null;
  replay_evidence: unknown;
  safety_report: ProposalSafetyReport | null;
  affected_artifacts: EvidencePointer[];
  handler_route: string | null;
  suggested_cli: string | null;
  audit_refs: EvidencePointer[];
  ui_disclosure: string;
}
