import { describe, expect, it } from "vitest";
import type { ProposalArtifact } from "../../types/proposalArtifact";
import {
  proposalArtifactWarnings,
  proposalCapabilityLabel,
  ratificationControlsAllowed,
} from "./proposalArtifactView";

const inspectOnly: ProposalArtifact = {
  proposal_id: "p1",
  subject: { kind: "construction", subject_id: "turn:1", display_name: "Construction" },
  state: "unknown",
  capability_level: "inspect_only",
  source_kind: "construction_evidence",
  proposed_change: null,
  reasoning_trace: null,
  evidence_pointers: [],
  validation: null,
  replay_evidence: null,
  safety_report: null,
  affected_artifacts: [],
  handler_route: null,
  suggested_cli: null,
  audit_refs: [],
  ui_disclosure: "inspect only",
};

describe("proposal artifact view helpers", () => {
  it("disallows ratification controls for inspect-only artifacts", () => {
    expect(ratificationControlsAllowed(inspectOnly)).toBe(false);
    expect(proposalCapabilityLabel(inspectOnly)).toBe(
      "Inspect-only: no mutation affordance allowed",
    );
  });

  it("disallows ratification controls for proposal-only artifacts", () => {
    const artifact = { ...inspectOnly, capability_level: "proposal_only" as const };

    expect(ratificationControlsAllowed(artifact)).toBe(false);
    expect(proposalCapabilityLabel(artifact)).toBe(
      "Proposal-only: review/export/copy allowed; apply disabled",
    );
  });

  it("allows ratification controls only with handler route", () => {
    const artifact = {
      ...inspectOnly,
      capability_level: "ratification_enabled" as const,
      handler_route: "/math-proposals/p1/ratify",
    };

    expect(ratificationControlsAllowed(artifact)).toBe(true);
    expect(proposalCapabilityLabel(artifact)).toBe(
      "Ratification enabled by admitted handler",
    );
  });

  it("warns on impossible handler/capability combinations", () => {
    expect(
      proposalArtifactWarnings({
        ...inspectOnly,
        handler_route: "/invalid",
      }),
    ).toEqual(["Handler route must not be present without ratification authority."]);

    expect(
      proposalArtifactWarnings({
        ...inspectOnly,
        capability_level: "ratification_enabled",
      }),
    ).toEqual(["Ratification authority declared without handler route."]);
  });

  it("surfaces validation and safety blockers", () => {
    expect(
      proposalArtifactWarnings({
        ...inspectOnly,
        validation: { status: "blocked", blockers: ["missing evidence"], warnings: [] },
        safety_report: { status: "failed", disclosures: ["handler not admitted"] },
      }),
    ).toEqual(["missing evidence", "handler not admitted"]);
  });
});
