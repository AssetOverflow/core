import type {
  ApiResponse,
  ErrorCode,
  EvalLaneSummary,
  EvalRunRequest,
  EvalRunResult,
  ArtifactRef,
  ArtifactDetail,
  ReplayComparison,
  ProposalDetail,
  ProposalState,
  ProposalSummary,
  AuditEvent,
  TurnJournalEntry,
  TurnJournalSummary,
  MathProposalSummary,
  MathProposalDetail,
  MathRatifyResult,
} from "../types/api";

export class WorkbenchApiError extends Error {
  constructor(
    public readonly code: ErrorCode,
    message: string,
  ) {
    super(message);
    this.name = "WorkbenchApiError";
  }
}

export const API_URL: string =
  import.meta.env.VITE_WORKBENCH_API_URL ?? "http://127.0.0.1:8765";

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 5000);
  try {
    const res = await fetch(`${API_URL}${path}`, { ...init, signal: controller.signal });
    const json: ApiResponse<T> = await res.json();
    if (!json.ok) {
      throw new WorkbenchApiError(json.error.code, json.error.message);
    }
    return json.data;
  } finally {
    clearTimeout(timeout);
  }
}

export async function fetchEvalLanes(): Promise<EvalLaneSummary[]> {
  return apiFetch<EvalLaneSummary[]>("/evals");
}

export async function runEvalLane(req: EvalRunRequest): Promise<EvalRunResult> {
  if (req.split === "holdout") {
    const hasConfig = typeof window !== "undefined" && (window as any).sealedEvalConfig === true;
    if (!hasConfig) {
      throw new WorkbenchApiError(
        "client_refused_sealed_holdout",
        "Holdout runs require sealed-eval config — use CLI"
      );
    }
  }

  const lanes = await fetchEvalLanes();
  const lane = lanes.find((l) => l.lane === req.lane);
  if (!lane) {
    throw new WorkbenchApiError("not_found", `Eval lane not found: ${req.lane}`);
  }
  if (!lane.read_only) {
    throw new WorkbenchApiError("client_refused_unsafe_lane", "API run disabled — use CLI");
  }

  return apiFetch<EvalRunResult>("/evals/run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
}

export async function fetchArtifacts(): Promise<ArtifactRef[]> {
  const data = await apiFetch<{ items: ArtifactRef[] }>("/artifacts");
  return data.items;
}

export async function fetchArtifactDetail(artifactId: string): Promise<ArtifactDetail> {
  return apiFetch<ArtifactDetail>(`/artifacts/${artifactId}`);
}

export async function fetchReplayComparison(artifactId: string): Promise<ReplayComparison> {
  return apiFetch<ReplayComparison>(`/replay/${artifactId}`);
}

export type ProposalStateFilter = ProposalState | "all";

interface ItemsEnvelope<T> {
  items: T[];
}

export async function fetchProposals(
  filter: ProposalStateFilter = "all",
): Promise<ProposalSummary[]> {
  const envelope = await apiFetch<ItemsEnvelope<ProposalSummary>>("/proposals");
  if (filter === "all") {
    return envelope.items;
  }
  return envelope.items.filter((proposal) => proposal.state === filter);
}

export async function fetchProposalDetail(proposalId: string): Promise<ProposalDetail> {
  return apiFetch<ProposalDetail>(`/proposals/${encodeURIComponent(proposalId)}`);
}

export async function fetchTraceTurns(
  limit?: number,
  offset?: number,
): Promise<TurnJournalSummary[]> {
  const params = new URLSearchParams();
  if (limit !== undefined) params.set("limit", String(limit));
  if (offset !== undefined) params.set("offset", String(offset));
  const query = params.toString();
  const envelope = await apiFetch<ItemsEnvelope<TurnJournalSummary>>(
    query ? `/trace/turns?${query}` : "/trace/turns",
  );
  return envelope.items;
}

export async function fetchTraceTurn(turnId: number): Promise<TurnJournalEntry> {
  return apiFetch<TurnJournalEntry>(`/trace/${encodeURIComponent(String(turnId))}`);
}

export async function fetchAuditEvents(
  limit?: number,
  offset?: number,
): Promise<ItemsEnvelope<AuditEvent>> {
  const params = new URLSearchParams();
  if (limit !== undefined) params.set("limit", String(limit));
  if (offset !== undefined) params.set("offset", String(offset));
  const query = params.toString();
  return apiFetch<ItemsEnvelope<AuditEvent>>(query ? `/audit/events?${query}` : "/audit/events");
}

export async function fetchMathProposals(): Promise<MathProposalSummary[]> {
  const envelope = await apiFetch<ItemsEnvelope<MathProposalSummary>>("/math-proposals");
  return envelope.items;
}

export async function fetchMathProposalDetail(proposalId: string): Promise<MathProposalDetail> {
  return apiFetch<MathProposalDetail>(`/math-proposals/${encodeURIComponent(proposalId)}`);
}

export async function ratifyMathProposal(
  proposalId: string,
  category?: string,
  polarity?: string,
  dryRun?: boolean,
): Promise<MathRatifyResult> {
  return apiFetch<MathRatifyResult>(`/math-proposals/${encodeURIComponent(proposalId)}/ratify`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ category, polarity, dry_run: dryRun }),
  });
}

export async function rejectMathProposal(
  proposalId: string,
  note?: string,
): Promise<{ proposal_id: string; rejected: boolean }> {
  return apiFetch<{ proposal_id: string; rejected: boolean }>(
    `/math-proposals/${encodeURIComponent(proposalId)}/reject`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ note }),
    },
  );
}

export async function deferMathProposal(
  proposalId: string,
): Promise<{ proposal_id: string; deferred: boolean }> {
  return apiFetch<{ proposal_id: string; deferred: boolean }>(
    `/math-proposals/${encodeURIComponent(proposalId)}/defer`,
    {
      method: "POST",
    },
  );
}
