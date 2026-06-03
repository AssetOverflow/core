# ADR-0203 — Binding-Graph Acyclicity Invariant (`circular_dependency` refusal)

**Status:** Accepted (proof_chain phase 2.1 — the isolated guard; ADR-0201 §Deferred)
**Date:** 2026-06-02
**Relates to:** **ADR-0132** (binding-graph data model — this *adds* an invariant to
its construction contract; see §amend-vs-additive), ADR-0201 (canonicalizer +
phase plan), ADR-0202 (proposition representation contract).

---

## Context

ADR-0132's `SemanticSymbolicBindingGraph.__post_init__` enforces **referential
integrity** (every `BoundEquation` dependency names a known symbol) but **not
acyclicity**. A cycle in the equation dependency structure — `x` defined from `y`,
`y` defined from `x`, or a self-dependency `x ← x` — is **circular reasoning**:
structurally well-formed, semantically invalid. It is the proof-domain analog of
the `20/5 == 4` class the arithmetic gate refuses.

`proof_chain` (ADR-0201) is the first consumer that can *build* such a structure:
its phase 2.2 wiring constructs binding graphs from proofs, where a malformed proof
could close a dependency loop. Per CORE's "build the defensive refusal NOW"
discipline, the guard must exist **before** the structure where a cycle can exist —
so this phase (2.1) lands it *before* any 2.2 wiring.

## Decision

Add an **acyclicity invariant** to binding-graph construction:

- **`generate/binding_graph/acyclicity.py`** — a pure `find_cycle(adjacency)`
  cycle detector (deterministic three-colour DFS; sorted traversal → byte-stable
  reported cycle; self-edge → length-1 cycle). No model import — testable in
  isolation against synthetic adjacency graphs.
- **Enforcement at the shared construction boundary.** `__post_init__` builds a
  `{lhs_symbol_id: ⋃ dependencies}` adjacency over its equations and calls
  `find_cycle`; a non-`None` result raises
  `BindingGraphError("circular_dependency: equation dependency cycle …")` naming
  the cycle. This runs on **every** binding graph — math and (future) proof alike —
  making a cyclic graph unrepresentable for all consumers.

### Why the shared `__post_init__` (not a proof-only check)

Putting it at the substrate boundary closes the gap universally and makes illegal
states unrepresentable (the CLAUDE.md design principle), rather than leaving the
math binding graph cycle-unchecked. The guard exists the instant the structure
becomes constructible — strictly *before* the proof wiring that makes a cycle
reachable.

### Math-lane regression proof (the shared-constructor risk)

Because the guard runs on the existing math/algebra path too, it must refuse no
existing graph. Verified:

- The **only** production producer is `generate/binding_graph/adapter.py`
  (`bind_math_problem_graph`). It mints a **fresh** result symbol per operation
  (`_op_result_symbol_id(idx)`) and depends only on symbols that already exist —
  edges point strictly backward in construction order. It is therefore **acyclic
  by construction** and cannot produce a graph this guard would refuse.
- No existing test constructs a dependency cycle (the `sym_ghost` fixture is the
  referential-integrity refusal, not a cycle).
- The **full binding-graph + admissibility test surface — 392 tests — stays
  green** with the guard in `__post_init__`. (Smoke: 67 passed.)

A future/in-flight consumer that *did* build a cycle would now be refused at
construction — which is the point.

## amend-vs-additive (ADR-0203 vs amending ADR-0132)

**Decision: a new additive ADR (this one) that references ADR-0132 — not an
amendment of the closed record.**

ADR-0132 is `Accepted`. The acyclicity invariant was not part of its original
decision; it became necessary later, when `proof_chain` made cycles *reachable*.
Recording it as a new invariant preserves that history — *why* the guard was added
and *when it became load-bearing* — which an in-place edit of the closed record
would erase. This mirrors the history-vs-current-state discipline used elsewhere
(append the new fact; don't rewrite the settled one). The code lives beside
ADR-0132's referential-integrity check in `__post_init__`; the *decision record* is
additive.

## Honesty boundary (load-bearing — carried by every phase-2 ADR, 0203–0205)

Through phase 2.3, `proof_chain` is **sound over its declared atoms** — it does
**not** reason over recognized input. Atoms are opaque/declared symbol ids
(ADR-0202); grounding them to ADR-0144 `EpistemicNode`/`FeatureBundle` carriers is
**phase 2.4** (fork B). This must **never** be softened to "reasons over input"
before 2.4 lands. This ADR is structure-only and makes no grounding claim; it is
named here so the boundary travels with the work, not just with the rule ADRs.

## Evidence

- `tests/test_binding_graph_acyclicity.py` — 17 tests: pure checker (acyclic→None;
  self-loop/2-/3-cycle/cycle-with-tail detected; deterministic), construction
  enforcement (cyclic + self-dependent refuse; acyclic + adapter-shape construct),
  and referential-integrity-still-fires-first.
- **Mutation-verified non-vacuous:** neutering `find_cycle` (→ always `None`) makes
  a 2-cycle construct without refusal — `test_two_cycle_equation_set_refuses` would
  fail. The guard is load-bearing, not decoration.
- Full binding-graph/admissibility surface: **392 passed**. Smoke: **67 passed**.

## Deferred (not in this phase)

- **2.2** — proof-graph builder (proof → `BoundEquation`s; `canonical_key` →
  `rhs_canonical`); the first construction that exercises this guard through the
  real proof path (ADR-0204).
- **2.3** — `modus_ponens` + the disagreement rule (ADR-0205).
- **2.4** — atom→`EpistemicNode` carrier grounding (ADR-0206).
