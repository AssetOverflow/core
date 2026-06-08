# CMB lookback review (CMB-a/b/c) — before CMB-d router wiring

**As of:** `main` @ `84d3456e` (CMB-a #650 · CMB-b #653 · CMB-c #654 all merged).
**Trigger:** the mandatory lookback before wiring a multi-rung substrate into shared infrastructure
(CLAUDE.md *Lookback Review Discipline* — "before starting the next phase of a multi-phase ADR" and
"after any 3+ PR sequence on the same surface"). CMB-d wires CMB into the shared
`route_setup` + contemplation + failure-family registry, where any latent CMB-c classification
mistake stops being local.

**Method.** A 5-dimension read-only fan-out audit (one agent per dimension, each reading the source
and running live probes) over a 10-item checklist, plus a synthesis pass. 38 findings: **25 solid /
4 drift / 8 gap / 1 reader hazard** (+ several CMB-d preconditions that are wiring, not CMB-c bugs).

**Verdict: ready for CMB-d once (a) the one reader hazard is fixed [done in this PR] and (b) the
registry preconditions below land in the CMB-d PR itself.**

---

## Provenance note (a false alarm, resolved)

The synthesis pass raised a "live main is CMB-a only; reader/solver are unmerged" alarm. **This is a
stale-local-checkout artifact, not a real finding.** Merges land server-side via `gh`; the *local*
`main` checkout was never pulled, so the synthesis agent's `git` saw an old tree. Verified:
`git cat-file -e origin/main:generate/combined_rate_comprehension/reader.py` → present at
`84d3456e`; `solver.py` likewise. The per-dimension audit agents read the worktree (= the merged
code) and their findings stand. Discount the provenance hazard.

---

## Hazard (1) — fixed in this PR

**H3 · single-agent-attribution over-claims `combine_mode_ambiguous`.** Two same-unit rates with a
query that attributes the answer to **one** agent — *"Alice types 5 words per minute and Bob types 3
words per minute. How many words does **Alice** type in 3 minutes?"* — is a single-rate question
with a distractor rate, not a combined query. The reader claimed the substantive
`combine_mode_ambiguous`; on the shared router (CMB-d) that is a substantive-refusal-on-foreign-text
= a hygiene breach.

**Fix (this PR):** the combined-query gate now excludes a single-agent `does <Agent>` attribution
(`_SINGLE_AGENT_QUERY`), so single-agent text steps aside as `not_combined_rate_shaped`. The
genuinely-combined forms (`… do they …`, `… are produced`, `does it`) still yield
`combine_mode_ambiguous`. Pinned by gold fixture **`cmb-16`** + `test_single_agent_attribution_steps_aside`.

A reader that **steps aside** on ambiguity is safe (wrong=0 preserved); only over-reads to a wrong
answer or substantive-refusals-on-foreign-text are hazards. H3 was the only one. The
comparison-query, sequential-duration, decimal-rate, incidental-drain, and reciprocal step-asides
are all correctly handled (confirmed) and are **not** hazards.

---

## Solid (the substrate that holds)

- **Division of labor (model/reader/solver).** The reader **parses** every solver-boundary setup
  (`eff ≤ 0`, non-integer) and never intercepts a solver-owned refusal — `non_positive_net_rate` and
  `non_integer_solution` appear nowhere in `reader.py`. The model permits `effective_rate ≤ 0` by
  construction; the solver owns it. `run_reader` 11/0/0 + (now) 8 refused-correct; `run_solver`
  6/0 + 5/0. No reader-owned malformed setup reaches the solver (the unit-mismatch guard fires
  before `RateUnit` construction; the model has one unit slot).
- **2×2 domain-entry grid.** All four cells correct; every substantive refusal is gated behind
  positive CMB-shaped evidence (the N6 over-proposing invariant) — `three_or_more_rates` /
  `rate_unit_mismatch` only after a cue; `combine_mode_ambiguous` only with a same-unit combined
  query; `missing_second_rate` only with a cooperative cue + two conjoined agents.
- **Foreign-organ hygiene.** 0 substantive refusals across all 36 R1/R2/R3 gold (every foreign
  fixture → `not_combined_rate_shaped`), and across fresh foreign probes (comparison questions, R1
  arithmetic, R2 prose, R3 single-rate with incidental cue words).
- **Reader correctness (the 3 adversarial-round classes hold).** Difference subtraction is
  semantic-role based (fill = minuend, drain = subtrahend) not text-order; sequential segments step
  aside (incl. loose connectors); decimals don't partial-parse.
- **Off-serving.** No CMB file imports `generate.derivation` / `core.reliability_gate` (AST-checked).
- **Cross-rung composition.** The reader's setups round-trip through the oracle's
  `combined_rate_setup_signature`; the solver consumes exactly the reader's output type; the closed
  taxonomies are consistent across model/reader/solver/oracle.

## Drift / gaps (no current wrong=0 risk; most are CMB-d's to resolve)

- `empty` refusal (blank input) is not in the oracle `READER_REASONS` — unreachable from prose
  routing; add only if a blank-input gold case is ever introduced.
- `_AGENT_CONJ` matches any `word and word` bigram (not just proper-noun pairs); `_LEADIN = 25` is an
  undocumented bound. Both are conservative (a miss → safe step-aside), not hazards.
- The remaining items are **CMB-d preconditions** (below), not CMB-c defects.

---

## CMB-d failure-family classification (the decision)

The load-bearing output. Reasons map to families as:

| Family bucket | Reasons | Rationale |
|---|---|---|
| **input_shape** (no proposal) | `not_combined_rate_shaped` | the step-aside reason — the router-hygiene gate **requires** it be mapped, or every CMB foreign refusal fails the invariant |
| **must_remain_refused** (no proposal) | `rate_unit_mismatch`*, `three_or_more_rates`, `clock_interval_deferred`, `reciprocal_work_rate_deferred`, `non_positive_net_rate` (solver), `non_integer_solution` (solver) | correct wrong=0 boundaries / deferred-capability boundaries, not coverage gaps |
| **proposal_allowed** | `combine_mode_ambiguous`, `missing_second_rate` | genuine, semantically-coherent coverage gaps — fired only **after** positive CMB recognition, and **before** the solver, so neither can emit a wrong answer |

**\* `rate_unit_mismatch` stays `must_remain_refused` for v1 — decisively.** It fires for two
structurally different sub-cases under one code: (A) dimensionally-**incompatible** units
(`rooms/hour` vs `liters/minute` — no conversion exists) and (B) a duration-unit ≠ rate-denominator
case. The reader has **no dimension representation** (`units.py` compares only `(numerator,
denominator)` string equality) and **cannot** distinguish convertible (`gallons/min` vs
`gallons/hour`) from incompatible. Marking it `proposal_allowed` would emit a "try conversion"
proposal for the incompatible case = a wrong=0 hazard if ratified. **Do not** introduce a narrower
`rate_unit_mismatch_convertible` family until the reader gains a dimension registry **and** the two
sub-cases fire under distinct codes **and** a separate conversion gold lane exists.

**Note on `missing_second_rate`:** it is `must_remain_refused`-by-default *and* `proposal_allowed`
in the sense above — it is an *under-specified-input* boundary (no reader enhancement can infer the
missing rate), distinct in kind from the math-impossibility boundaries. The proposal it licenses is
"what is the second agent's rate?", not a rule-learning proposal.

---

## CMB-d risk list (preconditions, to land in the CMB-d PR itself)

These are **live registry** facts verified against `main`; each must be handled in the same PR that
adds `classify_cmb` to `route_setup`:

1. **`not_combined_rate_shaped` is unmapped** in `failure_family.py` (`family_for_reason → None`).
   The moment CMB joins `test_router_organ_hygiene.py`, every CMB foreign refusal fails the
   "must map to `input_shape`" assertion. → add it to the `input_shape` family's `refusal_reasons`.
2. **Shared `rate_unit_mismatch` string collision.** R3 emits the same string → maps to R3's
   `unsupported_rate_duration` **growth** family (`proposal_allowed`, `owner=r3`). A CMB unit-mismatch
   (a hard boundary) would be mis-routed to a wrong-type R3 proposal. → CMB must emit a **distinct**
   string (e.g. `cmb_rate_unit_mismatch`) and register it `must_remain_refused`.
3. **`non_positive_net_rate` is unmapped** → `ContemplationResult.family` silently `None` on a CMB
   solver refusal. → add a `cmb_non_positive_net` family (`must_remain_refused`).
4. **`non_integer_solution` owner mislabel.** The CMB solver shares R2's string → family `owner=r2`.
   → emit a CMB-distinct string or extend the owner to credit CMB.
5. **`Organ` Literal + `ALL_REASONS` lack CMB.** → add `r4_combined_rate` (name TBD) to the `Organ`
   Literal and extend `ALL_REASONS` with every CMB reader+solver reason, or
   `test_registry_covers_the_whole_refusal_surface` won't catch an unregistered CMB reason.
6. **Off-serving assertion.** Add the per-module AST off-serving test for `classify_cmb` (substring
   scans false-negative on docstring mentions).
7. **Exactly-one-`setup_correct` contract.** Re-confirm `route_setup` still selects a unique organ
   when CMB joins — CMB must not make any R1/R2/R3 problem ambiguous, nor claim one (the hygiene
   audit shows it steps aside on all R1/R2/R3 gold, which protects this).

**CMB-d's claim stays narrow:** "CMB participates in routing + typed contemplation without
corrupting R1/R2/R3 or serving." No new capability (that was CMB-c).

---

## Net

The CMB-a/b/c substrate composes cleanly. One real reader hazard (H3) is fixed here with a ruler
fixture + test. The remaining items are CMB-d wiring preconditions, now enumerated with the family
classification resolved. Lane state after this PR: gold **19/19** (6/5/8), reader 11/0/0 + 8
refused-correct, solver 6/0 + 5/0, 0 hygiene breaches, serving + R1/R2/R3 unchanged.
