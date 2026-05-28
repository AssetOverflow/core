import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { TraceRoute } from "./TraceRoute";
import { CommandPalette } from "../../design/components/primitives/CommandPalette";
import { parseTraceContent } from "./parseTraceContent";
import type { ArtifactDetail, ArtifactRef, ChatTurnResult } from "../../types/api";

vi.mock("../../api/queries", async () => {
  const actual = await vi.importActual<typeof import("../../api/queries")>(
    "../../api/queries",
  );
  return {
    ...actual,
    useArtifacts: vi.fn(),
    useArtifact: vi.fn(),
  };
});

import { useArtifacts, useArtifact } from "../../api/queries";

const TRACE_HASH = "0123456789abcdef0123456789abcdef";

const mockArtifacts: ArtifactRef[] = [
  {
    artifact_id: "art-trace-a",
    kind: "trace",
    path: "traces/a.json",
    digest: "sha256:a",
    created_at: "2026-05-27T12:00:00Z",
  },
  {
    artifact_id: "art-trace-b",
    kind: "trace",
    path: "traces/b.json",
    digest: "sha256:b",
    created_at: "2026-05-28T12:00:00Z",
  },
  {
    artifact_id: "art-eval-1",
    kind: "eval_result",
    path: "evals/1.json",
    digest: "sha256:e",
    created_at: "2026-05-28T13:00:00Z",
  },
];

const mockTraceContent: Record<string, unknown> = {
  prompt: "what is a versor",
  surface: "A versor is a Clifford-algebra element used for rotations.",
  articulation_surface: "A versor is a Clifford-algebra element used for rotations.",
  walk_surface: "[node_42 → node_88 → node_91]",
  grounding_source: "vault",
  epistemic_state: "evidenced",
  normative_clearance: "cleared",
  normative_detail: "",
  trace_hash: TRACE_HASH,
  refusal_emitted: false,
  hedge_injected: false,
  mutation_mode: "off",
  identity_verdict: { outcome: "cleared", runtime_detail: "ok" },
  safety_verdict: { outcome: "cleared", runtime_detail: "" },
  ethics_verdict: { outcome: "cleared", runtime_detail: "" },
  proposal_candidates: [
    { candidate_id: "cand-aaa", source_kind: "vault_recall" },
  ],
  turn_cost_ms: 12,
  checkpoint_emitted: false,
};

const mockTraceDetail: ArtifactDetail = {
  ...mockArtifacts[0],
  content_type: "json",
  content: mockTraceContent,
};

function makeClient(): QueryClient {
  return new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
}

function renderRoute(initialUrl = "/trace") {
  const client = makeClient();
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[initialUrl]}>
        <Routes>
          <Route path="/trace" element={<TraceRoute />} />
          <Route path="/replay" element={<div data-testid="replay-page" />} />
          <Route path="/proposals" element={<div data-testid="proposals-page" />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("TraceRoute", () => {
  beforeEach(() => {
    vi.mocked(useArtifacts).mockReset();
    vi.mocked(useArtifact).mockReset();
  });

  describe("states", () => {
    it("renders a loading state while artifacts are loading", () => {
      vi.mocked(useArtifacts).mockReturnValue({
        data: undefined,
        isLoading: true,
        isError: false,
        error: null,
      } as any);

      renderRoute();
      expect(screen.getByText("Loading traces…")).toBeInTheDocument();
    });

    it("renders an error state when the artifact index fails", () => {
      vi.mocked(useArtifacts).mockReturnValue({
        data: undefined,
        isLoading: false,
        isError: true,
        error: { message: "Network error" } as any,
      } as any);

      renderRoute();
      expect(screen.getByText("Failed to load trace index")).toBeInTheDocument();
      expect(screen.getByText("Network error")).toBeInTheDocument();
    });

    it("renders an empty state when there are no trace-kind artifacts", () => {
      vi.mocked(useArtifacts).mockReturnValue({
        data: [mockArtifacts[2]], // only eval_result
        isLoading: false,
        isError: false,
        error: null,
      } as any);

      renderRoute();
      expect(screen.getByText("No traces recorded yet.")).toBeInTheDocument();
    });
  });

  describe("list", () => {
    beforeEach(() => {
      vi.mocked(useArtifacts).mockReturnValue({
        data: mockArtifacts,
        isLoading: false,
        isError: false,
        error: null,
      } as any);
      vi.mocked(useArtifact).mockReturnValue({
        data: undefined,
        isLoading: true,
        isError: false,
        error: null,
      } as any);
    });

    it("filters out non-trace artifacts", () => {
      renderRoute();
      const list = screen.getByTestId("trace-list");
      expect(within(list).getByTestId("trace-list-art-trace-a")).toBeInTheDocument();
      expect(within(list).getByTestId("trace-list-art-trace-b")).toBeInTheDocument();
      expect(
        within(list).queryByTestId("trace-list-art-eval-1"),
      ).not.toBeInTheDocument();
    });

    it("sorts traces newest first", () => {
      renderRoute();
      const list = screen.getByTestId("trace-list");
      const buttons = within(list).getAllByRole("button");
      // First entry should be the newer trace (art-trace-b, 2026-05-28)
      expect(buttons[0]).toHaveAttribute("data-testid", "trace-list-art-trace-b");
    });

    it("prompts the operator to pick a session when nothing is selected", () => {
      renderRoute();
      expect(
        screen.getByText("Select a trace to inspect its surfaces."),
      ).toBeInTheDocument();
    });
  });

  describe("detail — three surfaces (addendum §2)", () => {
    beforeEach(() => {
      vi.mocked(useArtifacts).mockReturnValue({
        data: mockArtifacts,
        isLoading: false,
        isError: false,
        error: null,
      } as any);
      vi.mocked(useArtifact).mockReturnValue({
        data: mockTraceDetail,
        isLoading: false,
        isError: false,
        error: null,
      } as any);
    });

    it("renders all three surfaces as distinct elements", () => {
      renderRoute("/trace?traceId=art-trace-a");

      const surfaceBlock = screen.getByTestId("trace-surface-surface");
      const articulationBlock = screen.getByTestId("trace-surface-articulation");
      const walkBlock = screen.getByTestId("trace-surface-walk");

      // Three distinct DOM nodes
      expect(surfaceBlock).not.toBe(articulationBlock);
      expect(articulationBlock).not.toBe(walkBlock);

      // Each labeled with its name AND its role annotation
      expect(within(surfaceBlock).getByText("surface")).toBeInTheDocument();
      expect(within(surfaceBlock).getByText("user-facing response")).toBeInTheDocument();
      expect(
        within(articulationBlock).getByText("articulation_surface"),
      ).toBeInTheDocument();
      expect(within(articulationBlock).getByText("realizer output")).toBeInTheDocument();
      expect(within(walkBlock).getByText("walk_surface")).toBeInTheDocument();
      expect(within(walkBlock).getByText("manifold evidence")).toBeInTheDocument();
    });

    it("does not collapse identical surface and articulation_surface into one element", () => {
      // mockTraceContent has surface === articulation_surface; ensure UI still
      // renders BOTH distinctly per addendum §2
      renderRoute("/trace?traceId=art-trace-a");

      const surfaceBlock = screen.getByTestId("trace-surface-surface");
      const articulationBlock = screen.getByTestId("trace-surface-articulation");
      const surfaceText = mockTraceContent.surface as string;

      expect(within(surfaceBlock).getByText(surfaceText)).toBeInTheDocument();
      expect(within(articulationBlock).getByText(surfaceText)).toBeInTheDocument();
    });

    it("renders verdicts, grounding, proposal candidates, and trace hash sections", () => {
      renderRoute("/trace?traceId=art-trace-a");
      expect(screen.getByTestId("trace-grounding")).toBeInTheDocument();
      expect(screen.getByTestId("trace-verdicts")).toBeInTheDocument();
      expect(screen.getByTestId("trace-proposals")).toBeInTheDocument();
      expect(screen.getByTestId("trace-hash")).toBeInTheDocument();
    });

    it("links to Replay with the artifact id", () => {
      renderRoute("/trace?traceId=art-trace-a");
      const link = screen.getByTestId(
        "trace-detail-replay-link",
      ) as HTMLAnchorElement;
      expect(link.getAttribute("href")).toBe("/replay?artifactId=art-trace-a");
    });

    it("links each proposal candidate back to /proposals", () => {
      renderRoute("/trace?traceId=art-trace-a");
      const link = screen.getByTestId(
        "trace-proposal-link-cand-aaa",
      ) as HTMLAnchorElement;
      expect(link.getAttribute("href")).toBe("/proposals?proposal_id=cand-aaa");
    });

    it("renders the trace_hash via TraceHashBadge when present", () => {
      renderRoute("/trace?traceId=art-trace-a");
      const hashPanel = screen.getByTestId("trace-hash");
      // TraceHashBadge truncates to 12 chars by default
      expect(within(hashPanel).getByText(TRACE_HASH.slice(0, 12))).toBeInTheDocument();
    });

    it("renders an error state when the detail query fails", () => {
      vi.mocked(useArtifact).mockReturnValue({
        data: undefined,
        isLoading: false,
        isError: true,
        error: { message: "404 not found" } as any,
      } as any);

      renderRoute("/trace?traceId=missing");
      expect(screen.getByText(/Failed to load trace missing/)).toBeInTheDocument();
    });

    it("explains when an artifact cannot be parsed as a trace", () => {
      vi.mocked(useArtifact).mockReturnValue({
        data: {
          ...mockTraceDetail,
          content: { not_a_trace: true },
        },
        isLoading: false,
        isError: false,
        error: null,
      } as any);

      renderRoute("/trace?traceId=art-trace-a");
      expect(
        screen.getByText(/does not parse as a trace/),
      ).toBeInTheDocument();
    });
  });

  describe("trace_hash stability (addendum §2 proof obligation)", () => {
    it("mounting, selecting, and unmounting the trace route does not mutate the hash on input data", () => {
      // Snapshot the input artifact and content BEFORE rendering.
      const before = JSON.stringify(mockTraceContent);
      const inputHash = (mockTraceContent.trace_hash as string);

      vi.mocked(useArtifacts).mockReturnValue({
        data: mockArtifacts,
        isLoading: false,
        isError: false,
        error: null,
      } as any);
      vi.mocked(useArtifact).mockReturnValue({
        data: mockTraceDetail,
        isLoading: false,
        isError: false,
        error: null,
      } as any);

      // Mount the route at a deep link
      const { unmount, rerender } = renderRoute("/trace?traceId=art-trace-a");
      expect(screen.getByTestId("trace-detail")).toBeInTheDocument();

      // Re-render (simulate navigation refresh) and unmount
      rerender(
        <QueryClientProvider client={makeClient()}>
          <MemoryRouter initialEntries={["/trace?traceId=art-trace-a"]}>
            <Routes>
              <Route path="/trace" element={<TraceRoute />} />
            </Routes>
          </MemoryRouter>
        </QueryClientProvider>,
      );
      unmount();

      // The input artifact content must be byte-identical after the route's lifecycle.
      // The parsed-then-rendered ChatTurnResult must also carry the same trace_hash.
      expect(JSON.stringify(mockTraceContent)).toBe(before);
      const parsed: ChatTurnResult | null = parseTraceContent(mockTraceContent);
      expect(parsed).not.toBeNull();
      expect(parsed!.trace_hash).toBe(inputHash);
    });
  });

  describe("⌘K commands", () => {
    it("CommandPalette exposes Open trace entries via the registry", async () => {
      vi.mocked(useArtifacts).mockReturnValue({
        data: mockArtifacts,
        isLoading: false,
        isError: false,
        error: null,
      } as any);
      vi.mocked(useArtifact).mockReturnValue({
        data: undefined,
        isLoading: true,
        isError: false,
        error: null,
      } as any);

      const client = makeClient();
      render(
        <QueryClientProvider client={client}>
          <MemoryRouter>
            <CommandPalette open={true} onOpenChange={vi.fn()} />
            <TraceRoute />
          </MemoryRouter>
        </QueryClientProvider>,
      );

      expect(
        await screen.findByRole("button", { name: /Open trace art-trace-a/ }),
      ).toBeInTheDocument();
      expect(
        await screen.findByRole("button", { name: /Open trace art-trace-b/ }),
      ).toBeInTheDocument();
    });
  });
});
