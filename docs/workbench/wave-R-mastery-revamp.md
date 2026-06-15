# Wave R — Mastery Revamp: Determinism Made Felt

> **Historical record — superseded.** This is the planning doc for its wave and
> records that wave, not current state. Wave M is complete. For the live surface
> see [`README.md`](./README.md) (Current Status), [`UI-UX-GUIDE.md`](./UI-UX-GUIDE.md),
> and the route registry `workbench-ui/src/app/routes.ts` (16 routes).

Status: approved plan
Date: 2026-06-12
Refines: `wave-1-evidence-spine.md` — keeps its spine and Wave-1 deliverables
(all shipped: PRs #702, #703, #704, #706); supersedes its Wave 2 / Wave 3
sequencing with the upgraded specs below.
Reviewed by: Claude Fable 5 (full re-audit of ADR-0160, ADR-0162, the shipped
`origin/main` code, and the Wave 1 plan), approved by Shay.
Execution-shape review (external, via Shay, 2026-06-12): R0 confirmed as a
strict PR train, never one PR; honesty fix made unconditional in R0a; route
conformance test front-loaded R1 → R0a; `Kbd` front-loaded R1 → R0d;
KeyboardHelp made registry-driven in R0d; merge order pinned R0a-first.
Declined with reasons: full serialization of echelon-1 dispatch (file
surfaces verified disjoint; parallel dispatch retained with serial merge),
and folding the Playwright lane into R0a (ADR-0162 acceptance 5–7 needs a
dedicated, parallel-safe brief).

## Why a revamp before Wave 2

Wave 1 shipped the correct architecture — the evidence spine is real, tested,
and on main.  But a fresh audit of the shipped code against the doctrine found
six gaps that compound if Wave 2 routes are built on top of them:

1. **The UI advertises capabilities that don't exist.**  `KeyboardHelp.tsx`
   documents `j/k` list navigation and the Wave 1 keyboard map says it
   shipped — no list in the app implements it.  `SearchInput`'s `/` binding is
   mounted nowhere.  An audit-native product whose help overlay makes false
   claims is violating its own first pillar.
2. **No evidence addresses.**  Every route is a flat path (zero URL params in
   `App.tsx`).  A selected turn, proposal, or eval result cannot be linked,
   bookmarked, or cited.  For a product whose identity is "evidence you can
   hand to someone," the URL is the most important audit artifact — and it
   does not exist.
3. **Doctrine lives in prose, not tests.**  ADR-0162 acceptance criteria 5–7
   require Playwright (reduced-motion collapse, palette-from-every-route,
   offline preview).  No Playwright exists.  The empty/error/loading contract
   has no conformance test.  Per CLAUDE.md's schema-defined proof obligations:
   a claim without a test that can meaningfully fail is decoration.
4. **The deferred substrate is exactly what compounds.**  Inspector resize,
   per-route `setSubject` call sites, palette action-commands, shared list
   navigation — all deferred "until a route needs them."  Six Wave-2 routes
   need all of them simultaneously.  Deferring means rework ×6.
5. **Wave 2/3 were spec'd as CRUD.**  "List with badges + detail panel" six
   times.  Nothing visualizes the structures that make CORE distinct:
   proposition chains, proof-carrying promotion DAGs, entailment traces, the
   wrong=0 ledger.
6. **No frontend CI lane exists at all.**  `smoke.yml` and `full-pytest.yml`
   are Python-only.  Frontend PRs merge with zero frontend CI verification,
   and the local full `pnpm test` hangs on worker teardown (live timer
   handles; diagnosed 2026-06-12).

## The design thesis

The blueprint asks for "Linear's calm + Raycast's speed + Instruments'
precision."  That is the floor.  The ceiling — what no other AI product can
copy honestly — is:

> **Every other AI UI animates fake cognition.  This one makes real
> determinism *felt*.**

Mastery is not more motion or more chrome (the ADR-0162 no-go list stands
unchanged).  Mastery is a small set of **signature interactions** that are
only possible *because* the engine is deterministic:

| Signature interaction | What it is | Pillar it embodies |
|---|---|---|
| **The Evidence Address** | Every evidence subject (turn / proposal / artifact / eval result) has a canonical URL; inspector state serializes into it; `Cmd+Shift+C` copies it anywhere | Audit-native — a claim becomes a pasteable link |
| **The Evidence Chain Rail** | The spine's seven stages (intent → subject → provenance → admissibility → replay → authority → action) as a persistent compact rail in the inspector, each stage lit with its actual status | Calm default, infinite depth — structure, zero theater |
| **The Replay Moment** | Select any turn → Replay → side-by-side original/replay → two trace hashes resolve **equal**, leaf diff confirms zero divergence | Replay before persuasion — the honest wow |
| **Deterministic structure rendering** | Proposal chains / PCCP proof-promotion DAGs / entailment traces as layered SVG DAGs with deterministic layout (same input → same pixels) | All three — interactive where masterful, static where honest |
| **The wrong=0 ledger surface** | Evals render the correct/refused/wrong triplet as the canonical visualization; refusals first-class; failures-first ordering | Audit-native — the engine's epistemic honesty, visible |

Deterministic layout is doctrine, not preference: force-directed layouts are
seeded-random, so the same evidence would render differently across sessions —
a literal replay violation.  Layered longest-path layout with lexicographic
tie-breaking renders identically forever and is screenshot-diffable.

---

## Wave R0 — Substrate hardening

Blocks everything.  Four briefs; R0a ∥ R0b ∥ R0c can run in parallel, R0d
lands after R0c.  **Brief 5 (Trace route) dispatch HOLDS until R0 lands** —
Trace is the first consumer of this substrate and building it twice is waste.

### R0a — Test-runner hardening + frontend CI lane

- [ ] `vite.config.ts` test config gains `testTimeout`, `hookTimeout`,
      `teardownTimeout` caps so a hung worker fails fast instead of hanging to
      a CI wall
- [ ] Timer hygiene audit: every `setInterval`/`setTimeout` in
      `workbench-ui/src/` has a cleanup path; component tests that mount
      timer-scheduling components (`Timestamp`, copy-feedback buttons) use
      fake timers
- [ ] Full multi-file `pnpm test` completes and **exits** locally
- [ ] New `.github/workflows/workbench-ui.yml`: path-filtered to
      `workbench-ui/**` **and the workflow file itself** (it validates its
      own changes), runs `pnpm install --frozen-lockfile && pnpm build
      && pnpm test`, `timeout-minutes: 15`
- [ ] Remove the `j/k`, `/`, and `Enter — Open selected item` rows from
      `KeyboardHelp.tsx` **unconditionally** — the overlay must not advertise
      shortcuts that do not exist.  R0d restores them when they become real
      (and makes the overlay registry-driven so this class of dishonesty is
      structurally impossible)
- [ ] Minimal route conformance test (front-loaded from R1 on
      execution-shape review): parametrized over the implemented routes
      (Chat, Proposals, Evals, Replay), asserts empty / error / loading each
      render with next-action / reproducer / specific-label content
      (ADR-0162 §6).  Minimal means existing routes only — the harness is
      the contract every later route must pass; fix what fails, no
      expected-fail lists

### R0b — Playwright smoke lane (pays ADR-0162 acceptance debt 5/6/7)

- [ ] `@playwright/test` devDependency + `playwright.config.ts` with
      `webServer` (vite preview build)
- [ ] e2e spec 1: `⌘K` opens the palette from every route; palette navigates
      to every route (acceptance criterion 6)
- [ ] e2e spec 2: `prefers-reduced-motion: reduce` collapses tokenized motion
      to instant (acceptance criterion 5)
- [ ] e2e spec 3: `/preview` renders every primitive with network access
      blocked (acceptance criterion 7 — offline-safe, per operator
      circumstances)
- [ ] `pnpm test:e2e` script; CI job added to `workbench-ui.yml` (separate
      job so vitest results are not hostage to browser install)

### R0c — Evidence addresses (URL = subject)

- [ ] `workbench-ui/src/app/evidenceAddress.ts`: `subjectToUrl(subject)` /
      `urlToSubject(params, search)` codec, round-trip property tested for
      every `EvidenceSubject` kind
- [ ] Route params in `App.tsx`: `/trace/:turnId?`, `/proposals/:proposalId?`,
      `/evals/:laneId?`, `/replay/:artifactId?` (placeholders keep flat paths
      until their R2 route lands; the codec already speaks their grammar)
- [ ] `?inspect=` query param carries the inspector subject + open state;
      `EvidenceProvider` syncs with the URL (deep link restores inspector)
- [ ] Existing routes (Proposals, Evals, Replay) read their param on load to
      restore selection and write it on selection change
- [ ] `Cmd+Shift+C` global shortcut + palette command "Copy evidence link"
      (registered but inert until R0d's action-command plumbing; ships the
      shortcut, R0d ships the palette verb)
- [ ] Tests: codec round-trip; deep-link restores Proposals selection;
      inspector state survives a simulated reload

### R0d — Interaction substrate (lands after R0c)

- [ ] `useListNavigation` hook: `j/k` + arrows + `Home`/`End` + `Enter` +
      input-focus guard; roving-tabindex or `aria-activedescendant` pattern
- [ ] `VirtualizedList` primitive over `@tanstack/react-virtual`,
      composing `useListNavigation`; deterministic keys
- [ ] `Panel` primitive: header / toolbar-slot / body chrome so routes stop
      hand-rolling borders
- [ ] Inspector resize: wire the existing `SplitPane` into `Shell.tsx` for
      the inspector column; width persisted (storage access guarded, per the
      `af8d4f75` precedent)
- [ ] Palette action commands: `commandRegistry` gains an action kind;
      per-route `register()` call sites (the deferred Wave-1 item); first
      verbs: "Copy evidence link", "Toggle inspector", "Run eval lane …"
      (registered by the Evals route; executes the existing read-only
      `POST /evals/run` — an ADR-0160-allowed lane, not a mutation)
- [ ] Wire `useListNavigation` + `SearchInput` into the Proposals list and
      Replay artifact list now (at least two real consumers; `/` becomes real
      where a `SearchInput` is mounted)
- [ ] `Kbd` primitive (front-loaded from R1 — KeyboardHelp and palette
      shortcut hints consume it)
- [ ] `KeyboardHelp.tsx` becomes **registry-driven**: the overlay renders
      from the shortcut/command registry instead of a hand-maintained list,
      so advertising an unimplemented shortcut is structurally impossible.
      The rows R0a removed return here as real, registry-backed entries

---

## Wave R1 — Design mastery pass (one PR, after R0)

- [ ] Typography precision: `tabular-nums` for every metric cell
      (`MetadataTable` values, eval metrics, turn costs); type-scale audit;
      `text-wrap: balance` on headings
- [ ] Selection-state unification: selected row vs focused row are visually
      distinct and consistent across routes (tokens, not per-route CSS)
- [ ] Hash display standard: one rule (12-char truncation + copy + mono)
      everywhere; consolidate `CopyableHash` (chat) with `DigestBadge`
      (cleanup-as-you-find: remove the duplicate)
- [ ] `EvidenceChainRail` component in `RightInspector`: seven stages, each
      lit (evidence present) / dim (not applicable) / hollow (not recorded).
      Statuses derive only from fields the subject actually carries — a stage
      with no data renders "not recorded", never a guess
- [ ] Empty-state glyphs: small static deterministic monochrome SVGs
- [ ] `Panel` adoption in Proposals + Evals (Chat/Replay opportunistic)
- [ ] **Doctrine-as-tests** (route conformance moved to R0a; the rest here):
      - [ ] Raw-hex scan test: no hex/rgb literals in `src/**` outside
            `tokens.css`
      - [ ] Schema-drift gate: `scripts/dump-schemas.py` (read-only AST walk
            of `workbench/schemas.py`, same pattern as `dump-enums.py`) →
            snapshot → vitest asserts `types/api.ts` field coverage

---

## Wave R2 — Projections (parallel briefs, written after R0/R1 land)

Every route is the same triad — **list (virtualized, `j/k`) → detail (tabs) →
inspector (chain rail)** — with evidence addresses and a conformance test.
Briefs get authored against the landed substrate; the specs below are the
commitments.

### Trace (Brief 5, upgraded — first dispatch of R2)

Everything in the existing Brief 5, plus: URL param selection via R0c codec,
`useListNavigation` + `VirtualizedList` for the timeline, `Panel` chrome,
versor-condition strip (see journal note below), and the conformance test.

### Runs / Audit / Packs / Vault / Settings

- **Runs** — `GET /runs`, `GET /runs/{session_id}`; session list with
  checkpoint badges; every turn cross-links to `/trace/:turnId`.
- **Audit** — `GET /audit/events`; vertical event timeline (new `Timeline`
  primitive); mutation-boundary events visually weighted above routine events.
- **Packs** — `GET /packs`, `GET /packs/{pack_id}`; new `TreeView` primitive;
  manifest checksum displayed with `DigestBadge` (verify affordance).
- **Vault** — `GET /vault/summary`, `GET /vault/entries`,
  `GET /vault/entries/{index}/recall`; epistemic-state badges; exact-recall
  provenance (`cga_inner` evidence shown, never an approximate score — runtime
  recall is exact by doctrine). **Vault P0/P1/P2 complete** (post-wave-R
  follow-on): P0 honest empty/unavailable framing (#760); P1 entry-inspector
  depth, status/facet/text filters, evidence-rail progression (#762/#763/#764);
  P2 read-only exact-CGA recall evidence (#766) — rehydrates the persisted vault
  and runs the real `VaultStore.recall`, reporting the genuine finite
  `cga_inner` + an `exact_self_match` flag (the `+inf` self-match sentinel never
  crosses the boundary). Read-only throughout; no runtime controls.
- **Settings** — localStorage prefs + read-only runtime config display; no
  engine mutation (CLI-only, stated in the UI).

**Journal addition (additive, append-only-safe):** an optional
`versor_condition` field on journal entries — **investigate first**: it ships
only if `ChatTurnResult`/runtime already exposes the value for the turn.  The
workbench layer must never compute field algebra itself.  Older entries render
"not recorded".

---

## Wave R3 — Theater (the wow, honest)

- **The Replay Moment** — implement the `/replay/{id}` backend (currently
  501): re-run a journaled turn deterministically, return original + replay
  envelopes; frontend hero flow renders hash-to-hash equality and a leaf diff
  with `≠` glyphs.  Read-only; replay does not checkpoint.
- **Deterministic DAG viewer** — one component, hand-rolled layered layout
  (longest-path layering, lexicographic tie-break, ~150 lines, golden-file
  layout tests, no graph dependency).  Pan/zoom/click-node-→-inspector.
  Consumers: proposal chains, PCCP proof-promotion (8 scenarios from
  `demos/proof_carrying_promotion`), entailment traces.
- **Demo Theater route** — `GET /demos`, `POST /demos/{id}/run`; scenario
  results with evidence-class badges and "what this proves / what this does
  not prove" honesty cards; proposer-was-wrong scenarios visually highlighted.
- **wrong=0 ledger view** — Evals renders the correct/refused/wrong triplet
  as the primary visualization; refusal reasons inspectable; failures-first.

---

## Dependency DAG

```
R0a ─┐
R0b ─┼─(R0c)──→ R0d ──→ R1 ──→ R2 (Trace ∥ Runs ∥ Audit ∥ Packs ∥ Vault ∥ Settings) ──→ R3
R0c ─┘
```

R0a / R0b / R0c are parallel-safe to **dispatch** (disjoint files; trivial
`package.json` merge between R0b and R0d is sequenced away).  **Merge order
is a strict train: R0a merges first** — it is the smallest PR, carries the
honesty fix, and lands the CI lane that then verifies R0b and R0c; R0b/R0c
merge next in either order; R0d follows R0c (shares
`evidenceContext`/`Shell`).  R1 is one PR after all of R0.  R2 routes are
mutually independent.  R3 follows the R2 routes it draws data from — no
theater work starts before R0/R1 are merged and tested.

## Keyboard map after R0

| Shortcut | Action | Status |
|---|---|---|
| `Cmd+K` | Command palette | shipped (Wave 1) |
| `Cmd+I` | Toggle inspector | shipped (Wave 1) |
| `Cmd+1`..`Cmd+0` | Navigate routes | shipped (Wave 1) |
| `Cmd+Shift+C` | Copy evidence link | R0c |
| `j/k` / arrows | List navigation | R0d (real, via `useListNavigation`) |
| `/` | Focus search | R0d (real where `SearchInput` is mounted) |
| `Enter` | Open selection | R0d |
| `Esc` | Close overlay / clear selection | shipped + R0d |
| `?` | Keyboard help | shipped (Wave 1; overlay lists only real shortcuts) |

## Explicit exclusions (unchanged from ADR-0160/0162 + Wave 1)

- No multi-user auth, cloud, SaaS, mobile
- No animated cognition theater, glassmorphism, neon, decorative motion
- No force-directed / nondeterministic graph layout — ever
- No corpus/pack mutation from the UI; mutation only through admitted
  corridors (ADR-0172 pattern)
- No framework churn: React 18 + Vite + stdlib-HTTP backend stay
- New dependencies limited to: `@playwright/test` (dev),
  `@tanstack/react-virtual` (runtime, ~3 kB)

## Risks and standing decisions

- **DAG layout**: hand-rolled over `dagre`/`elkjs` — determinism is doctrine,
  graphs are small (<50 nodes), and the layout is a pure function with
  golden-file tests.
- **`versor_condition` in the journal**: investigate-first; never computed in
  the workbench layer.
- **Vitest hang**: if R0a's timer hygiene doesn't fully resolve teardown,
  the timeout caps still convert "hangs 30 min" into "fails in seconds" —
  the CI lane is safe either way.
- **Pipeline merge model**: the AssetOverflow pipeline auto-merges agent
  branches; the reliable gate is pre-push verification.  Every brief carries
  its own verification commands for this reason.

## Brief pack

Dispatch briefs for R0a–R0d and R1 live in
`docs/handoff/wave-R-mastery-briefs-2026-06-12.md`.  R2/R3 briefs are
authored after R0/R1 land, against the real substrate.
