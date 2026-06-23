import { describe, expect, it, vi } from "vitest";
import type { ConstructionEvidence } from "../../types/constructionEvidence";
import {
  TRACE_CONSTRUCTION_EMPTY_LABEL,
  TRACE_CONSTRUCTION_ERROR_MUTATION_STATUS,
  TRACE_CONSTRUCTION_LOADING_LABEL,
  fetchTraceConstructionWith,
  traceConstructionPath,
  traceConstructionReproducer,
} from "./constructionEvidenceEndpoint";

const evidence: ConstructionEvidence = {
  schema_version: "construction_evidence_v1",
  turn_id: 7,
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
};

describe("construction evidence endpoint helpers", () => {
  it("builds the trace construction endpoint path", () => {
    expect(traceConstructionPath(7)).toBe("/trace/7/construction");
  });

  it("fetches construction evidence through an injected fetcher", async () => {
    const fetcher = vi.fn(<T,>(_path: string): Promise<T> => Promise.resolve(evidence as T));

    await expect(
      fetchTraceConstructionWith(7, fetcher as unknown as <T>(path: string) => Promise<T>),
    ).resolves.toBe(evidence);
    expect(fetcher).toHaveBeenCalledWith("/trace/7/construction");
  });

  it("defines loading/empty/error labels for route conformance", () => {
    expect(TRACE_CONSTRUCTION_LOADING_LABEL).toBe("Loading construction evidence...");
    expect(TRACE_CONSTRUCTION_EMPTY_LABEL).toBe("No construction evidence recorded for this turn.");
    expect(TRACE_CONSTRUCTION_ERROR_MUTATION_STATUS).toBe("No trace mutation occurred.");
  });

  it("builds a copyable reproducer", () => {
    expect(traceConstructionReproducer(7)).toBe("curl /trace/7/construction");
  });
});
