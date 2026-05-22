# Hebrew fluency — gaps

## v1 (current)

- Construction coverage: **C01 only** (simple declarative).
- Word order: verb-second (predicate-subject-object), via
  `generate.articulation._assemble` for `language == "he"`.
- Grounding: through `ChatRuntime.chat()` with `frame_pack="he"`.
- Rubric: **script + length** only (surface contains Hebrew script
  AND length ≤ max_words).  Lexeme-level subject/predicate/object
  slot matching is *not* gated at v1 — the runtime currently folds
  multi-token Hebrew input to a single lexeme through articulation
  (a known limitation, see v2 below).
- Holdout status: ADR-0103 adds plaintext `holdouts/v1/` cases so the
  lane now satisfies the `dev/public/holdout` requirement for
  attachment to ADR-0102 reasoning-capable contracts.

## v2 unblock path — Hebrew construction coverage

To extend to C02–C13 (negation, tense, aspect, quantification,
relative clause, etc.), the realizer needs Hebrew analogues of the
English-only modules:

1. **Hebrew morphology** — analogue of `generate/morphology.py`.
   At minimum: verb conjugation (qal, piel, hifil binyanim), past
   tense (qatal), imperfect (yiqtol), participles, plural agreement.

2. **Hebrew predicate display map** — analogue of
   `_PREDICATE_DISPLAY` in `generate/templates.py` mapping seed-pack
   predicates to surface forms.

3. **Hebrew rhetorical templates** — analogue of `_MOVE_TEMPLATES`.
   Verb-second order changes the slotting; placement of function
   words ("furthermore", "in contrast") needs Hebrew renderings.

4. **Hebrew negation marker** — `לֹא` placement before the verb
   (predicate-first position), not the English `does not <verb>`
   pattern.

5. **Hebrew quantifiers** — `כל` (all), `יש` (some/exists), etc.,
   with appropriate gender + number agreement to the subject.

6. **Lexeme-level slot grounding** — the HE runtime pipeline
   currently produces a single-lexeme articulation (e.g. surface
   `'דבר דבר'` regardless of multi-word Hebrew input).  v2 needs
   the grounding + planning layers to preserve distinct
   subject/predicate/object slots through articulation so the
   rubric can check lexeme presence per slot, not just script
   presence.

## Out of scope for this lane

- Pointed/unpointed text policy (nikkud).  Lexicon entries are
  currently unpointed.  Whether to render pointed surfaces is a
  pack-level decision, not a fluency decision.
- Right-to-left text rendering in tools/UI.  This lane scores the
  string; rendering is downstream concern.
- Modern Hebrew vs. Biblical Hebrew register.  Seed pack is
  cognition-tier Biblical Hebrew; modern register expansion is a
  separate pack.

## Related

- ADR-0020 (Rust parity sequencing) — language-track work is
  independent of the Rust parity track.
- Phase 5.1 (`english_fluency_ood`) — same harness shape; full
  13-construction coverage because English realizer infrastructure
  already exists.
