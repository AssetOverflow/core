# ADR-0047 — Wire the Forward Graph Constraint into the Chat Hot Path

**Status:** Accepted
**Date:** 2026-05-18
**Author:** Shay

---

## Context

[ADR-0046](./ADR-0046-forward-graph-constraint.md) introduced
`generate/graph_constraint.py:build_graph_constraint` — a function that
converts a `PropositionGraph` into an `AdmissibilityRegion` *before*
`generate()` runs.  ADR-0046 explicitly deferred the hot-path wire-up:

> *"The coupling between `chat/runtime.py` and `build_graph_constraint`
> is available but the hot-path wire-up is a follow-up ADR (wire when
> the intent bridge returns a non-empty graph on the main path)."*

This ADR closes that follow-up.  As of merge, the only call site that
built a `PropositionGraph` (`generate/intent_bridge.py:articulate_with_intent`)
did so *after* `generate()` returned, using the walk's recalled tokens
to fill `<pending>` object slots.  The graph still described the field
rather than constraining it.

---

## Decision

1. Expose a public graph builder from `generate/intent_bridge.py`:

   ```python
   def build_graph_from_input(text: str, plan: ArticulationPlan) -> PropositionGraph
   ```

   Same internal call as `_build_graph_from_intent`, just without the
   post-generation `ground_graph` step — suitable for forward use.

2. Add a config flag on `RuntimeConfig`:

   ```python
   forward_graph_constraint: bool = False
   ```

   Default `False` preserves all pre-ADR-0046 behaviour.

3. In `chat/runtime.py`, when the flag is `True` and the runtime is
   operating on the English path, build the graph and the region
   **before** `generate()` and pass it through:

   ```python
   forward_region = None
   if self.config.forward_graph_constraint and self.config.output_language == "en":
       pre_gen_graph = build_graph_from_input(text, articulation)
       forward_region = build_graph_constraint(pre_gen_graph, self._context.vocab)

   result = generate(
       ...,
       region=forward_region,
       ...,
   )
   ```

The post-generation `articulate_with_intent` path is left alone — it
still grounds `<pending>` slots from the recalled tokens for surface
realization.

---

## Why opt-in, not always-on

A first attempt wired the constraint unconditionally on the English
path and produced 15 test failures across the smoke and cognition
suites:

```
generate.exhaustion.InnerLoopExhaustion:
  AdmissibilityRegion[graph:p0] left no walk candidates.
```

`InnerLoopExhaustion` (ADR-0024) is doing exactly what it is supposed
to do — refusing honestly when the admissibility region's intersection
with the walk's candidate pool is empty.  The finding is that for many
benign inputs the intent-derived graph's CGA neighbourhood **does not
intersect** the walk's pool with `top_k = 8` on the current pack
sizes.  Either:

- The graph's anchor surfaces are in vocabulary but their top-k
  geometric neighbourhood does not overlap with the language/salience-
  filtered candidate set produced by the walk on that field state, or
- The graph nodes use `<pending>` / function-word slots whose
  versors are not where the walk is operating.

The honest response to that finding is **not** to widen `top_k` until
the failure goes away, and **not** to silently fall back to
unconstrained — both would erase the architectural information that
the geometry of the graph and the geometry of the walk are not yet
co-located.  Opt-in preserves the ADR-0024 refusal contract intact
and lets operators observe the behaviour on their workloads before
deciding whether to make it default-on.

This mirrors the ADR-0022 → ADR-0026 transition-window pattern:
ship the capability behind a flag, characterise empirically, then
decide on default behaviour in a follow-up.

---

## Characterisation — `core eval cognition`

A/B run on the 13-case public cognition split, identical
`RuntimeConfig` except for the flag:

| Metric                    | Flag OFF | Flag ON | Δ      |
|---------------------------|----------|---------|--------|
| `intent_accuracy`         | 100.0 %  | 100.0 % | 0      |
| `surface_groundedness`    | 15.4 %   | 15.4 %  | 0      |
| `term_capture_rate`       | 0.0 %    | 0.0 %   | 0      |
| `versor_closure_rate`     | 100.0 %  | 100.0 % | 0      |
| `InnerLoopExhaustion`     | 0        | 0       | 0      |
| Cases producing non-trivial constraint | n/a | **6 / 13** | — |

Per-case constraint engagement (flag ON):

| Case                                | Subject                         | Region              |
|-------------------------------------|---------------------------------|---------------------|
| Why does knowledge require evidence? | "does knowledge require evidence" | `graph:unconstrained` |
| Why does light exist?               | "does light exist"              | `graph:unconstrained` |
| **Compare memory and recall**       | "memory"                        | **`graph:p0`**      |
| **No, correction means reviewed repair** | ", correction means reviewed repair" | **`graph:p0`** |
| **What is knowledge?**              | "knowledge"                     | **`graph:p0`**      |
| **What is light?**                  | "light"                         | **`graph:p0`**      |
| **What is meaning?**                | "meaning"                       | **`graph:p0`**      |
| What is a procedure?                | "a procedure"                   | `graph:unconstrained` |
| What is a relation?                 | "a relation"                    | `graph:unconstrained` |
| How can I correct an error?         | "correct an error"              | `graph:unconstrained` |
| **Remember light**                  | "light"                         | **`graph:p0`**      |
| light logos                         | "light logos"                   | `graph:unconstrained` |
| Does memory require recall?         | "Does memory require recall?"   | `graph:unconstrained` |

### What this tells us

- **Wiring is correct and safe.**  No exhaustions; closure unchanged;
  intent classification unchanged.  When the graph names a single
  in-vocabulary concept (`light`, `knowledge`, `meaning`, `memory`,
  `correction`), the constraint engages.
- **Multi-word subject phrases bypass the constraint.**  The intent
  classifier returns the full subject phrase (`"does light exist"`,
  `"a procedure"`); the graph builder uses this directly; none of
  those multi-word surfaces are present in `en_core_cognition_v1`,
  so the graph builder produces a node whose subject surface is OOV
  and `build_graph_constraint` falls back to unconstrained.  This is
  not a bug in the constraint — it is the existing intent-classifier
  contract surfacing into the geometry layer.
- **The cognition lane's grounding gap is not in the candidate set.**
  Six cases narrow the walk's admissible vocabulary, yet
  `surface_groundedness` and `term_capture_rate` are byte-identical.
  Restricting *which* tokens the walk may visit did not change
  *what surface gets emitted* on this lane.  The surface-grounding
  gap therefore lives downstream of propagation — in the realizer /
  surface-assembly / dialogue role-resolution path — and is the
  next load-bearing pull.  This isolates the next ADR's scope.

---

## Consequences

### What changes

- `chat/runtime.py` now calls `build_graph_constraint` before
  `generate()` when `forward_graph_constraint` is enabled.
- `generate/intent_bridge.py` exposes `build_graph_from_input` as a
  public helper.  `_build_graph_from_intent` retained for internal use.
- `RuntimeConfig` gains one opt-in field; frozen dataclass contract
  preserved.

### What does not change

- `generate()` signature is unchanged (region already accepted via
  ADR-0022).
- Default runtime behaviour is byte-identical to pre-ADR-0047 main.
- ADR-0024 honest-refusal contract is intact — when an operator
  enables the flag on inputs that produce a too-tight constraint,
  the runtime refuses rather than silently relaxing.
- `versor_condition < 1e-6` invariant is unaffected (constraint
  filters indices, not rotor construction).

### Scope limits

- The graph builder is English-specific; the runtime guard restricts
  forward-constraint computation to `output_language == "en"`.
- The behaviour of the constraint on multi-word OOV subject phrases
  is the current intent-classifier contract — narrowing it (subject-
  span normalisation, single-token reduction) is out of scope and a
  candidate follow-up.
- `top_k = 8` is inherited from ADR-0046's default; this ADR does not
  re-tune it.  An eval that *does* differentiate flag ON vs OFF will
  need to land before any tuning is justified.

---

## Cross-References

- [ADR-0018](./ADR-0018-tool-use-scope.md) — original
  `intent_bridge` producing the post-hoc graph.
- [ADR-0022](./ADR-0022-forward-semantic-control.md) — the
  `AdmissibilityRegion` contract this ADR feeds into.
- [ADR-0024](./ADR-0024-inner-loop-admissibility.md) — the honest-
  refusal contract that fires when the constraint is too tight; the
  reason this ADR is opt-in.
- [ADR-0046](./ADR-0046-forward-graph-constraint.md) — the constraint
  primitive that this ADR wires into the live path.

---

## Verification

```
tests/test_forward_graph_constraint_wiring.py  — 5 tests, all green

Lanes (all green on this branch):
  core test --suite smoke         67 passed
  core test --suite cognition    121 passed
  core test --suite runtime       19 passed
  core test --suite algebra      132 passed
  core test --suite teaching      17 passed
  core test --suite packs          6 passed
  core eval cognition            metrics unchanged from main
                                 (flag OFF default = pre-ADR-0047)
```

The non-negotiable field invariant (`versor_condition(F) < 1e-6`)
remains satisfied: this ADR only changes which indices the walk
considers — it does not touch rotor construction, sandwich
application, or field update.
