# CORE Workbench API Contract v1

Status: draft
Scope: read-only local operator API

This contract defines the initial API surface for CORE Workbench v1.

The API exists to expose:

- runtime observability,
- replay evidence,
- proposal visibility,
- eval visibility,
- and trace inspection

without widening the mutation surface.

## Transport

- HTTP JSON
- optional websocket stream later
- local-first (`127.0.0.1`) in v1

## Response envelope

All responses MUST include `generated_at` as an ISO-8601 UTC timestamp.
`generated_at` is wall-clock UTC and not part of replay state. Clients hashing
or caching responses must exclude this field.
Successful responses:

```json
{
  "ok": true,
  "generated_at": "2026-05-26T00:00:00Z",
  "data": {}
}
```

Errors:

```json
{
  "ok": false,
  "generated_at": "2026-05-26T00:00:00Z",
  "error": {
    "code": "not_found",
    "message": "artifact not found"
  }
}
```

W-026 error codes:

- `bad_request`
- `evidence_unavailable`
- `not_found`
- `unsupported`
- `read_error`
- `eval_failed`
- `runtime_unavailable`

`unauthorized` is reserved for a later auth ADR.  W-026 remains unauthenticated
and local-only by default.

Exception mapping:

| Condition | HTTP status | Error code |
|---|---:|---|
| malformed request, invalid path, unsafe traversal | 400 | `bad_request` |
| well-formed missing artifact/proposal/lane/trace | 404 | `not_found` |
| artifact exceeds the W-026 read size limit | 413 | `read_error` |
| deterministic evidence source absent | 501 | `evidence_unavailable` |
| deferred W-027+ route | 501 | `unsupported` |
| filesystem read failure | 500 | `read_error` |
| unexpected runtime failure | 500 | `runtime_unavailable` |

## W-026 execution model

The Workbench API is a single-operator local service.  It emits a narrow local
development CORS response for the Vite workbench origin
`http://127.0.0.1:5173`; this supports W-028's documented split-server manual
integration workflow without making the API a remote service. Eval execution is
serialized per server instance so two `/evals/run` requests cannot race over
shared runtime checkpoint files.

### Side effects on `engine_state/`

W-026 is read-only with respect to teaching corpora and pack data. Two routes
touch runtime checkpoint surfaces governed by existing ADRs:

- `GET /runtime/status` instantiates `EngineStateStore` and reads
  `engine_state/manifest.json` via `load_manifest`.
- `POST /evals/run` with `lane="contemplation_quality"` transitively invokes
  the ADR-0159 replay baseline. That path can create normal `ChatRuntime`
  checkpoints under `engine_state/`, governed by ADR-0146 and ADR-0150.

These checkpoint writes are runtime artifacts, not teaching/corpus/pack
mutation. They are intentionally excluded from the W-026 read-only snapshot
invariant.

---

# Runtime

## GET /health

Purpose:

Basic liveness/readiness.

Response:

```json
{
  "ok": true,
  "data": {
    "status": "ok"
  }
}
```

---

## GET /runtime/status

Purpose:

Expose runtime metadata.

Response:

```json
{
  "ok": true,
  "data": {
    "backend": "rust",
    "git_revision": "abc123",
    "engine_state_present": true,
    "checkpoint_revision": "abc123",
    "revision_warning": false,
    "active_session_id": "session-001"
  }
}
```

---

# Chat

## POST /chat/turn

Purpose:

Execute a normal runtime turn and return the full UI evidence envelope.

This is the only Workbench POST route that touches the live chat runtime. Turns
are serialized per server instance by a module-level lock, matching ADR-0160's
single-operator-local v1 doctrine.

Request:

```json
{
  "prompt": "What does alpha cause?"
}
```

Validation:

- `prompt` is required and must be a string.
- `prompt.strip()` must be non-empty.
- `prompt` must not exceed 4096 characters.
- request `Content-Length` must not exceed 64 KiB.

Invalid prompt shape returns `400 bad_request`. Oversize request bodies return
`413 read_error`.

Response:

```json
{
  "ok": true,
  "generated_at": "2026-05-26T00:00:00Z",
  "data": {
    "prompt": "What does alpha cause?",
    "surface": "alpha causes beta",
    "articulation_surface": "alpha causes beta",
    "walk_surface": "alpha -> beta",
    "grounding_source": "teaching",
    "epistemic_state": "decoded",
    "normative_clearance": "cleared",
    "normative_detail": "",
    "trace_hash": "sha256:...",
    "refusal_emitted": false,
    "hedge_injected": false,
    "mutation_mode": "runtime_turn",
    "identity_verdict": {
      "outcome": "cleared",
      "runtime_detail": ""
    },
    "safety_verdict": {
      "outcome": "cleared",
      "runtime_detail": ""
    },
    "ethics_verdict": {
      "outcome": "cleared",
      "runtime_detail": ""
    },
    "proposal_candidates": [
      {
        "candidate_id": "abc123",
        "source_kind": "discovery"
      }
    ],
    "turn_cost_ms": 17,
    "checkpoint_emitted": true
  }
}
```

Important:

This endpoint must use the existing runtime path.  It must not introduce a
parallel persistence layer.

Mutation boundary:

- A chat turn may write `engine_state/` through the normal runtime checkpoint
  path governed by ADR-0146 and ADR-0150. `checkpoint_emitted` reports whether
  that occurred.
- A chat turn must not mutate `teaching/`, `packs/`, or `language_packs/data/`.
- A chat turn must not auto-accept proposals.
- `proposal_candidates` contains candidate identifiers only; it does not expose
  proposal acceptance/rejection affordances or candidate surfaces.
- `surface`, `articulation_surface`, and `walk_surface` remain distinct. The
  user-facing response is `surface`; `walk_surface` is telemetry/evidence.

---

# Trace

## GET /trace/{turn_id}

Purpose:

Inspect trace evidence for a turn.

W-026 status:

Trace storage is not implemented in W-026. Unknown turn ids MUST return
`404 not_found`. The API must never return a synthetic empty trace as a
successful response.

Response:

```json
{
  "ok": true,
  "data": {
    "turn_id": "turn-001",
    "surface": "...",
    "articulation_surface": "...",
    "walk_surface": "...",
    "trace_hash": "sha256:...",
    "grounding_source": "teaching",
    "replay_digest": "sha256:...",
    "proposal_refs": [],
    "admissibility": {
      "rejected_attempts": 0
    }
  }
}
```

---

# Replay

## GET /replay/{turn_id}

(Wave R3 — supersedes the unwired W-026 `{artifact_id}` placeholder.
Design record: `docs/analysis/replay-moment-backend-scoping-2026-06-12.md`.)

Purpose:

Re-execute a journaled turn's prompt in a **sealed fresh runtime**
(`ChatRuntime(no_load_state=True)` — no checkpoint load, no checkpoint
write, no proposal lineage) and compare the resulting envelope leaf-by-leaf
against the recorded `TurnJournalEntry`.

Important:

The API must not claim `"equivalent": true` unless a real re-execution has
run. Comparing a digest to itself is not replay evidence; if the replay
runtime fails, the route returns `runtime_unavailable` (500) and no
comparison object exists.

Honesty envelope: the claim demonstrated is *same prompt, same genesis
substrate → bit-identical envelope*. The original turn ran in its own fresh
runtime that may have loaded an engine-state checkpoint present at the
time; the journal does not record whether one existed, so `origin_state` is
`"unrecorded"` and a divergence means nondeterminism **or** origin-state
influence — the API never claims to distinguish them, and the frontend must
not render a divergence as a determinism-failure verdict.

Severity classes: every `TurnJournalEntry` field is classified exactly once
(enforced by test). `critical` divergences break equivalence; wall-clock
fields (`timestamp`, `turn_cost_ms`, `journal_digest`) are `informational`
and never do.

Errors: unknown or malformed `turn_id` → 404 `not_found`; replay runtime
failure → 500 `runtime_unavailable`. The route is read-only: it appends no
journal entry and writes no engine state.

Response:

```json
{
  "ok": true,
  "data": {
    "turn_id": 7,
    "comparison_basis": "sealed_fresh_runtime_single_turn",
    "origin_state": "unrecorded",
    "original_trace_hash": "sha256:...",
    "replay_trace_hash": "sha256:...",
    "equivalent": true,
    "replay_turn_cost_ms": 412,
    "divergences": [
      {
        "path": "timestamp",
        "original": "2026-06-12T18:00:00+00:00",
        "replay": "2026-06-12T23:55:01+00:00",
        "severity": "informational"
      }
    ]
  }
}
```

---

# Proposals

## GET /proposals

Purpose:

List proposal metadata.

Implementation rule:

Proposal reads MUST derive their current view by replaying
`teaching.proposals.ProposalLog.current_state()`. The append-only JSONL file is
an event log, not a table of proposal records.

Response:

```json
{
  "ok": true,
  "data": {
    "items": [
      {
        "proposal_id": "proposal-001",
        "state": "pending",
        "source_kind": "contemplation",
        "replay_equivalent": true,
        "created_at": "2026-05-26T00:00:00Z"
      }
    ]
  }
}
```

---

## GET /proposals/{proposal_id}

Purpose:

Detailed proposal inspection.

Response:

```json
{
  "ok": true,
  "data": {
    "proposal_id": "proposal-001",
    "state": "pending",
    "source_kind": "contemplation",
    "replay_equivalent": true,
    "proposed_chain": {},
    "replay_evidence": {},
    "downstream_effect": {},
    "artifact_refs": []
  }
}
```

Forbidden:

- accept endpoint
- reject endpoint
- mutation endpoint

---

# R2 Read Projections

These endpoints are read-only projections over existing artifacts. They do not
create event stores, run stores, pack stores, or vault persistence.

## GET /packs

Purpose:

List readable pack manifests from `language_packs/data/*/manifest.json` and
cleanly readable JSON manifests under `packs/*/*/manifest.json`.

Query:

- `limit`: non-negative integer, default `100`
- `offset`: non-negative integer, default `0`

Trust boundary:

Pack list reads only fixed repository roots. `GET /packs/{pack_id}` validates
`pack_id` against the safe pattern `[A-Za-z0-9][A-Za-z0-9_.-]{0,127}` before
any filesystem access. Path traversal and encoded slashes return
`400 bad_request`.

Response:

```json
{
  "ok": true,
  "data": {
    "items": [
      {
        "pack_id": "en_core_cognition_v1",
        "source": "language_pack",
        "manifest_path": "language_packs/data/en_core_cognition_v1/manifest.json",
        "version": "1.2.0",
        "language": "en",
        "modality": null,
        "determinism_class": "D0",
        "checksum": "82d5...",
        "checksums": {
          "checksum": "82d5..."
        }
      }
    ],
    "limit": 100,
    "offset": 0
  }
}
```

Manifest checksum fields are surfaced verbatim from the manifest. The API also
returns a separate `manifest_digest` on detail, computed from the manifest file
bytes, so byte integrity and manifest-authored checksums remain distinct.

## GET /packs/{pack_id}

Purpose:

Return one pack manifest projection. Unknown safe ids return `404 not_found`;
unsafe ids return `400 bad_request`.

Response includes the summary fields plus:

```json
{
  "manifest_digest": "sha256:...",
  "manifest": {}
}
```

---

## GET /audit/events

Purpose:

Return a merged audit timeline over existing deterministic artifacts:

- `engine_state/manifest.json` when present,
- `teaching/proposals/proposals.jsonl`,
- `teaching/math_proposals/proposals.jsonl`,
- persisted Workbench telemetry JSONL files under `workbench_data/`.

The route does not invent or append an event store. Events are sorted by
`timestamp`, then source/path/type/id tiebreakers.

Query:

- `limit`: non-negative integer, default `100`
- `offset`: non-negative integer, default `0`

Each event includes `source` and `mutation_boundary`. Mutation-boundary events
identify review transitions, accepted corpus appends, operator telemetry, or
engine checkpoint boundaries.

---

## GET /runs

Purpose:

List deterministic run/session projections that can be derived from existing
artifacts.

Current evidence sources:

- `workbench_data/turn_journal.jsonl` as `workbench_turn_journal` when turn
  entries exist.
- `engine_state/manifest.json` as `engine_state_checkpoint` when a checkpoint
  manifest exists.

Known gap:

The current persisted artifacts do not record a separate durable user-facing
session id. The API exposes the artifact boundary and includes `evidence_gap`
instead of synthesizing a false session identity.

---

## GET /runs/{session_id}

Purpose:

Return detail for a deterministic run projection. Unknown ids return
`404 not_found`. Turn journal details include paginated `turns`, where each turn
links to `/trace/{turn_id}`.

Query:

- `limit`: non-negative integer for turn refs, default `100`
- `offset`: non-negative integer for turn refs, default `0`

---

## GET /vault/summary

Purpose:

Return a cold summary of persisted vault evidence only when
`engine_state/session_state.json` contains a Shape B+ `vault` snapshot.

If the persisted snapshot is absent, the route returns:

```json
{
  "ok": false,
  "error": {
    "code": "evidence_unavailable",
    "message": "vault evidence unavailable: engine_state/session_state.json is absent"
  }
}
```

The route never reaches into live runtime memory.

## GET /vault/entries

Purpose:

Return metadata for persisted vault entries. The endpoint surfaces metadata and
a digest of each persisted versor encoding; it does not emit raw versor
coordinates or approximate recall scores.

Query:

- `limit`: non-negative integer, default `100`
- `offset`: non-negative integer, default `0`

---

# Evals

## GET /evals

Purpose:

List eval lanes.

Response:

```json
{
  "ok": true,
  "data": {
    "lanes": [
      "cognition",
      "learning-arc",
      "contemplation-quality"
    ]
  }
}
```

---

## POST /evals/run

Purpose:

Run a read-only eval lane.

Request:

```json
{
  "lane": "contemplation-quality"
}
```

Response:

```json
{
  "ok": true,
  "data": {
    "lane": "contemplation-quality",
    "passed": true,
    "metrics": {}
  }
}
```

Constraints:

- only lanes explicitly marked safe/read-only may run through the API
- mutation-capable workflows are forbidden in v1

---

# Artifacts

## GET /artifacts

Purpose:

Enumerate readable runtime artifacts.

Response:

```json
{
  "ok": true,
  "data": {
    "items": []
  }
}
```

---

## GET /artifacts/{artifact_id}

Purpose:

Read structured artifact content.

Constraints:

- artifacts must be repo-root constrained
- no arbitrary path traversal
- no arbitrary shell execution

---

# Security Constraints

## Forbidden in v1

- proposal mutation
- corpus mutation
- workflow dispatch
- arbitrary file reads
- remote execution
- arbitrary command execution
- hidden background jobs

## Required

- deterministic serialization
- stable artifact ids
- digest visibility
- explicit provenance where available
- read-only route tests
