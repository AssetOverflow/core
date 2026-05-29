# ADR-0177 — Cue-Precision Learning: from practice eliminations to trusted cue→op patterns

**Status:** Proposed
**Date:** 2026-05-28
**Author:** Shay
**Anchor:** [[thesis-decoding-not-generating]]
**Builds on:** [ADR-0175 — Calibrated Attempt-and-Eliminate Learning](./ADR-0175-calibrated-attempt-and-eliminate-learning.md) (the reliability ledger + `conservative_floor` + θ ceilings + the sealed practice loop — reused, keyed by cue-pattern) and [ADR-0176 — Multi-Step Composition](./ADR-0176-multistep-composition-question-targeting.md) (the search whose gold-checked candidate chains are the training signal)

---

## Context — the lever MS-1→MS-3 proved, and the honesty it forces

The multi-step search (MS-3) is built, deterministic, and wrong=0-safe, but
**low-coverage by design**: when several arithmetic shapes self-verify and
disagree, the uniqueness rule refuses, because broad cues cannot tell which
operation the text actually licenses. The lever, repeatedly, is **cue precision**:
learning, from the practice eliminations, which `(cue → op)` readings are reliable.

ADR-0175 §"Phase 3b finding" already named the prerequisite: self-verification is
**necessary but not sufficient** (9/13 self-verified attempts were wrong). Before
Phase 5 may let self-verification gate proposals, the gate must be made *sufficient*
— and that is exactly what a learned cue-pattern reliability provides.

This ADR scopes that learning. It is the **self-supervised ("learn-from-questions")**
half of the learning system; the **packs** half (comparatives, superordinate units)
supplies the irreducible world-facts (ADR-0175 §10).

### Two distinct gaps the eliminations expose

The MS-3 eliminations are *not* uniformly "wrong cue→op." Profiling them:

- **Gap A — cue→op precision.** Given a present cue, which op does it license *here*?
  "for 10 reps" → multiply; "works for 3 hours" → not. "and" → sometimes sum,
  sometimes mere conjunction. (0021: "for"→multiply was right.)
- **Gap B — compositional structure.** *Which* quantities group, in what order/op
  tree. The dominant MS-3 failure: product-of-**all** when the answer needs a
  sub-grouping or a mixed chain (0019 `120000` vs `660`; 0041 `2048` vs `6`). The
  op may be right; the *structure* is wrong.

Cue-precision is **Gap A**. It is necessary but, on its own, does not close Gap B.

## The mechanism

A **per-cue-pattern reliability ledger** (reusing ADR-0175's `ClassTally` +
`conservative_floor`, keyed by a cue-pattern string instead of a capability axis),
fed by gold-labeling the search's candidate chains in the sealed practice lane.

**Pattern key:** `(cue, op, unit_shape)` where `unit_shape ∈ {cross_unit, same_unit}`
— e.g. `("per", multiply, cross_unit)`. The `unit_shape` dimension captures the most
load-bearing precision (cross-unit multiplication is the *aggregate* signal)
without the instant starvation of keying on full operand-unit pairs. Finer context
(neighbouring lexemes) is a scale-dependent refinement, not v1.

**Credit assignment (per-case, contrastive via gold):** for each practice case,
the search emits candidate chains; label each by gold (value == answer); for every
step's pattern in a chain, record `+correct` if the chain matched gold else
`+wrong`. Reliability per pattern = `conservative_floor(correct, correct+wrong)`.
The pessimistic floor + `N_min` suppress the noise of coarse attribution (a pattern
earns trust only after many clean appearances). Learning does **not** depend on the
search *resolving* — it learns from labelling candidates, separate from the
resolve/refuse decision.

**Three uses, increasing risk:**

- **U1 — self-verification *trust* (the near-term value).** A chain may produce a
  *serving* proposal only if every step's cue-pattern reliability ≥ `θ_serve`. This
  makes self-verification **sufficient** (closes the ADR-0175 3b gap). With a cold
  ledger nothing clears `θ_serve` → no proposals → **safe**: it prevents the 3b
  "propose junk 70% of the time" disaster by construction. Its value is *correctness/
  trust*, not coverage.
- **U2 — search guidance.** Prefer/try high-reliability patterns first; deprioritise
  unproven shapes. Reduces wrong attempts. Refuse-preferring (pruning a right-but-
  unproven shape only costs coverage, never wrong=0).
- **U3 — disagreement resolution (the coverage lever).** When shapes disagree,
  resolve to the one whose patterns *decisively dominate* in reliability instead of
  refusing — **hard-gated**: only when the winner ≥ `θ` AND beats the alternatives by
  a margin; ties and near-ties refuse. Relaxes uniqueness using *earned evidence*,
  not a guess. Sealed practice checks it against gold; serving additionally requires
  ratification (Phase 5).

## The bottleneck — why cue-precision cannot stand alone yet (the load-bearing honesty)

A cue-pattern earns **positive** signal only from a chain that **matches gold**. On
the current blunt shapes (product-of-all / sum-of-all), only ~4 of 50 cases produce
a gold-matching candidate chain. The other ~43 produce only wrong chains, so:

1. **The ledger is starved of positive signal** — dominated by `+wrong`. Almost no
   pattern reaches `N_min` of *clean* appearances → reliabilities stay near zero →
   U1 trusts nothing, U3 resolves nothing. The mechanism runs but learns little.
2. **Structure failures (Gap B) pollute cue→op credit** — a `(cue, multiply)` whose
   op was *right* but appeared in a product-of-*all* chain that was structurally
   *wrong* gets `+wrong`. Coarse attribution conflates Gap A and Gap B, so a correct
   op is penalised for a structure error.
3. **Data starvation** — 50 cases, each cue appearing in a handful → even uncorrupted,
   the counts are far below `N_min`. Compounding needs **volume**.

**Consequence — cue-precision is tightly coupled to richer compositional shapes
(Gap B) and to scale.** Patterns can only earn reliability once the search can
produce gold-matching chains for them; that requires richer, *guided* shapes (Gap B).
And richer shapes explode combinatorially without cue-precision to prune them. They
**co-evolve**: Gap B supplies gold-matching candidates → cue-precision earns signal →
cue-precision prunes Gap B's search. Neither standalone closes coverage on the
current substrate.

## Recommended sequencing (the honest answer)

1. **Build the cue-precision substrate now (CP-1, CP-2 = U1).** The *mechanism* + the
   **self-verification trust gate**. Near-term value is **correctness**: it makes the
   Phase 5 proposal gate honest (only earned-reliability patterns may propose; cold
   ledger ⇒ refuse), permanently closing the 3b "necessary-not-sufficient" hazard.
   Low risk, no coverage promise.
2. **Then richer guided compositional shapes (Gap B, a sibling to ADR-0176 / its own
   ADR), pruned by the cue-precision ledger.** This is what produces gold-matching
   chains for more cases → gives cue-precision positive signal → and is the actual
   **flip-count** lever.
3. **Scale (more practice problems, ADR-0163 §Phase F)** is what makes the learning
   *compound*. On 50 cases this is mechanism-demonstration, not payoff.

So: cue-precision learning is the **trust substrate and the pruning engine**, not the
coverage unlock by itself. Coverage = Gap B (richer guided search) × scale, with
cue-precision as the safety gate and the prune.

## wrong=0 obligations (must be *proven*, not asserted)

Each needs a failing-under-violation test (CLAUDE.md §Schema-Defined Proof Obligations):

1. **Cold ledger ⇒ no regression.** With an empty/low ledger, U1 trusts nothing and
   U3 resolves nothing — behaviour identical to today's refuse-on-disagreement. A
   test fails if a cold ledger resolves a previously-refused disagreement.
2. **Ties refuse.** U3 with two patterns at equal (or within-margin) reliability +
   disagreeing chains → refuse. A test fails if a tie resolves.
3. **θ-gated serving.** No pattern below `θ_serve` may contribute to a serving
   proposal; serving stays `wrong=0`; the search stays sealed (no serving import).
4. **Credit noise cannot flip a served answer.** The conservative floor + `N_min` +
   margin + ratification (Phase 5) gate it; the ADR-0175 **gold tether** audits
   per-pattern reliability against gold and contracts appetite on divergence.
5. **Determinism/replay.** Ledger updates, the floor, and the tiebreak are
   deterministic; byte-stable across runs.

## Sub-phases

- **CP-1 — cue-pattern ledger + credit assignment.** `(cue, op, unit_shape)` ledger;
  per-case gold-labelling of candidate chains → per-pattern counts. Sealed practice.
  Tests: credit attribution; determinism; cold-ledger reliabilities are 0.
- **CP-2 — self-verification trust (U1) + search guidance (U2).** A chain proposes
  only if its patterns clear `θ`; the search orders/prunes by reliability. Tests:
  invariant #1 (cold ⇒ no proposals, no regression); U2 never causes a wrong=0
  violation.
- **CP-3 — disagreement resolution (U3), wrong=0-first.** Margin+θ-gated resolution;
  **prove ties refuse before enabling resolution.** Measure any coverage delta.
- **CP-4 — measurement + scale dependency.** Per-pattern reliability table; the
  (data-starved) compounding curve; honest report that flip-count payoff awaits
  Gap B + scale.

## Acceptance criteria (Proposed → Accepted)

1. CP-1/CP-2 land; invariant #1 (cold ⇒ no regression) and θ-gating proven; serving
   `wrong=0` unchanged; the self-verification *trust* gate is demonstrable (a chain
   with earned patterns proposes; one without refuses).
2. CP-3 proves ties/near-ties refuse before any reliability-based resolution.
3. Determinism/replay + seal invariants hold; capability lanes G1–G5/S1 stay 100%
   `wrong=0`.
4. The measurement honestly reports the data-starvation/Gap-B bottleneck rather than
   a coverage claim the 50-case substrate cannot support.

## Cross-references

- **Substrate:** [ADR-0175](./ADR-0175-calibrated-attempt-and-eliminate-learning.md)
  (`ClassTally`, `conservative_floor`, θ ceilings, gold tether, the sealed practice
  lane) — reused, keyed by cue-pattern.
- **Signal source:** [ADR-0176](./ADR-0176-multistep-composition-question-targeting.md)
  (`search_chain` candidate chains, gold-labelled in practice).
- **Co-requisite (the flip lever):** richer *guided* compositional shapes (Gap B) —
  a follow-on ADR; cue-precision prunes its search and learns from its gold-matching
  chains.
- **Scale:** ADR-0163 §Phase F — the volume that makes the loop compound.
- **Thesis:** [[thesis-decoding-not-generating]] — the engine learns which readings
  are true by elimination against gold; it is not handed a library of founds.
