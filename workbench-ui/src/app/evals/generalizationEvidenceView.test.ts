import { describe, expect, it } from "vitest";
import type { GeneralizationAuditReportView } from "../../types/generalizationEvidence";
import {
  GENERALIZATION_AUDIT_BANNER,
  generalizationGovernanceWarnings,
  generalizationOutcomeSummary,
  reportKindLabel,
} from "./generalizationEvidenceView";

const baseReport: GeneralizationAuditReportView = {
  policy_version: "generalization_benchmark_policy_v1",
  dataset: "gsm1k",
  split: "local_audit",
  n_items: 10,
  correct: 4,
  wrong: 0,
  refused: 6,
  unsupported: 0,
  candidate_attempts: 3,
  binding_failures: 2,
  replay_refusals: 1,
  sealed_trace_dispositions: [["sealed", 7]],
  dominant_residual_kinds: [["missing_binding", 5]],
  reason_codes: ["ok"],
  source_path: "evals/generalization/reports/gsm1k.json",
  source_digest: "sha256:abc",
  report_kind: "committed_pin",
  audit_only: true,
  raw_items_exposed: false,
};

describe("generalization evidence view helpers", () => {
  it("states the benchmark governance boundary", () => {
    expect(GENERALIZATION_AUDIT_BANNER).toContain("Audit-only");
    expect(GENERALIZATION_AUDIT_BANNER).toContain("No raw sealed items");
    expect(GENERALIZATION_AUDIT_BANNER).toContain("not direct mutation targets");
  });

  it("labels report authority", () => {
    expect(reportKindLabel(baseReport)).toBe("Committed report pin");
    expect(reportKindLabel({ ...baseReport, report_kind: "ephemeral_local" })).toBe(
      "Ephemeral local output",
    );
    expect(reportKindLabel({ ...baseReport, report_kind: "rebaseline_candidate" })).toBe(
      "Governed rebaseline candidate",
    );
    expect(reportKindLabel({ ...baseReport, report_kind: "unknown" })).toBe(
      "Unknown report authority",
    );
  });

  it("summarizes outcomes without hiding wrong count", () => {
    expect(generalizationOutcomeSummary(baseReport)).toBe(
      "4 correct / 0 wrong / 6 refused / 0 unsupported",
    );
    expect(generalizationOutcomeSummary({ ...baseReport, wrong: 2 })).toContain("2 wrong");
  });

  it("warns when report should not be treated as canonical", () => {
    expect(generalizationGovernanceWarnings(baseReport)).toEqual([]);
    expect(
      generalizationGovernanceWarnings({
        ...baseReport,
        report_kind: "ephemeral_local",
        audit_only: false,
        raw_items_exposed: true,
      }),
    ).toEqual([
      "Report is not marked audit-only.",
      "Report claims raw items are exposed; do not render item payloads.",
      "Report is not a committed pin; do not present as canonical baseline.",
    ]);
  });
});
