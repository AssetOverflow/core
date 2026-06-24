import type { PracticeEvidence } from "../../types/practiceEvidence";

export function tracePracticePath(turnId: number): string {
  return `/trace/${encodeURIComponent(String(turnId))}/practice`;
}

export async function fetchTracePracticeWith(
  turnId: number,
  fetcher: <T>(path: string) => Promise<T>,
): Promise<PracticeEvidence> {
  return fetcher<PracticeEvidence>(tracePracticePath(turnId));
}

export const TRACE_PRACTICE_LOADING_LABEL = "Loading sealed practice evidence...";
export const TRACE_PRACTICE_EMPTY_LABEL = "No sealed practice evidence recorded for this turn.";
export const TRACE_PRACTICE_ERROR_MUTATION_STATUS = "No trace mutation occurred.";

export function tracePracticeReproducer(turnId: number): string {
  return `curl /trace/${encodeURIComponent(String(turnId))}/practice`;
}
