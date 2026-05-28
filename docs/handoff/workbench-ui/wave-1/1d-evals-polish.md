# Brief 1d — Evals route polish

> **Operator:** GPT-OSS-120B or GitHub Copilot cloud agent (mechanical)
> **Branch:** `workbench/wave-1d-evals-polish`
> **Base:** `feat/workbench-ui-continuation` @ `685aaae`
> **Estimated diff:** ~120–200 lines, UI only
> **Why this operator:** Evals polish is mostly mechanical: state audits,
> numeric column alignment, route tests. Clear acceptance criteria, narrow
> file scope, no surface-contract subtlety. Ideal for a local or
> cloud-mechanical operator.

---

## Dispatch line

```bash
git fetch origin && \
git worktree add /Users/kaizenpro/Projects/core-w1d-evals \
  -b workbench/wave-1d-evals-polish origin/feat/workbench-ui-continuation && \
cd /Users/kaizenpro/Projects/core-w1d-evals/workbench-ui && \
pnpm install
```

---

## Doctrine refs

- `docs/plans/workbench-ui-continuation.md` §Phase 1d
- `docs/plans/workbench-ui-continuation-addendum.md` §1 (Evals = read-only;
  no lane mutation, no "suppress failing case" affordance), §7 (PR checklist)
- Evals UI must not hide or suppress failing cases. Filters that change
  view are fine; filters that remove failing cases from the underlying
  count are not.

## Scope (owned files)

- `src/app/evals/**`
- Test files colocated with the above

## May read (no edits)

- `src/api/queries.ts` — `useEvalLanes`, `useEvalLane`, `useEvalExecution`
- `src/design/tokens.css` — read; do not edit
- `src/types/api.ts` — append-only at the bottom of evals section if needed

## Off-limits

- `src/design/**`
- Shell / TopBar / LeftNav / StatusFooter / App.tsx
- Any backend Python file
- Any placeholder file
- Any affordance that mutates a lane definition or hides a failing case

## Tasks

- [ ] **State audit.** Lane list and eval-run view: loading, empty
      (no lanes; no runs for selected lane), error states.
- [ ] **Numeric column alignment.** Wherever numeric metrics render in a
      list or table, they must be right-aligned, monospace-numeric, and
      use tabular-nums for consistent digit width. Use existing tokens.
- [ ] **Metric readability.** Where a metric is shown alongside a target,
      render `actual / target` with the actual value emphasized. If a
      metric is failing (actual < target where higher-is-better, or
      actual > target where lower-is-better), apply the existing
      failure color token. No new tokens.
- [ ] **Lane selection persistence.** Selected lane should be reflected in
      the URL (query string is fine). Reloading the page should restore the
      selection.
- [ ] **⌘K command entry.** Add `Open eval lane <name>` palette entries
      driven by the existing `useEvalLanes` query. Only evals entries.
- [ ] **Route tests.** Cover:
      - lane list loading → success,
      - empty state when no lanes,
      - run view rendering metrics with correct alignment,
      - failure color applied when metric does not meet target.

## Acceptance criteria

- Every async surface in `src/app/evals/` has loading + empty + error.
- All numeric metric columns are right-aligned with `tabular-nums`.
- Failing metrics use the existing failure token, no hex literals.
- Lane selection survives reload via URL state.
- ⌘K `Open eval lane` entries present and keyboard-activatable.
- No backend changes. No off-limits files touched. No affordance that
  suppresses or hides failing cases.
- `pnpm test` and `pnpm test:enum-coverage` green.

## Validation

```bash
cd workbench-ui
pnpm install
pnpm test
pnpm test:enum-coverage
git diff --stat $(git merge-base HEAD origin/feat/workbench-ui-continuation)..HEAD

# No hex literals in the diff
git diff $(git merge-base HEAD origin/feat/workbench-ui-continuation)..HEAD -- 'src/app/evals/**' | grep -E '^\+.*#[0-9a-fA-F]{3,6}' && echo "FAIL: hex literal introduced" || echo "ok: no hex literals"

# No mutation hooks introduced
git diff $(git merge-base HEAD origin/feat/workbench-ui-continuation)..HEAD -- 'src/app/evals/**' | grep -E '^\+.*useMutation' && echo "FAIL: mutation introduced" || echo "ok: read-only preserved"
```

## PR

Title: `feat(workbench/evals): polish states, numeric alignment, lane URL state (wave 1d)`

Body uses the template in `docs/handoff/workbench-ui/wave-1/README.md`.

## When done

- [ ] PR open against `feat/workbench-ui-continuation`
- [ ] CI green
- [ ] This brief checked complete on the PR
