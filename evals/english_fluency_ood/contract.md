# english-fluency-ood eval lane (Phase 5.1)

## What it measures

Whether the deterministic realizer remains grammatical when the
(subject, predicate, object) vocabulary is **out of distribution**
relative to the `en_core_cognition_v1` semantic seed pack.  Phase
3 `grammatical_coverage` v1/v2 used pack-aligned vocabulary
(truth, knowledge, wisdom, etc.); this lane substitutes
vocabulary from four pack-absent domains:

- **nature**: river, wind, cloud, valley, dune, ridge
- **tech**: server, packet, signal, database, cable, record
- **domestic**: train, coffee, chair, station, cup, room, lamp
- **chemistry** (holdouts): molecule, atom, reaction, bond,
  enzyme, compound

If the realizer's fluency is mechanistic — templates over typed
graph nodes — then OOD vocabulary should pass the same syntactic
gates as pack vocabulary did at `grammatical_coverage` v1/v2.

If fluency is silently pack-bound (lemma lookup, normalisation,
re-routing), OOD inputs would degrade.

## Target constructions

Same 13 constructions as `grammatical_coverage` (C01–C13).  Each
construction is exercised on every (domain, item) triple in the
case set, so the per-construction score is N_domains × N_items.

## Predicates chosen to isolate the structural claim

OOD predicates are intentionally **regular verbs**
(flows, shapes, covers, returns, carries, stores, passes, warms,
lights, binds, forms, produces).  This keeps the lane focused on
structural fluency rather than English morphology: the realizer's
default `-ed` / `-ing` / `-s` rule applies cleanly.  Irregular
predicates (run/ran/run; bind/bound/bound) would conflate two
distinct gaps and are noted in gaps.md as a separate concern.

## Scoring

Delegated to `evals.grammatical_coverage.runner.run_lane`.  The
same rubric (`accept_surfaces` exact match OR all `constraints`
satisfied) applies.  Per-construction accuracy is reported.

## Phase 5 discipline

- Public/holdout split.  Holdouts use the **chemistry** domain,
  whose vocabulary the public split never sees.
- No threshold beyond the structural gate: every construction
  should pass at 100% if the structural claim holds.  Failures
  per construction are the diagnostic, not a sliding accuracy
  bar.
- Replay determinism is implicit: the realizer is pure-function
  per case; running the lane twice produces identical surfaces.

## Frontier baseline

Frontier LLMs are not the comparison here.  A frontier model
prompted with the same PropositionGraph and asked for a
surface will produce grammatical English at this scale —
that is its native capability, not a structural test.  CORE's
load-bearing claim is **determinism + provenance**: same input,
same output, traceable to the template that produced it.  The
frontier-structural-zero baseline therefore captures the lack
of an analogous typed surface, not an accuracy comparison.

## What this lane does NOT measure

- Morphology beyond what regular verbs need (irregular past
  tense, plural agreement under quantifiers).  Documented as
  known v1 gaps in gaps.md.
- Discourse-scale fluency (paragraphs, anaphora resolution
  across sentences, topic continuity).
- Non-English fluency (Phase 5.2+ lanes).
- Semantic appropriateness of the OOD predicates (e.g.
  "cloud flows valley" is grammatical but agronomically odd —
  this lane scores syntax, not world model).
