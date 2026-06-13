import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {
  MemoryRouter,
  Route,
  Routes,
  useLocation,
  useNavigationType,
} from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createTestQueryClient } from "../../test/createTestQueryClient";
import type { RunDetail, RunSummary } from "../../types/api";
import { EvidenceProvider } from "../evidenceContext";
import { RunsRoute } from "./RunsRoute";

const JOURNAL_RUN = "workbench_turn_journal";
const ENGINE_RUN = "engine_state_checkpoint";

const summaries: RunSummary[] = [
  {
    session_id: JOURNAL_RUN,
    source: "turn_journal",
    turn_count: 2,
    started_at: "2026-06-12T18:00:00Z",
    updated_at: "2026-06-12T18:05:00Z",
    checkpoint_present: false,
    checkpoint_revision: null,
    artifact_refs: [],
    evidence_gap: null,
  },
  {
    session_id: ENGINE_RUN,
    source: "engine_state_manifest",
    turn_count: 0,
    started_at: null,
    updated_at: "2026-06-12T17:00:00Z",
    checkpoint_present: true,
    checkpoint_revision: "rev-abc123",
    artifact_refs: [],
    evidence_gap: "turn journal not found alongside checkpoint",
  },
];

function detailFor(sessionId: string): RunDetail {
  const summary = summaries.find((s) => s.session_id === sessionId) ?? summaries[0];
  if (sessionId === JOURNAL_RUN) {
    return {
      ...summary,
      turns: [
        {
          turn_id: 1,
          trace_hash: "sha256:111111111111abcdef",
          timestamp: "2026-06-12T18:00:00Z",
          trace_path: "/trace/1",
          surface_excerpt: "First response",
          trace_integrity: "pipeline_trace",
        },
        {
          turn_id: 2,
          trace_hash: "sha256:222222222222abcdef",
          timestamp: "2026-06-12T18:05:00Z",
          trace_path: "/trace/2",
          surface_excerpt: "Second response",
          trace_integrity: "pipeline_trace",
        },
      ],
      manifest: null,
    };
  }
  return {
    ...summary,
    turns: [],
    manifest: { schema_version: 2, checkpoint_revision: "rev-abc123" },
  };
}

function LocationProbe() {
  const location = useLocation();
  const navigationType = useNavigationType();
  return (
    <>
      <span data-testid="location">{`${location.pathname}${location.search}`}</span>
      <span data-testid="nav-type">{navigationType}</span>
    </>
  );
}

function renderRoute(initialEntry = "/runs") {
  return render(
    <QueryClientProvider client={createTestQueryClient()}>
      <MemoryRouter initialEntries={[initialEntry]}>
        <EvidenceProvider>
          <Routes>
            <Route
              path="/runs/:sessionId?"
              element={
                <>
                  <RunsRoute />
                  <LocationProbe />
                </>
              }
            />
            <Route path="/trace/:turnId?" element={<LocationProbe />} />
          </Routes>
        </EvidenceProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function stubRunsFetch(items: RunSummary[] = summaries) {
  const fetchMock = vi.fn((input: unknown) => {
    const path = new URL(String(input)).pathname;
    if (path === "/runs") {
      return Promise.resolve({
        json: () => Promise.resolve({ ok: true, generated_at: "now", data: { items } }),
      });
    }
    const match = path.match(/^\/runs\/(.+)$/);
    if (match) {
      return Promise.resolve({
        json: () =>
          Promise.resolve({
            ok: true,
            generated_at: "now",
            data: detailFor(decodeURIComponent(match[1])),
          }),
      });
    }
    return Promise.resolve({
      json: () =>
        Promise.resolve({
          ok: false,
          generated_at: "now",
          error: { code: "not_found", message: `unexpected path ${path}` },
        }),
    });
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

const offsetDescriptors = {
  offsetHeight: Object.getOwnPropertyDescriptor(HTMLElement.prototype, "offsetHeight"),
  offsetWidth: Object.getOwnPropertyDescriptor(HTMLElement.prototype, "offsetWidth"),
};

describe("RunsRoute", () => {
  beforeEach(() => {
    Object.defineProperty(HTMLElement.prototype, "offsetHeight", {
      configurable: true,
      get: () => 560,
    });
    Object.defineProperty(HTMLElement.prototype, "offsetWidth", {
      configurable: true,
      get: () => 480,
    });
  });

  afterEach(() => {
    if (offsetDescriptors.offsetHeight) {
      Object.defineProperty(HTMLElement.prototype, "offsetHeight", offsetDescriptors.offsetHeight);
    }
    if (offsetDescriptors.offsetWidth) {
      Object.defineProperty(HTMLElement.prototype, "offsetWidth", offsetDescriptors.offsetWidth);
    }
    vi.restoreAllMocks();
    localStorage.clear();
  });

  it("renders the session list with checkpoint and turn-count evidence", async () => {
    stubRunsFetch();
    renderRoute();

    expect(await screen.findByText("Turn journal")).toBeInTheDocument();
    expect(screen.getByText("Engine-state checkpoint")).toBeInTheDocument();
    expect(screen.getByText(JOURNAL_RUN)).toBeInTheDocument();
    expect(screen.getByText("2 turns")).toBeInTheDocument();
    // checkpoint present vs absent are visually distinct
    expect(screen.getByText("no checkpoint")).toBeInTheDocument();
    expect(screen.getByText("rev-abc123")).toBeInTheDocument();
  });

  it("renders an evidence gap honestly in-row, never hidden", async () => {
    stubRunsFetch();
    renderRoute();

    expect(
      await screen.findByText(/evidence gap: turn journal not found alongside checkpoint/),
    ).toBeInTheDocument();
  });

  it("selecting a run writes /runs/<sessionId> with replace and shows detail", async () => {
    stubRunsFetch();
    const user = userEvent.setup();
    renderRoute();

    await user.click(await screen.findByText("Turn journal"));

    await waitFor(() =>
      expect(screen.getByTestId("location")).toHaveTextContent(`/runs/${JOURNAL_RUN}`),
    );
    expect(screen.getByTestId("nav-type")).toHaveTextContent("REPLACE");
  });

  it("every turn row cross-links to /trace/<turn_id> — the point of this route", async () => {
    stubRunsFetch();
    renderRoute(`/runs/${JOURNAL_RUN}`);

    const link1 = await screen.findByRole("link", { name: /Turn #1/ });
    expect(link1).toHaveAttribute("href", "/trace/1");
    const link2 = screen.getByRole("link", { name: /Turn #2/ });
    expect(link2).toHaveAttribute("href", "/trace/2");
    // the trace hash is shown as a digest badge on each turn row
    expect(screen.getByText("sha256:111111111111...")).toBeInTheDocument();
  });

  it("shows the engine-state manifest under the Manifest tab", async () => {
    stubRunsFetch();
    const user = userEvent.setup();
    renderRoute(`/runs/${ENGINE_RUN}`);

    // engine-state run has no cross-linkable turns
    expect(
      await screen.findByText(/records no cross-linkable turns/),
    ).toBeInTheDocument();

    await user.click(screen.getByRole("tab", { name: "Manifest" }));
    expect(await screen.findByText(/schema_version/)).toBeInTheDocument();
  });

  it("moves the session list focus with j/k through the VirtualizedList spine", async () => {
    stubRunsFetch();
    const user = userEvent.setup();
    renderRoute();

    const list = await screen.findByRole("listbox", { name: "Runs" });
    list.focus();
    expect(screen.getAllByRole("option")[0]).toHaveAttribute("aria-selected", "true");

    await user.keyboard("j");
    expect(screen.getAllByRole("option")[1]).toHaveAttribute("aria-selected", "true");

    await user.keyboard("k");
    expect(screen.getAllByRole("option")[0]).toHaveAttribute("aria-selected", "true");
  });
});
