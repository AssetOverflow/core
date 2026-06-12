# Wave 1 Evidence Spine — Dispatch Briefs

Date: 2026-06-12
Plan: `docs/workbench/wave-1-evidence-spine.md`
Merge target: `main`

## Dispatch DAG

```
Wave A (parallel — no dependencies between them):
  Brief 1: Backend Journal + Trace API       [GPT5.5]  feat/wb-journal
  Brief 2: Evidence Primitives               [Claude]   feat/wb-primitives
  Brief 3: Mutation Doctrine Docs            [GPT5.5]  feat/wb-mutation-docs

Wave B (after Brief 2 merges):
  Brief 4: Evidence Context + Inspector +    [Claude]   feat/wb-evidence-ui
           Command Registry

Wave C (after Briefs 1 + 4 merge):
  Brief 5: Trace Route                       [GPT5.5]  feat/wb-trace-route
```

Merge order: `3 → (1 ∥ 2) → 4 → 5`
Brief 3 can merge anytime (docs-only). Briefs 1 and 2 are parallel and
independent. Brief 4 requires Brief 2 on main. Brief 5 requires Briefs 1
and 4 on main.

---

## Brief 1 — Backend Journal + Trace API

**Agent:** GPT5.5-Thinking
**Scope:** Python backend only. No frontend, no React, no TypeScript.

### Worktree setup

```bash
cd /Users/kaizenpro/Projects/core
git fetch origin
git worktree add ../core-wb-journal origin/main -b feat/wb-journal
cd ../core-wb-journal
```

### Brief

You are building the Workbench Turn Evidence Journal — a local, append-only
JSONL record of the `ChatTurnResult` envelope already returned by
`/chat/turn`. This is a read model, not runtime memory, not teaching memory,
and not a cognitive runtime fork.

**Why this exists:** The workbench backend currently does NOT attach a
telemetry sink to chat turns. `WorkbenchApi()` constructs with no sink,
`_run_chat_turn()` creates a bare `ChatRuntime()`, and
`serialize_turn_event` redacts content by default. The journal records the
exact evidence the operator already saw, so the Trace route (Brief 5) can
display it honestly.

**Read before writing code:**
- `docs/workbench/wave-1-evidence-spine.md` — section 1D (your spec)
- `docs/workbench/api-contract-v1.md` — existing contract, especially line 231
  (three surfaces must stay separate)
- `workbench/api.py` — current `_run_chat_turn()` implementation
- `workbench/schemas.py` — existing schema patterns
- `workbench/server.py` — request routing
- `workbench/readers.py` — existing reader patterns

**Deliverables:**

1. `workbench/journal.py`
   - `TurnJournalEntry` frozen dataclass: `turn_id` (int, sequential),
     `timestamp` (ISO-8601 UTC), `trace_hash`, `prompt`, `surface`,
     `articulation_surface`, `walk_surface`, `grounding_source`,
     `epistemic_state`, `normative_clearance`, `verdicts` (identity/safety/
     ethics), `refusal_emitted`, `hedge_injected`, `proposal_candidates`,
     `turn_cost_ms`, `checkpoint_emitted`, `journal_digest` (SHA-256)
   - `TurnJournalSummary` frozen dataclass: `turn_id`, `timestamp`,
     `prompt_excerpt` (first 120 chars), `surface_excerpt` (first 120 chars),
     `trace_hash`, `grounding_source`
   - `TurnJournal` class: `__init__(journal_dir: Path)`, `append(entry)`,
     `list_summaries(limit, offset)`, `get_entry(turn_id)`,
     `next_turn_id() -> int`
   - Journal path: `workbench_data/turn_journal.jsonl`
   - JSONL is pure — every line valid JSON. No text headers.
   - `journal_digest` = SHA-256 of the canonical JSON serialization of the
     entry (excluding the digest field itself)
   - Append-only: no update, no delete, no truncation

2. `workbench_data/README.md`
   - Content-bearing warning: journal entries contain user prompts and engine
     surfaces. This file stores evidence already returned to the local
     operator. Not teaching memory. Not runtime memory.

3. Wire journal into `workbench/api.py`
   - `WorkbenchApi.__init__` creates a `TurnJournal` instance
   - After a successful `/chat/turn` response, append the result to the
     journal before returning the HTTP response
   - `turn_id` assigned by `TurnJournal.next_turn_id()`
   - Add `turn_id` to the existing `ChatTurnResult` response so the frontend
     can reference it

4. New API routes in `workbench/api.py`
   - `GET /trace/turns?limit=50&offset=0` — returns journal summaries in
     stable sequential order, inside `{ ok, generated_at, data: { items } }`
     envelope
   - `GET /trace/{turn_id}` — returns full journal entry for a turn, or 404
     for unknown turn_id. Never return synthetic data.
   - Update route dispatch in `do_GET` / `do_POST` handlers

5. Schema additions in `workbench/schemas.py`
   - `TurnJournalEntrySchema` and `TurnJournalSummarySchema` for API
     serialization (following existing patterns in the file)

6. Tests in `tests/test_workbench_journal.py`
   - Append-only: entries never modified or deleted
   - Stable ordering: sequential by turn_id
   - Prompt/content size limits: max 4096 chars prompt (matching existing
     `/chat/turn` validation)
   - Path confinement: journal writes only to `workbench_data/`
   - No journal writes to `teaching/`, `packs/`, `language_packs/data/`
   - No NEW writes to `engine_state/` beyond existing chat checkpoint behavior
     (ADR-0146/0150)
   - Journal digest is deterministic for identical content
   - Round-trip: `/chat/turn` response fields == `/trace/{turn_id}` fields
   - Unknown turn_id returns 404
   - Pagination: limit/offset produce correct slices
   - Empty journal returns empty items list, not error

**Constraints:**
- Use Python stdlib only (no FastAPI, no pydantic, no new dependencies)
- Follow existing `workbench/` code patterns (frozen dataclasses, readers)
- All three surfaces stored as separate fields — never merge them
- `workbench_data/` should be gitignored (add to `.gitignore` if not present)
- Run `uv run python -m pytest tests/test_workbench_journal.py -q` green
- Run `uv run python -m pytest tests/test_workbench_api.py -q` still green
  (existing tests must not break)
- Run `core test --suite smoke -q` green

### Work completed when

- [ ] `workbench/journal.py` exists with `TurnJournal`, `TurnJournalEntry`,
      `TurnJournalSummary`
- [ ] `/chat/turn` appends to journal and returns `turn_id`
- [ ] `GET /trace/turns` returns paginated summaries from real journal
- [ ] `GET /trace/{turn_id}` returns full entry or 404
- [ ] `workbench_data/README.md` documents content-bearing nature
- [ ] `workbench_data/` is gitignored
- [ ] All tests green: journal tests + existing workbench tests + smoke

### Update the plan

In `docs/workbench/wave-1-evidence-spine.md`, check off every box under
section 1D (Backend, New API endpoints, Tests). Do NOT check off section 1E
(Trace Route frontend) — that is Brief 5.

### PR and merge

```bash
cd ../core-wb-journal
git add workbench/journal.py workbench_data/README.md tests/test_workbench_journal.py
git add workbench/api.py workbench/schemas.py workbench/server.py
git add .gitignore docs/workbench/wave-1-evidence-spine.md
# Include any other changed files
git commit -m "feat(workbench): turn evidence journal + trace API (Wave 1D)

Append-only JSONL journal records the exact ChatTurnResult envelope
returned by /chat/turn with stable turn_id, trace_hash, all three
surfaces, verdicts, and deterministic journal_digest.

GET /trace/turns and GET /trace/{turn_id} serve journal evidence
for the Trace route frontend (Brief 5).

Read model only — no teaching/pack/engine_state mutation."
```

Push and open PR against `main`:
```bash
git push -u origin feat/wb-journal
gh pr create --title "feat(workbench): turn evidence journal + trace API (Wave 1D)" \
  --body "$(cat <<'EOF'
## Summary
- Adds `workbench/journal.py` — append-only JSONL turn evidence journal
- Wires journal into `/chat/turn` response path
- Adds `GET /trace/turns` and `GET /trace/{turn_id}` API endpoints
- Part of Wave 1 evidence spine (`docs/workbench/wave-1-evidence-spine.md`)

## Test plan
- [ ] `uv run python -m pytest tests/test_workbench_journal.py -q`
- [ ] `uv run python -m pytest tests/test_workbench_api.py -q`
- [ ] `core test --suite smoke -q`
- [ ] Manual: `core workbench api`, POST a chat turn, GET /trace/turns
EOF
)"
```

### Worktree cleanup

After merge:
```bash
cd /Users/kaizenpro/Projects/core
git worktree remove ../core-wb-journal
git branch -d feat/wb-journal
```

---

## Brief 2 — Evidence Primitives

**Agent:** Claude (Opus 4.6)
**Scope:** React/TypeScript frontend only. No Python, no backend changes.

### Worktree setup

```bash
cd /Users/kaizenpro/Projects/core
git fetch origin
git worktree add ../core-wb-primitives origin/main -b feat/wb-primitives
cd ../core-wb-primitives
```

### Brief

Build the six evidence primitives that Wave 1 needs. These are shared
design-system components used by the Trace route, Inspector, Command
Registry, and future Wave 2 routes. Build them with the same care as
building an oscilloscope panel — precise, token-driven, keyboard-navigable,
dark, calm.

**Read before writing code:**
- `docs/workbench/wave-1-evidence-spine.md` — section 1C
- `docs/workbench/design-system.md` — existing design system baseline
- `workbench-ui/src/design/tokens/tokens.css` — actual token names
- `workbench-ui/src/design/tokens/tokens.ts` — TypeScript token mirror
- `workbench-ui/src/design/components/` — existing component patterns
  (badges, primitives, states, StableJsonViewer)
- `workbench-ui/src/preview/PreviewPage.tsx` — preview page structure

**Deliverables — six components under
`workbench-ui/src/design/components/`:**

1. `SplitPane/SplitPane.tsx`
   - Resizable horizontal or vertical split via drag handle
   - Props: `direction: 'horizontal' | 'vertical'`, `defaultSplit: number`
     (percentage), `minSize: number` (px), `children: [ReactNode, ReactNode]`
   - Drag handle uses `cursor: col-resize` or `row-resize`
   - Persists split position in localStorage (keyed by caller-provided id)
   - Respects `prefers-reduced-motion` for any resize animation

2. `TabBar/TabBar.tsx`
   - Accessible tab bar with ARIA `role="tablist"`, `role="tab"`,
     `role="tabpanel"` attributes
   - Do NOT add `@radix-ui/react-tabs` as a dependency — implement with
     native ARIA semantics
   - Props: `tabs: Array<{ id: string, label: string }>`,
     `activeTab: string`, `onTabChange: (id: string) => void`,
     `children: ReactNode` (renders the active panel)
   - Keyboard: `ArrowLeft`/`ArrowRight` moves focus between tabs,
     `Enter`/`Space` activates, `Home`/`End` jumps to first/last
   - Active tab gets `aria-selected="true"` + visual indicator via
     `--color-border-accent`

3. `MetadataTable/MetadataTable.tsx`
   - Key-value pair display for structured metadata
   - Props: `rows: Array<{ key: string, value: ReactNode, copyable?: boolean }>`
   - Keys rendered in `--font-size-xs` with `--color-text-secondary`
   - Values rendered in `--font-size-sm` with `--color-text-primary`
   - Copyable values show a copy icon on hover, click copies to clipboard
   - Monospace font (`--font-mono`) for hash/digest/numeric values
   - Stable row ordering (render in array order, no sorting)

4. `DigestBadge/DigestBadge.tsx`
   - Copyable hash/digest display with truncation and verification indicator
   - Props: `digest: string`, `algorithm?: string` (default 'sha256'),
     `verified?: boolean | null`, `truncate?: number` (default 16)
   - Display: `sha256:abc123de...` with monospace font
   - Click copies full digest to clipboard, shows brief "Copied" feedback
   - Verified indicator: green dot (true), red dot (false), gray dot (null)
   - `aria-label` includes full digest for screen readers

5. `Timestamp/Timestamp.tsx`
   - Relative + absolute time display
   - Props: `iso: string` (ISO-8601 UTC), `format?: 'relative' | 'absolute'
     | 'both'` (default 'both')
   - Relative: "2m ago", "3h ago", "yesterday" (updates on 60s interval)
   - Absolute: formatted in PST/PDT (America/Los_Angeles) per user preference
   - Hover tooltip shows the other format (if relative shown, tooltip shows
     absolute, and vice versa)
   - `<time datetime="...">` element for semantic HTML

6. `SearchInput/SearchInput.tsx`
   - Filtered search input with keyboard shortcut binding
   - Props: `placeholder: string`, `value: string`,
     `onChange: (value: string) => void`, `shortcut?: string` (default '/')
   - Global keyboard listener: pressing the shortcut key focuses the input
     (unless already in an input/textarea)
   - Clear button (x) when value is non-empty
   - `--font-size-sm`, border uses `--color-border-default`, focus ring via
     `--color-focus-ring`
   - Debounced onChange (150ms) for performance

**For every component:**
- Built with design tokens only — no raw hex/rgb/hardcoded colors
- Motion via `--motion-duration-*` and `--motion-ease-*` tokens
- `prefers-reduced-motion: reduce` collapses motion to instant
- `:focus-visible` ring via `--color-focus-ring`
- Unit test in sibling `*.test.tsx` file
- Added to `PreviewPage.tsx` with all meaningful states rendered

**Constraints:**
- No new npm dependencies unless explicitly justified (TabBar is native ARIA,
  not Radix Tabs)
- TypeScript strict mode
- Follow existing component patterns in `design/components/`
- `pnpm build` green, `pnpm test` green

### Work completed when

- [ ] All six components exist under `design/components/`
- [ ] Each has a sibling test file, all passing
- [ ] PreviewPage renders all six with representative states
- [ ] `pnpm build` and `pnpm test` green
- [ ] No new npm dependencies added (unless justified and lockfile updated)

### Update the plan

In `docs/workbench/wave-1-evidence-spine.md`, check off every box under
section 1C. Check off the "Renders in PreviewPage" and "Unit test" boxes.

### PR and merge

```bash
cd ../core-wb-primitives
git add workbench-ui/src/design/components/SplitPane/
git add workbench-ui/src/design/components/TabBar/
git add workbench-ui/src/design/components/MetadataTable/
git add workbench-ui/src/design/components/DigestBadge/
git add workbench-ui/src/design/components/Timestamp/
git add workbench-ui/src/design/components/SearchInput/
git add workbench-ui/src/preview/PreviewPage.tsx
git add docs/workbench/wave-1-evidence-spine.md
git commit -m "feat(workbench): six evidence primitives (Wave 1C)

SplitPane, TabBar, MetadataTable, DigestBadge, Timestamp, SearchInput.
All token-driven, keyboard-navigable, ARIA-accessible, dark theme,
motion-respectful. No new dependencies."
```

Push and open PR:
```bash
git push -u origin feat/wb-primitives
gh pr create --title "feat(workbench): six evidence primitives (Wave 1C)" \
  --body "$(cat <<'EOF'
## Summary
- Six shared design-system components for the evidence spine
- All built with existing design tokens, no new dependencies
- PreviewPage updated with all component states
- Part of Wave 1 (`docs/workbench/wave-1-evidence-spine.md`)

## Test plan
- [ ] `cd workbench-ui && pnpm test`
- [ ] `cd workbench-ui && pnpm build`
- [ ] Visual: open `/preview`, verify all six components render correctly
EOF
)"
```

**Merge before Brief 4 starts.** Brief 4 imports these components.

### Worktree cleanup

After merge:
```bash
cd /Users/kaizenpro/Projects/core
git worktree remove ../core-wb-primitives
git branch -d feat/wb-primitives
```

---

## Brief 3 — Mutation Doctrine Docs

**Agent:** GPT5.5-Thinking
**Scope:** Documentation only. No code changes.

### Worktree setup

```bash
cd /Users/kaizenpro/Projects/core
git fetch origin
git worktree add ../core-wb-mutation-docs origin/main -b feat/wb-mutation-docs
cd ../core-wb-mutation-docs
```

### Brief

Update the workbench planning docs to reconcile mutation doctrine with
reality. The current docs say "no accept/reject buttons" and "no mutation
in v1," but math proposal ratify/reject/defer already exists in
`workbench/api.py` (lines 112+) and the UI has a gated ratification
corridor in `RatificationCommandPanel.tsx`.

The honest rule is not "no mutation ever." It is: no mutation without an
admitted corridor, explicit preconditions, telemetry, and replay evidence.

**Read before writing:**
- `docs/workbench/wave-1-evidence-spine.md` — section 1F
- `docs/workbench/implementation-plan.md` — current mutation language
- `docs/workbench/acceptance-gates.md` — current forbidden/required lists
- `workbench/api.py` — existing ratify/reject/defer routes (lines 112+)
- `workbench-ui/src/app/proposals/RatificationCommandPanel.tsx` — existing
  UI with precondition gates

**Deliverables:**

1. Update `docs/workbench/implementation-plan.md`
   - Replace blanket "no mutation" language with the admitted corridor rule
   - Document existing math ratification as the first admitted corridor
   - Keep the list of what remains forbidden (corpus mutation, pack mutation,
     workflow dispatch, arbitrary file writes)
   - Add a section: "Mutation doctrine" defining the four requirements:
     (1) ADR-governed path, (2) visible preconditions, (3) auditable
     telemetry, (4) replay evidence before action

2. Update `docs/workbench/acceptance-gates.md`
   - W-029 gates: replace "Forbidden: accept button / reject button" with
     "Mutation only through admitted corridors (see Mutation doctrine)"
   - Keep the red flags section but reframe: the red flag is not "UI can
     accept proposals" — it is "UI can accept proposals WITHOUT admitted
     corridor, preconditions, telemetry, or replay evidence"
   - Update V1 release gate #8: "verify from UI copy and docs that no
     UNADMITTED mutation path exists" (not "no mutation path")

3. Check off section 1F in `docs/workbench/wave-1-evidence-spine.md`

**Constraints:**
- Do not change any code — docs only
- Do not weaken security boundaries — the list of forbidden things (corpus
  mutation, pack mutation, workflow dispatch, etc.) stays forbidden
- The correction is precise: math ratification IS admitted; everything else
  remains forbidden until a future ADR admits it
- Keep existing document structure; amend sections in place

### Work completed when

- [ ] `implementation-plan.md` has a Mutation doctrine section with the
      four-requirement rule
- [ ] `acceptance-gates.md` W-029 gates updated to match reality
- [ ] `acceptance-gates.md` red flags reframed around unadmitted mutation
- [ ] `wave-1-evidence-spine.md` section 1F boxes checked
- [ ] No code changes in the PR

### PR and merge

```bash
cd ../core-wb-mutation-docs
git add docs/workbench/implementation-plan.md
git add docs/workbench/acceptance-gates.md
git add docs/workbench/wave-1-evidence-spine.md
git commit -m "docs(workbench): reconcile mutation doctrine with admitted corridors (Wave 1F)

Replace blanket 'no mutation' language with the honest rule:
no mutation without admitted ADR corridor, visible preconditions,
auditable telemetry, and replay evidence.

Math ratification is the first admitted corridor. Corpus/pack/workflow
mutation remains forbidden."
```

Push and open PR:
```bash
git push -u origin feat/wb-mutation-docs
gh pr create --title "docs(workbench): reconcile mutation doctrine (Wave 1F)" \
  --body "$(cat <<'EOF'
## Summary
- Updates implementation-plan.md and acceptance-gates.md
- Replaces blanket "no mutation" with admitted corridor doctrine
- Documents math ratification as the first admitted example
- Docs only — no code changes

## Test plan
- [ ] Read the diff — verify forbidden list unchanged, only language corrected
EOF
)"
```

Can merge anytime — no code dependencies.

### Worktree cleanup

After merge:
```bash
cd /Users/kaizenpro/Projects/core
git worktree remove ../core-wb-mutation-docs
git branch -d feat/wb-mutation-docs
```

---

## Brief 4 — Evidence Context + Inspector + Command Registry

**Agent:** Claude (Opus 4.6)
**Scope:** React/TypeScript frontend only. No Python, no backend changes.
**Prerequisite:** Brief 2 merged to main.

### Worktree setup

```bash
cd /Users/kaizenpro/Projects/core
git fetch origin
git worktree add ../core-wb-evidence-ui origin/main -b feat/wb-evidence-ui
cd ../core-wb-evidence-ui
```

Verify Brief 2 is on main before starting:
```bash
ls workbench-ui/src/design/components/SplitPane/SplitPane.tsx || echo "STOP: Brief 2 not merged yet"
```

### Brief

Build the evidence spine's UI architecture — the shared context that makes
every route a projection of one evidence manifold, plus the two surfaces
that consume it (Inspector and Command Palette).

**Read before writing code:**
- `docs/workbench/wave-1-evidence-spine.md` — sections 1A, 1B
- `workbench-ui/src/app/Shell.tsx` — current shell layout (hardcodes
  collapsed inspector)
- `workbench-ui/src/app/RightInspector.tsx` — currently returns null
- `workbench-ui/src/design/components/primitives/CommandPalette.tsx` —
  currently hardcoded list
- `workbench-ui/src/app/LeftNav.tsx` — route list (for command registration)
- `workbench-ui/src/types/api.ts` — existing API types
- `workbench-ui/src/design/components/` — primitives from Brief 2

**Deliverables:**

1. `workbench-ui/src/app/evidenceContext.tsx`
   - `EvidenceSubject` union type:
     ```
     { kind: 'turn', turnId: number, data: TurnJournalEntry }
     | { kind: 'proposal', proposalId: string, data: ProposalDetail }
     | { kind: 'artifact', artifactId: string, data: ArtifactDetail }
     | { kind: 'eval_result', lane: string, data: EvalRunResult }
     | { kind: 'none' }
     ```
   - `EvidenceContext` React context with `subject`, `setSubject`,
     `clearSubject`
   - `EvidenceProvider` component wrapping the Shell
   - `useEvidenceSubject()` hook for consumers

2. Rewrite `workbench-ui/src/app/RightInspector.tsx`
   - Consumes `useEvidenceSubject()`
   - Collapsed by default (calm default). Toggle via `Cmd+I` or explicit
     "inspect" action
   - When open, renders the appropriate evidence projection based on
     `subject.kind`:
     - `turn`: surfaces, grounding, verdicts, trace hash (compact view)
     - `proposal`: state, source, replay evidence, suggested CLI
     - `artifact`: metadata, digest, content preview
     - `eval_result`: pass/fail, metrics, failure detail
     - `none`: empty state with hint text
   - Resizable width via SplitPane (from Brief 2)
   - Stays open across route transitions (state in context, not route)
   - Uses `MetadataTable`, `DigestBadge`, `Timestamp` from Brief 2

3. Rewrite `workbench-ui/src/app/Shell.tsx`
   - Remove hardcoded `collapsed={true}`
   - Wrap content in `EvidenceProvider`
   - Inspector panel controlled by evidence context + user toggle

4. Rewrite `workbench-ui/src/design/components/primitives/CommandPalette.tsx`
   - `CommandRegistry` — registration-based command system:
     - `useCommandRegistry()` hook returns `register(commands)` and
       `unregister(id)`
     - Each route registers its commands on mount, unregisters on unmount
     - Command shape: `{ id, label, section, shortcut?, action: () => void }`
   - Built-in commands: navigate to each route (Chat, Trace, Replay,
     Proposals, Evals, Runs, Packs, Vault, Audit, Settings)
   - Fuzzy search over command labels
   - Recent items section: last 10 evidence subjects visited (stored in
     localStorage)
   - `Cmd+K` opens, type-ahead filters, arrow keys navigate, `Enter`
     executes, `Esc` closes
   - Uses `SearchInput` from Brief 2

5. Global keyboard listener (in Shell or dedicated hook)
   - `Cmd+K` — command palette
   - `Cmd+I` — toggle inspector
   - `Cmd+1` through `Cmd+0` — navigate to routes 1-10
   - `?` — show keyboard shortcut overlay (simple modal listing shortcuts)
   - `Esc` — close topmost overlay (palette > inspector > shortcut help)
   - Do not capture when focus is in an input/textarea

6. `StatusFooter.tsx` enrichment
   - Add API round-trip latency indicator (measure from last query)
   - Add turn count from journal (if endpoint available — otherwise defer)
   - Add proposal queue count badge (from existing `/proposals` data)

7. Tests
   - Evidence context: set subject, read subject, clear subject, persists
     across simulated route change
   - Inspector: opens on Cmd+I, closes on Cmd+I, renders correct projection
     per subject kind, stays open across route change
   - Command palette: registers route commands, fuzzy filters, executes
     navigation
   - Keyboard: Cmd+K opens palette, Esc closes, Cmd+I toggles inspector

**Constraints:**
- No new npm dependencies
- TypeScript strict mode
- Do not modify backend or Python code
- `pnpm build` green, `pnpm test` green

### Work completed when

- [ ] Evidence context provider wraps the shell
- [ ] Inspector opens/closes with Cmd+I, shows contextual evidence
- [ ] Command palette has route-registered commands with fuzzy search
- [ ] Global keyboard shortcuts work (Cmd+K, Cmd+I, Cmd+1-0, ?, Esc)
- [ ] All tests pass, build passes

### Update the plan

In `docs/workbench/wave-1-evidence-spine.md`, check off all boxes under
sections 1A and 1B.

### PR and merge

```bash
cd ../core-wb-evidence-ui
git add workbench-ui/src/app/evidenceContext.tsx
git add workbench-ui/src/app/RightInspector.tsx
git add workbench-ui/src/app/Shell.tsx
git add workbench-ui/src/design/components/primitives/CommandPalette.tsx
git add workbench-ui/src/app/StatusFooter.tsx
# Add test files and any other changed files
git add docs/workbench/wave-1-evidence-spine.md
git commit -m "feat(workbench): evidence context + inspector + command registry (Wave 1A+1B)

Evidence context provider makes every route a projection of one
evidence manifold. RightInspector shows contextual evidence per
selected subject. CommandPalette is route-registered with fuzzy
search. Global keyboard shortcuts for power-user workflow."
```

Push and open PR:
```bash
git push -u origin feat/wb-evidence-ui
gh pr create --title "feat(workbench): evidence context + inspector + command registry (Wave 1A+1B)" \
  --body "$(cat <<'EOF'
## Summary
- Shared evidence-subject context across all routes
- RightInspector: contextual evidence drawer (Cmd+I toggle)
- CommandPalette: route-registered, fuzzy-searchable (Cmd+K)
- Global keyboard shortcuts (Cmd+1-0, ?, Esc)
- Part of Wave 1 evidence spine

## Test plan
- [ ] `cd workbench-ui && pnpm test`
- [ ] `cd workbench-ui && pnpm build`
- [ ] Manual: open workbench, Cmd+K opens palette, navigate to routes,
      Cmd+I opens inspector
EOF
)"
```

**Merge before Brief 5 starts.**

### Worktree cleanup

After merge:
```bash
cd /Users/kaizenpro/Projects/core
git worktree remove ../core-wb-evidence-ui
git branch -d feat/wb-evidence-ui
```

---

## Brief 5 — Trace Route

**Agent:** GPT5.5-Thinking
**Scope:** React/TypeScript frontend. Consumes the backend from Brief 1.
**Prerequisites:** Briefs 1, 2, and 4 all merged to main.

### Worktree setup

```bash
cd /Users/kaizenpro/Projects/core
git fetch origin
git worktree add ../core-wb-trace-route origin/main -b feat/wb-trace-route
cd ../core-wb-trace-route
```

Verify prerequisites:
```bash
ls workbench/journal.py || echo "STOP: Brief 1 not merged"
ls workbench-ui/src/design/components/SplitPane/SplitPane.tsx || echo "STOP: Brief 2 not merged"
ls workbench-ui/src/app/evidenceContext.tsx || echo "STOP: Brief 4 not merged"
```

### Brief

Build the Trace route — the canonical proof of CORE's surface-separation
contract and the deepest inspection surface in the workbench. This route
makes "the deeper you go, the more transparent it becomes" literally true.

**Read before writing code:**
- `docs/workbench/wave-1-evidence-spine.md` — section 1E (your spec)
- `docs/workbench/api-contract-v1.md` — line 231 (surface separation is
  sacred)
- `workbench-ui/src/app/evidenceContext.tsx` — evidence subject context
  (from Brief 4)
- `workbench-ui/src/api/client.ts` — existing API client patterns
- `workbench-ui/src/api/queries.ts` — existing React Query hooks
- `workbench-ui/src/design/components/` — all primitives (from Brief 2)
- `workbench-ui/src/app/chat/TraceDrawer.tsx` — existing chat trace drawer
  (reference, not to be replaced — the Trace route is the full-page version)

**Deliverables:**

1. TypeScript types in `workbench-ui/src/types/api.ts`
   - `TurnJournalEntry` interface (mirrors Python `TurnJournalEntry`)
   - `TurnJournalSummary` interface (mirrors Python `TurnJournalSummary`)

2. API client in `workbench-ui/src/api/client.ts`
   - `fetchTraceTurns(limit?: number, offset?: number): Promise<ApiResponse<{ items: TurnJournalSummary[] }>>`
   - `fetchTraceTurn(turnId: number): Promise<ApiResponse<TurnJournalEntry>>`

3. React Query hooks in `workbench-ui/src/api/queries.ts`
   - `useTraceTurns(limit?, offset?)` — queries `/trace/turns`
   - `useTraceTurn(turnId)` — queries `/trace/{turn_id}`, enabled only when
     turnId is defined

4. Replace `TraceRoutePlaceholder.tsx` with `workbench-ui/src/app/trace/TraceRoute.tsx`

   Layout: `SplitPane` (horizontal) — turn timeline left, evidence panel right.

   **Left pane — Turn Timeline:**
   - List of `TurnJournalSummary` items from `useTraceTurns()`
   - Each item shows: `Timestamp`, prompt excerpt (first line, truncated),
     `DigestBadge` (trace_hash, truncated to 12 chars)
   - Keyboard navigation: `j/k` or arrow keys to move, `Enter` to select
   - Selected turn gets highlight border via `--color-border-accent`
   - `SearchInput` at top: filters by prompt text or trace_hash prefix
   - Empty state: "No turns recorded yet. Use Chat to create evidence."

   **Right pane — Trace Evidence Panel:**
   - `TabBar` with five tabs:
     - **Surfaces** — all three surfaces displayed with explicit labels:
       - `surface` labeled "User Surface (response)"
       - `articulation_surface` labeled "Articulation Surface (realizer)"
       - `walk_surface` labeled "Walk Surface (telemetry/evidence)"
       - Each in its own bordered card with monospace font for content
       - THIS IS the canonical proof of api-contract-v1.md surface separation
     - **Grounding** — `MetadataTable` showing `grounding_source` (with
       `GroundingSourceBadge`), `epistemic_state` (with
       `EpistemicStateBadge`), `normative_clearance` (with
       `NormativeClearanceBadge`)
     - **Verdicts** — `MetadataTable` showing identity/safety/ethics verdicts
       with outcome badges, refusal_emitted, hedge_injected
     - **Metadata** — `MetadataTable` showing turn_id, turn_cost_ms,
       checkpoint_emitted, proposal_candidates (count + IDs),
       journal_digest (`DigestBadge`)
     - **Raw** — `StableJsonViewer` showing the full `TurnJournalEntry` JSON,
       collapsed by default (operator must explicitly expand — calm default,
       infinite depth)

5. Evidence context integration
   - Selecting a turn in the timeline calls `setSubject({ kind: 'turn',
     turnId, data: fullEntry })`
   - This makes the RightInspector (from Brief 4) show the same turn from
     its compact angle
   - Deselecting (pressing `Esc` with no overlay open) calls
     `clearSubject()`

6. Update `workbench-ui/src/app/App.tsx`
   - Replace the placeholder import with the real `TraceRoute` component

7. Tests in `workbench-ui/src/app/trace/TraceRoute.test.tsx`
   - Empty state renders when no turns exist
   - Turn list renders journal summaries
   - Selecting a turn shows evidence panel with all five tabs
   - Surface tab shows all three surfaces with correct labels
   - Surface labels never say "response" for walk_surface
   - Raw tab is collapsed by default
   - Keyboard: j/k navigates, Enter selects, Esc deselects
   - Evidence subject context is updated on selection

**Design rules:**
- Walk surface is ALWAYS labeled "telemetry/evidence" — never confused with
  user surface
- Trace hash always visible and copyable (replay before persuasion)
- Raw JSON behind explicit expand (calm default, infinite depth)
- No decorative animation, no "thinking" indicators
- Failures/refusals more visually prominent than successes (audit-native)

**Constraints:**
- No new npm dependencies
- TypeScript strict mode
- Do not modify Python backend
- `pnpm build` green, `pnpm test` green
- Existing tests (chat, proposals, evals, replay) must still pass

### Work completed when

- [ ] Trace route replaces the placeholder
- [ ] Turn timeline shows real journal entries with search/filter
- [ ] Evidence panel shows all five tabs with correct content
- [ ] Three surfaces are displayed separately with explicit labels
- [ ] Walk surface labeled "telemetry/evidence"
- [ ] Raw JSON collapsed by default
- [ ] Evidence context updated on turn selection
- [ ] All tests pass, build passes

### Update the plan

In `docs/workbench/wave-1-evidence-spine.md`, check off all boxes under
section 1E. If all sections 1A-1F are now checked, add a completion note
at the top: "Wave 1 complete — [date]".

### PR and merge

```bash
cd ../core-wb-trace-route
git add workbench-ui/src/app/trace/
git add workbench-ui/src/types/api.ts
git add workbench-ui/src/api/client.ts
git add workbench-ui/src/api/queries.ts
git add workbench-ui/src/app/App.tsx
git add docs/workbench/wave-1-evidence-spine.md
git commit -m "feat(workbench): trace route — evidence spine projection (Wave 1E)

Replaces TraceRoutePlaceholder with real Trace route over the turn
evidence journal. Five-tab evidence panel: Surfaces (three surfaces
explicitly separated and labeled per api-contract-v1.md), Grounding,
Verdicts, Metadata, Raw JSON.

Integrates with evidence context — selecting a turn updates the
RightInspector. Walk surface labeled as telemetry/evidence."
```

Push and open PR:
```bash
git push -u origin feat/wb-trace-route
gh pr create --title "feat(workbench): trace route (Wave 1E)" \
  --body "$(cat <<'EOF'
## Summary
- Real Trace route replacing placeholder
- Turn timeline + five-tab evidence panel
- Surface separation contract visually proven
- Evidence context integration with RightInspector
- Completes Wave 1 evidence spine

## Test plan
- [ ] `cd workbench-ui && pnpm test`
- [ ] `cd workbench-ui && pnpm build`
- [ ] Manual: start API (`core workbench api`), start frontend (`pnpm dev`),
      chat a few turns, navigate to Trace, verify turns appear, select one,
      verify all five tabs, verify inspector shows the same turn
- [ ] Verify walk_surface is labeled "telemetry/evidence" not "response"
EOF
)"
```

### Worktree cleanup

After merge:
```bash
cd /Users/kaizenpro/Projects/core
git worktree remove ../core-wb-trace-route
git branch -d feat/wb-trace-route
```

---

## Summary Card

| Brief | Agent | Branch | Wave | Depends on | Merge order |
|---|---|---|---|---|---|
| 1 — Backend Journal | GPT5.5 | `feat/wb-journal` | A | — | 2nd (or 1st) |
| 2 — Evidence Primitives | Claude | `feat/wb-primitives` | A | — | 1st (or 2nd) |
| 3 — Mutation Docs | GPT5.5 | `feat/wb-mutation-docs` | A | — | anytime |
| 4 — Evidence UI | Claude | `feat/wb-evidence-ui` | B | Brief 2 | 3rd |
| 5 — Trace Route | GPT5.5 | `feat/wb-trace-route` | C | Briefs 1+2+4 | 4th (last) |

**Wave A dispatch:** Briefs 1, 2, 3 — all start now, in parallel.
**Wave B dispatch:** Brief 4 — starts after Brief 2 merges.
**Wave C dispatch:** Brief 5 — starts after Briefs 1 and 4 merge.
**Wave 1 complete:** When Brief 5 merges.
