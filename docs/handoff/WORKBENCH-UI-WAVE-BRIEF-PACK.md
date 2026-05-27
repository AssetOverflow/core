# Workbench UI Wave — Brief Pack (W1..W4)

**Goal:** Stand up the workbench frontend so the math teaching corridor
is operable by one operator at human-realistic throughput. Implements
the wave shape committed in
`docs/handoff/WORKBENCH-UI-WAVE-SCOPING.md` under the trust boundary
pinned by ADR-0173.

**Blocker.** Every brief here depends on **ADR-0173 W0** landing first
(PR #394). Do not dispatch W1..W4 until that PR merges.

**Bundling rule.** [[feedback-batch-during-research]]. This is
implementation mode, not research — one PR per wave (W4 splits into
two). No spec churn in the implementation PRs; if doctrine needs to
move, it moves in its own ADR PR first.

**Production-line discipline.** [[feedback-production-line-pattern]].
Dispatch lines are copy-paste-ready; each brief opens with a worktree
`add` line; brief pack is the single source of truth.

---

## Dependency DAG

```
ADR-0173 (PR #394)
  │
  ▼
W1 — Scaffold (one frontend PR; blocks W2/W3/W4)
  │
  ├──────────┬──────────┐
  ▼          ▼          ▼
 W2         W4a        W4b
(read)    (replay)   (eval)
  │
  ▼
W3 (ratification corridor — needs W2's queue + detail)
```

**Parallel-safe pairs:** {W2 ‖ W4a ‖ W4b} once W1 lands. W3 is
sequential after W2 because the RatificationCommandPanel is wired to
the ProposalDetailPanel that W2 ships.

**Recommended sequence (single-operator):** W1 → W2 → W3 → W4a → W4b.
**Recommended sequence (parallel, 2+ operators):**
W1 → (W2 ‖ W4a ‖ W4b) → W3.

---

## Operator profiles

Per [[feedback-parallel-dispatch-pattern]]:

| Wave | Profile | Why |
|---|---|---|
| W1 | **Codex** (mechanical) | Vite/TS/Tailwind/shadcn scaffold from ADR-0162 spec; deterministic toolchain bootstrap; minimal judgment. |
| W2 | **Sonnet** (tight-scope) | Frontend work over a fully-specified API contract; TanStack Query + Zustand; semantic color mapping from ADR-0162 ratified enums. |
| W3 | **Opus** (load-bearing wrong=0 surface) | Same profile as CC-2; ratification dispatch with hazard-pin discipline, partition tests, case 0050 pin. |
| W4a | **Sonnet** (tight-scope) | Replay surfaces over existing API routes. |
| W4b | **Sonnet** (tight-scope) | Eval surfaces over existing API routes. |

---

## Brief W1 — Frontend Scaffold

**Operator profile:** Codex (mechanical; Vite/TS/Tailwind bootstrap)
**Branch:** `feat/workbench-ui-w1-scaffold`
**Base:** `origin/main` (post-ADR-0173 merge)
**Style:** Frontend bootstrap. No app routes yet. Tokens + shell + palette + status footer only.

### Dispatch

```bash
git fetch origin main && \
  git worktree add /tmp/wt-wb-ui-w1 origin/main && \
  cd /tmp/wt-wb-ui-w1 && \
  git checkout -b feat/workbench-ui-w1-scaffold
```

### Reads required FIRST

- `docs/decisions/ADR-0160-core-workbench-v1.md` §"Architecture choice" + §"Trust boundary"
- `docs/decisions/ADR-0162-workbench-design-system.md` §"Token namespace", §"Typography", §"Color semantics", §"Motion", §"Keyboard contract", §"Layout shell", §"Component map — v1 must-ship", §"The no-go list", §"Implementation plan — Branch 1"
- `docs/decisions/ADR-0173-workbench-ratification-trust-boundary.md` §"Keyboard contract", §"What the workbench MUST NOT do"
- `docs/handoff/WORKBENCH-UI-WAVE-SCOPING.md` §"Guardrails"

### Outcome

`workbench-ui/` directory at repo root, fully bootstrapped per
ADR-0162 §"Implementation plan — Branch 1":

1. **`workbench-ui/package.json`** — pinned deps:
   - React 18.x, ReactDOM 18.x
   - Vite 5.x
   - TypeScript 5.x
   - Tailwind 3.x
   - shadcn-style primitives (Radix UI under shadcn)
   - TanStack Query 5.x
   - Zustand 4.x (state)
   - `lucide-react` for icons (bundled, no CDN)
2. **`workbench-ui/vite.config.ts`** — dev server on `127.0.0.1`, no
   network proxies to remote hosts, build output to `dist/`.
3. **`workbench-ui/tsconfig.json`** — strict TS.
4. **`workbench-ui/tailwind.config.js`** + **`postcss.config.js`**.
5. **`workbench-ui/src/design/tokens/tokens.css`** — every token
   from ADR-0162 §1–§4 (color, typography, motion, spacing).
6. **`workbench-ui/src/design/badges/`** — four badge primitives:
   - `EpistemicStateBadge` (15 values from `core/epistemic_state.py`)
   - `NormativeClearanceBadge` (4 values)
   - `ReviewStateBadge` (4 values from `teaching/proposals.py`)
   - `GroundingSourceBadge` (6 values)
   Each binds color + glyph + text label per ADR-0162 §3. **No color-only encoding.**
7. **`workbench-ui/src/shell/`** —
   - `WorkbenchShell.tsx` (the outer layout)
   - `TopBar.tsx`
   - `LeftNav.tsx`
   - `StatusFooter.tsx`
   - `CommandPalette.tsx` (focusable via `:` per ADR-0173)
8. **`workbench-ui/src/keyboard/`** —
   - `KeyboardHelpOverlay.tsx` populated from ADR-0173 §"Keyboard contract"
   - global `useKeyboard()` hook
   - `?` opens the help overlay
   - `Esc` dismisses
   - **No `Cmd`/`Ctrl` chords** (ADR-0173 constraint)
9. **`workbench-ui/src/api/client.ts`** — fetch wrapper for the
   existing backend (`http://127.0.0.1:<port>`); typed against
   `workbench/schemas.py` shapes via hand-written TS types in
   `src/api/types.ts`.
10. **`workbench-ui/dist/`** — added to **root `.gitignore`**.
11. **CI job** — `.github/workflows/workbench-ui-build.yml`:
    - triggers on PR touching `workbench-ui/**`
    - runs `npm ci && npm run build`
    - **does not commit `dist/`**
    - fails the PR if build fails

### Hard requirements

- **Tokens snapshot test.** A snapshot test pins the computed token
  values from `tokens.css` so future PRs cannot drift them silently.
- **Fonts bundled locally** per ADR-0173 Q4 — no CDN font fetch, no
  `@import url(...google...)`. License compliance is W1's
  responsibility.
- **Icons bundled locally** — `lucide-react` is installed as a
  dependency; no remote icon fetches.
- **No app routes yet.** W1 ships the shell; `/proposals`,
  `/evals`, `/trace` routes are W2/W3/W4's job.
- **Backend binds 127.0.0.1.** UI verified to refuse cross-origin
  requests; CORS configured restrictively in `workbench/server.py`
  if not already (read current state first; do not relax).
- **Keyboard help overlay populated from ADR-0173.** Verbatim
  bindings table.
- **Accessibility:** no icon-only buttons without `aria-label`; all
  badges carry text + shape, not color alone (ADR-0162 no-go list).
- **No-go list cross-check.** Reviewer must verify: no chat-clone
  bubbles, no "AI thinking" affordances, no glassmorphism, no
  purple-neon-cyberpunk, no graph-builder canvas, no dashboard
  splash metrics.

### Tests

- `workbench-ui/src/**/__tests__/*.test.tsx` using Vitest + React
  Testing Library
- `shell.test.tsx` — WorkbenchShell renders with TopBar, LeftNav, StatusFooter
- `command_palette.test.tsx` — `:` focuses palette, `Esc` dismisses
- `keyboard_help.test.tsx` — `?` opens overlay with ADR-0173 bindings
- `badges.test.tsx` — all four badge primitives render correct
  color + glyph + label for every enum value
- `tokens.snapshot.test.ts` — pins computed token bytes

### Deliverables

- `workbench-ui/` directory complete per outcome list
- root `.gitignore` updated (one line: `workbench-ui/dist/`)
- `.github/workflows/workbench-ui-build.yml`
- Tests green; CI workbench-ui-build job green
- No backend changes
- No changes to `core/`, `chat/`, `teaching/`, `field/`,
  `generate/`, `algebra/`, `language_packs/`

### Forbidden

- Adding app routes (W2/W3/W4 territory)
- Adding ratification UI (W3 territory)
- Adding any ProposalQueue/Card/Detail components (W2 territory)
- Adding any TraceDrawer/Replay/Eval components (W4 territory)
- Touching backend code (`workbench/api.py`, `workbench/readers.py`, etc.)
- Committing `dist/`
- Remote CDN dependencies (fonts, icons, runtime)
- `Cmd`/`Ctrl` keyboard chords
- Color-only state encoding
- Auto-dismiss toasts for audit events

---

## Brief W2 — Read Surfaces (Proposal Queue)

**Operator profile:** Sonnet (tight-scope frontend over fully-specified API)
**Branch:** `feat/workbench-ui-w2-proposal-queue`
**Base:** `origin/main` (post-W1 merge)
**Style:** Frontend only. Read-only against existing routes.

### Dispatch

```bash
git fetch origin main && \
  git worktree add /tmp/wt-wb-ui-w2 origin/main && \
  cd /tmp/wt-wb-ui-w2 && \
  git checkout -b feat/workbench-ui-w2-proposal-queue
```

### Reads required FIRST

- `workbench/api.py` — routes `/proposals`, `/proposals/{id}`,
  `/math-proposals`, `/math-proposals/{id}` (exact payload shapes)
- `workbench/schemas.py` — `ProposalSummary`, `ProposalDetail`,
  `MathProposalSummary`, `MathProposalDetail`, `MathReasoningStep`
- `docs/decisions/ADR-0162-workbench-design-system.md` §"Component map",
  §"StableJsonViewer", §"Empty/error/loading state contract"
- `docs/decisions/ADR-0173-workbench-ratification-trust-boundary.md`
  §"Keyboard contract" (queue + detail bindings)
- `docs/decisions/ADR-0167-audit-as-teaching-evidence.md` §"Partition guarantees"

### Outcome

Six components + two routes + two stores.

1. **`src/proposals/ProposalQueue.tsx`** — paginated list of
   pending proposals. Renders math + cognition in separate tabs
   (partition discipline). Default sort: oldest pending first.
   Filter chips: state, source kind, replay status.
2. **`src/proposals/ProposalCard.tsx`** — one-row representation:
   `proposal_id` (truncated, `CopyableHash`), `EpistemicStateBadge`,
   `ReviewStateBadge`, `age_proposals`, `replay_equivalent` icon,
   `handler_name` (if math).
3. **`src/proposals/ProposalDetailPanel.tsx`** — full detail view
   with `StableJsonViewer` over `evidence`, `replay_evidence`,
   `proposed_chain` / `proposed_change_payload`, and
   `reasoning_trace_steps` rendered as a step list (not a graph —
   ADR-0162 no graph-builder).
4. **`src/json/StableJsonViewer.tsx`** — canonical JSON renderer;
   sorted keys; no re-ordering; no syntax-highlight that mutates
   bytes; copy-to-clipboard per top-level node.
5. **`src/json/CopyableHash.tsx`** — truncated SHA with full-on-hover
   + copy button.
6. **`src/json/ArtifactLink.tsx`** — typed link to
   `/artifacts/{id}` route (lazy-loads the artifact).
7. **`src/routes/proposals.tsx`** — `/proposals` (cognition) +
   `/math-proposals` (math) routes; URL state binds to selected
   proposal id.
8. **`src/state/proposals.ts`** — Zustand store: queue cache,
   selected id, filter chips. TanStack Query owns the fetch.

### Keyboard wires (per ADR-0173)

- `g p` → navigate to `/proposals` (or `/math-proposals` based on
  last-viewed tab)
- `j` / `↓` → focus next proposal in queue
- `k` / `↑` → focus previous
- `Enter` → open detail panel for focused proposal
- `Esc` → close detail, return to queue
- `/` → focus filter input

### Hard requirements

- **Partition discipline.** Cognition and math queues are separate
  routes, separate Zustand slices, separate component trees.
  Math `ProposalCard` cannot render a cognition payload and vice
  versa. Verified by component test.
- **`StableJsonViewer` does not alter bytes.** A round-trip
  (`json.stringify(parsed)`) of the rendered payload equals the
  fetched payload byte-for-byte (modulo whitespace which is rendered
  but not stored).
- **No ratification UI.** No `r` keybind. No "ratify" button. No
  "accept" or "reject" affordance. That is W3's surface.
- **Empty/error/loading per ADR-0162 §6.** Empty state names what's
  missing; error state names the failure; loading state is a
  skeleton, not a spinner-soup splash.
- **Replay-state visualization.** `replay_equivalent: true|false|null`
  renders three distinct states (passed / failed / not-yet-replayed)
  — not collapsed to a two-state truthy/falsy icon. Per scoping
  brief pain point #6.
- **`suggested_ratify_cli` rendered (read-only).** Operator can
  copy via `y` keybind even though `r` (ratify) is not yet wired.
  This unblocks audit-fallback workflows during W2 before W3 ships.

### Tests

- `src/proposals/__tests__/queue.test.tsx` — renders 0, 1, many
  proposals; sort/filter behavior
- `src/proposals/__tests__/card.test.tsx` — one card per state
  permutation
- `src/proposals/__tests__/detail.test.tsx` — full detail render;
  `StableJsonViewer` byte-stability
- `src/proposals/__tests__/partition.test.tsx` — math card refuses
  cognition payload; vice versa
- `src/proposals/__tests__/keyboard.test.tsx` — j/k/Enter/Esc/`/`
  behavior per ADR-0173 contract
- `src/proposals/__tests__/replay_state.test.tsx` — three distinct
  states render distinctly (passed / failed / not-yet-replayed)
- `src/json/__tests__/stable_json.test.tsx` — round-trip
  byte-equality on a sample `MathProposalDetail` payload
- **e2e** — `e2e/proposal_queue.spec.ts` — Playwright; start
  backend with fixture proposals, open UI, verify the queue
  populates and the detail panel renders for one math + one
  cognition proposal

### Deliverables

- Components 1–8 above
- Routes + store wired
- Tests + e2e green
- Workbench backend untouched (read-only against existing routes)

### Forbidden

- Adding ratification UI (W3)
- Adding trace / replay / eval surfaces (W4)
- Backend route changes
- Mutating any existing component from W1
- Mixing cognition and math proposals in one queue/component

---

## Brief W3 — Ratification Corridor (the throughput multiplier)

**Operator profile:** Opus (load-bearing wrong=0 surface; ratification handler discipline; mirror CC-2 rigor)
**Branch:** `feat/workbench-ui-w3-ratification-corridor`
**Base:** `origin/main` (post-W2 merge, **and** post PR #393 / CC-2 merge for CompositionClaim handler availability)
**Style:** Frontend + thin backend dispatch test. Load-bearing.

### Dispatch

```bash
git fetch origin main && \
  git worktree add /tmp/wt-wb-ui-w3 origin/main && \
  cd /tmp/wt-wb-ui-w3 && \
  git checkout -b feat/workbench-ui-w3-ratification-corridor
```

### Reads required FIRST

- `docs/decisions/ADR-0173-workbench-ratification-trust-boundary.md` (entire ADR)
- `docs/decisions/ADR-0167-audit-as-teaching-evidence.md` §"Partition guarantees"
- `docs/decisions/ADR-0168-frameclaim-ratification.md` §"Acceptance gates"
- `docs/decisions/ADR-0169-compositionclaim-ratification.md` §"Acceptance gates"
- `teaching/math_lexical_ratification.py` — `apply_lexical_claim()`, exception types
- `teaching/math_frame_ratification.py` — `apply_frame_claim()`, exception types
- `teaching/math_composition_ratification.py` — `apply_composition_claim()`, exception types
- `workbench/api.py` — `POST /math-proposals/{id}/ratify` route + `MathRatifyResult` shape
- `tests/test_math_frame_ratification.py::test_case_0050_hazard_pin` (the template)
- `tests/test_math_composition_ratification.py::test_case_0050_hazard_pin` (same template)

### Outcome

One component, one keyboard surface, one e2e per handler.

1. **`src/proposals/RatificationCommandPanel.tsx`** — bottom-sheet
   panel attached to the focused proposal in `ProposalDetailPanel`.
   - Visible only when a proposal is focused AND in `pending` state
     AND `replay_equivalent == true` AND `handler_name` is in the
     admitted set (Lexical / Frame / Composition).
   - Disabled with a named status message when any precondition
     fails (per ADR-0173 §"Keyboard contract" — no silent failures).
   - Renders: handler name, claim signature digest, target JSONL
     artifact path, "ratify (r)" / "reject with note (x)" / "defer
     (d)" / "copy CLI (y)" affordances.
2. **`src/api/ratify.ts`** — typed wrapper around
   `POST /math-proposals/{id}/ratify`. On 200, returns
   `MathRatifyResult`. On 4xx, surfaces the structured error
   verbatim into the status footer (do not translate exception
   messages — operator audit fallback depends on raw text).
3. **`src/state/ratify.ts`** — Zustand slice for post-ratify
   auto-advance (focus next pending after a successful ratify).
4. **Operator-action telemetry wire** in `workbench/api.py` — emit
   `operator_ratify` / `operator_reject` / `operator_defer` events
   to the existing `chat/telemetry.py` sink per ADR-0173 Q3. Event
   schema:
   ```json
   {"event": "operator_ratify", "proposal_id": "...", "handler": "...", "outcome": "applied|rejected_precondition", "ratifier_kind": "workbench", ...}
   ```
5. **Ratification record extension** — `ratifier_kind: "workbench"`
   is written to the JSONL artifact's provenance record. **Audit
   forensic field only**; not a permission gate. Verified by test
   that strips `ratifier_kind` and confirms replay still works
   (per ADR-0161 §5 "Replay invariants").

### Keyboard wires (per ADR-0173)

- `r` → ratify focused proposal (only when preconditions hold;
  otherwise no-op + status footer message)
- `x` → reject with note (opens a single-line text input; `Enter`
  commits, `Esc` cancels)
- `d` → defer (proposal stays `pending`; operator-defer telemetry emits)
- `y` → copy `suggested_ratify_cli` to clipboard
- Post-ratify: focus auto-advances to next `pending` +
  `replay_equivalent==true` proposal

### Hard requirements

These mirror ADR-0173 §"Acceptance gates for W1..W4 → W3" verbatim.

- **Same Python entrypoint.** Every `r` keypress executes the same
  `apply_*_claim()` function as the corresponding CLI invocation.
  Verified by parametrized test (one per handler) that:
  1. constructs a fixture proposal
  2. ratifies via the UI (HTTP POST through the API)
  3. ratifies an equivalent fixture via the CLI
  4. diffs the resulting JSONL artifact rows
  5. asserts byte-equal **except for `ratifier_kind`**
- **Case 0050 hazard pin holds end-to-end.** Ratifying any admitted
  handler via the UI must not cause case 0050 to admit. Verified
  by e2e: ratify a synthetic CompositionClaim under each safe
  category, then run `core eval gsm8k_math` (via the existing
  `/evals/run` route) and assert case 0050 stays refused.
- **Exception surface verbatim.** `AlreadyRatified`,
  `WrongClaimSubType`, `WrongCompositionCategory`,
  `EvidenceTampered`, replay-regression errors — all surface
  verbatim into the status footer. No translation, no smoothing.
- **`r` is a no-op** on any proposal not in `pending` AND
  `replay_equivalent == true` AND admitted handler. The no-op
  emits a status-footer message naming the failing precondition.
- **Partition.** Math ratifications cannot mutate cognition
  artifacts and vice versa. Verified by test that attempts a
  cross-domain ratification and asserts the API returns 400 with a
  partition-violation reason.
- **No auto-ratify.** Replay-passed proposals remain `pending` until
  an explicit `r` keypress on a focused, expanded detail. Verified
  by test: poll the queue with replay-passed fixtures; assert no
  state transitions until a keypress arrives.
- **No batch ratification.** Each `r` press ratifies exactly one
  focused proposal. Multi-select UI is not introduced.
- **No CORS relaxation.** Backend continues to bind 127.0.0.1
  only; cross-origin requests refused. Verified by test.
- **Operator-action telemetry redact-by-default.** Events do not
  include surface text or token content. Verified by test:
  emit, parse, assert no proposal evidence text leaks.

### Tests

Mirror `tests/test_math_composition_ratification.py` rigor.

- `tests/test_workbench_ratify_lexical.py` — end-to-end UI ratify
  → JSONL artifact byte-diff vs CLI ratify
- `tests/test_workbench_ratify_frame.py` — same shape for FrameClaim
- `tests/test_workbench_ratify_composition.py` — same shape for CompositionClaim
- `tests/test_workbench_ratify_case_0050_hazard_pin.py` — mandatory
- `tests/test_workbench_ratify_partition.py` — math/cognition isolation
- `tests/test_workbench_ratify_no_auto.py` — auto-ratify forbidden
- `tests/test_workbench_ratify_exception_surface.py` — exceptions
  surface verbatim
- `tests/test_workbench_operator_telemetry.py` — events emit; no
  content leak
- `tests/test_workbench_ratify_idempotent.py` — duplicate ratify
  via UI returns `AlreadyRatified`
- `src/proposals/__tests__/ratification_panel.test.tsx` — frontend
  unit tests for visibility, keyboard, no-op behavior
- `e2e/ratification_corridor.spec.ts` — Playwright end-to-end for
  all three handlers

### Deliverables

- `RatificationCommandPanel.tsx`, `src/api/ratify.ts`,
  `src/state/ratify.ts`
- Backend: operator-action telemetry wire in `workbench/api.py`
- `workbench/readers.py` updates if needed for `ratifier_kind`
  surfacing (read current state first; minimal diff)
- All tests above, green
- `core test --suite teaching -q` green
- `core test --suite runtime -q` green
- `core eval gsm8k_math` green
- Case 0050 remains refused

### Forbidden

- Admitting a handler not in {Lexical, Frame, Composition}
- Adding auto-ratify of any flavor
- Adding batch / multi-select ratification
- Bypassing handler preconditions in any code path
- Adding remote operator auth, login, or token-bearer
- Relaxing CORS on the backend
- Adding `Cmd`/`Ctrl` keyboard chords
- Mutating `engine_state/*` outside the existing checkpoint path
- Treating `ratifier_kind` as a permission gate
- Adding a parallel telemetry log

---

## Brief W4a — Replay Surfaces

**Operator profile:** Sonnet (tight-scope frontend over existing routes)
**Branch:** `feat/workbench-ui-w4a-replay-surfaces`
**Base:** `origin/main` (post-W1; parallel-safe with W2/W3/W4b)
**Style:** Frontend only. Read-only.

### Dispatch

```bash
git fetch origin main && \
  git worktree add /tmp/wt-wb-ui-w4a origin/main && \
  cd /tmp/wt-wb-ui-w4a && \
  git checkout -b feat/workbench-ui-w4a-replay-surfaces
```

### Reads required FIRST

- `workbench/api.py` — `/trace/...`, `/replay/...` routes
- `workbench/schemas.py` — `ReplayComparison`, `ReplayDivergence`,
  `ReplayDivergenceSeverity`, `ReplayStatus`
- `docs/decisions/ADR-0160-core-workbench-v1.md` §"Trace Drawer",
  §"Replay Theater"
- `docs/decisions/ADR-0162-workbench-design-system.md` §"Component map"

### Outcome

Four components + one route.

1. **`src/trace/TraceDrawer.tsx`** — slide-in drawer showing the
   trace for a focused turn / proposal / ratification. Renders
   trace hash + step list (not graph). Opens via `g t` keybind.
2. **`src/replay/ReplayTheater.tsx`** — full-width panel hosting
   replay comparison + diff.
3. **`src/replay/ReplayComparisonPanel.tsx`** — side-by-side
   original-vs-replay hash + equivalent boolean + divergence count.
4. **`src/replay/ReplayDiffViewer.tsx`** — divergence list with
   severity coloring (info / warning / failure per ADR-0162); uses
   `StableJsonDiffViewer` from new component below.
5. **`src/json/StableJsonDiffViewer.tsx`** — canonical JSON diff;
   structural-aware (key/value/array-index), not line-based.
6. **`src/routes/trace.tsx`** — `/trace/:id` route.
7. **`src/routes/replay.tsx`** — `/replay/:id` route.

### Hard requirements

- **Read-only.** No replay-mutation UI. No "re-run replay" button
  in v1 (the backend route is read; replay is run server-side by
  separate mechanisms).
- **Diff is structural.** `StableJsonDiffViewer` operates on parsed
  JSON, not text lines. Byte-equal payloads produce zero
  divergences regardless of formatting.
- **Severity rendering.** info / warning / failure render
  distinctly without color-only encoding (icon + text + color).

### Tests

- `src/trace/__tests__/trace_drawer.test.tsx`
- `src/replay/__tests__/replay_theater.test.tsx`
- `src/replay/__tests__/replay_diff.test.tsx`
- `src/json/__tests__/stable_json_diff.test.tsx` — round-trip;
  byte-equal payloads → zero divergences
- `e2e/replay_theater.spec.ts`

### Forbidden

- Adding replay-mutation routes or buttons
- Line-based diff (must be structural)
- Color-only severity encoding

---

## Brief W4b — Eval Surfaces

**Operator profile:** Sonnet (tight-scope frontend over existing routes)
**Branch:** `feat/workbench-ui-w4b-eval-surfaces`
**Base:** `origin/main` (post-W1; parallel-safe with W2/W3/W4a)
**Style:** Frontend only. Drives existing read-only eval routes.

### Dispatch

```bash
git fetch origin main && \
  git worktree add /tmp/wt-wb-ui-w4b origin/main && \
  cd /tmp/wt-wb-ui-w4b && \
  git checkout -b feat/workbench-ui-w4b-eval-surfaces
```

### Reads required FIRST

- `workbench/api.py` — `/evals`, `/evals/{id}`, `POST /evals/run` routes
- `workbench/schemas.py` — `EvalLaneSummary`, `EvalRunResult`
- `docs/decisions/ADR-0160-core-workbench-v1.md` §"Eval Center"
- `docs/decisions/ADR-0166-measurement-capability-sequencing.md`
  (do **not** introduce new eval lanes)

### Outcome

Three components + one route.

1. **`src/evals/EvalCenter.tsx`** — top-level eval page.
2. **`src/evals/EvalLaneList.tsx`** — list of available lanes from
   `GET /evals`. Each row: lane name, latest run status, version,
   read-only badge, description. Clicking a row opens detail.
3. **`src/evals/EvalFailureViewer.tsx`** — for a failed eval run,
   list failing cases with their `MathReaderRefusalEvidence` (or
   cognition-equivalent) + `ArtifactLink` to the run JSON.
4. **`src/routes/evals.tsx`** — `/evals` route.

### Hard requirements

- **No new eval lanes.** ADR-0166 holds. The UI runs existing
  lanes only.
- **`POST /evals/run` is the only mutation surface.** It is
  read-only in effect (runs an eval; does not mutate corpus/packs).
  Other than that, every interaction is a GET.
- **Failure surfacing tied to evidence.** A failing case must link
  to the audit row that produced it (via `ArtifactLink`).
- **No vanity dashboard splash.** ADR-0162 no-go list:
  no "total turns" / "active sessions" / pulsing-orb metrics on
  the eval landing page.

### Tests

- `src/evals/__tests__/eval_center.test.tsx`
- `src/evals/__tests__/lane_list.test.tsx`
- `src/evals/__tests__/failure_viewer.test.tsx`
- `e2e/eval_center.spec.ts` — list lanes, open one, run via the
  read-only route, view results

### Forbidden

- Introducing new eval lanes (ADR-0166)
- Adding splash metrics / "AI cognition theater" panels
- Mutating corpus/packs through the eval surface

---

## Anti-regression invariants (all four briefs)

- `wrong == 0` on `core eval gsm8k_math` — preserved
- ADR-0166 — no new eval lanes
- ADR-0057 replay-equivalence — inherited
- ADR-0167 partition — math/cognition isolation in UI as on server
- Pinned-lane SHAs — should not require updates
- `engine_state/*` — never committed
- Case 0050 hazard — pinned in W3's test suite (mandatory)
- Backend bound to 127.0.0.1 — never relaxed
- No remote runtime dependencies — fonts, icons, telemetry all local

---

## Memory pointers

- [[feedback-batch-during-research]] — implementation mode; one PR per wave
- [[feedback-no-self-dispatch-of-subagents]] — Shay dispatches operators
- [[feedback-production-line-pattern]] — this brief pack pattern
- [[feedback-parallel-dispatch-pattern]] — operator profile mapping
- [[feedback-parallel-agent-worktrees]] — fresh worktree per brief
- [[feedback-wrong-zero-hazard-case-0050]] — W3 mandatory pin
- [[feedback-cleanup-as-you-find]] — apply if W1 finds dead workbench backend stubs
- [[user-circumstances]] — operators on library wifi; local-first matters
- [[milestone-adr-0172-tier1-2026-05-27]] — context for throughput-vs-capability framing
- [[adr-0167-audit-as-evidence-wave]] — parent corridor

---

## What ships when all PRs land

- **W1.** Operator can run `core workbench serve` and open a
  bootstrapped UI shell with command palette, keyboard help, and
  state badges. Nothing actionable yet.
- **W2.** Operator can read every pending math + cognition
  proposal, inspect evidence/replay/reasoning trace, and copy the
  suggested ratify CLI for shell fallback.
- **W3.** Operator can ratify a Lexical / Frame / Composition
  proposal via `r` keypress in **under 10 seconds per row** for a
  row whose evidence they understand. Case 0050 remains refused.
  The compounding loop runs at human-realistic throughput.
- **W4a.** Operator can inspect any trace or replay artifact
  inline; replay divergences are structurally diffed.
- **W4b.** Operator can run and inspect eval lanes inline; failing
  cases link back to their audit-row evidence.

**Together:** the math teaching corridor becomes operable by one
operator without context-switching to the shell. The five operator
pain points from the scoping brief are individually retired:

| Pain point | Retired by |
|---|---|
| HITL burden high | W3 keyboard corridor |
| No keyboard corridor for ratification | W3 `r`/`x`/`d`/`y` bindings |
| Evidence is text-block JSON | W2 `StableJsonViewer` + structured detail |
| Reasoning traces are flat | W2 step-list rendering of `MathReasoningStep` |
| Replay equivalence is opaque hex | W2 three-state replay visualization; W4a `ReplayComparisonPanel` |
| No "stuck queue" diagnosis | W2 filter chips + replay-state visualization |

---

## Copy-paste dispatch lines (when ready)

After ADR-0173 (PR #394) lands, dispatch in order:

```text
# W1 — Codex (mechanical scaffold)
Read docs/handoff/WORKBENCH-UI-WAVE-BRIEF-PACK.md §"Brief W1".
git fetch origin main && git worktree add /tmp/wt-wb-ui-w1 origin/main && cd /tmp/wt-wb-ui-w1 && git checkout -b feat/workbench-ui-w1-scaffold

# (wait for W1 merge)

# W2 — Sonnet (read surfaces)
Read docs/handoff/WORKBENCH-UI-WAVE-BRIEF-PACK.md §"Brief W2".
git fetch origin main && git worktree add /tmp/wt-wb-ui-w2 origin/main && cd /tmp/wt-wb-ui-w2 && git checkout -b feat/workbench-ui-w2-proposal-queue

# W4a — Sonnet (parallel with W2)
Read docs/handoff/WORKBENCH-UI-WAVE-BRIEF-PACK.md §"Brief W4a".
git fetch origin main && git worktree add /tmp/wt-wb-ui-w4a origin/main && cd /tmp/wt-wb-ui-w4a && git checkout -b feat/workbench-ui-w4a-replay-surfaces

# W4b — Sonnet (parallel with W2/W4a)
Read docs/handoff/WORKBENCH-UI-WAVE-BRIEF-PACK.md §"Brief W4b".
git fetch origin main && git worktree add /tmp/wt-wb-ui-w4b origin/main && cd /tmp/wt-wb-ui-w4b && git checkout -b feat/workbench-ui-w4b-eval-surfaces

# (wait for W2 merge AND #393 CompositionClaim merge)

# W3 — Opus (ratification corridor; load-bearing wrong=0)
Read docs/handoff/WORKBENCH-UI-WAVE-BRIEF-PACK.md §"Brief W3".
git fetch origin main && git worktree add /tmp/wt-wb-ui-w3 origin/main && cd /tmp/wt-wb-ui-w3 && git checkout -b feat/workbench-ui-w3-ratification-corridor
```

---

## Status zsh trap (operator convenience)

For local dispatch monitoring (mirror the pattern used during the
ADR-0172 Tier 1 wave):

```zsh
status() {
  for pr in 394 393; do
    gh pr view "$pr" --json number,title,state,mergeStateStatus,statusCheckRollup \
      | python3 -c "
import json,sys
d=json.load(sys.stdin)
checks=d.get('statusCheckRollup') or []
from collections import Counter
states=Counter(c.get('conclusion') or c.get('status') for c in checks)
print(f\"#{d['number']} {d['state']:<6} {d['mergeStateStatus']:<16} {dict(states)}  — {d['title'][:60]}\")
"
  done
}
```

Run `status` to get a single-line summary per gating PR.
