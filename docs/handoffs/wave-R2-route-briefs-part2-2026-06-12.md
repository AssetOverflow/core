# Wave R2 Route Briefs — Part 2 (R2-S, Runs, Packs, Vault, Settings)

Date: 2026-06-12
Plan: `docs/workbench/wave-R-mastery-revamp.md` § Wave R2.
Predecessor pack: `docs/handoff/wave-R2-route-briefs-2026-06-12.md` (R2-T/R2-A).

Execution: **strictly sequential merges** — every brief touches `App.tsx`,
`types/api.ts`, `routeConformance.test.tsx`, and the `NOT_YET_MIRRORED`
allowlist, so each PR rebases on the previous merge. Order:

```
R2-T → R2-A → R2-S → R2-R (Runs) → R2-P (Packs) → R2-V (Vault) → R2-X (Settings)
```

R2-S gates the rest: it adds the EvidenceSubject kinds the route briefs
publish. Do not start R2-R before R2-S is on main.

## Standing constraints (all briefs)

Identical to the predecessor pack's standing-constraints block — worktree off
fresh `origin/main`, green-local before push, **STOP after checks green;
Shay merges**, token-only styling (hexScan), shrink-only `NOT_YET_MIRRORED`
(remove the entry when you mirror a schema), ADR-0162 §6 conformance rows in
`MOUNT_ROUTES`, selected-vs-focused token discipline, no new mutation
endpoints, no invented data — absent evidence renders honest absence.

Backend ground truth (all already on main via #712, `workbench/api.py`):
list endpoints return `{items, limit, offset}` envelopes with `?limit=&offset=`
pagination; detail endpoints return the object directly. Schemas in
`workbench/schemas.py` are the TS-mirror source — mirror field-for-field.

---

## Brief R2-S — Evidence Subject Extension + Proposals Wrinkles (small, gating)

### Worktree + gates

```bash
cd /Users/kaizenpro/Projects/core
git fetch origin
git worktree add ../core-wb-r2-subjects origin/main -b feat/wb-r2-subjects
cd ../core-wb-r2-subjects
grep -q "audit_event" workbench-ui/src/app/evidenceContext.tsx && echo "STOP: already extended"
cd workbench-ui && pnpm install --frozen-lockfile
```

### Read first

- `src/app/evidenceContext.tsx` (EvidenceSubject union)
- `src/app/evidenceAddress.ts` (codec — `<kind>:<id>` inspect param + route-primary forms)
- `src/app/EvidenceChainRail.tsx` + its test (per-kind `deriveStages`; the
  "MEANINGFULLY FAILS" pattern: removing one fixture field hollows exactly
  its stage)
- `src/app/proposals/ProposalsRoute.tsx` (math-domain selection paths)
- `workbench/schemas.py` lines 285–380 (field names the rail derives from)

### Deliverables

1. Four new subject kinds: `run { sessionId }`, `pack { packId }`,
   `vault_entry { entryIndex }`, `audit_event { eventId }`. Codec forms
   `run:<sessionId>`, `pack:<packId>`, `vault:<entryIndex>`,
   `audit:<eventId>`; route-primary URL forms for `/runs/:sessionId` and
   `/packs/:packId`; vault/audit are inspect-param-only. Update
   `subjectEquals`, encode/decode round-trip tests.
2. `EvidenceChainRail.deriveStages` for each kind, derived from real fields
   (pack: `checksum`/`manifest_digest` → provenance, `determinism_class` →
   admissibility; run: `checkpoint_present`/`checkpoint_revision` → replay,
   `evidence_gap` non-null dims the chain; vault_entry: `epistemic_state` →
   admissibility, `versor_digest` → provenance; audit_event:
   `mutation_boundary` → action, `payload_digest` → provenance). Absent
   field → hollow, never lit. One MEANINGFULLY-FAILS test per kind.
3. Proposals wrinkles (recorded in the R0c report): (a) math-domain
   proposals are not published as inspector subjects — publish on selection
   exactly like the default domain; (b) the copied evidence link for a
   math proposal omits `?domain=math` — the codec/copy path must include it
   so the address round-trips to the same view. Regression tests for both.

No route work. No backend work. Small PR.

### Verification before push

```bash
cd workbench-ui && pnpm build && pnpm test
```

---

## Brief R2-R — Runs Route

### Worktree + gates

```bash
cd /Users/kaizenpro/Projects/core
git fetch origin
git worktree add ../core-wb-r2-runs origin/main -b feat/wb-r2-runs-route
cd ../core-wb-r2-runs
grep -q '"run"' workbench-ui/src/app/evidenceContext.tsx || echo "STOP: R2-S not merged"
cd workbench-ui && pnpm install --frozen-lockfile
```

### Read first

- `workbench/schemas.py` (RunSummary / RunTurnRef / RunDetail) and
  `workbench/readers.py::list_runs` / `read_run` (sources:
  engine_state_manifest + turn_journal; `evidence_gap` semantics)
- The Trace route as merged by R2-T (cross-link target + triad reference)
- `src/app/proposals/ProposalsRoute.tsx` (triad reference implementation)

### Deliverables

1. TS mirrors RunSummary/RunTurnRef/RunDetail; remove all three from
   `NOT_YET_MIRRORED`.
2. `GET /runs` list (VirtualizedList + `useListNavigation` window scope +
   SearchInput): session rows with checkpoint badge
   (`checkpoint_present`/`checkpoint_revision`), turn count, timestamps
   (Timestamp component). `evidence_gap` non-null renders the gap text
   honestly in-row — never hidden.
3. `GET /runs/{session_id}` detail in Panel + TabBar (Turns / Manifest /
   Raw). Every turn row shows `trace_hash` as DigestBadge and links to
   `/trace/<turn_id>` — the cross-link is the point of this route.
   Turn list paginates via `turn_limit`/`turn_offset`.
4. Selection publishes the `run` subject (R2-S) and the URL records it;
   `pushRecentItem` on visit.
5. Conformance rows in `MOUNT_ROUTES` (loading "Loading runs…", error,
   empty: "No runs recorded yet." + `core chat`).

### Verification before push

```bash
cd workbench-ui && pnpm build && pnpm test
```

---

## Brief R2-P — Packs Route

### Worktree + gates

```bash
cd /Users/kaizenpro/Projects/core
git fetch origin
git worktree add ../core-wb-r2-packs origin/main -b feat/wb-r2-packs-route
cd ../core-wb-r2-packs
grep -q '"pack"' workbench-ui/src/app/evidenceContext.tsx || echo "STOP: R2-S not merged"
cd workbench-ui && pnpm install --frozen-lockfile
```

### Read first

- `workbench/schemas.py` (PackSummary / PackDetail — note `checksums` dict
  and `manifest_digest`), `workbench/readers.py::list_packs` / `read_pack`
- `src/design/components/` inventory — TreeView does NOT exist yet; you add it

### Deliverables

1. TS mirrors PackSummary/PackDetail; shrink `NOT_YET_MIRRORED`.
2. New design primitive `TreeView` (`src/design/components/TreeView/`):
   deterministic expansion (no animation), keyboard-driven (arrows expand/
   collapse/traverse), small (~150 lines), own test. Registers its
   shortcuts via `useRegisterShortcuts` only while focused.
3. List: packs with `source`, `version`, `language`/`modality`, and a
   `determinism_class` badge. Detail in Panel + TabBar (Manifest tree via
   TreeView / Checksums / Raw). `checksum` and `manifest_digest` as
   DigestBadge; per-file `checksums` table with DigestBadges (this is the
   verify affordance — the manifest-checksum doctrine made visible).
4. Selection publishes the `pack` subject; URL `/packs/:packId`.
5. Conformance rows (empty state: "No packs discovered." +
   `core pack validate <path>`).

### Verification before push

```bash
cd workbench-ui && pnpm build && pnpm test
```

---

## Brief R2-V — Vault Route (fail-closed)

### Worktree + gates

```bash
cd /Users/kaizenpro/Projects/core
git fetch origin
git worktree add ../core-wb-r2-vault origin/main -b feat/wb-r2-vault-route
cd ../core-wb-r2-vault
grep -q '"vault_entry"' workbench-ui/src/app/evidenceContext.tsx || echo "STOP: R2-S not merged"
cd workbench-ui && pnpm install --frozen-lockfile
```

### Read first

- `workbench/schemas.py` (VaultSummary / VaultEntry) and
  `workbench/readers.py::read_vault_summary` / `list_vault_entries` —
  especially behavior when no persisted vault exists (`persisted: false`)
- `docs/runtime_contracts.md` (memory contract; exact-recall doctrine)

### Deliverables

1. TS mirrors VaultSummary/VaultEntry; shrink `NOT_YET_MIRRORED`.
2. **Fail-closed is the design**: when `persisted` is false (or entries
   empty), the route's PRIMARY state is the honest absence card — vault
   persistence is opt-in via `RuntimeConfig.persist_session_state`; say so,
   with the config pointer. No skeleton theater pretending data is coming.
3. With data: summary strip (entry_count, store_count, reproject_interval,
   max_entries) + VirtualizedList of entries with `epistemic_status` /
   `epistemic_state` badges and `versor_digest` DigestBadge.
4. **Doctrine line**: render only fields the backend returns. Do NOT
   compute, estimate, or display any similarity/relevance score — runtime
   recall is exact CGA (`cga_inner`) and the UI must not invent an
   approximate proxy for it.
5. Selection publishes `vault_entry` subject (inspect-param only).
6. Conformance rows (empty/fail-closed state asserted as the primary
   contract, not an afterthought).

### Verification before push

```bash
cd workbench-ui && pnpm build && pnpm test
```

---

## Brief R2-X — Settings Route

### Worktree + gates

```bash
cd /Users/kaizenpro/Projects/core
git fetch origin
git worktree add ../core-wb-r2-settings origin/main -b feat/wb-r2-settings-route
cd ../core-wb-r2-settings
cd workbench-ui && pnpm install --frozen-lockfile
```

### Read first

- `workbench/schemas.py::RuntimeStatus` + `GET /runtime/status` (already
  mirrored in `types/api.ts` — no NOT_YET_MIRRORED change expected)
- Existing localStorage usage (recent items) for the prefs pattern

### Deliverables

1. Two panels. **Workbench preferences** (localStorage only): default
   landing route, inspector open-by-default, list density
   (comfortable/compact). Each pref takes effect immediately and survives
   reload (test via storage mock).
2. **Runtime (read-only)**: render `/runtime/status` —
   backend, git_revision (DigestBadge), engine_state_present,
   checkpoint_revision, revision_warning (warning styling via tokens),
   active_session_id, mutation_mode. Plus the explicit statement:
   "Engine configuration is CLI-only. This page mutates nothing on the
   server." That sentence is asserted in the conformance test.
3. No backend changes; no new subject kind; no engine mutation of any kind.
4. Conformance rows (loading/error for the status fetch; the prefs panel
   has no empty state — it always renders).

### Verification before push

```bash
cd workbench-ui && pnpm build && pnpm test
```

---

## After this pack

R2 complete → R3 theater briefs: `/replay/{id}` backend + the Replay
Moment, deterministic DAG viewer (hand-rolled layered layout, golden-file
tests), Demo Theater (`GET /demos`, `POST /demos/{id}/run`), wrong=0 ledger
view in Evals. The `/replay` backend is Python-only and parallel-safe with
any in-flight R2 route PR.
