import { Link } from "react-router-dom";
import { useArtifact } from "../../api/queries";
import { EmptyState } from "../../design/components/states/EmptyState";
import { ErrorState } from "../../design/components/states/ErrorState";
import { LoadingState } from "../../design/components/states/LoadingState";
import { TraceHashBadge } from "../../design/components/badges";
import type { ChatTurnResult, TurnVerdict } from "../../types/api";
import { parseTraceContent } from "./parseTraceContent";
import { TraceSurfaces } from "./TraceSurfaces";

function VerdictRow({
  label,
  verdict,
}: {
  label: string;
  verdict: TurnVerdict | null;
}) {
  return (
    <div className="grid grid-cols-[6rem_1fr] gap-2 text-xs">
      <dt className="text-[var(--color-text-secondary)]">{label}</dt>
      <dd className="m-0 text-[var(--color-text-primary)]">
        {verdict ? (
          <>
            <span>{verdict.outcome}</span>
            {verdict.runtime_detail ? (
              <span className="ml-2 font-mono text-[var(--color-text-secondary)]">
                {verdict.runtime_detail}
              </span>
            ) : null}
          </>
        ) : (
          <span className="text-[var(--color-text-secondary)]">not emitted</span>
        )}
      </dd>
    </div>
  );
}

interface TraceDetailProps {
  traceId: string;
}

export function TraceDetail({ traceId }: TraceDetailProps) {
  const { data, isLoading, isError, error } = useArtifact(traceId);

  if (isLoading) {
    return <LoadingState label="Loading trace…" />;
  }

  if (isError) {
    return (
      <ErrorState
        whatFailed={`Failed to load trace ${traceId}`}
        mutationStatus="No changes were made"
        reproducer={`GET /artifacts/${traceId}`}
        retrySafety={error?.message ?? "Safe to retry — read-only operation"}
      />
    );
  }

  if (!data) {
    return (
      <EmptyState
        statement="Trace not available."
        nextAction="Pick another trace."
      />
    );
  }

  const result: ChatTurnResult | null = parseTraceContent(data.content);
  if (!result) {
    return (
      <EmptyState
        statement={`Artifact ${data.artifact_id} does not parse as a trace.`}
        nextAction={{
          kind: "cli",
          command: `core artifact show ${data.artifact_id}`,
        }}
      />
    );
  }

  return (
    <article
      className="flex flex-col gap-4"
      data-testid="trace-detail"
      aria-label="Trace detail"
    >
      <header className="flex items-start justify-between gap-3 rounded-md border border-[var(--color-border-subtle)] bg-[var(--color-surface-raised)] p-3">
        <div>
          <h2 className="m-0 text-sm font-semibold text-[var(--color-text-primary)]">
            {data.artifact_id}
          </h2>
          {data.created_at ? (
            <p className="m-0 mt-1 font-mono text-[10px] tabular-nums text-[var(--color-text-secondary)]">
              {data.created_at}
            </p>
          ) : null}
        </div>
        <Link
          to={`/replay?artifactId=${encodeURIComponent(data.artifact_id)}`}
          className="rounded border border-[var(--color-border-subtle)] px-2 py-1 text-xs text-[var(--color-text-primary)] hover:bg-[var(--color-surface-overlay)]"
          data-testid="trace-detail-replay-link"
        >
          Open in Replay →
        </Link>
      </header>

      {result.refusal_emitted ? (
        <section
          className="rounded-md border border-[var(--color-state-danger-border)] bg-[var(--color-state-danger-bg)] p-3 text-sm text-[var(--color-state-danger-text)]"
          data-testid="trace-refusal"
        >
          Refusal emitted.{" "}
          {result.normative_detail ? (
            <span className="font-mono">{result.normative_detail}</span>
          ) : (
            "No detail recorded."
          )}
        </section>
      ) : null}

      <TraceSurfaces result={result} />

      <section
        className="rounded-md border border-[var(--color-border-subtle)] bg-[var(--color-surface-raised)] p-3"
        data-testid="trace-grounding"
      >
        <h3 className="m-0 mb-2 text-sm font-semibold text-[var(--color-text-primary)]">
          Grounding
        </h3>
        <dl className="m-0 grid grid-cols-[max-content_1fr] gap-x-3 gap-y-1 text-xs">
          <dt className="text-[var(--color-text-secondary)]">grounding_source</dt>
          <dd className="m-0 text-[var(--color-text-primary)]">
            {result.grounding_source}
          </dd>
          <dt className="text-[var(--color-text-secondary)]">epistemic_state</dt>
          <dd className="m-0 text-[var(--color-text-primary)]">
            {result.epistemic_state}
          </dd>
          <dt className="text-[var(--color-text-secondary)]">normative_clearance</dt>
          <dd className="m-0 text-[var(--color-text-primary)]">
            {result.normative_clearance}
          </dd>
        </dl>
      </section>

      <section
        className="rounded-md border border-[var(--color-border-subtle)] bg-[var(--color-surface-raised)] p-3"
        data-testid="trace-verdicts"
      >
        <h3 className="m-0 mb-2 text-sm font-semibold text-[var(--color-text-primary)]">
          Verdicts
        </h3>
        <dl className="m-0 grid gap-1">
          <VerdictRow label="identity" verdict={result.identity_verdict} />
          <VerdictRow label="safety" verdict={result.safety_verdict} />
          <VerdictRow label="ethics" verdict={result.ethics_verdict} />
        </dl>
      </section>

      {result.proposal_candidates.length > 0 ? (
        <section
          className="rounded-md border border-[var(--color-border-subtle)] bg-[var(--color-surface-raised)] p-3"
          data-testid="trace-proposals"
        >
          <h3 className="m-0 mb-2 text-sm font-semibold text-[var(--color-text-primary)]">
            Proposal candidates
          </h3>
          <ul className="m-0 list-none space-y-1 p-0 text-xs">
            {result.proposal_candidates.map((c) => (
              <li
                key={c.candidate_id}
                className="flex items-center justify-between gap-2"
              >
                <span className="font-mono text-[var(--color-text-primary)]">
                  {c.candidate_id}
                </span>
                <Link
                  to={`/proposals?proposal_id=${encodeURIComponent(c.candidate_id)}`}
                  className="text-[var(--color-text-secondary)] underline underline-offset-2 hover:text-[var(--color-text-primary)]"
                  data-testid={`trace-proposal-link-${c.candidate_id}`}
                >
                  /proposals
                </Link>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <section
        className="rounded-md border border-[var(--color-border-subtle)] bg-[var(--color-surface-raised)] p-3"
        data-testid="trace-hash"
      >
        <h3 className="m-0 mb-2 text-sm font-semibold text-[var(--color-text-primary)]">
          Trace hash
        </h3>
        {result.trace_hash ? (
          <TraceHashBadge value={result.trace_hash} />
        ) : (
          <p className="m-0 text-xs text-[var(--color-text-secondary)]">
            No trace hash recorded.
          </p>
        )}
      </section>
    </article>
  );
}
