import { Link } from "react-router-dom";
import { useReplayComparison } from "../../../api/queries";
import { LoadingState } from "../../../design/components/states/LoadingState";
import { ErrorState } from "../../../design/components/states/ErrorState";
import { EmptyState } from "../../../design/components/states/EmptyState";

const SEVERITY_LABEL: Record<string, string> = {
  info: "low",
  warning: "material",
  failure: "breaking",
};

export function ReplayDiffInspectorView({
  artifactId,
}: {
  artifactId: string;
}) {
  const { data, isLoading, isError, error } = useReplayComparison(artifactId);

  if (isLoading) return <LoadingState label="Loading replay comparison…" />;
  if (isError)
    return (
      <ErrorState
        whatFailed={`Failed to load replay for ${artifactId}`}
        mutationStatus="No changes were made"
        reproducer={`GET /replay/${artifactId}`}
        retrySafety={error?.message ?? "Safe to retry — read-only operation"}
      />
    );
  if (!data)
    return (
      <EmptyState
        statement="No replay comparison data."
        nextAction="Select another entity."
      />
    );

  const failureCount = data.divergences.filter((d) => d.severity === "failure").length;
  const warningCount = data.divergences.filter((d) => d.severity === "warning").length;
  const infoCount = data.divergences.filter((d) => d.severity === "info").length;

  return (
    <div data-testid="inspector-replay-diff" className="flex flex-col gap-3">
      <header>
        <h3 className="m-0 text-sm font-semibold text-[var(--color-text-primary)]">
          Replay comparison
        </h3>
        <p className="m-0 mt-1 font-mono text-xs text-[var(--color-text-secondary)]">
          {data.artifact_id}
        </p>
      </header>

      <dl className="grid grid-cols-[max-content_1fr] gap-x-3 gap-y-1 text-xs">
        <dt className="text-[var(--color-text-secondary)]">Equivalent</dt>
        <dd className="m-0 text-[var(--color-text-primary)]">
          {data.equivalent ? "yes" : "no"}
        </dd>
        <dt className="text-[var(--color-text-secondary)]">Original hash</dt>
        <dd className="m-0 font-mono text-[var(--color-text-primary)]">
          {data.original_hash ? data.original_hash.slice(0, 16) : "—"}
        </dd>
        <dt className="text-[var(--color-text-secondary)]">Replay hash</dt>
        <dd className="m-0 font-mono text-[var(--color-text-primary)]">
          {data.replay_hash ? data.replay_hash.slice(0, 16) : "—"}
        </dd>
      </dl>

      <section
        className="rounded border border-[var(--color-border-subtle)] bg-[var(--color-surface-base)] p-2 text-xs"
        data-testid="inspector-replay-counts"
      >
        <div className="font-semibold text-[var(--color-text-primary)]">
          Divergences ({data.divergences.length})
        </div>
        <div className="mt-1 grid grid-cols-3 gap-2 tabular-nums">
          <div>
            <div className="text-[var(--color-text-secondary)]">
              {SEVERITY_LABEL.failure}
            </div>
            <div className="text-[var(--color-text-primary)]">{failureCount}</div>
          </div>
          <div>
            <div className="text-[var(--color-text-secondary)]">
              {SEVERITY_LABEL.warning}
            </div>
            <div className="text-[var(--color-text-primary)]">{warningCount}</div>
          </div>
          <div>
            <div className="text-[var(--color-text-secondary)]">
              {SEVERITY_LABEL.info}
            </div>
            <div className="text-[var(--color-text-primary)]">{infoCount}</div>
          </div>
        </div>
      </section>

      <Link
        to={`/replay?artifactId=${encodeURIComponent(data.artifact_id)}`}
        className="self-start rounded border border-[var(--color-border-subtle)] px-2 py-1 text-xs text-[var(--color-text-primary)] hover:bg-[var(--color-surface-overlay)]"
        data-testid="inspector-replay-open-link"
      >
        Open in Replay →
      </Link>
    </div>
  );
}
