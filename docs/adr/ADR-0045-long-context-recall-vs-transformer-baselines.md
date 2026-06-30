# ADR-0045 — Long-context recall: CORE vs transformer baselines

Status: Accepted (2026-05-17)

## Context

The long-context-cost lane (`evals/long_context_cost/runner.py`)
publishes CORE's vault-recall *latency* as a function of stored-entry
count `N` (linear scan, ~0.22ms @ 1k, ~21ms @ 100k).  What the lane
does *not* publish is a comparison against the alternative
architecture every reviewer asks about: a transformer's in-context
recall.

The architectural claim CORE has made since ADR-0001 is that vault
recall is *exact by construction* — `cga_inner` scan over every
stored versor, no approximate index, no embedding compression, no
attention bottleneck.  That claim is true by inspection of
`vault/store.py`, but it has not been published as a measurement
alongside the transformer numbers it contrasts with.

## Decision

Ship a deterministic needle-in-a-haystack measurement against CORE's
vault at multiple `N`, paired with frozen citations of published
transformer long-context recall numbers.

### Component 1 — CORE measurement

`evals/long_context_cost/comparison_runner.py` plants a distinctive
versor at a known index alongside `N-1` random distractors, queries
the vault, and asserts `top_k=1` returns the planted needle.  Default
`N ∈ {100, 1_000, 10_000, 100_000}`.

Expected recall: **1.0 at every N** by construction.  If it ever
drops, the vault has been broken.

### Component 2 — Transformer baselines

`evals/long_context_cost/baselines/transformer_long_context.json`
freezes the comparator numbers as cited published figures:

| System | Context | Reported recall |
|---|---|---|
| Anthropic Claude 2.1 | 200k | 50% (NIAH, no prompt engineering) |
| OpenAI GPT-4 Turbo 128k | 128k | ~71% (NIAH aggregate) |
| Google Gemini 1.5 Pro | 1M | 99.7% (NIAH headline) |
| NVIDIA RULER (eval) | 131k | varies — most models drop below 80% well before nominal context limit |

These are *not* re-measured here.  Citations point to the original
vendor / paper.  When a new published number warrants an update, the
baselines file is the single edit point.

### Combined artifact

`evals/long_context_cost/results/comparison_v1.json` carries both:
the CORE measurement and the frozen transformer citations, with a
`claim_supported` boolean gating the headline.

`tests/test_long_context_comparison.py` (5 tests) locks:

1. Schema stability.
2. `claim_supported == True` and CORE recall_pct == 100.0 across the
   tested N range.
3. Baselines retain `source` + `url` for every entry.
4. The default N range exercises at least 100k.
5. The `core_guarantee` block advertises `recall_kind ==
   "exact_cga_inner_scan"`.

## Scope and limits of the comparison

The two components measure different inputs.  CORE's needle-in-a-haystack
is over synthetic float32 versors of shape `(32,)`; the cited transformer
baselines are over natural-language needles in natural-language haystacks.
The comparison is at the *architectural* level — exact-scan recall vs
attention-based probabilistic recall — and is not a benchmark-for-benchmark
score.

What the CORE measurement does establish:

1. The `cga_inner`-based recall in `vault/store.py` returns the planted
   needle at top-1 for every tested N, at all four scales.
2. This holds independent of vault size up to 100,000 entries (the largest
   N reported here; the latency curve in `results/v1_metrics.json` extends
   the same primitive to 100k with linear cost).

What the cited baselines establish:

1. Published transformer NIAH recall is < 100% at moderate-to-long context
   lengths.  Headline figures range from 50% (Claude 2.1 at 200k tokens
   without prompt engineering) to 99.7% (Gemini 1.5 Pro at 1M tokens,
   single-needle).
2. RULER (Hsieh et al., 2024) shows most open-source models' effective
   context length is materially shorter than their advertised limit.

The architectural difference is structural, not benchmark-tuned: CORE's
recall path has no approximation, no index compression, and no learned
component, so its correctness on synthetic versors generalizes to any
content type the vault stores.  Transformer NIAH performance is itself
benchmark-specific and varies with elicitation, needle depth, and
context-length stress.

## Consequences

**Positive.**

- The architectural claim about exact recall is now a published
  measurement, not a docstring.
- Comparison is honest: CORE numbers are measured here; transformer
  numbers are cited from published sources, not strawmanned.
- The needle-in-a-haystack test is structural — any future change to
  the vault that breaks exact top-1 recall fails the suite.

**Trade-offs.**

- The CGA inner product for these synthetic float32 vectors can
  produce non-finite scores at conformal-point-at-infinity-like
  configurations.  Scores are sanitized to `null` in the JSON
  artifact; correctness (top-1 is the needle) is the load-bearing
  signal and is unaffected.
- The transformer baselines are point-in-time.  They will need to be
  refreshed as vendors publish new long-context recall figures.
- We deliberately do *not* run a transformer head-to-head here.  That
  would require API budget and harness work disproportionate to the
  worked claim.  The frozen-citations approach honors the claim
  ("CORE is exact") without overreaching ("CORE beats every
  transformer on every benchmark").

## How to verify

```bash
PYTHONPATH=. python3 evals/long_context_cost/comparison_runner.py
PYTHONPATH=. python3 -m pytest tests/test_long_context_comparison.py -q
```

## Where it lives

- `evals/long_context_cost/comparison_runner.py`
- `evals/long_context_cost/baselines/transformer_long_context.json`
- `evals/long_context_cost/results/comparison_v1.json`
- `tests/test_long_context_comparison.py`

## Related

- [ADR-0001](ADR-0001-deterministic-cognitive-engine.md) — exact recall.
- Existing latency curve: `evals/long_context_cost/runner.py` +
  `results/v1_metrics.json` (linear-scan median 0.22ms @ 1k, 21ms @ 100k).
- [ADR-0043](ADR-0043-pack-measurements-phase2.md) — sister Phase-2
  measurement lane.
