import {
  QueryClient,
  useQuery,
  useMutation,
  QueryClientProvider,
} from "@tanstack/react-query";
import {
  apiFetch,
  fetchHealth,
  fetchDemos,
  fetchEvalLanes,
  runEvalLane,
  fetchArtifacts,
  fetchArtifactDetail,
  fetchTurnReplay,
  runDemo,
  fetchProposalDetail,
  fetchProposals,
  fetchAuditEvents,
  fetchRuns,
  fetchRun,
  fetchPacks,
  fetchPack,
  fetchLogosPacks,
  fetchLogosPackOverview,
  fetchLogosPackSafety,
  fetchLogosPackContents,
  fetchLogosPackAlignment,
  fetchVaultSummary,
  fetchVaultEntries,
  fetchVaultEntryRecall,
  fetchCalibrationClasses,
  fetchServingMetrics,
  fetchTraceTurn,
  fetchTracePipeline,
  fetchTraceField,
  fetchTraceBundle,
  fetchTraceConstruction,
  fetchTracePractice,
  fetchTour,
  fetchLivedLife,
  fetchTraceTurns,
  fetchContemplationRun,
  fetchContemplationRuns,
  fetchMathProposals,
  fetchMathProposalDetail,
  ratifyMathProposal,
  rejectMathProposal,
  deferMathProposal,
  type ProposalStateFilter,
} from "./client";
import type { WorkbenchApiError } from "./client";
import type {
  HealthStatus,
  RuntimeStatus,
  DemoRunResult,
  DemoSummary,
  ArtifactRef,
  ArtifactDetail,
  ProposalSummary,
  ProposalDetail,
  AuditEvent,
  RunSummary,
  RunDetail,
  PackSummary,
  PackDetail,
  LogosPackSummary,
  LogosPackOverview,
  LogosSafetyReport,
  LogosPackContents,
  LogosAlignmentRow,
  VaultSummary,
  VaultEntry,
  VaultRecall,
  CalibrationClass,
  ServingMetrics,
  CognitivePipelineRecord,
  FieldEvidence,
  EvidenceBundle,
  DeterminismTour,
  LivedLife,
  TurnJournalEntry,
  TurnJournalSummary,
  EvalLaneSummary,
  EvalRunResult,
  ChatTurnResult,
  EvalRunRequest,
  TurnReplayComparison,
  ContemplationRunDetail,
  ContemplationRunSummary,
  MathProposalSummary,
  MathProposalDetail,
  MathRatifyResult,
} from "../types/api";
import type { ConstructionEvidence } from "../types/constructionEvidence";
import type { PracticeEvidence } from "../types/practiceEvidence";



export { QueryClientProvider };

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5000,
      refetchOnWindowFocus: false,
    },
  },
});

export function useRuntimeStatus() {
  return useQuery<RuntimeStatus>({
    queryKey: ["api", "runtime-status"],
    queryFn: () => apiFetch<RuntimeStatus>("/runtime/status"),
    refetchInterval: 30_000,
  });
}

export function useHealth() {
  // Liveness probe — polled faster than runtime status and isolated from it so
  // a healthy server still reads green even if /runtime/status is degraded.
  return useQuery<HealthStatus, WorkbenchApiError>({
    queryKey: ["api", "health"],
    queryFn: fetchHealth,
    refetchInterval: 15_000,
    retry: false,
  });
}

export function useArtifacts() {
  return useQuery<ArtifactRef[], WorkbenchApiError>({
    queryKey: ["api", "artifacts"],
    queryFn: () => fetchArtifacts(),
    staleTime: 60000,
    refetchOnWindowFocus: false,
  });
}

export function useArtifact(id: string) {
  return useQuery<ArtifactDetail, WorkbenchApiError>({
    queryKey: ["api", "artifact", id],
    queryFn: () => fetchArtifactDetail(id),
    enabled: !!id,
  });
}

export function useArtifactDetail(artifactId: string) {
  return useQuery<ArtifactDetail, WorkbenchApiError>({
    queryKey: ["api", "artifact", artifactId],
    queryFn: () => fetchArtifactDetail(artifactId),
    enabled: !!artifactId,
  });
}

export function useTurnReplay(turnId?: number | null) {
  return useQuery<TurnReplayComparison, WorkbenchApiError>({
    queryKey: ["api", "replay", "turn", turnId ?? null],
    queryFn: () => fetchTurnReplay(turnId as number),
    enabled: typeof turnId === "number",
    retry: false,
    staleTime: 30_000,
    refetchOnWindowFocus: false,
  });
}

export function useDemos() {
  return useQuery<DemoSummary[], WorkbenchApiError>({
    queryKey: ["api", "demos"],
    queryFn: fetchDemos,
    staleTime: 60_000,
    refetchOnWindowFocus: false,
  });
}

export function useDemoRun() {
  return useMutation<DemoRunResult, WorkbenchApiError, { demoId: string }>({
    mutationKey: ["demo-run"],
    mutationFn: ({ demoId }) => runDemo(demoId),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["api", "demo-run", variables.demoId] });
    },
  });
}

export function useContemplationRuns(limit?: number, offset?: number) {
  return useQuery<ContemplationRunSummary[], WorkbenchApiError>({
    queryKey: ["api", "contemplation", "runs", limit ?? null, offset ?? null],
    queryFn: () => fetchContemplationRuns(limit, offset),
    staleTime: 30_000,
    refetchOnWindowFocus: false,
  });
}

export function useContemplationRun(runId?: string | null) {
  return useQuery<ContemplationRunDetail, WorkbenchApiError>({
    queryKey: ["api", "contemplation", "run", runId ?? null],
    queryFn: () => fetchContemplationRun(runId as string),
    enabled: typeof runId === "string" && runId.length > 0,
    staleTime: 30_000,
    refetchOnWindowFocus: false,
  });
}

export function useProposals(filter: ProposalStateFilter = "all") {
  return useQuery<ProposalSummary[]>({
    queryKey: ["api", "proposals", filter],
    queryFn: () => fetchProposals(filter),
    staleTime: 30_000,
    refetchOnWindowFocus: false,
  });
}

export function useProposalDetail(proposalId: string) {
  return useQuery<ProposalDetail>({
    queryKey: ["api", "proposal", proposalId],
    queryFn: () => fetchProposalDetail(proposalId),
    enabled: !!proposalId,
    staleTime: 30_000,
    refetchOnWindowFocus: false,
  });
}

export function useTraceTurns(limit?: number, offset?: number) {
  return useQuery<TurnJournalSummary[], WorkbenchApiError>({
    queryKey: ["api", "trace", "turns", limit ?? null, offset ?? null],
    queryFn: () => fetchTraceTurns(limit, offset),
    staleTime: 30_000,
    refetchOnWindowFocus: false,
  });
}

export function useTraceTurn(turnId?: number | null) {
  return useQuery<TurnJournalEntry, WorkbenchApiError>({
    queryKey: ["api", "trace", "turn", turnId ?? null],
    queryFn: () => fetchTraceTurn(turnId as number),
    enabled: typeof turnId === "number",
    staleTime: 30_000,
    refetchOnWindowFocus: false,
  });
}

export function useTracePipeline(turnId?: number | null) {
  return useQuery<CognitivePipelineRecord, WorkbenchApiError>({
    queryKey: ["api", "trace", "pipeline", turnId ?? null],
    queryFn: () => fetchTracePipeline(turnId as number),
    enabled: typeof turnId === "number",
    staleTime: 30_000,
    refetchOnWindowFocus: false,
  });
}

export function useTraceField(turnId?: number | null) {
  return useQuery<FieldEvidence, WorkbenchApiError>({
    queryKey: ["api", "trace", "field", turnId ?? null],
    queryFn: () => fetchTraceField(turnId as number),
    enabled: typeof turnId === "number",
    staleTime: 30_000,
    refetchOnWindowFocus: false,
  });
}

export function useTraceBundle(turnId?: number | null) {
  return useQuery<EvidenceBundle, WorkbenchApiError>({
    queryKey: ["api", "trace", "bundle", turnId ?? null],
    queryFn: () => fetchTraceBundle(turnId as number),
    enabled: typeof turnId === "number",
    staleTime: 30_000,
    refetchOnWindowFocus: false,
  });
}

export function useTraceConstruction(turnId?: number | null) {
  return useQuery<ConstructionEvidence, WorkbenchApiError>({
    queryKey: ["api", "trace", "construction", turnId ?? null],
    queryFn: () => fetchTraceConstruction(turnId as number),
    enabled: typeof turnId === "number",
    staleTime: 30_000,
    refetchOnWindowFocus: false,
  });
}

export function useTracePractice(turnId?: number | null) {
  return useQuery<PracticeEvidence, WorkbenchApiError>({
    queryKey: ["api", "trace", "practice", turnId ?? null],
    queryFn: () => fetchTracePractice(turnId as number),
    enabled: typeof turnId === "number",
    staleTime: 30_000,
    refetchOnWindowFocus: false,
  });
}



export function useTour() {
  return useQuery<DeterminismTour, WorkbenchApiError>({
    queryKey: ["api", "tour"],
    queryFn: fetchTour,
    staleTime: 60_000,
    refetchOnWindowFocus: false,
  });
}

export function useLivedLife() {
  return useQuery<LivedLife, WorkbenchApiError>({
    queryKey: ["api", "lived-life"],
    queryFn: fetchLivedLife,
    // The life advances over uptime — keep it fresh without hammering.
    refetchInterval: 30_000,
    refetchOnWindowFocus: false,
  });
}

export function useAuditEvents(limit?: number, offset?: number) {
  return useQuery<{ items: AuditEvent[] }, WorkbenchApiError>({
    queryKey: ["api", "audit", "events", limit ?? null, offset ?? null],
    queryFn: () => fetchAuditEvents(limit, offset),
    staleTime: 30_000,
    refetchOnWindowFocus: false,
  });
}

export function useRuns(limit?: number, offset?: number) {
  return useQuery<RunSummary[], WorkbenchApiError>({
    queryKey: ["api", "runs", limit ?? null, offset ?? null],
    queryFn: () => fetchRuns(limit, offset),
    staleTime: 30_000,
    refetchOnWindowFocus: false,
  });
}

export function useRun(sessionId?: string | null, turnLimit?: number) {
  return useQuery<RunDetail, WorkbenchApiError>({
    queryKey: ["api", "run", sessionId ?? null, turnLimit ?? null],
    queryFn: () => fetchRun(sessionId as string, turnLimit),
    enabled: typeof sessionId === "string" && sessionId.length > 0,
    staleTime: 30_000,
    refetchOnWindowFocus: false,
  });
}

export function useEvalLanes() {
  return useQuery<EvalLaneSummary[]>({
    queryKey: ["api", "evals"],
    queryFn: fetchEvalLanes,
    staleTime: 60_000,
    refetchOnWindowFocus: false,
  });
}

export function useEvalLane(name: string) {
  return useQuery<EvalRunResult>({
    queryKey: ["api", "eval", name],
    queryFn: () => apiFetch<EvalRunResult>(`/evals/${name}`),
    enabled: !!name,
  });
}

export function useEvalRun() {
  return useMutation<EvalRunResult, WorkbenchApiError, EvalRunRequest>({
    mutationKey: ["eval-run"],
    mutationFn: runEvalLane,
  });
}

export function useChatTurn() {
  return useMutation<ChatTurnResult, WorkbenchApiError, { prompt: string }>({
    mutationKey: ["chat-turn"],
    mutationFn: ({ prompt }) =>
      apiFetch<ChatTurnResult>("/chat/turn", {
        method: "POST",
        body: JSON.stringify({ prompt }),
        headers: { "Content-Type": "application/json" },
      }),
  });
}

export function useMathProposals() {
  return useQuery<MathProposalSummary[]>({
    queryKey: ["api", "math-proposals"],
    queryFn: fetchMathProposals,
    staleTime: 30_000,
    refetchOnWindowFocus: false,
  });
}

export function useMathProposalDetail(proposalId: string) {
  return useQuery<MathProposalDetail>({
    queryKey: ["api", "math-proposal", proposalId],
    queryFn: () => fetchMathProposalDetail(proposalId),
    enabled: !!proposalId,
    staleTime: 30_000,
    refetchOnWindowFocus: false,
  });
}

export function useMathRatify() {
  return useMutation<
    MathRatifyResult,
    WorkbenchApiError,
    { proposalId: string; category?: string; polarity?: string; dryRun?: boolean }
  >({
    mutationKey: ["math-ratify"],
    mutationFn: ({ proposalId, category, polarity, dryRun }) =>
      ratifyMathProposal(proposalId, category, polarity, dryRun),
    onSuccess: (data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["api", "proposals"] });
      queryClient.invalidateQueries({ queryKey: ["api", "math-proposals"] });
      queryClient.invalidateQueries({ queryKey: ["api", "proposal", variables.proposalId] });
      queryClient.invalidateQueries({ queryKey: ["api", "math-proposal", variables.proposalId] });
    },
  });
}

export function useMathReject() {
  return useMutation<
    { proposal_id: string; rejected: boolean },
    WorkbenchApiError,
    { proposalId: string; note?: string }
  >({
    mutationKey: ["math-reject"],
    mutationFn: ({ proposalId, note }) => rejectMathProposal(proposalId, note),
    onSuccess: (data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["api", "proposals"] });
      queryClient.invalidateQueries({ queryKey: ["api", "math-proposals"] });
      queryClient.invalidateQueries({ queryKey: ["api", "proposal", variables.proposalId] });
      queryClient.invalidateQueries({ queryKey: ["api", "math-proposal", variables.proposalId] });
    },
  });
}

export function useMathDefer() {
  return useMutation<
    { proposal_id: string; deferred: boolean },
    WorkbenchApiError,
    { proposalId: string }
  >({
    mutationKey: ["math-defer"],
    mutationFn: ({ proposalId }) => deferMathProposal(proposalId),
    onSuccess: (data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["api", "proposals"] });
      queryClient.invalidateQueries({ queryKey: ["api", "math-proposals"] });
      queryClient.invalidateQueries({ queryKey: ["api", "proposal", variables.proposalId] });
      queryClient.invalidateQueries({ queryKey: ["api", "math-proposal", variables.proposalId] });
    },
  });
}

export function usePacks(limit?: number, offset?: number) {
  return useQuery<PackSummary[], WorkbenchApiError>({
    queryKey: ["api", "packs", limit ?? null, offset ?? null],
    queryFn: () => fetchPacks(limit, offset),
    staleTime: 30_000,
    refetchOnWindowFocus: false,
  });
}

export function usePack(packId?: string | null) {
  return useQuery<PackDetail, WorkbenchApiError>({
    queryKey: ["api", "pack", packId ?? null],
    queryFn: () => fetchPack(packId as string),
    enabled: typeof packId === "string" && packId.length > 0,
    staleTime: 30_000,
    refetchOnWindowFocus: false,
  });
}

export function useLogosPacks() {
  return useQuery<LogosPackSummary[], WorkbenchApiError>({
    queryKey: ["api", "logos", "packs"],
    queryFn: fetchLogosPacks,
    staleTime: 30_000,
    refetchOnWindowFocus: false,
  });
}

export function useLogosPackOverview(packId?: string | null) {
  return useQuery<LogosPackOverview, WorkbenchApiError>({
    queryKey: ["api", "logos", "pack", packId ?? null],
    queryFn: () => fetchLogosPackOverview(packId as string),
    enabled: typeof packId === "string" && packId.length > 0,
    staleTime: 30_000,
    refetchOnWindowFocus: false,
  });
}

export function useLogosPackSafety(packId?: string | null) {
  return useQuery<LogosSafetyReport, WorkbenchApiError>({
    queryKey: ["api", "logos", "pack", packId ?? null, "safety"],
    queryFn: () => fetchLogosPackSafety(packId as string),
    enabled: typeof packId === "string" && packId.length > 0,
    staleTime: 30_000,
    refetchOnWindowFocus: false,
  });
}

export function useLogosPackContents(packId?: string | null) {
  return useQuery<LogosPackContents, WorkbenchApiError>({
    queryKey: ["api", "logos", "pack", packId ?? null, "contents"],
    queryFn: () => fetchLogosPackContents(packId as string),
    enabled: typeof packId === "string" && packId.length > 0,
    staleTime: 30_000,
    refetchOnWindowFocus: false,
  });
}

export function useLogosPackAlignment(packId?: string | null) {
  return useQuery<LogosAlignmentRow[], WorkbenchApiError>({
    queryKey: ["api", "logos", "pack", packId ?? null, "alignment"],
    queryFn: () => fetchLogosPackAlignment(packId as string),
    enabled: typeof packId === "string" && packId.length > 0,
    staleTime: 30_000,
    refetchOnWindowFocus: false,
  });
}

export function useVaultSummary() {
  return useQuery<VaultSummary, WorkbenchApiError>({
    queryKey: ["api", "vault", "summary"],
    queryFn: () => fetchVaultSummary(),
    retry: false,
    staleTime: 30_000,
    refetchOnWindowFocus: false,
  });
}

export function useVaultEntries(enabled: boolean, limit?: number, offset?: number) {
  return useQuery<VaultEntry[], WorkbenchApiError>({
    queryKey: ["api", "vault", "entries", limit ?? null, offset ?? null],
    queryFn: () => fetchVaultEntries(limit, offset),
    enabled,
    retry: false,
    staleTime: 30_000,
    refetchOnWindowFocus: false,
  });
}

export function useVaultEntryRecall(entryIndex?: number | null) {
  return useQuery<VaultRecall, WorkbenchApiError>({
    queryKey: ["api", "vault", "recall", entryIndex ?? null],
    queryFn: () => fetchVaultEntryRecall(entryIndex as number),
    enabled: typeof entryIndex === "number",
    retry: false,
    staleTime: 30_000,
    refetchOnWindowFocus: false,
  });
}

export function useCalibrationClasses() {
  return useQuery<CalibrationClass[], WorkbenchApiError>({
    queryKey: ["api", "calibration", "classes"],
    queryFn: () => fetchCalibrationClasses(),
    retry: false,
    staleTime: 30_000,
    refetchOnWindowFocus: false,
  });
}

export function useServingMetrics() {
  return useQuery<ServingMetrics[], WorkbenchApiError>({
    queryKey: ["api", "serving", "metrics"],
    queryFn: () => fetchServingMetrics(),
    retry: false,
    staleTime: 30_000,
    refetchOnWindowFocus: false,
  });
}
