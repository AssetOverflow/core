# Brief 1c — Replay route polish

> **Operator:** Gemini 3.1 Pro (survey + cross-file presentation work)
> **Branch:** `workbench/wave-1c-replay-polish`
> **Base:** `feat/workbench-ui-continuation` @ `685aaae`
> **Estimated diff:** ~150–250 lines, UI only
> **Why this operator:** Replay polish requires reading divergence
> rendering across multiple files and improving clarity of metadata
> presentation. Gemini's strength is cross-file survey + presentation
> reasoning over a moderate diff surface.

---

## Dispatch line

```bash
git fetch origin && \
git worktree add /Users/kaizenpro/Projects/core-w1c-replay \
  -b workbench/wave-1c-replay-polish origin/feat/workbench-ui-continuation && \
cd /Users/kaizenpro/Projects/core-w1c-replay/workbench-ui && \
pnpm install
```

---

## Doctrine refs

- `docs/plans/workbench-ui-continuation.md` §Phase 1c
- `docs/plans/workbench-ui-continuation-addendum.md` §1 (Replay = read-only;
  no "fix" buttons, no artifact writes), §7 (PR checklist)
- The Replay route should never present an affordance to mutate an
  artifact. Read + render + link out only.

## Scope (owned files)

- `src/app/replay/**`
- Test files colocated with the above

## May read (no edits)

- `src/api/queries.ts` — observe `useReplayComparison`, `useArtifacts`, `useArtifact`
- `src/design/tokens.css` — divergence-severity tokens
- `src/types/api.ts` — append-only at the bottom of replay section if needed

## Off-limits

- `src/design/**`
- Shell / TopBar / LeftNav / StatusFooter / App.tsx
- Any backend Python file
- Any placeholder file
- **No mutating affordances of any kind** — no "rerun", "save", "fix",
  "accept divergence" buttons. Read-only doctrine.

## Tasks

- [ ] **Survey current state.** Read every file in `src/app/replay/` and
      produce a short comment block at the top of the route (or in this
      brief's PR description) summarizing what each component does. This
      forces a complete read before edits.
- [ ] **State audit.** Artifact-selector and comparison view: loading,
      empty (no artifacts available; selection invalid), error states.
- [ ] **Divergence-severity clarity.** Currently the divergence severity
      may be coded via color alone. Add a textual severity label next to
      the color band (e.g. `low`, `material`, `breaking`) so the meaning
      is unambiguous without the color legend.
- [ ] **Metadata presentation.** Artifact metadata (timestamp, trace_hash,
      run id, lane) should be presented in a key-value table or definition
      list with consistent alignment. No "wall of text" rendering.
- [ ] **Back-link to proposal.** When the comparison view is reached from
      a proposal, show a "Back to proposal #N" link. When reached directly,
      do not show the link. Drive this from URL state, not props.
- [ ] **Route tests.** Cover:
      - artifact selection populating comparison view,
      - empty state when no artifacts,
      - error state when comparison query fails,
      - severity label rendering for each severity bucket.

## Acceptance criteria

- Every async surface in `src/app/replay/` has loading + empty + error.
- Divergence severity is conveyed by **both** color **and** text label.
- Artifact metadata renders as a structured key-value layout.
- Back-link to proposal appears only when route was entered from a proposal.
- No mutating affordances anywhere in the diff.
- No backend changes. No off-limits files touched.
- `pnpm test` and `pnpm test:enum-coverage` green.

## Validation

```bash
cd workbench-ui
pnpm install
pnpm test
pnpm test:enum-coverage
git diff --stat $(git merge-base HEAD origin/feat/workbench-ui-continuation)..HEAD

# Confirm no write paths introduced (no new mutation hooks)
git diff $(git merge-base HEAD origin/feat/workbench-ui-continuation)..HEAD -- 'src/app/replay/**' | grep -E '^\+.*(useMutation|fetch\(|axios\.(post|put|patch|delete))' && echo "FAIL: mutation introduced" || echo "ok: read-only preserved"
```

## PR

Title: `feat(workbench/replay): polish states, severity labels, metadata layout (wave 1c)`

Body uses the template in `docs/handoff/workbench-ui/wave-1/README.md`.

## When done

- [ ] PR open against `feat/workbench-ui-continuation`
- [ ] CI green
- [ ] This brief checked complete on the PR
