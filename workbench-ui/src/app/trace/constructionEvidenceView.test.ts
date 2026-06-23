import { describe, expect, it } from "vitest";
import type { ConstructionEvidence, ContractAssessmentView } from "../../types/constructionEvidence";
import {
  CONSTRUCTION_AUTHORITY_DISCLOSURES,
  assessmentBlockerSummary,
  assessmentDisposition,
  constructionEvidenceEmptyMessage,
  sourceSpanIsExact,
  sourceSpanLabel,
} from "./constructionEvidenceView";

const missingEvidence: ConstructionEvidence = {
  schema_version: "construction_evidence_v1",
  turn_id: 1,
  status: "missing_evidence",
  missing_reason: "construction evidence was not persisted for this turn",
  problem_text: null,
  proposals: [],
  mentions: [],
  bindings: [],
  bound_relations: [],
  contract_assessments: [],
  diagnostic_only: true,
  serving_allowed: false,
};

const blockedAssessment: ContractAssessmentView = {
  candidate_organ: "quantity_entity_binding_candidate.v1",
  family_id: "binding.quantity_entity",
  missing_bindings: ["entity"],
  unresolved_hazards: ["ambiguous_quantity"],
  runnable: false,
  explanation: "missing entity binding",
  evidence_spans: [],
};

describe("construction evidence view helpers", () => {
  it("keeps load-bearing authority disclosures explicit", () => {
    expect(CONSTRUCTION_AUTHORITY_DISCLOSURES).toEqual([
      "Proposal != Runnable",
      "Contract Determines",
      "Diagnostic Only",
      "Serving Disallowed",
      "Exact Span Required",
    ]);
  });

  it("renders missing evidence as honest absence", () => {
    expect(constructionEvidenceEmptyMessage(missingEvidence)).toBe(
      "construction evidence was not persisted for this turn",
    );
  });

  it("labels source spans without normalization", () => {
    expect(sourceSpanLabel({ start: 9, end: 10, text: "3" })).toBe("9:10 3");
  });

  it("checks exact source spans against problem text", () => {
    const text = "Lena has 3 red marbles.";

    expect(sourceSpanIsExact(text, { start: 9, end: 10, text: "3" })).toBe(true);
    expect(sourceSpanIsExact(text, { start: 9, end: 10, text: "three" })).toBe(false);
    expect(sourceSpanIsExact(null, { start: 9, end: 10, text: "3" })).toBe(false);
  });

  it("classifies assessments as blocked when bindings or hazards remain", () => {
    expect(assessmentDisposition(blockedAssessment)).toBe("blocked");
    expect(assessmentBlockerSummary(blockedAssessment)).toBe("entity, ambiguous_quantity");
  });

  it("classifies assessments as runnable only with no blockers", () => {
    const runnable: ContractAssessmentView = {
      ...blockedAssessment,
      missing_bindings: [],
      unresolved_hazards: [],
      runnable: true,
    };

    expect(assessmentDisposition(runnable)).toBe("runnable");
    expect(assessmentBlockerSummary(runnable)).toBe("No blockers recorded.");
  });
});
