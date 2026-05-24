# ADR-G5 — Question Target Binding For Derived / Composed States

## Status
Proposed

## Problem

G.4 demonstrated that multi-clause initial-state parsing can improve while GSM8K admission still remains zero because the question layer cannot bind composed state into a requested target quantity.

Current architecture:

statement parse
-> candidate graph
-> state construction
-> solver
-> verifier

Gap:

question sentence
-> requested target binding

is still too shallow for composed/derived state.

## Objective

Add a deterministic question-target binding layer capable of:

- binding aggregate totals;
- binding composed holdings;
- binding derived quantities;
- preserving typed provenance;
- refusing ambiguous targets.

## Design

### 1. TargetBinding node

Introduce a typed graph node:

```text
TargetBinding(
  entity_scope,
  quantity_scope,
  aggregation_kind,
  provenance_edges,
)
```

Aggregation kinds:

- single
- sum
- difference
- multiplicative_total

No implicit averaging.

### 2. Aggregate target phrases

Recognize closed-set phrases:

- altogether
- in total
- combined
- total
- altogether combined

Ambiguous phrases refuse.

### 3. Derived-state binding

Allow target binding against:

- embedded quantifier outputs;
- composed multi-clause outputs;
- comparison-derived states;
- rate-derived totals.

But only when provenance path is explicit and verifier replay succeeds.

### 4. Refusal-first policy

Refuse when:

- multiple candidate targets survive;
- unit scopes mismatch;
- aggregation scope unresolved;
- entity scope ambiguous.

## Measurement

Primary gate:

```text
admitted_wrong == 0
```

Secondary gates:

- curated target-binding lane passes;
- deterministic report byte-equality;
- GSM8K question-layer refusal family decreases.

## Implementation sequence

1. Add TargetBinding graph type.
2. Add aggregate phrase parser.
3. Add question-target graph traversal.
4. Add verifier replay support.
5. Add curated axis lane.
6. Add GSM8K refusal-family measurement.

## Explicit anti-goals

- no best-effort target guessing;
- no fuzzy semantic ranking;
- no hidden LLM fallback;
- no benchmark-specific templates.
