import { useEffect, useMemo, useState } from "react";
import { ArrowUpRight, Eye } from "lucide-react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { WorkbenchApiError } from "../../api/client";
import { useRun, useRuns } from "../../api/queries";
import { DigestBadge } from "../../design/components/DigestBadge/DigestBadge";
import { Panel } from "../../design/components/Panel/Panel";
import { SearchInput } from "../../design/components/SearchInput/SearchInput";
import { SplitPane } from "../../design/components/SplitPane/SplitPane";
import { StableJsonViewer } from "../../design/components/StableJsonViewer";
import { TabBar, type Tab } from "../../design/components/TabBar/TabBar";
import { Timestamp } from "../../design/components/Timestamp/Timestamp";
import { VirtualizedList } from "../../design/components/VirtualizedList/VirtualizedList";
import { Button } from "../../design/components/primitives/Button";
import { EmptyState } from "../../design/components/states/EmptyState";
import { ErrorState } from "../../design/components/states/ErrorState";
import { LoadingState } from "../../design/components/states/LoadingState";
import type { RunDetail, RunSummary, RunTurnRef } from "../../types/api";
import { pushRecentItem } from "../commandRegistry";
import { subjectToUrl } from "../evidenceAddress";
import { useEvidenceSubject } from "../evidenceContext";

const RUN_TABS: readonly Tab[] = [
  { id: "turns", label: "Turns" },
  { id: "manifest", label: "Manifest" },
  { id: "raw", label: "Raw" },
];

// read_run() pages turns by limit/offset; the list grows by this step.
const TURN_PAGE = 100;

const SOURCE_LABEL: Record<string, string> = {
  turn_journal: "Turn journal",
  engine_state_manifest: "Engine-state checkpoint",
};

function sourceLabel(source: string): string {
  return SOURCE_LABEL[source] ?? source;
}

function errorMessage(error: unknown) {
  return error instanceof WorkbenchApiError ? error.message : "Runs request failed.";
}

function digestPayload(value: string | null | undefined): string | null {
  if (!value) return null;
  return value.replace(/^sha256:/, "");
}

function CheckpointBadge({
  present,
  revision,
}: {
  present: boolean;
  revision: string | null;
}) {
  if (!present) {
    return (
      <span className="inline-flex h-6 items-center rounded-md border border-[var(--color-border-subtle)] px-2 text-xs text-[var(--color-text-muted)]">
        no checkpoint
      </span>
    );
  }
  return (
    <span className="inline-flex h-6 items-center gap-1 rounded-md border border-[var(--color-border-subtle)] bg-[var(--color-surface-inset)] px-2 text-xs text-[var(--color-text-secondary)]">
      checkpoint
      {revision ? (
        <span className="font-mono text-[var(--color-text-muted)]">{revision}</span>
      ) : null}
    </span>
  );
}

function RunRow({
  run,
  selected,
  focused,
  onSelect,
}: {
  run: RunSummary;
  selected: boolean;
  focused: boolean;
  onSelect: () => void;
}) {
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
        <span className="block text-sm text-[var(--color-text-primary)]">
          {sourceLabel(run.source)}
        </span>
        <span className="mt-1 block truncate font-mono text-xs text-[var(--color-text-muted)]">
          {run.session_id}
        </span>
        <span className="mt-1 flex items-center gap-2 text-xs text-[var(--color-text-secondary)]">
          <span>{run.turn_count} turns</span>
          {run.updated_at ? (
            <>
              <span aria-hidden className="text-[var(--color-text-muted)]">·</span>
              <Timestamp iso={run.updated_at} format="relative" />
            </>
          ) : null}
        </span>
        {run.evidence_gap ? (
          <span className="mt-1 block text-xs text-[var(--color-state-warning-text)]">
            evidence gap: {run.evidence_gap}
          </span>
        ) : null}
      </span>
      <span className="justify-self-end">
        <CheckpointBadge present={run.checkpoint_present} revision={run.checkpoint_revision} />
      </span>
    </div>
  );
}

function TurnRefRow({ turn }: { turn: RunTurnRef }) {
  const digest = digestPayload(turn.trace_hash);
  return (
    <Link
      to={turn.trace_path}
      className="grid grid-cols-[minmax(0,1fr)_auto] items-start gap-3 rounded-md border border-[var(--color-border-subtle)] px-3 py-2 no-underline transition-colors hover:bg-[var(--color-surface-inset)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--color-focus-ring)]"
    >
      <span className="min-w-0">
        <span className="flex items-center gap-1 text-sm text-[var(--color-text-primary)]">
          Turn #{turn.turn_id}
          <ArrowUpRight size={13} aria-hidden className="text-[var(--color-text-muted)]" />
        </span>
        <span className="mt-1 block text-xs text-[var(--color-text-secondary)]">
          <Timestamp iso={turn.timestamp} format="relative" />
        </span>
        <span className="mt-1 block truncate text-xs text-[var(--color-text-muted)]">
          {turn.surface_excerpt || "Not recorded."}
        </span>
      </span>
      <span className="justify-self-end">
        {digest ? (
          <DigestBadge digest={digest} truncate={12} />
        ) : (
          <span className="font-mono text-xs text-[var(--color-text-muted)]">no hash</span>
        )}
      </span>
    </Link>
  );
}

function TurnsTab({
  detail,
  onLoadMore,
  canLoadMore,
}: {
  detail: RunDetail;
  onLoadMore: () => void;
  canLoadMore: boolean;
}) {
  if (detail.turns.length === 0) {
    return (
      <p className="m-0 text-sm text-[var(--color-text-secondary)]">
        This run records no cross-linkable turns. Engine-state checkpoints
        expose their evidence under Manifest.
      </p>
    );
  }
  return (
    <div className="grid gap-2">
      {detail.turns.map((turn) => (
        <TurnRefRow key={turn.turn_id} turn={turn} />
      ))}
      {canLoadMore ? (
        <Button type="button" variant="quiet" onClick={onLoadMore}>
          Load more turns
        </Button>
      ) : null}
    </div>
  );
}

function ManifestTab({ detail }: { detail: RunDetail }) {
  if (!detail.manifest) {
    return (
      <p className="m-0 text-sm text-[var(--color-text-secondary)]">
        No engine-state manifest recorded for this run.
      </p>
    );
  }
  return <StableJsonViewer source={JSON.stringify(detail.manifest, null, 2)} />;
}

function RawTab({ detail }: { detail: RunDetail }) {
  const [expanded, setExpanded] = useState(false);
  return expanded ? (
    <StableJsonViewer source={JSON.stringify(detail, null, 2)} />
  ) : (
    <div className="grid justify-items-start gap-2">
      <p className="m-0 text-sm text-[var(--color-text-secondary)]">
        Raw run JSON is collapsed by default.
      </p>
      <Button type="button" variant="quiet" onClick={() => setExpanded(true)}>
        <Eye size={14} aria-hidden />
        Expand raw JSON
      </Button>
    </div>
  );
}

function RunDetailPanel({
  detail,
  onLoadMore,
  canLoadMore,
}: {
  detail: RunDetail;
  onLoadMore: () => void;
  canLoadMore: boolean;
}) {
  const [activeTab, setActiveTab] = useState("turns");
  return (
    <Panel
      title={sourceLabel(detail.source)}
      toolbar={
        <CheckpointBadge
          present={detail.checkpoint_present}
          revision={detail.checkpoint_revision}
        />
      }
    >
      <TabBar tabs={RUN_TABS} activeTab={activeTab} onTabChange={setActiveTab}>
        {activeTab === "turns" ? (
          <TurnsTab detail={detail} onLoadMore={onLoadMore} canLoadMore={canLoadMore} />
        ) : null}
        {activeTab === "manifest" ? <ManifestTab detail={detail} /> : null}
        {activeTab === "raw" ? <RawTab detail={detail} /> : null}
      </TabBar>
    </Panel>
  );
}

export function RunsRoute() {
  const { sessionId } = useParams();
  const selectedSessionId = sessionId && sessionId.length > 0 ? sessionId : null;
  const navigate = useNavigate();
  const { setSubject } = useEvidenceSubject();
  const [search, setSearch] = useState("");
  const [turnLimit, setTurnLimit] = useState(TURN_PAGE);

  const runsQuery = useRuns();
  const runQuery = useRun(selectedSessionId, turnLimit);

  const runs = runsQuery.data ?? [];
  const filteredRuns = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return runs;
    return runs.filter(
      (run) =>
        run.session_id.toLowerCase().includes(q) ||
        sourceLabel(run.source).toLowerCase().includes(q),
    );
  }, [search, runs]);

  // Reset the turn window when the selected run changes.
  useEffect(() => {
    setTurnLimit(TURN_PAGE);
  }, [selectedSessionId]);

  useEffect(() => {
    if (selectedSessionId === null) return;
    setSubject({ kind: "run", sessionId: selectedSessionId, data: runQuery.data });
  }, [selectedSessionId, setSubject, runQuery.data]);

  function selectRun(run: RunSummary) {
    const subject = { kind: "run" as const, sessionId: run.session_id };
    const path = subjectToUrl(subject);
    navigate(path, { replace: true });
    pushRecentItem({ label: sourceLabel(run.source), path });
  }

  if (runsQuery.isLoading) {
    return <LoadingState label="Loading runs..." />;
  }

  if (runsQuery.isError) {
    return (
      <ErrorState
        whatFailed={errorMessage(runsQuery.error)}
        mutationStatus="No runs mutation occurred."
        reproducer="curl /runs"
        retrySafety="Retry: safe"
      />
    );
  }

  if (runs.length === 0) {
    return (
      <EmptyState
        statement="No runs recorded yet. Use Chat to create evidence."
        nextAction={{ kind: "cli", command: "core chat" }}
      />
    );
  }

  const canLoadMore = !!runQuery.data && runQuery.data.turns.length === turnLimit;

  return (
    <div className="h-full min-h-0">
      <SplitPane direction="horizontal" id="runs" defaultSplit={38} minSize={320}>
        <Panel title="Sessions">
          <div className="grid min-h-0 gap-3">
            <SearchInput
              placeholder="Filter by session or source"
              value={search}
              onChange={setSearch}
            />
            {filteredRuns.length === 0 ? (
              <EmptyState
                statement="No runs match this filter."
                nextAction={{ kind: "cli", command: "core chat" }}
              />
            ) : (
              <VirtualizedList
                ariaLabel="Runs"
                estimateSize={92}
                getKey={(run) => run.session_id}
                height="calc(100vh - 14rem)"
                initialRect={{ width: 480, height: 560 }}
                items={filteredRuns}
                onActivate={(run) => selectRun(run)}
                renderItem={(run, _index, focused) => (
                  <RunRow
                    run={run}
                    selected={run.session_id === selectedSessionId}
                    focused={focused}
                    onSelect={() => selectRun(run)}
                  />
                )}
              />
            )}
          </div>
        </Panel>

        <section className="h-full min-h-0 overflow-y-auto pl-3">
          {selectedSessionId === null ? (
            <EmptyState
              statement="Select a session to inspect its turns, manifest, and checkpoint."
              nextAction={{ kind: "cli", command: "core chat" }}
            />
          ) : runQuery.isLoading ? (
            <LoadingState label="Loading run detail..." />
          ) : runQuery.isError ? (
            <ErrorState
              whatFailed={errorMessage(runQuery.error)}
              mutationStatus="No runs mutation occurred."
              reproducer={`curl /runs/${selectedSessionId}`}
              retrySafety="Retry: safe"
            />
          ) : runQuery.data ? (
            <RunDetailPanel
              detail={runQuery.data}
              onLoadMore={() => setTurnLimit((n) => n + TURN_PAGE)}
              canLoadMore={canLoadMore}
            />
          ) : null}
        </section>
      </SplitPane>
    </div>
  );
}
