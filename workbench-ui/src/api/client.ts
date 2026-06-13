import type {
  ApiResponse,
  ErrorCode,
  DemoRunResult,
  DemoSummary,
  EvalLaneSummary,
  EvalRunRequest,
  EvalRunResult,
  ArtifactRef,
  ArtifactDetail,
  TurnReplayComparison,
  ProposalDetail,
  ProposalState,
  ProposalSummary,
  AuditEvent,
  RunSummary,
  RunDetail,
  PackSummary,
  PackDetail,
  VaultSummary,
  VaultEntry,
  CalibrationClass,
  ServingMetrics,
  CognitivePipelineRecord,
  FieldEvidence,
  TurnJournalEntry,
  TurnJournalSummary,
  ContemplationRunDetail,
  ContemplationRunSummary,
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

export async function apiFetch<T>(
  path: string,
  init?: RequestInit & { timeoutMs?: number },
): Promise<T> {
  const { timeoutMs = 5000, ...requestInit } = init ?? {};
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(`${API_URL}${path}`, { ...requestInit, signal: controller.signal });
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
  const envelope = await apiFetch<{ lanes: EvalLaneSummary[] }>("/evals");
  return envelope.lanes;
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
    timeoutMs: 120000,
  });
}

export async function fetchArtifacts(): Promise<ArtifactRef[]> {
  const data = await apiFetch<{ items: ArtifactRef[] }>("/artifacts");
  return data.items;
}

export async function fetchArtifactDetail(artifactId: string): Promise<ArtifactDetail> {
  return apiFetch<ArtifactDetail>(`/artifacts/${artifactId}`);
}

export async function fetchTurnReplay(turnId: number): Promise<TurnReplayComparison> {
  return apiFetch<TurnReplayComparison>(`/replay/${encodeURIComponent(String(turnId))}`);
}

export async function fetchDemos(): Promise<DemoSummary[]> {
  const envelope = await apiFetch<ItemsEnvelope<DemoSummary>>("/demos");
  return envelope.items;
}

export async function runDemo(demoId: string): Promise<DemoRunResult> {
  return apiFetch<DemoRunResult>(`/demos/${encodeURIComponent(demoId)}/run`, {
    method: "POST",
  });
}

export async function fetchContemplationRuns(
  limit?: number,
  offset?: number,
): Promise<ContemplationRunSummary[]> {
  const params = new URLSearchParams();
  if (limit !== undefined) params.set("limit", String(limit));
  if (offset !== undefined) params.set("offset", String(offset));
  const query = params.toString();
  const envelope = await apiFetch<ItemsEnvelope<ContemplationRunSummary>>(
    query ? `/contemplation/runs?${query}` : "/contemplation/runs",
  );
  return envelope.items;
}

export async function fetchContemplationRun(
  runId: string,
): Promise<ContemplationRunDetail> {
  return apiFetch<ContemplationRunDetail>(
    `/contemplation/runs/${encodeURIComponent(runId)}`,
  );
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

export async function fetchTracePipeline(turnId: number): Promise<CognitivePipelineRecord> {
  return apiFetch<CognitivePipelineRecord>(
    `/trace/${encodeURIComponent(String(turnId))}/pipeline`,
  );
}

export async function fetchTraceField(turnId: number): Promise<FieldEvidence> {
  return apiFetch<FieldEvidence>(
    `/trace/${encodeURIComponent(String(turnId))}/field`,
  );
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

export async function fetchRuns(limit?: number, offset?: number): Promise<RunSummary[]> {
  const params = new URLSearchParams();
  if (limit !== undefined) params.set("limit", String(limit));
  if (offset !== undefined) params.set("offset", String(offset));
  const query = params.toString();
  const envelope = await apiFetch<ItemsEnvelope<RunSummary>>(query ? `/runs?${query}` : "/runs");
  return envelope.items;
}

export async function fetchRun(
  sessionId: string,
  turnLimit?: number,
  turnOffset?: number,
): Promise<RunDetail> {
  const params = new URLSearchParams();
  if (turnLimit !== undefined) params.set("limit", String(turnLimit));
  if (turnOffset !== undefined) params.set("offset", String(turnOffset));
  const query = params.toString();
  const path = `/runs/${encodeURIComponent(sessionId)}`;
  return apiFetch<RunDetail>(query ? `${path}?${query}` : path);
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

export async function fetchPacks(limit?: number, offset?: number): Promise<PackSummary[]> {
  const params = new URLSearchParams();
  if (limit !== undefined) params.set("limit", String(limit));
  if (offset !== undefined) params.set("offset", String(offset));
  const query = params.toString();
  const envelope = await apiFetch<ItemsEnvelope<PackSummary>>(query ? `/packs?${query}` : "/packs");
  return envelope.items;
}

export async function fetchPack(packId: string): Promise<PackDetail> {
  return apiFetch<PackDetail>(`/packs/${encodeURIComponent(packId)}`);
}

export async function fetchVaultSummary(): Promise<VaultSummary> {
  return apiFetch<VaultSummary>("/vault/summary");
}

export async function fetchVaultEntries(limit?: number, offset?: number): Promise<VaultEntry[]> {
  const params = new URLSearchParams();
  if (limit !== undefined) params.set("limit", String(limit));
  if (offset !== undefined) params.set("offset", String(offset));
  const query = params.toString();
  const envelope = await apiFetch<ItemsEnvelope<VaultEntry>>(
    query ? `/vault/entries?${query}` : "/vault/entries",
  );
  return envelope.items;
}

export async function fetchCalibrationClasses(): Promise<CalibrationClass[]> {
  const envelope = await apiFetch<ItemsEnvelope<CalibrationClass>>("/calibration/classes");
  return envelope.items;
}

export async function fetchServingMetrics(): Promise<ServingMetrics[]> {
  const envelope = await apiFetch<ItemsEnvelope<ServingMetrics>>("/serving/metrics");
  return envelope.items;
}
