# LG-2 — CORE-Logos Studio: route shell + Overview / Identity / Safety

**Date:** 2026-06-14
**Wave:** read-only CORE-Logos Studio (L1–L5). Parent pack:
`docs/handoff/core-logos-studio-readonly-briefs-2026-06-14.md`. Plan:
`docs/workbench/core-logos-studio-plan.md`.
**Depends on:** **LG-1 merged** (`workbench/logos.py` + `/logos/*` endpoints +
the 10 `Logos*` schemas + their `NOT_YET_MIRRORED` allowlist entries). Do not
start until LG-1 is on `origin/main`; rebase on it.
**Scope (hard):** route shell + **Overview / Identity / Safety** tabs only.
Lexicon/Glosses/Morphology (LG-3) and Alignment (LG-4) are **separate follow-on
briefs** — do not implement their tabs here. The `/logos/contents` and
`/logos/alignment` endpoints exist but LG-2 reads only `/logos/packs`,
`/logos/packs/{id}`, and `/logos/packs/{id}/safety`.

## Non-negotiables (Wave M doctrine)
- **No theater, no recompute.** Render only what the live `/logos/*` endpoints
  return. The workbench computes nothing the engine owns.
- **Read-only.** No mutation calls; no "Draft proposal" affordance this wave.
- **Determinism.** No nondeterministic layout/motion. Golden-file/render tests.
- **Doctrine gates green:** route conformance, schema drift, enum coverage.

## Build

### 1. Route registration (`src/app/routes.ts`)
- Add `/logos` to `WORKBENCH_ROUTES` in the **Substrate** section (alongside
  Packs / CORE-Logos), wired through `ROUTE_ELEMENTS` as a **lazy** route
  element (Phase-E route-chunk pattern — match the existing lazy entries).
- Honest keyboard model: assign a `⌘`-digit only if one is free; otherwise
  palette-only (match the existing 10-pin-+-palette pattern). Bump the
  nav/palette/guide counts the registry derives.
- `routes.test.tsx` must stay green: element-map parity, unique ids/paths/
  digits, palette reachability, landing coverage.

### 2. TS schema mirror (`src/types/api.ts` + drift gate)
- Add TS interfaces for the **10 `Logos*` schemas** (`LogosPackSummary`,
  `LogosPackOverview`, `LogosPackContents`, `LogosLexiconRow`, `LogosGlossRow`,
  `LogosMorphologyRow`, `LogosAlignmentRow`, `LogosMorphologyLinkIssue`,
  `LogosAlignmentTargetIssue`, `LogosSafetyReport`) — field-faithful to
  `workbench/schemas.py` / `workbench-ui/schema-snapshot.json`.
- **Shrink `NOT_YET_MIRRORED`** in `src/design/doctrine/schemaDrift.test.ts`:
  remove each `Logos*` entry as its interface lands. The gate is shrink-only — a
  class gaining an interface while still listed fails. (Mirror all 10 even
  though LG-2 only *renders* a subset; the contract is per-schema, and LG-3/LG-4
  consume the rest.)

### 3. `SafetyVerdict` UI mapping + coverage (where it is rendered)
- Add `SafetyVerdict` to `src/design/components/badges/types.ts` and a
  `safetyVerdictMeta` (`satisfies BadgeMeta<SafetyVerdict>`) to `mappings.ts`,
  covering all four values: `clear` / `warning` / `failed` / `unknown` — with
  honest meanings (`unknown ≠ clear`, `warning ≠ clear`).
- Extend `scripts/dump-enums.py` to source `SafetyVerdict` from
  `workbench/schemas.py` (now justified — it is actually rendered), regenerate
  `workbench-ui/enum-snapshot.json`, and add a `SafetyVerdict` assertion to
  `enumCoverage.test.ts` (exact-coverage vs `safetyVerdictMeta`). This discharges
  the deferral recorded in LG-1.

### 4. `/logos` page shell
- Layout: SplitPane — **Pack Universe** rail · **Studio Workspace** · Evidence
  Inspector (reuse the existing `Panel`/`TabBar`/`SplitPane` primitives).
- **Pack Universe rail:** `GET /logos/packs`; group by role
  (depth_root / depth_relation / logos-cognition); count badges; a
  `SafetyVerdict` badge per pack (text label, not color-only).
- **Bottom status strip (persistent):**
  `selected pack · checksum status · gate/OOV · proposal mode: none — read-only`.

### 5. Tabs (this wave)
- **Overview** — `GET /logos/packs/{id}`: tri-language role framing + counts +
  the safety verdict badge. **Holonomy: render `holonomy_case_count` (0) as
  `missing_evidence` — no tab, no proof card, no success state.**
- **Identity** — manifest passport fields + raw manifest via the existing
  `StableJsonViewer`.
- **Safety** — `GET /logos/packs/{id}/safety` (`LogosSafetyReport`): checksum
  status, domain-contract status, dangling morphology links, **invalid
  alignment targets** (LG-1 surfaces the undeclared `en-collapse-*` anchors here
  — show them), epistemic-status counts, `missing_holonomy_refs` as `unknown`,
  known gaps, verdict. `unknown`/`warning` must never render as `clear`.

### 6. Evidence subject + address grammar (`src/app/evidenceAddress.ts`)
- Add the `logos_pack` subject kind (alongside `pack` / `run` / `vault_entry` /
  `audit_event`): union member, equality, encode/parse.
- Address grammar: `logos:<pack_id>` (distinct from the existing `pack:<id>`).
- Right-inspector projection + copyable pointer (Cmd+Shift+C) + `?inspect=`
  URL-sync, matching the existing subject pattern.
- Extend `evidenceAddress.test.ts` with a `logos_pack` round-trip case.
- **Defer** `logos_entry` / `logos_gloss` / `logos_morphology` /
  `logos_alignment_edge` subject kinds to LG-3/LG-4 (vocab-commitment: add a kind
  only when its tab renders it).

## Acceptance / tests
- `routes.test.tsx` — `/logos` registered, contract parity, counts bumped.
- `schemaDrift.test.ts` — 10 `Logos*` interfaces present; `NOT_YET_MIRRORED`
  shrunk by 10; gate green.
- `enumCoverage.test.ts` — `SafetyVerdict` exact-coverage green.
- `evidenceAddress.test.ts` — `logos_pack` round-trip.
- Render tests: Overview / Identity / Safety against fixture payloads, **including
  the honest absent-holonomy state** (count 0 + `missing_evidence`, no proof
  card) and a `warning`/`unknown` verdict never shown as `clear`.
- `pnpm build` clean (route lazy-loaded, no chunk-size regression).

## Out of scope (separate follow-on briefs)
- **LG-3** — Lexicon / Glosses / Morphology tabs + their evidence subjects.
- **LG-4** — Alignment tab (deterministic DAG centerpiece, invalid-target
  warnings) + holonomy-absent confirmation.

## Wrinkles to carry
- The LG-1 hazard fix means real logos packs read **`WARNING`** (e.g.
  `grc_logos_cognition_v1` has 5 undeclared `en-collapse-*` targets) — that is
  correct and should be *visible* in Safety, not smoothed over.
- `CLEAR` is unreachable as an *overall* verdict by design while holonomy proof
  is absent (LG-1: a logos pack tops out at `UNKNOWN`). Don't add UI that implies
  a clean pack should be green — `unknown` is the honest ceiling until W-Holonomy.
- `speculative` is the expected default `epistemic_status` (ADR-0021) — label it
  neutrally, not as a defect.
