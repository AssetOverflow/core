import { useMemo, useState } from "react";
import { EmptyState } from "../../design/components/states/EmptyState";
import type { ProposalSummary } from "../../types/api";
import { ProposalReplayBadge } from "./ProposalReplayBadge";
import { ProposalStateBadge } from "./ProposalStateBadge";
import { formatTimestamp, provenanceLabel, shortProposalId } from "./proposalView";

const INITIAL_ROWS = 60;
const ROW_INCREMENT = 40;

export function ProposalTable({
  proposals,
  selectedProposalId,
  focusedProposalId,
  onSelect,
}: {
  proposals: ProposalSummary[];
  selectedProposalId: string | null;
  focusedProposalId?: string | null;
  onSelect: (proposalId: string) => void;
}) {
  const [visibleCount, setVisibleCount] = useState(INITIAL_ROWS);
  const visibleProposals = useMemo(
    () => proposals.slice(0, visibleCount),
    [proposals, visibleCount],
  );

  if (proposals.length === 0) {
    return (
      <EmptyState
        statement="No proposals match this queue view."
        nextAction={{ kind: "cli", command: "core teaching proposals --state pending" }}
      />
    );
  }

  return (
    <section className="overflow-hidden rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-surface-raised)]">
      <div className="grid grid-cols-[minmax(7rem,1fr)_auto_auto_minmax(7rem,1fr)_minmax(9rem,1fr)] gap-3 border-b border-[var(--color-border-subtle)] px-3 py-2 text-xs font-medium uppercase tracking-normal text-[var(--color-text-muted)]">
        <span>proposal_id</span>
        <span>state</span>
        <span>replay</span>
        <span>source</span>
        <span>created</span>
      </div>
      <div className="max-h-[calc(100vh-17rem)] overflow-y-auto">
        {visibleProposals.map((proposal) => {
          const selected = proposal.proposal_id === selectedProposalId;
          const focused = proposal.proposal_id === focusedProposalId;
          return (
            <div
              aria-current={selected ? "true" : undefined}
              role="button"
              tabIndex={0}
              className={`grid w-full grid-cols-[minmax(7rem,1fr)_auto_auto_minmax(7rem,1fr)_minmax(9rem,1fr)] items-center gap-3 border-b border-[var(--color-border-subtle)] px-3 py-2 text-left text-sm text-[var(--color-text-primary)] hover:bg-[var(--color-surface-inset)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-inset focus-visible:outline-[var(--color-focus-ring)] transition-all ${
                selected ? "bg-[var(--color-surface-inset)]" : ""
              } ${
                focused
                  ? "bg-[var(--color-surface-inset)] border-l-2 border-[var(--color-focus-ring)] pl-[10px]"
                  : "border-l-2 border-transparent pl-[10px]"
              }`}
              key={proposal.proposal_id}
              onClick={() => onSelect(proposal.proposal_id)}

              onKeyDown={(event) => {
                if (event.key === "Enter" || event.key === " ") {
                  event.preventDefault();
                  onSelect(proposal.proposal_id);
                }
              }}
            >
              <span className="font-mono text-xs" title={proposal.proposal_id}>
                {shortProposalId(proposal.proposal_id)}
              </span>
              <ProposalStateBadge value={proposal.state} />
              <ProposalReplayBadge value={proposal.replay_equivalent} />
              <span className="truncate text-[var(--color-text-secondary)]">
                {provenanceLabel(proposal)}
              </span>
              <span className="text-xs text-[var(--color-text-secondary)]">
                {formatTimestamp(proposal.created_at)}
              </span>
            </div>
          );
        })}
        {visibleCount < proposals.length ? (
          <button
            className="w-full px-3 py-2 text-sm text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-inset)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-inset focus-visible:outline-[var(--color-focus-ring)]"
            onClick={() => setVisibleCount((count) => count + ROW_INCREMENT)}
            type="button"
          >
            Load more proposals
          </button>
        ) : null}
      </div>
    </section>
  );
}
