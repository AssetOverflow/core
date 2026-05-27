import type { ArtifactDetail, ReplayComparison } from "../../types/api";
import { ReplayStatusBadge, TraceHashBadge, ReplayStatus } from "../../design/components/badges";
import { EmptyState } from "../../design/components/states/EmptyState";
import { ReplayDiffViewer } from "./ReplayDiffViewer";
import { ReplayMetadataTable } from "./ReplayMetadataTable";

interface ReplayComparisonPanelProps {
  artifact: ArtifactDetail;
  comparison?: ReplayComparison | null;
  status: ReplayStatus;
}

export function ReplayComparisonPanel({
  artifact,
  comparison,
  status,
}: ReplayComparisonPanelProps) {
  const finalComparison: ReplayComparison = comparison || {
    artifact_id: artifact.artifact_id,
    original_hash: artifact.digest,
    replay_hash: null,
    equivalent: false,
    divergences: [],
  };

  return (
    <div className="space-y-6" data-testid="replay-comparison-panel">
      <div className="flex items-center justify-between border-b border-[var(--color-border-subtle)] pb-4">
        <h2 className="text-base font-semibold text-[var(--color-text-primary)]">Replay Evidence</h2>
        <ReplayStatusBadge value={status} />
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-surface-raised)] p-4 flex flex-col gap-2">
          <span className="text-[10px] font-semibold text-[var(--color-text-muted)] uppercase tracking-wider">
            Original Hash
          </span>
          <div>
            {finalComparison.original_hash ? (
              <TraceHashBadge value={finalComparison.original_hash} />
            ) : (
              <span className="text-xs font-mono text-[var(--color-text-muted)]">not_available</span>
            )}
          </div>
        </div>
        <div className="rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-surface-raised)] p-4 flex flex-col gap-2">
          <span className="text-[10px] font-semibold text-[var(--color-text-muted)] uppercase tracking-wider">
            Replay Hash
          </span>
          <div>
            {finalComparison.replay_hash ? (
              <TraceHashBadge value={finalComparison.replay_hash} />
            ) : (
              <span className="text-xs font-mono text-[var(--color-text-muted)]">not_available</span>
            )}
          </div>
        </div>
      </div>

      <div className="space-y-4">
        {status === "evidence_unavailable" ? (
          <EmptyState
            statement="Replay evidence is not available on the backend for this artifact kind."
            nextAction="Verify the backend replay path configuration."
          />
        ) : status === "equivalent" ? (
          <EmptyState
            statement="Replay evidence intact — no divergences."
            nextAction={{ kind: "cli", command: "core test --suite runtime" }}
          />
        ) : status === "not_yet_replayed" ? (
          <EmptyState
            statement="No replay has been attempted for this artifact yet."
            nextAction={{ kind: "cli", command: `core replay ${artifact.artifact_id}` }}
          />
        ) : (
          <ReplayDiffViewer divergences={finalComparison.divergences} />
        )}
      </div>

      <ReplayMetadataTable artifact={artifact} comparison={finalComparison} />
    </div>
  );
}
