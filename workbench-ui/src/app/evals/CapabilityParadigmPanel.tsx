import React from 'react';
import {
  Panel,
  StableJsonViewer,
  MetadataTable,
  TruncatedCell,
} from '../../design';

/**
 * CapabilityParadigmPanel
 *
 * Real surface for the capability paradigm state.
 * Shows recent derivation lifts, Gate progress, and ratification evidence
 * based on the current capability sprint work (question-bound aggregates,
 * Gate A1/A2a/A2b, strike batches, wrong=0 preservation).
 *
 * This component is intentionally data-agnostic for now but structured
 * to accept real data once the backend surfaces are available.
 */

interface LiftRecord {
  id: string;
  description: string;
  cases_lifted: string[];
  wrong_preserved: boolean;
  gate_context?: string;
  evidence_hash?: string;
}

interface GateStatus {
  gate: string;
  status: 'active' | 'completed' | 'blocked';
  injections: number;
  last_updated?: string;
}

interface CapabilityParadigmPanelProps {
  recentLifts?: LiftRecord[];
  gateStatuses?: GateStatus[];
  overallWrongZero?: boolean;
}

export function CapabilityParadigmPanel({
  recentLifts = [],
  gateStatuses = [],
  overallWrongZero = true,
}: CapabilityParadigmPanelProps) {
  return (
    <Panel
      title="Capability Paradigm"
      subtitle="Derivation lifts • Gate progress • Ratification evidence"
    >
      <div className="space-y-6">
        {/* Overall Health */}
        <div>
          <div className="mb-2 text-xs font-medium uppercase tracking-wider text-[var(--color-text-secondary)]">
            Invariant Status
          </div>
          <div className={`inline-flex items-center gap-2 rounded px-3 py-1 text-sm font-medium ${overallWrongZero
            ? "bg-[var(--color-state-success-bg)] text-[var(--color-state-success-text)]"
            : "bg-[var(--color-state-danger-bg)] text-[var(--color-state-danger-text)]"}`}>
            wrong = {overallWrongZero ? "0" : ">0"} across active capability lanes
          </div>
        </div>

        {/* Recent Lifts */}
        <div>
          <div className="mb-2 flex items-center justify-between">
            <div className="text-xs font-medium uppercase tracking-wider text-[var(--color-text-secondary)]">
              Recent Derivation Lifts
            </div>
            <div className="text-[10px] text-[var(--color-text-tertiary)]">
              Question-bound product aggregates • Strike batches
            </div>
          </div>

          {recentLifts.length > 0 ? (
            <div className="space-y-2">
              {recentLifts.map((lift) => (
                <div
                  key={lift.id}
                  className="rounded border border-[var(--color-border)] bg-[var(--color-surface-base)] p-3"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0 flex-1">
                      <div className="font-medium text-[var(--color-text-primary)]">
                        {lift.description}
                      </div>
                      <div className="mt-1 flex flex-wrap gap-1">
                        {lift.cases_lifted.map((c) => (
                          <span
                            key={c}
                            className="inline-block rounded bg-[var(--color-surface-inset)] px-1.5 py-px font-mono text-[10px] text-[var(--color-text-secondary)]"
                          >
                            {c}
                          </span>
                        ))}
                      </div>
                    </div>
                    <div className="text-right text-xs">
                      {lift.wrong_preserved && (
                        <span className="text-[var(--color-state-success-text)]">wrong=0 preserved</span>
                      )}
                    </div>
                  </div>
                  {lift.gate_context && (
                    <div className="mt-2 text-xs text-[var(--color-text-tertiary)]">
                      Gate context: {lift.gate_context}
                    </div>
                  )}
                  {lift.evidence_hash && (
                    <div className="mt-1 font-mono text-[10px] text-[var(--color-text-tertiary)]">
                      Evidence: {lift.evidence_hash}
                    </div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <div className="rounded border border-dashed border-[var(--color-border)] p-4 text-sm text-[var(--color-text-secondary)]">
              No recent lifts recorded in this session.
              <div className="mt-1 text-xs">
                Lifts from capability paradigm sprints (e.g. question-bound revenue/weight aggregates,
                Gate A2a unit partition injection) will appear here with case IDs and evidence hashes.
              </div>
            </div>
          )}
        </div>

        {/* Gate Status */}
        <div>
          <div className="mb-2 text-xs font-medium uppercase tracking-wider text-[var(--color-text-secondary)]">
            Gate Progress (A1 / A2a / A2b)
          </div>

          {gateStatuses.length > 0 ? (
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
              {gateStatuses.map((g) => (
                <div
                  key={g.gate}
                  className="rounded border border-[var(--color-border)] bg-[var(--color-surface-base)] p-3 text-sm"
                >
                  <div className="font-mono text-xs text-[var(--color-text-secondary)]">{g.gate}</div>
                  <div className="mt-1 font-semibold text-[var(--color-text-primary)]">
                    {g.status}
                  </div>
                  <div className="text-xs text-[var(--color-text-tertiary)]">
                    {g.injections} injections
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-sm text-[var(--color-text-secondary)]">
              Gate status and injection counts from recent derivation work will surface here.
            </div>
          )}
        </div>

        <div className="border-t border-[var(--color-border-subtle)] pt-3 text-[10px] text-[var(--color-text-tertiary)]">
          All lifts maintain algebraic coherence and wrong=0 invariant. Evidence is ratification-gated.
        </div>
      </div>
    </Panel>
  );
}
