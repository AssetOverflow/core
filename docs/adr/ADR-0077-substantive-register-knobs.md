# ADR-0077 — Substantive register knobs + register-tour gate strengthening (R6)

**Status:** Ratified
**Date:** 2026-05-19
**Author:** Shay
**Builds on:** [ADR-0068](./ADR-0068-register-pack-subsystem.md) (register
pack subsystem), [ADR-0070](./ADR-0070-register-terse-v1.md) (terse_v1),
[ADR-0071](./ADR-0071-seeded-variation.md) (seeded variation),
[ADR-0072](./ADR-0072-register-telemetry-operator-surface.md) (R5 tour),
[ADR-0075](./ADR-0075-realizer-slot-type-guard.md) (C1 coherence floor)
**Series:** R6 — substantive register consumption (precedes T1 curated
teaching depth)

---

## Context

R1–R5 shipped the register *machinery*: pack class, loader, seeded
variation, ChatRuntime threading, telemetry, operator tour.  The
orthogonality tour (ADR-0074) closed the inside-out arc with the
register axis byte-orthogonal to the anchor-lens axis.

But inspection of live orthogonality-tour output reveals two real
gaps:

* On `pack_grounded_surface` (DEFINITION / RECALL / COMPARISON /
  PROCEDURE), the **only knob any register currently consumes** is
  `disclosure_domain_count`, and that knob only fires on the
  **disclosure** composer — not on any pack-grounded composer.
  Result: across 3 × 3 × 2 = 18 cells, `terse_v1` is byte-identical
  to `default_neutral_v1` on every pack-grounded surface.
* `convivial_v1` is purely decorative (seeded opening/closing
  markers, ADR-0071); it never adds propositional expansion.
* The register-tour's `surfaces_vary_at_least_once` gate passes as
  long as **any one** register produces a different surface for
  any one prompt.  Convivial's wrapper alone satisfies it.
  Result: `terse_v1` could remain a permanent no-op on every
  pack-grounded surface and CI would never flag the regression.

R6 closes both: terse becomes substantively terse, convivial gains a
bounded propositional expansion, and the tour gate is replaced with
a per-register substantive-distinctness claim that can no longer be
satisfied by decoration alone.

### Architectural constraint: trace_hash invariance under register

R5 (ADR-0072) pinned the load-bearing invariant: **per-prompt
trace_hash is CONSTANT across registers**.  The orthogonality-tour
asserts this on every (lens, prompt) cell.  ADR-0073d's anchor-lens
arc deliberately moves trace_hash on the *substantive* axis; the
register axis must not.

This invariant is the load-bearing reason the two axes compose
without interference.  R6 must preserve it.

The current implementation hashes `pre_decoration_surface` to
produce `trace_hash`.  If R6 transformations modify
`pre_decoration_surface`, the invariant breaks.  R6 therefore
introduces a new layering boundary:

```
composer output  ──►  register_canonical_surface   ──► trace_hash
                                  │
                                  ▼
                       R6 substantive transforms
                                  │
                                  ▼
                       pre_decoration_surface
                                  │
                                  ▼
                       R4 seeded marker decoration
                                  │
                                  ▼
                              surface  (user-facing)
```

`register_canonical_surface` is the proposition expressed neutrally
— the form the composer emits with **no register touch at all**.
The pipeline reads this field for `trace_hash`.  Substantive
transformations (R6) and decorative transformations (R4) compose
**after** the hash is sealed.

This preserves the register-tour invariant: terse and convivial may
modify the user-facing surface as much as their pack schema allows,
but they can never move the trace_hash.

---

## Decision

### Schema additions

Three new register pack keys, each defaulting to "no-op" so
default_neutral_v1 stays byte-identical.

```
terse_v1.realizer_overrides:
  drop_provenance_tag : bool   # default False
    When True, the trailing "pack-grounded (<pack_id>)." or
    "teaching-grounded (<corpus_id>): …." provenance clause is
    elided from the pack-grounded composer's output.
  compress_gloss : bool        # default False
    When True, the DEFINITION gloss is rewritten in its terse form
    (drop "is a", drop leading article on the predicate noun phrase,
    keep the head noun + post-modifier).
  drop_articles : bool         # default False
    When True, surface-level "a / an / the" articles in pack-grounded
    composer output are dropped where dropping them does not break
    grammar (heuristic: not before a verb-after-"not" slot).

convivial_v1.realizer_overrides:
  append_semantic_domain_clause : bool   # default False
    When True, after the canonical DEFINITION surface, append one
    bounded clause expressing one additional `semantic_domain`
    atom from the lemma's pack entry — deterministically selected
    by lexicographic position of atoms not already realized in the
    composer's gloss.
```

All keys are **bounded, deterministic, pack-derived**.  No new free-
form text.  No model-generated expansion.  No user-text influence.

`default_neutral_v1` declares all three terse keys + the convivial
key explicitly as `false`, making the no-op contract auditable in
the pack file itself.

### Composer consumption

Two consumer sites added in R6 scope:

```
chat/pack_grounding.py :: pack_grounded_surface(...)
  + read realizer_overrides
  + apply drop_provenance_tag, compress_gloss, drop_articles
  + apply append_semantic_domain_clause

chat/cross_pack_grounding.py :: pack_grounded_comparison_surface(...)
  + read realizer_overrides
  + apply drop_provenance_tag only  (COMPARISON has no gloss/articles
    surface to compress on; expansion is out of R6 scope for COMPARISON)
```

`pack_grounded_correction_surface`, `pack_grounded_procedure_surface`,
NARRATIVE, EXAMPLE, cross-pack chain composers accept the
`realizer_overrides` kwarg but consume zero new keys in R6.  Their
substantive consumption is deferred to a follow-up phase keyed off
real demo evidence — same discipline as ADR-0075's deferred R1.

### Layering separation

Add `register_canonical_surface: str = ""` to `ChatResponse` and
`TurnEvent`.  The field carries the composer output BEFORE any
register transformation — substantive or decorative.

```
chat/runtime.py (stub path + main path):
  1. composer emits canonical surface
  2. register_canonical_surface = canonical
  3. (NEW) substantive_surface = _apply_substantive_register(canonical, register_pack)
  4. pre_decoration_surface = substantive_surface
  5. decorated = decorate_surface(pre_decoration_surface, register_pack)
  6. surface = decorated.surface

core/cognition/pipeline.py:
  Read `register_canonical_surface` for trace_hash when present;
  fall back to `pre_decoration_surface` otherwise (pre-R6 callers).
  Falling back preserves byte-identity for any TurnEvent constructed
  without the new field.
```

`_apply_substantive_register` is a new pure helper in
`chat/register_substantive.py` (sibling to `chat/register_variation.py`
which owns R4 decoration).

### Strengthened register-tour gate

Replace (not augment) the weak `surfaces_vary_at_least_once` claim
in `evals/register_tour/run_tour.py`.  The new gate:

```
terse_substantively_differs_from_neutral_on_at_least_one_pack_grounded_definition:
  For at least one DEFINITION prompt in the tour where
  grounding_source == "pack", the surface emitted under terse_v1
  is byte-different from the surface emitted under
  default_neutral_v1, AND that difference is not solely
  whitespace/punctuation (i.e. terse has produced substantive
  content compression).

convivial_substantively_differs_from_neutral_on_at_least_one_pack_grounded_definition:
  Same shape applied to convivial_v1.  Convivial's substantive
  contribution includes the appended semantic-domain clause OR
  a register marker — both are non-whitespace substantive
  differences.

trace_hash_constant_across_registers_per_prompt:
  Preserved verbatim from R5.  The R6 layering separation makes
  this invariant *load-bearing under substantive transformation*
  — terse compressing the gloss must not move trace_hash.
```

The first two claims are the new substantive-distinctness gates.
The third is R5's invariant under R6's stronger consumer set — the
register-tour now asserts trace_hash invariance specifically *while
the surfaces are demonstrably non-trivial across registers*.

`surfaces_vary_at_least_once` is removed.  Its falsifiability hole
(convivial's wrapper alone satisfying it) is closed by construction.

### Files

```
docs/decisions/ADR-0077-substantive-register-knobs.md    NEW (this file)

packs/register/default_neutral_v1.json                   EDIT
  - realizer_overrides explicitly sets all R6 keys to false
packs/register/terse_v1.json                             EDIT
  - realizer_overrides: drop_provenance_tag = true
                        compress_gloss      = true
                        drop_articles       = true
  - companion .mastery_report.json re-sealed
packs/register/convivial_v1.json                         EDIT
  - realizer_overrides: append_semantic_domain_clause = true
  - companion .mastery_report.json re-sealed
packs/register/loader.py                                 EDIT
  - widen realizer_overrides schema with the four new keys
  - ratify-time validation (closed set of known keys)
scripts/ratify_register_packs.py                         EDIT
  - gate widening: validate R6 keys; non-default values require
    `register_substantively_distinct_from_neutral` invariant pass

chat/register_substantive.py                             NEW
  - _apply_substantive_register(canonical, register_pack) -> str
  - four pure transformations, each guarded by its boolean knob

chat/pack_grounding.py                                   EDIT
  - pack_grounded_surface: pass-through accepts realizer_overrides
    (already in signature); consume drop_provenance_tag,
    compress_gloss, drop_articles via _apply_substantive_register
  - same for pack_grounded_definition path

chat/cross_pack_grounding.py                             EDIT
  - pack_grounded_comparison_surface: consume drop_provenance_tag

chat/runtime.py                                          EDIT
  - Introduce register_canonical_surface field flow
  - Insert _apply_substantive_register call between composer and
    pre_decoration_surface assignment (both stub + main paths)

core/cognition/pipeline.py                               EDIT
  - trace_hash reads register_canonical_surface when present;
    falls back to pre_decoration_surface

core/physics/identity.py                                 EDIT
  - TurnEvent.register_canonical_surface: str = ""

chat/telemetry.py                                        EDIT
  - serialize_turn_event emits register_canonical_surface
    (redacted under include_content=False — wire-format only)

evals/register_tour/run_tour.py                          EDIT
  - Replace surfaces_vary_at_least_once with the three new claims
  - Add terse/convivial substantive-distinctness predicates
  - Preserve all_grounding_sources_identical + all_trace_hashes_identical

tests/test_register_substantive_consumption.py           NEW
  - Per-knob unit tests against synthetic canonical surfaces
  - End-to-end: terse_v1 + DEFINITION drops provenance tag, etc.

tests/test_register_layering_separation.py               NEW
  - trace_hash invariance under substantive register transformation
  - register_canonical_surface byte-identical across registers per prompt

tests/test_register_tour_gate_strengthening.py           NEW
  - The new gate catches the regression: a synthetic terse_v1 with
    all R6 keys = false fails the gate; the real terse_v1 passes it.
```

No anchor-lens code touched.  No cognition-eval surface touched.
No new dynamic imports.  No filesystem writes outside ratify scripts.

### Invariants pinned

```
invariant_register_canonical_surface_constant_across_registers (NEW):
  For every (lens, prompt) cell in the register-tour and
  orthogonality-tour, register_canonical_surface is byte-identical
  across all three registers.  This is the layering-separation
  proof: substantive register transformations cannot leak into the
  canonical (truth-path) representation.

invariant_trace_hash_constant_across_registers_per_prompt (R5):
  Preserved.  Strengthened by R6: now holds while terse and
  convivial produce visibly different surfaces (R6's whole point).

invariant_terse_substantively_distinct_from_neutral (NEW):
  At least one pack-grounded DEFINITION prompt in the register-tour
  produces a surface under terse_v1 that is byte-different from
  the same prompt's surface under default_neutral_v1, with
  difference not solely whitespace/punctuation.

invariant_convivial_substantively_distinct_from_neutral (NEW):
  Same shape applied to convivial_v1.

invariant_realizer_no_illegal_articulation (C1):
  Preserved.  R6 transformations (drop_articles in particular)
  must not produce surfaces that trip R2/R3.  Tests pin this for
  every R6 knob combination.

invariant_realizer_guard_byte_identity_on_currently_passing_cases (C1):
  Preserved.  Cognition eval byte-identical under default_neutral_v1
  (the eval lane's pack).
```

---

## Consequences

### Capability unlocked

`terse_v1` becomes substantively terse on DEFINITION / RECALL /
COMPARISON.  `convivial_v1` gains a bounded propositional expansion.
The register axis acquires real substantive consumption on the
user's most-frequented composer path.

The strengthened tour gate ensures CI catches any future regression
where a register reverts to decoration-only behavior.

### Cognition lane

`default_neutral_v1` is the cognition-eval register.  All R6 keys
default to `false` on neutral.  Cognition eval is byte-identical
under R6 unless a future change opts neutral into a substantive
knob — and that would require its own ADR.

### Performance

Three deterministic string transformations per turn under terse,
one under convivial, zero under neutral.  All O(surface length).
No new caching.

### Trust boundaries

* **No new arbitrary-code surfaces.**  All knobs are bounded
  booleans (or in `convivial`'s case, a single bounded clause from
  a pack-resident atom).  Pack mutation remains proposal-only.
* **Closed-set schema.**  `register/loader.py` validates that
  `realizer_overrides` keys belong to a known set.  Unknown keys
  fail ratification.
* **Pack-derived expansion only.**  `convivial`'s
  `append_semantic_domain_clause` reads from the lemma's existing
  pack atoms.  No external lookup, no LLM call, no user-text
  influence.
* **User-text mutation path unchanged.**  R6 transformations operate
  on the canonical surface, which is itself a function of pack
  data and the input lemma.  User text never reaches the
  transformation logic directly.
* **Telemetry redaction preserved.**  `register_canonical_surface`
  is gated by the existing `include_content` kwarg.

### Replay determinism

Substantive transformations are pure functions of `(canonical, register_pack)`.
Pack data is deterministic from manifest checksums.  Therefore
substantive surface output is deterministic and replay-equivalent
across runs.

### What this explicitly does *not* do

* Does not extend lens consumption beyond `pack_grounded_surface`
  (that's the L2 anchor-lens follow-up named in ADR-0073).
* Does not add new register packs.  R6 is about consumption of
  existing knobs, not new packs.
* Does not change R4 seeded marker decoration.  Convivial's
  openers/closers still apply post-substantive.
* Does not re-enable R1 in C1.  Realizer guard stays as ADR-0075
  shipped it (R2 + R3 active, R1 deferred).
* Does not touch the orthogonality-tour's anchor-lens claims.
  Lens engagement is unchanged; only register substantive content
  expands.

---

## Verification

```
python -m pytest tests/test_register_substantive_consumption.py -q   N passed
python -m pytest tests/test_register_layering_separation.py -q       N passed
python -m pytest tests/test_register_tour_gate_strengthening.py -q   N passed

core eval cognition                                                  byte-identical
                                                                     under
                                                                     default_neutral_v1

core demo register-tour                                              exit 0
core demo anchor-lens-tour                                           exit 0
core demo orthogonality-tour                                         exit 0

Curated lanes:
  smoke / cognition / teaching / packs / runtime / algebra / full
```

The new register-tour exit code is the canonical R6 gate.  If the
tour exits non-zero while pack overrides claim non-default values,
either a register has regressed to no-op behavior or substantive
transformations have leaked into `register_canonical_surface`
(layering-separation breach).

---

## Follow-ups (not in R6 scope)

* **R7** — substantive knob consumption in `correction`,
  `procedure`, NARRATIVE, EXAMPLE composers.  Each needs its own
  composer-specific knob design; bundle is too large for one ADR.
* **R8** — register-aware lens annotation rendering.  Currently
  `[lens(<id>):<mode>]` is a fixed presentation; terse might
  prefer a compressed sigil, convivial a more expressive phrasing.
  Out of R6 scope to keep the lens-axis stable while the register
  axis expands.
* **T1** — curated teaching depth (the next item in the sequence).
  Independent of R6; can ship in parallel once C2 lands.
* **R6.1** — additional knob shapes (e.g., `terse_v1` gaining a
  bullet-form output knob for COMPARISON).  Deferred until the
  current R6 knobs have lived for at least one full eval cycle.
