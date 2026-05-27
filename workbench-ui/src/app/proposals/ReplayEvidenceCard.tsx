import { TraceHashBadge } from "../../design/components/badges";
import { StableJsonViewer } from "../../design/components/StableJsonViewer";
import type { ProposalDetail } from "../../types/api";
import { digestField, divergenceSummary, jsonSource } from "./proposalView";

export function ReplayEvidenceCard({ proposal }: { proposal: ProposalDetail }) {
  const originalDigest = digestField(proposal.replay_evidence, [
    "original_digest",
    "original_hash",
    "source_digest",
  ]);
  const replayDigest = digestField(proposal.replay_evidence, [
    "replay_digest",
    "replay_hash",
    "result_digest",
  ]);
  const summary = divergenceSummary(proposal.replay_evidence);

  return (
    <section className="grid gap-3">
      <div className="rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-surface-raised)] p-4">
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="m-0 text-sm font-semibold text-[var(--color-text-primary)]">Replay evidence</h3>
          <span className="text-xs text-[var(--color-text-secondary)]">
            {proposal.replay_equivalent === true ? "Equivalent" : proposal.replay_equivalent === false ? "Divergent" : "Unknown"}
          </span>
        </div>
        <dl className="mt-3 grid gap-2 text-xs">
          <div className="flex flex-wrap items-center gap-2">
            <dt className="text-[var(--color-text-muted)]">Original</dt>
            <dd className="m-0">{originalDigest ? <TraceHashBadge value={originalDigest} /> : "unknown"}</dd>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <dt className="text-[var(--color-text-muted)]">Replay</dt>
            <dd className="m-0">{replayDigest ? <TraceHashBadge value={replayDigest} /> : "unknown"}</dd>
          </div>
        </dl>
        {summary ? <p className="mt-3 text-sm text-[var(--color-text-secondary)]">{summary}</p> : null}
      </div>
      <StableJsonViewer source={jsonSource(proposal.replay_evidence)} />
    </section>
  );
}
