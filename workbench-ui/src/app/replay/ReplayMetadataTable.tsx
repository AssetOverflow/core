import type { ArtifactDetail, ReplayComparison } from "../../types/api";
import { TraceHashBadge } from "../../design/components/badges";

interface ReplayMetadataTableProps {
  artifact: ArtifactDetail;
  comparison: ReplayComparison;
}

export function ReplayMetadataTable({ artifact, comparison }: ReplayMetadataTableProps) {
  const divergenceCounts = comparison.divergences.reduce(
    (acc, div) => {
      acc[div.severity] = (acc[div.severity] || 0) + 1;
      return acc;
    },
    { info: 0, warning: 0, failure: 0 } as Record<"info" | "warning" | "failure", number>
  );

  // Extract run ID if present in content
  let runId: string | null = null;
  if (artifact.content && typeof artifact.content === "object") {
    const contentObj = artifact.content as any;
    runId = contentObj.run_id || contentObj.runId || contentObj.workflow_run_id || contentObj.session_id || contentObj.reasoning_trace_id || null;
  }

  // Extract lane if present in content or parsed from path
  let lane: string | null = null;
  if (artifact.content && typeof artifact.content === "object") {
    const contentObj = artifact.content as any;
    lane = contentObj.lane || contentObj.lane_name || contentObj.laneName || contentObj.split || null;
  }
  if (!lane && artifact.path) {
    const parts = artifact.path.split("/");
    if (parts[0] === "evals" && parts.length > 1) {
      lane = parts[1];
    }
  }

  // Format timestamp nicely
  const timestamp = artifact.created_at
    ? new Date(artifact.created_at).toLocaleString()
    : null;

  return (
    <section className="rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-surface-raised)] p-4">
      <h3 className="mb-3 text-sm font-semibold text-[var(--color-text-primary)]">Metadata Audit Details</h3>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs border-collapse">
          <thead>
            <tr className="border-b border-[var(--color-border-subtle)] text-[var(--color-text-muted)]">
              <th className="pb-2 font-medium w-1/3">Property</th>
              <th className="pb-2 font-medium w-2/3">Value</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[var(--color-border-subtle)] text-[var(--color-text-secondary)]">
            <tr>
              <td className="py-2 font-medium">Artifact ID</td>
              <td className="py-2 font-mono">{artifact.artifact_id}</td>
            </tr>
            <tr>
              <td className="py-2 font-medium">Kind</td>
              <td className="py-2">{artifact.kind}</td>
            </tr>
            <tr>
              <td className="py-2 font-medium">Content Type</td>
              <td className="py-2 font-mono">{artifact.content_type}</td>
            </tr>
            <tr>
              <td className="py-2 font-medium">Path</td>
              <td className="py-2 font-mono" data-testid="artifact-path-text">
                {artifact.path}
              </td>
            </tr>
            <tr>
              <td className="py-2 font-medium">Created At</td>
              <td className="py-2" data-testid="artifact-created-at">
                {timestamp || <span className="text-[var(--color-text-muted)]">None</span>}
              </td>
            </tr>
            <tr>
              <td className="py-2 font-medium">Artifact Digest / Trace Hash</td>
              <td className="py-2">
                {artifact.digest ? (
                  <TraceHashBadge value={artifact.digest} />
                ) : (
                  <span className="text-[var(--color-text-muted)]">None</span>
                )}
              </td>
            </tr>
            <tr>
              <td className="py-2 font-medium">Original Hash</td>
              <td className="py-2">
                {comparison.original_hash ? (
                  <TraceHashBadge value={comparison.original_hash} />
                ) : (
                  <span className="text-[var(--color-text-muted)]">None</span>
                )}
              </td>
            </tr>
            <tr>
              <td className="py-2 font-medium">Replay Hash</td>
              <td className="py-2">
                {comparison.replay_hash ? (
                  <TraceHashBadge value={comparison.replay_hash} />
                ) : (
                  <span className="text-[var(--color-text-muted)]">None</span>
                )}
              </td>
            </tr>
            <tr>
              <td className="py-2 font-medium">Run ID</td>
              <td className="py-2 font-mono" data-testid="artifact-run-id">
                {runId || <span className="text-[var(--color-text-muted)]">None</span>}
              </td>
            </tr>
            <tr>
              <td className="py-2 font-medium">Lane</td>
              <td className="py-2" data-testid="artifact-lane">
                {lane || <span className="text-[var(--color-text-muted)]">None</span>}
              </td>
            </tr>
            <tr>
              <td className="py-2 font-medium">Divergences</td>
              <td className="py-2">
                <span className="inline-flex flex-wrap gap-x-3 gap-y-1">
                  <span className="text-[var(--color-review-rejected)] font-medium">
                    Failure (breaking): {divergenceCounts.failure}
                  </span>
                  <span className="text-[var(--color-review-pending)] font-medium">
                    Warning (material): {divergenceCounts.warning}
                  </span>
                  <span className="text-[var(--color-grounding-vault)] font-medium">
                    Info (low): {divergenceCounts.info}
                  </span>
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  );
}
