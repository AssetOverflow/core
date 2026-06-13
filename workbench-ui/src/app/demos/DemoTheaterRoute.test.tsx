import { QueryClientProvider } from "@tanstack/react-query";
import { act, render, screen, waitFor } from "@testing-library/react";
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
import type { DemoRunResult, DemoSummary } from "../../types/api";
import { DemoTheaterRoute } from "./DemoTheaterRoute";

vi.mock("../../api/queries", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../api/queries")>();
  return {
    ...actual,
    useDemos: vi.fn(),
    useDemoRun: vi.fn(),
  };
});

import { useDemoRun, useDemos } from "../../api/queries";

const demos: DemoSummary[] = [
  {
    demo_id: "proof_carrying_promotion",
    title: "Proof-Carrying Coherence Promotion",
    description: "Vault-owned certified promotion.",
    evidence_class: "substrate_capability",
    scenario_count: 2,
    read_only: true,
    scenarios: [
      {
        scenario_id: "entailed-promotes",
        title: "Entailed Promotes",
        expected_status: "promoted",
        evidence_class: "substrate_capability",
        proposer_wrong: false,
        what_this_proves: "CORE recomputes entailment before promotion.",
        what_this_does_not_prove: "It does not prove autonomous curation.",
      },
      {
        scenario_id: "proposer-status-ignored",
        title: "Proposer Status Ignored",
        expected_status: "promoted",
        evidence_class: "substrate_capability",
        proposer_wrong: true,
        what_this_proves: "CORE ignores proposer status.",
        what_this_does_not_prove: "It does not trust model-provided status.",
      },
    ],
  },
  {
    demo_id: "deductive_entailment_authority",
    title: "Deductive Entailment Authority",
    description: "Engine and oracle agree.",
    evidence_class: "substrate_capability",
    scenario_count: 1,
    read_only: true,
    scenarios: [
      {
        scenario_id: "unknown-non-sequitur",
        title: "Unknown Non Sequitur",
        expected_status: "decided",
        evidence_class: "substrate_capability",
        proposer_wrong: false,
        what_this_proves: "The authority can return unknown.",
        what_this_does_not_prove: "It does not prove open-domain theorem proving.",
      },
    ],
  },
];

const runResult: DemoRunResult = {
  demo_id: "proof_carrying_promotion",
  all_passed: true,
  what_this_proves: "CORE recomputes entailment before promotion.",
  what_this_does_not_prove: "It does not prove autonomous curation.",
  scenarios: [
    {
      scenario_id: "proposer-status-ignored",
      status: "promoted",
      passed: true,
      proposer_wrong: true,
      evidence_class: "substrate_capability",
      decision_reason: "certified_entailment",
      trace_hash: "abcd1234",
      problems: [],
      response: { status: "promoted" },
      evidence_dag: {
        graph_id: "proposer-status-ignored:proof-carrying-promotion",
        graph_kind: "proof_carrying_promotion",
        title: "Proof-carrying promotion DAG",
        source_digest: "sha256:abc123",
        nodes: [
          {
            node_id: "request",
            label: "Request",
            summary: "demo-pccp",
            detail: { request_id: "demo-pccp" },
          },
          {
            node_id: "certify",
            label: "CORE Certifies",
            summary: "certified_entailment",
            detail: { decision_reason: "certified_entailment" },
          },
          {
            node_id: "outcome",
            label: "Outcome",
            summary: "promoted",
            detail: { status: "promoted" },
          },
        ],
        edges: [
          { from_node: "request", to_node: "certify", label: "evaluate" },
          { from_node: "certify", to_node: "outcome", label: "apply" },
        ],
      },
    },
  ],
};

function LocationProbe() {
  const location = useLocation();
  const navigationType = useNavigationType();
  return (
    <>
      <span data-testid="location">{location.pathname}</span>
      <span data-testid="nav-type">{navigationType}</span>
    </>
  );
}

function renderRoute(initialEntry = "/demos") {
  return render(
    <QueryClientProvider client={createTestQueryClient()}>
      <MemoryRouter initialEntries={[initialEntry]}>
        <Routes>
          <Route
            path="/demos/:demoId?"
            element={
              <>
                <DemoTheaterRoute />
                <LocationProbe />
              </>
            }
          />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

const offsetDescriptors = {
  offsetHeight: Object.getOwnPropertyDescriptor(HTMLElement.prototype, "offsetHeight"),
  offsetWidth: Object.getOwnPropertyDescriptor(HTMLElement.prototype, "offsetWidth"),
};

describe("DemoTheaterRoute", () => {
  beforeEach(() => {
    Object.defineProperty(HTMLElement.prototype, "offsetHeight", {
      configurable: true,
      get: () => 560,
    });
    Object.defineProperty(HTMLElement.prototype, "offsetWidth", {
      configurable: true,
      get: () => 360,
    });
    vi.mocked(useDemos).mockReturnValue({
      data: demos,
      isLoading: false,
      isError: false,
      error: null,
    } as any);
    vi.mocked(useDemoRun).mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as any);
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

  it("lists registered demos and selects via replace navigation", async () => {
    const user = userEvent.setup();
    renderRoute();

    await user.click(screen.getByText("Deductive Entailment Authority"));

    await waitFor(() =>
      expect(screen.getByTestId("location")).toHaveTextContent("/demos/deductive_entailment_authority"),
    );
    expect(screen.getByTestId("nav-type")).toHaveTextContent("REPLACE");
  });

  it("renders scenario honesty cards and proposer-wrong highlights", () => {
    renderRoute("/demos/proof_carrying_promotion");

    expect(screen.getByText("What this proves")).toBeInTheDocument();
    expect(screen.getByText("What this does not prove")).toBeInTheDocument();
    expect(screen.getByText("proposer-status-ignored")).toBeInTheDocument();
    expect(screen.getByText("Proposer was wrong")).toBeInTheDocument();
  });

  it("runs a selected demo and renders proposer-wrong run evidence", async () => {
    const user = userEvent.setup();
    let callbacks: any;
    vi.mocked(useDemoRun).mockReturnValue({
      mutate: vi.fn((_req, options) => {
        callbacks = options;
      }),
      isPending: false,
    } as any);
    renderRoute("/demos/proof_carrying_promotion");

    await user.click(screen.getByRole("button", { name: /run demo/i }));
    act(() => {
      callbacks.onSuccess(runResult);
    });

    expect(await screen.findByText("All scenarios passed")).toBeInTheDocument();
    expect(screen.getByText("proposer-wrong")).toBeInTheDocument();
    expect(screen.getByText("certified_entailment")).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "Proof-carrying promotion DAG" })).toBeInTheDocument();
  });
});
