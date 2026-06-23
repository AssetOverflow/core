import type { PracticeEvidence, PracticeSourceSpanView } from "../../types/practiceEvidence";

export const PRACTICE_AUTHORITY_DISCLOSURES = [
  "Diagnostic Only",
  "Serving Disallowed",
  "Mutation Disallowed",
  "Replay Execution Disallowed",
  "Workbench Did Not Execute Replay",
] as const;

export function practiceEvidenceEmptyMessage(evidence: PracticeEvidence): string | null {
  if (evidence.status === "missing_evidence") {
    return evidence.missing_reason ?? "No sealed practice evidence recorded for this turn.";
  }
  const chain = evidence.chain ?? [];
  return chain.length > 0 || evidence.sealed_trace != null || evidence.trace_refusal != null
    ? null
    : "No sealed practice evidence recorded for this turn.";
}

export function practiceSourceSpanLabel(span: PracticeSourceSpanView): string {
  const sentence =
    span.sentence_index === null || span.sentence_index === undefined
      ? "sentence unknown"
      : `sentence ${span.sentence_index}`;
  return `${span.start}:${span.end} ${span.text} (${sentence})`;
}
