import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useSearchParams } from "react-router-dom";
import { describe, expect, it, vi, afterEach } from "vitest";
import { ArtifactList } from "./ArtifactList";
import { ReplayStatusBadge, ReplayStatus } from "../../design/components/badges";
import { ReplayComparisonPanel } from "./ReplayComparisonPanel";
import { ReplayDiffViewer } from "./ReplayDiffViewer";
import { ReplayMetadataTable } from "./ReplayMetadataTable";
import { ReplayRoute } from "./ReplayRoute";
import type { ArtifactRef, ArtifactDetail, ReplayComparison } from "../../types/api";
import * as fs from "fs";
import * as path from "path";

// Mock globals
vi.stubGlobal("navigator", {
  clipboard: {
    writeText: vi.fn().mockResolvedValue(undefined),
  },
});

const mockArtifacts: ArtifactRef[] = [
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
    created_at: "2026-05-26T12:01:00Z",
  },
  {
    artifact_id: "art-prop-1",
    kind: "proposal",
    path: "proposals/1.json",
    digest: "sha256:3",
    created_at: "2026-05-26T12:02:00Z",
  },
  {
    artifact_id: "art-rep-1",
    kind: "contemplation_report",
    path: "reports/1.json",
    digest: "sha256:4",
    created_at: "2026-05-26T12:03:00Z",
  },
  {
    artifact_id: "art-tel-1",
    kind: "telemetry",
    path: "telemetry/1.jsonl",
    digest: "sha256:5",
    created_at: "2026-05-26T12:04:00Z",
  },
  {
    artifact_id: "art-state-1",
    kind: "engine_state_manifest",
    path: "state/1.json",
    digest: "sha256:6",
    created_at: "2026-05-26T12:05:00Z",
  },
  {
    artifact_id: "art-unk-1",
    kind: "unknown",
    path: "unknown/1.json",
    digest: "sha256:7",
    created_at: "2026-05-26T12:06:00Z",
  },
];

const mockArtifactDetail: ArtifactDetail = {
  artifact_id: "art-trace-1",
  kind: "trace",
  path: "traces/1.json",
  digest: "sha256:1",
  created_at: "2026-05-26T12:00:00Z",
  content_type: "json",
  content: { hello: "world" },
};

const mockReplayComparison: ReplayComparison = {
  artifact_id: "art-trace-1",
  original_hash: "sha256:orig-1234",
  replay_hash: "sha256:repl-5678",
  equivalent: false,
  divergences: [
    { path: "/a", original: 1, replay: 2, severity: "warning" },
    { path: "/b", original: true, replay: false, severity: "failure" },
    { path: "/c", original: "x", replay: "y", severity: "info" },
  ],
};

function renderWithProviders(ui: React.ReactElement, initialEntries = ["/"]) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={initialEntries}>{ui}</MemoryRouter>
    </QueryClientProvider>
  );
}

describe("W-031 Replay Theater Tests", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("ArtifactList", () => {
    it("renders empty state when API returns []", () => {
      render(
        <ArtifactList artifacts={[]} selectedId={null} onSelect={() => {}} />
      );
      expect(screen.getByTestId("artifact-list-empty")).toBeInTheDocument();
      expect(screen.getByText("No artifacts available.")).toBeInTheDocument();
    });

    it("groups by kind correctly with a fixture covering all 7 kind values", () => {
      render(
        <ArtifactList
          artifacts={mockArtifacts}
          selectedId={null}
          onSelect={() => {}}
        />
      );

      // Verify that all 7 group headings are rendered
      expect(screen.getByText("trace")).toBeInTheDocument();
      expect(screen.getByText("eval result")).toBeInTheDocument();
      expect(screen.getByText("proposal")).toBeInTheDocument();
      expect(screen.getByText("contemplation report")).toBeInTheDocument();
      expect(screen.getByText("telemetry")).toBeInTheDocument();
      expect(screen.getByText("engine state manifest")).toBeInTheDocument();
      expect(screen.getByText("unknown")).toBeInTheDocument();

      // Verify artifact IDs are present
      mockArtifacts.forEach((art) => {
        expect(screen.getByText(art.artifact_id)).toBeInTheDocument();
      });
    });

    it("selecting a row updates the URL query param", async () => {
      function HelperRoute() {
        const [searchParams] = useSearchParams();
        const artifactsQuery = mockArtifacts;
        return (
          <div>
            <div data-testid="url-param">{searchParams.get("artifactId")}</div>
            <ArtifactList
              artifacts={artifactsQuery}
              selectedId={searchParams.get("artifactId")}
              onSelect={(id) => {
                window.history.replaceState(
                  {},
                  "",
                  `?artifactId=${encodeURIComponent(id)}`
                );
                // Trigger popstate so react-router notices change in this test environment
                window.dispatchEvent(new PopStateEvent("popstate"));
              }}
            />
          </div>
        );
      }

      renderWithProviders(<HelperRoute />, ["/"]);
      const btn = screen.getByTestId("artifact-art-trace-1");
      fireEvent.click(btn);

      // Verify that the query parameter was updated
      await waitFor(() => {
        const url = new URL(window.location.href);
        expect(url.searchParams.get("artifactId")).toBe("art-trace-1");
      });
    });
  });

  describe("ReplayStatusBadge", () => {
    it("all four enum states render with the right label and color semantics", () => {
      const states = [
        { value: ReplayStatus.EQUIVALENT, label: "equivalent" },
        { value: ReplayStatus.NOT_YET_REPLAYED, label: "not_yet_replayed" },
        { value: ReplayStatus.DIVERGED, label: "diverged" },
        { value: ReplayStatus.EVIDENCE_UNAVAILABLE, label: "evidence_unavailable" },
      ];

      states.forEach(({ value, label }) => {
        const { unmount } = render(<ReplayStatusBadge value={value} />);
        expect(screen.getByRole("button", { name: label })).toBeInTheDocument();
        unmount();
      });
    });
  });

  describe("ReplayComparisonPanel", () => {
    it("equivalent=true renders the calm empty-state for divergences, NOT a celebratory affordance", () => {
      const eqComparison: ReplayComparison = {
        artifact_id: "art-trace-1",
        original_hash: "sha256:1",
        replay_hash: "sha256:1",
        equivalent: true,
        divergences: [],
      };

      render(
        <MemoryRouter>
          <ReplayComparisonPanel
            artifact={mockArtifactDetail}
            comparison={eqComparison}
            status={ReplayStatus.EQUIVALENT}
          />
        </MemoryRouter>
      );

      // Check for calm empty state text
      expect(screen.getByText("Replay evidence intact — no divergences.")).toBeInTheDocument();

      // Assert static text contains no celebratory affect
      const containerText = document.body.innerHTML;
      const forbiddenWords = ["success", "celebrate", "congratulations", "🎉", "✅", "🏆", "🌟"];
      forbiddenWords.forEach((word) => {
        expect(containerText.toLowerCase()).not.toContain(word);
      });
    });

    it("verifies the component source code files contain no celebratory words or emojis", () => {
      const dir = __dirname;
      const files = [
        "ReplayRoute.tsx",
        "ReplayComparisonPanel.tsx",
        "ReplayDiffViewer.tsx",
        "ReplayMetadataTable.tsx",
        "ArtifactList.tsx",
      ];

      files.forEach((file) => {
        const filePath = path.join(dir, file);
        const code = fs.readFileSync(filePath, "utf-8");
        const forbiddenWords = ["success", "celebrate", "congratulations", "🎉", "✅"];
        forbiddenWords.forEach((word) => {
          expect(
            code.toLowerCase(),
            `File ${file} contains forbidden positive-affect word: ${word}`
          ).not.toContain(word);
        });
      });
    });
  });

  describe("ReplayDiffViewer", () => {
    it("renders divergences ordered failure -> warning -> info", () => {
      render(<ReplayDiffViewer divergences={mockReplayComparison.divergences} />);

      const badges = screen.getAllByRole("button", { name: /(failure|warning|info)/i });
      expect(badges).toHaveLength(3);
      expect(badges[0].textContent).toBe("failure");
      expect(badges[1].textContent).toBe("warning");
      expect(badges[2].textContent).toBe("info");
    });

    it("renders severity label text ('breaking', 'material', 'low') next to badges", () => {
      render(<ReplayDiffViewer divergences={mockReplayComparison.divergences} />);

      expect(screen.getByTestId("severity-label-failure").textContent).toBe("breaking");
      expect(screen.getByTestId("severity-label-warning").textContent).toBe("material");
      expect(screen.getByTestId("severity-label-info").textContent).toBe("low");
    });

    it("renders nothing (null) with 0 divergences", () => {
      const { container } = render(<ReplayDiffViewer divergences={[]} />);
      expect(container.firstChild).toBeNull();
    });
  });

  describe("ReplayMetadataTable", () => {
    it("copyable digests work", () => {
      render(
        <ReplayMetadataTable
          artifact={mockArtifactDetail}
          comparison={mockReplayComparison}
        />
      );

      // Check presence of digest badges (which are copyable InfoBadges)
      const origBadge = screen.getByRole("button", { name: "sha256:orig-" });
      const replBadge = screen.getByRole("button", { name: "sha256:repl-" });

      expect(origBadge).toBeInTheDocument();
      expect(replBadge).toBeInTheDocument();
    });

    it("rendered path is text-only, not an anchor/link element", () => {
      render(
        <ReplayMetadataTable
          artifact={mockArtifactDetail}
          comparison={mockReplayComparison}
        />
      );

      const pathEl = screen.getByTestId("artifact-path-text");
      expect(pathEl.tagName.toLowerCase()).not.toBe("a");
      expect(pathEl.closest("a")).toBeNull();
      expect(pathEl.textContent).toBe(mockArtifactDetail.path);
    });

    it("renders timestamp, digest, run id, lane, and explicit severity labels", () => {
      const detailWithMeta: ArtifactDetail = {
        ...mockArtifactDetail,
        created_at: "2026-05-26T12:00:00Z",
        content: {
          run_id: "run-999",
          lane: "contemplation_quality",
        },
      };

      render(
        <ReplayMetadataTable
          artifact={detailWithMeta}
          comparison={mockReplayComparison}
        />
      );

      // Verify timestamp
      expect(screen.getByTestId("artifact-created-at")).toHaveTextContent("2026");

      // Verify run id & lane
      expect(screen.getByTestId("artifact-run-id")).toHaveTextContent("run-999");
      expect(screen.getByTestId("artifact-lane")).toHaveTextContent("contemplation_quality");

      // Verify divergence counts with textual labels
      expect(screen.getByText("Failure (breaking): 1")).toBeInTheDocument();
      expect(screen.getByText("Warning (material): 1")).toBeInTheDocument();
      expect(screen.getByText("Info (low): 1")).toBeInTheDocument();
    });
  });

  describe("ReplayRoute", () => {
    it("full happy-path with fixture artifact + fixture comparison", async () => {
      const fetchMock = vi.fn().mockImplementation((url: string) => {
        if (url.endsWith("/artifacts")) {
          return Promise.resolve({
            json: () => Promise.resolve({ ok: true, generated_at: "now", data: { items: mockArtifacts } }),
          });
        }
        if (url.endsWith("/artifacts/art-trace-1")) {
          return Promise.resolve({
            json: () => Promise.resolve({ ok: true, generated_at: "now", data: mockArtifactDetail }),
          });
        }
        if (url.endsWith("/replay/art-trace-1")) {
          return Promise.resolve({
            json: () => Promise.resolve({ ok: true, generated_at: "now", data: mockReplayComparison }),
          });
        }
        return Promise.reject(new Error("Unknown route"));
      });
      vi.stubGlobal("fetch", fetchMock);

      renderWithProviders(<ReplayRoute />, ["/replay?artifactId=art-trace-1"]);

      // Should load list, detail, and comparison
      expect(await screen.findByText("Replay Evidence")).toBeInTheDocument();
      expect(screen.getAllByText("art-trace-1").length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText("Replay Divergences")).toBeInTheDocument();
    });

    it("evidence_unavailable state when backend returns unsupported", async () => {
      const fetchMock = vi.fn().mockImplementation((url: string) => {
        if (url.endsWith("/artifacts")) {
          return Promise.resolve({
            json: () => Promise.resolve({ ok: true, generated_at: "now", data: { items: mockArtifacts } }),
          });
        }
        if (url.endsWith("/artifacts/art-trace-1")) {
          return Promise.resolve({
            json: () => Promise.resolve({ ok: true, generated_at: "now", data: mockArtifactDetail }),
          });
        }
        if (url.endsWith("/replay/art-trace-1")) {
          // Return unsupported error code
          return Promise.resolve({
            json: () => Promise.resolve({
              ok: false,
              generated_at: "now",
              error: { code: "unsupported", message: "route is unsupported" },
            }),
          });
        }
        return Promise.reject(new Error("Unknown route"));
      });
      vi.stubGlobal("fetch", fetchMock);

      renderWithProviders(<ReplayRoute />, ["/replay?artifactId=art-trace-1"]);

      expect(await screen.findByText("evidence_unavailable")).toBeInTheDocument();
      expect(screen.getByText("Replay evidence is not available on the backend for this artifact kind.")).toBeInTheDocument();
    });

    it("ErrorState only for genuine API errors (not for unsupported)", async () => {
      const fetchMock = vi.fn().mockImplementation((url: string) => {
        if (url.endsWith("/artifacts")) {
          return Promise.resolve({
            json: () => Promise.resolve({ ok: true, generated_at: "now", data: { items: mockArtifacts } }),
          });
        }
        if (url.endsWith("/artifacts/art-trace-1")) {
          return Promise.resolve({
            json: () => Promise.resolve({ ok: true, generated_at: "now", data: mockArtifactDetail }),
          });
        }
        if (url.endsWith("/replay/art-trace-1")) {
          // Return a genuine read_error
          return Promise.resolve({
            json: () => Promise.resolve({
              ok: false,
              generated_at: "now",
              error: { code: "read_error", message: "disk read error" },
            }),
          });
        }
        return Promise.reject(new Error("Unknown route"));
      });
      vi.stubGlobal("fetch", fetchMock);

      renderWithProviders(<ReplayRoute />, ["/replay?artifactId=art-trace-1"]);

      expect(await screen.findByText("What failed")).toBeInTheDocument();
      expect(screen.getByText("disk read error")).toBeInTheDocument();
    });

    it("renders Selected artifact not found when selected ID returns null detail data", async () => {
      const fetchMock = vi.fn().mockImplementation((url: string) => {
        if (url.endsWith("/artifacts")) {
          return Promise.resolve({
            json: () => Promise.resolve({ ok: true, generated_at: "now", data: { items: mockArtifacts } }),
          });
        }
        if (url.endsWith("/artifacts/missing-id")) {
          return Promise.resolve({
            json: () => Promise.resolve({ ok: true, generated_at: "now", data: null }),
          });
        }
        if (url.endsWith("/replay/missing-id")) {
          return Promise.resolve({
            json: () => Promise.resolve({ ok: true, generated_at: "now", data: mockReplayComparison }),
          });
        }
        return Promise.reject(new Error("Unknown route"));
      });
      vi.stubGlobal("fetch", fetchMock);

      renderWithProviders(<ReplayRoute />, ["/replay?artifactId=missing-id"]);

      expect(await screen.findByText("Selected artifact not found.")).toBeInTheDocument();
    });

    it("renders ErrorState in left pane when artifacts loading fails", async () => {
      const fetchMock = vi.fn().mockImplementation((url: string) => {
        if (url.endsWith("/artifacts")) {
          return Promise.resolve({
            json: () => Promise.resolve({
              ok: false,
              generated_at: "now",
              error: { code: "read_error", message: "Failed to read artifacts index" },
            }),
          });
        }
        return Promise.reject(new Error("Unknown route"));
      });
      vi.stubGlobal("fetch", fetchMock);

      renderWithProviders(<ReplayRoute />, ["/replay"]);

      const errorElements = await screen.findAllByText("Failed to read artifacts index");
      expect(errorElements.length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText("No corpus mutation occurred.").length).toBeGreaterThanOrEqual(1);
    });

    it("renders Back to proposal link only when fromProposal query parameter is present", () => {
      const { unmount } = renderWithProviders(
        <ReplayComparisonPanel
          artifact={mockArtifactDetail}
          comparison={mockReplayComparison}
          status={ReplayStatus.DIVERGED}
        />,
        ["/replay?artifactId=art-trace-1"]
      );

      expect(screen.queryByTestId("back-to-proposal")).not.toBeInTheDocument();
      unmount();

      renderWithProviders(
        <ReplayComparisonPanel
          artifact={mockArtifactDetail}
          comparison={mockReplayComparison}
          status={ReplayStatus.DIVERGED}
        />,
        ["/replay?artifactId=art-trace-1&fromProposal=proposal-777"]
      );

      const link = screen.getByTestId("back-to-proposal");
      expect(link).toBeInTheDocument();
      expect(link).toHaveTextContent("Back to proposal #proposal-777");
      expect(link.getAttribute("href")).toBe("/proposals?proposal_id=proposal-777");
    });
  });

  describe("Anti-motion & Animation Constraints", () => {
    it("verifies the component files contain no animation/motion triggers like transition, animate, fade", () => {
      const dir = __dirname;
      const files = [
        "ReplayRoute.tsx",
        "ReplayComparisonPanel.tsx",
        "ReplayDiffViewer.tsx",
        "ReplayMetadataTable.tsx",
        "ArtifactList.tsx",
      ];

      files.forEach((file) => {
        const filePath = path.join(dir, file);
        const code = fs.readFileSync(filePath, "utf-8");
        const forbiddenMotion = ["transition", "animate", "fade"];
        forbiddenMotion.forEach((trigger) => {
          expect(
            code.toLowerCase(),
            `File ${file} contains forbidden animation keyword: ${trigger}`
          ).not.toContain(trigger);
        });
      });
    });
  });
});
