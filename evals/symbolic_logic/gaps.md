# symbolic-logic lane — architectural findings

## Finding: No first-class inference operator

CORE has no operator that takes premises `A→B`, `B→C` and returns `A→C`.
Inference, when it happens, is emergent from:

- The teaching loop committing each correction premise to the vault.
- The probe's CGA recall surfacing entries that were geometrically
  linked by the cumulative field state.
- The realizer composing a surface from whatever the recall returned.

This is not the same as named-rule symbolic inference (modus ponens,
modus tollens, syllogism).  The v1 lane therefore measures the
*foundations* that any future inference operator would require:

- Premise chains store deterministically (M3).
- Premise chains replay deterministically (M2).
- Premise chains are recallable from probe state (M1).

A v2 lane would assert specific inference correctness — e.g., after
teaching `A is B` and `B is C`, the probe `What is A?` produces a
surface mentioning `C` (transitive recall through the relation graph).
That requires either:

- A first-class proposition-graph traversal operator on top of the
  vault, or
- A pack-axiom layer where pack-declared `A→B` rules participate in
  recall.

Neither exists in the current runtime.  The v1 lane is honest about
this; it tests what CORE *does* deterministically (chain storage and
replay) without overclaiming that CORE *reasons* symbolically.

## Suggested follow-up work

1. **PropositionGraph + reasoning operator**: Add an explicit module
   that consumes the cumulative teaching store, builds a relation
   graph, and applies named inference rules.  Output: an
   `inference_trace` field on `CognitiveTurnResult` carrying the
   rule chain that derived a recalled conclusion.

2. **Pack-axiom rules**: Extend pack manifests to declare rules
   (`X is_a Y`, `Y is_a Z` → `X is_a Z`).  Compile rules into versor
   space so recall can traverse them deterministically.

3. **v2 symbolic-logic lane**: Score correctness of specific
   inference outputs (e.g., probe surface contains the transitive
   target), not just chain storage.
