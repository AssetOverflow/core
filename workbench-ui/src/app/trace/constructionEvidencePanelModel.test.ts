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

function recordedEvidence(): ConstructionEvidence {
  return {
    ...missingEvidence,
    status: "recorded",
    missing_reason: null,
    problem_text: "Lena has 3 marbles.",
    proposals: [
      {
        family_id: "binding.quantity_entity",
        relation_type: "quantity_entity",
        candidate_organ: "quantity_entity_binding_candidate.v1",
        status: "proposed",
        evidence_spans: [{ start: 9, end: 10, text: "3" }],
        role_obligations: [
          {
            role: "quantity",
            required: true,
            description: "source quantity mention",
          },
          {
            role: "entity",
            required: true,
            description: "source entity mention",
          },
        ],
        diagnostic_only: true,
        serving_allowed: false,
      },
    ],
    mentions: [
      {
        mention_id: "m_lena",
        kind: "entity",
        surface: "Lena",
        span: { start: 0, end: 4, text: "Lena" },
        fact_id: null,
      },
      {
        mention_id: "m_bad",
        kind: "entity",
        surface: "Lena",
        span: { start: 0, end: 4, text: "Lena!" },
        fact_id: null,
      },
    ],
    bindings: [
      {
        binding_type: "quantity_to_entity",
        source_mention_id: "m_quantity",
        target_mention_id: "m_lena",
        evidence_spans: [{ start: 0, end: 10, text: "Lena has 3" }],
      },
    ],
    bound_relations: [
      {
        relation_type: "quantity_entity",
        roles: [
          {
            role: "entity",
            target_id: "m_lena",
            evidence_spans: [{ start: 0, end: 4, text: "Lena" }],
          },
          {
            role: "quantity",
            target_id: "m_quantity",
            evidence_spans: [{ start: 9, end: 10, text: "3" }],
          },
        ],
        evidence_spans: [{ start: 0, end: 10, text: "Lena has 3" }],
      },
    ],
    contract_assessments: [
      {
        candidate_organ: "quantity_entity_binding_candidate.v1",
        family_id: "binding.quantity_entity",
        missing_bindings: ["entity"],
        unresolved_hazards: ["ambiguous_quantity"],
        runnable: false,
        explanation: "missing entity",
        evidence_spans: [{ start: 0, end: 4, text: "Lena!" }],
      },
    ],
  };
}

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
    expect(model.sourceSpanRows).toEqual([]);
    expect(model.detailSections.find((section) => section.title === "Proposals")?.items).toEqual([]);
    expect(model.showRaw).toBe(false);
  });

  it("models recorded contract assessment blockers", () => {
    const model = constructionEvidencePanelModel(recordedEvidence());

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

  it("models proposals, mentions, bindings, bound relations, and exact span checks", () => {
    const model = constructionEvidencePanelModel(recordedEvidence());

    const proposals = model.detailSections.find((section) => section.title === "Proposals");
    expect(proposals?.items[0]).toMatchObject({
      title: "proposal 1: quantity_entity_binding_candidate.v1",
      rows: expect.arrayContaining([
        { key: "status", value: "proposed" },
        { key: "diagnostic_only", value: "true" },
        { key: "serving_allowed", value: "false" },
        {
          key: "authority",
          value: "diagnostic proposal only; contract assessment determines runnable status",
        },
      ]),
    });

    const mentions = model.detailSections.find((section) => section.title === "Mentions");
    expect(mentions?.items.map((item) => item.title)).toEqual([
      "mention m_lena: Lena",
      "mention m_bad: Lena",
    ]);

    const bindings = model.detailSections.find((section) => section.title === "Bindings");
    expect(bindings?.items[0].rows).toContainEqual({
      key: "target_mention_id",
      value: "m_lena",
    });

    const relations = model.detailSections.find((section) => section.title === "Bound relations");
    expect(relations?.items[0].rows).toContainEqual({
      key: "roles",
      value: "entity=m_lena, quantity=m_quantity",
    });

    expect(model.sourceSpanRows).toEqual(
      expect.arrayContaining([
        { key: "proposal 1.1", value: "9:10 3 — exact" },
        { key: "mention m_lena", value: "0:4 Lena — exact" },
        { key: "mention m_bad", value: "0:4 Lena! — inexact" },
        { key: "contract_assessment 1.1", value: "0:4 Lena! — inexact" },
      ]),
    );
  });
});
