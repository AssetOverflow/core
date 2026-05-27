import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { WorkbenchApiError, type ProposalStateFilter } from "../../api/client";
import { useProposalDetail, useProposals } from "../../api/queries";
import { Button } from "../../design/components/primitives/Button";
import { EmptyState } from "../../design/components/states/EmptyState";
import { ErrorState } from "../../design/components/states/ErrorState";
import { LoadingState } from "../../design/components/states/LoadingState";
import { ProposalChainViewer } from "./ProposalChainViewer";
import { ProposalProvenanceViewer } from "./ProposalProvenanceViewer";
import { ProposalSummaryCard } from "./ProposalSummaryCard";
import { ProposalTable } from "./ProposalTable";
import { ReplayEvidenceCard } from "./ReplayEvidenceCard";

const filters: ProposalStateFilter[] = ["pending", "accepted", "rejected", "all"];

function isProposalFilter(value: string | null): value is ProposalStateFilter {
  return value === "pending" || value === "accepted" || value === "rejected" || value === "withdrawn" || value === "unknown" || value === "all";
}

function errorMessage(error: unknown) {
  return error instanceof WorkbenchApiError ? error.message : "Proposal API request failed.";
}

export function ProposalsRoute() {
  const [searchParams, setSearchParams] = useSearchParams();
  const selectedFromUrl = searchParams.get("proposal_id");
  const filterFromUrl = searchParams.get("state");
  const [filter, setFilter] = useState<ProposalStateFilter>(
    isProposalFilter(filterFromUrl) ? filterFromUrl : "pending",
  );
  const proposalsQuery = useProposals(filter);
  const selectedProposalId = selectedFromUrl ?? null;
  const detailQuery = useProposalDetail(selectedProposalId ?? "");

  useEffect(() => {
    const urlFilter = searchParams.get("state");
    if (isProposalFilter(urlFilter) && urlFilter !== filter) {
      setFilter(urlFilter);
    }
  }, [filter, searchParams]);

  const proposals = useMemo(() => proposalsQuery.data ?? [], [proposalsQuery.data]);

  function updateRoute(next: { proposalId?: string | null; state?: ProposalStateFilter }) {
    const params = new URLSearchParams(searchParams);
    const nextState = next.state ?? filter;
    params.set("state", nextState);
    if (next.proposalId === null) {
      params.delete("proposal_id");
    } else if (next.proposalId) {
      params.set("proposal_id", next.proposalId);
    }
    setSearchParams(params, { replace: false });
  }

  function changeFilter(nextFilter: ProposalStateFilter) {
    setFilter(nextFilter);
    updateRoute({ state: nextFilter, proposalId: null });
  }

  function selectProposal(proposalId: string) {
    updateRoute({ proposalId });
  }

  if (proposalsQuery.isLoading) {
    return <LoadingState label="Loading proposal queue..." />;
  }

  if (proposalsQuery.isError) {
    return (
      <ErrorState
        whatFailed={errorMessage(proposalsQuery.error)}
        mutationStatus="No proposal mutation occurred."
        reproducer="curl /proposals"
        retrySafety="Retry: safe"
      />
    );
  }

  return (
    <div className="grid h-full min-h-0 gap-4 xl:grid-cols-[minmax(34rem,0.95fr)_minmax(32rem,1.05fr)]">
      <section className="grid min-h-0 content-start gap-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h1 className="m-0 text-base font-semibold text-[var(--color-text-primary)]">Proposal Queue</h1>
          <div className="flex flex-wrap gap-2" role="group" aria-label="Proposal state filter">
            {filters.map((state) => (
              <Button
                aria-pressed={filter === state}
                key={state}
                onClick={() => changeFilter(state)}
                type="button"
                variant={filter === state ? "primary" : "quiet"}
              >
                {state}
              </Button>
            ))}
          </div>
        </div>

        {proposals.length === 0 ? (
          <EmptyState
            statement="No proposals match this queue view."
            nextAction={{ kind: "cli", command: "core teaching proposals --state pending" }}
          />
        ) : (
          <ProposalTable
            proposals={proposals}
            selectedProposalId={selectedProposalId}
            onSelect={selectProposal}
          />
        )}
      </section>

      <section className="min-h-0 overflow-y-auto">
        {!selectedProposalId ? (
          <EmptyState
            statement="Select a proposal to inspect replay evidence, chain records, and provenance."
            nextAction={{ kind: "cli", command: "core teaching hitl-queue list" }}
          />
        ) : detailQuery.isLoading ? (
          <LoadingState label="Loading proposal detail..." />
        ) : detailQuery.isError ? (
          <ErrorState
            whatFailed={errorMessage(detailQuery.error)}
            mutationStatus="No proposal mutation occurred."
            reproducer={`curl /proposals/${selectedProposalId}`}
            retrySafety="Retry: safe"
          />
        ) : detailQuery.data ? (
          <div className="grid gap-4">
            <ProposalSummaryCard proposal={detailQuery.data} />
            <ReplayEvidenceCard proposal={detailQuery.data} />
            <ProposalChainViewer proposal={detailQuery.data} />
            <ProposalProvenanceViewer proposal={detailQuery.data} />
          </div>
        ) : null}
      </section>
    </div>
  );
}
