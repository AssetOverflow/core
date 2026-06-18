import { InfoBadge } from "../../design/components/badges/Badge";
import { MetadataTable } from "../../design/components/MetadataTable/MetadataTable";
import { Panel } from "../../design/components/Panel/Panel";
import { EmptyState } from "../../design/components/states/EmptyState";
import { EXPERIENCE_FLYWHEEL_CLI, EXPERIENCE_RECORD_FIELDS } from "./capabilityMasteryData";

export const EXPERIENCE_FLYWHEEL_ABSENCE_STATEMENT =
  "No Experience Flywheel records in this Workbench session. PR-1 (PR 816) is measurement-only — records are emitted by CLI to an explicit --out path; there is no GET /flywheel workbench endpoint yet.";

/**
 * Experience Flywheel — measurement-only sealed-practice memory (PR-1 / PR 816).
 * Honest empty state until a read-only backend surface lands.
 */
export function ExperienceFlywheelPanel() {
  return (
    <Panel
      title="Experience Flywheel"
      toolbar={
        <InfoBadge
          label="Measurement-only"
          colorToken="--color-text-secondary"
          meaning="PR-1 adapter reads report.json and sealed practice artifacts — never mutates serving, corpus, or packs."
          adr="ADR-0160 / ADR-0162"
          evidence="docs/analysis/gsm8k-experience-flywheel-pr1-lookback-2026-06-17.md"
        />
      }
    >
      <div className="flex flex-col gap-4" data-testid="experience-flywheel-panel">
        <EmptyState
          statement={EXPERIENCE_FLYWHEEL_ABSENCE_STATEMENT}
          nextAction={{ kind: "cli", command: EXPERIENCE_FLYWHEEL_CLI }}
        />

        <div>
          <h3 className="m-0 mb-2 text-xs font-semibold uppercase tracking-wide text-[var(--color-text-secondary)]">
            Compact record shape (when CLI emits --out)
          </h3>
          <MetadataTable
            rows={EXPERIENCE_RECORD_FIELDS.map((field) => ({
              key: field.key,
              value: field.value,
            }))}
          />
        </div>

        <MetadataTable
          rows={[
            {
              key: "Trust boundary",
              value: "No serving mutation • report.json read-only • no auto-promotion",
            },
            {
              key: "Backend status",
              value: "Pending — no workbench GET endpoint; do not invent live records",
            },
            {
              key: "Lookback",
              value: "docs/analysis/gsm8k-experience-flywheel-pr1-lookback-2026-06-17.md",
              mono: true,
            },
          ]}
        />
      </div>
    </Panel>
  );
}