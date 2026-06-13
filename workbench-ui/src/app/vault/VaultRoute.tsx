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

// Vault persistence is opt-in; absence is the common, honest state. This is
// the fail-closed primary contract, not an error.
const FAIL_CLOSED_STATEMENT =
  "No persisted vault. Session memory is held in-process and discarded on exit; persistence is opt-in via RuntimeConfig.persist_session_state.";
const FAIL_CLOSED_ACTION = "Set RuntimeConfig.persist_session_state = true";

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

function FailClosed() {
  return (
    <EmptyState statement={FAIL_CLOSED_STATEMENT} nextAction={FAIL_CLOSED_ACTION} />
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
    return <LoadingState label="Loading vault..." />;
  }

  // Fail-closed: no persisted vault is the expected primary state, not an error.
  if (summaryQuery.isError) {
    if (summaryQuery.error.code === "evidence_unavailable") {
      return <FailClosed />;
    }
    return (
      <ErrorState
        whatFailed={errorMessage(summaryQuery.error)}
        mutationStatus="No vault mutation occurred."
        reproducer="curl /vault/summary"
        retrySafety="Retry: safe"
      />
    );
  }

  if (!hasEntries) {
    return <FailClosed />;
  }

  return (
    <Panel
      title="Vault"
      toolbar={
        <span className="font-mono text-xs text-[var(--color-text-muted)]">
          {summary.entry_count} entries
        </span>
      }
    >
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
            statement="No vault entries match this filter."
            nextAction={FAIL_CLOSED_ACTION}
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
    </Panel>
  );
}
