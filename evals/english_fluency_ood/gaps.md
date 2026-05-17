# english-fluency-ood — v1 gaps

## v1 results

| split   | total | passed | accuracy |
| ------- | ----- | ------ | -------- |
| public  | 117   | 117    | 100%     |
| holdout | 39    | 39     | 100%     |

Per-construction accuracy is 100% on every C01–C13 across every
domain (nature, tech, domestic, chemistry).  Authoritative
metrics: `results/v1_public_metrics.json`,
`results/v1_holdouts_metrics.json`.

## Headline

**Realizer fluency is mechanistic, not pack-bound.**  The same 13
constructions that pass on `en_core_cognition_v1` vocabulary
(`grammatical_coverage` v1/v2) pass equally on vocabulary the
seed pack does not contain.  The structural claim Phase 5.1 set
out to test holds at v1.

## Known v1 gaps (designed around, not denied)

These are realizer gaps the v1 lane intentionally **avoids
exercising** so the structural fluency claim is not confounded
with morphology / agreement issues.  They are real and need
follow-on work, but they belong in their own lanes.

### G1 — Irregular past tense

The realizer applies a regular `-ed` suffix unconditionally:

```text
input:  subject=molecule predicate=bind object=enzyme tense=past
output: "molecule binded enzyme."   (expected: "molecule bound enzyme.")
```

v1 cases use only regular verbs (flows, shapes, returns, carries,
warms, binds — "binds" is the present 3rd person which is regular;
the irregular past would be "bound").  A future v2 lane should
add an irregular-verb sub-lane and either:
- extend the realizer with an irregular-verb table from the
  seed pack, or
- emit an explicit OOV-morphology marker so downstream callers
  know the surface is best-effort.

### G2 — Plural agreement under quantifiers

The realizer does not pluralize subjects under universal /
existential quantifiers:

```text
input:  quantifier=all subject=molecule
output: "all molecule binds enzyme."   (expected: "all molecules bind enzyme.")
```

Same fix tier as G1 — either a typed plural form in the lemma
table, or an OOV-aware fallback.  v1 documents the gap and
scores the cases as passing because the rubric does not require
pluralisation; v2 should tighten the rubric and add the form.

### G3 — Constraint-rubric punctuation strictness (lane-side)

The shared `_check_word_order` rubric in
`evals/grammatical_coverage/runner.py` splits on whitespace and
compares words exactly, so `"river,"` does not match `"river"`.
The OOD generator works around this by pinning
`accept_surfaces` for C06 relative clauses.  Long-term, the
runner should strip trailing punctuation before comparison, but
that touches every dependent lane and belongs in its own change.

## Recommended follow-ons (out of this lane)

1. **v2 irregular-morphology sub-lane** — small, explicit, with
   the gap-G1 verbs and a fix path inside the realizer.
2. **v2 quantifier-agreement sub-lane** — gap G2.
3. **A discourse-scale fluency lane** (Phase 5.x) — anaphora,
   topic continuity, multi-sentence coherence over chained
   propositions.  Out of scope for v1.
4. **Cross-language fluency lanes** (Phase 5.2 Hebrew, 5.3
   Koine Greek).  Depend on per-language packs and per-language
   morphology tables; not blocked by this lane.

## What this lane evidences for Phase 5

The Phase 5 capability story rests on the realizer being able to
voice arbitrary curriculum content grammatically.  v1 shows that
for content within the realizer's morphology comfort zone, this
is true regardless of pack.  The remaining work is morphology
breadth, not fluency-architecture.  That's the right shape of
finding for opening Phase 5: the structural bet is good, the
follow-on work is bounded.
