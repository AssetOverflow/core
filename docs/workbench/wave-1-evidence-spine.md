# Wave 1 — Evidence Spine

Status: approved plan
Date: 2026-06-12
Supersedes: implementation-plan.md phases W-032+
Peer-reviewed by: Codex (architectural path selection), GPT5.5-Thinking (trace
honesty correction), Claude Opus 4.6 (original plan + synthesis)

## Governing idea

Evidence context is the intrinsic UI space. Every route is a projection of the
same evidence manifold. The workbench is not organized around routes (boxes on
screen); it is organized around the evidence chain:

```
operator intent
  -> selected evidence subject
    -> provenance
      -> admissibility
        -> replay
          -> authority
            -> allowed action
```

Chat shows the newest turn. Trace deepens it. Replay tests it. Proposals ask
whether it may alter reviewed memory. Packs/Vault/Audit reveal the substrate
that made it possible. Once the spine exists, remaining routes become inevitable
projections — not independent features.

## Three governing principles (ADR-0160)

1. **Audit-native, not analytics theater.** Every panel answers: what happened,
   why was it allowed, what evidence exists, can it replay, who holds authority.
2. **Calm default, infinite depth.** Quiet surface by default; the deeper you
   inspect, the more transparent it becomes.
3. **Replay before persuasion.** Show deterministic evidence before asking the
   operator to trust anything.

---

## Wave 1 deliverables

Six pieces, one architectural idea.

### 1A. Command Registry + Full Navigation

- [ ] Replace hardcoded command list in `CommandPalette.tsx` with a
      route-registered command registry
- [ ] Each route registers its commands on mount via a shared context/provider
- [ ] Fuzzy search across routes, recent resources (turns, proposals, artifacts),
      and actions (run eval, copy hash)
- [ ] `Cmd+K` opens, type-ahead filters, arrow keys navigate, `Enter` executes,
      `Esc` closes
- [ ] Recent items: last 10 visited resources (turns, proposals, artifacts)
- [ ] Test: palette finds and navigates to every route and registered command

**Current state:** `CommandPalette.tsx` has only Chat/Proposals/Evals hardcoded.

**Key files:**
- `workbench-ui/src/design/components/primitives/CommandPalette.tsx`
- New: `workbench-ui/src/app/commandRegistry.ts` (or context provider)

---

### 1B. RightInspector as Evidence Drawer

- [ ] Remove permanent `collapsed=true` from `Shell.tsx`
- [ ] Create shared evidence-subject context: `useEvidenceSubject()` hook +
      provider in Shell
- [ ] Each route pushes its selection (turn, proposal, artifact, pack, eval
      result) into the shared context
- [ ] Inspector renders the appropriate evidence projection for the selected
      subject type
- [ ] Toggle via `Cmd+I` or "inspect" affordance on selectable items
- [ ] Stays open across route transitions (operator opened it deliberately)
- [ ] Collapsed by default on fresh load (calm default)
- [ ] Resizable width via drag handle
- [ ] Test: inspector opens, shows correct context for Chat selection, closes,
      persists across route change

**Current state:** `RightInspector.tsx` returns null. `Shell.tsx` hardcodes
`collapsed={true}`.

**Key files:**
- `workbench-ui/src/app/RightInspector.tsx`
- `workbench-ui/src/app/Shell.tsx`
- New: `workbench-ui/src/app/evidenceContext.ts`

---

### 1C. Minimal Evidence Primitives

Build only the six components the spine needs. Defer everything else until a
route proves it requires the component.

| Component | Purpose | Used by |
|---|---|---|
| `SplitPane` | Resizable horizontal/vertical split for list-detail | Trace, Proposals, Evals, Replay |
| `TabBar` | Accessible tab switching (see dependency note below) | Trace evidence sections, Inspector |
| `MetadataTable` | Key-value pair display for structured metadata | Trace, Proposals, Artifacts |
| `DigestBadge` | Copyable hash/digest with truncation + verify indicator | Trace, Replay, everywhere |
| `Timestamp` | Relative + absolute time, timezone-aware (PST/PDT) | All list views, Inspector |
| `SearchInput` | Filtered search with keyboard shortcut binding (`/`) | Command palette, list views |

For each component:

- [ ] Built with design tokens only (no raw hex/rgb)
- [ ] Motion via `--motion-duration-*` and `--motion-ease-*` tokens
- [ ] `prefers-reduced-motion` collapses to instant
- [ ] `:focus-visible` ring via `--color-focus-ring`
- [ ] Renders in PreviewPage (`/preview`)
- [ ] Unit test

**TabBar dependency note:** `@radix-ui/react-tabs` is not currently in
`package.json` (only `react-dialog` and `react-popover` are). Either add the
dependency explicitly with lockfile update, or implement TabBar with native
ARIA tab semantics without Radix. Decide at implementation time.

**Deferred primitives** (build when a route needs them):
- DataTable, TreeView, Timeline, CodeViewer, Drawer, Toast, SkeletonLoader, Kbd

---

### 1D. Workbench Turn Evidence Journal

**Critical correction (GPT5.5 review):** The workbench backend does NOT
currently attach a telemetry sink to chat turns. `WorkbenchApi()` constructs
with no sink, `_run_chat_turn()` creates a bare `ChatRuntime()`, and
`serialize_turn_event` redacts content by default. Raw runtime telemetry does
not contain the three surfaces needed for Trace.

**Solution:** A Workbench Turn Evidence Journal — a local, append-only,
content-bearing record of the `ChatTurnResult` envelope already returned by
`/chat/turn`.

This is a **read model**, not a cognitive runtime fork. It does not replace
runtime telemetry; it records the exact evidence the operator already saw.

#### Backend

- [x] New module: `workbench/journal.py`
- [x] `TurnJournal` class: append-only JSONL writer
- [x] Each `/chat/turn` response is journaled with:
      - `turn_id` (stable, sequential)
      - `timestamp` (ISO-8601 UTC)
      - `trace_hash` (from ChatTurnResult)
      - `prompt` (content-bearing — explicit in schema)
      - `surface`, `articulation_surface`, `walk_surface` (all three, kept
        separate per api-contract-v1.md line 231)
      - `grounding_source`, `epistemic_state`, `normative_clearance`
      - `verdicts` (identity, safety, ethics)
      - `refusal_emitted`, `hedge_injected`
      - `proposal_candidates`
      - `turn_cost_ms`
      - `journal_digest` (SHA-256 of the serialized entry)
- [x] Journal path: `workbench_data/turn_journal.jsonl` (under repo root, not
      under `engine_state/` or `teaching/`)
- [x] Content-bearing warning: journal entries contain user prompts and engine
      surfaces. Document this in `workbench_data/README.md` (not as a text
      header in the JSONL file — every line must be valid JSON)
- [x] Path confinement: journal writes only to `workbench_data/`
- [x] No journal writes to `teaching/`, `packs/`, `language_packs/data/`, or
      `engine_state/`. Note: existing chat turns DO write `engine_state/`
      through the normal runtime checkpoint path governed by ADR-0146/0150 —
      that is existing behavior, not journal behavior.

#### New API endpoints

- [x] `GET /trace/turns` — list journal entries (summary: turn_id, timestamp,
      prompt excerpt, surface excerpt, trace_hash, grounding_source)
- [x] `GET /trace/{turn_id}` — full journal entry for a turn (replaces the
      current 404 behavior)
- [x] Pagination: `?limit=50&offset=0` (default limit 50)
- [x] Unknown turn_id returns 404 (not synthetic data)

#### Tests

- [x] Append-only behavior: entries are never modified or deleted
- [x] Stable ordering: entries are sequential by turn_id
- [x] Prompt/content size limits respected (max 4096 chars prompt)
- [x] Path confinement: journal cannot write outside `workbench_data/`
- [x] No journal writes to `teaching/`, `packs/`, `language_packs/data/`; no
      NEW writes to `engine_state/` beyond existing chat checkpoint behavior
      (ADR-0146/0150)
- [x] Journal digest is deterministic for identical content
- [x] Round-trip: `/chat/turn` response -> journal -> `/trace/{turn_id}` ->
      identical evidence fields

#### Optional linkage to runtime telemetry

If `ChatRuntime` is later configured with a `JsonlFileSink`
(`include_content=True`), the Trace route can cross-reference journal entries
with runtime telemetry events by `trace_hash`. This is additive — the journal
is the primary read model.

#### Public interfaces and types

Backend (Python):
- `workbench/journal.py` — `TurnJournalEntry` dataclass, `TurnJournalSummary`
  dataclass, `TurnJournal` class (append, list, get)
- `workbench/schemas.py` — add `TurnJournalEntrySchema`, `TurnJournalSummarySchema`
  for API serialization

Frontend (TypeScript):
- `workbench-ui/src/types/api.ts` — add `TurnJournalEntry`,
  `TurnJournalSummary` interfaces mirroring the Python shapes
- `workbench-ui/src/api/client.ts` — add `fetchTraceTurns(limit?, offset?)`,
  `fetchTraceTurn(turnId)`
- `workbench-ui/src/api/queries.ts` — add `useTraceTurns()`,
  `useTraceTurn(turnId)` React Query hooks
- `workbench-ui/src/app/evidenceContext.ts` — `EvidenceSubject` union type:
  `{ kind: 'turn', data: TurnJournalEntry }` | `{ kind: 'proposal', ... }` |
  `{ kind: 'artifact', ... }` | `{ kind: 'eval_result', ... }` |
  `{ kind: 'none' }`

All new API responses use the existing `{ ok, generated_at, data/error }`
envelope.

---

### 1E. Trace Route

- [ ] Replace `TraceRoutePlaceholder.tsx` with real Trace route
- [ ] Layout: `SplitPane` — turn timeline (left) + trace evidence panel (right)
- [ ] Turn timeline: list of journal entries with `DigestBadge` (trace_hash
      thumbnail), `Timestamp`, prompt excerpt
- [ ] Trace evidence panel: `TabBar` with sections:
      - **Surfaces** — all three, labeled explicitly (surface = user response,
        walk_surface = telemetry evidence, articulation_surface = realizer
        output). This IS the canonical proof of the api-contract-v1.md surface
        separation contract.
      - **Grounding** — source, epistemic state, normative clearance
      - **Verdicts** — identity, safety, ethics verdicts with badge indicators
      - **Metadata** — `MetadataTable` showing turn_cost_ms, checkpoint_emitted,
        refusal/hedge status, proposal candidates
      - **Raw** — collapsed-by-default full JSON viewer (StableJsonViewer)
- [ ] Selection pushes turn into evidence-subject context (RightInspector shows
      same turn from inspector angle)
- [ ] `SearchInput` for filtering turns by prompt text or trace_hash prefix
- [ ] Empty state when journal is empty: "No turns recorded yet. Use Chat to
      create evidence."
- [ ] Test: navigate to Trace, see real journal entries, select one, see evidence
      panel, inspect raw JSON

**Key design rules:**
- Versor condition (when available): green < 1e-6, red >= 1e-6
- Walk surface labeled "telemetry/evidence" — never confused with user surface
- Trace hash always visible and copyable (replay before persuasion)
- Raw trace behind explicit expand (calm default, infinite depth)

---

### 1F. Mutation Doctrine Reconciliation

- [ ] Update `docs/workbench/implementation-plan.md` mutation section to match
      reality
- [ ] Update `docs/workbench/acceptance-gates.md` to reflect admitted corridors
- [ ] Document the honest rule:

**The mutation rule is not "no buttons ever." It is:**

1. **Admitted corridor** — mutation only through an ADR-governed path
   (math ratification via ADR-0172, chat turns via ADR-0146/0150).
2. **Explicit preconditions** — the UI shows what must be true before
   mutation is allowed.
3. **Telemetry** — every mutation emits an auditable event.
4. **Replay evidence** — the operator can see replay-equivalence status
   before acting.

`RatificationCommandPanel.tsx` already implements this pattern for math
proposals. This is the template for future mutation surfaces, not an exception
to a "no mutation" rule.

- [ ] Record what already exists: `ratify_math_proposal`, `reject`, `defer`
      in `workbench/api.py` lines 112+; `RatificationCommandPanel.tsx` with
      precondition gates
- [ ] No new mutation endpoints in Wave 1 beyond what exists

---

## Wave 2 — Projections (after spine is live)

Once the evidence spine exists, each remaining route becomes a projection.
These are parallelizable.

### Packs Route

- [ ] Backend: `GET /packs`, `GET /packs/{pack_id}`
- [ ] Frontend: pack list with verification badges, lexicon browser
- [ ] New primitive: `TreeView` (pack hierarchy)
- [ ] Pushes selected pack into evidence-subject context

### Vault Route

- [ ] Backend: `GET /vault/summary`, `GET /vault/entries`,
      `GET /vault/entries/{entry_id}`
- [ ] Frontend: entry list with epistemic state badges, recall history
- [ ] Pushes selected entry into evidence-subject context

### Audit Route

- [ ] Backend: `GET /audit/events`, `GET /audit/events/{event_id}`
- [ ] Frontend: vertical event timeline, mutation boundary highlighting
- [ ] New primitive: `Timeline`
- [ ] Pushes selected event into evidence-subject context

### Runs Route

- [ ] Backend: `GET /runs`, `GET /runs/{session_id}`
- [ ] Frontend: session list with checkpoint badges, turn history
- [ ] Cross-links to Trace for any turn
- [ ] Pushes selected session into evidence-subject context

### Settings Route

- [ ] Frontend (mostly localStorage): inspector default, JSON depth, timestamp
      format, API connection
- [ ] Runtime config display (read-only)
- [ ] No dangerous mutations — engine config changes require CLI

---

## Wave 3 — Polish + Demo Theater

### Existing module polish

- [ ] Chat: multi-line composer, submission history, richer evidence strip
- [ ] Proposals: visual chain diagram, provenance links, metric deltas
- [ ] Eval Center: failure-first display, lane health overview, run progress
- [ ] Replay Theater: synchronized side-by-side diff, multi-artifact comparison

### Demo Theater route

- [ ] Backend: `GET /demos`, `POST /demos/{demo_id}/run`,
      `GET /demos/{demo_id}/scenarios`
- [ ] Frontend: demo list, scenario results with evidence, "what this proves" /
      "what this does not prove" honesty cards
- [ ] Evidence class badges: substrate-capability vs interface-contract
- [ ] "Proposer was wrong" scenarios visually highlighted

---

## Keyboard map (global, shipped with Wave 1)

| Shortcut | Action |
|---|---|
| `Cmd+K` | Command palette |
| `Cmd+I` | Toggle inspector |
| `Cmd+1`..`Cmd+0` | Navigate to route 1-10 |
| `j/k` or Up/Down | Navigate lists |
| `Enter` | Open selected item |
| `Esc` | Close drawer/palette/inspector |
| `/` | Focus search input |
| `?` | Show keyboard shortcut overlay |

---

## Dependencies

```
Wave 1 (evidence spine) --> Wave 2 (projections, parallelizable)
                        --> Wave 3 (polish + demos)
```

Wave 1 must complete before Wave 2 work begins. Wave 2 routes are independent
of each other. Wave 3 can overlap with late Wave 2 work.

---

## Explicit exclusions

Per ADR-0160 doctrine and CLAUDE.md:

- No multi-user auth, cloud deployment, or SaaS surface
- No animated "thinking" indicators or decorative motion
- No dashboard analytics walls
- No plugin/agent marketplace
- No corpus/pack mutation from the UI
- No mobile layout (engineering workstation only)
- No Deephaven, heavy JVM dependencies, or streaming database engines
- No framework upgrades (stays React 18 + stdlib HTTP)

---

## Peer review record

| Reviewer | Key contribution |
|---|---|
| Claude Opus 4.6 | Original 7-phase plan; synthesis into evidence spine after critique |
| Codex | Path selection: "evidence spine first" over routes-first; evidence chain as intrinsic UI manifold; mutation doctrine correction (admitted corridors, not "no buttons") |
| GPT5.5-Thinking | Trace honesty correction: workbench chat turns do not attach telemetry sink; `ChatTurnResult` content is not in runtime telemetry; solution = Workbench Turn Evidence Journal as honest read model |
