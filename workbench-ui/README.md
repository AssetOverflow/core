# CORE Workbench UI

React/Vite/TypeScript frontend for CORE Workbench — a local operator/auditor UI
over the deterministic engine. 14 registry-driven routes (`src/app/routes.ts`):
chat; trace (per-turn pipeline / field-invariant / leeway / evidence-bundle
tabs); the guided determinism tour; replay (hash-to-hash); demos; proposals +
HITL ratification; evals (wrong=0 ledger); calibration (gold-tether arena);
runs; vault; packs; and audit. Read-only, with allowlisted execution only.

## Local development

```bash
# Terminal 1 — start the API (W-026)
uv run core workbench api

# Terminal 2 — start the frontend
cd workbench-ui
pnpm install
pnpm dev         # http://127.0.0.1:5173
```

## Custom API URL

```bash
VITE_WORKBENCH_API_URL=http://127.0.0.1:9000 pnpm dev
```

## Design system baseline

```bash
pnpm preview   # Serves dist/ on http://127.0.0.1:4173
# Navigate to /preview for the Branch 1 design-system baseline
```

## Tests

```bash
pnpm test                # Vitest unit + component tests
pnpm test:enum-coverage  # Badge enum coverage (requires uv)
```

## Schema drift detection

The TypeScript types in `src/types/api.ts` mirror `workbench/schemas.py`.
To check for drift after Python schema changes:

```bash
# From repo root
uv run python scripts/dump-api-schemas.py
# Then run: pnpm test (api.test.ts catches field-level drift)
```

## Architecture

- `src/app/` — Shell, TopBar, LeftNav, StatusFooter, ApiErrorBoundary, and the
  route surfaces in `src/app/<route>/`. `src/app/routes.ts` is the single route
  registry (feeds App, LeftNav, command palette, shortcuts, and conformance).
- `src/api/` — apiFetch client, TanStack Query hooks
- `src/types/` — TypeScript mirrors of Python schemas (`src/types/api.ts`)
- `src/routes/` — the Chat route entry
- `src/design/` — design-system substrate (tokens, primitives, doctrine gates)

## ADR cross-references

- ADR-0160 — Workbench v1 architecture
- ADR-0162 — Design substrate (Branch 1)
- ADR-0156, ADR-0157, ADR-0158 — Engine-state checkpoint and reboot audit trail
