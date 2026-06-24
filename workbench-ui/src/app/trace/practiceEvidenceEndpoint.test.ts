import { describe, expect, it, vi } from "vitest";
import type { PracticeEvidence } from "../../types/practiceEvidence";
import {
  fetchTracePracticeWith,
  tracePracticePath,
  tracePracticeReproducer,
} from "./practiceEvidenceEndpoint";

const evidence: PracticeEvidence = {
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

describe("practice evidence endpoint helpers", () => {
  it("builds encoded trace practice paths", () => {
    expect(tracePracticePath(7)).toBe("/trace/7/practice");
    expect(tracePracticeReproducer(7)).toBe("curl /trace/7/practice");
  });

  it("fetches practice evidence through an injected fetcher", async () => {
    const fetcher = vi.fn(<T,>(_path: string): Promise<T> => Promise.resolve(evidence as T));

    await expect(
      fetchTracePracticeWith(7, fetcher as unknown as <T>(path: string) => Promise<T>),
    ).resolves.toBe(evidence);
    expect(fetcher).toHaveBeenCalledWith("/trace/7/practice");
  });
});
