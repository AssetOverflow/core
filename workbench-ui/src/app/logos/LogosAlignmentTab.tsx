import { useMemo } from "react";
import { DagViewer } from "../../design/components/Dag/Dag";
import type { DagEdgeInput, DagNodeInput } from "../../design/components/Dag/layout";
import { TruncatedCell } from "../../design/components/TruncatedCell";
import type { LogosAlignmentRow } from "../../types/api";

// Read-only CORE-Logos alignment tab (LG-4). The trilingual resonance graph
// (he -> grc -> en) renders through the deterministic Dag primitive; the edge
// list carries selection + honest invalid-target warnings. Nothing is
// recomputed — every value is a field from GET /logos/packs/{id}/alignment.

/**
 * Pure, deterministic projection of alignment rows into Dag inputs. Exported so
 * the golden-file layout test can pin the geometry. Node order is sorted (not
 * row order) so the layout is stable regardless of edge ordering; edges follow
 * row order (the endpoint is already deterministic).
 */
export function alignmentToDag(rows: readonly LogosAlignmentRow[]): {
  nodes: DagNodeInput[];
  edges: DagEdgeInput[];
} {
  const ids = new Set<string>();
  for (const row of rows) {
    ids.add(row.source_id);
    ids.add(row.target_id);
  }
  const nodes: DagNodeInput[] = Array.from(ids)
    .sort((a, b) => a.localeCompare(b))
    .map((id) => ({ id, label: id }));
  const edges: DagEdgeInput[] = rows.map((row) => ({
    from: row.source_id,
    to: row.target_id,
    label: row.relation,
  }));
  return { nodes, edges };
}

function languageOf(id: string): string {
  if (id.startsWith("he-")) return "Hebrew";
  if (id.startsWith("grc-")) return "Koine Greek";
  if (id.startsWith("en-")) return "English";
  return "—";
}

function EdgeCard({
  row,
  selected,
  onSelect,
}: {
  row: LogosAlignmentRow;
  selected: boolean;
  onSelect: () => void;
}) {
  return (
    <div
      role="button"
      tabIndex={0}
      aria-current={selected ? "true" : undefined}
      onClick={onSelect}
      onKeyDown={(event) => {
        if (event.key !== "Enter" && event.key !== " ") return;
        event.preventDefault();
        onSelect();
      }}
      className={`grid gap-1 rounded-md border px-3 py-2 text-left transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--color-focus-ring)] ${
        row.invalid_target
          ? "border-[var(--color-state-warning-border)] bg-[var(--color-state-warning-bg)]"
          : selected
            ? "border-[var(--color-selected-border)] bg-[var(--color-selected-bg)]"
            : "border-[var(--color-border-subtle)] hover:bg-[var(--color-surface-inset)]"
      }`}
    >
      <div className="flex items-center justify-between gap-2 font-mono text-xs text-[var(--color-text-primary)]">
        <TruncatedCell
          value={`${row.source_id} → ${row.target_id}`}
          display={
            <>
              {row.source_id}{" "}
              <span aria-hidden className="text-[var(--color-text-muted)]">→</span> {row.target_id}
            </>
          }
          label="alignment edge"
        />
        <span className="text-[var(--color-text-secondary)]">{row.weight.toFixed(2)}</span>
      </div>
      <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-[11px] text-[var(--color-text-secondary)]">
        <span>{row.relation}</span>
        <span aria-hidden className="text-[var(--color-text-muted)]">·</span>
        <span>
          {languageOf(row.source_id)} → {languageOf(row.target_id)}
        </span>
        {row.target_pack_id ? (
          <>
            <span aria-hidden className="text-[var(--color-text-muted)]">·</span>
            <span className="font-mono">{row.target_pack_id}</span>
          </>
        ) : null}
      </div>
      {row.evidence_ids.length > 0 ? (
        <div className="flex flex-wrap gap-1">
          {row.evidence_ids.map((e) => (
            <span
              key={e}
              className="inline-flex h-5 items-center rounded border border-[var(--color-border-subtle)] bg-[var(--color-surface-inset)] px-1.5 text-[10px] font-mono text-[var(--color-text-secondary)]"
            >
              {e}
            </span>
          ))}
        </div>
      ) : null}
      {row.invalid_target ? (
        <p className="m-0 text-[11px] text-[var(--color-state-warning-text)]">
          invalid target — {row.target_id} resolves to no declared lexicon entry
        </p>
      ) : null}
    </div>
  );
}

export function AlignmentTab({
  rows,
  selectedEdgeId,
  onSelect,
}: {
  rows: readonly LogosAlignmentRow[];
  selectedEdgeId: string | null;
  onSelect: (row: LogosAlignmentRow) => void;
}) {
  const { nodes, edges } = useMemo(() => alignmentToDag(rows), [rows]);
  const invalidCount = useMemo(
    () => rows.filter((r) => r.invalid_target).length,
    [rows],
  );

  if (rows.length === 0) {
    return (
      <p className="m-0 text-sm text-[var(--color-text-secondary)]">
        This pack declares no cross-language alignment edges.
      </p>
    );
  }

  return (
    <div className="grid min-h-0 gap-4">
      <section>
        <h3 className="m-0 mb-2 text-xs font-semibold text-[var(--color-text-secondary)]">
          Resonance graph (deterministic)
        </h3>
        <DagViewer
          nodes={nodes}
          edges={edges}
          ariaLabel="CORE-Logos cross-language alignment graph"
          showInspector={false}
        />
      </section>
      <section className="grid gap-2">
        <div className="flex items-center justify-between text-xs text-[var(--color-text-secondary)]">
          <span>{rows.length} alignment edges</span>
          {invalidCount > 0 ? (
            <span className="text-[var(--color-state-warning-text)]">
              {invalidCount} invalid target{invalidCount === 1 ? "" : "s"}
            </span>
          ) : null}
        </div>
        {rows.map((row) => (
          <EdgeCard
            key={row.edge_id}
            row={row}
            selected={row.edge_id === selectedEdgeId}
            onSelect={() => onSelect(row)}
          />
        ))}
      </section>
    </div>
  );
}
