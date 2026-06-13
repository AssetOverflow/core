import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { createTestQueryClient } from "../../test/createTestQueryClient";
import type {
  ContemplationRunDetail,
  ContemplationRunSummary,
} from "../../types/api";
import { ContemplationRoute } from "./ContemplationRoute";

const RUN_ID = "2026-06-13T010203Z";

const summary: ContemplationRunSummary = {
  run_id: RUN_ID,
  source_path: "contemplation/runs/2026-06-13T010203Z.json",
  source_digest: "sha256:111111111111abcdef",
  prompt: "Why does narrative exist?",
  cold_subject: "narrative",
  scene_count: 2,
  learning_arc_closed: true,
  all_claims_supported: true,
  active_corpus_byte_identical: true,
};

const detail: ContemplationRunDetail = {
  ...summary,
  before: { grounding_source: "none" },
  after: { grounding_source: "teaching" },
  engine_chain: {
    subject: "narrative",
    connective: "reveals",
    object: "meaning",
  },
  scenes: [
    {
      scene_id: "S1_cold_session",
      claim: "cold session refused",
      detail: { grounding_source: "none" },
    },
    {
      scene_id: "S3_engine_authored_proposal",
      claim: "proposal remains pending",
      detail: { state: "pending" },
    },
  ],
};

function LocationProbe() {
  const location = useLocation();
  return <span data-testid="location">{location.pathname}</span>;
}

function renderRoute(initialEntry = "/contemplation") {
  return render(
    <QueryClientProvider client={createTestQueryClient()}>
      <MemoryRouter initialEntries={[initialEntry]}>
        <Routes>
          <Route
            path="/contemplation/:runId?"
            element={
              <>
                <ContemplationRoute />
                <LocationProbe />
              </>
            }
          />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function stubFetch(items: ContemplationRunSummary[] = [summary]) {
  const fetchMock = vi.fn((input: unknown) => {
    const path = new URL(String(input)).pathname;
    if (path === "/contemplation/runs") {
      return Promise.resolve({
        json: () => Promise.resolve({ ok: true, generated_at: "now", data: { items } }),
      });
    }
    if (path === `/contemplation/runs/${RUN_ID}`) {
      return Promise.resolve({
        json: () => Promise.resolve({ ok: true, generated_at: "now", data: detail }),
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
}

describe("ContemplationRoute", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders persisted contemplation runs and their process detail", async () => {
    stubFetch();
    const user = userEvent.setup();
    renderRoute();

    expect(await screen.findByText(RUN_ID)).toBeInTheDocument();
    expect(screen.getByText("Why does narrative exist?")).toBeInTheDocument();

    await user.click(screen.getByText("Why does narrative exist?"));

    await waitFor(() =>
      expect(screen.getByTestId("location")).toHaveTextContent(`/contemplation/${RUN_ID}`),
    );
    expect(await screen.findByText("Process Trace")).toBeInTheDocument();
    expect(screen.getByText("S1_cold_session")).toBeInTheDocument();
    expect(screen.getByText("S3_engine_authored_proposal")).toBeInTheDocument();
    expect(screen.getByText("cold session refused")).toBeInTheDocument();
    expect(screen.getByText(/\"connective\":\"reveals\"/)).toBeInTheDocument();
  });

  it("renders the honest absence state when no reports exist", async () => {
    stubFetch([]);
    renderRoute();

    expect(
      await screen.findByText("No contemplation process reports recorded."),
    ).toBeInTheDocument();
    expect(screen.getByText("core contemplate")).toBeInTheDocument();
  });
});
