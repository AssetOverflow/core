# ADR-0201 — Propositional Canonicalizer (the `proof_chain` keystone)

**Status:** Proposed (Phase 1 of `proof_chain`; standalone keystone shipped, not yet wired)

**Date:** 2026-06-02

**Relates to:** ADR-0131.1.B (`math_symbolic_equivalence` — the sibling pattern this
mirrors), ADR-0132/0133/0134/0135 (binding-graph data model / adapter /
admissibility / question-target — the future consumer), the `wrong == 0`
self-verification doctrine in `generate/derivation/verify.py`.

## Context

CORE has confirmed three things about building `proof_chain` as a real reasoning
primitive (not a declared label):

1. The ledger "operators" (`proof_chain`/`causal`/`modal`) are classification
   labels, not executors — `proof_chain` is green-field.
2. The `wrong == 0` self-check is **soundness, not correctness**: it fires only
   when grounded+licensed derivations collapse to **one unique canonical
   conclusion** and rivals are checked for agreement. It needs a *canonical,
   comparable* conclusion. For arithmetic, exact numeric equality gave that for
   free.
3. The ADR-0132 binding graph is already the DAG substrate proof trees need
   (`BoundEquation.dependencies` + per-node admissibility + provenance), with a
   shipped, hand-rolled sibling — `math_symbolic_equivalence` — that already
   demonstrates the `normalize → canonical-string → byte-equality →
   three-valued-verdict-with-REFUSED` discipline for algebra.

Logic does **not** get a comparable canonical conclusion for free: two
syntactically different formulas can be logically equivalent (`P∧Q ≡ Q∧P`,
`¬¬P ≡ P`, `P→Q ≡ ¬P∨Q`). Without a canonical form, the uniqueness/disagreement
rule cannot fire and `proof_chain` degrades from sound to merely cautious. This
ADR scopes the canonical form — the keystone everything else (rule checkers, the
disagreement rule) depends on.

## Decision

Canonicalize a propositional formula to a **Reduced Ordered Binary Decision
Diagram (ROBDD)** under a fixed (sorted-atom) variable ordering, and use a
canonical *string* serialization of the reduced diagram as the byte-equality
discriminator (the logic analog of `Polynomial.to_canonical_string()`).

- **ROBDD, not CNF/DNF.** For a fixed ordering the ROBDD is *canonical* — two
  formulas are logically equivalent **iff** their reduced diagrams are isomorphic.
  CNF/DNF are merely *normal* (standardized shape), not canonical, and have no
  poly-time equivalence-preserving transform. Free bonuses for later: tautology =
  the 1-terminal, contradiction = the 0-terminal, `f→g` valid iff
  `apply(f, ¬g, ∧)` = the 0-terminal — so `contradiction` and proof "conclusion
  follows" reduce to ROBDD checks.
- **Hand-rolled minimal**, no external BDD library (operator-confirmed). Stays in
  CORE's idiom (the symbolic substrate is entirely hand-rolled), deterministic by
  construction, fully inspectable, zero opaque dependencies. ~370 LOC:
  tokenizer + recursive-descent parser + `mk`/`apply`/`negate` + unique table +
  canonical serialization.
- **`wrong == 0` discipline preserved.** No approximate path. Out-of-grammar input
  raises `LogicError`; a diagram exceeding the node budget raises
  `LogicBudgetError` (a `LogicError` subclass, so callers refusing on `LogicError`
  refuse on budget too). Both surface as a `REFUSED` verdict — refuse rather than
  guess or churn.

## Honesty boundary (stated, not hidden)

- **Propositional logic** (finite Boolean variables): canonical and decidable.
  ROBDD gives a unique form + constant-time equivalence. The full soundness gate
  transfers. **This is the only regime this module claims.**
- **Cost caveat:** ROBDD *size* can be exponential in the worst case and is
  ordering-sensitive. Canonicity is cheap to *compare* but not always cheap to
  *build*. For bounded proof-step propositions (a handful of atoms) this is a
  non-issue; the node budget refuses on adversarial blowup rather than hanging.
- **Predicate / first-order logic:** NOT canonical in general — undecidable. There
  is no ROBDD-style canonical form for full FOL. **We do NOT claim `wrong == 0`
  for quantified reasoning** with this machinery. Quantifier-free fragments and
  specific decidable theories are later, separately-scoped steps, each with their
  own honest decidability claim.

## What shipped in this phase (standalone)

- `generate/logic_canonical.py` — `canonicalize(formula, *, max_nodes) ->
  CanonicalProposition{canonical_key, atoms, is_tautology, is_contradiction}`;
  `LogicError` / `LogicBudgetError`.
- `generate/logic_equivalence.py` — `check_equivalence(a, b) ->
  EquivalenceVerdict{EQUIVALENT|NOT_EQUIVALENT|REFUSED}` (close mirror of
  `math_symbolic_equivalence`).
- `tests/test_logic_canonical.py` — 33 standalone tests: canonicity laws
  (commutativity, double-negation, De Morgan, implication rewrite, distributivity,
  absorption, irrelevant-variable elision), discrimination (non-equivalent →
  distinct keys), terminal collapse, byte-determinism, operator-spelling parity,
  and the refusal paths (malformed → `LogicError`; budget blowup → `LogicBudgetError`).

Tested **in isolation**, exactly as the sibling is standalone — proving the
keystone holds alone before anything depends on it.

## Proof obligation (per CLAUDE.md §Schema-Defined Proof Obligations)

The canonicity tests must be able to *meaningfully fail*. Verified by mutation:
disabling the redundant-node reduction rule (`low == high → low`) flips
`P ∧ (Q ∨ ¬Q) ≡ P` to false, failing `test_irrelevant_variable_is_dropped_from_support`.
The equivalent-pairs and non-equivalent-pairs suites are mutually constraining: a
collapse-everything canonicalizer fails discrimination; a no-reduction
canonicalizer fails equivalence. The suite is non-vacuous by construction.

## Explicitly deferred (NOT in this phase)

- **Binding-graph wiring.** `proof_chain` would be the binding graph's *first*
  consumer — there is no existing graph-builder→serving path to join. The
  integration is **net-new wiring**, scoped separately. The canonical key is
  designed to drop into `BoundEquation.rhs_canonical` (a string field) when that
  wiring is built.
- **The acyclicity refusal.** A cycle in a proof DAG is circular reasoning; the
  binding graph currently checks referential integrity but not cycles. The
  `circular_dependency` refusal is net-new and must land *before* the structure
  is load-bearing — not in this standalone phase.
- **Inference rules.** No `operation_kind` logic vocab and no `_check_modus_ponens`
  yet. One sound rule (`modus_ponens`) + the disagreement rule on the canonical
  key is the next phase, once this keystone is accepted.

## Alternatives considered

- **CNF/DNF canonical string** — rejected: not canonical (clause/literal ordering
  is non-unique), and no poly-time equivalence-preserving transform exists.
- **External BDD library (`dd` / CUDD)** — rejected: the only opaque dependency in
  an otherwise hand-rolled substrate; determinism/`trace_hash` risk from
  hash-based node ids and reordering heuristics; CUDD is a C build/footprint cost;
  and the canonical-string serialization would still need to be hand-controlled
  for determinism, so the library does not save the load-bearing work.
