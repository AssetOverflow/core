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

  return (
    <section className="rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-surface-raised)] p-4">
      <h3 className="mb-3 text-sm font-semibold text-[var(--color-text-primary)]">Metadata Audit Details</h3>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs border-collapse">
          <thead>
            <tr className="border-b border-[var(--color-border-subtle)] text-[var(--color-text-muted)]">
              <th className="pb-2 font-medium">Property</th>
              <th className="pb-2 font-medium">Value</th>
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
              <td className="py-2 font-medium">Path</td>
              <td className="py-2 font-mono" data-testid="artifact-path-text">
                {artifact.path}
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
              <td className="py-2 font-medium">Divergences</td>
              <td className="py-2">
                <span className="inline-flex gap-2">
                  <span className="text-[var(--color-review-rejected)]">
                    Failure: {divergenceCounts.failure}
                  </span>
                  <span className="text-[var(--color-review-pending)]">
                    Warning: {divergenceCounts.warning}
                  </span>
                  <span className="text-[var(--color-grounding-vault)]">
                    Info: {divergenceCounts.info}
                  </span>
                </span>
              </td>
            </tr>
            <tr>
              <td className="py-2 font-medium">Content Type</td>
              <td className="py-2 font-mono">{artifact.content_type}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  );
}
