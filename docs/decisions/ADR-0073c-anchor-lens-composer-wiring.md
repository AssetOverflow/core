# ADR-0073c — First non-trivial lenses + composer wiring (Plan Phase L1.3)

**Status:** Accepted
**Date:** 2026-05-19
**Ratified:** 2026-05-19
**Author:** Shay
**Phase:** Plan Phase L1.3 (first non-trivial lenses + composer wiring)
**Parent:** [ADR-0073](./ADR-0073-anchor-lens-substrate.md) (umbrella)
**Builds on:** [ADR-0073a](./ADR-0073a-anchor-lens-content-phase.md) (substrate content),
[ADR-0073b](./ADR-0073b-anchor-lens-class-loader.md) (class + loader)
**Pattern:** mirrors ADR-0070 (terse_v1 — first non-trivial register)

---

## Context

L1.2 landed the architectural plumbing (AnchorLens class + loader +
unanchored sentinel + RuntimeConfig threading) with strict null-lift
discipline — no composer reads the lens, every lane is byte-identical
under `default_unanchored_v1`.  L1.3 now ships the **first non-trivial
lenses** and the composer wiring that consumes them.

The architectural orthogonality claim becomes load-bearing at L1.3:

* `register-tour`: per prompt, fixing lens, varying register → trace_hash CONSTANT.
* `anchor-lens-tour` (L1.4): per prompt, fixing register, varying lens → trace_hash DISTINCT.

Both must hold.  L1.3 lands the substantive surface lift that makes
the second claim true; L1.4 packages the demo that asserts it.

---

## Decision

### L1.3 wiring scope (deliberately narrow)

Composer wiring is restricted to **DEFINITION/RECALL via
`pack_grounded_surface` on the English cognition pack**.  Other
composers (COMPARISON, CORRECTION, PROCEDURE, NARRATIVE, EXAMPLE,
CAUSE, VERIFICATION) accept the `anchor_lens` kwarg but do not yet
consume it.

Rationale:

* The English cognition pack is the cognition lane's load-bearing
  corpus and the demo target for the L1.4 anchor-lens-tour.
* DEFINITION/RECALL is the simplest intent shape — one subject lemma,
  one composed sentence — so the engagement logic is observable
  end-to-end without entangling cross-pack chain traversal.
* COMPARISON/CORRECTION/PROCEDURE need richer engagement semantics
  (two-lemma cross product / dialogue context / verb phrases).  Those
  are deferred to L1.3b or later, mirroring how register's R3 shipped
  one knob before R4 broadened.

### Engagement criteria (single rule)

Given an English lemma `en_lemma` resolving to entry id `en_id` in
the cognition pack:

1. If `lens.is_null_lens()` or `lens.primary_substrate == "none"`
   ⇒ no engagement.
2. Load `alignment.jsonl` for substrate packs matching
   `lens.primary_substrate` (e.g. `grc_logos_cognition_v1` for
   `substrate="grc"`).
3. Find substrate lemmas whose alignment edges target `en_id`.
4. For each such substrate lemma, check whether its
   `semantic_domains` contains any atom from
   `lens.semantic_domain_preferences`.
5. First match wins.  Lens engages; the composer emits
   `cognitive_mode_label`.

The pivot is **shared `semantic_domains` atoms surfaced via the
alignment graph**, exactly the language-neutral commitment from
ADR-0073.  No transliteration tables, no lemma-string lookups, no
non-English glyphs in the engagement path.

### Surface lift

The pack-grounded surface gains an annotation between the existing
provenance tag and the terminating period:

```
no-lens:    "Knowledge is justified understanding ... pack-grounded (en_core_cognition_v1)."
lens-on:    "Knowledge is justified understanding ... pack-grounded (en_core_cognition_v1) [lens(grc_logos_v1):systematic]."
```

The annotation carries both `lens_id` and `cognitive_mode_label` so
audit consumers can answer "which lens fired with which mode" without
re-deriving from telemetry.  The bracket-prefix-suffix shape keeps
the annotation parseable; the surface remains pure ASCII (the L1.3
hard gate forbids non-ASCII characters at the user surface
regardless of substrate).

### First two ratified lenses

**`grc_logos_v1`** — primary substrate Greek; pivots on ἐπιστήμη to
distinguish systematic from experiential knowledge.

```json
{
  "lens_id": "grc_logos_v1",
  "primary_substrate": "grc",
  "semantic_domain_preferences": ["logos.episteme.systematic_knowledge"],
  "cognitive_mode_label": "systematic"
}
```

Engagement target: en lemma `knowledge` (en-core-cog-007).  The grc
cognition pack's `grc-core-cog-021` (ἐπιστήμη) carries the
preferred atom and is bound to en-007 via the
`cross_lang.logos.episteme.en_collapse` alignment edge added at
ADR-0073a.

**`he_logos_v1`** — primary substrate Hebrew; pivots on אמת
(`logos.aletheia.verity`) to render truth as covenant-grounded
verification.

```json
{
  "lens_id": "he_logos_v1",
  "primary_substrate": "he",
  "semantic_domain_preferences": ["logos.aletheia.verity"],
  "cognitive_mode_label": "covenant-verity"
}
```

Engagement target: en lemma `truth` (en-core-cog-002).  The he
cognition pack's `he-core-cog-002` (אמת) carries the preferred atom
and is bound to en-002 via the `cross_lang.logos.aletheia.en`
alignment edge added at ADR-0073a.

Both lenses are ratified via `scripts/ratify_anchor_lens_packs.py`
with the L1.3-widened gate: any lens whose preferences contain an
atom existing in at least one substrate pack's lemma is ratifiable
under method `anchor_lens_lifts_proposition`.  Null lenses keep
ratifying under `byte_identity_null_lift`.

### Ratification-gate widening

`scripts/ratify_anchor_lens_packs.py` gains a non-null branch:

* Null lens (substrate=="none", empty prefs, empty label) ⇒
  `byte_identity_null_lift` (L1.2 method).
* Non-null lens ⇒ verifies that every preferred atom appears in at
  least one substrate-pack lemma's `semantic_domains` (so the lens
  has a real pivot to land on) AND `cognitive_mode_label` is
  non-empty AND `primary_substrate ∈ {grc, he, en}`.  Method:
  `anchor_lens_lifts_proposition`.

Bypass paths are unchanged (`CORE_ALLOW_UNRATIFIED_ANCHOR_LENS=1`).

### Seam test widening

`tests/test_anchor_lens_pack_seam.py` adds `chat/pack_grounding.py`
(and any other composer L1.3 touches) to the **allowed** import set
— the same way ADR-0069 widened the register seam at R2.  Truth-path
modules stay anchor-lens-free.

### Runtime threading

`chat/runtime.py` already exposes `self.anchor_lens` (L1.2).  L1.3
threads it into `pack_grounded_surface(...)` at every call site in
`runtime.py` exactly as `register=self.register_pack` is threaded
today.  Other composers receive `anchor_lens=self.anchor_lens` for
forward-compat but no behavior change yet.

### Invariants pinned at L1.3

```
anchor_lens_byte_identity_null_lift (L1.2)        — preserved
register_invariant_grounding (R3)                  — preserved
seeded_variation_replay_equivalence (R4)           — preserved
register-tour seam (R5)                            — preserved

anchor_lens_lifts_proposition (NEW):
  For every cognition case in {knowledge_define, truth_*}:
    surface(grc_logos_v1) ≠ surface(unanchored)
    surface(he_logos_v1)  ≠ surface(unanchored)
    trace_hash differs across {unanchored, grc_logos_v1, he_logos_v1}
  Pinned by tests/test_anchor_lens_lifts_proposition.py.

anchor_lens_no_glyph_leak (NEW — hard gate):
  ChatResponse.surface contains only ASCII characters regardless of
  loaded lens.  Tested across {unanchored, grc_logos_v1, he_logos_v1}
  × every cognition case.  Pinned by tests/test_anchor_lens_no_glyph_leak.py.
```

The no-glyph-leak gate is **load-bearing**.  ADR-0073's substrate
commitment says English compound phrasing at the user surface, never
raw Greek/Hebrew glyphs.  A non-ASCII char in `ChatResponse.surface`
under any lens fails the lane immediately.

---

## Files

```
packs/anchor_lens/grc_logos_v1.json                            NEW
packs/anchor_lens/grc_logos_v1.mastery_report.json             NEW
packs/anchor_lens/he_logos_v1.json                             NEW
packs/anchor_lens/he_logos_v1.mastery_report.json              NEW

packs/anchor_lens/loader.py                                    EDIT
  - widen ratification (no schema change, just gate logic)

scripts/ratify_anchor_lens_packs.py                            EDIT
  - LENS_IDS adds grc_logos_v1 / he_logos_v1
  - widen gate to accept non-null lenses

chat/pack_grounding.py                                         EDIT
  - _resolve_anchor_lens_mode(en_lemma, lens) → str | None
  - build_pack_surface_candidate() gains anchor_lens kwarg
  - pack_grounded_surface() gains anchor_lens kwarg
  - surface format gains lens annotation when engaged

chat/runtime.py                                                EDIT
  - thread self.anchor_lens into pack_grounded_surface() call sites

tests/test_anchor_lens_pack_seam.py                            EDIT
  - widen allow-list to include chat/pack_grounding.py

tests/test_anchor_lens_lifts_proposition.py                    NEW
  - lens engagement, surface lift, trace_hash divergence

tests/test_anchor_lens_no_glyph_leak.py                        NEW
  - ASCII-only surface across all lenses × all cognition cases

tests/test_anchor_lens_engagement_unit.py                      NEW
  - _resolve_anchor_lens_mode unit coverage

docs/decisions/ADR-0073c-anchor-lens-composer-wiring.md        NEW (this file)
```

---

## Consequences

### Capability unlocked at L1.3

Composer produces structurally different surfaces from different
conceptual substrates, deterministically, with audit-traceable
provenance.  The proposition that English-default would render as
"Knowledge is justified understanding..." becomes
"...understanding... [lens(grc_logos_v1):systematic]." under the
Greek-anchored lens.  Trace_hash moves with it.

### Cognition lane

* `default_unanchored_v1` byte-identical (null-lift invariant
  preserved).
* `grc_logos_v1` and `he_logos_v1` deliberately move the lane's
  outputs.  L1.3 does NOT update the public-split cognition gate
  numbers — the cognition eval continues to run against the
  unanchored default.

### Backwards compatibility

* `pack_grounded_surface()` gains a keyword-only kwarg
  `anchor_lens=UNANCHORED`.  Positional-arg callers unaffected.
* Surface format change is additive: the lens annotation only
  appears when a non-null lens engages.  Without engagement, the
  surface is byte-identical to pre-L1.3.

### Performance

L1.3 adds one alignment-graph lookup + one substrate-lemma lookup per
pack-grounded turn under a non-null lens.  Under the unanchored
default (the production path until operators opt in) zero overhead.
The alignment graph + substrate lexicon are cached via `lru_cache`,
same pattern as the existing pack index.

### Trust boundaries

* Lens preferences are operator-authored content.  The L1.3 ratify
  gate verifies every preferred atom exists in at least one
  substrate-pack lemma — operators cannot ship a lens that
  references atoms not on disk.
* `anchor_lens_no_glyph_leak` is a hard gate: any non-ASCII at the
  user surface fails the lane.  This protects the layperson surface
  contract regardless of substrate.
* No new mutation surface; lens packs continue to be proposal-only
  for runtime, ratifiable only via the operator-only ratify script.

---

## Verification

```
python -m pytest tests/test_anchor_lens_engagement_unit.py -q   N passed
python -m pytest tests/test_anchor_lens_lifts_proposition.py -q N passed
python -m pytest tests/test_anchor_lens_no_glyph_leak.py -q     N passed
python -m pytest tests/test_anchor_lens_null_lift.py -q          4 passed
                                                                  (unchanged)
python -m pytest tests/test_anchor_lens_pack_loader.py -q       24 passed
                                                                  (unchanged)
python -m pytest tests/test_anchor_lens_pack_seam.py -q          N passed
                                                                  (allow-list
                                                                   widened
                                                                   for composer)

Curated lanes (must remain green):
  smoke / cognition / teaching / packs / runtime / algebra

Cognition eval byte-identical under default_unanchored_v1:
  public 100 / 100 / 91.7 / 100

core demo register-tour                                          exit 0
                                                                  (R5 seam
                                                                   still holds)
```

The orthogonality between the two tours is the load-bearing
architectural commitment.  L1.4 packages `anchor-lens-tour` as the
falsifiable demo for the substantive axis; L1.3 makes that demo
possible by delivering the surface lift the demo will assert.
