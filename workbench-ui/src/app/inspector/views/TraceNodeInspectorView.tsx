import { Link } from "react-router-dom";
import { useArtifact } from "../../../api/queries";
import { LoadingState } from "../../../design/components/states/LoadingState";
import { ErrorState } from "../../../design/components/states/ErrorState";
import { EmptyState } from "../../../design/components/states/EmptyState";
import { TraceHashBadge } from "../../../design/components/badges";
import { parseTraceContent } from "../../trace/parseTraceContent";

export function TraceNodeInspectorView({
  artifactId,
  nodeId,
}: {
  artifactId: string;
  nodeId?: string;
}) {
  const { data, isLoading, isError, error } = useArtifact(artifactId);

  if (isLoading) return <LoadingState label="Loading trace node…" />;
  if (isError)
    return (
      <ErrorState
        whatFailed={`Failed to load trace ${artifactId}`}
        mutationStatus="No changes were made"
        reproducer={`GET /artifacts/${artifactId}`}
        retrySafety={error?.message ?? "Safe to retry — read-only operation"}
      />
    );
  if (!data)
    return (
      <EmptyState
        statement="No trace data."
        nextAction="Select another entity."
      />
    );

  const result = parseTraceContent(data.content);
  if (!result)
    return (
      <EmptyState
        statement={`Artifact ${artifactId} does not parse as a trace.`}
        nextAction="Pick another entity."
      />
    );

  return (
    <div data-testid="inspector-trace-node" className="flex flex-col gap-3">
      <header>
        <h3 className="m-0 text-sm font-semibold text-[var(--color-text-primary)]">
          Trace node
        </h3>
        <p className="m-0 mt-1 font-mono text-xs text-[var(--color-text-secondary)]">
          {artifactId}
          {nodeId ? <span className="ml-2">· {nodeId}</span> : null}
        </p>
      </header>

      {/* Addendum §2 — three surfaces rendered distinctly. */}
      <section
        className="flex flex-col gap-2"
        data-testid="inspector-trace-surfaces"
      >
        <div
          className="rounded border border-[var(--color-border-subtle)] bg-[var(--color-surface-base)] p-2"
          data-testid="inspector-trace-surface-surface"
        >
          <div className="text-[10px] uppercase tracking-wide text-[var(--color-text-secondary)]">
            surface · user-facing
          </div>
          <p className="m-0 mt-1 text-xs text-[var(--color-text-primary)]">
            {result.surface}
          </p>
        </div>
        <div
          className="rounded border border-[var(--color-border-subtle)] bg-[var(--color-surface-base)] p-2"
          data-testid="inspector-trace-surface-articulation"
        >
          <div className="text-[10px] uppercase tracking-wide text-[var(--color-text-secondary)]">
            articulation_surface · realizer
          </div>
          <p className="m-0 mt-1 text-xs text-[var(--color-text-primary)]">
            {result.articulation_surface ?? (
              <span className="text-[var(--color-text-secondary)]">
                not emitted
              </span>
            )}
          </p>
        </div>
        <div
          className="rounded border border-[var(--color-border-subtle)] bg-[var(--color-surface-base)] p-2"
          data-testid="inspector-trace-surface-walk"
        >
          <div className="text-[10px] uppercase tracking-wide text-[var(--color-text-secondary)]">
            walk_surface · manifold evidence
          </div>
          <p className="m-0 mt-1 font-mono text-[10px] text-[var(--color-text-primary)]">
            {result.walk_surface ?? (
              <span className="text-[var(--color-text-secondary)]">
                not emitted
              </span>
            )}
          </p>
        </div>
      </section>

      <dl className="grid grid-cols-[max-content_1fr] gap-x-3 gap-y-1 text-xs">
        <dt className="text-[var(--color-text-secondary)]">grounding</dt>
        <dd className="m-0 text-[var(--color-text-primary)]">
          {result.grounding_source}
        </dd>
        <dt className="text-[var(--color-text-secondary)]">epistemic</dt>
        <dd className="m-0 text-[var(--color-text-primary)]">
          {result.epistemic_state}
        </dd>
        <dt className="text-[var(--color-text-secondary)]">clearance</dt>
        <dd className="m-0 text-[var(--color-text-primary)]">
          {result.normative_clearance}
        </dd>
      </dl>

      {result.trace_hash ? (
        <div data-testid="inspector-trace-hash">
          <TraceHashBadge value={result.trace_hash} />
        </div>
      ) : null}

      <Link
        to={`/trace?traceId=${encodeURIComponent(artifactId)}`}
        className="self-start rounded border border-[var(--color-border-subtle)] px-2 py-1 text-xs text-[var(--color-text-primary)] hover:bg-[var(--color-surface-overlay)]"
        data-testid="inspector-trace-open-link"
      >
        Open in Trace →
      </Link>
    </div>
  );
}
