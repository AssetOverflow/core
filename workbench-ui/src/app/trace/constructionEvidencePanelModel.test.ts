import { describe, expect, it } from "vitest";
import type { ConstructionEvidence } from "../../types/constructionEvidence";
import { constructionEvidencePanelModel } from "./constructionEvidencePanelModel";

const missingEvidence: ConstructionEvidence = {
  schema_version: "construction_evidence_v1",
  turn_id: 7,
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

describe("construction evidence panel model", () => {
  it("models missing evidence honestly", () => {
    const model = constructionEvidencePanelModel(missingEvidence);

    expect(model.status).toBe("missing_evidence");
    expect(model.emptyMessage).toBe("construction evidence was not persisted for this turn");
    expect(model.reproducer).toBe("curl /trace/7/construction");
    expect(model.authorityRows).toEqual([
      { key: "schema_version", value: "construction_evidence_v1" },
      { key: "status", value: "missing_evidence" },
      { key: "diagnostic_only", value: "true" },
      { key: "serving_allowed", value: "false" },
      { key: "missing_reason", value: "construction evidence was not persisted for this turn" },
    ]);
    expect(model.countRows).toEqual([
      { key: "proposals", value: "0" },
      { key: "mentions", value: "0" },
      { key: "bindings", value: "0" },
      { key: "bound_relations", value: "0" },
      { key: "contract_assessments", value: "0" },
    ]);
    expect(model.showRaw).toBe(false);
  });

  it("models recorded contract assessment blockers", () => {
    const model = constructionEvidencePanelModel({
      ...missingEvidence,
      status: "recorded",
      missing_reason: null,
      problem_text: "Lena has 3 marbles.",
      contract_assessments: [
        {
          candidate_organ: "quantity_entity_binding_candidate.v1",
          family_id: "binding.quantity_entity",
          missing_bindings: ["entity"],
          unresolved_hazards: ["ambiguous_quantity"],
          runnable: false,
          explanation: "missing entity",
          evidence_spans: [],
        },
      ],
    });

    expect(model.emptyMessage).toBe(null);
    expect(model.countRows.find((row) => row.key === "contract_assessments")?.value).toBe("1");
    expect(model.assessmentRows).toEqual([
      {
        key: "quantity_entity_binding_candidate.v1:binding.quantity_entity",
        value: "blocked — entity, ambiguous_quantity",
      },
    ]);
    expect(model.showRaw).toBe(true);
  });
});
