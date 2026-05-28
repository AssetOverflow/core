import { Link } from "react-router-dom";
import { useArtifact } from "../../../api/queries";
import { LoadingState } from "../../../design/components/states/LoadingState";
import { ErrorState } from "../../../design/components/states/ErrorState";
import { EmptyState } from "../../../design/components/states/EmptyState";

export function ArtifactInspectorView({
  artifactId,
}: {
  artifactId: string;
}) {
  const { data, isLoading, isError, error } = useArtifact(artifactId);

  if (isLoading)
    return <LoadingState label="Loading artifact detail…" />;
  if (isError)
    return (
      <ErrorState
        whatFailed={`Failed to load artifact ${artifactId}`}
        mutationStatus="No changes were made"
        reproducer={`GET /artifacts/${artifactId}`}
        retrySafety={error?.message ?? "Safe to retry — read-only operation"}
      />
    );
  if (!data)
    return (
      <EmptyState
        statement="No artifact data."
        nextAction="Select another entity."
      />
    );

  return (
    <div data-testid="inspector-artifact" className="flex flex-col gap-3">
      <header>
        <h3 className="m-0 text-sm font-semibold text-[var(--color-text-primary)]">
          Artifact
        </h3>
        <p className="m-0 mt-1 font-mono text-xs text-[var(--color-text-secondary)]">
          {data.artifact_id}
        </p>
      </header>
      <dl className="grid grid-cols-[max-content_1fr] gap-x-3 gap-y-1 text-xs">
        <dt className="text-[var(--color-text-secondary)]">Kind</dt>
        <dd className="m-0 text-[var(--color-text-primary)]">
          {data.kind.replace(/_/g, " ")}
        </dd>
        <dt className="text-[var(--color-text-secondary)]">Path</dt>
        <dd className="m-0 font-mono text-[var(--color-text-primary)]">
          {data.path}
        </dd>
        <dt className="text-[var(--color-text-secondary)]">Created</dt>
        <dd className="m-0 font-mono tabular-nums text-[var(--color-text-primary)]">
          {data.created_at ?? "—"}
        </dd>
        <dt className="text-[var(--color-text-secondary)]">Digest</dt>
        <dd className="m-0 font-mono text-[var(--color-text-primary)]">
          {data.digest ?? "—"}
        </dd>
      </dl>
      <div className="flex flex-wrap gap-2 text-xs">
        <Link
          to={`/replay?artifactId=${encodeURIComponent(data.artifact_id)}`}
          className="rounded border border-[var(--color-border-subtle)] px-2 py-1 text-[var(--color-text-primary)] hover:bg-[var(--color-surface-overlay)]"
          data-testid="inspector-artifact-replay-link"
        >
          Open in Replay →
        </Link>
        <Link
          to={`/runs?runId=${encodeURIComponent(data.artifact_id)}`}
          className="rounded border border-[var(--color-border-subtle)] px-2 py-1 text-[var(--color-text-primary)] hover:bg-[var(--color-surface-overlay)]"
          data-testid="inspector-artifact-runs-link"
        >
          Open in Runs →
        </Link>
      </div>
    </div>
  );
}
