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
- `not_found`
- `unsupported`
- `read_error`
- `eval_failed`
- `runtime_unavailable`

`unauthorized` is reserved for a later auth ADR.  W-026 remains unauthenticated
and local-only by default.

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

Execute a normal runtime turn.

Request:

```json
{
  "prompt": "What does alpha cause?"
}
```

Response:

```json
{
  "ok": true,
  "data": {
    "turn_id": "turn-001",
    "surface": "alpha causes beta",
    "grounding_source": "teaching",
    "trace_hash": "sha256:...",
    "proposal_state": null,
    "replay_available": true
  }
}
```

Important:

This endpoint must use the existing runtime path.  It must not introduce a
parallel persistence layer.

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

## GET /replay/{artifact_id}

Purpose:

Return replay comparison information.

Important:

The API must not claim `"equivalent": true` unless a real replay/compare path
has run. Comparing an artifact digest to itself is not replay evidence. Until
the replay theater is wired, this route should return `unsupported` or a
non-equivalent comparison with explicit divergence evidence.

Response:

```json
{
  "ok": true,
  "data": {
    "artifact_id": "artifact-001",
    "original_hash": "sha256:...",
    "replay_hash": null,
    "equivalent": false,
    "divergences": [
      {
        "path": "$",
        "original": "artifact digest",
        "replay": null,
        "severity": "info"
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
