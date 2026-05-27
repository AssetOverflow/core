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

export function useProposals() {
  return useQuery<ProposalSummary[]>({
    queryKey: ["api", "proposals"],
    queryFn: () => apiFetch<ProposalSummary[]>("/proposals"),
  });
}

export function useProposal(id: string) {
  return useQuery<ProposalDetail>({
    queryKey: ["api", "proposal", id],
    queryFn: () => apiFetch<ProposalDetail>(`/proposals/${id}`),
    enabled: !!id,
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

