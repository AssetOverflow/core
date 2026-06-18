import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { CapabilityParadigmPanel } from "./CapabilityParadigmPanel";
import {
  EXPERIENCE_FLYWHEEL_ABSENCE_STATEMENT,
  ExperienceFlywheelPanel,
} from "./ExperienceFlywheelPanel";
import { CapabilityMasterySection } from "./CapabilityMasterySection";
import { DOCUMENTED_TRAIN_SAMPLE_BASELINE } from "./capabilityMasteryData";

describe("Capability mastery surfaces", () => {
  it("ExperienceFlywheelPanel renders honest empty state and CLI guidance", () => {
    render(<ExperienceFlywheelPanel />);
    expect(screen.getByTestId("experience-flywheel-panel")).toBeInTheDocument();
    expect(screen.getByText(EXPERIENCE_FLYWHEEL_ABSENCE_STATEMENT)).toBeInTheDocument();
    expect(
      screen.getByText("scripts/gsm8k_experience_flywheel.py --limit 50 --out /tmp/gsm8k-experience.json"),
    ).toBeInTheDocument();
    expect(screen.getByText("Measurement-only")).toBeInTheDocument();
  });

  it("CapabilityParadigmPanel shows documented baseline and gate ladder through A2s", () => {
    render(<CapabilityParadigmPanel />);
    const { correct, refused, wrong } = DOCUMENTED_TRAIN_SAMPLE_BASELINE;
    expect(screen.getAllByText(`${correct} / ${refused} / ${wrong}`).length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("Documented")).toBeInTheDocument();
    expect(screen.getByTestId("gate-row-A2e")).toBeInTheDocument();
    expect(screen.getByTestId("gate-row-A2f")).toBeInTheDocument();
    expect(screen.getByTestId("gate-row-A2q")).toBeInTheDocument();
    expect(screen.getByTestId("gate-row-A2r")).toBeInTheDocument();
    expect(screen.getByTestId("gate-row-A2s")).toBeInTheDocument();
    expect(screen.getByText("0004")).toBeInTheDocument();
    expect(screen.getByText("0007")).toBeInTheDocument();
    expect(screen.getByTestId("cluster-contract-sprint11")).toBeInTheDocument();
    expect(screen.getByTestId("cluster-contract-sprint12")).toBeInTheDocument();
    expect(screen.getByTestId("blocked-DCS")).toBeInTheDocument();
    expect(screen.getByTestId("blocked-multiplicative_aggregate")).toBeInTheDocument();
  });

  it("CapabilityMasterySection composes both panels", () => {
    render(<CapabilityMasterySection />);
    expect(screen.getByTestId("capability-mastery-section")).toBeInTheDocument();
    expect(screen.getByText("Experience Flywheel")).toBeInTheDocument();
    expect(screen.getByText("Capability Paradigm")).toBeInTheDocument();
  });
});
