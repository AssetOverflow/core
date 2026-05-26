# CORE Workbench — Current Implementation Status

Branch: `feat/w026-workbench-readonly-api`

This branch intentionally converges at the first reviewable Workbench milestone:

- authenticated local operator API
- read-only observability endpoints
- Bun/Vite/React Workbench shell
- pre-login observatory intro
- trace observability scaffold
- proposal/eval/artifact/replay surfaces

It is not the final Workbench. It is the first coherent operator platform
foundation.

## Implemented

### Backend

- `workbench/` package
- FastAPI app factory
- standalone `core-workbench` entrypoint
- environment-driven host/port
- single-admin auth
- signed HTTP-only session cookie
- password hashing utility
- read-only runtime status endpoint
- read-only artifact listing/detail endpoints
- read-only proposal listing/detail endpoints
- safe eval lane listing/execution gate
- replay artifact comparison scaffold
- trace endpoint scaffold

### Frontend

- `workbench/ui/` Bun/Vite/React/TypeScript shell
- authenticated login screen
- session restoration
- authenticated API client
- runtime status panel
- proposal queue panel
- eval lane panel
- artifact panel
- replay panel
- pre-login observatory intro
- deterministic observatory clock
- observatory topology primitives
- stabilization and motion primitives
- trace drawer component
- Chat surface wired to authenticated trace endpoint

### Startup

- `workbench/.env.example`
- `scripts/workbench-dev`
- `scripts/workbench-up`

## Doctrine preserved

- local-first
- single-admin
- read-only-first
- replay before persuasion
- proposal is not ratification
- no corpus mutation
- no pack mutation
- no proposal accept/reject route
- no workflow dispatch
- no hidden background jobs
- no fake cognition animation

## Known limitations

- Chat execution is not yet wired to `CognitiveTurnPipeline`.
- Trace storage is not yet backed by live turn artifacts.
- Replay comparison currently uses same-artifact digest equality as a scaffold.
- Frontend build/typecheck has not been run in this connector environment.
- Backend route tests were added but not executed here.
- `scripts/workbench-up` assumes `bun` and `uv` are installed locally.

## Next branch boundary

The next branch should not keep expanding this PR indefinitely.

Recommended next branch:

`feat/W-030-workbench-live-runtime-turns`

Scope:

1. Add `/chat/turn` backend endpoint using the existing runtime path.
2. Persist or expose a trace artifact for the returned turn.
3. Return `turn_id`, `surface`, `grounding_source`, `trace_hash`, and replay metadata.
4. Update `ChatSurface` to submit prompts.
5. Auto-load the returned trace into `TraceDrawer`.
6. Keep all proposal/corpus mutation paths forbidden.

## Review focus for this branch

Reviewers should focus on:

- auth correctness
- route protection
- read-only boundaries
- artifact path traversal protection
- eval safe-lane gating
- UI dependency footprint
- startup ergonomics
- whether this is a coherent first Workbench milestone

Do not review this branch as if it is the finished observatory. It is the
foundation that makes the next live-runtime branch possible.
