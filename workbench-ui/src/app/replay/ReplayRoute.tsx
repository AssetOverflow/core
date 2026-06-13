import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { WorkbenchApiError } from "../../api/client";
import { useTraceTurns, useTurnReplay } from "../../api/queries";
import { DigestBadge } from "../../design/components/DigestBadge/DigestBadge";
import { Panel } from "../../design/components/Panel/Panel";
import { SearchInput } from "../../design/components/SearchInput/SearchInput";
import { SplitPane } from "../../design/components/SplitPane/SplitPane";
import { Timestamp } from "../../design/components/Timestamp/Timestamp";
import { VirtualizedList } from "../../design/components/VirtualizedList/VirtualizedList";
import { EmptyState } from "../../design/components/states/EmptyState";
import { ErrorState } from "../../design/components/states/ErrorState";
import { LoadingState } from "../../design/components/states/LoadingState";
import type {
  TurnJournalSummary,
  TurnReplayComparison,
  TurnReplayDivergence,
} from "../../types/api";
import { pushRecentItem } from "../commandRegistry";
import { useEvidenceSubject } from "../evidenceContext";

function parseTurnId(raw: string | undefined): number | null {
  if (!raw || !/^\d+$/.test(raw)) return null;
  const value = Number(raw);
  return Number.isSafeInteger(value) ? value : null;
}

function errorMessage(error: unknown) {
  return error instanceof WorkbenchApiError ? error.message : "Replay request failed.";
}

function digestPayload(value: string | null | undefined): string | null {
  if (!value) return null;
  return value.replace(/^sha256:/, "");
}

function stringify(value: unknown): string {
  if (typeof value === "string") return value;
  return JSON.stringify(value);
}

function TurnRow({
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
          {turn.prompt_excerpt || `Turn #${turn.turn_id}`}
        </span>
      </span>
      <span className="justify-self-end font-mono text-xs text-[var(--color-text-muted)]">
        #{turn.turn_id}
      </span>
    </div>
  );
}

function HashPair({ comparison }: { comparison: TurnReplayComparison }) {
  const original = digestPayload(comparison.original_trace_hash);
  const replay = digestPayload(comparison.replay_trace_hash);
  return (
    <div className="grid grid-cols-[auto_1fr] items-center gap-x-3 gap-y-2 text-sm">
      <span className="text-[var(--color-text-secondary)]">original</span>
      <span>{original ? <DigestBadge digest={original} truncate={16} /> : "not recorded"}</span>
      <span className="text-[var(--color-text-secondary)]">replay</span>
      <span>{replay ? <DigestBadge digest={replay} truncate={16} /> : "not recorded"}</span>
    </div>
  );
}

function Verdict({ equivalent }: { equivalent: boolean }) {
  return (
    <div
      className={`flex items-center gap-2 rounded-md border px-3 py-2 ${
        equivalent
          ? "border-[var(--color-state-verified)] text-[var(--color-state-verified)]"
          : "border-[var(--color-state-contradicted)] text-[var(--color-state-contradicted)]"
      }`}
    >
      <span aria-hidden className="font-mono text-lg">
        {equivalent ? "≡" : "≠"}
      </span>
      <span className="text-sm font-semibold">
        {equivalent ? "Replay equivalent — bit-identical envelope" : "Replay diverged"}
      </span>
    </div>
  );
}

function DivergenceRow({ divergence }: { divergence: TurnReplayDivergence }) {
  const critical = divergence.severity === "critical";
  return (
    <li
      className={`grid gap-1 rounded-md border px-3 py-2 ${
        critical
          ? "border-[var(--color-state-contradicted)] bg-[var(--color-surface-inset)]"
          : "border-[var(--color-border-subtle)]"
      }`}
    >
      <span className="flex items-center gap-2">
        <span aria-hidden className="font-mono text-[var(--color-text-muted)]">
          ≠
        </span>
        <span className="font-mono text-xs text-[var(--color-text-primary)]">{divergence.path}</span>
        <span
          className={`text-[10px] uppercase tracking-wide ${
            critical ? "text-[var(--color-state-contradicted)]" : "text-[var(--color-text-muted)]"
          }`}
        >
          {divergence.severity}
        </span>
      </span>
      <span className="grid grid-cols-[auto_1fr] gap-x-2 font-mono text-xs">
        <span className="text-[var(--color-text-secondary)]">original</span>
        <span className="break-all text-[var(--color-text-primary)]">
          {stringify(divergence.original)}
        </span>
        <span className="text-[var(--color-text-secondary)]">replay</span>
        <span className="break-all text-[var(--color-text-primary)]">
          {stringify(divergence.replay)}
        </span>
      </span>
    </li>
  );
}

function ReplayHero({ comparison }: { comparison: TurnReplayComparison }) {
  // critical first, then informational; stable within a severity by path.
  const ordered = useMemo(() => {
    const weight = (s: string) => (s === "critical" ? 0 : 1);
    return [...comparison.divergences].sort(
      (a, b) => weight(a.severity) - weight(b.severity) || a.path.localeCompare(b.path),
    );
  }, [comparison.divergences]);
  const informationalOnly =
    comparison.divergences.length > 0 &&
    comparison.divergences.every((d) => d.severity === "informational");

  return (
    <Panel title={`Replay of Turn #${comparison.turn_id}`}>
      <div className="grid gap-4">
        <Verdict equivalent={comparison.equivalent} />
        <HashPair comparison={comparison} />

        <section className="rounded-md border border-[var(--color-border-subtle)] bg-[var(--color-surface-inset)] p-3">
          <h3 className="m-0 text-xs font-semibold text-[var(--color-text-secondary)]">
            What this proves
          </h3>
          <p className="mt-1 mb-0 text-xs text-[var(--color-text-muted)]">
            Basis: <span className="font-mono">{comparison.comparison_basis}</span>. The prompt was
            re-executed in a sealed fresh runtime. Origin state is{" "}
            <span className="font-mono">{comparison.origin_state}</span> — the journal does not
            record whether the original turn loaded a checkpoint, so a divergence means
            nondeterminism <em>or</em> origin-state influence; it is not, on its own, a determinism
            failure.
          </p>
        </section>

        {comparison.divergences.length === 0 ? (
          <p className="m-0 text-sm text-[var(--color-text-secondary)]">
            No divergences — every leaf of the envelope matched.
          </p>
        ) : (
          <section className="grid gap-2">
            <h3 className="m-0 text-xs font-semibold text-[var(--color-text-secondary)]">
              Leaf divergences ({comparison.divergences.length})
              {informationalOnly ? " — all informational (wall-clock; expected)" : ""}
            </h3>
            <ul className="m-0 grid list-none gap-2 p-0">
              {ordered.map((divergence) => (
                <DivergenceRow key={divergence.path} divergence={divergence} />
              ))}
            </ul>
          </section>
        )}
      </div>
    </Panel>
  );
}

export function ReplayRoute() {
  const { turnId } = useParams();
  const selectedTurnId = parseTurnId(turnId);
  const navigate = useNavigate();
  const { setSubject } = useEvidenceSubject();
  const [search, setSearch] = useState("");

  const turnsQuery = useTraceTurns();
  const replayQuery = useTurnReplay(selectedTurnId);

  const turns = turnsQuery.data ?? [];
  const filteredTurns = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return turns;
    return turns.filter(
      (turn) =>
        turn.prompt_excerpt.toLowerCase().includes(q) || String(turn.turn_id).includes(q),
    );
  }, [search, turns]);

  // Publish the turn subject for the inspector.
  useEffect(() => {
    if (selectedTurnId === null) return;
    setSubject({ kind: "turn", turnId: selectedTurnId });
  }, [selectedTurnId, setSubject]);

  function selectTurn(turn: TurnJournalSummary) {
    navigate(`/replay/${turn.turn_id}`, { replace: true });
    pushRecentItem({ label: `Replay #${turn.turn_id}`, path: `/replay/${turn.turn_id}` });
  }

  if (turnsQuery.isLoading) {
    return <LoadingState label="Loading turns..." />;
  }

  if (turnsQuery.isError) {
    return (
      <ErrorState
        whatFailed={errorMessage(turnsQuery.error)}
        mutationStatus="No replay mutation occurred."
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
      <SplitPane direction="horizontal" id="replay" defaultSplit={36} minSize={320}>
        <Panel title="Replayable turns">
          <div className="grid min-h-0 gap-3">
            <SearchInput
              placeholder="Filter by prompt or turn id"
              value={search}
              onChange={setSearch}
            />
            {filteredTurns.length === 0 ? (
              <EmptyState
                statement="No turns match this filter."
                nextAction={{ kind: "cli", command: "core chat" }}
              />
            ) : (
              <VirtualizedList
                ariaLabel="Replayable turns"
                estimateSize={72}
                getKey={(turn) => String(turn.turn_id)}
                height="calc(100vh - 14rem)"
                initialRect={{ width: 480, height: 560 }}
                items={filteredTurns}
                onActivate={(turn) => selectTurn(turn)}
                renderItem={(turn, _index, focused) => (
                  <TurnRow
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
              statement="Select a turn to replay it deterministically and compare hashes."
              nextAction={{ kind: "cli", command: "core chat" }}
            />
          ) : replayQuery.isLoading ? (
            <LoadingState label="Replaying turn..." />
          ) : replayQuery.isError ? (
            <ErrorState
              whatFailed={errorMessage(replayQuery.error)}
              mutationStatus="No replay mutation occurred."
              reproducer={`curl /replay/${selectedTurnId}`}
              retrySafety="Retry: safe"
            />
          ) : replayQuery.data ? (
            <ReplayHero comparison={replayQuery.data} />
          ) : null}
        </section>
      </SplitPane>
    </div>
  );
}
