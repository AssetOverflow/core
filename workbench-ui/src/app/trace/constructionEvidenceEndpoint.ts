import type { ConstructionEvidence } from "../../types/constructionEvidence";

export function traceConstructionPath(turnId: number): string {
  return `/trace/${encodeURIComponent(String(turnId))}/construction`;
}

export async function fetchTraceConstructionWith(
  turnId: number,
  fetcher: <T>(path: string) => Promise<T>,
): Promise<ConstructionEvidence> {
  return fetcher<ConstructionEvidence>(traceConstructionPath(turnId));
}

export const TRACE_CONSTRUCTION_LOADING_LABEL = "Loading construction evidence...";
export const TRACE_CONSTRUCTION_EMPTY_LABEL = "No construction evidence recorded for this turn.";
export const TRACE_CONSTRUCTION_ERROR_MUTATION_STATUS = "No trace mutation occurred.";

export function traceConstructionReproducer(turnId: number): string {
  return `curl /trace/${encodeURIComponent(String(turnId))}/construction`;
}
