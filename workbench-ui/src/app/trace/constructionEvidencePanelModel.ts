import type { ConstructionEvidence } from "../../types/constructionEvidence";
import {
  assessmentBlockerSummary,
  assessmentDisposition,
  constructionEvidenceEmptyMessage,
} from "./constructionEvidenceView";
import { traceConstructionReproducer } from "./constructionEvidenceEndpoint";

export interface ConstructionEvidenceSummaryRow {
  key: string;
  value: string;
}

export interface ConstructionEvidencePanelModel {
  status: ConstructionEvidence["status"];
  emptyMessage: string | null;
  reproducer: string;
  authorityRows: ConstructionEvidenceSummaryRow[];
  countRows: ConstructionEvidenceSummaryRow[];
  assessmentRows: ConstructionEvidenceSummaryRow[];
  showRaw: boolean;
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
      { key: "diagnostic_only", value: evidence.diagnostic_only ? "true" : "false" },
      { key: "serving_allowed", value: evidence.serving_allowed ? "true" : "false" },
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
    showRaw: evidence.status === "recorded",
  };
}
