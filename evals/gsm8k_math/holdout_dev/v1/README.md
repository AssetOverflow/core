# GSM8K Held-Out Dev Lane (v1)

**The honest iteration metric.** 500 real GSM8K problems CORE was **not** built against.

## Why it exists

The 50-case `train_sample` is the data CORE's grammar was hand-built against. On
2026-06-04 the first real sealed measurement exposed the consequence: tuning against
those 50 produced "lift" that was **pure overfit** and **committed wrong answers on the
real exam** (a `wrong=0` breach). The three numbers, same scorer, same day:

| Set | Correct | Wrong | What it is |
|---|---:|---:|---|
| `train_sample` (50) | 4 | 0 | the data CORE was built on — **overfit, no predictive validity** |
| **`holdout_dev` (500, this lane)** | **1** | **0** | **real GSM8K CORE was NOT built on — the honest signal** |
| sealed test (1,319) | (re-measure) | 0 expected | the final exam (sealed, never read by Claude) |

**Baseline was 0/500** — the 4 train "correct" generalised to *zero* held-out cases.
**2026-06-04: the first sound lift took it to 1/500, wrong=0** — the clean ratio-chain
reader (`generate/derivation/ratio_chain.py`), a *verifiable* (not search-based) reading.
Real GSM8K capability is now a measured, honest **0.2%** — small, but real and rising,
on data that can't be gamed. The sealed test must re-confirm `wrong=0` (operator-run).

## The discipline (train / dev / test)

- **Iterate here.** This set is *open* (you may read it; it is large enough that trivial
  memorisation is not the win). Watch `correct` move off 0.
- **`wrong == 0` is the floor**, not the goal. Refusing everything is the *failing*
  baseline (0/500), not a pass — the lane gate is `correct` rising **with** `wrong=0`.
- **The sealed test (1,319) is the final arbiter.** A capability change is real only when
  it moves `correct` here AND holds `wrong=0` on the sealed set. Never trust a train_sample
  gain again.

## Provenance

`openai/gsm8k` *train* split, minus the 50 `train_sample` questions, sorted by
`sha256(question)`, first 500. Deterministic and reproducible. The sealed *test* split is
untouched.

## Run

```bash
PYTHONPATH=. .venv/bin/python -m evals.gsm8k_math.holdout_dev.v1.runner
```

Exits non-zero if `wrong > 0` (the floor). Current baseline: **1 / 0 / 499** (first sound lift, 2026-06-04).
