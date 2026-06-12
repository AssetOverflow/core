# Wave R2 Route Briefs — R2-T (Trace) then R2-A (Audit)

Date: 2026-06-12
Plan: `docs/workbench/wave-R-mastery-revamp.md` § Wave R2.
Execution: **strictly sequential** (R2-T merges before R2-A starts — they
share `App.tsx`, `types/api.ts`, and `routeConformance.test.tsx`).

**Agent:** GPT5.5-Thinking (XHIGH)

## Standing constraints (both briefs)

- Worktree off fresh `origin/main`; verify the gate lines before any code.
- Pre-push verification is the gate (the lane runs in CI, but green-local
  first). After pushing and confirming checks green: **STOP and report.
  Shay merges.**
- Token-only styling — `src/design/doctrine/hexScan.test.ts` enforces it.
- TS mirrors: when you add an interface for a schema listed in
  `NOT_YET_MIRRORED` (`src/design/doctrine/schemaDrift.test.ts`), you MUST
  remove its entry — the drift gate fails in both directions by design.
- Surfaces stay distinct: `surface` ≠ `articulation_surface` ≠
  `walk_surface`. Trace is the canonical proof of this contract.
- Selected rows use `--color-selected-bg` / `--color-selected-border`;
  focus ring is keyboard position only.
- Every route state honors ADR-0162 §6 — and adds itself to
  `routeConformance.test.tsx` (`MOUNT_ROUTES` table).
- No new mutation endpoints. No invented data — absent evidence renders
  honest absence states.

---

## Brief R2-T — Trace Route (the flagship)

### Worktree + gates

```bash
cd /Users/kaizenpro/Projects/core
git fetch origin
git worktree add ../core-wb-r2-trace origin/main -b feat/wb-r2-trace-route
cd ../core-wb-r2-trace
ls workbench-ui/src/app/EvidenceChainRail.tsx || echo "STOP: R1 (#713) not merged"
ls workbench/journal.py || echo "STOP: journal missing"
cd workbench-ui && pnpm install --frozen-lockfile
```

### Read first

- `docs/workbench/wave-1-evidence-spine.md` § 1E (the original spec — this
  brief upgrades it onto the landed substrate)
- `docs/workbench/api-contract-v1.md` (surface separation, line ~231)
- `workbench/journal.py` + `workbench/schemas.py` (TurnJournalEntrySchema /
  TurnJournalSummarySchema — your TS mirror source)
- `src/app/evidenceAddress.ts` (the codec already speaks `/trace/<turnId>`)
- `src/app/proposals/ProposalsRoute.tsx` (the reference implementation of
  the triad: window-scope list nav + URL selection + subject publication)
- `src/design/components/` — Panel, VirtualizedList, TabBar, DigestBadge,
  Timestamp, SearchInput, StableJsonViewer
- `src/app/routeConformance.test.tsx` (the contract your route joins)

### Deliverables

1. **TS mirrors** in `src/types/api.ts`: `TurnJournalEntry`,
   `TurnJournalSummary` (field-exact per `schema-snapshot.json`). Remove
   both `Schema` entries from `NOT_YET_MIRRORED` — the drift gate now
   proves the mirror.
2. **Client + hooks**: `fetchTraceTurns(limit?, offset?)`,
   `fetchTraceTurn(turnId)` in `client.ts`; `useTraceTurns()`,
   `useTraceTurn(turnId)` (enabled only with a turnId) in `queries.ts`.
3. **`src/app/trace/TraceRoute.tsx`** replacing the placeholder
   (delete `src/routes/TraceRoutePlaceholder.tsx`, update `App.tsx` — the
   `/trace/:turnId?` param path already exists from R0c):
   - `SplitPane` (horizontal, `id="trace"`): timeline left, evidence right.
   - **Left**: `SearchInput` (filter by prompt text or trace-hash prefix) +
     `VirtualizedList` of summaries — each row: `Timestamp`, prompt excerpt
     (first line, truncated), `DigestBadge` (strip `sha256:`, default
     12-char). List nav via the VirtualizedList's built-in keyboard spine.
     Selected row uses the selected tokens.
   - **Right**: `Panel` + `TabBar`, five tabs:
     - **Surfaces** — all three, explicitly labeled: `surface` "User
       Surface (response)", `articulation_surface` "Articulation Surface
       (realizer)", `walk_surface` "Walk Surface (telemetry/evidence)".
       Each in its own bordered card, mono. THIS is the canonical proof of
       the surface-separation contract — a test must assert all three
       labels render distinctly.
     - **Grounding** — `MetadataTable` + GroundingSource/EpistemicState/
       NormativeClearance badges.
     - **Verdicts** — identity/safety/ethics verdicts, refusal_emitted,
       hedge_injected.
     - **Metadata** — turn_id, turn_cost_ms, checkpoint_emitted, proposal
       candidates, journal_digest (`DigestBadge`).
     - **Raw** — `StableJsonViewer`, collapsed behind an explicit expand
       (calm default, infinite depth).
   - **Selection**: writes `/trace/<turnId>` via the codec (`replace`, not
     `push`), publishes `setSubject({ kind: "turn", turnId, data })` — the
     inspector and EvidenceChainRail light from real fields. Deep link
     restores selection (param read on load). `pushRecentItem` with
     `Turn #<id>` so the palette's Recent section learns turns.
   - **Empty state**: "No turns recorded yet. Use Chat to create
     evidence." + next action `{ kind: "cli", command: "core chat" }`.
   - **versor_condition: DO NOT add.** The journal does not carry it;
     rendering it would require backend changes (investigate-first item,
     deferred). Render nothing rather than synthesize.
4. **Conformance row**: add Trace to `MOUNT_ROUTES`
   (loading "Loading trace…", the standard error contract via your
   ErrorState props, the empty statement + command above). The `/trace/turns`
   endpoint returns the envelope with `{ items: [...] }`.
5. **Route tests** (`src/app/trace/TraceRoute.test.tsx`): mocked fetch;
   timeline renders; selecting shows the evidence panel; the three surface
   labels render distinctly; raw JSON is collapsed by default; deep link
   `/trace/3` restores selection; `j/k` moves the timeline.

### Verification before push

```bash
cd workbench-ui && pnpm build && pnpm test && pnpm test:e2e
```

PR title: `feat(workbench): Trace route — turn evidence timeline over the journal (Wave R2-T)`

---

## Brief R2-A — Audit Route (AFTER R2-T merges)

### Worktree + gates

```bash
cd /Users/kaizenpro/Projects/core
git fetch origin
git worktree add ../core-wb-r2-audit origin/main -b feat/wb-r2-audit-route
cd ../core-wb-r2-audit
ls workbench-ui/src/app/trace/TraceRoute.tsx || echo "STOP: R2-T not merged"
cd workbench-ui && pnpm install --frozen-lockfile
```

### Read first

- `workbench/schemas.py` (`AuditEvent`) + `workbench/api.py`
  (`GET /audit/events` — landed in #712, pagination + stable ordering)
- `docs/workbench/wave-R-mastery-revamp.md` § R2 Audit

### Deliverables

1. **TS mirror**: `AuditEvent` in `types/api.ts`; remove from
   `NOT_YET_MIRRORED`.
2. **`Timeline` primitive** (`src/design/components/Timeline/`): vertical,
   deterministic ordering as delivered by the API (never re-sort
   client-side), each entry shows `Timestamp`, source tag, summary;
   entries with `mutation_boundary: true` get visual weight (selected-token
   border, NOT color-only — include a label). Unit tested; preview entry.
3. **`src/app/audit/AuditRoute.tsx`** replacing the placeholder:
   `Panel` + `SearchInput` (filter by source/summary) + `VirtualizedList`-
   backed `Timeline`; pagination via the API's limit/offset (a quiet
   "Load more", no infinite scroll).
4. **Scope boundary — explicitly deferred**: audit events do NOT become
   evidence subjects in this PR. Extending the `EvidenceSubject` union
   touches the codec/inspector/rail and is a separate, small, reviewed PR
   (it will be spec'd by Claude). Selection here is visual focus only.
5. **Conformance row** + route tests (mocked fetch: list, filter,
   mutation-boundary weighting, pagination, empty "No audit events
   recorded." + next action, error contract, loading "Loading audit
   events…").

### Verification before push

```bash
cd workbench-ui && pnpm build && pnpm test && pnpm test:e2e
```

PR title: `feat(workbench): Audit route — event timeline with mutation-boundary weighting (Wave R2-A)`

---

## After this pack

Remaining R2: Runs, Packs, Vault (fail-closed until persisted evidence
exists), Settings — briefs authored after R2-T/R2-A land. Then R3 theater:
`/replay` backend + the Replay Moment, deterministic DAG viewer, Demo
Theater, wrong=0 ledger.
