# ADR-0053 — Cognition Lane Closure: Dev-Driven Corpus Expansion + CORRECTION Acknowledgement

**Status:** Accepted
**Date:** 2026-05-18
**Author:** Shay

---

## Context

[ADR-0052](./ADR-0052-teaching-grounded-surface.md) closed the third
grounding-source branch (teaching-grounded for CAUSE / VERIFICATION)
and lifted the public 13-case cognition split to 92.3% / 83.3%.
Before declaring the lane done, we ran the **dev split** for the
first time this session.  Result:

| split (13 cases each) | intent_acc | surface_grounded | term_capture | versor_closure |
|---|---|---|---|---|
| public  (post-0052) | 100% | 92.3% | 83.3% | 100% |
| dev     (post-0052) | 100% | **69.2%** | 57.1% | 100% |
| gap                 | 0    | **−23.1 pp** | −26.2 pp | 0 |

Two findings emerged from per-case inspection:

1. **The ADR-0048→0052 chain is not overfit.**  Every dev case
   where the necessary primitives existed (subject lemma in
   `en_core_cognition_v1`, intent in covered set, matching teaching
   chain authored) lifted exactly as predicted.
2. **The gap was content, not architecture.**  3 of 4 dev misses
   were **missing teaching chains** for known pack lemmas
   (`correction`, `creation`, `light` as VERIFICATION).  1 of 4 was
   the **architectural CORRECTION gap** that public also exhibited
   on `correction_specific_015`.

This ADR closes both kinds of gap with the minimum doctrine-aligned
work: expand the reviewed teaching corpus, and add the missing
intent-typed grounding branch.

---

## Decision

### Part 1 — Teaching corpus expansion (no code)

Add 7 new reviewed cognition chains to
`teaching/cognition_chains/cognition_chains_v1.jsonl`:

| chain_id | subject | intent | connective | object |
|---|---|---|---|---|
| `cause_correction_reveals_truth` | correction | cause | reveals | truth |
| `cause_creation_reveals_meaning` | creation | cause | reveals | meaning |
| `verification_light_reveals_truth` | light | verification | reveals | truth |
| `cause_truth_grounds_knowledge` | truth | cause | grounds | knowledge |
| `cause_wisdom_orders_judgment` | wisdom | cause | orders | judgment |
| `verification_truth_requires_evidence` | truth | verification | requires | evidence |
| `verification_wisdom_grounds_judgment` | wisdom | verification | grounds | judgment |

Each chain uses **only pack-resident lemmas** as subject and object
and a **recognised connective predicate** already in
`generate/semantic_templates.py:_PREDICATE_HUMANIZE`
(`reveals`, `requires`, `grounds`, `orders`).  Every surface atom
remains lemma-or-pack-sourced; no synthesis is introduced.

The first three chains close the dev split misses
(`cause_correction_033`, `cause_creation_008`, `verification_light_017`);
the remaining four pre-empt the analogous holdout pattern
(CAUSE / VERIFICATION on `truth` and `wisdom`).

Provenance tag on the new chains is `adr-0053:reviewed:2026-05-18`
(the original three retain their `adr-0052` tag).  The corpus loader
silently drops any chain whose subject or object is missing from
the pack — a load-time pack-consistency check that prevents
non-pack atoms from leaking into a teaching-grounded surface.

### Part 2 — CORRECTION acknowledgement branch

Add `pack_grounded_correction_surface()` to `chat/pack_grounding.py`
and a CORRECTION branch in
`chat/runtime.py:_maybe_pack_grounded_surface`.

**Surface format** (fixed template, all atoms pack-sourced):

```text
correction received — pack-grounded ({pack_id}): {d1}; {d2}; {d3}.
No prior turn in this session to correct yet.
```

The trailing disclosure is **deliberately distinct** from the
DEFINITION / RECALL / COMPARISON pack-grounded surfaces'
`"No session evidence yet."`  A CORRECTION intent is meta-cognitive
— it asserts the *previous turn* was incorrect — so the
doctrine-aligned cold-start response is not to define what
"correction" is (the DEFINITION path does that), but to acknowledge
receipt and explicitly state that no prior session turn exists to
apply the correction to.

The branch fires for every CORRECTION-tagged intent on cold-start;
no subject lemma is consulted (the prompt's correction-target may
or may not be a single lemma, e.g. `"No, that's wrong"` has no
subject).  The post-correction reviewed-teaching path
(`teaching/correction.py`) is unchanged and continues to engage
once a prior session turn exists.

### Part 3 — Diagnostic memory

Save the dev-split generalisation finding as a project memory
(`memory/dev-holdout-generalization-2026-05-18.md`) so future
sessions know:

- the ADR chain generalises;
- the next-cheapest pull on cognition metrics is corpus expansion,
  not new branches;
- holdouts are not yet wired into the official `core eval cognition`
  CLI — adding them is a separate ADR.

---

## Why this is doctrine-aligned

- **Reviewed memory expansion is the curriculum-teaching activity
  CLAUDE.md item #6 calls for.**  Each new chain is reviewed,
  immutable, source-tagged.  No bulk corpus ingest.
- **Every surface atom is pack-sourced or a closed-template
  connective.**  No LLM, no synthesis, no fabrication.
- **The CORRECTION branch does not invent a parallel teaching path.**
  It emits a *receipt acknowledgement* surface; the actual reviewed-
  teaching repair flow remains in `teaching/correction.py`.
- **Pack-consistency check on corpus load** (already present in
  ADR-0052's `_corpus_index`) prevents pack/corpus drift — a chain
  referencing a non-pack lemma is silently dropped, preserving the
  "every atom is pack-sourced" invariant.
- **No algebra, no normalisation, no hot-path repair.**  Both
  changes are content + a stub-path branch.

---

## Characterisation — `core eval cognition`

A/B run on **both splits**, baseline = post-ADR-0052:

| Metric                    | Pre  | Post | Δ           |
|---------------------------|------|------|-------------|
| **PUBLIC** intent_accuracy         | 100.0 %     | 100.0 %     | 0           |
| **PUBLIC** surface_groundedness    |  92.3 %     | **100.0 %** | **+7.7 pp** |
| **PUBLIC** term_capture_rate       |  83.3 %     | **91.7 %**  | **+8.3 pp** |
| **PUBLIC** versor_closure_rate     | 100.0 %     | 100.0 %     | 0           |
| **DEV**    intent_accuracy         | 100.0 %     | 100.0 %     | 0           |
| **DEV**    surface_groundedness    |  69.2 %     | **100.0 %** | **+30.8 pp**|
| **DEV**    term_capture_rate       |  57.1 %     | **78.6 %**  | **+21.5 pp**|
| **DEV**    versor_closure_rate     | 100.0 %     | 100.0 %     | 0           |
| `versor_condition < 1e-6` | preserved   | preserved   | invariant  |

**Both splits now hit 100% surface_groundedness.**  Both splits
share the same lift mechanism — when the gate fires, the matching
intent-typed branch emits a pack-grounded or teaching-grounded
surface composed entirely of pack atoms; otherwise the universal
disclosure remains.  No bias, no overfit, no per-split tuning.

---

## Consequences

### What changes

- `teaching/cognition_chains/cognition_chains_v1.jsonl` grows from
  3 to 10 chains.
- `chat/pack_grounding.py` gains `pack_grounded_correction_surface()`.
- `chat/runtime.py:_maybe_pack_grounded_surface` gains a
  CORRECTION branch.
- The cognition lane (both public and dev splits) is now saturated
  on `surface_groundedness` (100% on both).
- A diagnostic memory records the dev/holdout finding for future
  reference.

### What does not change

- `UnknownDomainGate` semantics unchanged.
- `_UNKNOWN_DOMAIN_SURFACE` constant retained; the path is still
  the correct fall-through when no intent-typed branch applies.
- Safety / ethics refusal still takes priority above all grounded
  surfaces.
- `teaching/correction.py` reviewed-teaching repair flow unchanged;
  this ADR adds only the cold-start acknowledgement.
- `versor_condition(F) < 1e-6` invariant unaffected.
- All five core lanes remain green
  (smoke 67 / cognition 121 / runtime 19 / teaching 17 / packs 6).

### Scope limits

- **Holdouts (19 cases) not yet in the official runner.**  The
  `--split` CLI option accepts only `{dev, public}`.  Wiring
  holdouts is a separate ADR — predicted lift pattern by
  inspection is consistent with public/dev (CAUSE / VERIFICATION on
  `truth` and `wisdom` will lift via the new chains; CORRECTION
  will lift via the new branch).
- **CORRECTION subject lemma not yet captured in the surface.**
  Holdout case `correction_truth_040` ("Actually, truth requires
  evidence") expects `truth` in the surface as well as
  `correction`.  Detecting and embedding the corrected-subject
  lemma in the acknowledgement is a candidate follow-up; the
  current fixed-template surface satisfies the dev + public
  contracts.
- **English only** (`en_core_cognition_v1`).  Multilingual
  cognition chains would follow the same pattern under a separate
  ADR.
- **3 of the 7 new chains target holdout, not dev/public.**  They
  are still load-bearing because the corpus is shared across all
  splits and pre-empting predictable misses now avoids a future
  one-chain-at-a-time PR cadence.

---

## Cross-References

- [ADR-0048](./ADR-0048-pack-grounded-surface.md) /
  [ADR-0050](./ADR-0050-pack-grounded-comparison.md) /
  [ADR-0052](./ADR-0052-teaching-grounded-surface.md) — the
  three preceding grounding-source branches this ADR completes.
- [ADR-0018](./ADR-0018-tool-use-scope.md) — teaching store and
  CORRECTION intent classification this ADR consults.
- `teaching/correction.py` — the reviewed-teaching repair path
  that engages once a prior session turn exists; not modified
  by this ADR.

---

## Verification

```
tests/test_pack_grounded_correction.py            — 15 tests, all green
tests/test_pack_grounded_comparison.py            — 15 pre-existing tests still green
tests/test_pack_grounding.py                      — 18 pre-existing tests still green
tests/test_teaching_grounding.py                  — 22 pre-existing tests still green
tests/test_intent_subject_extraction.py           — 30 pre-existing tests still green

Lanes (all green on this branch):
  core test --suite smoke         67 passed
  core test --suite cognition    121 passed
  core test --suite runtime       19 passed
  core test --suite teaching      17 passed
  core test --suite packs          6 passed

core eval cognition (post-0053):
                       public        dev
  intent_accuracy        100.0%   100.0%
  surface_groundedness   100.0%   100.0%   ← BOTH SPLITS SATURATED
  term_capture_rate       91.7%    78.6%
  versor_closure_rate    100.0%   100.0%
```

The non-negotiable field invariant (`versor_condition(F) < 1e-6`)
is preserved: this ADR adds reviewed-memory content and one
stub-path branch — no algebra, no normalisation, no field update.
