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
import type { TurnJournalSummary, TurnReplayComparison } from "../../types/api";
import { EvidenceProvider } from "../evidenceContext";
import { ReplayRoute } from "./ReplayRoute";

const summaries: TurnJournalSummary[] = [
  {
    turn_id: 1,
    timestamp: "2026-06-12T18:00:00Z",
    prompt_excerpt: "What is truth?",
    surface_excerpt: "Truth is coherent.",
    trace_hash: "sha256:111111111111aaaa",
    grounding_source: "pack",
    trace_integrity: "pipeline_trace",
  },
  {
    turn_id: 2,
    timestamp: "2026-06-12T18:01:00Z",
    prompt_excerpt: "What is beauty?",
    surface_excerpt: "Beauty is form.",
    trace_hash: "sha256:222222222222bbbb",
    grounding_source: "teaching",
    trace_integrity: "pipeline_trace",
  },
];

function comparisonFor(turnId: number): TurnReplayComparison {
  if (turnId === 1) {
    // equivalent, only an informational (wall-clock) divergence
    return {
      turn_id: 1,
      comparison_basis: "sealed_fresh_runtime_single_turn",
      origin_state: "unrecorded",
      original_trace_hash: "sha256:111111111111aaaa",
      replay_trace_hash: "sha256:111111111111aaaa",
      equivalent: true,
      replay_turn_cost_ms: 412,
      divergences: [
        {
          path: "timestamp",
          original: "2026-06-12T18:00:00Z",
          replay: "2026-06-13T00:00:00Z",
          severity: "informational",
        },
      ],
    };
  }
  // diverged: a critical surface divergence
  return {
    turn_id: 2,
    comparison_basis: "sealed_fresh_runtime_single_turn",
    origin_state: "unrecorded",
    original_trace_hash: "sha256:222222222222bbbb",
    replay_trace_hash: "sha256:999999999999cccc",
    equivalent: false,
    replay_turn_cost_ms: 401,
    divergences: [
      {
        path: "surface",
        original: "Beauty is form.",
        replay: "Beauty is symmetry.",
        severity: "critical",
      },
    ],
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

function renderRoute(initialEntry = "/replay") {
  return render(
    <QueryClientProvider client={createTestQueryClient()}>
      <MemoryRouter initialEntries={[initialEntry]}>
        <EvidenceProvider>
          <Routes>
            <Route
              path="/replay/:turnId?"
              element={
                <>
                  <ReplayRoute />
                  <LocationProbe />
                </>
              }
            />
          </Routes>
        </EvidenceProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function stubReplayFetch(items: TurnJournalSummary[] = summaries) {
  const fetchMock = vi.fn((input: unknown) => {
    const path = new URL(String(input)).pathname;
    if (path === "/trace/turns") {
      return Promise.resolve({
        json: () => Promise.resolve({ ok: true, generated_at: "now", data: { items } }),
      });
    }
    const match = path.match(/^\/replay\/(\d+)$/);
    if (match) {
      return Promise.resolve({
        json: () =>
          Promise.resolve({ ok: true, generated_at: "now", data: comparisonFor(Number(match[1])) }),
      });
    }
    return Promise.resolve({
      json: () =>
        Promise.resolve({
          ok: false,
          generated_at: "now",
          error: { code: "not_found", message: `unexpected ${path}` },
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

describe("ReplayRoute", () => {
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

  it("lists journaled turns to replay", async () => {
    stubReplayFetch();
    renderRoute();
    expect(await screen.findByText("What is truth?")).toBeInTheDocument();
    expect(screen.getByText("What is beauty?")).toBeInTheDocument();
  });

  it("excludes legacy-unhashed rows from the replayable list", async () => {
    stubReplayFetch([
      summaries[0],
      {
        ...summaries[1],
        trace_hash: null,
        trace_integrity: "legacy_unhashed",
      },
    ]);
    renderRoute();

    expect(await screen.findByText("What is truth?")).toBeInTheDocument();
    expect(screen.queryByText("What is beauty?")).not.toBeInTheDocument();
  });

  it("shows an empty state when only legacy rows exist", async () => {
    stubReplayFetch([
      {
        ...summaries[0],
        trace_hash: null,
        trace_integrity: "legacy_unhashed",
      },
    ]);
    renderRoute();

    expect(await screen.findByText("No pipeline-stamped turns are replayable yet.")).toBeInTheDocument();
  });

  it("renders the equivalence hero with the honesty card for a matching replay", async () => {
    stubReplayFetch();
    renderRoute("/replay/1");

    expect(await screen.findByText(/Replay equivalent/)).toBeInTheDocument();
    // honesty fields are surfaced, not hidden
    expect(screen.getByText("sealed_fresh_runtime_single_turn")).toBeInTheDocument();
    expect(screen.getByText("unrecorded")).toBeInTheDocument();
    // an equivalent replay with only wall-clock drift is labeled as such
    expect(screen.getByText(/all informational/)).toBeInTheDocument();
  });

  it("renders a diverged verdict with the critical leaf for a tampered replay", async () => {
    stubReplayFetch();
    renderRoute("/replay/2");

    expect(await screen.findByText("Replay diverged")).toBeInTheDocument();
    // the critical divergence is shown at its exact leaf path
    expect(screen.getByText("surface")).toBeInTheDocument();
    expect(screen.getByText("Beauty is symmetry.")).toBeInTheDocument();
    expect(screen.getAllByText("critical").length).toBeGreaterThan(0);
  });

  it("selecting a turn writes /replay/<turnId> with replace", async () => {
    stubReplayFetch();
    const user = userEvent.setup();
    renderRoute();

    await user.click(await screen.findByText("What is beauty?"));

    await waitFor(() => expect(screen.getByTestId("location")).toHaveTextContent("/replay/2"));
    expect(screen.getByTestId("nav-type")).toHaveTextContent("REPLACE");
    expect(await screen.findByText("Replay diverged")).toBeInTheDocument();
  });

  it("moves the turn list focus with j/k through the VirtualizedList spine", async () => {
    stubReplayFetch();
    const user = userEvent.setup();
    renderRoute();

    const list = await screen.findByRole("listbox", { name: "Replayable turns" });
    list.focus();
    expect(screen.getAllByRole("option")[0]).toHaveAttribute("aria-selected", "true");

    await user.keyboard("j");
    expect(screen.getAllByRole("option")[1]).toHaveAttribute("aria-selected", "true");
  });
});
