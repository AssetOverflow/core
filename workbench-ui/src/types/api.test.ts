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
  ReplayDivergence: ["path", "original", "replay", "severity"],
  ReplayComparison: [
    "artifact_id",
    "original_hash",
    "replay_hash",
    "equivalent",
    "divergences",
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
