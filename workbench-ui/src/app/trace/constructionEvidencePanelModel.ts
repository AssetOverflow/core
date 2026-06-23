import type {
  BoundRelationRoleView,
  ConstructionEvidence,
  SourceSpanView,
} from "../../types/constructionEvidence";
import {
  assessmentBlockerSummary,
  assessmentDisposition,
  constructionEvidenceEmptyMessage,
  sourceSpanIsExact,
  sourceSpanLabel,
} from "./constructionEvidenceView";
import { traceConstructionReproducer } from "./constructionEvidenceEndpoint";

export interface ConstructionEvidenceSummaryRow {
  key: string;
  value: string;
}

export interface ConstructionEvidenceDetailItem {
  title: string;
  rows: ConstructionEvidenceSummaryRow[];
}

export interface ConstructionEvidenceDetailSection {
  title: string;
  emptyMessage: string;
  items: ConstructionEvidenceDetailItem[];
}

export interface ConstructionEvidencePanelModel {
  status: ConstructionEvidence["status"];
  emptyMessage: string | null;
  reproducer: string;
  authorityRows: ConstructionEvidenceSummaryRow[];
  countRows: ConstructionEvidenceSummaryRow[];
  assessmentRows: ConstructionEvidenceSummaryRow[];
  detailSections: ConstructionEvidenceDetailSection[];
  sourceSpanRows: ConstructionEvidenceSummaryRow[];
  showRaw: boolean;
}

function boolLabel(value: boolean): string {
  return value ? "true" : "false";
}

function noneIfEmpty(values: readonly string[]): string {
  return values.length > 0 ? values.join(", ") : "none";
}

function spanExactness(problemText: string | null, span: SourceSpanView): string {
  const exactness = sourceSpanIsExact(problemText, span) ? "exact" : "inexact";
  return `${sourceSpanLabel(span)} — ${exactness}`;
}

function spanList(problemText: string | null, spans: readonly SourceSpanView[]): string {
  return spans.length > 0
    ? spans.map((span) => spanExactness(problemText, span)).join("; ")
    : "none";
}

function roleList(roles: readonly BoundRelationRoleView[]): string {
  return roles.length > 0
    ? roles.map((role) => `${role.role}=${role.target_id}`).join(", ")
    : "none";
}

function sourceSpanRows(evidence: ConstructionEvidence): ConstructionEvidenceSummaryRow[] {
  const rows: ConstructionEvidenceSummaryRow[] = [];
  evidence.proposals.forEach((proposal, index) => {
    proposal.evidence_spans.forEach((span, spanIndex) => {
      rows.push({
        key: `proposal ${index + 1}.${spanIndex + 1}`,
        value: spanExactness(evidence.problem_text, span),
      });
    });
  });
  evidence.mentions.forEach((mention) => {
    rows.push({
      key: `mention ${mention.mention_id}`,
      value: spanExactness(evidence.problem_text, mention.span),
    });
  });
  evidence.bindings.forEach((binding, index) => {
    binding.evidence_spans.forEach((span, spanIndex) => {
      rows.push({
        key: `binding ${index + 1}.${spanIndex + 1}`,
        value: spanExactness(evidence.problem_text, span),
      });
    });
  });
  evidence.bound_relations.forEach((relation, relationIndex) => {
    relation.evidence_spans.forEach((span, spanIndex) => {
      rows.push({
        key: `bound_relation ${relationIndex + 1}.${spanIndex + 1}`,
        value: spanExactness(evidence.problem_text, span),
      });
    });
    relation.roles.forEach((role, roleIndex) => {
      role.evidence_spans.forEach((span, spanIndex) => {
        rows.push({
          key: `bound_relation ${relationIndex + 1}.role ${roleIndex + 1}.${spanIndex + 1}`,
          value: spanExactness(evidence.problem_text, span),
        });
      });
    });
  });
  evidence.contract_assessments.forEach((assessment, index) => {
    assessment.evidence_spans.forEach((span, spanIndex) => {
      rows.push({
        key: `contract_assessment ${index + 1}.${spanIndex + 1}`,
        value: spanExactness(evidence.problem_text, span),
      });
    });
  });
  return rows;
}

function detailSections(evidence: ConstructionEvidence): ConstructionEvidenceDetailSection[] {
  return [
    {
      title: "Proposals",
      emptyMessage: "No construction proposals recorded.",
      items: evidence.proposals.map((proposal, index) => ({
        title: `proposal ${index + 1}: ${proposal.candidate_organ}`,
        rows: [
          { key: "family_id", value: proposal.family_id },
          { key: "relation_type", value: proposal.relation_type },
          { key: "status", value: proposal.status },
          { key: "diagnostic_only", value: boolLabel(proposal.diagnostic_only) },
          { key: "serving_allowed", value: boolLabel(proposal.serving_allowed) },
          {
            key: "authority",
            value: "diagnostic proposal only; contract assessment determines runnable status",
          },
          {
            key: "role_obligations",
            value:
              proposal.role_obligations.length > 0
                ? proposal.role_obligations
                    .map(
                      (role) =>
                        `${role.role} ${role.required ? "required" : "optional"} — ${role.description}`,
                    )
                    .join("; ")
                : "none",
          },
          { key: "evidence_spans", value: spanList(evidence.problem_text, proposal.evidence_spans) },
        ],
      })),
    },
    {
      title: "Mentions",
      emptyMessage: "No mentions recorded.",
      items: evidence.mentions.map((mention) => ({
        title: `mention ${mention.mention_id}: ${mention.surface}`,
        rows: [
          { key: "kind", value: mention.kind },
          { key: "surface", value: mention.surface },
          { key: "fact_id", value: mention.fact_id ?? "none" },
          { key: "span", value: spanExactness(evidence.problem_text, mention.span) },
        ],
      })),
    },
    {
      title: "Bindings",
      emptyMessage: "No mention bindings recorded.",
      items: evidence.bindings.map((binding, index) => ({
        title: `binding ${index + 1}: ${binding.binding_type}`,
        rows: [
          { key: "binding_type", value: binding.binding_type },
          { key: "source_mention_id", value: binding.source_mention_id },
          { key: "target_mention_id", value: binding.target_mention_id },
          { key: "evidence_spans", value: spanList(evidence.problem_text, binding.evidence_spans) },
        ],
      })),
    },
    {
      title: "Bound relations",
      emptyMessage: "No bound relations recorded.",
      items: evidence.bound_relations.map((relation, index) => ({
        title: `bound relation ${index + 1}: ${relation.relation_type}`,
        rows: [
          { key: "relation_type", value: relation.relation_type },
          { key: "roles", value: roleList(relation.roles) },
          { key: "evidence_spans", value: spanList(evidence.problem_text, relation.evidence_spans) },
          {
            key: "role_spans",
            value:
              relation.roles.length > 0
                ? relation.roles
                    .map((role) => `${role.role}: ${spanList(evidence.problem_text, role.evidence_spans)}`)
                    .join("; ")
                : "none",
          },
        ],
      })),
    },
    {
      title: "Contract assessments",
      emptyMessage: "No contract assessments recorded.",
      items: evidence.contract_assessments.map((assessment, index) => ({
        title: `assessment ${index + 1}: ${assessment.candidate_organ}`,
        rows: [
          { key: "family_id", value: assessment.family_id ?? "unknown" },
          { key: "disposition", value: assessmentDisposition(assessment) },
          { key: "runnable", value: boolLabel(assessment.runnable) },
          { key: "missing_bindings", value: noneIfEmpty(assessment.missing_bindings) },
          { key: "unresolved_hazards", value: noneIfEmpty(assessment.unresolved_hazards) },
          { key: "explanation", value: assessment.explanation || "none" },
          { key: "evidence_spans", value: spanList(evidence.problem_text, assessment.evidence_spans) },
        ],
      })),
    },
  ];
}

export function constructionEvidencePanelModel(
  evidence: ConstructionEvidence,
): ConstructionEvidencePanelModel {
  return {
    status: evidence.status,
    emptyMessage: constructionEvidenceEmptyMessage(evidence),
    reproducer: traceConstructionReproducer(evidence.turn_id),
    authorityRows: [
      { key: "schema_version", value: evidence.schema_version },
      { key: "status", value: evidence.status },
      { key: "diagnostic_only", value: boolLabel(evidence.diagnostic_only) },
      { key: "serving_allowed", value: boolLabel(evidence.serving_allowed) },
      { key: "missing_reason", value: evidence.missing_reason ?? "none" },
    ],
    countRows: [
      { key: "proposals", value: String(evidence.proposals.length) },
      { key: "mentions", value: String(evidence.mentions.length) },
      { key: "bindings", value: String(evidence.bindings.length) },
      { key: "bound_relations", value: String(evidence.bound_relations.length) },
      { key: "contract_assessments", value: String(evidence.contract_assessments.length) },
    ],
    assessmentRows: evidence.contract_assessments.map((assessment) => ({
      key: `${assessment.candidate_organ}:${assessment.family_id ?? "unknown"}`,
      value: `${assessmentDisposition(assessment)} — ${assessmentBlockerSummary(assessment)}`,
    })),
    detailSections: detailSections(evidence),
    sourceSpanRows: sourceSpanRows(evidence),
    showRaw: evidence.status === "recorded",
  };
}
