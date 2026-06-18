import { CapabilityParadigmPanel } from "./CapabilityParadigmPanel";
import { ExperienceFlywheelPanel } from "./ExperienceFlywheelPanel";

/** Capability mastery surfaces for the Evals route (reconciled from PR 821). */
export function CapabilityMasterySection() {
  return (
    <section
      className="flex flex-col gap-4"
      data-testid="capability-mastery-section"
      aria-label="Capability mastery surfaces"
    >
      <ExperienceFlywheelPanel />
      <CapabilityParadigmPanel />
    </section>
  );
}