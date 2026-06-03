# ROBDD Proof-Chain Design Note

**Status:** research note; reconciled with ADR-0201 / ADR-0202  
**Scope:** propositional canonicalizer and proof-corpus design support  
**Date:** 2026-06-02

This note is syntax-independent at the proof-corpus level, but the formula
grammar and atom contract are now fixed by ADR-0202. The canonicalizer internals
and canonical-key string are fixed by ADR-0201. Proof-chain DAG wiring and
inference-rule result objects remain future work.

## Executive Shape

Reduced ordered binary decision diagrams (ROBDDs) are a good fit for the
propositional proof-chain keystone because they make the intrinsic space of a
proposition explicit: a Boolean function over a fixed ordered variable space.
Within that space, equivalence is structural identity, not a rewrite guess.

The honesty boundary is just as important: this applies to propositional logic
under a fixed variable ordering. It does not transfer to predicate logic,
quantifiers, ungrounded propositions, or proof graphs with circular dependency.
Those cases should refuse with typed reasons rather than approximate.

## Minimal Hand-Rolled Requirements

A minimal ROBDD manager needs these pieces:

- Two terminal leaves, `FALSE` and `TRUE`, represented by stable identities.
- Nonterminal nodes with `(variable, low, high)` where `low` is the branch for
  the variable being false and `high` is the branch for true.
- A fixed variable order shared by every proposition compared in the same
  equivalence domain.
- A `mk(variable, low, high)` constructor that is the only way to build
  nonterminal nodes.
- A unique table keyed by `(variable, low_id, high_id)`.
- A computed cache keyed by `(operator, left_id, right_id)` for binary `apply`.

The reduction rules are the load-bearing laws:

1. Eliminate redundant tests: if `low == high`, return the child.
2. Merge isomorphic subgraphs: if another node has the same variable and
   children, return the existing node identity.

When these are enforced by `mk` and the variable order is fixed, a shared ROBDD
manager gives a strong canonical form: two represented functions are equivalent
iff their reduced diagrams are isomorphic. ADR-0201 exposes that identity as a
byte-deterministic structural `canonical_key` string, with tautology serialized
as `T` and contradiction serialized as `F`.

## Apply Algorithm

The core construction operator is `apply(op, left, right)`.

At each recursive step:

1. Return from the computed cache if `(op, left, right)` was already solved.
2. Apply terminal identities when both inputs are leaves, and simple short-cuts
   where the selected operator permits them.
3. Select the topmost variable among the two input roots under the fixed order.
4. Recur on the low cofactors and high cofactors for that variable.
5. Reconstruct through `mk(top_variable, low_result, high_result)`.
6. Cache and return the resulting node.

This is propagation through the Boolean function manifold, with `mk` as the
corrective conjugate that collapses redundant or duplicated structure on the way
back up. The resulting identity is not a syntactic normal form; it is the
reduced function itself, shared in the manager.

## Variable Ordering

Variable ordering is not a cosmetic choice. ROBDD size can vary sharply across
orders, and finding an optimal ordering is itself hard. CORE should therefore
treat ordering as a deterministic contract, not an optimization contest.

For the small proof-step regime, the simplest adequate policy is:

- derive the variable set from declared proposition atoms,
- reject ungrounded variables before construction,
- sort by the ADR-0202 atom id,
- freeze that order for all propositions in a comparison or proof step.

Alternative local heuristics can be considered later only if they remain
byte-deterministic and are replayed as part of the trace. ADR-0201 chooses the
simplest v1 policy: atoms appearing in the formula, sorted lexicographically.

The important constraint is that two propositions being compared must be built
in the same manager ordering. Different orders can represent the same Boolean
function with different graph identities, so ordering must be part of the
canonicalization domain.

## Budget and Blowup Guard

Bryant's original framing is the right discipline for CORE: many practical
Boolean functions compact well, but worst-case exponential growth remains real.
The canonicalizer should therefore have an explicit budget guard, not an
implicit timeout.

Candidate budget dimensions:

- maximum variable count,
- maximum created node count,
- maximum recursive `apply` calls,
- maximum computed-cache entries,
- maximum parse/AST depth before ROBDD construction,
- maximum proof-DAG node count for proof-chain validation.

When a bound trips, the result should be the ADR-0202 typed refusal
`canonicalization_budget_exceeded`. It should not return a partial
canonical key, fall back to CNF/DNF, stochastic sampling, truth-table truncation,
or syntactic equality. Refusal preserves `wrong == 0`; churning or guessing does
not.

The budget should be part of replay evidence. A refusal is only useful if the
trace can say which bound tripped and at what count. That lets future work tune
the construction boundary from evidence without changing the logical verdict of
any completed case.

## Complement Edges

Complement edges are optional for a first implementation. They can reduce memory
by encoding negation as a bit on an edge or pointer instead of constructing a
separate complemented graph. Mature packages use this technique, but it raises
implementation obligations:

- regularize node pointers before unique-table lookup,
- define whether external root identity includes a complement mark,
- apply De Morgan transformations carefully in internal constructors,
- keep serialization byte-stable despite pointer-like internal representation.

For CORE v1, plain nodes are easier to audit. Complement edges become attractive
only if node pressure is observed under replayable benchmark evidence.

## Library vs Hand-Rolled

ADR-0201 chose the hand-rolled path. The tradeoff remains useful context for why
that choice fits the proof-step regime.

### Mature Library Path

CUDD-style packages are battle-tested. They provide unique tables, computed
caches, garbage collection, complement edges, dynamic variable reordering, and a
large operation set. That is the strongest argument for using a mature library:
the difficult low-level machinery has already been exercised by verification
workloads.

The cost is that such a dependency is heavy relative to the proof-step target:
opaque memory management, platform/build friction, optional dynamic reordering,
pointer-level identities, and many features CORE does not need for a small,
deterministic propositional corridor. If node identity is the canonical key,
library behavior must be constrained enough that replay is byte-stable.

### Minimal Hand-Rolled Path

A hand-rolled ROBDD manager is more work, but the v1 surface is compact:
terminal leaves, `mk`, unique table, computed cache, fixed variable ordering,
and `apply` for `not`, `and`, `or`, `implies`, and equivalence checking.

This path fits CORE's character when the proposition regime is deliberately
small: inspectable, deterministic, local, and easy to refuse when budgets trip.
The risk is underestimating edge cases in hash-consing, ordering, cache
invalidity, serialization, or proof-DAG interaction. Those risks should be paid
down with an independent corpus and explicit refusal tests, not hidden by broad
fallbacks.

## Proof-Chain Boundary

ROBDD identity proves truth-functional equivalence. It does not, by itself,
prove that a submitted proof chain is valid. The proof-chain layer still needs
its own structural checks:

- every referenced dependency must exist and be grounded,
- the dependency graph must be acyclic,
- each inference rule must declare the propositions it consumes,
- the derived proposition must be checked by the canonicalizer under the same
  variable-order domain,
- out-of-regime formulas must refuse before canonical-key comparison.

The first `modus_ponens` rule can be framed as a small entailment check:
dependencies contain an antecedent and a matching implication; the proposed
conclusion must match the implication's consequent in the ADR-0202 formula
representation. Future proof-chain wiring still needs to choose whether this is
implemented by syntactic pattern over parsed formula nodes, by ROBDD entailment,
or by a narrow rule object that delegates equivalence checks to the canonicalizer.

## Validation Corpus Consequences

The independent corpus should test behavior, not implementation internals. It
should therefore include:

- equivalence pairs that force real Boolean canonicalization rather than shallow
  operand sorting,
- non-equivalence near misses that catch over-collapse,
- TRUE/FALSE terminal reductions,
- valid and invalid `modus_ponens` examples,
- circular proof-DAG refusal,
- quantified/predicate out-of-regime refusal,
- budget-exceeded refusal for a scalable family.

The corpus does not assert concrete node numbers. It asserts
equality/difference of `canonical_key`, typed terminal identity (`T` / `F`), and
typed refusals under the ADR-0202 atom and formula contract.

## Confirmed Contract Points

- Formula representation: ADR-0202 grammar over declared atom ids.
- Atom grounding: per-case atoms declare `gloss` and either
  `binding.features` for intended ADR-0144/ADR-0143 FeatureBundle matching or
  `binding: null` for schematic atoms.
- Variable ordering: lexicographic sorted atoms appearing in the formula.
- Canonical key: ADR-0201 byte-deterministic structural string; `T` and `F` for
  terminal constants.
- Budget refusal: `canonicalization_budget_exceeded`.
- Complement edges: out of v1; ADR-0201 shipped a plain hand-rolled ROBDD.
- Still future proof-chain work: proof-DAG dependency object, circularity
  checker, and concrete inference-rule result object.

## Sources

- Randal E. Bryant, "Graph-Based Algorithms for Boolean Function
  Manipulation," IEEE Transactions on Computers, C-35:8, 1986.
  https://doi.org/10.1109/TC.1986.1676819
- Randal E. Bryant, "Binary Decision Diagrams: An Algorithmic Basis for
  Symbolic Model Checking," 2018 chapter draft.
  https://www.cs.cmu.edu/~bryant/pubdir/hmc-bdd18.pdf
- Fabio Somenzi, CUDD Programmer's Manual, release 2.5.0.
  https://www.cs.rice.edu/~lm30/RSynth/CUDD/cudd/doc/
- Seiichiro Tani, Kiyoharu Hamaguchi, and Shuzo Yajima, "The complexity of the
  optimal variable ordering problems of shared binary decision diagrams,"
  ISAAC 1993. https://doi.org/10.1007/3-540-57568-5_270
