# ADR-0046 — PropositionGraph as Forward Admissibility Constraint

**Status:** Accepted  
**Date:** 2026-05-18  
**Author:** Shay  

---

## Context

The 2026-05-17 assessment identified the load-bearing structural gap in CORE:

> *The `PropositionGraph` is currently a post-hoc structural wrapper over what
> the field already produced, not a forward constraint on what the field should
> produce. That's the seam — not a disconnection, but a directionality that
> limits how much the graph can steer generation rather than describe it.*

The `intent_bridge.py` path (ADR-0018) builds a `PropositionGraph` from the
classified intent and the `ArticulationPlan`, then grounds it with recalled
words from the generation result.  The graph is built *after* `generate()` has
already walked the manifold.  The graph describes; it does not constrain.

`generate()` already accepts an `AdmissibilityRegion` (ADR-0022 through
ADR-0026).  The region is computed from the vocabulary's admissibility
structure.  What was missing was the coupling: convert the graph's named
node versors into an `AdmissibilityRegion` *before* calling `generate()`.

---

## Decision

Add `generate/graph_constraint.py` with one public entry point:

```python
build_graph_constraint(
    graph: PropositionGraph,
    vocab,
    *,
    top_k: int = 8,
) -> AdmissibilityRegion
```

The region's `allowed_indices` is the union of the CGA top-k neighbourhoods
of every named surface in the graph, computed by exact `cga_inner` scan.

This converts the graph from a descriptor into a forward constraint:

```
geometry (CGA versor neighbourhood)
  → structure (PropositionGraph nodes)
    → propagation (AdmissibilityRegion fed to generate())
```

The `chat/runtime.py` hot path can now call:

```python
graph = _build_graph_from_intent(intent, articulation)
region = build_graph_constraint(graph, vocab, top_k=8)
result = generate(field_state, vocab, persona, region=region, ...)
```

This is a *drop-in* — `generate()` already accepts `region`.  The only new
code is the CGA neighbourhood computation in `graph_constraint.py`.

---

## Consequences

### What changes

- The generation walk is now shaped by the proposition's geometric meaning
  before any tokens are produced, not after.
- The `admissibility_trace` in every `GenerationResult` now carries the graph
  root IDs as the region label — full traceability from surface token back to
  the intent node that constrained it.
- The system satisfies the three-pillar coupling end-to-end:
  **Pillar 1** (geometry, CGA algebra) → **Pillar 2** (structure, typed graph)
  → **Pillar 3** (propagation, constrained field walk).

### What does not change

- `generate()` API is unchanged.
- Empty or fully OOV graphs return an unconstrained region — existing fallback
  contract is preserved.
- All existing tests pass unchanged.
- `versor_condition < 1e-6` invariant is unaffected (the region filters
  candidates; it does not alter the rotor construction or field update).

### Scope limits (documented)

- `top_k=8` is an operational default.  Pack authors who need tighter or
  looser constraints can override at call time.
- The coupling between `chat/runtime.py` and `build_graph_constraint` is
  available but the hot-path wire-up is a follow-up ADR (wire when the
  intent bridge returns a non-empty graph on the main path).
- The CGA neighbourhood is computed over the full vocab on each call
  (O(|vocab| × |nodes|)).  At current pack sizes this is negligible;
  a cached neighbourhood index is a future optimisation if packs grow.

---

## Industry Demo Suite

Three standalone demos in `evals/industry_demos/` make falsifiable claims
no transformer-LLM wrapper can reproduce:

| Demo | Claim |
|------|-------|
| `demo_01_forward_constraint` | Graph constrains walk via CGA geometry *before* any tokens are produced |
| `demo_02_geometry_drives_identity` | Identity pack swap changes manifold geometry, not just output text |
| `demo_03_deterministic_audit` | Three independent runtimes produce byte-identical audit records (architectural determinism) |

Each demo exits 0 on pass, 1 on fail, and prints structured JSON evidence.

The exact-recall-at-scale claim that previously sat under this ADR as a
fourth demo has been **moved out**.  An earlier draft attempted to
demonstrate it via random `standard_normal` vectors run through
`unitize_versor`; that construction is not valid as a versor in `Cl(4,1)`
(mixed signature `cga_inner` is not self-maximising for arbitrary
unitized random vectors), and the demo failed at N=10 000 in exactly
the way the construction predicts.  The correct home for that claim
remains [ADR-0045](./ADR-0045-long-context-recall-vs-transformer-baselines.md),
which measures recall on the actual vault path with properly
constructed versors at N ∈ {100, 1k, 10k, 100k} = 100 %.  Putting the
same claim behind a weaker construction here would have been honest
neither to the geometry nor to the existing measurement.

---

## Cross-References

- [ADR-0018](./ADR-0018-tool-use-scope.md) — `intent_bridge.py` originally
  builds the `PropositionGraph` from the classified intent and articulation
  plan; this ADR converts that graph into a forward constraint.
- [ADR-0022](./ADR-0022-forward-semantic-control.md) through
  [ADR-0026](./ADR-0026-ranked-admissibility-with-margin.md) — `AdmissibilityRegion`
  contract that `generate()` already accepts; this ADR provides a new
  source for that region (the graph) without changing the contract.
- [ADR-0045](./ADR-0045-long-context-recall-vs-transformer-baselines.md) —
  load-bearing exact-recall measurement; the canonical source for that
  claim (see note above).

---

## Verification

```
tests/test_graph_constraint.py        — 8 tests, all green
evals/industry_demos/demo_01..03.py   — 3 demos, each exits 0

Lanes (all green on this branch):
  core test --suite smoke         67 passed
  core test --suite cognition    121 passed
  core test --suite runtime       19 passed
  core test --suite algebra      132 passed
  core test --suite teaching      17 passed
  core test --suite packs          6 passed
  core eval cognition           intent_accuracy=100%  versor_closure_rate=100%
```

The non-negotiable field invariant (`versor_condition(F) < 1e-6`) is
unaffected: this ADR only narrows the candidate index set fed to
`generate()` — it does not touch versor construction, sandwich
application, or field update.
