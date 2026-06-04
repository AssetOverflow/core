<!-- CANONICAL | docs/analysis/pivot-to-deductive-logic-2026-06-04.md | 2026-06-04 | strategy/post-mortem | why we left the GSM8K chase, what went wrong, and the deductive-logic path we are now on | verified: deductive holdout 500/500 wrong=0, deterministic 3,000-case engine-vs-oracle fuzz (2,796 definite) 0 disagreements -->

# The pivot to deductive logic — what went wrong, and the path now

This is the load-bearing record of a strategic correction. It documents (1) the
GSM8K capability chase and exactly how it misled us for weeks, (2) the measurement
that exposed the truth, (3) why the terrain was wrong for CORE, and (4) the
deductive-logic direction we are now on, with the plan and the disciplines that keep
us honest. Read this before resuming capability work.

---

## 1. What we were doing, and what went wrong

**The goal:** lift CORE's GSM8K (grade-school math word problem) accuracy off zero
while holding the prime directive `wrong = 0` (refuse rather than confabulate).

**The mistake — a ruler that could not measure.** Development was scored on
`train_sample` — the **50 cases the grammar was hand-built against**. Tuning against
those 50 produced "lift" with **no predictive validity**: it was overfit to the exact
problems being optimised. Worse, it hid a real defect.

**The breach.** The first real **sealed** measurement (the full 1,319-case GSM8K test
split, decrypted and run by the operator, never read by Claude) showed serving was
**`0 correct / 5 WRONG / 1314 refused`** — a live `wrong = 0` **breach**. The five
wrong answers were `product_bridge` promoting the derivation composer's confabulations
to serving. This had been invisible *for weeks* behind the 50-case ruler, which
reported a clean `wrong = 0` the whole time.

**The cost.** Time and tokens were spent making the system *worse* (wiring an unsound
reader into serving) while believing it was improving, and the work was shown to
outside professionals as progress. That is the failure this document exists to prevent
recurring.

**Immediate remediation (done):** the unsound committing bridges (`product_bridge`,
`goal_residual`) were disabled; sealed re-confirmed `0 / 0 / 1319` — back to the honest
refusal floor with zero confabulation. Rule recorded in `docs/claims_ledger.md`: never
re-enable a committing bridge without sealed-proven `wrong = 0`.

---

## 2. The measurement that exposed the truth

We built the instrument we never had: a **held-out dev lane** — 500 real GSM8K
problems CORE was **not** built against (`evals/gsm8k_math/holdout_dev/`). One scorer,
three sets, same day:

| Set | correct | wrong | what it is |
|---|---:|---:|---|
| `train_sample` (50) | 4 | 0 | the data CORE was **built on** — overfit, no predictive validity |
| `holdout_dev` (500) | 5† | 0 | real GSM8K **never built-against** — the composer scored **0**; the 5 are the narrow R1 reconstruction |
| sealed test (1,319) | 0 | 0 | the final exam |

† Committed `evals/gsm8k_math/holdout_dev/v1/report.json` reads **5 correct / 0 wrong
/ 495 refused**. All 5 come from the narrow, verifier-gated **R1 comparative-total
reconstruction** (a typed reader, not the composer), which landed the same day; the
composer (`resolve_pooled`) generalised to **0** of 500. The "0%" below is the
composer's number — the subject of this post-mortem. (The original snapshot read
`0/500`; it predated the R1 landing and is corrected here to match the committed
artifact.)

**The composer's real GSM8K capability was 0%.** Its four train "correct" generalised
to *zero* of 500 held-out cases (the 5 committed held-out correct are the separate R1
reconstruction, above). Serving held `wrong = 0` only because it refused everything real.

**The deeper finding — the composer is *unsound*, not just narrow.** The derivation
composer (`resolve_pooled`), the reader the whole composition program was built around
as "`wrong=0`-safe", measured on held-out: **2 correct / 87 WRONG / 411 refused —
17% confabulation.** And no gate fixes it: characterising all 89 commits, *step count,
pool size, and op-sequence do not separate the 2 right from the 87 wrong.* The composer
**cannot distinguish its correct readings from its wrong ones** — so no principled gate
admits the right while refusing the wrong. (Full analysis:
`docs/analysis/real-gsm8k-capability-measurement-2026-06-04.md`.)

Four committing-reader lift attempts were built and **empirically falsified** on
held-out (not just argued): the composer (17% wrong), a maximally-narrow forced reader
(100% wrong when it fired), a strict sum-reader (100% wrong), and the sound
candidate-graph filter (built 0 admissible candidates — sound but constructs nothing).
**Shallow committing cannot be sound on real GSM8K**, because GSM8K problems that look
like "two numbers and a cue word" are almost always multi-step problems where the
shallow reading is wrong every time.

---

## 3. Why the terrain was wrong for CORE

GSM8K is **deliberately engineered** to require 2–8 step natural-language reasoning —
built to defeat exactly the pattern-matching we kept attempting. CORE is a
**deterministic, verifiable** engine; its strength is exact, inspectable, replayable
reasoning where a conclusion can be *checked*. GSM8K is the benchmark built *for*
stochastic multi-step LLM reasoning. **We were arm-wrestling a machine on its home
court.**

This is not a new realisation buried in the loss — it is CORE's own stated doctrine:
*"Next primitives = checkable-conclusion domains (logic / constraint / proof)."* The
GSM8K chase had drifted away from it.

---

## 4. The path now: deductive logic (checkable-conclusion terrain)

We pivoted the "sizeable numbers" goal to **deductive logic**, where the answer is
*verifiable by construction* — so capability can show real correct numbers, not just a
refusal floor, and `wrong = 0` is structural rather than aspirational.

**What this reuses (already paid for, previously zero-consumer):** the ADR-0201 ROBDD
propositional canonicalizer, the binding-graph DAG (ADR-0132), the proof_chain model /
builder / single-step modus ponens (ADR-0204/0205).

### Phase 1 — DONE (this PR)

A **sound and complete propositional entailment operator**
(`generate/proof_chain/entail.py`, ADR-0206) — the multi-hop inference operator
`evals/symbolic_logic/gaps.md` said did not exist and ADR-0205 deferred:

> premises ⊨ query  iff  `(⋀ premises) → query` is a tautology — an exact ROBDD check.

Outcomes: `entailed` / `refuted` / `unknown` / `refused` (inconsistent or
out-of-decidable-regime). `wrong = 0` is structural; quantified/predicate input refuses
by design (propositional regime only).

**Measured, honestly:**

| set | n | correct | wrong | non-trivial (entailed+refuted) |
|---|---:|---:|---:|---:|
| dev | 200 | 200 | **0** | 74 |
| **holdout v1** | 500 | **500** | **0** | **227** |
| fuzz (seed 424242, engine vs **independent** oracle) | 2,796 | 2,796 | **0** | 1,241 |

The gold is computed by an **independent truth-table oracle**
(`evals/deductive_logic/oracle.py`) sharing **no code** with the ROBDD engine.
The committed gate (`test_engine_matches_independent_oracle_fuzz`) runs a
deterministic **3,000-case** fuzz of which **2,796** are in-regime/definite, with
**zero** engine-vs-oracle disagreements (a complementary 4,000-case fuzz exercises
inconsistent-premise refusal) — the soundness evidence the GSM8K composer could
never produce. INV-25 (`tests/test_architectural_invariants.py`) ratifies that
independence structurally.

**Honest caveat (state it plainly):** propositional validity is *decidable*, so 100%
is the expected ceiling for a correct implementation. The value is not "solved
something unsolved" — it is (a) CORE's first real, non-zero, **independently-verified**
capability (not a refusal floor), (b) the honest foundation the harder layers build on,
(c) it is on CORE's terrain. External framing: *"CORE performs sound, complete,
deterministic deductive inference — multi-hop entailment and refutation — verified
`wrong = 0` against an independent oracle on held-out data."*

### Phases 2–4 — the plan

2. **Scale + recognizable benchmark.** Harder/deeper held-out sets; a grounded
   **RuleTaker / ProofWriter** mirror (finite-entity rules ground to propositional) →
   a number on a *published, recognizable* benchmark, same `wrong = 0` discipline.
3. **NL→logic grounding.** Read English logic problems into formulas. This is where it
   becomes externally impressive — and where the GSM8K natural-language rake lives, so
   it is measured the same disciplined way (held-out + independent gold) and refuses
   what it cannot ground.
4. **Serving.** Wire the operator into `chat/runtime` so CORE answers deductive queries
   to users, gated by the same `wrong = 0` discipline (and, for any serving promotion,
   the sealed-confirmation rule from §1).

---

## 5. Disciplines carried forward (the anti-recurrence rules)

1. **Never score capability on data the system was built against.** Every capability
   claim is measured on held-out data + confirmed on a sealed/independent arbiter.
   No `train_sample`-class ruler is ever the score again.
2. **Gold must be independent of the system under test.** A held-out lane uses an
   independent oracle (or sealed operator-run gold), never the engine's own output.
3. **`wrong = 0` is a floor, not a result.** "Refuses everything" is the *failing*
   baseline. The capability claim is *coverage with* `wrong = 0`.
4. **No serving promotion without sealed/independent-proven `wrong = 0`.** The
   product_bridge breach is the standing reason.
5. **Falsify lift attempts empirically, on held-out, before trusting them.** Build the
   reader, measure it on data it was not tuned to, and report what it actually does —
   including the failures.
6. **Prefer checkable-conclusion terrain.** Where the answer is verifiable, capability
   is honest and `wrong = 0` is structural. That is where CORE competes.

---

## Reproduce

```bash
PYTHONPATH=. .venv/bin/python -m evals.deductive_logic.runner          # dev + holdout; exits 1 if wrong>0
PYTHONPATH=. .venv/bin/python -m pytest tests/test_deductive_logic_entail.py -q
# GSM8K honest baseline (context for the pivot):
PYTHONPATH=. .venv/bin/python -m evals.gsm8k_math.holdout_dev.v1.runner # the held-out instrument
```
