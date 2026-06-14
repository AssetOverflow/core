# LG-3 — CORE-Logos Studio: Contents tabs (Lexicon / Glosses / Morphology)

**Date:** 2026-06-14
**Wave:** read-only CORE-Logos Studio (L1–L5). Parent pack:
`docs/handoff/core-logos-studio-readonly-briefs-2026-06-14.md`. Plan:
`docs/workbench/core-logos-studio-plan.md`.
**Depends on:** **LG-2 merged** (`/logos` route shell + the 10 `Logos*` TS
interfaces already mirrored + `NOT_YET_MIRRORED` shrunk). Rebase on it. May be
authored in parallel with LG-4, but **merges sequentially** with it (shared
train files: `routes.ts` / `App.tsx` / `api.ts` / `evidenceAddress.ts`) —
rebase-union + retest, Wave R/M discipline.
**Scope (hard):** the three **Contents** tabs only — Lexicon, Glosses,
Morphology. **No Alignment tab (LG-4). No mutation affordances.** Reads only
`GET /logos/packs/{id}/contents` (`LogosPackContents`).

## Non-negotiables
- **No theater, no recompute.** Render only fields the `/logos/contents`
  endpoint returns. Dangling-link flags **reuse** the LG-1 safety report's
  `dangling_morphology_links` — never recompute link integrity in React.
- Read-only; determinism (no nondeterministic ordering); doctrine gates green.

## Build

Add three tabs to the existing `/logos` `TabBar` (pattern:
`src/app/packs/PacksRoute.tsx`). Each list uses the shared primitives:
`src/design/components/VirtualizedList`, `src/design/components/SearchInput`,
`src/design/hooks/useListNavigation.ts`, with selection tokens.

### Lexicon (`LogosLexiconRow`)
Columns: `entry_id` · `surface` · `lemma` · `language` · `pos`/`part_of_speech`
· `semantic_domains` · `morphology_id` · `provenance_ids` · `epistemic_status`.
- Search over surface/lemma/domain; filter by `epistemic_status`; group by
  semantic domain.
- Flag rows whose `morphology_id` appears in the safety report's
  `dangling_morphology_links` (cross-reference, don't recompute).
- `speculative` is the expected default (ADR-0021) — label neutrally.

### Glosses (`LogosGlossRow`)
Columns: `gloss_id` · `lemma` · `gloss` · `pos` · linked `entry_ids` ·
`provenance_ids` · `epistemic_status`. Link each gloss to its lexicon entries
via `entry_ids`. Raw row available in a collapsible (`raw`).

### Morphology (`LogosMorphologyRow`)
- Render the ordered operator chain **in schema order**:
  `root → prefix_chain → stem → inflection → suffix_chain`. Ordering is
  load-bearing (Semitic root / Koine grammar) — **never re-sort**.
- Link to the lexicon entry via `morphology_id`; flag dangling (same
  cross-reference to the safety report).

### Evidence subjects (`src/app/evidenceAddress.ts`)
Add three subject kinds + address grammar (alongside the LG-2 `logos_pack`):
- `logos_entry` → `logos:<pack_id>:entry:<entry_id>`
- `logos_gloss` → `logos:<pack_id>:gloss:<gloss_id>`
- `logos_morphology` → `logos:<pack_id>:morphology:<morphology_id>`
Each: union member, equality, encode/parse, right-inspector projection,
copyable pointer, `?inspect=` sync, chain-rail derivation. Round-trip tests in
`evidenceAddress.test.ts`.

## Acceptance / tests
- Render + filter + keyboard-nav tests for each tab against fixture
  `LogosPackContents`.
- Dangling-link flag test: a row flagged in the safety report shows the flag;
  others don't.
- Morphology order test: chain renders in schema order (assert against a known
  Hebrew entry, e.g. `he-morph-008` suffix `ים`).
- `evidenceAddress.test.ts` — round-trip for all three new kinds.
- `routes.test.tsx` / `schemaDrift` / `enumCoverage` stay green. **No new
  engine schemas** (LG-2 mirrored them) — `NOT_YET_MIRRORED` untouched.
- `pnpm build` clean.

## Out of scope (separate brief)
- **LG-4** — Alignment tab + holonomy-absent confirmation.
