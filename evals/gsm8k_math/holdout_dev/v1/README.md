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
| **`holdout_dev` (500, this lane)** | **0** | **0** | **real GSM8K CORE was NOT built on — the honest baseline** |
| sealed test (1,319) | 0 | 0 | the final exam (sealed, never read by Claude) |

The 4 train "correct" generalise to **zero** of 500 held-out cases. **Real GSM8K
capability is 0%.** That is the truth this lane keeps in front of us.

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

Exits non-zero if `wrong > 0` (the floor). Current baseline: **0 / 0 / 500**.
