import React from 'react';
import { Panel, EmptyState, StableJsonViewer } from '../../design';

/**
 * CapabilityParadigmPanel
 *
 * Surfaces the current state of the capability paradigm, recent derivation lifts,
 * Gate A* processes, and strike/batch progress.
 * Placeholder for now — will be expanded with real data from the derivation
 * and ratification surfaces.
 */

export function CapabilityParadigmPanel() {
  return (
    <Panel
      title="Capability Paradigm"
      subtitle="Lifts, Gates & Derivation Progress"
    >
      <EmptyState
        title="Capability surfaces coming online"
        description="Recent work on question-bound product aggregates, Gate A1/A2a/A2b injections, and strike batches will appear here with evidence of lifts while preserving wrong=0."
        actionLabel="View recent derivation PRs"
        onAction={() => {
          window.open('https://github.com/AssetOverflow/core/pulls?q=is%3Apr+capability+OR+gate+OR+derivation', '_blank');
        }}
      />

      <div className="mt-4 text-xs text-[var(--color-text-tertiary)]">
        This panel will eventually show ratified capabilities, lift history, gate verdicts,
        and links to traces/contemplation records for the capability paradigm.
      </div>
    </Panel>
  );
}
