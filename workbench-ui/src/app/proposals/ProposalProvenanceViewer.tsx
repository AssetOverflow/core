import { Link } from "react-router-dom";
import { StableJsonViewer } from "../../design/components/StableJsonViewer";
import type { ProposalDetail } from "../../types/api";
import { jsonSource } from "./proposalView";
import { SuggestedCLIBox } from "./SuggestedCLIBox";

function replayLinkForProposal(proposal: ProposalDetail): string | null {
  const primaryArtifact = proposal.artifact_refs[0];
  if (primaryArtifact) {
    return `/replay?artifactId=${encodeURIComponent(primaryArtifact.artifact_id)}`;
  }
  return null;
}

export function ProposalProvenanceViewer({ proposal }: { proposal: ProposalDetail }) {
  const replayLink = replayLinkForProposal(proposal);

  return (
    <section className="grid gap-3">
      <div className="rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-surface-raised)] p-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h3 className="m-0 text-sm font-semibold text-[var(--color-text-primary)]">Source provenance</h3>
          {replayLink ? (
            <Link
              to={replayLink}
              className="text-xs text-[var(--color-text-accent)] underline-offset-2 hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--color-focus-ring)]"
            >
              View replay →
            </Link>
          ) : (
            <span className="text-xs text-[var(--color-text-muted)]">
              {/* TODO: link to /artifacts/<id> route when Phase 2 ships */}
              No replay artifact available
            </span>
          )}
        </div>
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
                <div className="flex items-center justify-between gap-2">
                  <span className="font-mono text-[var(--color-text-primary)]">{artifact.artifact_id}</span>
                  <Link
                    to={`/replay?artifactId=${encodeURIComponent(artifact.artifact_id)}`}
                    className="shrink-0 text-xs text-[var(--color-text-accent)] underline-offset-2 hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--color-focus-ring)]"
                    aria-label={`View replay for artifact ${artifact.artifact_id}`}
                  >
                    replay
                  </Link>
                </div>
                <span className="truncate text-[var(--color-text-secondary)]">{artifact.path}</span>
              </li>
            ))}
          </ul>
        ) : null}
      </div>
      <StableJsonViewer source={jsonSource({ source: proposal.source, evidence: proposal.evidence })} />
      <SuggestedCLIBox proposal={proposal} />
    </section>
  );
}
