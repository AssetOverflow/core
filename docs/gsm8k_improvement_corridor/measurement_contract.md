# Measurement Contract

## Primary invariant

```text
admitted_wrong == 0
```

This is the load-bearing contract.

Admission may remain low temporarily.
Wrong admitted answers may not rise.

## Every phase must produce

1. Curated capability-axis cases.
2. Deterministic report artifacts.
3. GSM8K refusal-family deltas.
4. Regression sweep results.
5. Typed refusal distributions.

## Forbidden success modes

- benchmark-specific hacks;
- hidden fuzzy ranking;
- probabilistic best-guess;
- parser relaxation without verifier support;
- silent coercion of ambiguous units/entities.

## Required evidence

### Curated lane

Each phase ships:

```text
evals/math_capability_axes/<phase>/v1/
```

with:

- cases.jsonl
- runner.py
- report.json
- contract.md

### GSM8K probe

Every phase reruns:

```text
evals/gsm8k_math/train_sample/v1/
```

Tracked:

- admission_rate
- admitted_wrong
- refusal_family_counts
- refusal_family_delta

## Determinism requirements

Reports must be byte-equal across repeated runs.

All graph serialization must be stable.

All provenance ordering must be deterministic.

## Architectural discipline

The objective is not:

> maximize benchmark score.

The objective is:

> maximize trustworthy admission under deterministic reasoning constraints.
