# Workbench UI — Continuation Plan

> **Status:** temporary working plan — delete when all phases are merged
> **Scope:** `workbench-ui/` only
> **Tracks against:** current `main` @ `89defef`

---

## Context

The CORE Workbench is a React + Vite + TanStack Query frontend that serves as the
primary operator interface for the CORE engine. The shell is structurally sound.
Four feature routes are implemented. Six routes remain placeholders. The right
inspector is a stub kept collapsed. This plan sequences the remaining work.

### What exists today

| Area | Status | Notes |
|---|---|---|
| Shell grid (TopBar / LeftNav / StatusFooter) | ✅ Live | Token-driven, tested |
| Design token substrate (`src/design/`) | ✅ Complete | **Do not expand** except `EmptyState` / `CommandPalette` |
| CommandPalette (⌘K) | ✅ Live | Wired in TopBar |
| ApiErrorBoundary | ✅ Live | Wraps `<Outlet />` |
| Chat route | ✅ Implemented | `src/app/chat/` — turn flow, trace drawer, evidence |
| Proposals route | ✅ Implemented | `src/app/proposals/` — queue, detail, review lifecycle |
| Replay route | ✅ Implemented | `src/app/replay/` — artifact comparison |
| Evals route | ✅ Implemented | `src/app/evals/` — lanes, runs, metrics |
| Trace route | 🔴 Placeholder | `src/routes/TraceRoutePlaceholder.tsx` |
| Runs route | 🔴 Placeholder | `src/routes/RunsRoutePlaceholder.tsx` |
| Packs route | 🔴 Placeholder | `src/routes/PacksRoutePlaceholder.tsx` |
| Vault route | 🔴 Placeholder | `src/routes/VaultRoutePlaceholder.tsx` |
| Audit route | 🔴 Placeholder | `src/routes/AuditRoutePlaceholder.tsx` |
| Settings route | 🔴 Placeholder | `src/routes/SettingsRoutePlaceholder.tsx` |
| RightInspector | 🔴 Stub | Hardcoded collapsed in `Shell.tsx` (W-027) |

### Existing query hooks (api/queries.ts)

- `useRuntimeStatus` — `/runtime/status`
- `useChatTurn` — `/chat/turn`
- `useArtifacts` — artifact listing
- `useArtifact` — artifact detail
- `useReplayComparison` — `/replay/compare`
- `useProposals` — proposals listing
- `useProposal` — proposal detail
- `useEvalLanes` — eval lanes listing
- `useEvalLane` — eval lane detail
- `useEvalExecution` — eval run execution

**No hooks yet exist** for: runs, trace sessions, packs, vault, audit log, or settings.

---

## Constraints

- Documentation stays in Markdown, never HTML dashboards.
- `src/design/` is a protected Branch 1 substrate. Only `EmptyState` and `CommandPalette` may be edited there.
- New UI pieces go feature-local: `src/app/<feature>/` or `src/routes/<Feature>Route.tsx`.
- Zero hardcoded hex values — always reference CSS custom properties from `tokens.css`.
- No new state management libraries. Prefer TanStack Query + React `useState` / `useReducer` + `useContext` where needed.
- All new routes need at minimum a smoke test and a loading/empty/error state.
- Schema/type mirrors in `src/types/api.ts` must stay in sync with the Python backend.
- PR discipline: small, load-bearing, each with tests. Follow existing ADR checklist.

---

## Implementation Sequence

### Phase 1 — Polish the four implemented routes

**Branch prefix:** `workbench/WIP-1-*`
**Goal:** Make Chat, Proposals, Replay, and Evals cohesive and cross-linked before adding new surfaces.

#### 1a — Chat

- [ ] Audit loading / empty / error states for consistency
- [ ] Improve trace-hash and proposal-candidate navigation from within a turn response
- [ ] Verify ⌘K command entries exist for `New chat session` and `Jump to proposal`
- [ ] Extend `Shell.test.tsx`-style tests for any new interaction paths

#### 1b — Proposals

- [ ] Audit queue list loading / empty / error states
- [ ] Strengthen proposal detail: add direct link to its source artifact and replay-comparison entry
- [ ] Expose review-lifecycle color tokens (`review-pending`, `accepted`, `rejected`, `withdrawn`) consistently across list and detail views
- [ ] Ensure suggested-CLI block is selectable / copyable

#### 1c — Replay

- [ ] Audit artifact-selector loading / empty / error states
- [ ] Improve divergence-severity and metadata presentation clarity
- [ ] Add a direct link from replay comparison back to the originating proposal where applicable
- [ ] Add route tests for primary comparison path

#### 1d — Evals

- [ ] Audit lane list and eval run view states
- [ ] Improve metric readability — consider aligned numeric columns
- [ ] Add route tests for lane selection and run inspection

---

### Phase 2 — Build the Runs route

**Branch prefix:** `workbench/WIP-2-runs`
**Goal:** Replace `RunsRoutePlaceholder.tsx` with a real first-version route.

**Why this is next:** The existing `useArtifacts` and `useArtifact` query hooks already provide the needed read paths. Runs is the closest unfinished route to having backend support.

- [ ] Create `src/app/runs/` directory
- [ ] Build `RunsRoute.tsx`: artifact listing table — sortable by date, filterable by status
- [ ] Build `RunDetail.tsx`: artifact detail panel — metadata, trace hash, proposal links, replay entry-point
- [ ] Wire deep link from RunDetail → Replay comparison
- [ ] Add loading / empty / error states
- [ ] Update `App.tsx` to swap placeholder for the real route
- [ ] Add route tests

---

### Phase 3 — Build the Trace route

**Branch prefix:** `workbench/WIP-3-trace`
**Goal:** Replace `TraceRoutePlaceholder.tsx` with a first-version standalone trace explorer built by promoting and reusing the chat trace model.

**Why this is next:** Chat already contains trace-oriented UI logic. Trace should be grown by promotion, not by inventing a separate graph system from scratch.

- [ ] Audit what `src/app/chat/` already exposes for trace viewing
- [ ] Extract or adapt the trace model into a reusable `src/app/trace/` home
- [ ] Build `TraceRoute.tsx`: trace session list / selector
- [ ] Build `TraceDetail.tsx`: node-by-node state exploration using existing state-color tokens (`decoded`, `inferred`, `evidenced`, `contradicted`, etc.)
- [ ] Read-only first — no mutations in v1
- [ ] Add `useTraceSession` and `useTraceNode` query hooks to `queries.ts` once backend contract is confirmed
- [ ] Update `App.tsx` to swap placeholder
- [ ] Add route tests

---

### Phase 4 — Activate the RightInspector

**Branch prefix:** `workbench/WIP-4-inspector`
**Goal:** Replace the inspector stub and the hardcoded `inspectorCollapsed = true` in `Shell.tsx` with a real, read-only detail surface.

**Why this comes after Runs + Trace:** Entity shapes must be concrete before the inspector can meaningfully propagate them. Doing this first would mean speculating on schema.

- [ ] Add a minimal selection model: a `useInspectorStore` context/reducer that routes can publish into
- [ ] Lift the inspector toggle into `TopBar` (icon button, rightmost, `aria-expanded`)
- [ ] Replace `const inspectorCollapsed = true` with reactive state wired to the store
- [ ] Implement `RightInspector.tsx` — reads selected entity from the store, renders detail by entity type
- [ ] Support initial entity types: `artifact`, `proposal`, `trace-node`, `replay-diff`
- [ ] Read-only in v1
- [ ] Add tests for toggle behavior and entity rendering

---

### Phase 5 — Define contracts for remaining placeholder routes

**Branch prefix:** `workbench/WIP-5-contracts`
**Goal:** Before building Packs, Vault, Audit, and Settings, confirm Python schema shapes and add TypeScript mirrors.

**These routes are still true placeholders with no corresponding query hooks. Contract work precedes UI depth.**

#### Packs
- [ ] Confirm pack listing and pack-detail API shapes with backend
- [ ] Add `usePackList` and `usePack` hooks to `queries.ts`
- [ ] Add types to `src/types/api.ts`

#### Vault
- [ ] Confirm vault entry listing and entry-detail API shapes
- [ ] Add `useVaultEntries` and `useVaultEntry` hooks
- [ ] Add types to `src/types/api.ts`

#### Audit
- [ ] Confirm clearance-event log API shape (pagination, filters)
- [ ] Add `useAuditLog` hook
- [ ] Add types to `src/types/api.ts`

#### Settings
- [ ] Enumerate mutable runtime settings and confirm read/write API contract
- [ ] Decide which settings are operator-only (read only in UI) vs. writable from the workbench
- [ ] Add `useSettings` and `useUpdateSettings` hooks

---

### Phase 6 — Implement remaining routes

**Branch prefix:** `workbench/WIP-6-*`
**Goal:** One route per PR, in this priority order based on anticipated backend readiness.

1. **Vault** — hierarchical grounded knowledge browser; uses grounding-source color tokens (`grounding-teaching`, `grounding-pack`, `grounding-vault`, `grounding-oov`, etc.)
2. **Packs** — pack management: list, inspect contents, trigger re-ingestion; piggybacks on vault color system
3. **Audit** — temporal clearance-event log; uses clearance tokens (`cleared`, `violated`, `unassessable`, `suppressed`); time-sorted, paginated table
4. **Settings** — runtime config surface: model selection, threshold sliders, API endpoint override; write paths gated behind explicit confirmation

Each must have:
- [ ] Loading / empty / error states
- [ ] Route tests
- [ ] Updated `App.tsx` wiring (placeholder swap)
- [ ] ⌘K command entries

---

### Phase 7 — ⌘K command registry completion

**Branch prefix:** `workbench/WIP-7-command-palette`
**Goal:** Fill the CommandPalette command registry with live, route-aware entries.

- [ ] Route navigation: all 10 nav items accessible via ⌘K
- [ ] Context-sensitive: `Jump to run #N`, `Open vault entry`, `Inspect proposal`, `Compare artifacts`
- [ ] Live search over recent runs and sessions via existing query hooks
- [ ] Keyboard-first: full arrow-key navigation, Escape to close, Enter to activate

---

## Validation checklist (per PR)

```
cd workbench-ui
pnpm test
pnpm test:enum-coverage
```

Before merging a placeholder-swap PR:
- [ ] Old placeholder file removed from `src/routes/`
- [ ] New route wired in `App.tsx`
- [ ] New route has at minimum: loading state, empty state, error state, one smoke test
- [ ] No hardcoded hex values
- [ ] No new dependencies added without discussion

---

## Done criteria

This plan is complete when:

- [ ] All four existing routes are cohesive, cross-linked, and consistently handle all async states
- [ ] `Runs` is a live route backed by artifact/replay query hooks
- [ ] `Trace` is a live route promoted from the chat trace model
- [ ] `RightInspector` is a real, toggleable, read-only inspection surface
- [ ] `Packs`, `Vault`, `Audit`, `Settings` have confirmed backend contracts and TypeScript mirrors
- [ ] All six placeholder files in `src/routes/` are replaced and deleted
- [ ] ⌘K command registry covers all 10 routes and key entity-jump commands
- [ ] `src/design/` remains untouched except for `EmptyState` / `CommandPalette` allowed edits
- [ ] Every route has tests

---

*Delete this file once all items above are checked and the final PR in each phase is merged.*
