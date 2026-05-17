# Koine Greek fluency — gaps

## v1 (current)

- Construction coverage: **C01 only** (simple declarative).
- Word order: subject-object-predicate, via
  `generate.articulation._assemble` for `language == "grc"`.
- Grounding: through `ChatRuntime.chat()` with `frame_pack="grc"`.
- Rubric: **script + length** only.  Lexeme-level slot matching is
  not gated at v1 for the same runtime-folding reason as Hebrew
  (see v2 §6 below).

## v2 unblock path — Koine Greek construction coverage

To extend to C02–C13 (negation, tense, aspect, quantification,
relative clause, etc.), the realizer needs Greek analogues of the
English-only modules:

1. **Greek morphology** — analogue of `generate/morphology.py`.
   At minimum: verb conjugation across the principal parts (present,
   future, aorist, perfect, perfect middle, aorist passive),
   participles (active/middle/passive across tenses), noun
   declension (1st/2nd/3rd) with case-marked subject/object slots
   instead of word-order-marked.

2. **Greek predicate display map** — analogue of `_PREDICATE_DISPLAY`
   in `generate/templates.py` mapping seed-pack predicates to surface
   forms with appropriate aspect marking.

3. **Greek rhetorical templates** — analogue of `_MOVE_TEMPLATES`.
   Particle-driven discourse markers (μέν / δέ, γάρ, οὖν) instead of
   English function words ("furthermore", "in contrast").

4. **Greek negation** — οὐ / μή placement before the verb, with the
   οὐ/μή split governed by mood (indicative vs. non-indicative).

5. **Greek quantifiers** — πᾶς (all), τις (some/indefinite), with
   declension matching the subject's case/number/gender.

6. **Case-marked agreement** — Greek's free word order is governed
   by morphological case; the realizer needs to mark subject in
   nominative and object in accusative regardless of surface order.
   The lexicon entries currently lack case-paradigm tags.

7. **Lexeme-level slot grounding** — same limitation as Hebrew:
   the GRC runtime pipeline currently produces single-lexeme
   articulations for multi-token Greek input.  v2 needs the
   grounding + planning layers to preserve distinct
   subject/predicate/object slots so the rubric can check lexeme
   presence per slot.

## Out of scope for this lane

- Polytonic accent generation.  Lexicon entries carry accents as
  fixed strings; the realizer does not currently compute accent
  shift on enclisis.
- Attic vs. Koine register distinction.  Seed pack is Koine
  (logos-tier vocabulary); Attic expansion is a separate pack.
- Reconstructive pronunciation (Erasmian vs. modern vs.
  reconstructed Koine).  Lane scores the script; pronunciation is
  out of band.

## Related

- ADR-0020 (Rust parity sequencing) — language-track work is
  independent of the Rust parity track.
- Phase 5.2 (Hebrew) — same v1 scope rationale; same v2 unblock
  pattern, swapped for Greek-specific morphology.
