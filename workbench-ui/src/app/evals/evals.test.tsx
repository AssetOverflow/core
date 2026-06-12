import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { QueryClientProvider } from "@tanstack/react-query";
import { createTestQueryClient } from "../../test/createTestQueryClient";
import { EvalLaneCard } from "./EvalLaneCard";
import { EvalRunButton } from "./EvalRunButton";
import { EvalMetricGrid } from "./EvalMetricGrid";
import { EvalFailureViewer } from "./EvalFailureViewer";
import { EvalsRoute } from "./EvalsRoute";
import { runEvalLane, WorkbenchApiError } from "../../api/client";
import type { EvalLaneSummary, EvalRunResult } from "../../types/api";

// Mock queries
vi.mock("../../api/queries", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../api/queries")>();
  return {
    ...actual,
    useEvalLanes: vi.fn(),
    useEvalRun: vi.fn(),
  };
});

import { useEvalLanes, useEvalRun } from "../../api/queries";

const mockLanes: EvalLaneSummary[] = [
  { lane: "contemplation_quality", versions: ["v1", "v2"], read_only: true, description: "Contemplation checks" },
  { lane: "unsafe_lane", versions: ["v1"], read_only: false, description: "Unsafe checks" },
];

const mockResult: EvalRunResult = {
  lane: "contemplation_quality",
  version: "v1",
  split: "public",
  passed: false,
  metrics: { accuracy: 0.8, passed: 4, total: 5 },
  cases: [
    { case_id: "c1", passed: true },
    { case_id: "c2", passed: false, expected: "val1", actual: "val2", failure_reason: "Mismatch value" },
  ],
  source_digest: "abcdef1234567890",
};

function makeClient() {
  return createTestQueryClient();
}

describe("W-030 Component Tests", () => {
  const fetchMock = vi.fn();

  beforeEach(() => {
    vi.resetAllMocks();
    fetchMock.mockImplementation((url: any) => {
      const urlStr = typeof url === "string" ? url : String(url?.url || url || "");
      if (urlStr.endsWith("/evals")) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ ok: true, generated_at: "2026-05-26T00:00:00Z", data: mockLanes }),
        });
      }
      if (urlStr.endsWith("/evals/run")) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ ok: true, generated_at: "2026-05-26T00:00:00Z", data: mockResult }),
        });
      }
      return Promise.reject(new Error(`Unhandled URL: ${urlStr}`));
    });
    vi.stubGlobal("fetch", fetchMock);
    if (typeof window !== "undefined") {
      delete (window as any).sealedEvalConfig;
    }
  });

  // 1. EvalLaneCard
  describe("EvalLaneCard", () => {
    it("renders read_only badge correctly for both values; clicking selects via callback", () => {
      const selectSpy = vi.fn();
      
      // Test read_only === true
      const { rerender } = render(
        <EvalLaneCard lane={mockLanes[0]} isSelected={false} onSelect={selectSpy} />
      );
      expect(screen.getByText("Read-Only")).toBeInTheDocument();
      
      // Click selects via callback
      fireEvent.click(screen.getByTestId("eval-lane-card"));
      expect(selectSpy).toHaveBeenCalledTimes(1);

      // Test read_only === false
      rerender(<EvalLaneCard lane={mockLanes[1]} isSelected={false} onSelect={selectSpy} />);
      expect(screen.getByText("CLI-Only")).toBeInTheDocument();
      expect(screen.getByTitle("API run disabled — use CLI")).toBeInTheDocument();
    });
  });

  // 2. EvalRunButton
  describe("EvalRunButton", () => {
    it("hidden when lane.read_only === false; visible but holdout-disabled with correct hover-text otherwise", () => {
      // Mock useEvalRun mutation
      vi.mocked(useEvalRun).mockReturnValue({
        mutate: vi.fn(),
        isPending: false,
        isError: false,
        isSuccess: false,
        error: null,
      } as any);

      const runStartSpy = vi.fn();
      const runSuccessSpy = vi.fn();
      const runErrorSpy = vi.fn();

      // Non-read-only lane -> should be null
      const { rerender } = render(
        <EvalRunButton
          lane={mockLanes[1]}
          onRunStart={runStartSpy}
          onRunSuccess={runSuccessSpy}
          onRunError={runErrorSpy}
        />
      );
      expect(screen.queryByTestId("eval-run-form")).not.toBeInTheDocument();

      // Read-only lane -> should render, holdout disabled
      rerender(
        <EvalRunButton
          lane={mockLanes[0]}
          onRunStart={runStartSpy}
          onRunSuccess={runSuccessSpy}
          onRunError={runErrorSpy}
        />
      );
      expect(screen.getByTestId("eval-run-form")).toBeInTheDocument();
      const holdoutOption = screen.getByRole("option", { name: "Holdout" }) as HTMLOptionElement;
      expect(holdoutOption).toBeDisabled();
      expect(holdoutOption.getAttribute("title")).toBe("Holdout runs require sealed-eval config — use CLI");
    });
  });

  // 3. EvalMetricGrid
  describe("EvalMetricGrid", () => {
    it("enforces deterministic key ordering across two identical runs", () => {
      const metricsRun1 = {
        total: 10,
        passed: 9,
        accuracy: 0.9,
        latency_ms: 150,
      };

      const metricsRun2 = {
        latency_ms: 150,
        accuracy: 0.9,
        passed: 9,
        total: 10,
      };

      const { container: container1, unmount: unmount1 } = render(<EvalMetricGrid metrics={metricsRun1} />);
      const cards1 = Array.from(container1.querySelectorAll('[data-testid="metric-card"]')).map(el => el.textContent);
      unmount1();

      const { container: container2 } = render(<EvalMetricGrid metrics={metricsRun2} />);
      const cards2 = Array.from(container2.querySelectorAll('[data-testid="metric-card"]')).map(el => el.textContent);

      // Verify lexicographical order
      expect(cards1).toEqual(cards2);
      expect(cards1[0]).toContain("accuracy");
      expect(cards1[1]).toContain("latency ms");
      expect(cards1[2]).toContain("passed");
      expect(cards1[3]).toContain("total");
    });
  });

  // 4. EvalFailureViewer
  describe("EvalFailureViewer", () => {
    it("renders calm-success EmptyState with 0 failures", () => {
      render(
        <EvalFailureViewer cases={[{ case_id: "c1", passed: true }]} passed={true} laneName="contemplation_quality" />
      );
      
      expect(screen.queryByTestId("eval-failures")).not.toBeInTheDocument();
      expect(screen.getByText("All checks passed for eval lane contemplation_quality.")).toBeInTheDocument();
    });

    it("renders failure cards with expected vs actual diff for failed cases", () => {
      render(
        <EvalFailureViewer
          cases={[
            { case_id: "c1", passed: true },
            { case_id: "c2", passed: false, expected: "val1", actual: "val2", failure_reason: "Wrong outcome" },
          ]}
          passed={false}
          laneName="contemplation_quality"
        />
      );

      expect(screen.getByText("Failures (1)")).toBeInTheDocument();
      expect(screen.getByText("c2")).toBeInTheDocument();
      expect(screen.getByText("Wrong outcome")).toBeInTheDocument();
      expect(screen.getByTestId("json-diff")).toBeInTheDocument();
    });
  });

  // 5. EvalsRoute
  describe("EvalsRoute", () => {
    it("full happy-path with selection, running and result viewing", async () => {
      // Mock useEvalLanes query
      vi.mocked(useEvalLanes).mockReturnValue({
        data: mockLanes,
        isLoading: false,
        isError: false,
        error: null,
      } as any);

      // Mock useEvalRun mutation
      let mutateCallback: any;
      vi.mocked(useEvalRun).mockReturnValue({
        mutate: vi.fn((req, options) => {
          mutateCallback = options;
        }),
        isPending: false,
        isError: false,
        isSuccess: false,
        error: null,
      } as any);

      const client = makeClient();
      render(
        <QueryClientProvider client={client}>
          <MemoryRouter initialEntries={["/evals?lane=contemplation_quality"]}>
            <EvalsRoute />
          </MemoryRouter>
        </QueryClientProvider>
      );

      // Verify lane details are shown
      expect(screen.getByText("contemplation_quality", { selector: "h2" })).toBeInTheDocument();
      expect(screen.getByTestId("run-button")).toBeInTheDocument();

      // Trigger run
      fireEvent.click(screen.getByTestId("run-button"));
      
      // Simulate success
      expect(mutateCallback).toBeDefined();
      mutateCallback.onSuccess(mockResult);

      // Result should be visible
      await waitFor(() => {
        expect(screen.getByText("Status:")).toBeInTheDocument();
      });
      expect(screen.getByText("accuracy")).toBeInTheDocument();
      expect(screen.getByText("Failures (1)")).toBeInTheDocument();
    });

    it("renders ErrorState when fetchEvalLanes fails", () => {
      vi.mocked(useEvalLanes).mockReturnValue({
        data: null,
        isLoading: false,
        isError: true,
        error: new Error("Network Error"),
      } as any);

      const client = makeClient();
      render(
        <QueryClientProvider client={client}>
          <MemoryRouter initialEntries={["/evals"]}>
            <EvalsRoute />
          </MemoryRouter>
        </QueryClientProvider>
      );

      expect(screen.getByText("Network Error")).toBeInTheDocument();
      expect(screen.getByText("Mutation status")).toBeInTheDocument();
    });

    it("verifies direct runEvalLane client-side refusal logic", async () => {
      // Refusal 1: lane.read_only === false
      await expect(
        runEvalLane({ lane: "unsafe_lane", split: "public" })
      ).rejects.toThrowError(
        new WorkbenchApiError("client_refused_unsafe_lane", "API run disabled — use CLI")
      );

      // Refusal 2: split === "holdout" without sealed config flag
      await expect(
        runEvalLane({ lane: "contemplation_quality", split: "holdout" })
      ).rejects.toThrowError(
        new WorkbenchApiError("client_refused_sealed_holdout", "Holdout runs require sealed-eval config — use CLI")
      );

      // Success: split === "holdout" with sealed config flag
      if (typeof window !== "undefined") {
        (window as any).sealedEvalConfig = true;
      }
      
      // Expect it to call fetch successfully without throwing refusals
      const res = await runEvalLane({ lane: "contemplation_quality", split: "holdout" });
      expect(res).toEqual(mockResult);
    });
  });
});
