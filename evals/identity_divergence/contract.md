# identity-divergence eval lane

## What it measures

Whether CORE's identity system produces meaningfully *different* articulations
when presented with different identity profiles, and whether each articulation
remains internally *coherent* with its respective profile.

This tests the architectural claim that identity is load-bearing: different
identity axes should produce different, principled behaviors, not random noise.

## Identity axis sets

Two deliberately opposed axis sets produce different stances on the same
proposition:

| Axis Set | Orientation | Example preference |
|----------|-------------|-------------------|
| A (Precision) | Accuracy-first, explicit qualification, technical precision | "Light might reveal some aspects of truth" (hedged) |
| B (Generosity) | Inclusivity-first, broader generalization, relational emphasis | "Light reveals truth" (direct claim) |

### Axis A: Precision-first identity
- Weight accuracy over coverage
- Prefer qualified claims and caveats
- Emphasize technical distinctions
- Flag uncertainty explicitly
- Avoid overstatement

### Axis B: Generosity-first identity
- Weight inclusivity over precision
- Prefer direct, affirmative claims
- Emphasize unity and connection
- Implicit confidence
- Embrace broader interpretation

## Shared curriculum

Curated set of ~100 teaching events, identical for both agents:
- Articulation prompts (proposition graphs to realize)
- Domain instruction (kinship, color, spatial relations)
- Logical reasoning (transitivity, hierarchy)
- Uncertainty handling (contradiction, ambiguity)

## Scoring rubric

### Divergence metric

Measured on articulation outputs:
- Syntactic divergence: different surface forms for same graph
- Modal divergence: modal strength (must/might/should)
- Hedge divergence: presence/absence of qualifiers (maybe, arguably, perhaps)
- Polarity divergence: confirmation vs. hedging

Divergence score = fraction of articulations where axis A vs. B produce
measurably different outputs (lexically, syntactically, or modally).

**Pass threshold:** Divergence > 0.30 (at least 30% of outputs differ)

### Coherence metric

For each identity profile, measured per articulation:
- Consistency within profile: does the output respect its own axis preferences?
- Contradiction check: outputs should not contradict known teaching
- Modal alignment: should express appropriate uncertainty for the domain

Coherence score = fraction of articulations that remain consistent with their
identity profile (no hedges for Axis B, no overstatements for Axis A).

**Pass threshold:** Coherence > 0.85 (85%+ consistency)

### Identity-stripped baseline

Same curriculum with identity disabled (neutral profile):
- Should produce consistent "default" articulations
- Divergence with stripped baseline should be near zero
- Proves identity is the causal factor, not noise

**Pass threshold:** Divergence(A vs. stripped) > Divergence(baseline A vs. B)
(i.e., axis A differs more from baseline than the baseline differs from itself)

## Pass thresholds (v1)

- Divergence: > 0.30 (meaningful difference)
- Coherence (Axis A): > 0.85
- Coherence (Axis B): > 0.85
- Coherence (stripped): > 0.85
- Causal check: divergence_A_vs_baseline > divergence_baseline_A_vs_baseline
- Overall: all thresholds must be met

## Evaluation protocol

1. Load identity profiles (A, B, stripped neutral)
2. Load shared curriculum teaching examples
3. For each articulation prompt:
   - Run with Axis A identity → realize surface
   - Run with Axis B identity → realize surface
   - Run with stripped identity → realize surface
4. Score divergence and coherence
5. Report per-axis and aggregate metrics

## Data layout

```
evals/identity_divergence/
  contract.md           # this file
  axes/
    axis_a.yaml         # precision-first profile
    axis_b.yaml         # generosity-first profile
  curriculum/
    teaching.jsonl      # ~100 teaching events
  dev/
    cases.jsonl         # dev set
  public/
    v1/
      cases.jsonl       # public test set
  holdouts/
    v1/
      cases.jsonl       # sealed holdout
  runner.py             # scorer (divergence + coherence)
  results/              # output reports
```
