import { useMemo, useState } from "react";
import { SearchInput } from "../../design/components/SearchInput/SearchInput";
import { VirtualizedList } from "../../design/components/VirtualizedList/VirtualizedList";
import type {
  LogosGlossRow,
  LogosLexiconRow,
  LogosMorphologyRow,
} from "../../types/api";

// Read-only CORE-Logos contents tabs (LG-3). Each list reuses VirtualizedList
// (windowing + keyboard nav via useListNavigation) and SearchInput. Selection
// publishes a pack-scoped evidence subject; no data is recomputed here.

const LIST_HEIGHT = 360;
const TEST_RECT = { width: 720, height: LIST_HEIGHT };

function FilterChip({
  label,
  active,
  onClick,
}: {
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      aria-pressed={active}
      onClick={onClick}
      className={`h-6 rounded-md border px-2 text-xs transition-colors ${
        active
          ? "border-[var(--color-selected-border)] bg-[var(--color-selected-bg)] text-[var(--color-text-primary)]"
          : "border-[var(--color-border-subtle)] bg-[var(--color-surface-inset)] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]"
      }`}
    >
      {label}
    </button>
  );
}

function Tag({ children }: { children: React.ReactNode }) {
  return (
    <span className="inline-flex h-5 items-center rounded border border-[var(--color-border-subtle)] bg-[var(--color-surface-inset)] px-1.5 text-[10px] text-[var(--color-text-secondary)]">
      {children}
    </span>
  );
}

function DanglingFlag() {
  return (
    <span className="inline-flex h-5 items-center rounded border border-[var(--color-state-warning-border)] bg-[var(--color-state-warning-bg)] px-1.5 text-[10px] text-[var(--color-state-warning-text)]">
      dangling morphology
    </span>
  );
}

function RowShell({
  selected,
  onSelect,
  children,
}: {
  selected: boolean;
  onSelect: () => void;
  children: React.ReactNode;
}) {
  return (
    <div
      role="button"
      tabIndex={-1}
      aria-current={selected ? "true" : undefined}
      onClick={onSelect}
      className={`grid gap-1 border-b border-[var(--color-border-subtle)] px-3 py-2 text-left ${
        selected
          ? "border-l-2 border-l-[var(--color-selected-border)] bg-[var(--color-selected-bg)] pl-[10px]"
          : "border-l-2 border-l-transparent pl-[10px]"
      }`}
    >
      {children}
    </div>
  );
}

// ---------------------------------------------------------------- Lexicon ----

export function LexiconTab({
  rows,
  danglingEntryIds,
  selectedEntryId,
  onSelect,
}: {
  rows: readonly LogosLexiconRow[];
  danglingEntryIds: ReadonlySet<string>;
  selectedEntryId: string | null;
  onSelect: (row: LogosLexiconRow) => void;
}) {
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [domainFilter, setDomainFilter] = useState<string>("all");

  const statuses = useMemo(
    () => Array.from(new Set(rows.map((r) => r.epistemic_status))).sort(),
    [rows],
  );
  const domains = useMemo(
    () => Array.from(new Set(rows.flatMap((r) => r.semantic_domains))).sort(),
    [rows],
  );

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return rows.filter((r) => {
      if (statusFilter !== "all" && r.epistemic_status !== statusFilter) return false;
      if (domainFilter !== "all" && !r.semantic_domains.includes(domainFilter)) return false;
      if (!q) return true;
      return (
        r.surface.toLowerCase().includes(q) ||
        r.lemma.toLowerCase().includes(q) ||
        r.entry_id.toLowerCase().includes(q) ||
        r.semantic_domains.some((d) => d.toLowerCase().includes(q))
      );
    });
  }, [rows, query, statusFilter, domainFilter]);

  return (
    <div className="grid min-h-0 gap-3">
      <SearchInput
        placeholder="Search surface, lemma, entry id, or domain"
        value={query}
        onChange={setQuery}
      />
      <div className="flex flex-wrap items-center gap-1.5">
        <span className="text-[10px] uppercase text-[var(--color-text-muted)]">status</span>
        <FilterChip label="all" active={statusFilter === "all"} onClick={() => setStatusFilter("all")} />
        {statuses.map((s) => (
          <FilterChip key={s} label={s} active={statusFilter === s} onClick={() => setStatusFilter(s)} />
        ))}
      </div>
      {domains.length > 0 ? (
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-[10px] uppercase text-[var(--color-text-muted)]">domain</span>
          <FilterChip label="all" active={domainFilter === "all"} onClick={() => setDomainFilter("all")} />
          {domains.map((d) => (
            <FilterChip key={d} label={d} active={domainFilter === d} onClick={() => setDomainFilter(d)} />
          ))}
        </div>
      ) : null}
      <div className="text-xs text-[var(--color-text-secondary)]">
        {filtered.length} of {rows.length} entries
      </div>
      <VirtualizedList
        items={filtered}
        ariaLabel="CORE-Logos lexicon"
        height={LIST_HEIGHT}
        estimateSize={64}
        initialRect={TEST_RECT}
        getKey={(row) => row.entry_id}
        onActivate={onSelect}
        renderItem={(row, _index, focused) => (
          <RowShell selected={focused || row.entry_id === selectedEntryId} onSelect={() => onSelect(row)}>
            <div className="flex items-center justify-between gap-2">
              <span className="truncate font-mono text-sm text-[var(--color-text-primary)]">
                {row.surface} · {row.lemma}
              </span>
              <span className="font-mono text-[10px] text-[var(--color-text-muted)]">{row.entry_id}</span>
            </div>
            <div className="flex flex-wrap items-center gap-1.5">
              <Tag>{row.language}</Tag>
              {row.pos ?? row.part_of_speech ? <Tag>{row.pos ?? row.part_of_speech}</Tag> : null}
              <Tag>{row.epistemic_status}</Tag>
              {row.semantic_domains.map((d) => (
                <Tag key={d}>{d}</Tag>
              ))}
              {danglingEntryIds.has(row.entry_id) ? <DanglingFlag /> : null}
            </div>
          </RowShell>
        )}
      />
    </div>
  );
}

// ----------------------------------------------------------------- Glosses ----

export function GlossesTab({
  rows,
  selectedGlossId,
  onSelect,
}: {
  rows: readonly LogosGlossRow[];
  selectedGlossId: string | null;
  onSelect: (row: LogosGlossRow) => void;
}) {
  const [query, setQuery] = useState("");
  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return rows;
    return rows.filter(
      (r) =>
        r.lemma.toLowerCase().includes(q) ||
        r.gloss.toLowerCase().includes(q) ||
        r.entry_ids.some((e) => e.toLowerCase().includes(q)),
    );
  }, [rows, query]);

  return (
    <div className="grid min-h-0 gap-3">
      <SearchInput
        placeholder="Search lemma, gloss text, or linked entry id"
        value={query}
        onChange={setQuery}
      />
      <div className="text-xs text-[var(--color-text-secondary)]">
        {filtered.length} of {rows.length} glosses
      </div>
      <VirtualizedList
        items={filtered}
        ariaLabel="CORE-Logos glosses"
        height={LIST_HEIGHT}
        estimateSize={64}
        initialRect={TEST_RECT}
        getKey={(row) => row.gloss_id}
        onActivate={onSelect}
        renderItem={(row, _index, focused) => (
          <RowShell selected={focused || row.gloss_id === selectedGlossId} onSelect={() => onSelect(row)}>
            <div className="flex items-center justify-between gap-2">
              <span className="truncate font-mono text-sm text-[var(--color-text-primary)]">{row.lemma}</span>
              {row.pos ? <Tag>{row.pos}</Tag> : null}
            </div>
            <p className="m-0 text-xs text-[var(--color-text-secondary)] [text-wrap:balance]">{row.gloss}</p>
            {row.entry_ids.length > 0 ? (
              <div className="flex flex-wrap gap-1.5">
                {row.entry_ids.map((e) => (
                  <Tag key={e}>{e}</Tag>
                ))}
              </div>
            ) : null}
          </RowShell>
        )}
      />
    </div>
  );
}

// -------------------------------------------------------------- Morphology ----

/** The operator chain, rendered in schema order — never re-sorted. */
export function morphologyChain(row: LogosMorphologyRow): string[] {
  return [
    ...row.prefix_chain,
    ...(row.root ? [`√${row.root}`] : row.stem ? [row.stem] : []),
    ...row.suffix_chain,
  ];
}

export function MorphologyTab({
  rows,
  selectedMorphologyId,
  onSelect,
}: {
  rows: readonly LogosMorphologyRow[];
  selectedMorphologyId: string | null;
  onSelect: (row: LogosMorphologyRow) => void;
}) {
  const [query, setQuery] = useState("");
  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return rows;
    return rows.filter(
      (r) =>
        r.surface.toLowerCase().includes(q) ||
        r.lemma.toLowerCase().includes(q) ||
        r.morphology_id.toLowerCase().includes(q) ||
        (r.root ?? "").toLowerCase().includes(q),
    );
  }, [rows, query]);

  return (
    <div className="grid min-h-0 gap-3">
      <SearchInput
        placeholder="Search surface, lemma, root, or morphology id"
        value={query}
        onChange={setQuery}
      />
      <div className="text-xs text-[var(--color-text-secondary)]">
        {filtered.length} of {rows.length} morphology records
      </div>
      <VirtualizedList
        items={filtered}
        ariaLabel="CORE-Logos morphology"
        height={LIST_HEIGHT}
        estimateSize={64}
        initialRect={TEST_RECT}
        getKey={(row) => row.morphology_id}
        onActivate={onSelect}
        renderItem={(row, _index, focused) => {
          const chain = morphologyChain(row);
          return (
            <RowShell
              selected={focused || row.morphology_id === selectedMorphologyId}
              onSelect={() => onSelect(row)}
            >
              <div className="flex items-center justify-between gap-2">
                <span className="truncate font-mono text-sm text-[var(--color-text-primary)]">
                  {row.surface} · {row.lemma}
                </span>
                <span className="font-mono text-[10px] text-[var(--color-text-muted)]">
                  {row.morphology_id}
                </span>
              </div>
              {chain.length > 0 ? (
                <div className="flex flex-wrap items-center gap-1 font-mono text-xs text-[var(--color-text-secondary)]">
                  {chain.map((seg, i) => (
                    <span key={`${row.morphology_id}-${i}`} className="flex items-center gap-1">
                      {i > 0 ? <span aria-hidden className="text-[var(--color-text-muted)]">→</span> : null}
                      <span>{seg}</span>
                    </span>
                  ))}
                </div>
              ) : null}
            </RowShell>
          );
        }}
      />
    </div>
  );
}
