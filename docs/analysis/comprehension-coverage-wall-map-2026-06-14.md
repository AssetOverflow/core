# Wall map: the recognizer/coverage wall is COMPOSITION

**Date:** 2026-06-14
**Status:** diagnostic map (the real capability lever, per the C decision — point at
the recognizer/coverage wall). Evidence: committed refusal taxonomy + live lane runs
+ 3× prior empirical confirmation (ADR-0191/0192/0193 milestones).
**Bottom line:** more single-shape recognizers are **proven metric-inert.** The wall
is that shape-recognizers do not **compose** within a compound statement or across
statements with coreference. The capability gain lives in compositional reading,
not in widening any one shape.

## Evidence

### 1. GSM8K diagnostic — the composition signature
`train_sample` serving: **4 admitted / 0 wrong / 46 refused** (8% admission). The
curated refusal taxonomy (`refusal_taxonomy_v3.json`, 50 cases) shows **no single
barrier exceeds 5/50 (10%)** and the barriers are fragmented across ~24 primary
categories:

```
primary_barrier (top):  compound_statement 5 · novel_initial_form 5 ·
  novel_initial_verb 4 · fraction_operand 4 · conditional_question 3 ·
  context_filler 3 · compound_comparative 3 · rate_price 2 · … (long 1-2 tail)
secondary_barriers (co-occurring): compound_comparative 5 · percentage_of 5 ·
  fraction_operand 4 · rate_price 4 · multi_step_complex 4 · rate_comparative 4 ·
  coreference_pronoun 3 · …
```

The secondaries are the tell: refused cases **stack 3-4 structures at once**
(a compound statement *with* a comparative *and* a fraction operand *and* a pronoun
coreference). The two raw refusal modes confirm it:
- `recognizer matched but produced no injection` (majority) — the category is
  recognized (`discrete_count_statement`, `rate_with_currency`,
  `multiplicative_aggregation`, …) but the injection layer can't structure the
  *composed* sentence.
- `no admissible candidate` — the composed shape isn't recognized at all.

### 2. Capability lanes are narrow curated-gold conformance, not open coverage
- `evals/combined_rate_oracle`: **19/19 valid**, `by_expect = {solved: 6,
  solver_refuses: 5, reader_refuses: 8}` — the combined-rate reader handles exactly
  **6 solvable shapes**; everything else it correctly refuses. It is an *oracle*
  (does the reader match the curated gold), not a coverage measure.
- `evals/comprehension/*`: per-domain conformance runners (propositional, syllogism,
  set-membership, total-ordering, relational metric/predicate) — the flagship
  deductive lanes, each 100%-conformant to a curated gold.

So each capability is a **shape-specific reader at 100% of a small gold.** Capability
= gold scope. The readers are individually correct and individually narrow.

### 3. Single-shape widening is metric-inert (already proven 3×)
ADR-0191/0192/0193 confirmed empirically that adding one operator/recognizer is
metric-inert on the real corpus — because the refused cases need *composition*, not
one more shape. This map's barrier data is the fourth confirmation.

## Diagnosis

The wall is **compositional reading**: the organ recognizes individual structures
(rate, fraction, comparative, count, percentage, coreference) but cannot **compose**
them — combine multiple recognized sub-structures within one compound clause, and
carry referents across statements. Real GSM8K problems are compositions; the readers
are a bank of isolated shape-recognizers. That is why admission caps at ~8% and why
every single-shape fix has been inert.

## Leverage (two tiers, honestly)

- **Tier 1 — near-term recognizer coverage (small, capped):** the pure
  *single-barrier* misses (`novel_initial_form`/`novel_initial_verb` and a few
  unrecognized rates/temporals like "Every week, he gets 6 cards", "Mark does a gig
  every other day for 2 weeks") can be admitted by adding their recognizers. Honest
  estimate: **~+5 cases** (4→~9/46), then it hits the composition wall hard, because
  the remaining ~37 refused cases carry *multiple* co-occurring barriers that one
  recognizer doesn't clear.
- **Tier 2 — compositional reading (the real lever):** a layer that **composes**
  recognized sub-structures within a compound statement and **resolves coreference**
  across statements, so a sentence that is rate+comparative+fraction+pronoun reads as
  one composed structure. This is the only path past ~10/46, and it is an
  architectural build (not a recognizer addition). It must preserve wrong=0 (a
  composed reading still passes the self-verification/disagreement gate).

## Recommendation

**Do not pour effort into more isolated shape-recognizers — it is proven inert.**
The capability gain is Tier 2 (compositional reading). Tier 1 is a small honest
warm-up at best; I would not lead with it.

Tier 2 is make-or-break and the solution space is wide (how to compose, where the
composition layer sits relative to extract/clauses/compose, how coreference is
resolved deterministically, how composed readings stay wrong=0). That warrants a
**design effort** — multiple independent architecture attempts, judged and
synthesized — before any build. Proposed as the next step, on sign-off.
