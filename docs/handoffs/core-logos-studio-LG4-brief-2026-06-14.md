# LG-4 — CORE-Logos Studio: Alignment tab (centerpiece) + holonomy-absent

**Date:** 2026-06-14
**Wave:** read-only CORE-Logos Studio (L1–L5). Parent pack:
`docs/handoff/core-logos-studio-readonly-briefs-2026-06-14.md`. Plan:
`docs/workbench/core-logos-studio-plan.md`.
**Depends on:** **LG-2 merged** (`/logos` route shell + the 10 `Logos*` TS
interfaces mirrored). Rebase on it. May be authored in parallel with LG-3 but
**merges sequentially** with it (shared train files: `routes.ts` / `App.tsx` /
`api.ts` / `evidenceAddress.ts`) — rebase-union + retest.
**Scope (hard):** the **Alignment** tab (the wave centerpiece) + confirming the
honest holonomy-absent state. **No contents tabs (LG-3). No mutation.** Reads
only `GET /logos/packs/{id}/alignment` (`list[LogosAlignmentRow]`).

## Non-negotiables
- **Determinism is the whole point.** Render with the existing **deterministic**
  DAG primitive (`src/design/components/Dag/Dag.tsx`, layered longest-path via
  `layout.ts`). **No force-directed / nondeterministic layout, no motion-as-
  cognition.** A golden-file layout test is required (mirror
  `Dag/Dag.layout.golden.json`).
- No theater, no recompute. Render only the endpoint's fields.

## Build

### Alignment tab
- Add an **Alignment** tab to the existing `/logos` `TabBar`. The trilingual
  resonance graph (he → grc → en) is the strongest real data in the wave — make
  it the centerpiece. Consumer pattern: `src/app/proposals/ProposalChainViewer.tsx`
  (the existing `Dag` consumer).
- Per-edge card / row (`LogosAlignmentRow`): `source_id` · `target_id` ·
  `relation` · `weight` · `evidence_ids` · `target_pack_id` · **invalid-target
  warning** when `invalid_target` is true.
- **Surface the invalid targets honestly.** LG-1 reports 5 undeclared
  `en-collapse-*` anchors (`breath/heart/holy/soul/time`) as `invalid_target` in
  `grc_logos_cognition_v1`; the declared 3 (`love/justice/peace`) resolve. Show
  the warning — do **not** hide or smooth it. This is a reviewer-visible "the
  geometry tells the truth" moment, not a defect to mask.
- Answer the plan's four questions in the tab: what does this Hebrew root align
  with / what Greek relation carries the same pressure / what English surface
  receives it / what evidence supports the edge (`evidence_ids`, e.g.
  `John1:1` / `Gen1:1`).

### Evidence subject (`src/app/evidenceAddress.ts`)
- Add `logos_alignment_edge` → `logos:<pack_id>:alignment:<edge_id>`, where
  `edge_id` is the LG-1 deterministic id
  (`sha256(source|target|relation)[:16]`, already on `LogosAlignmentRow`).
- Union member, equality, encode/parse, right-inspector projection, copyable
  pointer, `?inspect=` sync, chain-rail derivation. Round-trip test.

### Holonomy — confirm absent-state (no new tab)
- **No Holonomy tab, no proof card, no success state.** Overview already shows
  `holonomy_case_count` 0 + `missing_evidence` (LG-2); Safety shows
  `missing_holonomy_refs` `unknown`. LG-4's only holonomy work is a guard that
  **no holonomy proof affordance leaks in** — add a test asserting the `/logos`
  surface renders no holonomy success/proof element. (Real holonomy cards are
  the future W-Holonomy wave once `holonomy.jsonl` exists.)

## Acceptance / tests
- **Golden-file layout test** for the alignment DAG (deterministic node/edge
  layout; mirror the `Dag.layout.golden.json` pattern).
- Invalid-target render test: an `invalid_target` edge shows the warning; a
  resolved edge does not. Assert the 5 undeclared `en-collapse-*` anchors warn.
- `evidenceAddress.test.ts` — `logos_alignment_edge` round-trip.
- Holonomy-absent guard: no proof/success element on the `/logos` surface.
- `routes.test.tsx` / `schemaDrift` / `enumCoverage` stay green. **No new engine
  schemas** — `NOT_YET_MIRRORED` untouched.
- `pnpm build` clean.
- **Run the FULL `pnpm exec vitest run` before push — it must pass AND exit.**
  The CI `workbench-ui` job gates on the whole suite; focused per-file runs miss
  a PR's own new test files and cross-cutting tests (LG-2 lesson: stale
  route-count assertions only surfaced in the full run, never the focused one).

## Out of scope (separate brief)
- **LG-3** — Lexicon / Glosses / Morphology contents tabs.
- **W-Holonomy / W-Forge** — future waves (author `holonomy.jsonl`; universal
  `ProposalArtifact` envelope + Patch Forge). Not this wave.
