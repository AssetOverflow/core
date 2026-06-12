import type { ArtifactRef } from "../../types/api";
import { cn } from "../../design/lib";
import { EmptyState } from "../../design/components/states/EmptyState";
import { useListNavigation } from "../../design/hooks/useListNavigation";

interface ArtifactListProps {
  artifacts: ArtifactRef[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}

const KINDS = [
  "trace",
  "eval_result",
  "proposal",
  "contemplation_report",
  "telemetry",
  "engine_state_manifest",
  "unknown",
] as const;

type ArtifactKind = (typeof KINDS)[number];

export function ArtifactList({ artifacts, selectedId, onSelect }: ArtifactListProps) {
  // Initialize grouped structure
  const grouped: Record<ArtifactKind, ArtifactRef[]> = {
    trace: [],
    eval_result: [],
    proposal: [],
    contemplation_report: [],
    telemetry: [],
    engine_state_manifest: [],
    unknown: [],
  };

  artifacts.forEach((art) => {
    const kind = KINDS.includes(art.kind as ArtifactKind)
      ? (art.kind as ArtifactKind)
      : "unknown";
    grouped[kind].push(art);
  });

  // Sort each group
  KINDS.forEach((kind) => {
    grouped[kind].sort((a, b) => {
      if (a.created_at && b.created_at) {
        return b.created_at.localeCompare(a.created_at);
      }
      if (a.created_at) return -1;
      if (b.created_at) return 1;
      return a.artifact_id.localeCompare(b.artifact_id);
    });
  });

  // Flat traversal order across groups for the keyboard spine (R0d).
  const flatOrder = KINDS.flatMap((kind) => grouped[kind]);
  const flatIndexById = new Map(flatOrder.map((a, i) => [a.artifact_id, i]));
  const { listProps, itemProps } = useListNavigation({
    itemCount: flatOrder.length,
    onActivate: (index) => {
      const art = flatOrder[index];
      if (art) onSelect(art.artifact_id);
    },
  });

  if (artifacts.length === 0) {
    return (
      <div className="p-2" data-testid="artifact-list-empty">
        <EmptyState
          statement="No artifacts available."
          nextAction={{ kind: "cli", command: "core eval cognition" }}
        />
      </div>
    );
  }

  return (
    <nav
      className="flex h-full flex-col gap-4 overflow-y-auto pr-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--color-focus-ring)]"
      aria-label="Artifact list navigation"
      data-testid="artifact-list"
      {...listProps}
    >
      {KINDS.map((kind) => {
        const items = grouped[kind];
        if (items.length === 0) return null;

        return (
          <div key={kind} className="space-y-1" data-testid={`group-${kind}`}>
            <h4 className="px-2 text-[10px] font-semibold uppercase tracking-wider text-[var(--color-text-muted)]">
              {kind.replace(/_/g, " ")}
            </h4>
            <div className="space-y-0.5">
              {items.map((art) => {
                const isSelected = art.artifact_id === selectedId;
                const { ref: rowRef, ...rowProps } = itemProps(
                  flatIndexById.get(art.artifact_id) ?? 0,
                );
                return (
                  <button
                    key={art.artifact_id}
                    {...rowProps}
                    ref={rowRef}
                    onClick={() => onSelect(art.artifact_id)}
                    type="button"
                    className={cn(
                      "w-full rounded px-2 py-1.5 text-left focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--color-focus-ring)]",
                      isSelected
                        ? "bg-[var(--color-surface-raised)] text-[var(--color-text-primary)] border-l-2 border-[var(--color-focus-ring)] pl-1.5"
                        : "text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-raised)] hover:text-[var(--color-text-primary)]"
                    )}
                    aria-current={isSelected ? "true" : undefined}
                    data-testid={`artifact-${art.artifact_id}`}
                  >
                    <div className="truncate text-xs font-medium font-mono">
                      {art.artifact_id}
                    </div>
                    {art.created_at && (
                      <div className="text-[10px] text-[var(--color-text-muted)] mt-0.5">
                        {new Date(art.created_at).toLocaleTimeString([], {
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </div>
                    )}
                  </button>
                );
              })}
            </div>
          </div>
        );
      })}
    </nav>
  );
}
