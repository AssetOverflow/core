# ADR-0125 — Reasoning-Isolation Perturbation Suite

**Status:** Accepted
**Date:** 2026-05-22
**Author:** CORE agents + reviewers
**Depends on:** ADR-0114a, ADR-0115, ADR-0116, ADR-0118a

---

## Context

ADR-0114a Obligation #5 requires a programmatic perturbation suite that
separates concept-stable reasoning from surface pattern matching.
Perturbations are either invariance-preserving, where the answer must
not change, or invariance-breaking, where CORE must produce the
predicted changed graph/trace result.

ADR-0118a already covered OOD surface variation for entity renaming,
unit renaming, and linear number scaling. This ADR adds the semantic
suite over the same GSM8K-style parser development lane without
changing the parser, solver, graph schema, or authored dev cases.

---

## Decision

`generate/perturbation_suite.py` exports:

```text
generate_perturbations(problem, ground_truth_graph, *, seed)
```

and the frozen, slotted `Perturbation` record. The generator is pure and
deterministic: same problem, graph, and seed produce byte-equal
perturbation records.

The suite reuses ADR-0118a registry and rendering helpers for entity and
unit relabeling. It adds semantic transforms that stay inside the
ADR-0115 Phase 1.1 pattern registry:

| Transform | Kind | Behavior |
|---|---|---|
| `rename_entities` | invariance-preserving | Relabel every entity through the ADR-0118a OOD registry. |
| `rename_units` | invariance-preserving | Relabel every unit through the ADR-0118a OOD registry. |
| `reorder_independent_initial_possessions` | invariance-preserving | Reverse two or more independent initial possession sentences. |
| `reorder_independent_operations` | invariance-preserving | Reverse operations only when their affected `(entity, unit)` state sets are pairwise disjoint. |
| `replace_verb_with_synonym` | invariance-preserving | Replace the first add/subtract/transfer verb with a different parser-registry synonym of the same kind. |
| `add_zero_quantity_entity` | invariance-preserving | Add an unused registry entity with zero of the queried unit. |
| `swap_non_commuting_operations` | invariance-breaking | Swap two same-state operations when the replay trace changes; expected answer and trace hash are computed from the swapped graph. |

`scale_numbers_by_k` is not duplicated here. ADR-0118a owns that
Obligation #2 transform and already pins the linear scaling ratio.

`evals/gsm8k_parser_dev/perturbation_score.py` scores the live
parser+solver against generated perturbations, reports explicit skip
counts, prints per-transform ratios, and exits `0` iff both aggregate
invariance classes score 100%.

---

## Invariants

### `adr_0125_generator_determinism`

Two calls with the same problem, graph, and seed produce byte-equal
serialized perturbation records.

### `adr_0125_preserving_answer_stability`

Every invariance-preserving perturbation solves to the original answer
value.

### `adr_0125_breaking_predictable_result`

Every invariance-breaking perturbation solves to the expected answer and
the predicted trace hash computed from the perturbed graph.

### `adr_0125_parser_registry_boundary`

All rendered perturbations stay inside the documented parser pattern
registry: direct initial possessions, supported operation verbs,
supported transfer syntax, supported multiply/divide syntax, and one
supported question.

### `adr_0125_skips_are_explicit`

Inapplicable transforms are skipped with reported reasons. They are not
counted as silent failures or fabricated successes.

---

## ADR-0114a Obligation Discharge Summary

This ADR closes ADR-0114a Obligation #5 for the GSM8K-style parser dev
lane by making reasoning-isolation perturbations executable and scored
through the same parser+solver contract used for public cases.

| Obligation #5 transform | Status under ADR-0125 |
|---|---|
| Rename all entities | Discharged here by reuse of ADR-0118a helpers |
| Rename all units | Discharged here by reuse of ADR-0118a helpers |
| Multiply all numbers by `k` | Discharged by ADR-0118a, not duplicated |
| Reorder independent sentences | Discharged for independent initial possessions; independent operations implemented with 0 applicable current dev cases |
| Swap order of non-commuting operations | Discharged with predicted answer + trace-hash check |
| Replace verb with synonym in registry | Discharged |

The current 50-case dev split has no pairwise-disjoint operation cases,
so `reorder_independent_operations` reports `0/0` applicable and
`50/50` skipped. The transform is implemented and covered by a synthetic
unit test; future dev/holdout cases that contain independent operations
will be scored by the same gate.

---

## Acceptance Evidence

Accepted when:

- `generate/perturbation_suite.py` exports `Perturbation` and
  `generate_perturbations`
- `evals/gsm8k_parser_dev/perturbation_score.py` runs as
  `python3 -m evals.gsm8k_parser_dev.perturbation_score`
- `tests/test_perturbation_suite.py` is green
- Smoke suite is green
- The perturbation scorer reports:
  - `add_zero_quantity_entity`: 50/50 = 1.0000
  - `rename_entities`: 50/50 = 1.0000
  - `rename_units`: 50/50 = 1.0000
  - `reorder_independent_initial_possessions`: 21/21 = 1.0000
  - `reorder_independent_operations`: 0/0 = n/a, 50 skipped
  - `replace_verb_with_synonym`: 36/36 = 1.0000
  - `swap_non_commuting_operations`: 17/17 = 1.0000
  - invariance-preserving: 207/207 = 1.0000
  - invariance-breaking: 17/17 = 1.0000
- ADR linked from `docs/decisions/README.md` index and frontier

---

## Consequences

- ADR-0114a Obligation #5 now has a deterministic local score lane for
  applicable GSM8K-style dev perturbations.
- The scorer distinguishes semantic invariance from source-order graph
  identity: reordering may change tuple order in `MathProblemGraph`, but
  the answer invariant is still checked through the solver.
- Trace-changing swaps are first-class evidence even when the final
  numeric answer remains equal.
- Independent-operation coverage is explicit rather than implied; the
  current public dev set has no applicable pairwise-disjoint operations.

---

## Out of Scope

- Number scaling, which remains owned by ADR-0118a.
- Parser, solver, graph-schema, or dev-case expansion.
- New constructions outside ADR-0115 Phase 1.1.
- Holdout scoring. The generator is holdout-ready, but holdout access
  remains governed by ADR-0114a Obligation #1.
- LLMs, sampling, stochastic generation, approximate recall, or
  unreviewed mutation.
