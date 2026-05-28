# Brief 1b — Proposals route polish

> **Operator:** Sonnet 4.6 (tight-scope route work)
> **Branch:** `workbench/wave-1b-proposals-polish`
> **Base:** `feat/workbench-ui-continuation` @ `685aaae`
> **Estimated diff:** ~150–250 lines, UI only
> **Why this operator:** Proposals has a well-defined lifecycle
> (pending / accepted / rejected / withdrawn) and clear color tokens
> already in `src/design/`. Tight contract, no surface-contract surprises.

---

## Dispatch line

```bash
git fetch origin && \
git worktree add /Users/kaizenpro/Projects/core-w1b-proposals \
  -b workbench/wave-1b-proposals-polish origin/feat/workbench-ui-continuation && \
cd /Users/kaizenpro/Projects/core-w1b-proposals/workbench-ui && \
pnpm install
```

---

## Doctrine refs

- `docs/plans/workbench-ui-continuation.md` §Phase 1b
- `docs/plans/workbench-ui-continuation-addendum.md` §1 (Proposals is
  proposal-only — no direct accept/reject endpoints introduced; UI only
  calls existing API), §7 (PR checklist)

## Scope (owned files)

- `src/app/proposals/**`
- Test files colocated with the above

## May read (no edits)

- `src/api/queries.ts` — observe existing `useProposals` / `useProposal` shapes
- `src/design/tokens.css` — read review-lifecycle tokens; do not edit
- `src/types/api.ts` — append-only at the bottom of proposals section if needed

## Off-limits

- `src/design/**` (including tokens)
- Shell / TopBar / LeftNav / StatusFooter / App.tsx
- Any backend Python file
- Any placeholder file
- Any new proposal-mutation endpoint or hook (proposal-only discipline)

## Tasks

- [ ] **State audit.** Confirm queue list and proposal detail handle loading,
      empty, and error consistently. Wire `EmptyState` from `src/design/`
      where missing.
- [ ] **Lifecycle color consistency.** The four states (`pending`,
      `accepted`, `rejected`, `withdrawn`) must render with the same color
      tokens in both list and detail. Verify each token is referenced via
      CSS custom property — no hex literals.
- [ ] **Cross-route links.** From proposal detail:
      - link to the source artifact (use existing Runs/artifact route path
        if present; otherwise the artifact route Phase 2 will introduce —
        for now link to the Replay-comparison entry-point if that exists),
      - link to the replay-comparison view for the proposal if applicable.
      Document any link that cannot land because the target route is a
      placeholder; leave a TODO with the route name.
- [ ] **Suggested-CLI block.** Make the suggested-CLI snippet block
      `user-select: text` (or a copy button) so the operator can copy it.
- [ ] **⌘K command entries.** Add `Open proposal <id>` palette entry
      driven by the existing `useProposals` query. Only proposals entries —
      do not touch other features'.
- [ ] **Route tests.** Cover at least:
      - queue renders with loading → success transition,
      - empty state when zero proposals returned,
      - error state when query errors,
      - lifecycle color class applied per state.

## Acceptance criteria

- Loading / empty / error covered everywhere in `src/app/proposals/`.
- All four lifecycle states render with the documented tokens, no hex
  literals anywhere in this brief's diff (`grep -E '#[0-9a-fA-F]{3,6}'`
  returns nothing in the diff).
- Suggested-CLI block is selectable or has a copy button.
- ⌘K entries for proposals are present and keyboard-activatable.
- No backend changes. No off-limits files touched.
- `pnpm test` and `pnpm test:enum-coverage` green.

## Validation

```bash
cd workbench-ui
pnpm install
pnpm test
pnpm test:enum-coverage
git diff --stat $(git merge-base HEAD origin/feat/workbench-ui-continuation)..HEAD
# Verify no hex literals introduced
git diff $(git merge-base HEAD origin/feat/workbench-ui-continuation)..HEAD -- 'src/app/proposals/**' | grep -E '^\+.*#[0-9a-fA-F]{3,6}' && echo "FAIL: hex literal introduced" || echo "ok: no hex literals"
```

## PR

Title: `feat(workbench/proposals): polish states, lifecycle colors, links (wave 1b)`

Body uses the template in `docs/handoff/workbench-ui/wave-1/README.md`.

## When done

- [ ] PR open against `feat/workbench-ui-continuation`
- [ ] CI green
- [ ] This brief checked complete on the PR
