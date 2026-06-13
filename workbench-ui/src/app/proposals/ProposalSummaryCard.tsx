import type { ProposalDetail } from "../../types/api";
import { LeewayEvidenceCard } from "../LeewayEvidenceCard";
import { ProposalReplayBadge } from "./ProposalReplayBadge";
import { ProposalStateBadge } from "./ProposalStateBadge";
import { formatTimestamp, proposalSummaryText } from "./proposalView";

export function ProposalSummaryCard({ proposal }: { proposal: ProposalDetail }) {
  return (
    <section className="rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-surface-raised)] p-4">
      <div className="flex flex-wrap items-center gap-2">
        <h2 className="m-0 font-mono text-sm font-semibold text-[var(--color-text-primary)]">
          {proposal.proposal_id}
        </h2>
        <ProposalStateBadge value={proposal.state} />
        <ProposalReplayBadge value={proposal.replay_equivalent} />
      </div>
      <p className="mt-3 text-sm text-[var(--color-text-secondary)]">
        {proposalSummaryText(proposal)}
      </p>
      <dl className="mt-4 grid grid-cols-2 gap-3 text-xs">
        <div>
          <dt className="text-[var(--color-text-muted)]">Created</dt>
          <dd className="m-0 text-[var(--color-text-primary)]">{formatTimestamp(proposal.created_at)}</dd>
        </div>
        <div>
          <dt className="text-[var(--color-text-muted)]">Downstream effect</dt>
          <dd className="m-0 text-[var(--color-text-primary)]">{proposal.downstream_effect}</dd>
        </div>
      </dl>
      <div className="mt-4">
        <LeewayEvidenceCard evidence={proposal.leeway_evidence} />
      </div>
    </section>
  );
}
