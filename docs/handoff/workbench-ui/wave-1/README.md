# Workbench UI — Wave 1 Brief Pack

> **Parent plan:** `docs/plans/workbench-ui-continuation.md`
> **Binding addendum:** `docs/plans/workbench-ui-continuation-addendum.md`
> **Base branch:** `feat/workbench-ui-continuation` @ `685aaae`
> **Scope:** Phase 1 only — polish the four implemented routes

## What this wave does

Polish Chat, Proposals, Replay, and Evals so they are cohesive,
cross-linked, and handle loading/empty/error states consistently —
before any new route lands. All four routes are already implemented;
this is hardening, not feature work.

## Parallel safety

| Operator brief        | Owns                              | Read-only touches                |
|-----------------------|-----------------------------------|----------------------------------|
| 1a — Chat polish      | `src/app/chat/**`                 | `src/types/api.ts` (append only) |
| 1b — Proposals polish | `src/app/proposals/**`            | `src/types/api.ts` (append only) |
| 1c — Replay polish    | `src/app/replay/**`               | `src/types/api.ts` (append only) |
| 1d — Evals polish     | `src/app/evals/**`                | `src/types/api.ts` (append only) |

**Off-limits to every brief:**
- `src/design/**` (protected substrate — plan constraint)
- `src/app/Shell.tsx`, `LeftNav.tsx`, `TopBar.tsx`, `StatusFooter.tsx`
- `src/app/App.tsx` route table (no swaps in Wave 1)
- Any placeholder file in `src/routes/` (those belong to Phase 2+)
- `workbench-ui/src/design/tokens.css` and friends
- Backend Python (this is a UI-only wave)

**Coordinated surface:**
- CommandPalette entries: each brief adds **only** entries for its
  own feature; no brief edits another's entries. If a conflict appears
  at merge, the second-merging brief rebases additively.
- `src/types/api.ts`: append-only additions to the bottom of the
  matching section. No edits to existing types.

## Dispatch DAG

```
        ┌── 1a Chat polish (Opus 4.6) ───────┐
main ──>│                                    │── merge any order
        │── 1b Proposals polish (Sonnet 4.6)─│   (all four parallel-safe)
        │                                    │
        │── 1c Replay polish (Gemini 3.1) ───│
        │                                    │
        └── 1d Evals polish (GPT-OSS/Copilot)┘
```

All four briefs are dispatchable simultaneously. No order dependency.

## Doctrine that applies to every brief

From `docs/plans/workbench-ui-continuation-addendum.md`:

- **§1 trust classification.** Chat = read + turn-submit; Proposals = proposal-only;
  Replay = read-only; Evals = read-only. No brief introduces a write path.
- **§2 surface contract (Chat brief only).** `surface`, `walk_surface`, and
  `articulation_surface` rendered distinctly; `trace_hash` stability test required.
- **§7 per-PR checklist.** Every PR answers the four CLAUDE.md §PR Checklist
  questions in its description.
- **§8 proof obligations.** New TS unions must have a test that fails under
  their named violation, or the type is decoration.

## Validation each brief must run

```bash
cd workbench-ui
pnpm install      # if first time on this worktree
pnpm test         # all green
pnpm test:enum-coverage
```

Backend-touching changes are **out of scope** for Wave 1 and must be
rejected at review. Any "while I'm here" backend edit means the PR
fails the trust-classification check.

## PR template (every brief uses this)

```markdown
## Wave 1 brief: <1a|1b|1c|1d> — <feature> polish

### Trust classification
<read-only | read + turn-submit | proposal-only>

### CLAUDE.md §PR Checklist
- Capability/property/boundary added: <one line>
- Invariant preserved: <one line, e.g. trace_hash stability, no design-substrate edit>
- CLI/test lane that proves it: pnpm test + pnpm test:enum-coverage (UI-only)
- Trust boundary enforced: <one line; "no write paths introduced">

### Diff scope
- Owned: <files>
- Read-only touched: <files>
- Off-limits respected: yes

### Tests
- Added: <tests>
- Passing: pnpm test green; pnpm test:enum-coverage green
```

## Done criteria for the wave

- [ ] All four PRs merged to `feat/workbench-ui-continuation`
- [ ] No off-limits files modified across the merged set
- [ ] No backend changes across the merged set
- [ ] `pnpm test` and `pnpm test:enum-coverage` green on the merged tip
- [ ] CommandPalette has entries for the new interactions added by each brief
- [ ] All four briefs in this folder marked done in their respective files
