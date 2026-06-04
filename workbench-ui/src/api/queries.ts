import {
  QueryClient,
  useQuery,
  useMutation,
  QueryClientProvider,
} from "@tanstack/react-query";
import {
  apiFetch,
  fetchEvalLanes,
  runEvalLane,
  fetchArtifacts,
  fetchArtifactDetail,
  fetchReplayComparison,
  fetchProposalDetail,
  fetchProposals,
  fetchMathProposals,
  fetchMathProposalDetail,
  ratifyMathProposal,
  rejectMathProposal,
  deferMathProposal,
  type ProposalStateFilter,
} from "./client";
import type { WorkbenchApiError } from "./client";
import type {
  RuntimeStatus,
  ArtifactRef,
  ArtifactDetail,
  ProposalSummary,
  ProposalDetail,
  EvalLaneSummary,
  EvalRunResult,
  ChatTurnResult,
  EvalRunRequest,
  ReplayComparison,
  MathProposalSummary,
  MathProposalDetail,
  MathRatifyResult,
} from "../types/api";

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

export function useReplayComparison(artifactId: string) {
  return useQuery<ReplayComparison, WorkbenchApiError>({
    queryKey: ["api", "replay", artifactId],
    queryFn: () => fetchReplayComparison(artifactId),
    enabled: !!artifactId,
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



