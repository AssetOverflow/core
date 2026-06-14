# W-Holonomy — author real holonomy cases + the Holonomy proof-card tab

**Date:** 2026-06-14
**Status:** forward brief (post read-only Studio, L1–L5 complete: LG-1 #737 /
LG-2 #738 / LG-3+LG-4 #739 all merged). Dispatch when prioritized.
**Predecessor doctrine:** `docs/workbench/core-logos-studio-plan.md` (Holonomy
tab §) — which the read-only wave deliberately rendered as `missing_evidence`
because no pack-level `holonomy.jsonl` exists yet. This wave fills that.

## Why this is the hard one (read before scoping)

Holonomy is the **crown proof** of the tri-language design: aligned canonical
clauses (Hebrew path, Greek path, English path) must produce *nearby holonomies
without flattening their distinctions*. The `HolonomyAlignmentCase` schema
already exists (`language_packs/schema.py`) and **test-level** proof cases exist
(`tests/test_alignment_graph.py`), but **no logos pack carries `holonomy.jsonl`**
and there is **no serving-path holonomy proof evaluator**.

Two hard constraints from CLAUDE.md bind this wave:

1. **No success state without proof.** A Holonomy proof card may render a
   "holds" verdict ONLY when a real proof was computed. Absent/failed proof
   renders as `missing_evidence` / `failed`, never green. (This is why the
   read-only wave showed count-0, not a fake card.)
2. **Schema-Defined Proof Obligations.** `HolonomyAlignmentCase` only becomes a
   *verified* property when an executing test **meaningfully fails** under a
   violated case — i.e. a case whose paths flatten a distinction, or whose
   holonomy exceeds tolerance, must make the evaluator return `failed` and a
   test must assert that. A proof evaluator that passes everything is decoration.

This is genuine field-algebra work, not data entry. Scope it as a multi-PR wave.

## Sequenced PRs

### WH-1 (engine) — deterministic holonomy proof evaluator
- New evaluator (e.g. `alignment/holonomy.py`) that, given a
  `HolonomyAlignmentCase` (source_refs across pack_ids, expected_relation,
  negative_source_refs, tolerance), composes the field-path holonomy over the
  aligned canonical clauses using the **owned algebra** (`algebra` /
  `versor_apply` / `cga_inner`) — never a re-implemented metric — and returns a
  typed verdict: `holds` / `flattened` / `exceeds_tolerance` / `missing_refs`.
- The `negative_source_refs` are the falsifier: a real case must distinguish the
  positive alignment from the negatives (no flattening). **Non-vacuous tests:**
  a known-good case returns `holds`; a case with a negative ref swapped in
  returns a non-`holds` verdict; a missing ref returns `missing_refs`. Seed the
  fixtures from the existing `tests/test_alignment_graph.py` proof shape.
- Pure/deterministic; respects `versor_condition < 1e-6` by construction (no
  hot-path repair). Off the serving path (no `generate.derivation` import).

### WH-2 (pack content) — author `holonomy.jsonl`
- Author real `HolonomyAlignmentCase` rows into the logos packs (start with
  `he_logos_micro_v1` + `grc_logos_micro_v1`, the curated micro packs), each
  with ≥2 source_refs across ≥2 pack_ids, an `expected_relation`,
  `negative_source_refs`, and a `tolerance`.
- Add a `holonomy_checksum` to each manifest pinned to the bytes written
  (`sha256(holonomy_path.read_bytes())`); compiler verifies it like the
  glosses dual-checksum. Deterministic row order.
- **Depends on WH-1** so authored cases are validated against a real evaluator
  (don't author cases no evaluator can check — that recreates the decoration
  risk). Reconcile collapse anchors first if a case touches them
  (`logos-collapse-anchor-reconciliation-2026-06-14.md`).

### WH-3 (reader) — surface cases + proof status
- Extend `workbench/logos.py`: populate `LogosPackContents.holonomy_cases`
  (currently `[]`) from `holonomy.jsonl`, and add a `LogosHolonomyCase` read
  model carrying the case fields **plus the WH-1 proof verdict** (computed
  read-only via the evaluator, or read from a persisted proof if WH-1 persists
  one — prefer persist-first if the computation is non-trivial, mirroring C3).
- Overview `holonomy_case_count` becomes real; Safety `missing_holonomy_refs`
  resolves from `unknown` once cases exist. Schema mirror + drift gate; the
  read model SHA-pinned if it asserts a proof metric.

### WH-4 (UI) — the Holonomy tab (proof cards)
- Add a **Holonomy** tab to `/logos` (between Alignment and Safety). Render each
  case as a proof card: the three paths (Hebrew ↘ / Greek ↗ / English),
  source_refs, expected_relation, tolerance, and the **proof verdict**.
- **Honesty gate (load-bearing):** render a "holds" affordance ONLY for
  `holds`; render `flattened` / `exceeds_tolerance` / `missing_refs` as their
  honest failed/absent state with no success styling. A test must assert that a
  non-`holds` case renders no success element.
- New `logos_holonomy_case` evidence subject
  (`logos_holonomy_case:<packId>/<caseId>`) + inspector projection + chain-rail
  derivation (the `replay` stage = the proof verdict). Mirror the LG-3/LG-4
  subject pattern.
- Full `pnpm exec vitest run` (pass AND exit) + golden-file layout test if the
  proof card uses the DAG primitive for the path diagram.

## Non-negotiables
- No success without computed proof; the evaluator must meaningfully fail.
- Engine math owned by `algebra` — never re-implemented in reader or UI.
- Read-only; no mutation. Off the serving path.
- Deterministic; `versor_condition` preserved by construction (no hot-path repair).

## Out of scope
- Patch Forge / proposal envelope (W-Forge).
- Cross-turn or session-level field-coherence trends.
