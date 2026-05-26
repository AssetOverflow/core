# CORE Workbench v1 — Implementation Plan

This plan intentionally starts with planning and read-only observability before
any mutating workflow.  The purpose is to preserve CORE's existing ADR trust
boundaries while making the system legible to operators, engineers, and auditors.

## Work queue

| Work item | Title | Scope | Mutation allowed? |
|---|---|---|---|
| W-026 | Read-only API contract | endpoint schemas + stdlib local server surface only | No |
| W-027 | Frontend shell | navigation, layout, design tokens, empty states | No |
| W-028 | Chat + trace drawer | basic chat, turn metadata, trace drawer | Runtime turn only |
| W-029 | Proposal queue | proposal-log read model, detail view, CLI-copy affordance | No |
| W-030 | Eval center | lane discovery, run/read evals, result viewer | Eval result writes only if CLI already supports it |
| W-031 | Replay theater | artifact selection, digest compare, replay status UI | No |

## Phase sequencing

### Phase 0 — Planning package

Deliverables:

- ADR-0160
- Product/UX blueprint
- Implementation plan
- API contract
- data-shape contract
- acceptance gates

No code beyond docs.

### Phase 1 — Read-only API skeleton

Goal: expose a narrow local workbench API without introducing new mutation paths.

Deliverables:

- `workbench/api.py`
- `workbench/schemas.py`
- `workbench/readers.py`
- `workbench/server.py`
- route tests with temp fixtures
- CLI command: `core workbench api --host 127.0.0.1 --port 8765`

Initial endpoints:

- `GET /health`
- `GET /runtime/status`
- `GET /artifacts`
- `GET /artifacts/{artifact_id}`
- `GET /proposals`
- `GET /proposals/{proposal_id}`
- `GET /evals`
- `GET /evals/{lane}`
- `POST /evals/run`

Strict rules:

- W-026 is API-only. No frontend, auth, visual intro, trace drawer, chat UI,
  live chat endpoint, or replay theater.
- Use the Python standard-library HTTP server for W-026. Defer FastAPI or any
  other web framework unless a later ADR admits the dependency.
- No proposal accept/reject endpoints.
- No synthetic trace/replay evidence. Routes for later phases must return
  `unsupported` or `not_found` until a real evidence path exists.

### Phase 2 — Frontend shell

Goal: create a minimal, elegant workbench UI shell.

Proposed layout:

```text
+--------------------------------------------------------------+
| CORE Workbench        runtime status      replay status      |
+----------------------+---------------------------------------+
| Chat                 | Main Panel                            |
| Replay               |                                       |
| Proposals            |                                       |
| Evals                |                                       |
| Artifacts            |                                       |
| Runtime              |                                       |
+----------------------+---------------------------------------+
```

Deliverables:

- `workbench/ui/` or `apps/workbench/` depending repo convention
- React/Vite/TypeScript shell
- read-only API client
- navigation
- empty states
- no mocks as long-lived architecture; fixtures only in tests/story views

### Phase 3 — Chat + Trace Drawer

Goal: prove a small chat surface can expose trace metadata without becoming a
chatbot clone.

Deliverables:

- prompt box
- response surface
- trust badges
- expandable trace drawer
- grounding/provenance summary
- telemetry line link when available

Mutation boundary:

A live chat turn may use the existing runtime path.  The workbench must label
any runtime checkpointing clearly and must not add hidden persistence beyond
runtime behavior already governed by ADR-0146/0150.

### Phase 4 — Proposal Queue

Goal: make proposal lifecycle visible.

Deliverables:

- pending/accepted/rejected state filters
- proposal detail panel
- replay-equivalence evidence
- source provenance
- proposed chain display
- copyable local CLI command for review

Forbidden in v1:

- accept button
- reject button
- workflow dispatch
- direct corpus mutation

### Phase 5 — Eval Center

Goal: turn deterministic evals into a UI surface.

Deliverables:

- lane list
- run lane action for read-only lanes
- result JSON viewer
- metric cards
- case failures
- contemplation-quality detail view

Mutation boundary:

If `--save` equivalent behavior is exposed, it must be explicit and documented;
otherwise first pass should run and display without writing.

### Phase 6 — Replay Theater

Goal: make deterministic replay obvious.

Deliverables:

- artifact selector
- original vs replay comparison
- trace hash / digest comparison
- divergence panel
- pass/fail badge

## API design constraints

- All schemas must be explicit dataclasses in W-026.
- No raw arbitrary filesystem reads from user-provided paths.
- Artifact readers must be rooted under known repo directories.
- Every response should contain enough metadata to audit source path, digest,
  and timestamp when available.
- Mutation endpoints are forbidden in v1.
- Proposal reads must derive state from `ProposalLog.current_state()`, not by
  treating append-only JSONL events as proposal rows.

## Frontend constraints

- TypeScript strict mode.
- API client generated or manually typed from schema contract.
- No global mutable singleton for runtime state.
- No decorative animation as status.
- Color only communicates operational meaning.
- JSON viewers must preserve stable key ordering when possible.

## Test expectations

Each implementation PR must include:

- route-level tests for API endpoints
- schema serialization tests
- permission/path traversal tests for artifact readers
- frontend smoke/build check once UI exists
- no-mutation regression checks for read-only routes

## Release criteria for v1

The v1 workbench is accepted when an operator can:

1. start the local workbench server,
2. open the UI,
3. inspect runtime status,
4. run or view contemplation-quality,
5. inspect a proposal without accepting it,
6. inspect a trace/replay artifact,
7. perform a basic chat turn,
8. verify no hidden mutation path exists.

## Explicit deferrals

- multi-user collaboration
- cloud deployment
- mobile UI
- auth, unless a separate ADR admits it after the local read-only boundary is
  proven
- proposal accept/reject buttons
- workflow dispatch
- packaged desktop app
- public marketing site
- arbitrary plugin/tool execution

## Prototype branch rejection criteria

Do not continue from a prototype branch that:

- mixes W-026 with W-027/W-028 frontend or trace/chat work
- adds auth before the local read-only API boundary is accepted
- adds FastAPI, uvicorn, pydantic, or another web framework without ADR review
- claims replay equivalence by comparing an artifact digest to itself
- returns placeholder trace data as a successful trace response
- parses proposal log events as if they were proposal records
