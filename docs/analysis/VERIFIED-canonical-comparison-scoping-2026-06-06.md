# Scoping: the `VERIFIED` canonical-comparison producer (the real math-serving unlock)

**Date:** 2026-06-06 · **Status:** scoping (no code) · **Unblocks:** the ADR-0206 §5
math-serving widening (the seam is built + inert; this is the gate it waits on).

## The gap

`select_self_verified` proves **soundness** — grounding ∧ cue ∧ unit ∧ uniqueness — and
refuses on disagreement. It does **not** prove **correctness**: that the committed value
is the right answer to the question. Serving has **no gold**, so correctness can't be
checked by comparison to an answer key. `EpistemicState.VERIFIED` is reserved precisely
for the capability that closes this gap, and it is "the only state that will license
widening past gold" (ADR-0206 §4). Until a producer exists, the math seam stays inert and
the absolute `wrong == 0` is safe.

## Why a statistical license can't substitute

A reliability license (Step E) is a Wilson lower bound — it permits the *cognition* path
to serve a **disclosed** estimate. Math answers aren't disclosed; a licensed-but-wrong
math serve is a *silent* wrong. The absolute invariant needs **absolute** evidence, not a
0.99 bound. So `VERIFIED` must be a *proof of correctness*, not a confidence score.

## Candidate mechanisms (in order of promise)

1. **Back-substitution / constraint satisfaction (recommended first target).** For a
   problem reducible to a constraint system over its *stated* quantities, plug the
   candidate answer back in and verify it satisfies every constraint. This is a genuine
   correctness check **without gold** — it decides truth against the problem's own
   structure ("decode a reality that already is", the canonical-form thesis). Well-posed
   for a constraint-bearing subset (e.g., "x of the N are red, the rest blue; how many
   blue?" → answer must satisfy red+blue=N). The binding constraint is the same
   comprehension wall (word → constraint system), so scope it to shapes the reader already
   extracts cleanly.
2. **Independent canonical re-derivation.** Stronger than today's disagreement rule:
   require K *structurally disjoint* derivations to converge on the same canonical normal
   form. Caveat — convergence is still evidential, not a proof; this raises confidence but
   does **not** by itself justify `VERIFIED` for an absolute invariant. Use only as a
   *necessary* pre-filter, never the sole gate.
3. **Reuse a domain where correctness is decidable.** Deductive logic already produces
   proven-correct answers (the sound+complete ROBDD — [[project-deductive-logic-flagship]]).
   That is the existence proof that `VERIFIED` is real; but it flows through the logic
   path, not `select_self_verified`. A bridge would let logic-checkable arithmetic
   sub-claims earn `VERIFIED`.

## Recommended arc (each its own PR, wrong=0-gated)

1. **Contract.** Define `VERIFIED`'s canonical-comparison obligation: a predicate that,
   given a candidate `Resolution` + the problem, returns proven-correct / not — with a
   *meaningful-fail* test (it must reject a sound-but-wrong answer, the `20/5==4` class).
2. **Producer for ONE checkable class** (back-substitution over a constraint-bearing
   shape). Emit `EpistemicState.VERIFIED` only when the back-substitution check passes.
3. **Wire** `_canonically_verified` (the seam's gate, already built + tested) to that
   producer. The math seam then widens for exactly that class — and only it.
4. **Re-pin** the serving-lane SHAs under the freeze (the deferred `reach_level` emission;
   ADR-0206 §5) — re-pinning a frozen gate is a deliberate, reviewed act, with the eval
   delta as the truth test (sealed run must show wrong=0 preserved + the new served class).
5. **Independent oracle** on a holdout (INV-25 discipline): the widened class must hold
   wrong=0 against a *separate* gold lane, not just the back-substitution check.

## Honest risk

The hard part is comprehension (word → constraints), not the check. So the first producer
should target the *narrowest* shape the reader extracts reliably, proving the mechanism
end-to-end (build → emit VERIFIED → seam widens → wrong=0 holds on holdout) before
widening the shape coverage. This is the "checkable-conclusion domains" direction
([[project-self-check-soundness-not-correctness]]) made concrete for math serving.

## Empirical verdict (2026-06-06) — DO NOT BUILD the fold-reader certifier

A validate-first probe killed the back-substitution / pure-chain-certifier idea on the
independent holdout, BEFORE any build:

- The serving `verify` (`math_verifier.verify`) is **solver-replay soundness**, not
  correctness — it proves the solver executed the graph faithfully, NOT that the *parse*
  (text→graph) is right. wrong=0 holds by the candidate-graph parser's conservative refusal.
- **No independent second reader helps.** On the refused set the R1 graph reader covers
  `0/44` (train_sample) — it is *nested* in candidate-graph, not complementary. Cross-reader
  agreement → 0 flips.
- The fold-derivation reader IS complementary but **unsafe**: on `holdout_dev` it answers
  89 of the 495 refused cases at **2 correct / 87 WRONG**. The train_sample looked like
  3 correct / 7 wrong — **overfit**.
- A pure-chain certifier (admit when no unhandled-structure cue: profit/per/%/more-than/…)
  splits the holdout fold-answers into **1 correct / 37 WRONG (admit)** vs 1/50 (refuse).
  It would **admit 37 wrong answers** — a wrong=0 breach. The mis-reads carry no shallow
  structural signature; separating the 2 correct from the 87 wrong *is* the comprehension
  problem. A certifier strict enough to reject all 87 rejects the 2 too.

**Conclusion:** the VERIFIED-for-arithmetic producer via the existing readers is **not
buildable at wrong=0**. Math serving is **comprehension-bound**: the candidate-graph parser
refuses what it cannot model, and the only complementary reader is ~98% wrong on those. The
ADR-0206 §5 math seam correctly stays **inert**; the real lever is the general COMPREHEND
organ (helps every domain), not a narrow GSM8K certifier. Re-open only if a genuinely
complementary, independently-validated reader lands. Probe: `resolve_pooled` vs
`_score_one_candidate_graph` over `evals/gsm8k_math/holdout_dev/v1/cases.jsonl`.
