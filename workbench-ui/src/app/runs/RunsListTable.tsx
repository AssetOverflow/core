import { useMemo, useState } from "react";
import type { ArtifactKind, ArtifactRef } from "../../types/api";
import { cn } from "../../design/lib";

type SortDir = "asc" | "desc";

const KIND_FILTERS: ReadonlyArray<ArtifactKind | "all"> = [
  "all",
  "trace",
  "eval_result",
  "proposal",
  "contemplation_report",
  "telemetry",
  "engine_state_manifest",
  "unknown",
];

interface RunsListTableProps {
  runs: ArtifactRef[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toISOString().replace("T", " ").slice(0, 19) + " UTC";
}

export function RunsListTable({ runs, selectedId, onSelect }: RunsListTableProps) {
  const [kindFilter, setKindFilter] = useState<ArtifactKind | "all">("all");
  const [sortDir, setSortDir] = useState<SortDir>("desc");

  const visible = useMemo(() => {
    const filtered =
      kindFilter === "all" ? runs : runs.filter((r) => r.kind === kindFilter);
    return [...filtered].sort((a, b) => {
      const aT = a.created_at ?? "";
      const bT = b.created_at ?? "";
      if (aT === bT) return a.artifact_id.localeCompare(b.artifact_id);
      const cmp = aT.localeCompare(bT);
      return sortDir === "desc" ? -cmp : cmp;
    });
  }, [runs, kindFilter, sortDir]);

  if (runs.length === 0) {
    return null; // EmptyState owned by parent route
  }

  return (
    <div className="flex flex-col gap-3" data-testid="runs-list-table">
      <div className="flex items-center gap-2">
        <label
          htmlFor="runs-kind-filter"
          className="text-xs text-[var(--color-text-secondary)]"
        >
          Kind:
        </label>
        <select
          id="runs-kind-filter"
          className="rounded border border-[var(--color-border-subtle)] bg-[var(--color-surface-sunken)] px-2 py-1 text-xs text-[var(--color-text-primary)]"
          value={kindFilter}
          onChange={(e) => setKindFilter(e.target.value as ArtifactKind | "all")}
          data-testid="runs-kind-filter"
        >
          {KIND_FILTERS.map((k) => (
            <option key={k} value={k}>
              {k === "all" ? "All" : k.replace(/_/g, " ")}
            </option>
          ))}
        </select>
      </div>

      <table
        className="w-full border-collapse text-xs"
        data-testid="runs-table"
      >
        <thead>
          <tr className="border-b border-[var(--color-border-subtle)] text-left text-[var(--color-text-secondary)]">
            <th className="py-2 pr-2 font-medium">Artifact ID</th>
            <th className="py-2 px-2 font-medium">Kind</th>
            <th className="py-2 px-2 font-medium">
              <button
                type="button"
                className="inline-flex items-center gap-1 text-left font-medium text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]"
                onClick={() =>
                  setSortDir((d) => (d === "desc" ? "asc" : "desc"))
                }
                aria-label={`Sort by date (${sortDir === "desc" ? "descending" : "ascending"})`}
                data-testid="runs-sort-date"
              >
                Created
                <span aria-hidden>{sortDir === "desc" ? "↓" : "↑"}</span>
              </button>
            </th>
          </tr>
        </thead>
        <tbody>
          {visible.length === 0 ? (
            <tr>
              <td
                colSpan={3}
                className="py-3 text-center text-[var(--color-text-muted)]"
                data-testid="runs-no-match"
              >
                No runs match filter.
              </td>
            </tr>
          ) : (
            visible.map((r) => {
              const isSelected = r.artifact_id === selectedId;
              return (
                <tr
                  key={r.artifact_id}
                  className={cn(
                    "border-b border-[var(--color-border-subtle)]",
                    isSelected && "bg-[var(--color-surface-raised)]",
                  )}
                >
                  <td className="py-2 pr-2 font-mono">
                    <button
                      type="button"
                      onClick={() => onSelect(r.artifact_id)}
                      className={cn(
                        "text-left underline-offset-2 hover:underline",
                        isSelected
                          ? "text-[var(--color-text-primary)]"
                          : "text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]",
                      )}
                      data-testid={`runs-row-${r.artifact_id}`}
                      aria-current={isSelected ? "true" : undefined}
                    >
                      {r.artifact_id}
                    </button>
                  </td>
                  <td className="py-2 px-2 text-[var(--color-text-secondary)]">
                    {r.kind.replace(/_/g, " ")}
                  </td>
                  <td className="py-2 px-2 font-mono tabular-nums text-[var(--color-text-secondary)]">
                    {formatDate(r.created_at)}
                  </td>
                </tr>
              );
            })
          )}
        </tbody>
      </table>
    </div>
  );
}
