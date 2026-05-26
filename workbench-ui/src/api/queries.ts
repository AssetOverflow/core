import {
  QueryClient,
  useQuery,
  useMutation,
  QueryClientProvider,
} from "@tanstack/react-query";
import { apiFetch } from "./client";
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

export function useArtifacts(limit?: number) {
  const params = limit !== undefined ? `?limit=${limit}` : "";
  return useQuery<ArtifactRef[]>({
    queryKey: ["api", "artifacts", limit],
    queryFn: () => apiFetch<ArtifactRef[]>(`/artifacts${params}`),
  });
}

export function useArtifact(id: string) {
  return useQuery<ArtifactDetail>({
    queryKey: ["api", "artifact", id],
    queryFn: () => apiFetch<ArtifactDetail>(`/artifacts/${id}`),
    enabled: !!id,
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
    queryFn: () => apiFetch<EvalLaneSummary[]>("/evals"),
  });
}

export function useEvalLane(name: string) {
  return useQuery<EvalRunResult>({
    queryKey: ["api", "eval", name],
    queryFn: () => apiFetch<EvalRunResult>(`/evals/${name}`),
    enabled: !!name,
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
