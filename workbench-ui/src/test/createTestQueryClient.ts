import { QueryClient } from "@tanstack/react-query";

/**
 * QueryClient for tests.
 *
 * `gcTime: 0` is load-bearing: TanStack Query v5 defaults to 5 minutes,
 * which schedules a garbage-collection timer per cached query. Those live
 * timers keep vitest workers from exiting at teardown — the root cause of
 * the full-suite hang diagnosed 2026-06-12 (Wave R brief R0a).
 */
export function createTestQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
      mutations: { retry: false, gcTime: 0 },
    },
  });
}
