import { Timestamp } from "../Timestamp/Timestamp";
import { VirtualizedList } from "../VirtualizedList/VirtualizedList";

export interface TimelineEntry {
  id: string;
  timestamp: string | null;
  source: string;
  summary: string;
  mutationBoundary?: boolean;
}

export const TIMELINE_PREVIEW_ENTRY: TimelineEntry = {
  id: "preview-audit-event",
  timestamp: "2026-06-12T18:00:00Z",
  source: "operator_telemetry",
  summary: "Operator telemetry recorded without mutation.",
  mutationBoundary: false,
};

export interface TimelineProps<T extends TimelineEntry> {
  entries: readonly T[];
  selectedId?: string | null;
  onSelect?: (entry: T) => void;
  height: number | string;
  ariaLabel: string;
  estimateSize?: number;
  initialRect?: { width: number; height: number };
}

function TimelineRow<T extends TimelineEntry>({
  entry,
  selected,
  focused,
  onSelect,
}: {
  entry: T;
  selected: boolean;
  focused: boolean;
  onSelect: () => void;
}) {
  const weighted = !!entry.mutationBoundary;
  const borderClass = weighted || selected
    ? "border-l-[var(--color-selected-border)]"
    : focused
      ? "border-l-[var(--color-focus-ring)]"
      : "border-l-transparent";

  return (
    <article
      role="button"
      tabIndex={-1}
      aria-current={selected ? "true" : undefined}
      onClick={onSelect}
      className={`grid gap-2 border-b border-l-2 border-b-[var(--color-border-subtle)] px-3 py-3 text-left transition-colors hover:bg-[var(--color-surface-inset)] ${borderClass} ${
        selected ? "bg-[var(--color-selected-bg)]" : ""
      }`}
    >
      <div className="flex flex-wrap items-center gap-2">
        {entry.timestamp ? (
          <Timestamp iso={entry.timestamp} format="both" />
        ) : (
          <span className="text-xs text-[var(--color-text-muted)]">No timestamp</span>
        )}
        <span className="rounded border border-[var(--color-border-subtle)] bg-[var(--color-surface-inset)] px-1.5 py-0.5 font-mono text-[10px] text-[var(--color-text-secondary)]">
          {entry.source}
        </span>
        {weighted ? (
          <span className="rounded border border-[var(--color-selected-border)] bg-[var(--color-selected-bg)] px-1.5 py-0.5 text-[10px] font-semibold text-[var(--color-text-primary)]">
            Mutation boundary
          </span>
        ) : null}
      </div>
      <p className="m-0 text-sm leading-5 text-[var(--color-text-primary)]">
        {entry.summary}
      </p>
    </article>
  );
}

export function Timeline<T extends TimelineEntry>({
  entries,
  selectedId,
  onSelect,
  height,
  ariaLabel,
  estimateSize = 84,
  initialRect,
}: TimelineProps<T>) {
  return (
    <VirtualizedList
      ariaLabel={ariaLabel}
      estimateSize={estimateSize}
      getKey={(entry) => entry.id}
      height={height}
      initialRect={initialRect}
      items={entries}
      onActivate={(entry) => onSelect?.(entry)}
      renderItem={(entry, _index, focused) => (
        <TimelineRow
          entry={entry}
          selected={entry.id === selectedId}
          focused={focused}
          onSelect={() => onSelect?.(entry)}
        />
      )}
    />
  );
}
