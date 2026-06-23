import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { ConstructionEvidence } from "../../types/constructionEvidence";
import { ConstructionEvidencePanel } from "./ConstructionEvidencePanel";

const recordedEvidence: ConstructionEvidence = {
  schema_version: "construction_evidence_v1",
  turn_id: 7,
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
  diagnostic_only: true,
  serving_allowed: false,
};

describe("ConstructionEvidencePanel", () => {
  it("renders read-only construction detail sections without granting proposal authority", () => {
    render(
      <ConstructionEvidencePanel
        evidence={recordedEvidence}
        isLoading={false}
        error={null}
        turnId={7}
        errorMessage={(error) => String(error)}
      />,
    );

    const panel = screen.getByTestId("construction-evidence-panel");
    expect(within(panel).getByText("Proposals")).toBeInTheDocument();
    expect(within(panel).getByText("Mentions")).toBeInTheDocument();
    expect(within(panel).getByText("Bindings")).toBeInTheDocument();
    expect(within(panel).getByText("Bound relations")).toBeInTheDocument();
    expect(within(panel).getByText("Contract assessments")).toBeInTheDocument();
    expect(within(panel).getByText("Source span checks")).toBeInTheDocument();

    expect(
      within(panel).getByText("diagnostic proposal only; contract assessment determines runnable status"),
    ).toBeInTheDocument();
    expect(within(panel).getAllByText("false").length).toBeGreaterThan(0);
    expect(within(panel).getAllByText(/quantity_entity_binding_candidate\.v1/).length).toBeGreaterThan(0);
    expect(within(panel).getAllByText("0:4 Lena — exact").length).toBeGreaterThan(0);
    expect(within(panel).getAllByText("0:4 Lena! — inexact").length).toBeGreaterThan(0);
    expect(within(panel).getByText("curl /trace/7/construction")).toBeInTheDocument();
  });
});
