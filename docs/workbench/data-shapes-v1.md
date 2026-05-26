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
  raw?: unknown;
};
```

The trace drawer may show `raw`, but only behind an explicit expand action.

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
};
```

V1 may include `suggested_cli` for copy-only operator review.  It must not
execute it.

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
