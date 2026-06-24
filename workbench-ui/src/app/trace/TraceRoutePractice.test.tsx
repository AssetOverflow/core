import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createTestQueryClient } from "../../test/createTestQueryClient";
import { EvidenceProvider } from "../evidenceContext";
import { TraceRoute } from "./TraceRoute";

function jsonOk(data: unknown) {
  return Promise.resolve({
    json: () => Promise.resolve({ ok: true, generated_at: "now", data }),
  });
}

function traceSummary(turnId: number) {
  return {
    turn_id: turnId,
    timestamp: "2026-06-23T20:00:00Z",
    prompt_excerpt: "Lena has 3 marbles.",
    surface_excerpt: "Trace surface",
    trace_hash: "sha256:777777777777abcdef",
    grounding_source: "pack",
    trace_integrity: "pipeline_trace",
  };
}

function traceEntry(turnId: number) {
  const summary = traceSummary(turnId);
  return {
    ...summary,
    prompt: "Lena has 3 marbles.",
    surface: "Trace surface",
    articulation_surface: "Trace articulation",
    walk_surface: "Trace walk",
    epistemic_state: "evidenced",
    normative_clearance: "cleared",
    verdicts: {
      identity: { outcome: "cleared", runtime_detail: "identity ok" },
      safety: { outcome: "cleared", runtime_detail: "safety ok" },
      ethics: { outcome: "cleared", runtime_detail: "ethics ok" },
    },
    refusal_emitted: false,
    hedge_injected: false,
    proposal_candidates: [],
    turn_cost_ms: 12,
    checkpoint_emitted: true,
    journal_digest: "sha256:journal777abcdef",
    pipeline_record: null,
  };
}

function pipelineRecord() {
  return {
    schema_version: "cognitive_pipeline_record_v1",
    status: "missing_evidence",
    missing_reason: "pipeline_record_not_persisted",
    trace_hash: "sha256:777777777777abcdef",
    versor_condition: null,
    field_digest: null,
    stages: [],
    edges: [],
  };
}

function fieldEvidence() {
  return {
    schema_version: "field_evidence_v1",
    status: "missing_evidence",
    missing_reason: "field evidence was not persisted for this turn",
    trace_hash: "sha256:777777777777abcdef",
    versor_condition: null,
    versor_condition_ceiling: 0.000001,
    field_valid: null,
    field_digest: null,
    parent_field_digest: null,
    transition_inner_product: null,
  };
}

function evidenceBundle(turnId: number) {
  return {
    schema_version: "evidence_bundle_v1",
    turn_id: turnId,
    generated_from: "turn_journal",
    trace_hash: "sha256:777777777777abcdef",
    trace_integrity: "pipeline_trace",
    prompt: "Lena has 3 marbles.",
    surface: "Trace surface",
    grounding_source: "pack",
    epistemic_state: "evidenced",
    normative_clearance: "cleared",
    refusal_emitted: false,
    journal_digest: "sha256:journal777abcdef",
    pipeline_record: null,
    field_evidence: null,
    leeway_evidence: null,
    replay_reproducer: `core replay turn ${turnId}`,
    bundle_digest: "sha256:bundle777abcdef",
  };
}

function missingPracticeEvidence(turnId: number) {
  return {
    schema_version: "practice_evidence_v1",
    turn_id: turnId,
    status: "missing_evidence",
    missing_reason: "practice evidence was not persisted for this turn",
    record_kind: null,
    practice_disposition: null,
    chain: [],
    sealed_trace: null,
    trace_refusal: null,
    diagnostic_only: true,
    serving_allowed: false,
    mutation_allowed: false,
    replay_execution_allowed: false,
    replay_executed_by_workbench: false,
  };
}

function recordedPracticeEvidence(turnId: number) {
  return {
    ...missingPracticeEvidence(turnId),
    status: "recorded",
    missing_reason: null,
    record_kind: "sealed_trace",
    practice_disposition: "accepted",
    chain: [
      {
        kind: "problem_frame",
        status: "recorded",
        refs: ["problem_frame.0"],
        summary: "problem frame summary",
      },
    ],
    sealed_trace: {
      trace_id: "trace_123",
      trace_policy_version: "v1",
      input_digest: "sha256:input",
      problem_frame_digest: "sha256:pf",
      original_contract_assessment_id: "assessment_1",
      residual_ids: [],
      search_gate_decision_id: "decision_1",
      compute_budget_id: "budget_1",
      geometric_search_run_id: "run_1",
      candidate_attempt_ids: [],
      candidate_attempt_binding_ids: [],
      replay_result_ids: [],
      replay_refusal_ids: [],
      upstream_identity_chain: [],
      practice_disposition: "accepted",
      trace_records: [],
      evidence_spans: [
        {
          text: "Lena has 3 marbles.",
          start: 0,
          end: 18,
          sentence_index: 0,
        },
      ],
      created_by_policy: "policy_1",
      explanation: "all good",
    },
  };
}

function stubTraceFetch(practiceEvidence: unknown) {
  const fetchMock = vi.fn((input: unknown) => {
    const path = new URL(String(input)).pathname;
    if (path === "/trace/turns") {
      return jsonOk({ items: [traceSummary(7)] });
    }
    if (path === "/trace/7") {
      return jsonOk(traceEntry(7));
    }
    if (path === "/trace/7/pipeline") {
      return jsonOk(pipelineRecord());
    }
    if (path === "/trace/7/field") {
      return jsonOk(fieldEvidence());
    }
    if (path === "/trace/7/bundle") {
      return jsonOk(evidenceBundle(7));
    }
    if (path === "/trace/7/construction") {
      return jsonOk({});
    }
    if (path === "/trace/7/practice") {
      return jsonOk(practiceEvidence);
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

function renderRoute() {
  return render(
    <QueryClientProvider client={createTestQueryClient()}>
      <MemoryRouter initialEntries={["/trace/7"]}>
        <EvidenceProvider>
          <Routes>
            <Route path="/trace/:turnId?" element={<TraceRoute />} />
          </Routes>
        </EvidenceProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

const offsetDescriptors = {
  offsetHeight: Object.getOwnPropertyDescriptor(HTMLElement.prototype, "offsetHeight"),
  offsetWidth: Object.getOwnPropertyDescriptor(HTMLElement.prototype, "offsetWidth"),
};

describe("TraceRoute practice tab", () => {
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

  it("fetches practice evidence through the trace practice endpoint", async () => {
    const fetchMock = stubTraceFetch(missingPracticeEvidence(7));
    const user = userEvent.setup();
    renderRoute();

    await user.click(await screen.findByRole("tab", { name: "Practice" }));

    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining("/trace/7/practice"),
        expect.any(Object),
      ),
    );
    const tab = await screen.findByTestId("practice-evidence-panel");
    expect(within(tab).getAllByText("practice evidence was not persisted for this turn")[0]).toBeInTheDocument();
    expect(within(tab).getByText("diagnostic_only")).toBeInTheDocument();
    expect(within(tab).getByText("serving_allowed")).toBeInTheDocument();
    expect(within(tab).getByText("curl /trace/7/practice")).toBeInTheDocument();
  });

  it("renders recorded practice evidence", async () => {
    stubTraceFetch(recordedPracticeEvidence(7));
    const user = userEvent.setup();
    renderRoute();

    await user.click(await screen.findByRole("tab", { name: "Practice" }));

    const tab = await screen.findByTestId("practice-evidence-panel");
    expect(within(tab).getAllByText("problem_frame")[0]).toBeInTheDocument();
    expect(within(tab).getByText("problem frame summary")).toBeInTheDocument();
    expect(within(tab).getAllByText("trace_123")[0]).toBeInTheDocument();
    expect(within(tab).getAllByText(/Lena has 3 marbles\./)[0]).toBeInTheDocument();
    expect(within(tab).getByText("diagnostic_only")).toBeInTheDocument();
    expect(within(tab).getByText("serving_allowed")).toBeInTheDocument();
  });
});
