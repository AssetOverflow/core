import type { DemoNarrative } from "../../types/demoNarrative";

export const DEMO_PARTNER_BLURB =
  "A frontier model can propose. CORE can govern. Workbench can prove what happened, what was refused, what replayed, and what remains only a proposal.";

export function demoNarrativeValidationWarnings(narrative: DemoNarrative): string[] {
  const warnings: string[] = [];
  const seen = new Set<string>();
  const orders = narrative.steps.map((step) => step.order);

  for (const step of narrative.steps) {
    if (seen.has(step.step_id)) {
      warnings.push(`duplicate step_id: ${step.step_id}`);
    }
    seen.add(step.step_id);
    if (step.what_this_proves.trim().length === 0) {
      warnings.push(`step ${step.step_id} is missing what_this_proves`);
    }
    if (step.what_this_does_not_prove.trim().length === 0) {
      warnings.push(`step ${step.step_id} is missing what_this_does_not_prove`);
    }
    for (const link of step.evidence_links) {
      if (!link.route.startsWith("/")) {
        warnings.push(`step ${step.step_id} has non-route evidence link: ${link.route}`);
      }
    }
  }

  const sorted = [...orders].sort((a, b) => a - b);
  if (orders.some((order, index) => order !== sorted[index])) {
    warnings.push("steps must be sorted by order");
  }
  return warnings;
}

export function demoStepHonestyPair(step: DemoNarrative["steps"][number]): string {
  return `Proves: ${step.what_this_proves} / Does not prove: ${step.what_this_does_not_prove}`;
}
