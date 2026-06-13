import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { FieldInvariantCard } from "./FieldInvariantCard";
import type { FieldEvidence } from "../../../types/api";

function recorded(overrides: Partial<FieldEvidence> = {}): FieldEvidence {
  return {
    schema_version: "field_evidence_v1",
    status: "recorded",
    missing_reason: null,
    trace_hash: "trace-abc",
    versor_condition: 6.5e-13,
    versor_condition_ceiling: 1e-6,
    field_valid: true,
    field_digest: "sha256:f92fa3b99b6086fdaaaa",
    parent_field_digest: null,
    transition_inner_product: null,
    ...overrides,
  };
}

describe("FieldInvariantCard", () => {
  it("shows the exact versor_condition and a valid assertion", () => {
    render(<FieldInvariantCard record={recorded()} />);
    expect(screen.getByText("field valid")).toBeInTheDocument();
    expect(screen.getByTestId("field-versor-condition").textContent).toContain(
      "6.500e-13",
    );
  });

  it("renders the cga_inner transition value when a prior field exists", () => {
    render(
      <FieldInvariantCard
        record={recorded({
          parent_field_digest: "sha256:beef",
          transition_inner_product: 1.0,
        })}
      />,
    );
    expect(screen.getByTestId("field-transition")).toBeInTheDocument();
  });

  it("never claims valid when the field breaches the ceiling", () => {
    render(
      <FieldInvariantCard
        record={recorded({ versor_condition: 1e-3, field_valid: false })}
      />,
    );
    expect(screen.queryByText("field valid")).not.toBeInTheDocument();
    expect(screen.getByText("field breach")).toBeInTheDocument();
  });

  it("is honest about absent evidence", () => {
    render(
      <FieldInvariantCard
        record={recorded({
          status: "missing_evidence",
          missing_reason: "field_evidence_not_persisted",
          versor_condition: null,
          field_valid: null,
          field_digest: null,
        })}
      />,
    );
    expect(screen.getByTestId("field-missing")).toBeInTheDocument();
    expect(screen.getByText(/No field evidence/)).toBeInTheDocument();
  });

  it("does not render any raw multivector array", () => {
    const { container } = render(<FieldInvariantCard record={recorded()} />);
    expect(container.textContent).not.toMatch(/\[0,\s*0,\s*0/);
    expect(container.textContent).not.toContain("b64");
  });
});
