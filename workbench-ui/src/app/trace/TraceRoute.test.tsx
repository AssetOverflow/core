import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
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
import type { CognitivePipelineRecord, TurnJournalEntry, TurnJournalSummary } from "../../types/api";
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
    trace_integrity: "pipeline_trace",
  },
  {
    turn_id: 2,
    timestamp: "2026-06-12T18:01:00Z",
    prompt_excerpt: "Second prompt",
    surface_excerpt: "Second response",
    trace_hash: "sha256:222222222222abcdef",
    grounding_source: "teaching",
    trace_integrity: "pipeline_trace",
  },
  {
    turn_id: 3,
    timestamp: "2026-06-12T18:02:00Z",
    prompt_excerpt: "Third prompt",
    surface_excerpt: "Third response",
    trace_hash: "sha256:333333333333abcdef",
    grounding_source: "vault",
    trace_integrity: "pipeline_trace",
  },
];

function pipelineRecord(traceHash: string | null): CognitivePipelineRecord {
  const stages = [
    "input",
    "intent",
    "proposition_graph",
    "articulation_target",
    "realizer",
    "walk_telemetry",
    "trace_hash",
  ] as const;
  return {
    schema_version: "cognitive_pipeline_record_v1",
    status: "recorded",
    missing_reason: null,
    trace_hash: traceHash,
    versor_condition: 0,
    field_digest: null,
    stages: stages.map((stage) => ({
      stage_id: stage,
      label: stage === "proposition_graph" ? "PropositionGraph" : stage,
      status: "recorded",
      summary: stage,
      detail:
        stage === "input"
          ? { stage, input_text: "fixture prompt" }
          : stage === "realizer"
            ? { stage, surface: "fixture realization" }
            : { stage },
    })),
    edges: [
      { from_stage: "input", to_stage: "intent", label: "classify" },
      { from_stage: "intent", to_stage: "proposition_graph", label: "plan graph" },
      { from_stage: "proposition_graph", to_stage: "articulation_target", label: "topology" },
      { from_stage: "articulation_target", to_stage: "realizer", label: "realize" },
      { from_stage: "realizer", to_stage: "walk_telemetry", label: "retain evidence" },
      { from_stage: "walk_telemetry", to_stage: "trace_hash", label: "seal" },
    ],
  };
}

function missingPipelineRecord(traceHash: string | null): CognitivePipelineRecord {
  return {
    schema_version: "cognitive_pipeline_record_v1",
    status: "missing_evidence",
    missing_reason: "pipeline_record_not_persisted",
    trace_hash: traceHash,
    versor_condition: null,
    field_digest: null,
    stages: [],
    edges: [],
  };
}

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
    trace_integrity: summary.trace_integrity,
    journal_digest: `sha256:journal${summary.turn_id}abcdef`,
    pipeline_record: pipelineRecord(summary.trace_hash),
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

function stubTraceFetch(
  items: TurnJournalSummary[] = summaries,
  entryFactory: (id: number) => TurnJournalEntry = entry,
  pipelineFactory: (id: number) => CognitivePipelineRecord = (id) =>
    pipelineRecord(entry(id).trace_hash),
) {
  const fetchMock = vi.fn((input: unknown) => {
    const path = new URL(String(input)).pathname;
    if (path === "/trace/turns") {
      return Promise.resolve({
        json: () => Promise.resolve({ ok: true, generated_at: "now", data: { items } }),
      });
    }
    const pipelineMatch = path.match(/^\/trace\/(\d+)\/pipeline$/);
    if (pipelineMatch) {
      return Promise.resolve({
        json: () =>
          Promise.resolve({
            ok: true,
            generated_at: "now",
            data: pipelineFactory(Number(pipelineMatch[1])),
          }),
      });
    }
    const bundleMatch = path.match(/^\/trace\/(\d+)\/bundle$/);
    if (bundleMatch) {
      const id = Number(bundleMatch[1]);
      return Promise.resolve({
        json: () =>
          Promise.resolve({
            ok: true,
            generated_at: "now",
            data: {
              schema_version: "evidence_bundle_v1",
              turn_id: id,
              generated_from: "turn_journal",
              trace_hash: `sha256:trace${id}`,
              trace_integrity: "pipeline_trace",
              prompt: "p",
              surface: "s",
              grounding_source: "pack",
              epistemic_state: "evidenced",
              normative_clearance: "cleared",
              refusal_emitted: false,
              journal_digest: `sha256:journal${id}`,
              pipeline_record: null,
              field_evidence: null,
              leeway_evidence: null,
              replay_reproducer: `core replay turn ${id} # re-run sealed; expect trace_hash == sha256:trace${id}`,
              bundle_digest: `sha256:bundle${id}abcdef0123456789`,
            },
          }),
      });
    }
    const constructionMatch = path.match(/^\/trace\/(\d+)\/construction$/);
    if (constructionMatch) {
      const id = Number(constructionMatch[1]);
      return Promise.resolve({
        json: () =>
          Promise.resolve({
            ok: true,
            generated_at: "now",
            data: {
              schema_version: "construction_evidence_v1",
              turn_id: id,
              status: "missing_evidence",
              missing_reason: "construction evidence was not persisted for this turn",
              problem_text: null,
              proposals: [],
              mentions: [],
              bindings: [],
              bound_relations: [],
              contract_assessments: [],
              diagnostic_only: true,
              serving_allowed: false,
            },
          }),
      });
    }
    const match = path.match(/^\/trace\/(\d+)$/);
    if (match) {
      return Promise.resolve({
        json: () =>
          Promise.resolve({ ok: true, generated_at: "now", data: entryFactory(Number(match[1])) }),
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
    expect(screen.getByText("3/3")).toBeInTheDocument();
  });

  it("classifies hashless journal rows as legacy, not trace proof", async () => {
    stubTraceFetch([
      summaries[0],
      {
        ...summaries[1],
        trace_hash: null,
        trace_integrity: "legacy_unhashed",
      },
    ]);
    renderRoute();

    expect(await screen.findByText("1/2")).toBeInTheDocument();
    expect(screen.getAllByText("legacy_unhashed").length).toBeGreaterThan(0);
    expect(screen.queryByText("no hash")).not.toBeInTheDocument();
  });

  it("selecting a turn writes /trace/<turnId> with replace and shows evidence", async () => {
    stubTraceFetch();
    const user = userEvent.setup();
    renderRoute();

    await user.click(await screen.findByText("First prompt"));

    await waitFor(() => expect(screen.getByTestId("location")).toHaveTextContent("/trace/1"));
    expect(screen.getByTestId("nav-type")).toHaveTextContent("REPLACE");
    await user.click(await screen.findByRole("tab", { name: "Surfaces" }));
    expect(await screen.findByText("User response for turn 1")).toBeInTheDocument();
  });

  it("renders the three surface labels distinctly", async () => {
    stubTraceFetch();
    const user = userEvent.setup();
    renderRoute("/trace/2");

    await user.click(await screen.findByRole("tab", { name: "Surfaces" }));
    expect(await screen.findByText("User Surface (response)")).toBeInTheDocument();
    expect(screen.getByText("Articulation Surface (realizer)")).toBeInTheDocument();
    expect(screen.getByText("Walk Surface (telemetry/evidence)")).toBeInTheDocument();
  });

  it("exports a citable, downloadable evidence bundle", async () => {
    // Set only the two object-URL methods (jsdom lacks them); leave the URL
    // constructor intact so the fetch mock's `new URL()` keeps working.
    const createObjectURL = vi.fn(() => "blob:mock-bundle");
    const revokeObjectURL = vi.fn();
    const originalCreate = URL.createObjectURL;
    const originalRevoke = URL.revokeObjectURL;
    URL.createObjectURL = createObjectURL as typeof URL.createObjectURL;
    URL.revokeObjectURL = revokeObjectURL as typeof URL.revokeObjectURL;
    stubTraceFetch();
    const user = userEvent.setup();
    renderRoute("/trace/2");

    await user.click(await screen.findByRole("tab", { name: "Bundle" }));

    const bundle = await screen.findByTestId("evidence-bundle");
    // The citable digest is shown (truncated form of the content address).
    expect(within(bundle).getByText(/bundle2abcdef0123/)).toBeInTheDocument();
    // "What this proves / does not prove" honesty is present.
    expect(within(bundle).getByText(/Does not prove:/)).toBeInTheDocument();
    // A deterministic download anchor is offered.
    const download = within(bundle).getByTestId("bundle-download");
    expect(download).toHaveAttribute("href", "blob:mock-bundle");
    expect(download.getAttribute("download")).toContain("evidence-bundle-turn-2");
    expect(createObjectURL).toHaveBeenCalled();

    URL.createObjectURL = originalCreate;
    URL.revokeObjectURL = originalRevoke;
  });

  it("renders the persisted cognitive pipeline as a deterministic DAG", async () => {
    stubTraceFetch();
    renderRoute("/trace/2");

    expect(await screen.findByRole("img", { name: "Cognitive pipeline DAG" })).toBeInTheDocument();
    expect(screen.getByText("cognitive_pipeline_record_v1")).toBeInTheDocument();
    expect(screen.getAllByText("PropositionGraph").length).toBeGreaterThan(0);
    expect(screen.getByText("valid")).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Selected pipeline stage detail" })).toBeInTheDocument();
    expect(screen.getByText(/fixture prompt/)).toBeInTheDocument();
  });

  it("selects pipeline stages from the deterministic stage rail", async () => {
    stubTraceFetch();
    const user = userEvent.setup();
    renderRoute("/trace/2");

    const rail = await screen.findByRole("region", { name: "Pipeline stages" });
    await user.click(within(rail).getByRole("button", { name: /realizer/i }));

    expect(screen.getByText(/fixture realization/)).toBeInTheDocument();
    expect(within(rail).getByRole("button", { name: /realizer/i })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
  });

  it("shows missing evidence for pre-widening turns without a pipeline record", async () => {
    stubTraceFetch(
      summaries,
      (id) => ({ ...entry(id), pipeline_record: null }),
      (id) => missingPipelineRecord(entry(id).trace_hash),
    );
    renderRoute("/trace/2");

    expect(await screen.findByText("missing_evidence")).toBeInTheDocument();
    expect(screen.getByText("Pipeline stage evidence was not persisted for this turn.")).toBeInTheDocument();
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

    expect(await screen.findByRole("img", { name: "Cognitive pipeline DAG" })).toBeInTheDocument();
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
