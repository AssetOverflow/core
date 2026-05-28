import { Link } from "react-router-dom";
import { useProposalDetail } from "../../../api/queries";
import { LoadingState } from "../../../design/components/states/LoadingState";
import { ErrorState } from "../../../design/components/states/ErrorState";
import { EmptyState } from "../../../design/components/states/EmptyState";
import { ReviewStateBadge } from "../../../design/components/badges";
import { ReviewState } from "../../../design/components/badges/types";

const STATE_TO_REVIEW: Record<string, ReviewState> = {
  pending: ReviewState.PENDING,
  accepted: ReviewState.ACCEPTED,
  rejected: ReviewState.REJECTED,
  withdrawn: ReviewState.WITHDRAWN,
};

export function ProposalInspectorView({
  proposalId,
}: {
  proposalId: string;
}) {
  const { data, isLoading, isError, error } = useProposalDetail(proposalId);

  if (isLoading) return <LoadingState label="Loading proposal detail…" />;
  if (isError)
    return (
      <ErrorState
        whatFailed={`Failed to load proposal ${proposalId}`}
        mutationStatus="No changes were made"
        reproducer={`GET /proposals/${proposalId}`}
        retrySafety={error?.message ?? "Safe to retry — read-only operation"}
      />
    );
  if (!data)
    return (
      <EmptyState
        statement="No proposal data."
        nextAction="Select another entity."
      />
    );

  const reviewState = STATE_TO_REVIEW[data.state] ?? ReviewState.PENDING;

  return (
    <div data-testid="inspector-proposal" className="flex flex-col gap-3">
      <header className="flex items-start justify-between gap-2">
        <div>
          <h3 className="m-0 text-sm font-semibold text-[var(--color-text-primary)]">
            Proposal
          </h3>
          <p className="m-0 mt-1 font-mono text-xs text-[var(--color-text-secondary)]">
            {data.proposal_id}
          </p>
        </div>
        <ReviewStateBadge value={reviewState} />
      </header>
      <dl className="grid grid-cols-[max-content_1fr] gap-x-3 gap-y-1 text-xs">
        <dt className="text-[var(--color-text-secondary)]">Source kind</dt>
        <dd className="m-0 text-[var(--color-text-primary)]">
          {data.source_kind}
        </dd>
        <dt className="text-[var(--color-text-secondary)]">Created</dt>
        <dd className="m-0 font-mono tabular-nums text-[var(--color-text-primary)]">
          {data.created_at ?? "—"}
        </dd>
        <dt className="text-[var(--color-text-secondary)]">Replay equivalent</dt>
        <dd className="m-0 text-[var(--color-text-primary)]">
          {data.replay_equivalent === null
            ? "unknown"
            : data.replay_equivalent
              ? "yes"
              : "no"}
        </dd>
        <dt className="text-[var(--color-text-secondary)]">Downstream effect</dt>
        <dd className="m-0 text-[var(--color-text-primary)]">
          {data.downstream_effect}
        </dd>
      </dl>
      <Link
        to={`/proposals?proposal_id=${encodeURIComponent(data.proposal_id)}`}
        className="self-start rounded border border-[var(--color-border-subtle)] px-2 py-1 text-xs text-[var(--color-text-primary)] hover:bg-[var(--color-surface-overlay)]"
        data-testid="inspector-proposal-open-link"
      >
        Open in Proposals →
      </Link>
    </div>
  );
}
