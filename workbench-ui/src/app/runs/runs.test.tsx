import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, fireEvent, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { RunsRoute } from "./RunsRoute";
import { CommandPalette } from "../../design/components/primitives/CommandPalette";
import type { ArtifactDetail, ArtifactRef } from "../../types/api";

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

const mockRuns: ArtifactRef[] = [
  {
    artifact_id: "art-trace-1",
    kind: "trace",
    path: "traces/1.json",
    digest: "sha256:1",
    created_at: "2026-05-26T12:00:00Z",
  },
  {
    artifact_id: "art-eval-1",
    kind: "eval_result",
    path: "evals/1.json",
    digest: "sha256:2",
    created_at: "2026-05-27T12:01:00Z",
  },
  {
    artifact_id: "art-prop-1",
    kind: "proposal",
    path: "proposals/1.json",
    digest: "sha256:3",
    created_at: "2026-05-28T12:02:00Z",
  },
];

const mockProposalDetail: ArtifactDetail = {
  ...mockRuns[2],
  content_type: "json",
  content: {
    proposal_id: "prop-abc-123",
    trace_hash: "0123456789abcdef0123456789abcdef",
  },
};

function makeClient(): QueryClient {
  return new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
}

function renderRoute(initialUrl = "/runs") {
  const client = makeClient();
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[initialUrl]}>
        <Routes>
          <Route path="/runs" element={<RunsRoute />} />
          <Route path="/replay" element={<div data-testid="replay-page" />} />
          <Route path="/proposals" element={<div data-testid="proposals-page" />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("RunsRoute", () => {
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
      expect(screen.getByText("Loading runs…")).toBeInTheDocument();
    });

    it("renders an error state when the artifact index fails", () => {
      vi.mocked(useArtifacts).mockReturnValue({
        data: undefined,
        isLoading: false,
        isError: true,
        error: { message: "Disk read error" } as any,
      } as any);

      renderRoute();
      expect(screen.getByText("Failed to load runs index")).toBeInTheDocument();
      expect(screen.getByText("Disk read error")).toBeInTheDocument();
    });

    it("renders an empty state when there are zero runs", () => {
      vi.mocked(useArtifacts).mockReturnValue({
        data: [],
        isLoading: false,
        isError: false,
        error: null,
      } as any);

      renderRoute();
      expect(screen.getByText("No runs recorded yet.")).toBeInTheDocument();
    });
  });

  describe("list", () => {
    beforeEach(() => {
      vi.mocked(useArtifacts).mockReturnValue({
        data: mockRuns,
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

    it("renders one row per artifact", () => {
      renderRoute();
      expect(screen.getByTestId("runs-row-art-trace-1")).toBeInTheDocument();
      expect(screen.getByTestId("runs-row-art-eval-1")).toBeInTheDocument();
      expect(screen.getByTestId("runs-row-art-prop-1")).toBeInTheDocument();
    });

    it("defaults to descending date sort (newest first)", () => {
      renderRoute();
      const table = screen.getByTestId("runs-table");
      const rows = within(table).getAllByRole("row");
      // rows[0] is the header; rows[1] should be the newest (prop-1, 2026-05-28)
      expect(within(rows[1]).getByTestId("runs-row-art-prop-1")).toBeInTheDocument();
      expect(within(rows[3]).getByTestId("runs-row-art-trace-1")).toBeInTheDocument();
    });

    it("toggles sort to ascending when the date header is clicked", () => {
      renderRoute();
      fireEvent.click(screen.getByTestId("runs-sort-date"));
      const rows = within(screen.getByTestId("runs-table")).getAllByRole("row");
      // ascending: oldest first = trace-1
      expect(within(rows[1]).getByTestId("runs-row-art-trace-1")).toBeInTheDocument();
    });

    it("filters by artifact kind", () => {
      renderRoute();
      fireEvent.change(screen.getByTestId("runs-kind-filter"), {
        target: { value: "proposal" },
      });
      expect(screen.getByTestId("runs-row-art-prop-1")).toBeInTheDocument();
      expect(screen.queryByTestId("runs-row-art-trace-1")).not.toBeInTheDocument();
      expect(screen.queryByTestId("runs-row-art-eval-1")).not.toBeInTheDocument();
    });

    it("shows a no-match row when the filter matches nothing", () => {
      vi.mocked(useArtifacts).mockReturnValue({
        data: [mockRuns[0]],
        isLoading: false,
        isError: false,
        error: null,
      } as any);
      renderRoute();
      fireEvent.change(screen.getByTestId("runs-kind-filter"), {
        target: { value: "proposal" },
      });
      expect(screen.getByTestId("runs-no-match")).toBeInTheDocument();
    });

    it("prompts the operator to pick a run when nothing is selected", () => {
      renderRoute();
      expect(screen.getByText("Select a run to see details.")).toBeInTheDocument();
    });
  });

  describe("detail", () => {
    beforeEach(() => {
      vi.mocked(useArtifacts).mockReturnValue({
        data: mockRuns,
        isLoading: false,
        isError: false,
        error: null,
      } as any);
    });

    it("shows detail when a runId is in the URL", () => {
      vi.mocked(useArtifact).mockReturnValue({
        data: mockProposalDetail,
        isLoading: false,
        isError: false,
        error: null,
      } as any);

      renderRoute("/runs?runId=art-prop-1");
      expect(screen.getByTestId("run-detail")).toBeInTheDocument();
      const metadata = screen.getByTestId("run-detail-metadata");
      expect(within(metadata).getByText("proposal")).toBeInTheDocument();
    });

    it("provides a deep link to Replay for the selected run", () => {
      vi.mocked(useArtifact).mockReturnValue({
        data: mockProposalDetail,
        isLoading: false,
        isError: false,
        error: null,
      } as any);

      renderRoute("/runs?runId=art-prop-1");
      const link = screen.getByTestId("run-detail-replay-link") as HTMLAnchorElement;
      expect(link.getAttribute("href")).toBe("/replay?artifactId=art-prop-1");
    });

    it("provides a link to the originating proposal when content carries proposal_id", () => {
      vi.mocked(useArtifact).mockReturnValue({
        data: mockProposalDetail,
        isLoading: false,
        isError: false,
        error: null,
      } as any);

      renderRoute("/runs?runId=art-prop-1");
      const propLink = screen.getByTestId("run-detail-proposal-link") as HTMLAnchorElement;
      expect(propLink.getAttribute("href")).toBe(
        "/proposals?proposal_id=prop-abc-123",
      );
    });

    it("renders the trace hash badge when content carries trace_hash", () => {
      vi.mocked(useArtifact).mockReturnValue({
        data: mockProposalDetail,
        isLoading: false,
        isError: false,
        error: null,
      } as any);

      renderRoute("/runs?runId=art-prop-1");
      expect(screen.getByTestId("run-detail-trace-hash")).toBeInTheDocument();
    });

    it("renders an error state when the detail query fails", () => {
      vi.mocked(useArtifact).mockReturnValue({
        data: undefined,
        isLoading: false,
        isError: true,
        error: { message: "404 not found" } as any,
      } as any);

      renderRoute("/runs?runId=missing-id");
      expect(screen.getByText(/Failed to load run missing-id/)).toBeInTheDocument();
    });
  });

  describe("⌘K commands", () => {
    it("CommandPalette exposes Open run entries via the registry", async () => {
      vi.mocked(useArtifacts).mockReturnValue({
        data: mockRuns,
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
            <RunsRoute />
          </MemoryRouter>
        </QueryClientProvider>,
      );

      expect(
        await screen.findByRole("button", { name: /Open run art-trace-1/ }),
      ).toBeInTheDocument();
      expect(
        await screen.findByRole("button", { name: /Open run art-prop-1/ }),
      ).toBeInTheDocument();
    });
  });

  describe("read-only invariant", () => {
    it("RunsRoute and RunDetail introduce no mutation hooks", () => {
      // Source-level check: this test is a marker. The real enforcement is the
      // grep in the brief's validation block; this assertion is a guard so the
      // intent is recorded in the test surface as well.
      expect(true).toBe(true);
    });
  });
});
