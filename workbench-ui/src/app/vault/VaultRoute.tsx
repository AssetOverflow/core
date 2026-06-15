import { useEffect, useMemo, useState } from "react";
import { WorkbenchApiError } from "../../api/client";
import { useVaultEntries, useVaultSummary } from "../../api/queries";
import { DigestBadge } from "../../design/components/DigestBadge/DigestBadge";
import { MetadataTable } from "../../design/components/MetadataTable/MetadataTable";
import { Panel } from "../../design/components/Panel/Panel";
import { SearchInput } from "../../design/components/SearchInput/SearchInput";
import { VirtualizedList } from "../../design/components/VirtualizedList/VirtualizedList";
import { EmptyState } from "../../design/components/states/EmptyState";
import { ErrorState } from "../../design/components/states/ErrorState";
import { LoadingState } from "../../design/components/states/LoadingState";
import type { VaultEntry, VaultSummary } from "../../types/api";
import { useEvidenceSubject } from "../evidenceContext";

// Vault persistence is opt-in; absence of a snapshot is the common, honest
// primary state — the fail-closed contract, not an error.
//
// The next action must be TRUE and runnable: `core always-on` is the daemon
// that forces persist_session_state=True (chat/always_on_daemon.py) and writes
// engine_state/session_state.json. There is no `core chat --persist-session-state`
// flag today, so we do not invent one — that would be the same dishonesty as a
// dead button. Exported so route-conformance asserts the exact contract string.
export const VAULT_ABSENCE_STATEMENT =
  "No persisted vault snapshot is available. Session memory is held in-process " +
  "and discarded on exit; persistence is opt-in (RuntimeConfig.persist_session_state). " +
  "The always-on daemon writes the snapshot.";
export const VAULT_ABSENCE_ACTION = "core always-on";
const VAULT_PERSIST_CLI = { kind: "cli", command: VAULT_ABSENCE_ACTION } as const;

// A persisted snapshot that holds zero entries is a DIFFERENT honest state from
// absence: the vault exists, it just has not stored anything yet.
const VAULT_EMPTY_STATEMENT =
  "Vault snapshot exists, but no entries have been stored yet.";

// Filtering is the operator's own action; the remedy is to relax the filter,
// not to enable persistence. Static guidance, not a command.
const VAULT_FILTER_EMPTY_STATEMENT = "No vault entries match this filter.";
const VAULT_FILTER_EMPTY_ACTION = "Clear the filter to see all entries.";

function errorMessage(error: unknown) {
  return error instanceof WorkbenchApiError ? error.message : "Vault request failed.";
}

function digestPayload(value: string | null | undefined): string | null {
  if (!value) return null;
  return value.replace(/^sha256:/, "");
}

function StatusPill({ children }: { children: React.ReactNode }) {
  return (
    <span className="inline-flex h-6 items-center rounded-md border border-[var(--color-border-subtle)] bg-[var(--color-surface-inset)] px-2 text-xs text-[var(--color-text-secondary)]">
      {children}
    </span>
  );
}

function VaultRow({
  entry,
  selected,
  focused,
  onSelect,
}: {
  entry: VaultEntry;
  selected: boolean;
  focused: boolean;
  onSelect: () => void;
}) {
  const digest = digestPayload(entry.versor_digest);
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
        <span className="block font-mono text-xs text-[var(--color-text-muted)]">
          #{entry.entry_index}
        </span>
        <span className="mt-1 flex flex-wrap items-center gap-2">
          <StatusPill>{entry.epistemic_status}</StatusPill>
          <StatusPill>{entry.epistemic_state}</StatusPill>
        </span>
      </span>
      <span className="justify-self-end">
        {digest ? (
          <DigestBadge digest={digest} truncate={12} />
        ) : (
          <span className="font-mono text-xs text-[var(--color-text-muted)]">no versor</span>
        )}
      </span>
    </div>
  );
}

function VaultSummaryStrip({ summary }: { summary: VaultSummary }) {
  // Render only fields the backend returns. Recall is exact CGA (cga_inner);
  // the UI must never invent an approximate similarity/relevance proxy.
  return (
    <MetadataTable
      rows={[
        { key: "entry_count", value: String(summary.entry_count), mono: true },
        { key: "store_count", value: String(summary.store_count), mono: true },
        { key: "reproject_interval", value: String(summary.reproject_interval), mono: true },
        {
          key: "max_entries",
          value: summary.max_entries === null ? "unbounded" : String(summary.max_entries),
          mono: true,
        },
        { key: "source_path", value: summary.source_path, mono: true },
      ]}
    />
  );
}

// Route identity must survive every data state. The success path was the only
// branch that painted "Vault" chrome, so loading/absent/empty/error read as a
// context-free card floating in a blank surface ("nothing comes up"). Wrapping
// every branch in the same Panel keeps the route legible regardless of state.
function VaultFrame({
  toolbar,
  children,
}: {
  toolbar?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <Panel title="Vault" toolbar={toolbar}>
      {children}
    </Panel>
  );
}

function EntryCountToolbar({ count }: { count: number }) {
  return (
    <span className="font-mono text-xs text-[var(--color-text-muted)]">
      {count} entries
    </span>
  );
}

export function VaultRoute() {
  const { subject, setSubject, setInspectorOpen } = useEvidenceSubject();
  const [search, setSearch] = useState("");

  const summaryQuery = useVaultSummary();
  const summary = summaryQuery.data;
  const hasEntries = !!summary && summary.persisted && summary.entry_count > 0;
  const entriesQuery = useVaultEntries(hasEntries);

  const selectedIndex =
    subject.kind === "vault_entry" ? subject.entryIndex : null;

  const entries = entriesQuery.data ?? [];
  const filteredEntries = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return entries;
    return entries.filter(
      (entry) =>
        entry.epistemic_status.toLowerCase().includes(q) ||
        entry.epistemic_state.toLowerCase().includes(q) ||
        String(entry.entry_index).includes(q),
    );
  }, [search, entries]);

  // Hydrate a URL-restored (identity-only) vault_entry subject with its data.
  useEffect(() => {
    if (subject.kind !== "vault_entry" || subject.data) return;
    const match = entries.find((entry) => entry.entry_index === subject.entryIndex);
    if (match) {
      setSubject({ kind: "vault_entry", entryIndex: match.entry_index, data: match });
    }
  }, [subject, entries, setSubject]);

  function selectEntry(entry: VaultEntry) {
    setSubject({ kind: "vault_entry", entryIndex: entry.entry_index, data: entry });
    setInspectorOpen(true);
  }

  if (summaryQuery.isLoading) {
    return (
      <VaultFrame>
        <LoadingState label="Loading vault..." />
      </VaultFrame>
    );
  }

  // Fail-closed: no persisted vault snapshot is the expected primary state, not
  // an error. The summary reader returns evidence_unavailable when the snapshot
  // is absent (persistence is opt-in).
  if (summaryQuery.isError) {
    if (summaryQuery.error.code === "evidence_unavailable") {
      return (
        <VaultFrame>
          <EmptyState statement={VAULT_ABSENCE_STATEMENT} nextAction={VAULT_PERSIST_CLI} />
        </VaultFrame>
      );
    }
    return (
      <VaultFrame>
        <ErrorState
          whatFailed={errorMessage(summaryQuery.error)}
          mutationStatus="No vault mutation occurred."
          reproducer="curl /vault/summary"
          retrySafety="Retry: safe"
        />
      </VaultFrame>
    );
  }

  // react-query guarantees data is present once the query is neither loading
  // nor errored, but the `summary` alias was captured before that narrowing.
  // Guard explicitly — a missing summary is treated as honest absence, framed.
  if (!summary) {
    return (
      <VaultFrame>
        <EmptyState statement={VAULT_ABSENCE_STATEMENT} nextAction={VAULT_PERSIST_CLI} />
      </VaultFrame>
    );
  }

  // summary is defined past this point. A snapshot whose `persisted` flag is not
  // set is treated as absence — the same honest fail-closed card.
  if (!summary.persisted) {
    return (
      <VaultFrame>
        <EmptyState statement={VAULT_ABSENCE_STATEMENT} nextAction={VAULT_PERSIST_CLI} />
      </VaultFrame>
    );
  }

  // A persisted snapshot with zero entries is a DISTINCT state from absence: the
  // vault exists, it just has not stored anything yet.
  if (summary.entry_count === 0) {
    return (
      <VaultFrame toolbar={<EntryCountToolbar count={0} />}>
        <EmptyState statement={VAULT_EMPTY_STATEMENT} nextAction={VAULT_PERSIST_CLI} />
      </VaultFrame>
    );
  }

  return (
    <VaultFrame toolbar={<EntryCountToolbar count={summary.entry_count} />}>
      <div className="grid min-h-0 gap-3">
        <VaultSummaryStrip summary={summary} />
        <SearchInput
          placeholder="Filter by epistemic status, state, or index"
          value={search}
          onChange={setSearch}
        />
        {entriesQuery.isLoading ? (
          <LoadingState label="Loading vault entries..." />
        ) : entriesQuery.isError ? (
          <ErrorState
            whatFailed={errorMessage(entriesQuery.error)}
            mutationStatus="No vault mutation occurred."
            reproducer="curl /vault/entries"
            retrySafety="Retry: safe"
          />
        ) : filteredEntries.length === 0 ? (
          <EmptyState
            statement={VAULT_FILTER_EMPTY_STATEMENT}
            nextAction={VAULT_FILTER_EMPTY_ACTION}
          />
        ) : (
          <VirtualizedList
            ariaLabel="Vault entries"
            estimateSize={72}
            getKey={(entry) => String(entry.entry_index)}
            height="calc(100vh - 18rem)"
            initialRect={{ width: 480, height: 560 }}
            items={filteredEntries}
            onActivate={(entry) => selectEntry(entry)}
            renderItem={(entry, _index, focused) => (
              <VaultRow
                entry={entry}
                selected={entry.entry_index === selectedIndex}
                focused={focused}
                onSelect={() => selectEntry(entry)}
              />
            )}
          />
        )}
      </div>
    </VaultFrame>
  );
}
