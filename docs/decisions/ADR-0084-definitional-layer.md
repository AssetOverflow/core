# ADR-0084 — Definitional Layer for Lexicon Packs

**Status:** Proposed
**Date:** 2026-05-20
**Author:** Shay

---

## Context

Lexicon packs today carry per-lemma `atoms` and `semantic_domains` —
classification tags used by the composer as if they were glosses:

```
light — teaching-grounded (cognition_chains_v1):
  cognition.illumination; logos.core.
  light reveals truth (cognition.truth)...
```

`cognition.illumination` is not a definition. It's a bucket. The
composer can *mention* it, but cannot *quote* or *paraphrase* it,
because there's nothing to quote. Every surface that emerges from
this is therefore structurally bureaucratic: the system reports
which bucket a lemma sits in, then walks a chain. It never tells
you what the lemma *means*.

This has two downstream consequences we've absorbed silently:

1. **Surfaces don't read as answers.** ADR-0083's
   *"light reveals truth, which grounds knowledge, which requires
   evidence"* is structurally correct (every visible token is
   lemma / domain-tag / connective) but it does not answer
   *"Why does light exist?"*. It walks a graph. The reason it walks
   a graph and not a definition is that we do not store
   definitions — we store graph edges.

2. **Chains are graph-walks, not meaning-walks.** A ratified chain
   `light → reveals → truth` is true because someone reviewed it,
   not because the words' definitions entail it. The system has no
   way to check that `reveals` coheres with what `light` and `truth`
   *are*. So the corpus accepts whatever passes review; the
   review boundary is the only gate. Definitions would let the
   chain be *self-validating* — license-checkable against the
   subject's invited predicates.

The φ separation probe (memory: `phi-separation-falsified`)
established that semantic capability lives in chain composition,
not in φ geometry. ADR-0083 raised the depth ceiling on chain
composition. ADR-0084 raises the *fidelity* ceiling by introducing
the first definitional substrate the composer can draw from.

---

## Decision

Extend the pack schema with an **optional** per-entry definitional
block. Backwards-compatible: every existing pack remains valid
unchanged, and every existing composer path degrades byte-identically
when the block is absent.

### Schema extension

```jsonc
{
  "lemma": "light",
  "atoms": ["light"],
  "semantic_domains": ["cognition.illumination", "logos.core"],

  // ADR-0084 — optional definitional block
  "definition": {
    "gloss": "the medium by which what exists becomes visible",
    "definitional_atoms": ["medium", "exist", "visible"],
    "predicates_invited": ["reveals", "illuminates", "shines"],
    "definition_version": 1,
    "provenance": "adr-0084:reviewed:2026-05-20"
  }
}
```

| Field | Required | Purpose |
|---|---|---|
| `gloss` | yes (inside `definition`) | One-sentence definition. Composer-quotable. |
| `definitional_atoms` | yes | Every content word in `gloss` that is not a closed-class function word. Each must be (a) another lemma in this same pack, (b) a lemma in another mounted pack, or (c) a marked semantic primitive in `packs/primitives/` (introduced as part of this ADR). |
| `predicates_invited` | yes | Predicates this lemma *legitimately appears with as subject*. Used by ADR-0086 to license chain ratification. v1 lemmas may carry an empty list during the migration — license-checking is opt-in at the pack level. |
| `definition_version` | yes | Bumped on every gloss change. Lets calibration / replay tests freeze a definitional snapshot. |
| `provenance` | yes | Same review-trail discipline as ratified chains. |

### Definitional closure rule

The pack ratification gate is extended:

> A pack with a `definition` block on any entry is ratified only if
> every `definitional_atoms` reference resolves to (a) another
> lemma in the same pack, (b) a lemma in another *currently mounted*
> pack at ratification time, or (c) a primitive in `packs/primitives/`.
> Cycles are permitted — definitions can co-reference (a primitive
> like `exist` need not bottom out at a leaf). The only forbidden
> state is an *unresolvable* reference.

This is the only thing that keeps a definitional pack from being a
disguised dictionary of LLM-generated text. Every word in every
gloss is traceable to a ratified source.

### Primitives pack (new, small)

Create `packs/primitives/en_semantic_primitives_v1/`. ~30–60 entries.
Words like `exist`, `be`, `medium`, `visible`, `what`, `cause`,
`relation`, `same`, `different`. These do not have their own gloss
— their meaning is taken as primitive at the system level (analogous
to the ratified axioms in `packs/safety/`). This pack mounts by
default and is never auto-mutable.

The primitives discipline is the load-bearing claim of this ADR:
**we accept a small set of words as primitive so the rest can be
defined in terms of them.** The alternative (every word defined in
terms of other defined words) requires bottoming out somewhere; we
make that explicit.

### Composer is *not* changed in this ADR

ADR-0084 ships the schema extension, the ratification gate, the
primitives pack, and one pilot pack (`en_core_cognition_v1`) with
glosses added end-to-end. Composer integration — surfaces that
actually *quote* the gloss — is ADR-0085 (Gloss-Aware Composer).
Predicate licensing at ratification time is ADR-0086.

This sequencing matters: ratify the substrate before any composer
can depend on it, and prove the schema and closure rule are
operational before adding consumers.

### Pack-level opt-in

A pack signals participation by adding `"definitional_layer": true`
to its manifest. Packs without this flag are unchanged at every
boundary. Mounted alongside non-definitional packs, a definitional
pack contributes glosses for its own lemmas only; cross-pack gloss
access happens through `definitional_atoms` resolution at
ratification time, not at composition time.

---

## Verification

### Required tests

- **Schema validation**:
  - new pack with valid `definition` block parses;
  - missing `gloss` rejected;
  - missing `definitional_atoms` rejected;
  - empty `predicates_invited` accepted (migration aid);
  - unrecognised key inside `definition` rejected (strict gate).
- **Closure rule**:
  - reference to an unmounted pack lemma → ratification failure;
  - reference to a primitive present in `en_semantic_primitives_v1` → pass;
  - reference to a lemma in the same pack → pass;
  - mutual reference (A's gloss uses B, B's gloss uses A) → pass;
  - typo / missing lemma → ratification failure with the unresolved token named.
- **Primitives pack**:
  - loads with `definitional_layer: true` but every entry has an
    empty `definitional_atoms` (terminal by construction);
  - mounting twice is a no-op;
  - non-mountable as a teaching corpus.
- **Backward compatibility**:
  - all existing packs ratify unchanged;
  - all cognition / teaching / smoke / runtime suites pass byte-identically;
  - `core eval cognition` metrics unchanged.
- **Pilot pack measurement**:
  - `en_core_cognition_v1` after gloss addition: every lemma has a
    `definition` block; every `definitional_atoms` reference resolves;
    `definition_version=1` on every entry; manifest checksum updated.

### Lanes (regression check)

```
core test --suite smoke
core test --suite cognition
core test --suite teaching
core test --suite packs
core test --suite runtime
core eval cognition
```

All metrics expected byte-identical (composer is unchanged in this
ADR — definitions are loaded but unread).

### Pilot pack scope

The pilot is `en_core_cognition_v1`. ~22 cognition lemmas
(`light`, `truth`, `knowledge`, `wisdom`, `memory`, `evidence`,
`thought`, `meaning`, `understanding`, `inference`, etc.). Each gets
one sentence, drawn exclusively from the primitives pack +
co-pack lemmas. Targeted at the cases the prompt-diversity suite
(companion to this ADR) exercises.

---

## Consequences

### What changes

- `language_packs/compiler.py` — schema accepts the optional
  `definition` block; ratification gate enforces closure.
- `language_packs/data/en_core_cognition_v1/` — pilot pack gains
  glosses end-to-end; manifest checksum refreshed; companion mastery
  report updated.
- New `packs/primitives/en_semantic_primitives_v1/` — ratified
  primitives pack; mounted by default; never auto-mutable.
- `docs/runtime_contracts.md` — adds the definitional-layer contract
  (what a gloss is, what closure means, where primitives live).

### What does not change

- Composer behaviour: every surface is byte-identical to today.
  ADR-0084 ships substrate, not consumers.
- Versor / vault / recall: completely untouched.
- The non-negotiable field invariant `versor_condition(F) < 1e-6`.
- Trust boundaries: glosses are pack content, ratified through the
  same mastery-report self-seal as every other pack artifact.
- ADR-0073 anchor lenses: each lens-substrate pack can carry its
  own gloss for the same English lemma — definitions and lenses
  belong together. (Different traditions, different definitions
  for `λόγος` / `דבר`.) This ADR neither requires nor blocks
  per-lens glosses; it makes them possible.

---

## Scope limits

- **No composer changes.** Surface-level lift is ADR-0085's job.
  This ADR is solely the substrate.
- **No predicate licensing enforcement.** ADR-0086's job. v1
  accepts `predicates_invited: []` so packs can adopt the schema
  before they're ready to commit to predicate constraints.
- **English pilot only.** The Greek (`grc_logos_v1`) and Hebrew
  (`he_logos_v1`) cognition-tier packs do *not* get glosses in
  this ADR. Per-lens glosses come after the English pilot has
  proven the schema is operational and the closure rule does what
  it claims.
- **Pack-level opt-in.** Without `"definitional_layer": true` in
  the manifest, a pack ratifies as today.
- **Primitives are commitments, not universals.** The primitives
  pack encodes *this system's* primitives. Operators who disagree
  fork the pack.

---

## Why now

The prompt-diversity eval suite (companion proposal at
`evals/prompt_diversity/contract.md`) is about to expose the
surface-quality problem at scale: the same chain-walk template
applied to every question shape. Surfaces *should* read like
answers to the questions asked. Today they read like graph
traversals.

The composer cannot fix this on its own — it has no material to
work with beyond domain tags and connectives. ADR-0084 supplies
the material. ADR-0085 teaches the composer to use it. ADR-0086
license-checks new chains against it. Without the substrate, the
composer changes are speculation.

ADR-0084 is also the smallest possible commitment: optional schema
field, optional pack flag, one pilot pack, no composer change, no
runtime change. It's the most reversible-yet-load-bearing step in
the sequence.

---

## Cross-References

- [ADR-0083](./ADR-0083-transitive-chain-surface.md) — raised the
  *depth* ceiling on chain composition; ADR-0084 raises the
  *fidelity* ceiling.
- [ADR-0073](./ADR-0073-anchor-lens-substrate.md) — anchor lens
  substrate; per-lens glosses are the natural extension of this ADR
  to non-English cognition-tier packs.
- [ADR-0029 / ADR-0027](./ADR-0029-safety-pack.md) — pack-layer
  ratification discipline (mastery-report self-seal) reused
  verbatim for definitional packs and the primitives pack.
- Companion: `evals/prompt_diversity/contract.md` — the prompt
  suite that will measure whether ADR-0084 → 0085 → 0086 actually
  moves surface quality across question shapes.
- Memory: `phi-separation-falsified` — semantic capability lives
  in chain composition, not φ geometry; ADR-0084 is the natural
  next substrate move for chain composition specifically.
- Future: ADR-0085 (Gloss-Aware Composer), ADR-0086 (Predicate
  Licensing at Ratification).
