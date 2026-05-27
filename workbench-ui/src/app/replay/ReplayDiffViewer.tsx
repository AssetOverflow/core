import type { ReplayDivergence } from "../../types/api";
import { ReplayDivergenceSeverityBadge, ReplayDivergenceSeverity } from "../../design/components/badges";
import { StableJsonViewer } from "../../design/components/StableJsonViewer";
import { Copy } from "lucide-react";
import { Button } from "../../design/components/primitives/Button";

interface ReplayDiffViewerProps {
  divergences: ReplayDivergence[];
}

const severityOrder: Record<"info" | "warning" | "failure", number> = {
  failure: 3,
  warning: 2,
  info: 1,
};

function serializeValue(val: unknown): string {
  if (val === undefined) return "";
  try {
    return JSON.stringify(val);
  } catch {
    return String(val);
  }
}

export function ReplayDiffViewer({ divergences }: ReplayDiffViewerProps) {
  if (divergences.length === 0) {
    return null;
  }

  const sortedDivergences = [...divergences].sort((a, b) => {
    const diff = severityOrder[b.severity] - severityOrder[a.severity];
    if (diff !== 0) return diff;
    return a.path.localeCompare(b.path);
  });

  const copyPath = (path: string) => {
    navigator.clipboard.writeText(path).catch(() => {
      // fail silently
    });
  };

  return (
    <div className="space-y-4" data-testid="replay-diff-viewer">
      <h3 className="text-sm font-semibold text-[var(--color-text-primary)]">Replay Divergences</h3>
      <div className="space-y-4">
        {sortedDivergences.map((div) => {
          const key = `${div.severity}-${div.path}`;
          return (
            <div
              key={key}
              className="rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-surface-raised)] p-4 space-y-3"
            >
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--color-border-subtle)] pb-2">
                <div className="flex items-center gap-2">
                  <ReplayDivergenceSeverityBadge value={div.severity as ReplayDivergenceSeverity} />
                  <span className="font-mono text-xs text-[var(--color-text-secondary)] break-all select-all">
                    {div.path}
                  </span>
                </div>
                <Button
                  onClick={() => copyPath(div.path)}
                  variant="quiet"
                  type="button"
                  aria-label={`Copy path ${div.path}`}
                >
                  <Copy size={12} className="mr-1" />
                  Copy Path
                </Button>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <div className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-[var(--color-text-muted)]">
                    Original Value
                  </div>
                  <StableJsonViewer source={serializeValue(div.original)} />
                </div>
                <div>
                  <div className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-[var(--color-text-muted)]">
                    Replay Value
                  </div>
                  <StableJsonViewer source={serializeValue(div.replay)} />
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
