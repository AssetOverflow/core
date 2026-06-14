import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { createTestQueryClient } from "../../test/createTestQueryClient";
import type { DeterminismTour } from "../../types/api";
import { TourRoute } from "./TourRoute";

const TOUR: DeterminismTour = {
  schema_version: "determinism_tour_v1",
  title: "The Determinism Tour",
  thesis: "Bring a claim from any model and watch the engine decide, refuse, and replay it.",
  steps: [
    {
      step_id: "intro",
      order: 0,
      kind: "intro",
      headline: "Determinism you can check",
      narrative: "Each step runs a real demo over pinned fixtures.",
      demo_id: null,
      demo_title: null,
      what_this_proves: null,
      what_this_does_not_prove: null,
      route_hint: "/demos",
    },
    {
      step_id: "decide",
      order: 1,
      kind: "demo",
      headline: "Bring a claim — the engine decides",
      narrative: "Served only when the pinned engine and an oracle agree.",
      demo_id: "deductive_entailment_authority",
      demo_title: "Deductive Entailment Authority",
      what_this_proves: "CORE serves decisions only when engine and oracle agree.",
      what_this_does_not_prove: "It does not claim open-domain theorem proving.",
      route_hint: "/demos/deductive_entailment_authority",
    },
    {
      step_id: "payoff",
      order: 2,
      kind: "payoff",
      headline: "Replay to the same hash",
      narrative: "Every decision replays to the same trace hash.",
      demo_id: null,
      demo_title: null,
      what_this_proves: null,
      what_this_does_not_prove: null,
      route_hint: "/replay",
    },
  ],
};

function stubFetch(tour: DeterminismTour = TOUR) {
  vi.stubGlobal(
    "fetch",
    vi.fn(() =>
      Promise.resolve({
        json: () => Promise.resolve({ ok: true, generated_at: "now", data: tour }),
      }),
    ),
  );
}

function renderRoute() {
  return render(
    <QueryClientProvider client={createTestQueryClient()}>
      <MemoryRouter initialEntries={["/tour"]}>
        <TourRoute />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("TourRoute", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("renders the provider-agnostic thesis and the ordered narrative", async () => {
    stubFetch();
    renderRoute();

    expect(await screen.findByText(/Bring a claim from any model/)).toBeInTheDocument();
    expect(screen.getByText("Determinism you can check")).toBeInTheDocument();
    expect(screen.getByText("Bring a claim — the engine decides")).toBeInTheDocument();
    expect(screen.getByText("Replay to the same hash")).toBeInTheDocument();
  });

  it("shows honest what-proves / what-does-not-prove cards on demo steps", async () => {
    stubFetch();
    renderRoute();

    expect(await screen.findByText("what this proves")).toBeInTheDocument();
    expect(screen.getByText(/engine and oracle agree/)).toBeInTheDocument();
    expect(screen.getByText("what this does not prove")).toBeInTheDocument();
    expect(screen.getByText(/does not claim open-domain/)).toBeInTheDocument();
    // The demo step links to the real demo route.
    expect(screen.getByTestId("tour-link-decide")).toHaveAttribute(
      "href",
      "/demos/deductive_entailment_authority",
    );
  });
});
