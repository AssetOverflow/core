# Koine Greek fluency eval lane (Phase 5.3)

## What it measures (v1, honest scope)

Whether the deterministic articulation layer
(`generate/articulation.py`) produces a Greek-script surface in
subject-object-predicate word order when given a (subject,
predicate, object) triple drawn from the
`grc_logos_cognition_v1` / `grc_logos_micro_v1` seed packs.

This is the C01 (simple declarative) gate only.

## Why v1 is C01-only

Identical reasoning to the Phase 5.2 Hebrew lane: the realizer's
tense/aspect/quantifier/negation logic in `generate/templates.py`
and `generate/morphology.py` is English-only.  Greek requires its
own morphology + rhetorical templates before C02–C13 can be
measured honestly.  See `gaps.md` for the v2 unblock path.

## Inputs

`public/v1/cases.jsonl`
:  3 cases — one per triple from the seed packs, all C01.

`dev/cases.jsonl`
:  1 case — smoke check for runner integration.

## Scoring rubric

A case passes if the realized surface:
1. Contains Greek script (U+0370..U+03FF or U+1F00..U+1FFF for
   polytonic)
2. Is in `accept_surfaces` OR satisfies all `constraints`
   (`must_contain`, `max_words`)

## Provenance

Same `realize()` entry point as
`tests/test_articulation.py::test_realize_greek_surface_uses_greek_script_and_compact`,
generalized into a lane with multiple cases and the standard scoring
shape.
