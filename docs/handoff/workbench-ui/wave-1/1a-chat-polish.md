# Brief 1a — Chat route polish

> **Operator:** Opus 4.6 (foundations / surface-contract sensitive)
> **Branch:** `workbench/wave-1a-chat-polish`
> **Base:** `feat/workbench-ui-continuation` @ `685aaae`
> **Estimated diff:** ~150–300 lines, UI only
> **Why this operator:** Chat is the one Phase 1 brief that touches the
> Runtime Surface Contract (`surface` / `walk_surface` / `articulation_surface`).
> Distinguishing those correctly under the addendum §2 is high-stakes.

---

## Dispatch line

```bash
git fetch origin && \
git worktree add /Users/kaizenpro/Projects/core-w1a-chat \
  -b workbench/wave-1a-chat-polish origin/feat/workbench-ui-continuation && \
cd /Users/kaizenpro/Projects/core-w1a-chat/workbench-ui && \
pnpm install
```

Then open the worktree in your editor and start.

---

## Doctrine refs (read before touching code)

- `docs/plans/workbench-ui-continuation.md` §Phase 1a
- `docs/plans/workbench-ui-continuation-addendum.md` §1 (Chat trust class),
  §2 (Trace surface contract — applies to Chat's trace drawer), §7 (PR checklist)
- `docs/runtime_contracts.md` — surface distinction and `trace_hash` stability

## Scope (owned files)

- `src/app/chat/**` — everything in this folder
- Test files colocated with the above

## May read (no edits)

- `src/types/api.ts` (append-only at the bottom of the chat section if
  new types are needed)
- `src/api/queries.ts` (no edits; this brief does not add hooks)

## Off-limits

- `src/design/**`
- `src/app/Shell.tsx`, `App.tsx`, `LeftNav.tsx`, `TopBar.tsx`, `StatusFooter.tsx`
- Any backend Python file
- Any placeholder file in `src/routes/`

## Tasks

- [ ] **State audit.** Walk every async surface in `src/app/chat/` and confirm
      it has loading, empty, and error states. Where missing, add them using
      `EmptyState` from `src/design/`.
- [ ] **Surface distinction.** Inspect the trace drawer / evidence panel. The
      three surfaces — `surface`, `walk_surface`, `articulation_surface` —
      must render as three distinct UI elements with labels the operator can
      tell apart at a glance. If currently conflated, separate them.
- [ ] **Navigation hardening.** From a turn response:
      - clicking `trace_hash` opens the trace drawer at that turn,
      - any proposal candidate links to its detail in the Proposals route
        (use the existing route path; do not invent a new one).
- [ ] **⌘K commands.** Confirm or add palette entries for `New chat session`
      and `Jump to proposal <id>`. Entries belong to chat; do not edit other
      features' entries.
- [ ] **Trace-hash stability test.** Add a test asserting that mounting the
      trace drawer, navigating nodes, and unmounting does not mutate any
      `trace_hash` value held in component state. This is the addendum §2
      proof obligation.
- [ ] **Tests for new interaction paths.** Use the existing `Shell.test.tsx`
      pattern: render under MemoryRouter + QueryClientProvider, drive
      interactions through `@testing-library/react`.

## Acceptance criteria

- Every async surface in `src/app/chat/` has loading + empty + error states.
- Trace drawer labels `surface` / `walk_surface` / `articulation_surface`
  distinctly. A reviewer should be able to point at each on screen.
- `trace_hash` stability test exists and passes.
- ⌘K entries for `New chat session` and `Jump to proposal` are present and
  keyboard-activatable.
- No edits to off-limits files. `git diff --stat` shows only `src/app/chat/`
  and (optionally) `src/types/api.ts` append-only.
- `pnpm test` and `pnpm test:enum-coverage` green.

## Validation

```bash
cd workbench-ui
pnpm install
pnpm test
pnpm test:enum-coverage
git diff --stat $(git merge-base HEAD origin/feat/workbench-ui-continuation)..HEAD
```

The diff-stat output must include only `src/app/chat/**` and optionally
appended lines in `src/types/api.ts`. Anything else is out of scope.

## PR

Title: `feat(workbench/chat): polish states, surface distinction, ⌘K (wave 1a)`

Body uses the template in `docs/handoff/workbench-ui/wave-1/README.md`.

## When done

- [ ] PR open against `feat/workbench-ui-continuation`
- [ ] CI green
- [ ] Mark this brief complete by checking the box in this file in a follow-up
      commit on the same PR (single source of truth: this file)
