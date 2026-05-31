# ADR-0195 — Product Promotion Bridge

**Status:** Accepted / Implemented.
**Date:** 2026-05-30.

## Decision

Promote only a narrow subset of the pooled derivation reader into the serving
candidate-graph path: complete pure-product readings whose question asks for an
aggregate product target, and whose surface lacks known non-product hazards.

This is not a wholesale import of `resolve_pooled`. The pooled reader solves
GSM8K train-sample `0003` and `0021`, but still commits eight known wrong
products on the same 50-case sample. The bridge therefore acts as a correction
gate over the pooled reader.

## Guard

`generate.derivation.product_bridge.resolve_promotable_product()` admits only when:

- `resolve_pooled()` resolves uniquely;
- the selected derivation is classified `complete`;
- every step is `multiply` and no step is a comparative scalar;
- the question target is revenue/money-made or total moved weight;
- hazard surfaces such as rate questions, percentages, residual state,
  profit/equation targets, same-amount group totals, and comma-number extraction
  gaps are absent.

## Evidence

The official train-sample lane moves from `4/46/0` to `6/44/0`:

- newly correct: `gsm8k-train-sample-v1-0003`, `gsm8k-train-sample-v1-0021`;
- wrong remains `0`;
- case `0050` remains refused;
- the eight known pooled-reader wrong commits remain unpromoted.

The ADR-0126 exit threshold remains unmet (`correct >= 10`), so the runner still
exits nonzero even though the metric improves.
