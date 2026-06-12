# Wave R Mastery Revamp — Dispatch Briefs (R0a–R0d, R1)

Date: 2026-06-12
Plan: `docs/workbench/wave-R-mastery-revamp.md` (read it first — it is the
governing spec; this pack is the per-operator cut).

## Dispatch order

```
Echelon 1 (parallel):  R0a  ∥  R0b  ∥  R0c
Echelon 2:             R0d  (after R0c merges)
Echelon 3:             R1   (after all R0 merges)
```

Brief 5 (Trace route, `wave-1-evidence-spine-briefs-2026-06-12.md`) **stays
on hold** until R0 lands; it gets re-issued upgraded as the first R2 brief.

## Standing constraints (every brief)

- Worktree per operator, always off fresh `origin/main` — never share a
  working dir.
- The merge pipeline is automated; **pre-push verification is the gate.**
  Run your brief's verification block before pushing.
- Token-only styling (no raw hex/rgb outside `tokens.css`); no color-only
  encoding; motion only via `--motion-*` tokens; `prefers-reduced-motion`
  collapses to instant.
- ADR-0162 no-go list applies verbatim (no thinking animations, no
  glassmorphism, no toasts that auto-dismiss audit events, no icon-only
  buttons).
- Surfaces stay distinct everywhere: `surface` ≠ `articulation_surface` ≠
  `walk_surface`.
- No mutation endpoints, no writes outside `workbench_data/` from workbench
  code.
- Until R0a merges: full `pnpm test` may hang on teardown.  Verify with
  `pnpm build` + per-file `pnpm vitest run <file>`; `pkill -9 -f vitest`
  afterwards if needed.
- Commit format `<type>(workbench): <description>`; push with `-u`; open a
  PR titled as given in the brief.

---

## Brief R0a — Test-runner hardening + frontend CI lane

**Suggested operator:** Codex
**Scope:** `workbench-ui/` test config + timer hygiene; one new GitHub
workflow.  No product code changes beyond timer cleanup.

### Worktree

```bash
cd /Users/kaizenpro/Projects/core
git fetch origin
git worktree add ../core-wb-r0a origin/main -b feat/wb-r0a-test-hardening
cd ../core-wb-r0a/workbench-ui && pnpm install
```

### Context

Full multi-file `pnpm test` hangs on worker teardown — tests pass, the
process never exits.  Diagnosed 2026-06-12: live handles at teardown
(`Timestamp.tsx` `setInterval(..., 60_000)`, copy-feedback `setTimeout`s);
`vite.config.ts` has no `testTimeout`/`teardownTimeout`; switching pools does
not fix it; single files exit clean.  Separately: **no CI workflow runs
workbench-ui at all** (`smoke.yml` / `full-pytest.yml` are Python-only).

### Deliverables

1. `vite.config.ts` test config: `testTimeout: 10_000`,
   `hookTimeout: 10_000`, `teardownTimeout: 5_000`.  Tune pool options only
   if measurements justify it — caps first, knobs second.
2. Timer hygiene: audit every `setInterval`/`setTimeout`/`AbortController`
   under `src/`; ensure each has a cleanup path on unmount.  In tests that
   mount timer-scheduling components (`Timestamp`, copy buttons), use
   `vi.useFakeTimers()` with restoration in `afterEach`.
3. Prove it: full `pnpm test` runs to completion AND the process exits.
   Record wall-clock in the PR body.
4. New `.github/workflows/workbench-ui.yml`:
   - `on: pull_request` + `push: branches: [main]`, both with
     `paths: ['workbench-ui/**']`
   - single job, `timeout-minutes: 15`: pnpm setup (frozen lockfile) →
     `pnpm build` → `pnpm test`
   - Node 20, pnpm via `corepack` or `pnpm/action-setup`
5. Honesty fix (skip if R0d already merged): remove the `j/k` and `/` rows
   from `KeyboardHelp.tsx` and its test expectations — the overlay must not
   advertise shortcuts that do not exist.

### Verification before push

```bash
cd workbench-ui && pnpm build && time pnpm test   # must EXIT, all green
git -C .. diff --stat origin/main                  # only intended files
```

PR title: `fix(workbench): test-runner teardown hardening + frontend CI lane`

---

## Brief R0b — Playwright smoke lane

**Suggested operator:** GPT5.5-Thinking
**Scope:** `workbench-ui/` e2e only.  Pays ADR-0162 acceptance-criteria debt
(§ acceptance 5, 6, 7).  No product code changes except test hooks
(`data-testid` additions are allowed, sparingly).

### Worktree

```bash
cd /Users/kaizenpro/Projects/core
git fetch origin
git worktree add ../core-wb-r0b origin/main -b feat/wb-r0b-playwright
cd ../core-wb-r0b/workbench-ui && pnpm install
```

### Deliverables

1. `@playwright/test` devDependency (pinned), `playwright.config.ts` with
   `webServer` serving the built app (`pnpm build && vite preview`),
   chromium-only project (keep the lane lean).
2. `e2e/palette.spec.ts` — from each of the ten routes: `Meta+K` opens the
   palette; selecting a navigation command reaches every route (URL
   asserted).  The app must be usable with the backend absent — routes render
   their error/empty states, never a white screen (this doubles as an
   offline-resilience assertion).
3. `e2e/reduced-motion.spec.ts` — with `reducedMotion: 'reduce'`, tokenized
   motion collapses to instant (assert computed transition/animation
   durations are `0s` on a drawer open and palette open).
4. `e2e/preview-offline.spec.ts` — `context.route('**', abort)` for
   non-localhost requests; `/preview` still renders every primitive section
   (fonts are self-hosted; nothing may fetch the network).
5. `pnpm test:e2e` script; add a **separate job** to
   `.github/workflows/workbench-ui.yml` if R0a's workflow exists on your
   base, else create the file with just your job (merge is trivial either
   way) — `timeout-minutes: 15`, cache playwright browsers.

### Verification before push

```bash
cd workbench-ui && pnpm build && pnpm test:e2e    # all green locally
```

PR title: `test(workbench): playwright smoke lane (ADR-0162 acceptance 5-7)`

---

## Brief R0c — Evidence addresses (URL = subject)

**Suggested operator:** Claude
**Scope:** React/TypeScript.  The audit-native deep-linking substrate every
R2 route will consume.

### Worktree

```bash
cd /Users/kaizenpro/Projects/core
git fetch origin
git worktree add ../core-wb-r0c origin/main -b feat/wb-r0c-evidence-addresses
cd ../core-wb-r0c/workbench-ui && pnpm install
```

### Read first

- `docs/workbench/wave-R-mastery-revamp.md` § R0c
- `workbench-ui/src/app/evidenceContext.tsx` (the `EvidenceSubject` union)
- `workbench-ui/src/app/App.tsx`, `useGlobalKeyboard.ts`,
  `commandRegistry.ts`

### Deliverables

1. `workbench-ui/src/app/evidenceAddress.ts`:
   - `subjectToUrl(subject: EvidenceSubject): string` — canonical path
     (`/trace/42`, `/proposals/<id>`, `/evals/<lane>`, `/replay/<artifact>`)
     plus `?inspect=` when the inspector is open on a different subject
   - `urlToSubject(params, searchParams): { route: EvidenceSubject | null,
     inspect: EvidenceSubject | null }` — total inverse; malformed input
     returns `null`, never throws
   - The codec speaks ALL subject kinds now, including ones whose routes are
     still placeholders — the grammar is fixed once.
2. `App.tsx` route params: `/trace/:turnId?`, `/proposals/:proposalId?`,
   `/evals/:laneId?`, `/replay/:artifactId?`.  Placeholder routes keep flat
   paths.
3. `EvidenceProvider` ↔ URL sync: `?inspect=` carries inspector subject +
   open state; deep link restores it; subject changes update the URL
   (`replace`, not `push` — selection churn must not pollute history).
4. Existing routes restore selection from their param on load and write it
   on selection change: `ProposalsRoute`, `EvalsRoute`, `ReplayRoute`.
5. `Cmd+Shift+C` in `useGlobalKeyboard`: copies
   `window.location.origin + subjectToUrl(current subject)`; no-op with no
   subject; input-focus guard applies.  Visible copy-confirmation must not
   auto-dismiss audit context (a transient inline "Copied" on the inspector
   header is fine; no toast).
6. Tests: codec round-trip for every subject kind (including malformed
   inputs); deep-link restores Proposals selection (MemoryRouter
   `initialEntries`); `?inspect=` restores inspector; URL updates use
   `replace`.

### Verification before push

```bash
cd workbench-ui && pnpm build
pnpm vitest run src/app/evidenceAddress.test.ts src/app/evidenceContext.test.tsx src/app/proposals/ProposalsRoute.test.tsx
# (per-file runs until R0a lands; then plain `pnpm test`)
```

PR title: `feat(workbench): evidence addresses — deep-linkable subjects + inspector URL state`

---

## Brief R0d — Interaction substrate (AFTER R0c merges)

**Suggested operator:** Codex or GPT5.5-Thinking
**Scope:** React/TypeScript.  List navigation, virtualization, panel chrome,
inspector resize, palette action verbs.

### Worktree

```bash
cd /Users/kaizenpro/Projects/core
git fetch origin
git worktree add ../core-wb-r0d origin/main -b feat/wb-r0d-interaction-substrate
cd ../core-wb-r0d/workbench-ui && pnpm install
ls src/app/evidenceAddress.ts || echo "STOP: R0c not merged"
```

### Deliverables

1. `src/design/hooks/useListNavigation.ts`: `j`/`k`/`ArrowUp`/`ArrowDown`/
   `Home`/`End` move focus, `Enter` activates, input-focus guard (reuse the
   `isInputFocused` pattern from `useGlobalKeyboard.ts`).  Roving tabindex or
   `aria-activedescendant` — focused row visibly distinct, screen-reader
   coherent.  Unit tested.
2. `src/design/components/VirtualizedList/`: wraps `@tanstack/react-virtual`
   (add dep, pinned), composes `useListNavigation`, deterministic item keys,
   stable scroll restoration.  Tested (virtualization kicks in above the
   threshold; keyboard nav still works across virtualized boundaries).
3. `src/design/components/Panel/`: header (title + toolbar slot) + body
   chrome, token-only.  This is the standard panel every R2 route composes.
4. Inspector resize in `Shell.tsx`: wire the existing `SplitPane` for the
   inspector column; width persisted to localStorage **with guarded access**
   (see commit `af8d4f75` for the precedent — storage can throw).
5. Palette action commands: `commandRegistry.ts` gains an action kind
   (discriminated union: `navigate` | `action`); routes register/unregister
   their own commands on mount (the deferred Wave-1 call-site pattern).
   First verbs: "Copy evidence link" (calls R0c's address copy), "Toggle
   inspector", and Evals registers "Run eval lane <lane>" (executes the
   existing read-only `POST /evals/run` — ADR-0160-allowed lane, not a
   mutation).
6. Wire it for real: Proposals list and Replay artifact list adopt
   `useListNavigation` + `SearchInput` (the `/` shortcut becomes real where
   mounted).
7. `KeyboardHelp.tsx`: advertise exactly the shortcuts that now work — and
   only those.  (If R0a removed `j/k` and `/` rows, restore them — they are
   real now.)

### Verification before push

```bash
cd workbench-ui && pnpm build && pnpm test     # R0a is merged by now: full run must exit green
```

PR title: `feat(workbench): interaction substrate — list nav, virtualization, panel chrome, inspector resize, palette verbs`

---

## Brief R1 — Design mastery pass (AFTER all R0 merges)

**Suggested operator:** Claude
**Scope:** one PR, visual + doctrine-as-tests.  No new routes, no new
endpoints.

### Worktree

```bash
cd /Users/kaizenpro/Projects/core
git fetch origin
git worktree add ../core-wb-r1 origin/main -b feat/wb-r1-design-mastery
cd ../core-wb-r1/workbench-ui && pnpm install
ls src/design/components/Panel || echo "STOP: R0d not merged"
```

### Deliverables

1. `Kbd` primitive; adopt in `KeyboardHelp` and palette shortcut hints.
2. Typography precision: `tabular-nums` on every metric cell
   (`MetadataTable` values, eval metrics, `turn_cost_ms`); type-scale audit
   against ADR-0162 §2; `text-wrap: balance` on headings.
3. Selection-state unification: one tokenized treatment for selected vs
   focused rows, applied across Proposals / Evals / Replay lists.
4. Hash display standard: 12-char truncation + copy + mono everywhere;
   consolidate `src/app/chat/CopyableHash.tsx` into `DigestBadge` and delete
   the duplicate (cleanup-as-you-find: imports, tests, preview entries).
5. `EvidenceChainRail` in `RightInspector`: the seven spine stages (intent →
   subject → provenance → admissibility → replay → authority → action), each
   rendered lit (evidence present) / dim (not applicable) / hollow (not
   recorded).  Status derives ONLY from fields the subject carries — never
   inferred, never faked.  "Not recorded" is an honest, visible state.
6. Empty-state glyphs: small static deterministic monochrome SVGs (inline,
   no asset fetches).
7. `Panel` adoption in Proposals + Evals routes (Chat/Replay opportunistic).
8. **Doctrine-as-tests:**
   - Route conformance test parametrized over implemented routes: empty /
     error / loading each render with next-action / reproducer /
     specific-label content (ADR-0162 §6, executable).
   - Raw-hex scan: vitest node test walking `src/**` asserting no
     hex/rgb literals outside `tokens.css`.
   - Schema-drift gate: `scripts/dump-schemas.py` (read-only AST walk over
     `workbench/schemas.py`, exact `scripts/dump-enums.py` pattern) →
     `schema-snapshot.json` → vitest asserts `src/types/api.ts` covers every
     dataclass field.  Engine schema drift fails loudly at test time.

### Verification before push

```bash
cd workbench-ui && pnpm build && pnpm test && pnpm test:e2e
cd .. && uv run python scripts/dump-schemas.py > /dev/null  # script runs clean
```

PR title: `feat(workbench): design mastery pass — chain rail, typography, doctrine-as-tests`

---

## After this pack

R2 briefs (Trace upgraded, Runs, Audit, Packs, Vault, Settings — parallel)
and R3 briefs (Replay Moment, deterministic DAG viewer, Demo Theater,
wrong=0 ledger) are authored once R0/R1 are on main, against the real
substrate.  Specs and exclusions: `docs/workbench/wave-R-mastery-revamp.md`.
