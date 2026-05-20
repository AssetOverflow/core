# ADR-0074 — Orthogonality tour: anchor-lens × register composition demo

**Status:** Accepted
**Date:** 2026-05-19
**Ratified:** 2026-05-19
**Author:** Shay
**Builds on:** [ADR-0072](./ADR-0072-register-telemetry-operator-surface.md)
(register-tour, R5), [ADR-0073d](./ADR-0073d-anchor-lens-telemetry-tour.md)
(anchor-lens-tour, L1.4)

---

## Context

Two single-axis tours ship today:

* `core demo register-tour` — pins `trace_hash CONSTANT` across
  registers within a fixed lens.
* `core demo anchor-lens-tour` — pins `trace_hash DISTINCT` across
  lenses within a fixed register.

L1.3's `test_register_seam_within_lens_holds` already parametrizes
the inner claim over every lens choice.  ADR-0074 packages **both
claims simultaneously** into a single demo that walks the full
register × lens × prompt matrix and asserts the orthogonality holds
turn-by-turn across the entire grid.

Without this composition demo, an operator can verify each axis
independently but has no single artifact answering the question:

> When I drive `core chat --register X --anchor-lens Y`, are the two
> axes actually independent, or does some unintended coupling
> sneak in?

ADR-0074 ships that artifact as `core demo orthogonality-tour`.

---

## Decision

### Demo shape

A single 3 × 3 × 2 grid:

* **Lenses (3):** `default_unanchored_v1`, `grc_logos_v1`, `he_logos_v1`
* **Registers (3):** `default_neutral_v1`, `terse_v1`, `convivial_v1`
* **Prompts (2):** `"What is knowledge?"` (grc engages),
  `"What is truth?"` (he engages)

That is 18 cells.  For each cell the demo records:

```
surface, trace_hash, grounding_source,
register_id, register_variant_id,
anchor_lens_id, anchor_lens_mode_label
```

### Composed claims

```
A) inner_register_invariant_within_lens:
   For each (lens, prompt) cell, the three register runs share an
   identical trace_hash.
   (R5 register-tour, applied 6 times: 3 lenses × 2 prompts.)

B) outer_lens_distinctness_within_register:
   For each (register, prompt) cell where any non-unanchored lens
   engages, that engaged lens's trace_hash differs from the
   unanchored baseline's trace_hash for the same (register, prompt).
   (L1.4 anchor-lens-tour, applied 6 times: 3 registers × 2 prompts.)

C) surface_carries_register_marker_under_convivial:
   For every convivial cell with a non-empty surface,
   register_variant_id is non-empty (convivial always picks an
   opening from its non-empty bucket).

D) surface_carries_lens_annotation_when_engaged:
   For every cell where a non-unanchored lens engages on the
   prompt's en lemma, the surface contains `[lens(<id>):<mode>]`
   and anchor_lens_mode_label is non-empty.

E) no_substrate_glyph_leak_across_grid:
   No cell's surface contains Greek/Hebrew/Syriac/Arabic letter
   blocks.  (ADR-0073c gate re-asserted across the full matrix.)
```

The five claims together pin the orthogonality: A says register
varies the surface without changing the proposition; B says lens
varies the proposition; C and D say the user-visible markers behave
as expected; E says no axis leaks substrate glyphs even under
composition.

### Files

```
evals/orthogonality_tour/__init__.py                          NEW
evals/orthogonality_tour/run_tour.py                          NEW

core/cli.py                                                    EDIT
  - cmd_demo handler wires orthogonality-tour
  - demo target choices add "orthogonality-tour"
  - cmd_demo description gains a line for orthogonality-tour
  - EPILOG gains "core demo orthogonality-tour"

tests/test_orthogonality_tour_demo.py                          NEW
  - Five claims pinned individually
  - all_claims_supported overall
  - grid shape sanity check (3 × 3 × 2 = 18 cells)

docs/decisions/ADR-0074-orthogonality-tour.md                  NEW (this file)
```

No runtime, composer, loader, pack, or schema changes.  The demo is
a pure consumer of the existing telemetry contracts.

### Invariants pinned

```
register-tour (R5)                                — preserved
anchor-lens-tour (L1.4)                           — preserved
register_invariant_grounding (R3)                 — preserved
anchor_lens_byte_identity_null_lift (L1.2)        — preserved
anchor_lens_lifts_proposition (L1.3)              — preserved
anchor_lens_no_glyph_leak (L1.3)                  — preserved

invariant_orthogonality_tour_seam (NEW):
  evals/orthogonality_tour/run_tour.py asserts the five composed
  claims above on the full 3 × 3 × 2 grid.  Exits non-zero on any
  violation.  Pinned by tests/test_orthogonality_tour_demo.py.
```

---

## Consequences

### Capability unlocked

A single command answers "are register and anchor-lens genuinely
orthogonal under composition?"  with structured evidence — 18 cells'
worth of surfaces, trace hashes, and telemetry fields, plus five
falsifiable claim booleans.

### Cognition lane

Unchanged.  The demo is consumer-only; no production code path is
touched.

### Performance

The demo runs 18 chat turns sequentially.  At current per-turn
latency this lands in single-digit seconds.  No caching changes.

### Trust boundaries

* No new mutation surface.  Demo only reads telemetry.
* Glyph-leak gate is re-asserted in the demo's own claim bundle so
  it can never silently regress under composition.
* CLI choice list is the only operator-visible change; the
  underlying flags (`--register`, `--anchor-lens`) are unchanged.

---

## Verification

```
python -m pytest tests/test_orthogonality_tour_demo.py -q       N passed
core demo orthogonality-tour                                    exit 0
core demo orthogonality-tour --json                             stable schema

Curated lanes (must remain green):
  smoke / cognition / teaching / packs / runtime / algebra

Existing single-axis tours continue to pass:
  core demo register-tour                                       exit 0
  core demo anchor-lens-tour                                    exit 0
```

The orthogonality tour's exit code is the canonical composition
gate — if it ever exits non-zero in CI, the orthogonality between
the two axes has regressed and one of the single-axis tours is also
likely to be failing.
