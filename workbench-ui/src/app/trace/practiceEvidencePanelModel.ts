import type {
  PracticeEvidence,
  PracticeEvidenceCard,
  PracticeSourceSpanView,
  SealedPracticeTraceView,
  PracticeTraceRefusalView,
} from "../../types/practiceEvidence";
import { tracePracticeReproducer } from "./practiceEvidenceEndpoint";
import { practiceEvidenceEmptyMessage, practiceSourceSpanLabel } from "./practiceEvidenceView";

export interface PracticeEvidenceSummaryRow {
  key: string;
  value: string;
}

export interface PracticeEvidenceDetailItem {
  title: string;
  rows: PracticeEvidenceSummaryRow[];
}

export interface PracticeEvidenceDetailSection {
  title: string;
  emptyMessage: string;
  items: PracticeEvidenceDetailItem[];
}

export interface PracticeEvidencePanelModel {
  status: PracticeEvidence["status"];
  emptyMessage: string | null;
  reproducer: string;
  authorityRows: PracticeEvidenceSummaryRow[];
  countRows: PracticeEvidenceSummaryRow[];
  chainRows: PracticeEvidenceSummaryRow[];
  detailSections: PracticeEvidenceDetailSection[];
  sourceSpanRows: PracticeEvidenceSummaryRow[];
  showRaw: boolean;
}

function boolLabel(value: boolean): string {
  return value ? "true" : "false";
}

function listLabel(values: readonly string[]): string {
  return values.length > 0 ? values.join(", ") : "none";
}

function sourceSpanRows(evidence: PracticeEvidence): PracticeEvidenceSummaryRow[] {
  const rows: PracticeEvidenceSummaryRow[] = [];
  const append = (prefix: string, spans: readonly PracticeSourceSpanView[]) => {
    spans.forEach((span, index) => {
      rows.push({ key: `${prefix}.${index + 1}`, value: practiceSourceSpanLabel(span) });
    });
  };
  if (evidence.sealed_trace !== null) {
    append("sealed_trace", evidence.sealed_trace.evidence_spans);
  }
  return rows;
}

function cardRows(card: PracticeEvidenceCard): PracticeEvidenceSummaryRow[] {
  return [
    { key: "kind", value: card.kind },
    { key: "status", value: card.status },
    { key: "refs", value: listLabel(card.refs) },
    { key: "summary", value: card.summary || "none" },
    {
      key: "authority",
      value: "identity card only; Workbench does not execute search, replay, operators, sealing, or mutation",
    },
  ];
}

function sealedTraceRows(trace: SealedPracticeTraceView): PracticeEvidenceSummaryRow[] {
  return [
    { key: "trace_id", value: trace.trace_id },
    { key: "trace_policy_version", value: trace.trace_policy_version },
    { key: "input_digest", value: trace.input_digest },
    { key: "problem_frame_digest", value: trace.problem_frame_digest },
    { key: "original_contract_assessment_id", value: trace.original_contract_assessment_id },
    { key: "residual_ids", value: listLabel(trace.residual_ids) },
    { key: "search_gate_decision_id", value: trace.search_gate_decision_id },
    { key: "compute_budget_id", value: trace.compute_budget_id },
    { key: "geometric_search_run_id", value: trace.geometric_search_run_id },
    { key: "candidate_attempt_ids", value: listLabel(trace.candidate_attempt_ids) },
    { key: "candidate_attempt_binding_ids", value: listLabel(trace.candidate_attempt_binding_ids) },
    { key: "replay_result_ids", value: listLabel(trace.replay_result_ids) },
    { key: "replay_refusal_ids", value: listLabel(trace.replay_refusal_ids) },
    { key: "upstream_identity_chain", value: listLabel(trace.upstream_identity_chain) },
    { key: "practice_disposition", value: trace.practice_disposition },
    { key: "trace_records", value: listLabel(trace.trace_records) },
    { key: "created_by_policy", value: trace.created_by_policy || "none" },
    { key: "explanation", value: trace.explanation || "none" },
  ];
}

function traceRefusalRows(refusal: PracticeTraceRefusalView): PracticeEvidenceSummaryRow[] {
  return [
    { key: "trace_refusal_id", value: refusal.trace_refusal_id },
    { key: "trace_policy_version", value: refusal.trace_policy_version },
    { key: "input_digest", value: refusal.input_digest ?? "none" },
    { key: "practice_disposition", value: refusal.practice_disposition },
    { key: "reason_codes", value: listLabel(refusal.reason_codes) },
    { key: "explanation", value: refusal.explanation || "none" },
  ];
}

function detailSections(evidence: PracticeEvidence): PracticeEvidenceDetailSection[] {
  return [
    {
      title: "Evidence chain",
      emptyMessage: "No sealed practice chain cards recorded.",
      items: evidence.chain.map((card, index) => ({
        title: `card ${index + 1}: ${card.kind}`,
        rows: cardRows(card),
      })),
    },
    {
      title: "Sealed trace",
      emptyMessage: "No sealed practice trace recorded.",
      items:
        evidence.sealed_trace === null
          ? []
          : [
              {
                title: evidence.sealed_trace.trace_id,
                rows: sealedTraceRows(evidence.sealed_trace),
              },
            ],
    },
    {
      title: "Trace refusal",
      emptyMessage: "No practice trace refusal recorded.",
      items:
        evidence.trace_refusal === null
          ? []
          : [
              {
                title: evidence.trace_refusal.trace_refusal_id,
                rows: traceRefusalRows(evidence.trace_refusal),
              },
            ],
    },
  ];
}

export function practiceEvidencePanelModel(evidence: PracticeEvidence): PracticeEvidencePanelModel {
  return {
    status: evidence.status,
    emptyMessage: practiceEvidenceEmptyMessage(evidence),
    reproducer: tracePracticeReproducer(evidence.turn_id),
    authorityRows: [
      { key: "schema_version", value: evidence.schema_version },
      { key: "status", value: evidence.status },
      { key: "record_kind", value: evidence.record_kind ?? "none" },
      { key: "practice_disposition", value: evidence.practice_disposition ?? "none" },
      { key: "diagnostic_only", value: boolLabel(evidence.diagnostic_only) },
      { key: "serving_allowed", value: boolLabel(evidence.serving_allowed) },
      { key: "mutation_allowed", value: boolLabel(evidence.mutation_allowed) },
      { key: "replay_execution_allowed", value: boolLabel(evidence.replay_execution_allowed) },
      { key: "replay_executed_by_workbench", value: boolLabel(evidence.replay_executed_by_workbench) },
      { key: "missing_reason", value: evidence.missing_reason ?? "none" },
    ],
    countRows: [
      { key: "chain_cards", value: String(evidence.chain.length) },
      { key: "sealed_trace", value: evidence.sealed_trace === null ? "0" : "1" },
      { key: "trace_refusal", value: evidence.trace_refusal === null ? "0" : "1" },
      {
        key: "source_spans",
        value: String(evidence.sealed_trace === null ? 0 : evidence.sealed_trace.evidence_spans.length),
      },
    ],
    chainRows: evidence.chain.map((card) => ({
      key: card.kind,
      value: `${card.status} — ${listLabel(card.refs)}`,
    })),
    detailSections: detailSections(evidence),
    sourceSpanRows: sourceSpanRows(evidence),
    showRaw: evidence.status === "recorded",
  };
}
