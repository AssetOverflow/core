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
import type { TurnJournalEntry, TurnJournalSummary } from "../../types/api";
import { EvidenceProvider } from "../evidenceContext";
import { TraceRoute } from "./TraceRoute";

const summaries: TurnJournalSummary[] = [
  {
    turn_id: 1,
    timestamp: "2026-06-12T18:00:00Z",
    prompt_excerpt: "First prompt\nwith more",
    surface_excerpt: "First response",
    trace_hash: "sha256:111111111111abcdef",
    grounding_source: "pack",
  },
  {
    turn_id: 2,
    timestamp: "2026-06-12T18:01:00Z",
    prompt_excerpt: "Second prompt",
    surface_excerpt: "Second response",
    trace_hash: "sha256:222222222222abcdef",
    grounding_source: "teaching",
  },
  {
    turn_id: 3,
    timestamp: "2026-06-12T18:02:00Z",
    prompt_excerpt: "Third prompt",
    surface_excerpt: "Third response",
    trace_hash: "sha256:333333333333abcdef",
    grounding_source: "vault",
  },
];

function entry(id: number): TurnJournalEntry {
  const summary = summaries.find((item) => item.turn_id === id) ?? summaries[0];
  return {
    turn_id: summary.turn_id,
    timestamp: summary.timestamp,
    trace_hash: summary.trace_hash,
    prompt: `${summary.prompt_excerpt} full text`,
    surface: `User response for turn ${summary.turn_id}`,
    articulation_surface: `Realizer surface for turn ${summary.turn_id}`,
    walk_surface: `Walk evidence for turn ${summary.turn_id}`,
    grounding_source: summary.grounding_source,
    epistemic_state: "evidenced",
    normative_clearance: "cleared",
    verdicts: {
      identity: { outcome: "cleared", runtime_detail: "identity ok" },
      safety: { outcome: "cleared", runtime_detail: "safety ok" },
      ethics: { outcome: "cleared", runtime_detail: "ethics ok" },
    },
    refusal_emitted: false,
    hedge_injected: false,
    proposal_candidates: [{ candidate_id: "candidate-1", source_kind: "discovery" }],
    turn_cost_ms: 17,
    checkpoint_emitted: true,
    journal_digest: `sha256:journal${summary.turn_id}abcdef`,
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

function renderRoute(initialEntry = "/trace") {
  return render(
    <QueryClientProvider client={createTestQueryClient()}>
      <MemoryRouter initialEntries={[initialEntry]}>
        <EvidenceProvider>
          <Routes>
            <Route
              path="/trace/:turnId?"
              element={
                <>
                  <TraceRoute />
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

function stubTraceFetch(items: TurnJournalSummary[] = summaries) {
  const fetchMock = vi.fn((input: unknown) => {
    const path = new URL(String(input)).pathname;
    if (path === "/trace/turns") {
      return Promise.resolve({
        json: () => Promise.resolve({ ok: true, generated_at: "now", data: { items } }),
      });
    }
    const match = path.match(/^\/trace\/(\d+)$/);
    if (match) {
      return Promise.resolve({
        json: () =>
          Promise.resolve({ ok: true, generated_at: "now", data: entry(Number(match[1])) }),
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

describe("TraceRoute", () => {
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

  it("renders the timeline from journal summaries", async () => {
    stubTraceFetch();
    renderRoute();

    expect(await screen.findByText("First prompt")).toBeInTheDocument();
    expect(screen.getByText("Second prompt")).toBeInTheDocument();
    expect(screen.getByText("sha256:111111111111...")).toBeInTheDocument();
  });

  it("selecting a turn writes /trace/<turnId> with replace and shows evidence", async () => {
    stubTraceFetch();
    const user = userEvent.setup();
    renderRoute();

    await user.click(await screen.findByText("First prompt"));

    await waitFor(() => expect(screen.getByTestId("location")).toHaveTextContent("/trace/1"));
    expect(screen.getByTestId("nav-type")).toHaveTextContent("REPLACE");
    expect(await screen.findByText("User response for turn 1")).toBeInTheDocument();
  });

  it("renders the three surface labels distinctly", async () => {
    stubTraceFetch();
    renderRoute("/trace/2");

    expect(await screen.findByText("User Surface (response)")).toBeInTheDocument();
    expect(screen.getByText("Articulation Surface (realizer)")).toBeInTheDocument();
    expect(screen.getByText("Walk Surface (telemetry/evidence)")).toBeInTheDocument();
  });

  it("keeps raw JSON collapsed by default", async () => {
    stubTraceFetch();
    const user = userEvent.setup();
    renderRoute("/trace/2");

    await user.click(await screen.findByRole("tab", { name: "Raw" }));

    expect(screen.getByText("Raw journal JSON is collapsed by default.")).toBeInTheDocument();
    expect(screen.queryByTestId("json-rows")).not.toBeInTheDocument();
  });

  it("restores selection from a deep-linked turn id", async () => {
    stubTraceFetch();
    renderRoute("/trace/3");

    expect(await screen.findByText("User response for turn 3")).toBeInTheDocument();
    expect(screen.getByText("Third prompt").closest('[aria-current="true"]')).not.toBeNull();
  });

  it("moves timeline focus with j/k through the VirtualizedList keyboard spine", async () => {
    stubTraceFetch();
    const user = userEvent.setup();
    renderRoute();

    const list = await screen.findByRole("listbox", { name: "Trace turns" });
    list.focus();
    expect(screen.getAllByRole("option")[0]).toHaveAttribute("aria-selected", "true");

    await user.keyboard("j");
    expect(screen.getAllByRole("option")[1]).toHaveAttribute("aria-selected", "true");

    await user.keyboard("k");
    expect(screen.getAllByRole("option")[0]).toHaveAttribute("aria-selected", "true");
  });
});
