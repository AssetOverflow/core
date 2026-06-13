import { StableJsonViewer } from "../../design/components/StableJsonViewer";
import { DagViewer, type DagEdgeInput, type DagNodeInput } from "../../design/components/Dag";
import type { ProposalDetail } from "../../types/api";
import { chainRecords, isRecord, jsonSource, stringField } from "./proposalView";

function nodeLabel(record: unknown, index: number) {
  if (!isRecord(record)) return `Chain node ${index + 1}`;
  return (
    stringField(record, ["id", "chain_id", "subject", "predicate", "object"]) ??
    `Chain node ${index + 1}`
  );
}

function provenance(record: unknown) {
  if (!isRecord(record)) return null;
  const direct = stringField(record, ["provenance", "source", "source_id", "corpus_id"]);
  return direct;
}

function chainNodeId(record: unknown, index: number, seen: Set<string>) {
  const base = isRecord(record)
    ? stringField(record, ["id", "chain_id", "node_id", "claim_id"]) ?? `chain-${index + 1}`
    : `chain-${index + 1}`;
  let id = base;
  let suffix = 2;
  while (seen.has(id)) {
    id = `${base}-${suffix}`;
    suffix += 1;
  }
  seen.add(id);
  return id;
}

function dagFromRecords(records: unknown[]): { nodes: DagNodeInput[]; edges: DagEdgeInput[] } {
  const seen = new Set<string>();
  const nodes = records.map((record, index) => ({
    id: chainNodeId(record, index, seen),
    label: nodeLabel(record, index),
    detail: record,
  }));
  const edges = nodes.slice(1).map((node, index) => ({
    from: nodes[index].id,
    to: node.id,
  }));
  return { nodes, edges };
}

export function ProposalChainViewer({ proposal }: { proposal: ProposalDetail }) {
  const records = chainRecords(proposal.proposed_chain);
  const dag = dagFromRecords(records);

  return (
    <section className="rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-surface-raised)] p-4">
      <h3 className="m-0 text-sm font-semibold text-[var(--color-text-primary)]">Proposed chain</h3>
      {records.length === 0 ? (
        <p className="text-sm text-[var(--color-text-secondary)]">No chain records are present.</p>
      ) : (
        <div className="mt-3 grid gap-4">
          <DagViewer nodes={dag.nodes} edges={dag.edges} ariaLabel="Proposal chain DAG" />
          <ol className="grid gap-3 p-0">
            {records.map((record, index) => (
              <li
                className="grid gap-2 rounded-md border border-[var(--color-border-subtle)] bg-[var(--color-surface-inset)] p-3"
                key={`${nodeLabel(record, index)}-${index}`}
              >
                <div className="flex items-center justify-between gap-3">
                  <span className="font-mono text-xs text-[var(--color-text-primary)]">
                    {index + 1}. {nodeLabel(record, index)}
                  </span>
                  {provenance(record) ? (
                    <span className="truncate text-xs text-[var(--color-text-muted)]">
                      {provenance(record)}
                    </span>
                  ) : null}
                </div>
                <StableJsonViewer source={jsonSource(record)} />
              </li>
            ))}
          </ol>
        </div>
      )}
    </section>
  );
}
