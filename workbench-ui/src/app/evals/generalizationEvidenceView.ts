import type { GeneralizationAuditReportView } from "../../types/generalizationEvidence";

export const GENERALIZATION_AUDIT_BANNER =
  "Audit-only. No raw sealed items are exposed here. Benchmark failures are diagnosis signals, not direct mutation targets.";

export function reportKindLabel(report: GeneralizationAuditReportView): string {
  switch (report.report_kind) {
    case "committed_pin":
      return "Committed report pin";
    case "ephemeral_local":
      return "Ephemeral local output";
    case "rebaseline_candidate":
      return "Governed rebaseline candidate";
    case "unknown":
    default:
      return "Unknown report authority";
  }
}

export function generalizationOutcomeSummary(report: GeneralizationAuditReportView): string {
  return `${report.correct} correct / ${report.wrong} wrong / ${report.refused} refused / ${report.unsupported} unsupported`;
}

export function generalizationGovernanceWarnings(report: GeneralizationAuditReportView): string[] {
  const warnings: string[] = [];
  if (!report.audit_only) {
    warnings.push("Report is not marked audit-only.");
  }
  if (report.raw_items_exposed) {
    warnings.push("Report claims raw items are exposed; do not render item payloads.");
  }
  if (report.report_kind !== "committed_pin") {
    warnings.push("Report is not a committed pin; do not present as canonical baseline.");
  }
  return warnings;
}
