<!-- CANONICAL | real-gsm8k-capability-measurement-2026-06-04.md | 2026-06-04 | measurement (Opus) lane | the honest measurement of real GSM8K capability + why the composer is unsound | verified against origin/main 43169979 + held-out dev lane + operator sealed runs -->

# Real GSM8K Capability — the honest measurement (and why "wrong=0" was a 50-case illusion)

This is the result the project should have been seeing for weeks. It was hidden because
development was scored on a 50-case sample CORE was built against, never on held-out data.
Now measured on 500 held-out cases (the new `holdout_dev` lane) and the sealed 1,319.

## 1. The numbers — one scorer, three sets (2026-06-04)

| Set | correct | wrong | refused | what it is |
|---|---:|---:|---:|---|
| `train_sample` (50) | 4 | 0 | 46 | the data CORE was **built on** — overfit |
| `holdout_dev` (500) | **0** | 0 | 500 | real GSM8K **never built-against** — the honest baseline |
| sealed test (1,319) | **0** | 0 | 1,319 | the final exam |

**Real GSM8K capability is 0%.** The 4 train "correct" generalise to **zero** of 500
held-out cases. Serving holds `wrong=0` **only because it refuses everything real** — the
one genuine, defensible property (zero confabulation), not an accuracy.

## 2. The deeper finding — the composer is *unsound*, not just narrow

The serving path refuses real cases (0/0/500). The obvious "lift" is to wire the
**derivation composer** (`resolve_pooled` — the ADR-0178/0207 substrate, the reader the
whole composition program was built around as `wrong=0`-safe). Measured on held-out:

> **`resolve_pooled` on the 500: 2 correct / 87 WRONG / 411 refused — 17.4% wrong.**

The composer's self-verification gate (grounding ∧ cue ∧ unit ∧ completeness ∧ uniqueness)
**is not `wrong=0`-safe on real data.** "wrong=0" held only on the 50 train cases it was
tuned to. On real GSM8K the composer confabulates 17%. This is *why* `product_bridge`
(which wraps `resolve_pooled`) committed 0/5 on the sealed set — it was exposing a leaky
reader through a narrow whitelist.

## 3. Why no gate fixes it — correct and wrong are structurally identical

Characterising all 89 composer commits on held-out (2 correct, 87 wrong):

- **Step count** does not separate them: wrong commits span 1–5 steps; the 2 correct are at
  2 and 4 — inside the wrong distribution.
- **Pool size** does not separate them: 54 of 87 wrong are *lone chains* (pool = 1, no rival
  to trigger the disagreement refusal); the 2 correct also have pool ∈ {1, 2}.
- **Op-sequence** does not separate them: the wrong commits are dominated by multiply-chains
  (`multiply,multiply` ×28, `multiply` ×25, triple+ ×22); the 2 correct are *also*
  multiply-chains.

**The composer cannot distinguish its correct readings from its wrong ones.** The 2 correct
are indistinguishable from the 87 wrong by every structural feature available to a gate.
Therefore **no principled gate admits the correct while refusing the wrong** — any gate that
keeps the 2 would be overfit to those exact cases (the same disease that produced the
breach). The disagreement rule, the substrate's main `wrong=0` defence, fails on the 54
lone-chain wrongs by construction.

## 3b. Two lift attempts, both empirically falsified (not just diagnosed)

I did not stop at diagnosis — I built and measured two committing readers on held-out:

| Attempt | held-out 500 | result |
|---|---|---|
| `resolve_pooled` (the built composer) | 2 correct / **87 wrong** | 17% confabulation |
| Maximally-narrow forced reader (exactly 2 grounded quantities + one unambiguous op cue) | 0 correct / **61 wrong** | **100% confab when it fires** |
| Strictest sum-reader (exactly 2 numbers + total-cue in question + every complexity cue blocked → A+B) | 0 correct / **2 wrong** | **100% confab; the 2 "simple" cases were multi-step (a fraction, a "double") hiding behind 2 numbers** |
| candidate-graph sound filter (roundtrip + disagreement) | **0 admissible candidates built** | sound, but constructs nothing to commit |

The narrow reader is the more brutal result: GSM8K problems that *look* like "2 numbers + a
cue word" are almost never 2-operand problems — they are multi-step problems where the
shallow reading is wrong **every single time**. Shallow committing **cannot** be sound on
real GSM8K. This is measured, not asserted.

**Third leg — the sound path has no headroom either.** The candidate-graph (the
roundtrip-admissible + disagreement filter that *is* `wrong=0` on held-out) was checked for
disambiguation headroom: on the 500 it builds **0 admissible candidates** (498/500 enumerate
zero branches at all). It is `wrong=0` not because it disambiguates well but because **it
constructs no reading to commit.** There is nothing to soundly tiebreak. All three paths are
exhausted: the sound one builds nothing; the two that build, confabulate.

## 3c. The architectural impasse (the load-bearing finding)

CORE has two GSM8K paths, and the held-out data shows **neither can soundly lift capability**:

- **The candidate-graph / recognizer-injector path is SOUND** (`wrong=0` on held-out) — but
  it is **frozen** by ADR-0207 §4 to "lexeme-recognition + refusal-only, no new positive
  capability," and it covers **0** real cases.
- **The derivation composer is OPEN** (ADR-0207 §5 routes all positive capability here) — but
  it is **unsound** (17% wrong on held-out, no separating gate).

**This falsifies ADR-0207's central premise.** ADR-0207 froze the regex path and deferred all
positive capability to the composer *on the belief that the composer is the `wrong=0`-safe
mechanism*. The first held-out measurement shows the opposite: **the frozen path was the sound
one; the open path confabulates.** The ratified strategy locked out the only sound mechanism
in favor of an unsound one. ADR-0207 §5 needs re-opening with this evidence (a follow-up ADR),
because "feed the composer" is a path to *more confabulation*, not lift.

## 3d. The first SOUND lift — verifiable readers work where search does not

The four falsified attempts above share one trait: they **search/infer and commit**. A
fifth approach — a **structurally-forced, verifiable** reader — succeeds where they fail.

The **clean ratio-chain reader** (`generate/derivation/ratio_chain.py`) reads only the
narrow class of chained ratio relations bottoming out at a grounded quantity
(*"cat is 8; rabbit is half the cat; dog is 3× the rabbit → 12"*). The answer is **forced**
by the chain, not guessed; the reader **refuses** any comparative-additive / aggregate sign.

> **Measured on held-out 500: fires 1, 1 correct / 0 WRONG.** It generalises to novel
> renumbered/re-entitied chains (box→crate→pallet, Mary→sister→mother) and refuses what it
> cannot prove. Wired to serving: **held-out 0/500 → 1/500, train_sample wrong=0.**

This is the **first honest, sound capability off zero** — small (0.2%) but real, generalising,
and `wrong=0`. It confirms the path: not "feed the composer" (search, 17% wrong) but **narrow
verifiable readers**, each measured `wrong=0` on held-out **and** the sealed test before trust.
The substrate's failure was never that *no* reading is sound — it is that *search-based*
committing cannot tell sound from unsound. Forced, verifiable readings can.

## 4. What this means (honest, load-bearing)

1. **The only `wrong=0`-safe policy on real GSM8K is refusal.** Current serving (0/0/500) is
   that policy. It is the honest floor, and the zero-confabulation discipline is real.
2. **Incremental composer tuning is not a path to sound lift.** The composer's readings are
   not verifiable as built; committing them leaks ~17% wrong. Tightening to dodge specific
   held-out wrongs is overfitting.
3. **Real lift requires a fundamentally more *verifiable* reading mechanism** — one that can
   prove a multi-step reading correct (or refuse), rather than search-and-self-verify, which
   the data shows is indistinguishable between right and wrong. That is deep research, not a
   knob.
4. **The instrument now exists.** Every future capability claim is measured on `holdout_dev`
   (correct must rise with `wrong=0`) and confirmed on the sealed test. No train_sample
   number is ever the score again.

## 5. The honest external framing (for any outward material)

CORE on real GSM8K: **0% coverage, 0 confabulations.** It refuses what it cannot verify; it
does not guess. That is the truthful claim — not an accuracy number. The composition
substrate is a research direction with a measured 17% confabulation rate on real data, which
is *why it is not wired to serving*. Progress is now measurable honestly for the first time.

## Reproduce

```bash
PYTHONPATH=. .venv/bin/python -m evals.gsm8k_math.holdout_dev.v1.runner   # 0/0/500
# composer-unsoundness:
PYTHONPATH=. .venv/bin/python -c "import json;from generate.derivation.pool import resolve_pooled;d=[json.loads(l) for l in open('evals/gsm8k_math/holdout_dev/v1/cases.jsonl')];c=w=0
for x in d:
 r=resolve_pooled(x['problem'])
 if r: c+= abs(r.answer-x['expected_answer'])<1e-6; w+= abs(r.answer-x['expected_answer'])>=1e-6
print('composer correct',c,'wrong',w)"
# sealed (operator only, key required): 0/0/1319
```
