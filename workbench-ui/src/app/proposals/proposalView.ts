import type { ProposalDetail, ProposalSummary } from "../../types/api";

export type JsonRecord = Record<string, unknown>;

export function shortProposalId(proposalId: string) {
  return proposalId.length > 14 ? `${proposalId.slice(0, 10)}...` : proposalId;
}

export function formatTimestamp(value: string | null) {
  if (!value) return "unknown";
  const timestamp = Date.parse(value);
  if (Number.isNaN(timestamp)) return value;
  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(timestamp));
}

export function jsonSource(value: unknown) {
  return JSON.stringify(value ?? null, null, 2);
}

export function isRecord(value: unknown): value is JsonRecord {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export function provenanceLabel(proposal: Pick<ProposalSummary, "source_kind" | "proposal_id">) {
  return proposal.source_kind || proposal.proposal_id;
}

export function proposalSummaryText(proposal: ProposalDetail) {
  if (isRecord(proposal.source)) {
    for (const key of ["summary", "title", "label", "source_id"]) {
      const value = proposal.source[key];
      if (typeof value === "string" && value.trim()) {
        return value;
      }
    }
  }
  return `${proposal.source_kind} proposal`;
}

export function chainRecords(proposedChain: unknown): unknown[] {
  if (Array.isArray(proposedChain)) return proposedChain;
  if (isRecord(proposedChain)) {
    const records = proposedChain.chain_records;
    if (Array.isArray(records)) return records;
    const nodes = proposedChain.nodes;
    if (Array.isArray(nodes)) return nodes;
  }
  return proposedChain === undefined || proposedChain === null ? [] : [proposedChain];
}

export function stringField(record: JsonRecord, keys: string[]) {
  for (const key of keys) {
    const value = record[key];
    if (typeof value === "string" && value.trim()) {
      return value;
    }
  }
  return null;
}

export function digestField(value: unknown, keys: string[]) {
  if (!isRecord(value)) return null;
  return stringField(value, keys);
}

export function divergenceSummary(value: unknown) {
  if (!isRecord(value)) return null;
  const direct = stringField(value, ["divergence_summary", "summary", "divergence"]);
  if (direct) return direct;
  const divergences = value.divergences;
  if (Array.isArray(divergences)) {
    return divergences.length === 0 ? "No divergences reported." : `${divergences.length} divergence record(s).`;
  }
  return null;
}
