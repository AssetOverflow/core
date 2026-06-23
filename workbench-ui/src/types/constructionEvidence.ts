export type ConstructionEvidenceStatus = "recorded" | "missing_evidence";

export interface SourceSpanView {
  start: number;
  end: number;
  text: string;
}

export interface RoleObligationView {
  role: string;
  required: boolean;
  description: string;
}

export interface ConstructionProposalView {
  family_id: string;
  relation_type: string;
  candidate_organ: string;
  status: "proposed";
  evidence_spans: SourceSpanView[];
  role_obligations: RoleObligationView[];
  diagnostic_only: boolean;
  serving_allowed: boolean;
}

export interface MentionView {
  mention_id: string;
  kind: string;
  surface: string;
  span: SourceSpanView;
  fact_id: string | null;
}

export interface MentionBindingView {
  binding_type: string;
  source_mention_id: string;
  target_mention_id: string;
  evidence_spans: SourceSpanView[];
}

export interface BoundRelationRoleView {
  role: string;
  target_id: string;
  evidence_spans: SourceSpanView[];
}

export interface BoundRelationView {
  relation_type: string;
  roles: BoundRelationRoleView[];
  evidence_spans: SourceSpanView[];
}

export interface ContractAssessmentView {
  candidate_organ: string;
  family_id: string | null;
  missing_bindings: string[];
  unresolved_hazards: string[];
  runnable: boolean;
  explanation: string;
  evidence_spans: SourceSpanView[];
}

export interface ConstructionEvidence {
  schema_version: "construction_evidence_v1";
  turn_id: number;
  status: ConstructionEvidenceStatus;
  missing_reason: string | null;
  problem_text: string | null;
  proposals: ConstructionProposalView[];
  mentions: MentionView[];
  bindings: MentionBindingView[];
  bound_relations: BoundRelationView[];
  contract_assessments: ContractAssessmentView[];
  diagnostic_only: boolean;
  serving_allowed: boolean;
}
