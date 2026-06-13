import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { AlertTriangle } from "lucide-react";
import { useEvidenceSubject } from "../evidenceContext";
import { WorkbenchApiError, type ProposalStateFilter } from "../../api/client";
import { useProposalDetail, useProposals, useMathProposals, useMathProposalDetail } from "../../api/queries";
import type { ProposalSummary, MathProposalDetail, ProposalState, DownstreamEffect, MathReasoningStep } from "../../types/api";
import { Button } from "../../design/components/primitives/Button";
import { EmptyState } from "../../design/components/states/EmptyState";
import { SearchInput } from "../../design/components/SearchInput/SearchInput";
import { useListNavigation } from "../../design/hooks/useListNavigation";
import { ErrorState } from "../../design/components/states/ErrorState";
import { LoadingState } from "../../design/components/states/LoadingState";
import { ProposalChainViewer } from "./ProposalChainViewer";
import { ProposalProvenanceViewer } from "./ProposalProvenanceViewer";
import { ProposalSummaryCard } from "./ProposalSummaryCard";
import { ProposalTable } from "./ProposalTable";
import { Panel } from "../../design/components/Panel/Panel";
import { ReplayEvidenceCard } from "./ReplayEvidenceCard";
import { RatificationCommandPanel } from "./RatificationCommandPanel";
import { LeewayEvidenceCard } from "../LeewayEvidenceCard";

const filters: ProposalStateFilter[] = ["pending", "accepted", "rejected", "all"];

function isProposalFilter(value: string | null): value is ProposalStateFilter {
  return (
    value === "pending" ||
    value === "accepted" ||
    value === "rejected" ||
    value === "withdrawn" ||
    value === "unknown" ||
    value === "all"
  );
}

function errorMessage(error: unknown) {
  return error instanceof WorkbenchApiError ? error.message : "Proposal API request failed.";
}

export function ProposalsRoute() {
  const { proposalId: selectedFromUrl } = useParams();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { setSubject } = useEvidenceSubject();
  const filterFromUrl = searchParams.get("state");
  const domainFromUrl = searchParams.get("domain");

  const [domain, setDomain] = useState<"math" | "cognition">(
    domainFromUrl === "math" ? "math" : "cognition"
  );
  
  const [filter, setFilter] = useState<ProposalStateFilter>(
    isProposalFilter(filterFromUrl) ? filterFromUrl : "pending",
  );
  const [search, setSearch] = useState("");


  // Queries
  const mathProposalsQuery = useMathProposals();
  const cognitionProposalsQuery = useProposals(filter);

  const selectedProposalId = selectedFromUrl ?? null;

  const mathDetailQuery = useMathProposalDetail(
    domain === "math" ? (selectedProposalId ?? "") : ""
  );
  const cognitionDetailQuery = useProposalDetail(
    domain === "cognition" ? (selectedProposalId ?? "") : ""
  );

  // Synchronize state from URL
  useEffect(() => {
    const urlFilter = searchParams.get("state");
    if (isProposalFilter(urlFilter) && urlFilter !== filter) {
      setFilter(urlFilter);
    }
  }, [filter, searchParams]);

  useEffect(() => {
    const urlDomain = searchParams.get("domain");
    if ((urlDomain === "math" || urlDomain === "cognition") && urlDomain !== domain) {
      setDomain(urlDomain as "math" | "cognition");
    }
  }, [domain, searchParams]);

  // Load appropriate proposals list
  const rawProposals = useMemo(() => {
    if (domain === "math") {
      return mathProposalsQuery.data ?? [];
    } else {
      return cognitionProposalsQuery.data ?? [];
    }
  }, [domain, mathProposalsQuery.data, cognitionProposalsQuery.data]);

  // Map to unified ProposalSummary structure
  const allProposals: ProposalSummary[] = useMemo(() => {
    if (domain === "math") {
      return (rawProposals as any[]).map((mp) => ({
        proposal_id: mp.proposal_id,
        state: "pending" as ProposalState,
        source_kind: `math / ${mp.proposed_change_kind}`,
        replay_equivalent: true,
        created_at: null,
        downstream_effect: "unknown" as DownstreamEffect,
      }));
    } else {
      return (rawProposals as ProposalSummary[]) ?? [];
    }
  }, [domain, rawProposals]);

  // Client-side narrowing via SearchInput ("/" focuses it while mounted).
  const proposals: ProposalSummary[] = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return allProposals;
    return allProposals.filter(
      (p) =>
        p.proposal_id.toLowerCase().includes(q) ||
        p.source_kind.toLowerCase().includes(q),
    );
  }, [allProposals, search]);

  // Shared list navigation (window scope — the queue IS the route's primary
  // surface). Replaces the bespoke window keydown listener this route
  // carried since W-029; one pattern app-wide (Wave R brief R0d).
  const { focusedIndex, setFocusedIndex } = useListNavigation({
    itemCount: proposals.length,
    scope: "window",
    onActivate: (index) => {
      if (proposals[index]) selectProposal(proposals[index].proposal_id);
    },
    onEscape: () => updateRoute({ proposalId: null }),
  });

  const focusedProposalId = useMemo(() => {
    if (proposals.length > 0 && focusedIndex >= 0 && focusedIndex < proposals.length) {
      return proposals[focusedIndex].proposal_id;
    }
    return null;
  }, [proposals, focusedIndex]);

  // Reset focus when domain or filter changes
  useEffect(() => {
    setFocusedIndex(0);
  }, [domain, filter]);

  // Publish the selected proposal as the evidence subject: identity
  // immediately, detail once the query resolves. Math proposal subjects carry
  // domain="math" so copied evidence links round-trip to the same corridor.
  useEffect(() => {
    if (!selectedProposalId) return;
    setSubject({
      kind: "proposal",
      proposalId: selectedProposalId,
      domain,
      data: domain === "math" ? mathDetailQuery.data : cognitionDetailQuery.data,
    });
  }, [selectedProposalId, domain, mathDetailQuery.data, cognitionDetailQuery.data, setSubject]);

  function updateRoute(next: { proposalId?: string | null; state?: ProposalStateFilter; domain?: "math" | "cognition" }) {
    const params = new URLSearchParams(searchParams);
    const nextDomain = next.domain ?? domain;
    const nextState = next.state ?? filter;

    if (nextDomain === "math") {
      params.set("domain", "math");
    } else {
      params.delete("domain");
    }
    params.set("state", nextState);

    const nextProposalId =
      next.proposalId === null ? null : (next.proposalId ?? selectedProposalId);
    const path = nextProposalId
      ? `/proposals/${encodeURIComponent(nextProposalId)}`
      : "/proposals";
    const search = params.toString();
    // Selection churn must not pollute history: replace, never push.
    navigate(search ? `${path}?${search}` : path, { replace: true });
  }

  function changeFilter(nextFilter: ProposalStateFilter) {
    setFilter(nextFilter);
    updateRoute({ state: nextFilter, proposalId: null });
  }

  function changeDomain(nextDomain: "math" | "cognition") {
    setDomain(nextDomain);
    updateRoute({ domain: nextDomain, proposalId: null });
  }

  function selectProposal(proposalId: string) {
    const index = proposals.findIndex((p) => p.proposal_id === proposalId);
    if (index !== -1) {
      setFocusedIndex(index);
    }
    updateRoute({ proposalId });
  }

  // Auto-advance focus on success
  const autoAdvance = () => {
    let nextIndex = -1;
    for (let i = focusedIndex + 1; i < proposals.length; i++) {
      if (proposals[i].state === "pending" || domain === "math") {
        nextIndex = i;
        break;
      }
    }
    if (nextIndex === -1) {
      for (let i = 0; i < focusedIndex; i++) {
        if (proposals[i].state === "pending" || domain === "math") {
          nextIndex = i;
          break;
        }
      }
    }

    if (nextIndex !== -1) {
      setFocusedIndex(nextIndex);
      selectProposal(proposals[nextIndex].proposal_id);
    } else {
      updateRoute({ proposalId: null });
    }
  };

  const isLoading = domain === "math" ? mathProposalsQuery.isLoading : cognitionProposalsQuery.isLoading;
  const isError = domain === "math" ? mathProposalsQuery.isError : cognitionProposalsQuery.isError;
  const error = domain === "math" ? mathProposalsQuery.error : cognitionProposalsQuery.error;

  if (isLoading) {
    return <LoadingState label="Loading proposal queue..." />;
  }

  if (isError) {
    return (
      <ErrorState
        whatFailed={errorMessage(error)}
        mutationStatus="No proposal mutation occurred."
        reproducer={`curl /${domain === "math" ? "math-" : ""}proposals`}
        retrySafety="Retry: safe"
      />
    );
  }

  const detailQuery = domain === "math" ? mathDetailQuery : cognitionDetailQuery;

  return (
    <div className="grid h-full min-h-0 gap-4 xl:grid-cols-[minmax(34rem,0.95fr)_minmax(32rem,1.05fr)]">
      <Panel
        title="Proposal Queue"
        toolbar={
          <div className="flex bg-[var(--color-surface-inset)] p-0.5 rounded border border-[var(--color-border-subtle)]">
              <button
                onClick={() => changeDomain("math")}
                className={`px-3 py-1 rounded text-xs font-semibold transition-all ${
                  domain === "math"
                    ? "bg-[var(--color-surface-raised)] text-[var(--color-text-primary)] shadow-sm"
                    : "text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]"
                }`}
              >
                Math Corridor
              </button>
              <button
                onClick={() => changeDomain("cognition")}
                className={`px-3 py-1 rounded text-xs font-semibold transition-all ${
                  domain === "cognition"
                    ? "bg-[var(--color-surface-raised)] text-[var(--color-text-primary)] shadow-sm"
                    : "text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]"
                }`}
              >
                Cognition Queue
              </button>
          </div>
        }
      >
        <div className="grid content-start gap-3">
          {domain === "cognition" && (
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
          )}

        <SearchInput
          placeholder="Filter by proposal id or source kind"
          value={search}
          onChange={setSearch}
        />

        {proposals.length === 0 ? (
          <EmptyState
            statement={domain === "math" ? "No math proposals match this queue view." : "No proposals match this queue view."}

            nextAction={{
              kind: "cli",
              command: domain === "math" ? "core eval gsm8k_math" : "core teaching proposals --state pending",
            }}
          />
        ) : (
          <ProposalTable
            proposals={proposals}
            selectedProposalId={selectedProposalId}
            focusedProposalId={focusedProposalId}
            onSelect={selectProposal}
          />
        )}
        </div>
      </Panel>

      <section className="min-h-0 overflow-y-auto pr-1">
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
            reproducer={`curl /${domain === "math" ? "math-" : ""}proposals/${selectedProposalId}`}
            retrySafety="Retry: safe"
          />
        ) : detailQuery.data ? (
          domain === "math" ? (
            <MathProposalDetailView
              proposal={detailQuery.data as MathProposalDetail}
              state="pending"
              replayEquivalent={true}
              onSuccess={autoAdvance}
              onDefer={autoAdvance}
            />
          ) : (
            <div className="grid gap-4">
              <ProposalSummaryCard proposal={detailQuery.data as any} />
              <ReplayEvidenceCard proposal={detailQuery.data as any} />
              <ProposalChainViewer proposal={detailQuery.data as any} />
              <ProposalProvenanceViewer proposal={detailQuery.data as any} />
            </div>
          )
        ) : null}
      </section>
    </div>
  );
}

interface MathProposalDetailViewProps {
  proposal: MathProposalDetail;
  state: string;
  replayEquivalent: boolean | null;
  onSuccess: () => void;
  onDefer: () => void;
}

function MathProposalDetailView({
  proposal,
  state,
  replayEquivalent,
  onSuccess,
  onDefer,
}: MathProposalDetailViewProps) {
  const steps = proposal.reasoning_trace_steps || [];
  const hashes = proposal.evidence_hashes || [];

  return (
    <div className="grid gap-4">
      {/* Summary Card */}
      <section className="rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-surface-raised)] p-4">
        <div className="flex flex-wrap items-center gap-2">
          <h2 className="m-0 font-mono text-sm font-semibold text-[var(--color-text-primary)]">
            {proposal.proposal_id}
          </h2>
          <span className="text-xs font-semibold px-2 py-0.5 rounded bg-[var(--color-state-neutral-bg)] border border-[var(--color-state-neutral-border)] text-[var(--color-state-neutral-text)]">
            {proposal.shape_category}
          </span>
          <span className="text-xs font-semibold px-2 py-0.5 rounded bg-[var(--color-state-success-bg)] border border-[var(--color-state-success-border)] text-[var(--color-state-success-text)] font-mono">
            math_contemplation
          </span>
        </div>
        <p className="mt-3 text-sm text-[var(--color-text-secondary)]">
          Proposed change: <strong className="text-[var(--color-text-primary)] font-mono">{proposal.proposed_change_kind}</strong>
        </p>
        <dl className="mt-4 grid grid-cols-2 gap-3 text-xs">
          <div>
            <dt className="text-[var(--color-text-muted)]">Structural Commonality</dt>
            <dd className="m-0 text-[var(--color-text-primary)] font-medium mt-0.5">{proposal.structural_commonality}</dd>
          </div>
          <div>
            <dt className="text-[var(--color-text-muted)]">Replay Equivalence Hash</dt>
            <dd className="m-0 text-[var(--color-text-primary)] font-mono truncate mt-0.5" title={proposal.replay_equivalence_hash}>
              {proposal.replay_equivalence_hash}
            </dd>
          </div>
        </dl>
      </section>

      <LeewayEvidenceCard evidence={proposal.leeway_evidence} />

      {/* Wrong Zero Assertion Card */}
      <section className="rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-surface-raised)] p-4">
        <h3 className="m-0 text-sm font-semibold text-[var(--color-text-primary)] flex items-center gap-2">
          <AlertTriangle size={15} className="text-[var(--color-state-warning-text)]" />
          Wrong Zero Assertion
        </h3>
        <p className="mt-2.5 text-xs font-mono text-[var(--color-state-warning-text)] bg-[var(--color-surface-inset)] p-3 rounded border border-[var(--color-border-subtle)] whitespace-pre-wrap leading-relaxed">
          {proposal.wrong_zero_assertion}
        </p>
      </section>

      {/* Proposed Change Payload Card */}
      <section className="rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-surface-raised)] p-4">
        <h3 className="m-0 text-sm font-semibold text-[var(--color-text-primary)] mb-3">Proposed Change Payload</h3>
        <pre className="p-3 bg-[var(--color-surface-inset)] rounded border border-[var(--color-border-subtle)] font-mono text-xs text-[var(--color-text-primary)] overflow-x-auto">
          {JSON.stringify(proposal.proposed_change_payload, null, 2)}
        </pre>
      </section>

      {/* Reasoning Trace Steps */}
      <section className="rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-surface-raised)] p-4">
        <h3 className="m-0 text-sm font-semibold text-[var(--color-text-primary)] mb-3">
          Reasoning Steps ({steps.length})
        </h3>
        <div className="grid gap-3 max-h-[30rem] overflow-y-auto pr-1">
          {steps.map((step: MathReasoningStep) => (
            <div key={step.step_index} className="p-3 bg-[var(--color-surface-inset)] rounded border border-[var(--color-border-subtle)] text-xs">
              <div className="flex items-center justify-between mb-1.5 font-medium text-[var(--color-text-primary)]">
                <span>Step {step.step_index}: <span className="text-[var(--color-link)] font-mono">{step.step_kind}</span></span>
                <span className="text-[var(--color-text-muted)] font-mono">[{step.input_pointers?.join(", ")}]</span>
              </div>
              <p className="m-0 text-[var(--color-text-primary)] font-semibold mb-1">
                {step.claim}
              </p>
              <p className="m-0 text-[var(--color-text-secondary)] italic">
                {step.justification}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* Evidence Hashes */}
      <section className="rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-surface-raised)] p-4">
        <h3 className="m-0 text-sm font-semibold text-[var(--color-text-primary)] mb-3">Evidence Hashes</h3>
        <div className="grid gap-1.5">
          {hashes.map((hash: string, i: number) => (
            <div key={i} className="flex items-center gap-2">
              <span className="text-xs text-[var(--color-text-muted)] font-mono">#{i + 1}</span>
              <code className="bg-[var(--color-surface-inset)] px-2 py-1 rounded font-mono text-xs text-[var(--color-text-primary)] truncate flex-1">
                {hash}
              </code>
            </div>
          ))}
        </div>
      </section>

      {/* Ratification Command Panel */}
      <RatificationCommandPanel
        proposal={proposal}
        state={state}
        replayEquivalent={replayEquivalent}
        onSuccess={onSuccess}
        onDefer={onDefer}
      />
    </div>
  );
}
