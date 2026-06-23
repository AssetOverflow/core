import type {
  ConstructionEvidence,
  ContractAssessmentView,
  SourceSpanView,
} from "../../types/constructionEvidence";

export const CONSTRUCTION_AUTHORITY_DISCLOSURES = [
  "Proposal != Runnable",
  "Contract Determines",
  "Diagnostic Only",
  "Serving Disallowed",
  "Exact Span Required",
] as const;

export function constructionEvidenceEmptyMessage(evidence: ConstructionEvidence): string | null {
  if (evidence.status === "missing_evidence") {
    return evidence.missing_reason ?? "No construction evidence recorded for this turn.";
  }
  const hasEvidence =
    evidence.proposals.length > 0 ||
    evidence.mentions.length > 0 ||
    evidence.bindings.length > 0 ||
    evidence.bound_relations.length > 0 ||
    evidence.contract_assessments.length > 0;
  return hasEvidence ? null : "No construction evidence recorded for this turn.";
}

export function sourceSpanLabel(span: SourceSpanView): string {
  return `${span.start}:${span.end} ${span.text}`;
}

export function sourceSpanIsExact(problemText: string | null, span: SourceSpanView): boolean {
  if (problemText === null) {
    return false;
  }
  return (
    span.start >= 0 &&
    span.end >= span.start &&
    span.end <= problemText.length &&
    span.text.length > 0 &&
    problemText.slice(span.start, span.end) === span.text
  );
}

export function assessmentDisposition(assessment: ContractAssessmentView): "runnable" | "blocked" {
  return assessment.runnable &&
    assessment.missing_bindings.length === 0 &&
    assessment.unresolved_hazards.length === 0
    ? "runnable"
    : "blocked";
}

export function assessmentBlockerSummary(assessment: ContractAssessmentView): string {
  const blockers = [...assessment.missing_bindings, ...assessment.unresolved_hazards];
  return blockers.length > 0 ? blockers.join(", ") : "No blockers recorded.";
}
