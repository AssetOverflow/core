# CORE Workbench UI

React/Vite/TypeScript frontend for CORE Workbench — a local operator UI for
inspecting engine state, proposals, evals, and audit trails.

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

- `src/app/` — Shell, TopBar, LeftNav, StatusFooter, ApiErrorBoundary
- `src/api/` — apiFetch client, TanStack Query hooks
- `src/types/` — TypeScript mirrors of Python schemas
- `src/routes/` — Route placeholder components
- `src/design/` — Branch 1 design-system substrate (DO NOT MODIFY except EmptyState and CommandPalette)

## ADR cross-references

- ADR-0160 — Workbench v1 architecture
- ADR-0162 — Design substrate (Branch 1)
- ADR-0156, ADR-0157, ADR-0158 — Engine-state checkpoint and reboot audit trail
