# CORE-Logos Studio — Read-Only Wave (L1–L5) Brief Pack

**Date:** 2026-06-14
**Status:** scoped + ratified by Shay (2026-06-14). Read-only Studio only; honest
absent-state holonomy. Predecessor: Wave M complete (B + C + D + B4).
**Plan doc:** `docs/workbench/core-logos-studio-plan.md` (this wave executes its
L1–L5; L6 Patch Forge / L7 handlers explicitly deferred — see Follow-up waves).
**Execution:** committed brief pack, parallel-safe DAG, dispatched per the
production line that shipped Wave R/M. Briefs are dispatch-ready; Shay dispatches.

---

## Scope decision (locked)

- **Holonomy: honest absent-state now.** No logos pack carries `holonomy.jsonl`;
  the `HolonomyAlignmentCase` *schema* exists (`language_packs/schema.py`) and
  test-level proof cases exist (`tests/test_alignment_graph.py`), but there is no
  pack-level data instance. The Studio renders `holonomy_case_count = 0` +
  `missing_evidence`; **no Holonomy tab, no proof cards, no success state**
  (plan rule, `core-logos-studio-plan.md` Holonomy §). Seeding real
  `holonomy.jsonl` is a follow-up wave.
- **Wave scope: read-only Studio only (L1–L5).** No new mutation power. Patch
  Forge (L6) is gated behind the universal `ProposalArtifact` envelope, which is
  still a planning doc (`proposal-artifact-substrate-v1.md`, no code, no ADR) —
  deferred to its own wave.

## Non-negotiables (bind every brief)

- **Backend-reader-first, no theater.** LG-1 (Python) lands and gates the
  frontend. Every surface reads *real* pack artifacts.
- **Never re-implement engine/pack truth in React or in a new validator.**
  Checksums via `language_packs.compiler`; domain contract via
  `language_packs.domain_contract`; alignment via `alignment.graph`; morphology
  via `morphology.registry`. The only *new* deterministic checks permitted are
  pure-schema link-integrity checks (dangling morphology link, invalid alignment
  target) — pure stdlib, no algebra, with non-vacuous tests.
- **Read-only doctrine holds.** No `/logos` mutation endpoint. Bottom status
  strip reads `proposal mode: none — read-only`. The "Draft proposal" button does
  **not** exist this wave.
- **Determinism in the UI.** Alignment diagram uses the existing deterministic
  DAG primitive (layered longest-path) — no force-directed/nondeterministic
  layout, golden-file layout test required.
- **Doctrine gates extend to every new surface:** schema mirrored
  (`scripts/dump-schemas.py` snapshot + drift gate), enums covered (`SafetyVerdict`),
  route conformant (`routeConformance`), `NOT_YET_MIRRORED` kept empty.

---

## Verified substrate (reuse surface — do not re-derive)

| Need | Reuse | Notes |
|---|---|---|
| Manifest fields/checksums | existing `workbench/readers.py` `_read_json_object`, `_sha256_file`, `SAFE_PACK_ID_RE`, `_display_path` | `read_pack` is manifest-only today — do **not** extend it; put logos readers in a NEW `workbench/logos.py` (avoids `readers.py` merge contention) |
| Lexicon rows | `language_packs.compiler._parse_entry(payload) → LexicalEntry` | `epistemic_status` defaults to `"speculative"` per ADR-0021 — most rows will read speculative; that is honest, not alarming |
| Gloss rows | **none** — read `glosses.jsonl` as raw rows → workbench-layer projection | Do NOT commit a core `GlossEntry` dataclass speculatively (defer-vocab-commitment) |
| Morphology | `morphology.registry.load_morphology(pack_id) → MorphologyRegistry` (`.entries`, `.get`) | `MorphologyEntry` ordering is load-bearing (root→prefix_chain→stem→inflection→suffix_chain) — render in schema order, never re-sort |
| Alignment | `alignment.graph.load_alignment(pack_id) → AlignmentGraph` (`.edges`, `.edges_from`, `.get_edge`) | Edge rows have **no explicit id** → derive a deterministic id `sha256(f"{source_id}|{target_id}|{relation}")[:16]` for the evidence address |
| Checksum verify | `language_packs.compiler` checksum + glosses dual-checksum path | already verifies bytes-on-disk |
| Domain contract | `language_packs.domain_contract.validate_domain_contract_pack(pack_id) → DomainContractValidation` | reuse verbatim |
| Schemas | dataclasses already in `language_packs/schema.py` | `LexicalEntry`, `MorphologyEntry`, `AlignmentEdge`, `HolonomyAlignmentCase`, `LanguagePackManifest` |

**Logos-pack predicate (Pack Universe filter — define explicitly, deterministic):**
a pack qualifies iff `alignment.jsonl` exists in its data dir OR manifest `role`
∈ {`depth_root`, `depth_relation`}. Today this yields exactly
`he_logos_micro_v1`, `grc_logos_micro_v1`, `grc_logos_cognition_v1`,
`he_core_cognition_v1`. The broader `/packs` inventory route stays unchanged.

---

## DAG

```text
LG-1 (Python, GATING) ──▶ LG-2 (route shell) ──┬──▶ LG-3 (contents tabs)
                                                └──▶ LG-4 (alignment + holonomy-absent)
```

LG-3 ∥ LG-4 once LG-2 merges. Doctrine gates fold into each PR's acceptance (no
separate Phase-E PR this wave). **Shared train files** (`workbench-ui/src/app/routes.ts`,
`App.tsx`, `api.ts`/types, `routeConformance`, `NOT_YET_MIRRORED`): LG-2/3/4 merge
**sequentially or rebase-union + retest** on those, per Wave R/M discipline.

---

## LG-1 — Logos read models + readers + endpoints  (Python; GATING)

**Goal:** real read-only readers over logos pack artifacts; no frontend.

**Build:**
- New module `workbench/logos.py` (read-only; never touch `readers.py` pack fns):
  - `list_logos_packs() → list[LogosPackSummary]` (the predicate above; deterministic sort).
  - `logos_pack_overview(pack_id) → LogosPackOverview`: manifest fields (language,
    role, script, version, determinism_class, gate_engaged, oov_policy) + counts
    (`lexicon_count`, `gloss_count`, `morphology_count` via `load_morphology`,
    `alignment_edge_count` via `load_alignment`, `frame_count`/`composition_count`
    = 0 unless files exist, `holonomy_case_count = 0`) + `safety_status` +
    `manifest_digest`.
  - `logos_pack_contents(pack_id) → LogosPackContents`: lexicon (via
    `compiler._parse_entry`), glosses (raw→`LogosGlossRow` projection), morphology
    (`.entries`), alignment (`.edges` + derived edge id). frames/compositions/
    holonomy = empty tuples (honest absent).
  - `logos_pack_safety(pack_id) → LogosSafetyReport`: checksum status (compiler),
    domain-contract (`validate_domain_contract_pack`), **new** dangling-morphology
    detection (`entry.morphology_id` not in registry), **new** invalid-alignment-
    target detection (target not resolvable within pack/declared targets),
    epistemic_status counts, `missing_holonomy_refs` honest `unknown`, known_gaps
    from manifest. Verdict enum `SafetyVerdict {clear, warning, failed, unknown}` —
    `unknown ≠ clear`, `warning ≠ clear`, `failed` blocks (no handler this wave anyway).
- `workbench/schemas.py`: `LogosPackSummary`, `LogosPackOverview`,
  `LogosPackContents` (with `LogosLexiconRow`/`LogosGlossRow`/`LogosMorphologyRow`/
  `LogosAlignmentRow`), `LogosSafetyReport`, `SafetyVerdict`.
- `workbench/api.py`: `GET /logos/packs`, `/logos/packs/{id}`,
  `/logos/packs/{id}/contents`, `/logos/packs/{id}/safety`,
  `/logos/packs/{id}/alignment`. Fail-closed 404 (unknown/unsafe pack id) /
  501 (`evidence_unavailable`) consistent with vault/other readers. `_validate_pack_id`.

**Acceptance / tests (non-vacuous):**
- dangling-link test: break one `morphology_id` → safety verdict ≠ `clear` and the
  broken link is listed.
- checksum-mismatch test: corrupt a byte → checksum status fails, verdict ≠ `clear`.
- absent-holonomy test: `holonomy_case_count == 0` and no proof/success field exists.
- enum coverage `SafetyVerdict`; schema mirror snapshot + drift gate green;
  `NOT_YET_MIRRORED` empty.
- 0 serving-path imports; no algebra import in `logos.py`.

---

## LG-2 — `/logos` route shell + Overview / Identity / Safety  (Frontend; after LG-1)

**Build:**
- Register `/logos` in `workbench-ui/src/app/routes.ts` (**Substrate** section,
  alongside Packs). Honest keyboard model per registry capacity (chord if a digit
  is free, else palette-only — match the existing pattern, bump nav/palette/guide counts).
- `LogosStudio` page: SplitPane (Pack Universe rail · Studio Workspace · Evidence
  Inspector) + bottom status strip `selected pack · checksum status · gate/OOV ·
  proposal mode: none — read-only`.
- Pack Universe rail: logos packs grouped by role (depth_root / depth_relation /
  logos-cognition), count badges, safety badge (text label, not color-only).
- Tabs (TabBar): **Overview** (tri-language role framing + counts + safety verdict),
  **Identity** (manifest passport + `StableJsonViewer` raw), **Safety** (the
  `LogosSafetyReport`; `unknown`/`warning` never rendered as clear).
- Evidence subject `logos_pack` (address `logos:<pack_id>`), right-inspector
  projection, copyable pointer. **Defer** `logos_holonomy_case` subject (no data).

**Acceptance:** `routes.test.tsx` parity (counts/ids/paths/digits/palette/landing),
`enumCoverage` SafetyVerdict, render tests for each tab incl. the `missing_evidence`
holonomy state in Overview/Safety. Build clean (route lazy-loaded per Phase-E pattern).

---

## LG-3 — Contents tabs: Lexicon / Glosses / Morphology  (Frontend; after LG-2)

**Build:**
- Each list = `VirtualizedList` + `SearchInput` + `useListNavigation` + selection tokens.
- **Lexicon:** columns entry_id · surface · lemma · language · POS · semantic_domains
  · morphology_id · provenance_ids · epistemic_status. Filter by epistemic_status;
  flag dangling morphology links (cross-check the safety report, don't recompute);
  group by semantic domain. (`speculative` is the expected default — label neutrally.)
- **Glosses:** gloss row · linked entry/lemma · gloss text · provenance · status.
- **Morphology:** ordered operator chain (root → prefix_chain → stem → inflection →
  suffix_chain) rendered **in schema order**, never re-sorted; linked lexicon entry;
  dangling-link flag.
- Evidence subjects `logos_entry` (`logos:<pack>:entry:<id>`), `logos_gloss`
  (`logos:<pack>:gloss:<id>`), `logos_morphology` (`logos:<pack>:morphology:<id>`) +
  chain-rail derivations.

**Acceptance:** render + filter + nav tests; subject-address round-trip; routes/enum
gates green.

---

## LG-4 — Alignment tab (centerpiece) + holonomy-absent  (Frontend; after LG-2, ∥ LG-3)

**Build:**
- **Alignment** tab = the strongest real data (he→grc→en resonance, real
  `evidence_ids` like `John1:1`/`Gen1:1`). Render with the existing deterministic
  **DAG primitive** (layered longest-path) — **no force-directed**. Columns/edge
  card: source · target · relation · weight · evidence_ids · target pack ·
  invalid-target warning. Answer the plan's four questions (what does this Hebrew
  root align with / what Greek relation / what English surface / what evidence).
- Evidence subject `logos_alignment_edge` (`logos:<pack>:alignment:<edge_id>`,
  edge_id = the LG-1 derived deterministic id).
- **Holonomy: NOT a tab.** Overview already shows `holonomy_case_count = 0` +
  `missing_evidence`; Safety shows `missing_holonomy_refs` as `unknown`. If any
  holonomy affordance is visible at all, it is an explicit "unavailable — no
  holonomy cases in this pack" panel with **no proof cards and no success state**.

**Acceptance:** **golden-file layout test** for the alignment diagram (determinism);
invalid-target warning render test; subject round-trip; gates green.

---

## Follow-up waves (explicitly OUT of scope here — documented so the shape is ready)

1. **W-Holonomy (pack-content + review):** author real `holonomy.jsonl` for the
   logos packs, seeded from the proof shape in `tests/test_alignment_graph.py`
   (he→grc→en path + resonance/distinction proof), checksum it (manifest
   `holonomy_checksum` dual-checksum), validate via compiler, then a *real*
   Holonomy proof-card tab + `logos_holonomy_case` subject. The Studio shape built
   here (absent-state + count + safety `unknown`) is exactly where this data enters.
2. **W-Forge (substrate-first):** land the universal `ProposalArtifact` envelope as
   its own ADR + tests (`proposal-artifact-substrate-v1.md`), THEN Patch Forge (L6,
   `Draft proposal` only, no file write) and handler family 1 (`gloss_add`/
   `gloss_update`, L7) per the plan's handler order + proof obligations.

---

## Wrinkles surfaced (for the record)

- Alignment rows carry **no explicit id** → deterministic derived id (LG-1).
- Glosses have **no core schema** → workbench projection only; no speculative core dataclass.
- `LexicalEntry.epistemic_status` defaults `speculative` (ADR-0021) → most rows read
  speculative honestly; UI must not present that as a defect.
- New link-integrity checks (dangling morphology / invalid alignment target) are
  *new* code but pure-schema/stdlib — permitted, but require non-vacuous tests
  (must fail when a link is deliberately broken).
- `pack_provenance.py` is math-obligation-specific — **not** the Logos safety
  validator (Shay's correction). Reuse compiler + domain_contract + the two link checks.
- Shared train files (`routes.ts`/`App.tsx`/api types/`routeConformance`/
  `NOT_YET_MIRRORED`) → LG-2/3/4 sequential-or-rebase-union merge discipline.
