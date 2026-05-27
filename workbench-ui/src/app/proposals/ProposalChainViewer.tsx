import { StableJsonViewer } from "../../design/components/StableJsonViewer";
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

export function ProposalChainViewer({ proposal }: { proposal: ProposalDetail }) {
  const records = chainRecords(proposal.proposed_chain);

  return (
    <section className="rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-surface-raised)] p-4">
      <h3 className="m-0 text-sm font-semibold text-[var(--color-text-primary)]">Proposed chain</h3>
      {records.length === 0 ? (
        <p className="text-sm text-[var(--color-text-secondary)]">No chain records are present.</p>
      ) : (
        <ol className="mt-3 grid gap-3 p-0">
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
      )}
    </section>
  );
}
