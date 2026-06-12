import { useEffect, useMemo, useState } from "react";
import { Eye } from "lucide-react";
import { useNavigate, useParams } from "react-router-dom";
import { WorkbenchApiError } from "../../api/client";
import { useTraceTurn, useTraceTurns } from "../../api/queries";
import { DigestBadge } from "../../design/components/DigestBadge/DigestBadge";
import { MetadataTable } from "../../design/components/MetadataTable/MetadataTable";
import { Panel } from "../../design/components/Panel/Panel";
import { SearchInput } from "../../design/components/SearchInput/SearchInput";
import { SplitPane } from "../../design/components/SplitPane/SplitPane";
import { StableJsonViewer } from "../../design/components/StableJsonViewer";
import { TabBar, type Tab } from "../../design/components/TabBar/TabBar";
import { Timestamp } from "../../design/components/Timestamp/Timestamp";
import { VirtualizedList } from "../../design/components/VirtualizedList/VirtualizedList";
import {
  EpistemicStateBadge,
  GroundingSourceBadge,
  NormativeClearanceBadge,
  type EpistemicState,
  type GroundingSource,
  type NormativeClearance,
} from "../../design/components/badges";
import { Button } from "../../design/components/primitives/Button";
import { EmptyState } from "../../design/components/states/EmptyState";
import { ErrorState } from "../../design/components/states/ErrorState";
import { LoadingState } from "../../design/components/states/LoadingState";
import type { TurnJournalEntry, TurnJournalSummary } from "../../types/api";
import { pushRecentItem } from "../commandRegistry";
import { subjectToUrl } from "../evidenceAddress";
import { useEvidenceSubject } from "../evidenceContext";

const TRACE_TABS: readonly Tab[] = [
  { id: "surfaces", label: "Surfaces" },
  { id: "grounding", label: "Grounding" },
  { id: "verdicts", label: "Verdicts" },
  { id: "metadata", label: "Metadata" },
  { id: "raw", label: "Raw" },
];

function parseTurnId(raw: string | undefined): number | null {
  if (!raw || !/^\d+$/.test(raw)) return null;
  const value = Number(raw);
  return Number.isSafeInteger(value) ? value : null;
}

function errorMessage(error: unknown) {
  return error instanceof WorkbenchApiError ? error.message : "Trace journal request failed.";
}

function digestPayload(value: string | null | undefined): string | null {
  if (!value) return null;
  return value.replace(/^sha256:/, "");
}

function firstLine(value: string): string {
  return value.split(/\r?\n/, 1)[0] || "";
}

function surfaceText(value: string | null): string {
  return value && value.trim() ? value : "Not recorded.";
}

function proposalCandidateLabel(candidate: Record<string, unknown>): string {
  const id = candidate.candidate_id;
  const source = candidate.source_kind;
  if (typeof id === "string" && typeof source === "string") return `${id} (${source})`;
  if (typeof id === "string") return id;
  return JSON.stringify(candidate);
}

function asVerdict(value: unknown): { outcome: string; runtime_detail: string } | null {
  if (!value || typeof value !== "object") return null;
  const record = value as Record<string, unknown>;
  return {
    outcome: typeof record.outcome === "string" ? record.outcome : "unassessable",
    runtime_detail: typeof record.runtime_detail === "string" ? record.runtime_detail : "",
  };
}

function SurfaceCard({
  label,
  value,
}: {
  label: string;
  value: string | null;
}) {
  return (
    <section className="rounded-md border border-[var(--color-border-subtle)] bg-[var(--color-surface-inset)] p-3">
      <h3 className="m-0 text-xs font-semibold text-[var(--color-text-secondary)]">
        {label}
      </h3>
      <pre className="mt-2 max-h-52 overflow-auto whitespace-pre-wrap break-words font-mono text-xs leading-5 text-[var(--color-text-primary)]">
        {surfaceText(value)}
      </pre>
    </section>
  );
}

function TraceRow({
  turn,
  selected,
  focused,
  onSelect,
}: {
  turn: TurnJournalSummary;
  selected: boolean;
  focused: boolean;
  onSelect: () => void;
}) {
  const digest = digestPayload(turn.trace_hash);
  return (
    <div
      role="button"
      tabIndex={-1}
      aria-current={selected ? "true" : undefined}
      onClick={onSelect}
      className={`grid w-full grid-cols-[minmax(0,1fr)_auto] items-start gap-3 border-b border-[var(--color-border-subtle)] px-3 py-2 text-left transition-colors hover:bg-[var(--color-surface-inset)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-inset focus-visible:outline-[var(--color-focus-ring)] ${
        selected ? "bg-[var(--color-selected-bg)]" : ""
      } ${
        selected
          ? "border-l-2 border-l-[var(--color-selected-border)] pl-[10px]"
          : focused
            ? "border-l-2 border-l-[var(--color-focus-ring)] pl-[10px]"
            : "border-l-2 border-l-transparent pl-[10px]"
      }`}
    >
      <span className="min-w-0">
        <span className="block text-xs text-[var(--color-text-secondary)]">
          <Timestamp iso={turn.timestamp} format="relative" />
        </span>
        <span className="mt-1 block truncate text-sm text-[var(--color-text-primary)]">
          {firstLine(turn.prompt_excerpt) || `Turn #${turn.turn_id}`}
        </span>
        <span className="mt-1 block truncate text-xs text-[var(--color-text-muted)]">
          {turn.surface_excerpt}
        </span>
      </span>
      <span className="justify-self-end">
        {digest ? (
          <DigestBadge digest={digest} truncate={12} />
        ) : (
          <span className="font-mono text-xs text-[var(--color-text-muted)]">no hash</span>
        )}
      </span>
    </div>
  );
}

function SurfacesTab({ turn }: { turn: TurnJournalEntry }) {
  return (
    <div className="grid gap-3">
      <SurfaceCard label="User Surface (response)" value={turn.surface} />
      <SurfaceCard label="Articulation Surface (realizer)" value={turn.articulation_surface} />
      <SurfaceCard label="Walk Surface (telemetry/evidence)" value={turn.walk_surface} />
    </div>
  );
}

function GroundingTab({ turn }: { turn: TurnJournalEntry }) {
  return (
    <MetadataTable
      rows={[
        {
          key: "grounding_source",
          value: <GroundingSourceBadge value={turn.grounding_source as GroundingSource} />,
        },
        {
          key: "epistemic_state",
          value: <EpistemicStateBadge value={turn.epistemic_state as EpistemicState} />,
        },
        {
          key: "normative_clearance",
          value: <NormativeClearanceBadge value={turn.normative_clearance as NormativeClearance} />,
        },
      ]}
    />
  );
}

function VerdictsTab({ turn }: { turn: TurnJournalEntry }) {
  const identity = asVerdict(turn.verdicts.identity);
  const safety = asVerdict(turn.verdicts.safety);
  const ethics = asVerdict(turn.verdicts.ethics);
  return (
    <MetadataTable
      rows={[
        { key: "identity", value: identity ? identity.outcome : "not recorded" },
        { key: "identity_detail", value: identity?.runtime_detail || "none" },
        { key: "safety", value: safety ? safety.outcome : "not recorded" },
        { key: "safety_detail", value: safety?.runtime_detail || "none" },
        { key: "ethics", value: ethics ? ethics.outcome : "not recorded" },
        { key: "ethics_detail", value: ethics?.runtime_detail || "none" },
        { key: "refusal_emitted", value: turn.refusal_emitted ? "yes" : "no" },
        { key: "hedge_injected", value: turn.hedge_injected ? "yes" : "no" },
      ]}
    />
  );
}

function MetadataTab({ turn }: { turn: TurnJournalEntry }) {
  const traceDigest = digestPayload(turn.trace_hash);
  const journalDigest = digestPayload(turn.journal_digest);
  return (
    <MetadataTable
      rows={[
        { key: "turn_id", value: String(turn.turn_id), mono: true, copyable: true },
        { key: "timestamp", value: <Timestamp iso={turn.timestamp} /> },
        { key: "turn_cost_ms", value: `${turn.turn_cost_ms}ms`, mono: true },
        { key: "checkpoint_emitted", value: turn.checkpoint_emitted ? "yes" : "no" },
        {
          key: "trace_hash",
          value: traceDigest ? <DigestBadge digest={traceDigest} truncate={12} /> : "not recorded",
        },
        {
          key: "journal_digest",
          value: journalDigest ? <DigestBadge digest={journalDigest} truncate={12} /> : "not recorded",
        },
        {
          key: "proposal_candidates",
          value:
            turn.proposal_candidates.length > 0
              ? turn.proposal_candidates.map(proposalCandidateLabel).join(", ")
              : "none",
        },
      ]}
    />
  );
}

function RawTab({ turn }: { turn: TurnJournalEntry }) {
  const [expanded, setExpanded] = useState(false);
  return expanded ? (
    <StableJsonViewer source={JSON.stringify(turn, null, 2)} />
  ) : (
    <div className="grid justify-items-start gap-2">
      <p className="m-0 text-sm text-[var(--color-text-secondary)]">
        Raw journal JSON is collapsed by default.
      </p>
      <Button type="button" variant="quiet" onClick={() => setExpanded(true)}>
        <Eye size={14} aria-hidden />
        Expand raw JSON
      </Button>
    </div>
  );
}

function TraceDetail({ turn }: { turn: TurnJournalEntry }) {
  const [activeTab, setActiveTab] = useState("surfaces");
  return (
    <Panel
      title={`Turn #${turn.turn_id}`}
      toolbar={
        turn.trace_hash ? (
          <DigestBadge digest={digestPayload(turn.trace_hash) ?? ""} truncate={12} />
        ) : null
      }
    >
      <TabBar tabs={TRACE_TABS} activeTab={activeTab} onTabChange={setActiveTab}>
        {activeTab === "surfaces" ? <SurfacesTab turn={turn} /> : null}
        {activeTab === "grounding" ? <GroundingTab turn={turn} /> : null}
        {activeTab === "verdicts" ? <VerdictsTab turn={turn} /> : null}
        {activeTab === "metadata" ? <MetadataTab turn={turn} /> : null}
        {activeTab === "raw" ? <RawTab turn={turn} /> : null}
      </TabBar>
    </Panel>
  );
}

export function TraceRoute() {
  const { turnId } = useParams();
  const selectedTurnId = parseTurnId(turnId);
  const navigate = useNavigate();
  const { setSubject } = useEvidenceSubject();
  const [search, setSearch] = useState("");

  const turnsQuery = useTraceTurns();
  const turnQuery = useTraceTurn(selectedTurnId);

  const turns = turnsQuery.data ?? [];
  const filteredTurns = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return turns;
    return turns.filter((turn) => {
      const trace = turn.trace_hash?.replace(/^sha256:/, "").toLowerCase() ?? "";
      return (
        turn.prompt_excerpt.toLowerCase().includes(q) ||
        trace.startsWith(q) ||
        trace.includes(q)
      );
    });
  }, [search, turns]);

  useEffect(() => {
    if (selectedTurnId === null) return;
    setSubject({ kind: "turn", turnId: selectedTurnId, data: turnQuery.data });
  }, [selectedTurnId, setSubject, turnQuery.data]);

  function selectTurn(turn: TurnJournalSummary) {
    const subject = { kind: "turn" as const, turnId: turn.turn_id };
    const path = subjectToUrl(subject);
    navigate(path, { replace: true });
    pushRecentItem({ label: `Turn #${turn.turn_id}`, path });
  }

  if (turnsQuery.isLoading) {
    return <LoadingState label="Loading trace..." />;
  }

  if (turnsQuery.isError) {
    return (
      <ErrorState
        whatFailed={errorMessage(turnsQuery.error)}
        mutationStatus="No trace mutation occurred."
        reproducer="curl /trace/turns"
        retrySafety="Retry: safe"
      />
    );
  }

  if (turns.length === 0) {
    return (
      <EmptyState
        statement="No turns recorded yet. Use Chat to create evidence."
        nextAction={{ kind: "cli", command: "core chat" }}
      />
    );
  }

  return (
    <div className="h-full min-h-0">
      <SplitPane direction="horizontal" id="trace" defaultSplit={38} minSize={320}>
        <Panel title="Turn Timeline">
          <div className="grid min-h-0 gap-3">
            <SearchInput
              placeholder="Filter by prompt or trace hash"
              value={search}
              onChange={setSearch}
            />
            {filteredTurns.length === 0 ? (
              <EmptyState
                statement="No turns match this trace filter."
                nextAction={{ kind: "cli", command: "core chat" }}
              />
            ) : (
              <VirtualizedList
                ariaLabel="Trace turns"
                estimateSize={84}
                getKey={(turn) => String(turn.turn_id)}
                height="calc(100vh - 14rem)"
                initialRect={{ width: 480, height: 560 }}
                items={filteredTurns}
                onActivate={(turn) => selectTurn(turn)}
                renderItem={(turn, _index, focused) => (
                  <TraceRow
                    turn={turn}
                    selected={turn.turn_id === selectedTurnId}
                    focused={focused}
                    onSelect={() => selectTurn(turn)}
                  />
                )}
              />
            )}
          </div>
        </Panel>

        <section className="h-full min-h-0 overflow-y-auto pl-3">
          {selectedTurnId === null ? (
            <EmptyState
              statement="Select a turn to inspect surfaces, grounding, verdicts, and metadata."
              nextAction={{ kind: "cli", command: "core chat" }}
            />
          ) : turnQuery.isLoading ? (
            <LoadingState label="Loading trace turn..." />
          ) : turnQuery.isError ? (
            <ErrorState
              whatFailed={errorMessage(turnQuery.error)}
              mutationStatus="No trace mutation occurred."
              reproducer={`curl /trace/${selectedTurnId}`}
              retrySafety="Retry: safe"
            />
          ) : turnQuery.data ? (
            <TraceDetail turn={turnQuery.data} />
          ) : null}
        </section>
      </SplitPane>
    </div>
  );
}
