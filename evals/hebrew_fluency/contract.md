# Hebrew fluency eval lane (Phase 5.2)

## What it measures (v1, honest scope)

Whether the deterministic articulation layer
(`generate/articulation.py`) produces a Hebrew-script surface in
verb-second word order (predicate-subject-object) when given a
(subject, predicate, object) triple drawn from the
`he_core_cognition_v1` / `he_logos_micro_v1` seed packs.

This is the C01 (simple declarative) gate only.

## Why v1 is C01-only

The realizer's tense/aspect/quantifier/negation logic in
`generate/templates.py` and `generate/morphology.py` is English-only:

  - `_PREDICATE_DISPLAY` maps English predicates to English phrases
  - `_inflect_predicate` calls `past_tense`, `present_participle`,
    `past_participle`, `base_form` from `generate/morphology.py` —
    all English regular-verb morphology
  - `_MOVE_TEMPLATES` produce English-only function words ("furthermore",
    "in contrast", "next", "correction")

Measuring C02–C13 in Hebrew without first building Hebrew morphology
+ Hebrew rhetorical templates would be measuring code paths that
don't exist.  The honest v1 scope is what *does* exist: pack
grounding + word-order assembly through `_assemble`.

## Inputs

`public/v1/cases.jsonl`
:  3 cases — one per triple from the seed packs, all C01.

`dev/cases.jsonl`
:  1 case — smoke check for runner integration.

`holdouts/v1/cases.jsonl`
:  5 sealed plaintext Hebrew realization cases added for ADR-0103.
   These cases are not referenced by the development split and complete
   the `dev/public/holdout` requirement for attaching
   `hebrew_fluency` to ADR-0102 ratified contracts.

## Scoring rubric

A case passes if the realized surface:
1. Contains Hebrew script (U+0590..U+05FF)
2. Is in `accept_surfaces` OR satisfies all `constraints`
   (`must_contain`, `max_words`)

## Provenance

Same `realize()` entry point as
`tests/test_articulation.py::test_realize_hebrew_surface_uses_hebrew_script_and_compact`,
generalized into a lane with multiple cases and the standard scoring
shape.
