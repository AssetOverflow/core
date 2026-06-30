# ADR-0176 — Multi-Step Grounded Composition with Question-Targeting

**Status:** Proposed
**Date:** 2026-05-28
**Author:** Shay
**Anchor:** [[thesis-decoding-not-generating]]
**Builds on:** [ADR-0175 — Calibrated Attempt-and-Eliminate Learning](./ADR-0175-calibrated-attempt-and-eliminate-learning.md) (the self-verification gate, the sealed practice lane, the reliability ledger, the elimination/learning loop — all reused here)

---

## Context — the dominant remaining lever

After ADR-0175 Phases 1–3b + the completeness clause, the sealed practice search
flips exactly the single-step-complete case (0021); serving is unchanged at
`3/47/0`. The deterministic microscope (practice eliminations) is unambiguous
about why:

- **79% of the corpus needs multiplication; 0% is single-step; median is 3 steps.**
- The search today proposes **one product per sentence**. Most cases need a
  **chain** of operations where each step's result feeds the next.

Sampling the gold `<<a*b=c>>` derivations shows the shape precisely:

| Case | Gold steps | Notes |
|---|---|---|
| 0021 | `15*10=150 → 3*150=450` | intermediate `150` feeds step 2 |
| 0003 | `48*24=1152 → 1152*0.75=864` | chain; price cue in the question |
| 0024 | `20+36+40+50=146 → 3*146=438` | **mixed** ops (sum then ×); `3` is "three times" |
| 0033 | `12*7=84 → 84/2=42 → 42+5=47 → 25-12=13 → 47+13=60` | 5 steps, mixed ops; `25` is from the **question** |

Three structural truths emerge:

1. **Derivations are chains/DAGs** — intermediate results (150, 1152, 84, 146)
   become operands for later steps.
2. **Quantities come from the body *and* the question** (0033's `25` is in the
   question "when she is 25").
3. **Several steps need comparatives/word-quantities** (`half`→÷2,
   `three times`→×3) — the extraction gap the microscope already flagged
   (0015/0025), now load-bearing.

**Multi-step grounded composition with question-targeting is the capability that
moves the serving number.** It is the genuine hard core of GSM8K solving — not a
plumbing phase. This ADR scopes it.

## Decision

A **bounded, deterministic, target-guided multi-step grounded derivation search**,
gated by ADR-0175's strengthened self-verification gate (grounding ∧ cue ∧ unit ∧
completeness) + uniqueness, plus a new **question-target match**. It runs in the
**sealed practice lane** (wrong tolerated; the learning signal); serving stays
wrong=0 and untouched until a later phase (ADR-0175 Phase 5) ratifies proposals.

The two new ideas beyond ADR-0175:

- **Question-targeting** turns the question into a *target* (unit/entity, an
  aggregation hint like "total", and any question-sourced quantities). The target
  is both the **search-pruning signal** (only pursue chains that can reach the
  target unit) and the **stopping criterion** (a chain is a candidate answer only
  when its result matches the target). This is what makes the search tractable and
  is the difference between "compute something" and "answer the question."
- **Multi-step chaining** — intermediate results become derived quantities
  available to later steps; the chain is gated as a whole.

### Components

1. **Question-targeting (QT).** Parse the question sentence into a `Target`
   (unit/entity + aggregation hint + question-sourced quantities). Reuse the
   existing question extraction (`extract_question_candidates` /
   `CandidateUnknown`) rather than reinvent. Output drives search pruning + the
   stopping criterion.

2. **Multi-step derivation model.** Extend `GroundedDerivation` from a left-fold to
   a **chain with derived intermediates**: each step's result is a new `Quantity`
   (value computed; unit per the op's unit algebra; provenance = "derived", not
   text-grounded) available as an operand to later steps. Text/question operands
   must still ground; intermediates need not.

3. **Target-guided bounded search.** Deterministic enumeration of step-chains over
   {extracted body quantities, question quantities, derived intermediates},
   **bounded** by `MAX_STEPS` and a branching cap (refuse-on-overflow, like
   `MAX_TOTAL_BRANCHES`). **Pruned by the target** (drop chains whose reachable
   result-unit can't match the target) and **guided by cue patterns** (ADR-0175's
   provisional/learned cue→op patterns choose which ops to try).

4. **Gate the whole chain.** ADR-0175 `self_verifies` extended to chains
   (grounding on text operands; cue grounding per step; unit consistency through
   the chain; **completeness** over body+question quantities) **+ question-target
   match** + cross-chain **uniqueness** (a single distinct target-matching answer
   resolves; zero or disagreeing refuse).

5. **Practice measurement + learning.** Run in the sealed lane; measure the
   flip-curve on the multi-step chunk; eliminations feed ADR-0175's
   cue-pattern/reliability learning. Generality guarded by ADR-0114a perturbation.

## wrong=0 obligations (must be *proven*, not asserted)

Extends ADR-0175's invariants to chains; each needs a failing-under-violation test:

1. **Invariant #2 (multi-step).** No chain self-verifies unless every text operand
   is grounded, every step's cue is grounded, units are consistent through the
   chain, it is complete (uses all body+question quantities), and it matches the
   question target — *even if its value coincides with gold*. The spurious
   multi-step test (a coincidental chain that skips a quantity or mismatches the
   target → refused).
2. **Seal (#1).** The search is practice-only; no `generate`/`chat` import; serving
   stays `3/47/0`; 0050 refuses in serving.
3. **Determinism/replay (#3).** Fixed enumeration order + depth cap; byte-stable.
   Bounded (refuse-on-overflow, never unbounded enumeration).
4. **Target-match is necessary.** A chain whose result unit/entity does not match
   the question target cannot resolve (it answered a different question).

## Dependencies (honest)

- **Comparatives / word-quantity extraction** — `half`→÷2, `N times`→×N,
  `twice`→×2, implied counts. The microscope already flagged this (0015/0025) and
  the gold shows it (0024/0033). A small **curated, HITL-ratified comparatives
  pack** supplies these irreducible primitives (per ADR-0175 §10: the engine
  cannot derive "twice = 2" from arithmetic). **Prerequisite for several cases.**
- **Question-quantity extraction** — quantities stated in the question (0033's
  `25`) must be extracted and made available to the search.
- **Cue-pattern learning** (ADR-0175) guides which ops to try; the provisional cue
  set is acceptable to start, refined by practice eliminations.
- **Reuse:** the math solver (multi-op graphs already supported), the round-trip
  grounding primitives, and the existing question extraction.

## Sub-phases (wrong=0-first — gate/target before broad search)

- **MS-1 — Question-targeting.** Extract the `Target` from the question (+ question
  quantities). Tests: target unit/entity/aggregation parsed; question quantities
  surfaced. No search yet.
- **MS-2 — Multi-step model.** Chain with derived intermediates; completeness over
  body+question; chain arithmetic + unit algebra. Tests: a hand-built 0021/0033
  chain computes + self-verifies; an incomplete/target-mismatched chain refuses.
- **MS-3 — Target-guided bounded search.** Deterministic, depth-bounded,
  target-pruned, cue-guided enumeration. Tests: bounded + deterministic;
  refuse-on-overflow.
- **MS-4 — Gate extension + invariant #2-multi-step proof.** The spurious
  multi-step refusal test is the load-bearing deliverable.
- **MS-5 — Practice measurement.** Flip-curve on the multi-step chunk; perturbation
  generality; eliminations → learning. Measure honestly.

## The honest hard part

Multi-step search **explodes combinatorially**, and ADR-0175's uniqueness rule will
**refuse most cases** (many chains self-verify and disagree). That is *safe* but
*low-coverage*. The three levers that make it tractable without sacrificing
wrong=0:

1. **Target-pruning** — only chains reaching the question's target survive
   (collapses the space dramatically; also the stopping criterion).
2. **Cue-guidance** — try ops the learned/provisional cue patterns license, not all
   ops blindly.
3. **Depth bound + refuse-on-overflow** — bounded, deterministic, refuse rather
   than truncate.

Expect **low coverage initially**, climbing as cue-pattern learning sharpens and
the comparatives pack lands. The flip-curve is measured, not promised; coverage
that doesn't hold under perturbation does not count (ADR-0114a). And serving lift
still waits on ADR-0175 Phase 5 (ratification) — this ADR produces the *capability*
and the *practice signal*, not a serving-number change by itself.

## Acceptance criteria (Proposed → Accepted)

1. MS-1/MS-2 land with target extraction + a chain model that self-verifies a
   hand-built multi-step derivation and refuses incomplete/target-mismatched ones.
2. MS-4 proves invariant #2-multi-step (spurious chain refused).
3. MS-5 reports a measured flip-curve on the multi-step chunk with `wrong=0` held
   in serving and flips holding under perturbation.
4. Determinism/replay + seal invariants hold; capability lanes G1–G5/S1 remain
   100% `wrong=0`.

## Cross-references

- **Builds on:** [ADR-0175](./ADR-0175-calibrated-attempt-and-eliminate-learning.md)
  (gate, practice lane, ledger, learning loop, completeness clause).
- **Substrate available:** ADR-0174 `eliminate_violating`/`reevaluate`/`contemplate`
  (could guide chain search — generalize off reading-coupled types first); the
  math solver's multi-op support; `extract_question_candidates`.
- **Comparatives pack:** the curated world-fact primitives (ADR-0175 §10 self-
  proving-vs-pack split; the microscope-flagged 0015/0025/0024/0033 gap).
- **Thesis:** [[thesis-decoding-not-generating]] — comprehend the question, find the
  chain that answers it; do not pattern-match a shape.
