import { useMemo } from "react";
import { useSearchParams } from "react-router-dom";
import { useArtifacts } from "../../api/queries";
import { EmptyState } from "../../design/components/states/EmptyState";
import { ErrorState } from "../../design/components/states/ErrorState";
import { LoadingState } from "../../design/components/states/LoadingState";
import { cn } from "../../design/lib";
import type { ArtifactRef } from "../../types/api";
import { TraceDetail } from "./TraceDetail";
import { useTraceCommands } from "./useTraceCommands";

function formatTime(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toISOString().replace("T", " ").slice(0, 19) + " UTC";
}

export function TraceRoute() {
  const { data: artifacts, isLoading, isError, error } = useArtifacts();
  const [searchParams, setSearchParams] = useSearchParams();
  const selectedId = searchParams.get("traceId");

  const traces: ArtifactRef[] = useMemo(() => {
    const all = artifacts ?? [];
    return all
      .filter((a) => a.kind === "trace")
      .sort((a, b) => {
        const aT = a.created_at ?? "";
        const bT = b.created_at ?? "";
        if (aT === bT) return a.artifact_id.localeCompare(b.artifact_id);
        return bT.localeCompare(aT);
      });
  }, [artifacts]);

  useTraceCommands(traces);

  function handleSelect(id: string) {
    const next = new URLSearchParams(searchParams);
    next.set("traceId", id);
    setSearchParams(next, { replace: false });
  }

  if (isLoading) {
    return (
      <div className="p-4" data-testid="trace-route">
        <LoadingState label="Loading traces…" />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="p-4" data-testid="trace-route">
        <ErrorState
          whatFailed="Failed to load trace index"
          mutationStatus="No changes were made"
          reproducer="GET /artifacts"
          retrySafety={error?.message ?? "Safe to retry — read-only operation"}
        />
      </div>
    );
  }

  if (traces.length === 0) {
    return (
      <div className="p-4" data-testid="trace-route">
        <EmptyState
          statement="No traces recorded yet."
          nextAction={{ kind: "cli", command: "core eval cognition" }}
        />
      </div>
    );
  }

  return (
    <div
      className="grid h-full grid-cols-1 gap-4 p-4 md:grid-cols-[16rem_1fr]"
      data-testid="trace-route"
    >
      <nav
        className="flex flex-col gap-1 overflow-y-auto border-r border-[var(--color-border-subtle)] pr-2"
        aria-label="Trace sessions"
        data-testid="trace-list"
      >
        <h2 className="px-2 text-xs font-semibold uppercase tracking-wider text-[var(--color-text-secondary)]">
          Trace sessions
        </h2>
        {traces.map((t) => {
          const isSelected = t.artifact_id === selectedId;
          return (
            <button
              key={t.artifact_id}
              type="button"
              onClick={() => handleSelect(t.artifact_id)}
              data-testid={`trace-list-${t.artifact_id}`}
              aria-current={isSelected ? "true" : undefined}
              className={cn(
                "w-full rounded px-2 py-1.5 text-left text-xs focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--color-focus-ring)]",
                isSelected
                  ? "bg-[var(--color-surface-raised)] text-[var(--color-text-primary)] border-l-2 border-[var(--color-focus-ring)] pl-1.5"
                  : "text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-raised)] hover:text-[var(--color-text-primary)]",
              )}
            >
              <div className="truncate font-mono">{t.artifact_id}</div>
              <div className="mt-0.5 font-mono text-[10px] tabular-nums text-[var(--color-text-muted)]">
                {formatTime(t.created_at)}
              </div>
            </button>
          );
        })}
      </nav>

      <div className="overflow-y-auto" data-testid="trace-detail-pane">
        {selectedId ? (
          <TraceDetail traceId={selectedId} />
        ) : (
          <EmptyState
            statement="Select a trace to inspect its surfaces."
            nextAction="Pick a session on the left."
          />
        )}
      </div>
    </div>
  );
}
