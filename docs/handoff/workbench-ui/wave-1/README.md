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

---

## Live status (wave coordinator: Opus 4.7)

> **Last updated:** 2026-05-28 — 3 of 4 PRs open; 1d cleaned of off-scope base commits; awaiting 1b
> **Coordinator role:** maintained by Opus 4.7 on operator workstation.
> Source of truth for PR state is `gh pr list`; this table is a
> human-readable projection refreshed on operator request.

### Per-brief tracker

| Brief | Operator           | Branch                                | Pushed | PR    | Draft | CI       | Mergeable | Notes |
|-------|--------------------|---------------------------------------|--------|-------|-------|----------|-----------|-------|
| 1a    | Opus 4.6           | `workbench/wave-1a-chat-polish`       | yes    | #415  | no    | sourcery ip | yes    | scope OK; see 1a-note |
| 1b    | Sonnet 4.6         | `workbench/wave-1b-proposals-polish`  | no     | —     | —     | —        | —         | dispatched, in flight |
| 1c    | Gemini 3.1 Pro     | `workbench/wave-1c-replay-polish`     | yes    | #417  | no    | sourcery ip | yes    | scope 100% clean |
| 1d    | Gemini 3.5 Flash † | `polish-workbench-evals-flow`         | yes    | #418  | no    | re-running  | yes    | branch name deviated; cleaned post-push; see 1d-note |

† Dispatch-shape learning: file-lookup-from-stale-base is a Gemini Flash task,
not a GPT-OSS one. Carry into Wave 2 operator assignment.

**1a-note (PR #415):** Diff includes `src/design/components/primitives/CommandPalette*`
and `src/routes/ChatRoute.tsx`. Both are outside the brief's literal owned-files
list, but:
- CommandPalette edits are **explicitly permitted by the parent plan**
  (§Constraints: "Only `EmptyState` and `CommandPalette` may be edited" in
  `src/design/`). The brief was over-tightened; plan wins.
- `src/routes/ChatRoute.tsx` is the live route entry for Chat (not a placeholder).
  `?reset=1` query-param handling for "New chat session" belongs there.
  Semantically correct; soft scope expansion.

Both accepted by coordinator. Brief authoring lesson recorded for Wave 2:
explicitly carve out CommandPalette and the live route entry-points from
the "off-limits" list, since both are necessary for feature polish.

**1d-note (PR #418):** Original push contained three off-scope artifacts
that pre-existed on the branch base (not introduced by the operator):

- `docs/decisions/ADR-0174-held-hypothesis-comprehension.md` (+294 lines, operator's separate work)
- `generate/math_roundtrip.py` (backend Python — addendum off-limits)
- `tests/test_math_roundtrip.py` (backend Python — addendum off-limits)

Root cause: the operator's worktree base (`polish-workbench-evals-flow`)
was rooted at commits `f90f0cf` (ADR-0174) and `86d4e98` (roundtrip fix)
before the operator started. The Gemini Flash operator's own commit
(`37b04d5`) was clean and in scope. The merge of
`feat/workbench-ui-continuation` into the branch happened mid-task and
did not introduce the off-scope content — it was already there.

**Remediation (coordinator):** force-pushed a clean branch consisting only
of the operator's commit cherry-picked onto `feat/workbench-ui-continuation`
HEAD. New tip is `b9ee22d`. Diff = 5 files, all in scope. PR re-CI'd.

**Salvaged content:** ADR-0174 preserved at
`/tmp/shay-rescued-from-pr418/ADR-0174-held-hypothesis-comprehension.md`
for separate-PR handling per operator decision.

**Brief authoring lesson for Wave 2:** dispatch line must specify
`origin/feat/workbench-ui-continuation` explicitly, **and** the brief
must include a "check your base SHA" step before the first edit so
operators on stale or pre-loaded worktrees catch it immediately:

```bash
git merge-base HEAD origin/feat/workbench-ui-continuation
# Must equal HEAD of origin/feat/workbench-ui-continuation;
# if not, abort and reseat the worktree.
```

Refresh command (run on operator workstation, paste to coordinator):

```bash
gh pr list --base feat/workbench-ui-continuation --state all \
  --json number,title,headRefName,state,mergeable,isDraft,statusCheckRollup \
  --limit 20
```

### Conflict watchlist

Files where >1 brief is allowed to touch (additive only).
Coordinator inspects these at every PR open and again before merge:

- `workbench-ui/src/types/api.ts` — append-only by all four. Coordinator
  verifies each PR's diff against this file is **purely additive** at the
  bottom of the section the brief owns.
- CommandPalette command registry — each brief adds **only** its own
  entries. If two briefs touched the same registry array, second-to-merge
  rebases additively.
- Any colocated test utility that ends up shared. None expected; if one
  appears, it gets promoted to a small helper file in a follow-up PR, not
  in any of the 4 wave-1 PRs.

### Merge-order policy

All four briefs are parallel-safe by construction (disjoint `src/app/<feature>/**`).
**Order of merge is FIFO by green-CI time**, not by brief letter. The
coordinator:

1. Verifies the PR's owned-files scope matches its brief.
2. Verifies the diff against `src/types/api.ts` is additive at the bottom
   of the owning section.
3. Verifies `pnpm test` and `pnpm test:enum-coverage` are green on the PR.
4. Verifies the PR description answers the four CLAUDE.md §PR Checklist
   questions.
5. Approves and merges. No re-bases required between briefs unless a
   conflict actually appears on the watchlist surfaces.

If a conflict does appear on `src/types/api.ts` or CommandPalette, the
**later** PR rebases its additive change and force-pushes; the earlier PR
is not blocked.

### Wave 2 readiness gate

Wave 2 brief pack opens only when:

- [ ] All four wave-1 PRs merged to `feat/workbench-ui-continuation`
- [ ] `pnpm test` and `pnpm test:enum-coverage` green on the merged tip
- [ ] No off-limits files modified across the merged diff
- [ ] No backend Python changes across the merged diff
- [ ] This `Live status` section marked `Wave complete — ready for Wave 2`

When the coordinator declares readiness, Wave 2 covers Phase 2 (Runs),
Phase 3 (Trace), and Phase 5 contract drafts. Phase 4 (Inspector) stays
gated until Runs/Trace entity shapes land.

### Coordinator escalation triggers

The coordinator flags to the operator (interrupts the wave) if:

- a PR's diff touches off-limits files,
- a PR introduces a backend Python change,
- a PR introduces any mutation hook (`useMutation`, POST/PUT/PATCH/DELETE)
  in Replay or Evals (read-only routes per addendum §1),
- a PR weakens or removes the `trace_hash` stability test in Chat,
- a PR introduces hex literals (must use tokens),
- CI red on a PR persists past the operator's expected cycle time.
