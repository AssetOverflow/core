# Foundational physics fluency OOD — gaps

## v1 (current)

- Constructions covered: all 13 (C01–C13) via grammatical_coverage rubric.
- Domains covered: public — mechanics, electricity, thermodynamics; holdout —
  optics.
- Predicates default to regular verbs to keep morphology gaps from
  confounding the structural fluency claim.

## Known gaps for v2

The Phase 5.1 English fluency OOD lane already names three realizer
gaps that apply equally here:

  G1. Irregular past tense — past_tense() handles regular -ed but not
      irregular forms (e.g. "ran", "stood").
  G2. Plural agreement — the realizer does not pluralise nouns or
      conjugate to plural subjects.
  G3. Punctuation strictness — the rubric pins comma-bounded relative
      clauses exactly; small punctuation differences still fail.

These are not lane-specific.  When 5.1 closes them, every domain lane
gains the same coverage for free.

## Out of scope for this lane

- Domain-specific semantic correctness (whether "ribosome assembles
  protein" is *true* biology).  This lane measures fluency, not
  factual correctness.  Truth checks live in the
  `epistemic_status` surface (ADR-0021) and future curriculum
  lanes.
