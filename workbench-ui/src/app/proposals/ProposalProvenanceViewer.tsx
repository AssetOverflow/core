import { StableJsonViewer } from "../../design/components/StableJsonViewer";
import { TruncatedCell } from "../../design/components/TruncatedCell";
import type { ProposalDetail } from "../../types/api";
import { jsonSource } from "./proposalView";
import { SuggestedCLIBox } from "./SuggestedCLIBox";

export function ProposalProvenanceViewer({ proposal }: { proposal: ProposalDetail }) {
  return (
    <section className="grid gap-3">
      <div className="rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-surface-raised)] p-4">
        <h3 className="m-0 text-sm font-semibold text-[var(--color-text-primary)]">Source provenance</h3>
        <dl className="mt-3 grid gap-2 text-xs">
          <div className="grid grid-cols-[8rem_1fr] gap-3">
            <dt className="text-[var(--color-text-muted)]">source_kind</dt>
            <dd className="m-0 font-mono text-[var(--color-text-primary)]">{proposal.source_kind}</dd>
          </div>
          <div className="grid grid-cols-[8rem_1fr] gap-3">
            <dt className="text-[var(--color-text-muted)]">artifacts</dt>
            <dd className="m-0 text-[var(--color-text-primary)]">{proposal.artifact_refs.length}</dd>
          </div>
          <div className="grid grid-cols-[8rem_1fr] gap-3">
            <dt className="text-[var(--color-text-muted)]">evidence</dt>
            <dd className="m-0 text-[var(--color-text-primary)]">{proposal.evidence.length}</dd>
          </div>
        </dl>
        {proposal.artifact_refs.length > 0 ? (
          <ul className="mt-3 grid gap-2 p-0">
            {proposal.artifact_refs.map((artifact) => (
              <li
                className="grid gap-1 rounded-md border border-[var(--color-border-subtle)] bg-[var(--color-surface-inset)] p-2 text-xs"
                key={artifact.artifact_id}
              >
                <span className="font-mono text-[var(--color-text-primary)]">{artifact.artifact_id}</span>
                <TruncatedCell
                  value={artifact.path}
                  label="artifact path"
                  className="text-[var(--color-text-secondary)]"
                />
              </li>
            ))}
          </ul>
        ) : null}
      </div>
      <StableJsonViewer source={jsonSource({ source: proposal.source, evidence: proposal.evidence })} />
      <SuggestedCLIBox proposalId={proposal.proposal_id} />
    </section>
  );
}
