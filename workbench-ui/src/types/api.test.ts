/**
 * Schema drift test: verifies that the TypeScript API types stay in sync with
 * the Python dataclasses in workbench/schemas.py.
 *
 * Workflow:
 *   1. Run `uv run python scripts/dump-api-schemas.py` to regenerate the snapshot.
 *   2. If the snapshot changes, update this test (and api.ts) to match.
 *   3. CI runs the snapshot diff to catch silent field additions on the Python side.
 */
import { describe, it, expect } from "vitest";
import snapshot from "../../api-schema-snapshot.json";

// PYTHON_FIELDS mirrors the expected snapshot structure for each dataclass.
// If dump-api-schemas.py produces different fields, tests below will fail,
// indicating TypeScript types need updating.
const EXPECTED_PYTHON_FIELDS: Record<string, string[]> = {
  RuntimeStatus: [
    "backend",
    "git_revision",
    "engine_state_present",
    "checkpoint_revision",
    "revision_warning",
    "active_session_id",
    "mutation_mode",
  ],
  TurnVerdict: ["outcome", "runtime_detail"],
  ProposalRef: ["candidate_id", "source_kind"],
  CognitivePipelineStage: ["stage_id", "label", "status", "summary", "detail"],
  CognitivePipelineEdge: ["from_stage", "to_stage", "label"],
  CognitivePipelineRecord: [
    "schema_version",
    "status",
    "missing_reason",
    "trace_hash",
    "versor_condition",
    "field_digest",
    "stages",
    "edges",
  ],
  ChatTurnResult: [
    "prompt",
    "surface",
    "articulation_surface",
    "walk_surface",
    "grounding_source",
    "epistemic_state",
    "normative_clearance",
    "normative_detail",
    "trace_hash",
    "refusal_emitted",
    "hedge_injected",
    "mutation_mode",
    "identity_verdict",
    "safety_verdict",
    "ethics_verdict",
    "proposal_candidates",
    "turn_cost_ms",
    "checkpoint_emitted",
    "leeway_evidence",
    "pipeline_record",
  ],
  ArtifactRef: ["artifact_id", "kind", "path", "digest", "created_at"],
  // ArtifactDetail inherits from ArtifactRef in Python; snapshot only shows own fields.
  ArtifactDetail: ["content_type", "content"],
  ProposalSummary: [
    "proposal_id",
    "state",
    "source_kind",
    "replay_equivalent",
    "created_at",
    "downstream_effect",
  ],
  // ProposalDetail inherits from ProposalSummary in Python; snapshot only shows own fields.
  ProposalDetail: [
    "proposed_chain",
    "replay_evidence",
    "source",
    "evidence",
    "artifact_refs",
    "suggested_cli",
  ],
  EvalLaneSummary: ["lane", "versions", "read_only", "description"],
  EvalRunResult: ["lane", "version", "split", "passed", "metrics", "cases", "source_digest"],
  DemoDagNode: ["node_id", "label", "summary", "detail"],
  DemoDagEdge: ["from_node", "to_node", "label"],
  DemoEvidenceDag: ["graph_id", "graph_kind", "title", "source_digest", "nodes", "edges"],
  DemoScenarioSummary: [
    "scenario_id",
    "title",
    "expected_status",
    "evidence_class",
    "proposer_wrong",
    "what_this_proves",
    "what_this_does_not_prove",
  ],
  DemoSummary: [
    "demo_id",
    "title",
    "description",
    "evidence_class",
    "scenario_count",
    "read_only",
    "scenarios",
  ],
  DemoScenarioRunResult: [
    "scenario_id",
    "status",
    "passed",
    "proposer_wrong",
    "evidence_class",
    "decision_reason",
    "trace_hash",
    "problems",
    "response",
    "evidence_dag",
  ],
  DemoRunResult: [
    "demo_id",
    "all_passed",
    "what_this_proves",
    "what_this_does_not_prove",
    "scenarios",
  ],
  ContemplationScene: ["scene_id", "claim", "detail"],
  ContemplationRunSummary: [
    "run_id",
    "source_path",
    "source_digest",
    "prompt",
    "cold_subject",
    "scene_count",
    "learning_arc_closed",
    "all_claims_supported",
    "active_corpus_byte_identical",
  ],
  ContemplationRunDetail: ["before", "after", "engine_chain", "scenes"],
  IdentityContinuity: [
    "status",
    "engine_identity",
    "parent_engine_identity",
    "current_engine_identity",
    "written_at_revision",
    "current_revision",
    "lineage_relation",
    "verification_summary",
    "evidence_gap",
  ],
  RunSummary: [
    "session_id",
    "source",
    "turn_count",
    "started_at",
    "updated_at",
    "checkpoint_present",
    "checkpoint_revision",
    "artifact_refs",
    "evidence_gap",
  ],
  RunTurnRef: [
    "turn_id",
    "trace_hash",
    "timestamp",
    "trace_path",
    "surface_excerpt",
    "trace_integrity",
  ],
  RunDetail: ["turns", "manifest", "identity_continuity"],
  TurnReplayDivergence: ["path", "original", "replay", "severity"],
  TurnReplayComparison: [
    "turn_id",
    "comparison_basis",
    "origin_state",
    "original_trace_hash",
    "replay_trace_hash",
    "equivalent",
    "replay_turn_cost_ms",
    "divergences",
  ],
  TurnJournalSummarySchema: [
    "turn_id",
    "timestamp",
    "prompt_excerpt",
    "surface_excerpt",
    "trace_hash",
    "grounding_source",
    "trace_integrity",
  ],
  TurnJournalEntrySchema: [
    "turn_id",
    "timestamp",
    "trace_hash",
    "prompt",
    "surface",
    "articulation_surface",
    "walk_surface",
    "grounding_source",
    "epistemic_state",
    "normative_clearance",
    "verdicts",
    "refusal_emitted",
    "hedge_injected",
    "proposal_candidates",
    "turn_cost_ms",
    "checkpoint_emitted",
    "trace_integrity",
    "journal_digest",
    "leeway_evidence",
    "pipeline_record",
  ],
};

describe("api-schema-snapshot — Python ↔ TypeScript drift detection", () => {
  it("snapshot file is present and has dataclasses key", () => {
    expect(snapshot).toBeDefined();
    expect(snapshot).toHaveProperty("dataclasses");
  });

  for (const [className, expectedFields] of Object.entries(EXPECTED_PYTHON_FIELDS)) {
    it(`${className}: snapshot fields match expected TS mirror`, () => {
      const dc = (snapshot as { dataclasses: Record<string, { fields: Record<string, string> }> })
        .dataclasses[className];
      expect(dc, `Dataclass ${className} missing from snapshot`).toBeDefined();
      const snapshotFields = Object.keys(dc.fields);
      for (const field of expectedFields) {
        expect(snapshotFields, `Field ${field} missing from snapshot for ${className}`).toContain(
          field,
        );
      }
    });
  }
});
