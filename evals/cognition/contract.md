# Cognition Eval Lane — Contract

**Lane:** `cognition`
**Version:** v1
**Created:** 2026-05-15

## What this lane measures

End-to-end cognitive pipeline correctness: given a natural-language prompt, does
the `CognitiveTurnPipeline` produce a response that:

1. Classifies intent correctly.
2. Captures expected domain terms in the realized surface.
3. Contains expected surface fragments (grounding check).
4. Maintains versor closure (`versor_condition < 1e-6`).
5. Produces a deterministic trace hash across runs.

## Scoring rubric

Each case produces five binary signals. Lane-level metrics are rates over cases:

| Metric | Definition | v1 pass threshold |
|--------|-----------|-------------------|
| `intent_accuracy` | Fraction of cases with correct intent classification | >= 0.90 |
| `term_capture_rate` | Fraction of expected terms found in surface | >= 0.80 |
| `surface_groundedness` | Fraction of cases where all expected surface fragments present | >= 0.80 |
| `versor_closure_rate` | Fraction of cases with `versor_condition < 1e-6` | 1.00 |
| `determinism` | All trace hashes identical across 2 runs | true |

## Pass criteria

- **Public v1:** All five metrics meet or exceed thresholds above.
- **Holdout:** intent_accuracy >= 0.85, versor_closure_rate == 1.00.

## Version escalation plan

- **v2:** Longer prompts, paraphrased surface forms, rarer vocabulary (e.g.
  "elucidate" instead of "what is"), multi-clause prompts.
- **v3:** Adversarial items targeting weakest category from v2 results.

## Categories tested

definition, comparison, cause, procedure, recall, correction, verification,
unknown

## Runner

`runner.py` in this directory. Invoked via `core eval cognition`.
