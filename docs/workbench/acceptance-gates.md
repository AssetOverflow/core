# CORE Workbench v1 — Acceptance Gates

These gates define when the Workbench v1 planning and implementation phases are
acceptable. They intentionally privilege trust-boundary preservation over visual
polish.

## Planning branch gates

The planning branch is acceptable when it includes:

- ADR defining doctrine and scope
- product/UX blueprint
- implementation plan
- API contract
- data-shape contract
- UI component map
- explicit non-goals
- explicit mutation boundaries and admitted-corridor requirements
- work queue for W-026 through W-031

## W-026 — Read-only API gates

Required:

- local-only API defaults to `127.0.0.1`
- non-local bind requires an explicit operator flag
- typed response schemas
- route tests
- path traversal tests for artifact readers
- proposal event-log read-model tests using `ProposalLog.current_state()`
- unknown trace ids return `404`, not placeholder success payloads
- no proposal accept/reject route outside an admitted corridor
- no corpus mutation route
- no pack mutation route
- no workflow dispatch route
- no hidden background worker
- no frontend commits
- no auth surface
- no FastAPI/uvicorn/pydantic dependency

Blockers:

- fake replay equality by comparing an artifact digest to itself
- placeholder trace-as-success responses
- parsing proposal events as proposal records
- non-local bind without explicit operator opt-in
- auth added before the local read-only boundary is accepted
- frontend, visual intro, trace drawer, or chat UI included in W-026

Acceptance command candidates:

```bash
uv run python -m pytest tests/test_workbench_schemas.py -q
uv run python -m pytest tests/test_workbench_api.py -q
uv run python -m pytest tests/test_workbench_readers.py -q
```

## W-027 — Frontend shell gates

Required:

- TypeScript strict mode
- left navigation
- top runtime bar
- empty states for all modules
- API client shape aligned to `data-shapes-v1.md`
- no mutation buttons outside an admitted corridor
- no fake/mock runtime as permanent architecture

Acceptance command candidates:

```bash
npm --prefix workbench/ui run typecheck
npm --prefix workbench/ui run build
```

## W-028 — Chat + Trace Drawer gates

Required:

- prompt/response flow
- trust badge row
- trace drawer collapsed by default
- grounding source visible
- trace hash visible when present
- mutation state visible
- raw trace behind explicit expansion

Forbidden:

- replacing user surface with telemetry surface
- hidden checkpointing beyond existing runtime behavior
- decorative thinking animation

## W-029 — Proposal Queue gates

Required:

- list proposals
- filter by state
- inspect proposal detail
- display source provenance
- display replay evidence
- display proposed chain
- display suggested CLI copy command
- mutation only through admitted corridors:
  ADR-governed path, visible preconditions, auditable telemetry, and replay
  evidence before action

Forbidden:

- unadmitted accept/reject button
- workflow dispatch
- direct proposal mutation outside an admitted corridor
- corpus mutation
- pack mutation
- arbitrary file writes

## W-030 — Eval Center gates

Required:

- list lanes
- display lane metadata
- run safe/read-only lanes
- show metrics
- show failures prominently
- show contemplation-quality details

Forbidden:

- sealed holdout execution without explicit sealed-eval configuration
- hidden saving of results
- mutation-capable workflow execution

## W-031 — Replay Theater gates

Required:

- artifact selection
- original/replay hash comparison
- equivalence badge
- divergence display
- stable JSON viewer

Forbidden:

- non-deterministic replay display
- aesthetic animation presented as evidence

## V1 release gates

The v1 workbench is releasable when an operator can:

1. start the local API,
2. open the UI,
3. see runtime status,
4. inspect a proposal and see whether an admitted corridor applies,
5. run/view contemplation-quality,
6. inspect trace/replay metadata,
7. perform a basic chat turn,
8. verify from UI copy and docs that no unadmitted ratification/mutation path exists.

## Red flags

Any of these should block merge:

- UI can accept/reject proposals without an admitted corridor, visible
  preconditions, auditable telemetry, and replay evidence
- API exposes arbitrary path reads
- API invokes shell from user input
- frontend hardcodes fake eval/proposal data as product path
- mutation status is hidden
- replay status is shown without digest/evidence
- telemetry surfaces are confused with user-facing surfaces
