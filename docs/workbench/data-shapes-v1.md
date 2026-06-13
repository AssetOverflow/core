# CORE Workbench v1 — Data Shape Contracts

Status: draft

This document defines the canonical UI-facing shapes for CORE Workbench v1.
They are intentionally narrower than internal runtime structures.

The workbench should expose enough information to audit and replay behavior
without leaking unnecessary internals into the UI contract.

## Naming conventions

- IDs are stable strings.
- Hashes/digests should include an algorithm prefix when possible.
- Timestamps are ISO-8601 UTC strings.
- Unknown values should be explicit (`"unknown"`) rather than omitted when they
  materially affect audit interpretation.

---

# Envelope

```ts
export type WorkbenchResponse<T> =
  | {
      ok: true;
      generated_at: string;
      data: T;
    }
  | {
      ok: false;
      generated_at: string;
      error: WorkbenchError;
    };

export type WorkbenchError = {
  code:
    | "bad_request"
    | "evidence_unavailable"
    | "not_found"
    | "unsupported"
    | "read_error"
    | "eval_failed"
    | "runtime_unavailable";
  message: string;
  detail?: unknown;
};
```

---

# Runtime

```ts
export type RuntimeStatus = {
  backend: "numpy" | "mlx" | "rust" | "unknown";
  git_revision: string;
  engine_state_present: boolean;
  checkpoint_revision: string | "unknown";
  revision_warning: boolean;
  active_session_id: string | null;
  mutation_mode: "read_only" | "runtime_turn";
};
```

`mutation_mode` is UI-facing.  It does not redefine runtime doctrine.  It tells
an operator whether the current surface is purely reading artifacts or executing
normal runtime turns.

---

# Chat

```ts
export type ChatTurnRequest = {
  prompt: string;
};

export type ChatTurnSummary = {
  turn_id: string;
  surface: string;
  grounding_source: string | null;
  trace_hash: string | null;
  replay_available: boolean;
  proposal_state: "none" | "pending" | "accepted" | "rejected" | null;
  mutation_state: "none" | "transient" | "proposal_only" | "ratified";
  leeway_evidence?: LeewayEvidence | null;
  pipeline_record?: CognitivePipelineRecord | null;
  field_evidence?: FieldEvidence | null;
};
```

`surface` is the user-visible response.  The UI must not substitute telemetry
surfaces into the user surface.

---

# Trace

```ts
export type TraceDetail = {
  turn_id: string;
  surface: string;
  articulation_surface: string | null;
  walk_surface: string | null;
  trace_hash: string | null;
  replay_digest: string | null;
  grounding_source: string | null;
  proposal_refs: string[];
  candidate_refs: string[];
  admissibility: {
    rejected_attempts: number | null;
    exhausted: boolean | null;
  };
  pipeline_record?: CognitivePipelineRecord | null;
  field_evidence?: FieldEvidence | null;
  raw?: unknown;
};
```

The trace drawer may show `raw`, but only behind an explicit expand action.

```ts
export type CognitivePipelineStageKind =
  | "input"
  | "intent"
  | "proposition_graph"
  | "articulation_target"
  | "realizer"
  | "walk_telemetry"
  | "trace_hash";

export type CognitivePipelineRecord = {
  schema_version: "cognitive_pipeline_record_v1";
  status: "recorded" | "missing_evidence";
  missing_reason: string | null;
  trace_hash: string | null;
  versor_condition: number | null;
  field_digest: string | null;
  stages: {
    stage_id: CognitivePipelineStageKind;
    label: string;
    status: "recorded" | "missing_evidence";
    summary: string;
    detail: Record<string, unknown>;
  }[];
  edges: {
    from_stage: CognitivePipelineStageKind;
    to_stage: CognitivePipelineStageKind;
    label: string | null;
  }[];
};
```

`pipeline_record` is required for newly journaled turns and nullable for
pre-widening rows.  The UI must render `missing_evidence` when it is absent and
must not reconstruct stage internals from replay as if they were persisted.
The first-class read endpoint is `GET /trace/{turn_id}/pipeline`; it returns a
`CognitivePipelineRecord` directly and uses `status: "missing_evidence"` for
pre-widening rows.  The Trace route renders the record as a deterministic stage
rail, DAG, and selected-stage detail inspector; those views are projections of
`stages` and `edges` only, not replay-derived cognition.

## FieldEvidence (C3 field substrate)

```ts
export type FieldEvidence = {
  schema_version: "field_evidence_v1";
  status: "recorded" | "missing_evidence";
  missing_reason: string | null;
  trace_hash: string | null;
  versor_condition: number | null;       // exact, measured over field_state_after
  versor_condition_ceiling: number;      // 1e-6 — the CLAUDE.md invariant bound
  field_valid: boolean | null;           // versor_condition < ceiling
  field_digest: string | null;           // sha256 of the canonical field bytes
  parent_field_digest: string | null;    // sha256 of field_state_before, or null
  transition_inner_product: number | null; // cga_inner(before, after), or null
};
```

`field_evidence` is the geometry under a turn: only the engine's EXACT scalar
invariants and a content-addressed digest cross the boundary — never the raw
CL(4,1) multivector.  It is required for newly journaled turns and nullable for
pre-widening rows; the UI renders `missing_evidence` when absent and never
reconstructs the field.  `field_valid` is consistency-checked against the
ceiling at construction, so the Field tab can never claim a valid field while
`versor_condition` breaches `1e-6` (the wrong=0 analogue for the geometry).  The
first-class read endpoint is `GET /trace/{turn_id}/field`; it returns a
`FieldEvidence` directly.  The Trace route's **Field** tab renders it as the
measured value against the ceiling, the `cga_inner` transition, and the digests
— inspectable exact numbers and invariant status, no decorative geometry.

---

# Proposal

```ts
export type ProposalSummary = {
  proposal_id: string;
  state: "pending" | "accepted" | "rejected" | "unknown";
  source_kind: string;
  replay_equivalent: boolean | null;
  created_at: string | null;
  downstream_effect: "unknown" | "none" | "observed";
};

export type ProposalDetail = ProposalSummary & {
  proposed_chain: unknown;
  replay_evidence: unknown;
  source: unknown;
  evidence: unknown[];
  artifact_refs: ArtifactRef[];
  suggested_cli?: string;
  leeway_evidence?: LeewayEvidence | null;
};
```

V1 may include `suggested_cli` for copy-only operator review.  It must not
execute it.

```ts
export type LeewayEvidence = {
  class_name: string;
  license: "PROPOSE" | "SERVE" | "blocked" | "unknown";
  theta: number | null;
  claim_disclosure: "approximate" | "verified" | "proposal_only" | "none";
  source_digest: string | null;
  calibration_evidence_ref: string | null;
};
```

`LeewayEvidence` is nullable. The UI may render it when present, but must render
explicit absence when it is null/missing and must never derive class/license/theta
in the frontend.

---

# Eval

```ts
export type EvalLaneSummary = {
  lane: string;
  versions: string[];
  read_only: boolean;
  description: string | null;
};

export type EvalRunRequest = {
  lane: string;
  version?: string;
  split?: "dev" | "public" | "holdout";
};

export type EvalRunResult = {
  lane: string;
  version: string;
  split: string;
  passed: boolean | null;
  metrics: Record<string, unknown>;
  cases: unknown[];
  source_digest?: string;
};
```

The API should initially allow only explicitly safe lanes.  `holdout` should be
disabled unless the backend proves the sealed-eval path is configured.

---

# Demo Evidence DAG

```ts
export type DemoEvidenceDag = {
  graph_id: string;
  graph_kind: "proof_carrying_promotion" | "deductive_entailment";
  title: string;
  source_digest: string | null;
  nodes: {
    node_id: string;
    label: string;
    summary: string;
    detail: Record<string, unknown>;
  }[];
  edges: {
    from_node: string;
    to_node: string;
    label: string | null;
  }[];
};
```

`DemoScenarioRunResult.evidence_dag` is nullable.  It is populated by the
backend reader for proof-carrying coherence promotion and deductive-entailment
authority scenarios from the committed demo authority response.  The UI may
render it with the deterministic DAG primitive but must not infer proof edges
from raw response JSON.

---

# Calibration

```ts
export type CalibrationClass = {
  class_name: string;
  correct: number;
  wrong: number;
  refused: number;
  committed: number;
  reliability_floor: number;
  coverage: number;
  propose_required: number;
  propose_licensed: boolean;
  serve_required: number;
  serve_licensed: boolean;
  source_path: string;
  source_digest: string;
};

export type ServingMetrics = {
  lane: string;
  correct: number;
  refused: number;
  wrong: number;
  sample_count: number;
  source_path: string;
  source_digest: string;
};
```

Reliability and license verdicts are engine-owned derivations from
`core.reliability_gate`; the workbench mirrors the read model.

---

# Contemplation

```ts
export type ContemplationScene = {
  scene_id: string;
  claim: string;
  detail: Record<string, unknown>;
};

export type ContemplationRunSummary = {
  run_id: string;
  source_path: string;
  source_digest: string | null;
  prompt: string | null;
  cold_subject: string | null;
  scene_count: number;
  learning_arc_closed: boolean | null;
  all_claims_supported: boolean | null;
  active_corpus_byte_identical: boolean | null;
};

export type ContemplationRunDetail = ContemplationRunSummary & {
  before: Record<string, unknown> | null;
  after: Record<string, unknown> | null;
  engine_chain: Record<string, unknown> | null;
  scenes: ContemplationScene[];
};
```

Contemplation runs are read-only projections over committed
`contemplation/runs/*.json` reports. `run_id` is the report filename stem,
not a synthesized session id. Scene details remain report-authored evidence;
the route must not promote speculative findings or apply proposals.

---

# Replay

```ts
export type ReplayComparison = {
  artifact_id: string;
  original_hash: string | null;
  replay_hash: string | null;
  equivalent: boolean;
  divergences: ReplayDivergence[];
};

export type ReplayDivergence = {
  path: string;
  original: unknown;
  replay: unknown;
  severity: "info" | "warning" | "failure";
};
```

---

# Artifact

```ts
export type ArtifactRef = {
  artifact_id: string;
  kind:
    | "trace"
    | "eval_result"
    | "proposal"
    | "contemplation_report"
    | "telemetry"
    | "engine_state_manifest"
    | "unknown";
  path: string;
  digest: string | null;
  created_at: string | null;
};

export type ArtifactDetail = ArtifactRef & {
  content_type: "json" | "jsonl" | "text" | "unknown";
  content: unknown;
};
```

Artifact paths must be repo-root constrained.  The backend must never honor an
arbitrary user-supplied filesystem path.

---

# R2 Read Projections

```ts
export type PackSummary = {
  pack_id: string;
  source: "language_pack" | "runtime_pack";
  manifest_path: string;
  version: string | null;
  language: string | null;
  modality: string | null;
  determinism_class: string | null;
  checksum: string | null;
  checksums: Record<string, string>;
};

export type PackDetail = PackSummary & {
  manifest_digest: string;
  manifest: Record<string, unknown>;
};
```

`checksum` and `checksums` are manifest-authored values and must remain
verbatim. `manifest_digest` is the backend-computed digest of the manifest file
bytes.

```ts
export type AuditEvent = {
  event_id: string;
  source:
    | "engine_state_manifest"
    | "math_proposal_log"
    | "operator_telemetry"
    | "reboot_telemetry"
    | "teaching_proposal_log";
  source_path: string;
  timestamp: string | null;
  event_type: string;
  mutation_boundary: boolean;
  summary: string;
  ref_id: string | null;
  payload_digest: string;
  payload: unknown;
};
```

Audit events are projections over existing artifacts. `event_id` and
`payload_digest` are deterministic backend digests; they are not new stored
identifiers.

```ts
export type RunSummary = {
  session_id: string;
  source: "engine_state_manifest" | "turn_journal";
  turn_count: number;
  started_at: string | null;
  updated_at: string | null;
  checkpoint_present: boolean;
  checkpoint_revision: string | null;
  artifact_refs: ArtifactRef[];
  evidence_gap: string | null;
};

export type RunTurnRef = {
  turn_id: number;
  trace_hash: string | null;
  timestamp: string;
  trace_path: string;
  surface_excerpt: string;
};

export type IdentityContinuity = {
  status: "verified" | "break" | "missing_evidence";
  engine_identity: string | null;
  parent_engine_identity: string | null;
  current_engine_identity: string | null;
  written_at_revision: string | null;
  current_revision: string;
  lineage_relation:
    | "self_parent"
    | "descends_from_parent"
    | "missing_parent"
    | "unavailable";
  verification_summary: string;
  evidence_gap: string | null;
};

export type RunDetail = RunSummary & {
  turns: RunTurnRef[];
  manifest: Record<string, unknown> | null;
  identity_continuity: IdentityContinuity | null;
};
```

When no durable per-session id exists, `session_id` names the artifact boundary
(`workbench_turn_journal` or `engine_state_checkpoint`) and `evidence_gap`
states the missing persisted fact.

`identity_continuity` is backend-projected from `engine_state/manifest.json`
plus the current ratified substrate identity. The UI must render this field
directly; it must not infer continuity status by parsing raw manifest JSON.
Legacy manifests that predate `engine_identity` return
`status: "missing_evidence"` instead of a synthesized verdict.

```ts
export type VaultSummary = {
  source_path: string;
  entry_count: number;
  store_count: number;
  reproject_interval: number;
  max_entries: number | null;
  persisted: boolean;
};

export type VaultEntry = {
  entry_index: number;
  epistemic_status: string;
  epistemic_state: string;
  metadata: Record<string, unknown>;
  versor_digest: string | null;
};
```

Vault shapes are available only from persisted `engine_state/session_state.json`
evidence. If absent, the API returns `501 evidence_unavailable`.

---

# UI state tags

These are display-only semantic tags.

```ts
export type TrustBadge =
  | "replay_passed"
  | "replay_failed"
  | "grounded"
  | "ungrounded"
  | "pending_review"
  | "mutation_none"
  | "mutation_transient"
  | "mutation_ratified"
  | "revision_warning"
  | "refusal";
```

Colors should be mapped only to these operational meanings.

---

# Backward compatibility rule

Internal runtime objects may evolve faster than the workbench UI.  The API layer
must normalize into these v1 shapes so the frontend does not depend on private
runtime structure.
