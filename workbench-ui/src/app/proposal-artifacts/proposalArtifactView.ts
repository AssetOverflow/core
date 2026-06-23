import type { ProposalArtifact } from "../../types/proposalArtifact";

export function ratificationControlsAllowed(artifact: ProposalArtifact): boolean {
  return artifact.capability_level === "ratification_enabled" && artifact.handler_route !== null;
}

export function proposalCapabilityLabel(artifact: ProposalArtifact): string {
  switch (artifact.capability_level) {
    case "ratification_enabled":
      return artifact.handler_route === null
        ? "Ratification disabled: no handler route"
        : "Ratification enabled by admitted handler";
    case "proposal_only":
      return "Proposal-only: review/export/copy allowed; apply disabled";
    case "inspect_only":
    default:
      return "Inspect-only: no mutation affordance allowed";
  }
}

export function proposalArtifactWarnings(artifact: ProposalArtifact): string[] {
  const warnings: string[] = [];
  if (artifact.capability_level !== "ratification_enabled" && artifact.handler_route !== null) {
    warnings.push("Handler route must not be present without ratification authority.");
  }
  if (artifact.capability_level === "ratification_enabled" && artifact.handler_route === null) {
    warnings.push("Ratification authority declared without handler route.");
  }
  if (artifact.validation?.status === "blocked") {
    warnings.push(...artifact.validation.blockers);
  }
  if (artifact.safety_report?.status === "failed") {
    warnings.push(...artifact.safety_report.disclosures);
  }
  return warnings;
}
