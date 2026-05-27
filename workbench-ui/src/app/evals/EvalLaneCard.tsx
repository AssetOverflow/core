import type { EvalLaneSummary } from "../../types/api";

export function EvalLaneCard({
  lane,
  isSelected,
  onSelect,
}: {
  lane: EvalLaneSummary;
  isSelected: boolean;
  onSelect: () => void;
}) {
  const readOnlyStyle = lane.read_only
    ? {
        backgroundColor: "color-mix(in srgb, var(--color-state-verified) 18%, transparent)",
        borderColor: "var(--color-state-verified)",
        color: "var(--color-state-verified)",
      }
    : {
        backgroundColor: "color-mix(in srgb, var(--color-state-undetermined) 18%, transparent)",
        borderColor: "var(--color-state-undetermined)",
        color: "var(--color-text-muted)",
      };

  return (
    <button
      onClick={onSelect}
      className={`w-full text-left p-3 rounded-lg border transition-all duration-150 focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--color-focus-ring)] ${
        isSelected
          ? "border-[var(--color-border-strong)] bg-[var(--color-surface-raised)] shadow-[var(--shadow-panel)]"
          : "border-[var(--color-border-subtle)] bg-[var(--color-surface-base)] hover:bg-[var(--color-surface-raised)]"
      }`}
      type="button"
      data-testid="eval-lane-card"
    >
      <div className="flex items-start justify-between gap-2">
        <h4 className="font-mono text-sm font-semibold text-[var(--color-text-primary)] truncate">
          {lane.lane}
        </h4>
        <span
          style={readOnlyStyle}
          className="shrink-0 inline-flex items-center rounded border px-1.5 py-0.5 text-[10px] font-semibold transition-colors"
          title={lane.read_only ? "API runs enabled" : "API run disabled — use CLI"}
          data-testid="read-only-badge"
        >
          {lane.read_only ? "Read-Only" : "CLI-Only"}
        </span>
      </div>

      {lane.description && (
        <p className="mt-1 text-xs text-[var(--color-text-secondary)] line-clamp-2">
          {lane.description}
        </p>
      )}

      <div className="mt-2.5 flex flex-wrap gap-1" data-testid="version-badges">
        {lane.versions.map((version) => (
          <span
            key={version}
            className="inline-flex items-center rounded bg-[var(--color-state-neutral-bg)] border border-[var(--color-state-neutral-border)] px-1 py-0.5 font-mono text-[9px] text-[var(--color-state-neutral-text)]"
          >
            {version}
          </span>
        ))}
      </div>
    </button>
  );
}
