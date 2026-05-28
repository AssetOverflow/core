import { Link } from "react-router-dom";
import { useArtifact } from "../../api/queries";
import { EmptyState } from "../../design/components/states/EmptyState";
import { ErrorState } from "../../design/components/states/ErrorState";
import { LoadingState } from "../../design/components/states/LoadingState";
import { TraceHashBadge } from "../../design/components/badges";

function extractTraceHash(content: unknown): string | null {
  if (content && typeof content === "object" && "trace_hash" in content) {
    const v = (content as Record<string, unknown>).trace_hash;
    return typeof v === "string" ? v : null;
  }
  return null;
}

function extractProposalId(content: unknown): string | null {
  if (content && typeof content === "object" && "proposal_id" in content) {
    const v = (content as Record<string, unknown>).proposal_id;
    return typeof v === "string" ? v : null;
  }
  return null;
}

interface RunDetailProps {
  runId: string;
}

export function RunDetail({ runId }: RunDetailProps) {
  const { data, isLoading, isError, error } = useArtifact(runId);

  if (isLoading) {
    return <LoadingState label="Loading run detail…" />;
  }

  if (isError) {
    return (
      <ErrorState
        whatFailed={`Failed to load run ${runId}`}
        mutationStatus="No changes were made"
        reproducer={`GET /artifacts/${runId}`}
        retrySafety={
          error?.message ?? "Safe to retry — read-only operation"
        }
      />
    );
  }

  if (!data) {
    return (
      <EmptyState
        statement="Run detail not available."
        nextAction="Select a different run."
      />
    );
  }

  const traceHash = extractTraceHash(data.content);
  const proposalId = extractProposalId(data.content);

  return (
    <section
      className="flex flex-col gap-4 rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-surface-raised)] p-4"
      data-testid="run-detail"
    >
      <header className="flex items-start justify-between gap-3">
        <div>
          <h3 className="m-0 text-sm font-semibold text-[var(--color-text-primary)]">
            Run detail
          </h3>
          <p className="m-0 mt-1 font-mono text-xs text-[var(--color-text-secondary)]">
            {data.artifact_id}
          </p>
        </div>
        <Link
          to={`/replay?artifactId=${encodeURIComponent(data.artifact_id)}`}
          className="rounded border border-[var(--color-border-subtle)] px-2 py-1 text-xs text-[var(--color-text-primary)] hover:bg-[var(--color-surface-overlay)]"
          data-testid="run-detail-replay-link"
        >
          Open in Replay →
        </Link>
      </header>

      <dl
        className="grid grid-cols-[max-content_1fr] gap-x-3 gap-y-1 text-xs"
        data-testid="run-detail-metadata"
      >
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

        <dt className="text-[var(--color-text-secondary)]">Content type</dt>
        <dd className="m-0 text-[var(--color-text-primary)]">
          {data.content_type}
        </dd>

        {traceHash && (
          <>
            <dt className="text-[var(--color-text-secondary)]">Trace hash</dt>
            <dd className="m-0" data-testid="run-detail-trace-hash">
              <TraceHashBadge value={traceHash} />
            </dd>
          </>
        )}

        {proposalId && (
          <>
            <dt className="text-[var(--color-text-secondary)]">Proposal</dt>
            <dd className="m-0">
              <Link
                to={`/proposals?proposal_id=${encodeURIComponent(proposalId)}`}
                className="text-[var(--color-text-primary)] underline underline-offset-2 hover:text-[var(--color-focus-ring)]"
                data-testid="run-detail-proposal-link"
              >
                {proposalId}
              </Link>
            </dd>
          </>
        )}
      </dl>
    </section>
  );
}
