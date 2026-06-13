import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { LeewayEvidenceCard } from "./LeewayEvidenceCard";

describe("LeewayEvidenceCard", () => {
  it("renders a served-with-leeway tuple from typed data", () => {
    render(
      <LeewayEvidenceCard
        evidence={{
          class_name: "additive",
          license: "PROPOSE",
          theta: 0.85,
          claim_disclosure: "approximate",
          source_digest: "sha256:practice",
          calibration_evidence_ref: "calibration:additive",
        }}
      />,
    );
    expect(screen.getByText("additive")).toBeInTheDocument();
    expect(screen.getByText(/PROPOSE · θ 85\.0%/)).toBeInTheDocument();
    expect(screen.getByText("approximate")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "calibration:additive" })).toHaveAttribute(
      "href",
      "/calibration?inspect=calibration%3Aadditive",
    );
  });

  it("renders explicit absence for verified turns with no leeway tuple", () => {
    render(<LeewayEvidenceCard evidence={null} />);
    expect(screen.getByText("No leeway evidence recorded.")).toBeInTheDocument();
    expect(screen.queryByText(/PROPOSE|SERVE/)).not.toBeInTheDocument();
  });
});
