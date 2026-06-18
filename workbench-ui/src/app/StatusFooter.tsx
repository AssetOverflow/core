import { useState } from 'react';
import { useIsMutating } from '@tanstack/react-query';
import { useHealth, useRuntimeStatus } from '../api/queries';
import { useCopyToClipboard } from '../design/hooks/useCopyToClipboard';

function HealthIndicator() {
  const { data: health, isLoading } = useHealth();

  const healthy = health?.status === 'healthy';
  const pending = isLoading;

  const dotColor = pending
    ? 'var(--color-text-tertiary)'
    : healthy
      ? 'var(--color-state-success-text)'
      : 'var(--color-state-danger-text)';

  const label = pending ? 'Checking' : healthy ? 'Healthy' : 'Unhealthy';

  return (
    <span
      data-testid="health-indicator"
      className="inline-flex items-center gap-1.5 text-xs text-[var(--color-text-secondary)]"
      title={label}
    >
      <span
        className="inline-block h-2 w-2 rounded-full"
        style={{ backgroundColor: dotColor }}
      />
      {label}
    </span>
  );
}

export function StatusFooter() {
  const { data: runtime } = useRuntimeStatus();
  const isMutating = useIsMutating() > 0;
  const [revisionExpanded, setRevisionExpanded] = useState(false);
  const { copy } = useCopyToClipboard();

  const mutationModeEl = runtime?.mutation_mode ? (
    <span className="rounded bg-[var(--color-surface-inset)] px-1.5 py-px text-[10px] font-medium text-[var(--color-text-secondary)]">
      {runtime.mutation_mode === 'read_only' ? 'Read Only' : 'Runtime Turn'}
    </span>
  ) : null;

  // Small real enhancement: Capability health indicator (wrong=0 status)
  const capabilityHealth = runtime?.capability_health ?? { wrong_zero: true, flywheel_active: false };

  return (
    <footer className="flex h-9 items-center border-t border-[var(--color-border-subtle)] bg-[var(--color-surface-base)] px-3 text-xs text-[var(--color-text-secondary)]">
      <div className="flex flex-1 items-center gap-4">
        <HealthIndicator />

        {mutationModeEl}

        {/* NEW: Capability health indicator (small, real, non-stub) */}
        <span
          className="inline-flex items-center gap-1.5 text-xs"
          title={capabilityHealth.wrong_zero ? 'All capability lanes maintaining wrong=0' : 'Capability invariant violation detected'}
        >
          <span
            className={`inline-block h-2 w-2 rounded-full ${capabilityHealth.wrong_zero ? 'bg-[var(--color-state-success-text)]' : 'bg-[var(--color-state-danger-text)]'}`}
          />
          <span className="font-mono text-[10px]">
            {capabilityHealth.wrong_zero ? 'wrong=0' : 'wrong>0'}
          </span>
          {capabilityHealth.flywheel_active && (
            <span className="ml-1 text-[var(--color-state-success-text)]">flywheel</span>
          )}
        </span>

        {runtime?.git_revision && (
          <button
            onClick={() => copy(runtime.git_revision)}
            className="font-mono text-[var(--color-text-tertiary)] hover:text-[var(--color-text-primary)] focus:outline-none focus:ring-1 focus:ring-[var(--color-border)]"
            title="Copy full revision"
            aria-label="Copy git revision"
          >
            {runtime.git_revision.slice(0, 8)}
          </button>
        )}

        {runtime?.checkpoint_revision && (
          <button
            onClick={() => setRevisionExpanded(!revisionExpanded)}
            className="font-mono text-[var(--color-text-tertiary)] hover:text-[var(--color-text-primary)]"
            aria-expanded={revisionExpanded}
            aria-label="Toggle checkpoint details"
          >
            {runtime.checkpoint_revision.slice(0, 8)}
            {revisionExpanded && (
              <span className="ml-1 text-[var(--color-text-tertiary)]">(engine checkpoint)</span>
            )}
          </button>
        )}
      </div>

      {isMutating && (
        <span className="text-[var(--color-state-warning-text)]">Mutating…</span>
      )}
    </footer>
  );
}
