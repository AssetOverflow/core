import { describe, expect, it } from "vitest";
import type { PracticeEvidence } from "../../types/practiceEvidence";
import { practiceEvidencePanelModel } from "./practiceEvidencePanelModel";

const missingEvidence: PracticeEvidence = {
  schema_version: "practice_evidence_v1",
  turn_id: 7,
  status: "missing_evidence",
  missing_reason: "sealed practice evidence was not persisted for this turn",
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

function sealedTraceEvidence(): PracticeEvidence {
  return {
    ...missingEvidence,
    status: "recorded",
    missing_reason: null,
    record_kind: "sealed_trace",
    practice_disposition: "sealed",
    chain: [
      {
        kind: "problem_frame",
        status: "recorded",
        refs: ["pf_123"],
        summary: "Problem frame digest bound into the sealed practice trace.",
      },
      {
        kind: "geometric_search_run",
        status: "recorded",
        refs: ["gsr_1"],
        summary: "Geometric search run identity; Workbench does not execute search.",
      },
      {
        kind: "replay_results",
        status: "missing_evidence",
        refs: [],
        summary: "Replay adapter result identities; Workbench does not run replay here.",
      },
    ],
    sealed_trace: {
      trace_id: "spt_1",
      trace_policy_version: "sealed-practice-v1",
      input_digest: "input_sha",
      problem_frame_digest: "pf_123",
      original_contract_assessment_id: "ca_1",
      residual_ids: ["res_1"],
      search_gate_decision_id: "sg_1",
      compute_budget_id: "budget_1",
      geometric_search_run_id: "gsr_1",
      candidate_attempt_ids: ["attempt_1"],
      candidate_attempt_binding_ids: ["binding_1"],
      replay_result_ids: [],
      replay_refusal_ids: ["rr_1"],
      upstream_identity_chain: ["pf_123", "ca_1", "res_1", "sg_1", "budget_1", "gsr_1"],
      practice_disposition: "sealed",
      trace_records: ["record_1"],
      evidence_spans: [{ text: "Lena has 3 marbles.", start: 0, end: 20, sentence_index: 0 }],
      created_by_policy: "sealed-practice-v1",
      explanation: "sealed diagnostic practice trace",
    },
    trace_refusal: null,
  };
}

function refusalEvidence(): PracticeEvidence {
  return {
    ...missingEvidence,
    status: "recorded",
    missing_reason: null,
    record_kind: "trace_refusal",
    practice_disposition: "refused",
    chain: [
      {
        kind: "trace_refusal",
        status: "recorded",
        refs: ["ptr_1"],
        summary: "Practice trace refused before a sealed practice trace could be projected.",
      },
    ],
    trace_refusal: {
      trace_refusal_id: "ptr_1",
      trace_policy_version: "sealed-practice-v1",
      input_digest: null,
      practice_disposition: "refused",
      reason_codes: ["missing_residual"],
      explanation: "no residual target",
    },
    sealed_trace: null,
  };
}

describe("practice evidence panel model", () => {
  it("models missing evidence honestly", () => {
    const model = practiceEvidencePanelModel(missingEvidence);

    expect(model.status).toBe("missing_evidence");
    expect(model.emptyMessage).toBe("sealed practice evidence was not persisted for this turn");
    expect(model.reproducer).toBe("curl /trace/7/practice");
    expect(model.authorityRows).toEqual([
      { key: "schema_version", value: "practice_evidence_v1" },
      { key: "status", value: "missing_evidence" },
      { key: "record_kind", value: "none" },
      { key: "practice_disposition", value: "none" },
      { key: "diagnostic_only", value: "true" },
      { key: "serving_allowed", value: "false" },
      { key: "mutation_allowed", value: "false" },
      { key: "replay_execution_allowed", value: "false" },
      { key: "replay_executed_by_workbench", value: "false" },
      { key: "missing_reason", value: "sealed practice evidence was not persisted for this turn" },
    ]);
    expect(model.countRows).toEqual([
      { key: "chain_cards", value: "0" },
      { key: "sealed_trace", value: "0" },
      { key: "trace_refusal", value: "0" },
      { key: "source_spans", value: "0" },
    ]);
    expect(model.chainRows).toEqual([]);
    expect(model.sourceSpanRows).toEqual([]);
    expect(model.showRaw).toBe(false);
  });

  it("models a recorded sealed practice trace without granting authority", () => {
    const model = practiceEvidencePanelModel(sealedTraceEvidence());

    expect(model.emptyMessage).toBe(null);
    expect(model.showRaw).toBe(true);
    expect(model.countRows).toContainEqual({ key: "chain_cards", value: "3" });
    expect(model.chainRows).toEqual([
      { key: "problem_frame", value: "recorded — pf_123" },
      { key: "geometric_search_run", value: "recorded — gsr_1" },
      { key: "replay_results", value: "missing_evidence — none" },
    ]);
    expect(model.authorityRows).toEqual(
      expect.arrayContaining([
        { key: "diagnostic_only", value: "true" },
        { key: "serving_allowed", value: "false" },
        { key: "mutation_allowed", value: "false" },
        { key: "replay_execution_allowed", value: "false" },
        { key: "replay_executed_by_workbench", value: "false" },
      ]),
    );

    const chain = model.detailSections.find((section) => section.title === "Evidence chain");
    expect(chain?.items[1]).toMatchObject({
      title: "card 2: geometric_search_run",
      rows: expect.arrayContaining([
        {
          key: "authority",
          value:
            "identity card only; Workbench does not execute search, replay, operators, sealing, or mutation",
        },
      ]),
    });

    const sealed = model.detailSections.find((section) => section.title === "Sealed trace");
    expect(sealed?.items[0]?.rows ?? []).toEqual(
      expect.arrayContaining([
        { key: "geometric_search_run_id", value: "gsr_1" },
        { key: "replay_refusal_ids", value: "rr_1" },
      ]),
    );
    expect(model.sourceSpanRows).toEqual([
      { key: "sealed_trace.1", value: "0:20 Lena has 3 marbles. (sentence 0)" },
    ]);
  });

  it("models practice trace refusals", () => {
    const model = practiceEvidencePanelModel(refusalEvidence());

    expect(model.emptyMessage).toBe(null);
    expect(model.countRows).toContainEqual({ key: "trace_refusal", value: "1" });
    expect(model.chainRows).toEqual([{ key: "trace_refusal", value: "recorded — ptr_1" }]);

    const refusal = model.detailSections.find((section) => section.title === "Trace refusal");
    expect(refusal?.items[0]?.rows ?? []).toEqual(
      expect.arrayContaining([
        { key: "trace_refusal_id", value: "ptr_1" },
        { key: "reason_codes", value: "missing_residual" },
        { key: "explanation", value: "no residual target" },
      ]),
    );
  });
});