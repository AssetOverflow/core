<!-- FILE: docs/analysis/solver-operation-coverage.md -->

# Solver Operation Coverage Audit

Status: Proposed analysis draft. No serving behavior is changed. This is a
read-only structural audit to de-risk ADR-0174 Phase 5b / Phase-4-style
composition work. Verdicts below are code-reading conclusions only; they must be
verified in the Claude lane with executable solver/binding-graph cases before
any promotion claim.

## Scope

Read surfaces:

- `generate/math_problem_graph.py`
- `generate/math_solver.py`
- `generate/binding_graph/{model,adapter,admissibility,allocation,question_target,units}.py`
- ADR-0116, ADR-0117, ADR-0132, ADR-0133, ADR-0134, ADR-0135
- Skimmed ADR-0174 Phase 5b and ADR-0203/0204/0205 to confirm current
  composition/proof-DAG framing.

Important correction to the relay: the current solver/graph vocabulary is not
only `{add, subtract, transfer, multiply, divide}`. `MathProblemGraph` and
`math_solver` both include the eight operation kinds:

```text
add, subtract, transfer, multiply, divide,
apply_rate, compare_additive, compare_multiplicative
```

ADR-0174 Phase 5b states the same: the solver is already waiting for these
operations; the gap is reader -> injector -> `Operation` front-end wiring plus
composition.

## Existing Operation Substrate

| Surface | Evidence | Consequence |
|---|---|---|
| Closed operation vocabulary | `generate/math_problem_graph.py` defines `VALID_OPERATION_KINDS` with eight kinds. | New arithmetic verbs are not needed for ordinary multiply/divide/rate/comparison chains. |
| Pack-bound solver dispatch | `generate/math_solver.py` maps all eight kinds to `en_arithmetic_v1` lemmas before solving. | Missing pack lemmas fail loudly; no hidden operation fallback. |
| Stateful solver semantics | `_apply` mutates `(actor, unit)` terminal state for `add`, `subtract`, `transfer`, `multiply`, `divide`; `_apply_rate` produces numerator-unit state from denominator-unit state; comparisons derive an actor state from a reference actor. | The solver is good at forward state trajectories, but weak at keeping multiple same-unit derived intermediates alive under one actor. |
| Unknown shape | `Unknown(entity, unit)` resolves either terminal state for one entity or total-across all entities with that unit. | Target questions that ask for a missing operand, number of iterations, or intermediate state are not represented by `Unknown` alone. |
| Binding-graph equation/data model | `BoundEquation(operation_kind=...)`, `BoundUnknown(question_form=...)`, semantic roles include `rate`, `duration`, `difference`, `ratio`. | The graph can name richer forms than the solver's final `Unknown`, but current adapter still comes from existing `MathProblemGraph` operation chains. |
| Unit admissibility | `check_admissibility` covers additive, multiplicative, divide, `apply_rate`, and comparison kinds. | Dimensional proofs exist for the current eight operation kinds; new node types would need explicit admissibility rules. |
| Question-target binding | `infer_question_form` recognizes `ratio`, `difference`, `rate`, `total`, and `count` from operation kinds touching the unknown. | It can label answer form, but it does not solve inverse targets or select intermediate operation indices yet. |
| Acyclicity | ADR-0203 adds `circular_dependency` refusal to the shared binding-graph constructor. | Any new equation/intermediate-node extension must remain a DAG, not a cyclic algebra system hidden inside the graph. |

## Phase-4 Target Chains

| Target chain | Verdict | Existing operations that can carry it | What is missing / risk |
|---|---|---|---|
| Multi-step rate-sum | Expressible via composition for straight-line rate applications and sums. Piecewise tariffs/conditionals need scoped selection before admission. | `apply_rate` computes `X/Y * Y -> X`; `add`/`subtract` can aggregate generated same-unit totals. Binding admissibility has an `apply_rate` rule requiring one rate dep plus one duration/count dep. | The reader must emit the base duration/count quantities, rate hypotheses, and sum operations without clobbering unrelated same-unit state. Piecewise tariffs such as "$50/day or $500/14 days" need a tariff/choice scope or explicit branch-disagreement gate; that is a binding/composition problem, not a missing arithmetic verb. |
| Ratio chain | Expressible via composition for forward ratio chains. Inverse ratio equations need a target/equation extension. | `compare_multiplicative` supports "actor = factor * reference"; `multiply`/`divide` support scalar transformations; `infer_question_form` maps touching `compare_multiplicative` to `ratio`. | Forward chains like `A`, `B = 2A`, `C = 1/2(A+B)` can be represented if the reader emits the right reference actors and order. Inverse forms such as "ducks are 10 more than 4x chickens; ducks = 150; find total birds" require solving for an unknown reference, not just applying a forward operation. That needs equation/target solving or a new binding node shape, not a new `ratio` operation kind. |
| Accumulate-against-target | Needs new binding-graph target/equation capability; not expressible as a fixed existing operation chain in the current solver. | `add`, `subtract`, `multiply`, `divide`, and `apply_rate` can express the arithmetic once the iteration count or missing operand is known. | The current solver consumes a fully specified graph in source order, then resolves terminal `Unknown(entity, unit)`. It cannot represent "after how many weeks", "how many cups to sell to reach profit", or "how long to make back cost" as an unknown operand/iteration count. This needs a first-class target-slot/equation node or bounded inverse solver with refusal/disagreement, plus proof that no cyclic dependency is introduced. |
| Percent/fraction mutation | Mostly expressible via composition for forward mutations; needs intermediate-symbol/scope support for same-unit derived amounts and event subsets. | Percent/fraction values can be scalar `multiply`/`divide` factors, with `add`/`subtract` for mutation and `compare_multiplicative` for relative quantities. Binding admissibility already covers multiply/divide dimensions. | Some cases are safe forward mutations ("eat 75% of a pan", "lose half"). Others require original and derived same-unit quantities to coexist, e.g. principal plus interest, insured vs uninsured portions, operating cost as percent of startup cost. The current solver overwrites `(actor, unit)` for multiply/divide and `apply_rate`, so these need derived intermediate symbols/event scopes or separate binding nodes. A new `percent` operation kind is not structurally necessary; a new scoped intermediate/equation representation may be. |

## Structural Verdict

Phase 4/5b is mostly **not** blocked by missing arithmetic operation kinds. The
current operation vocabulary already covers the primitive arithmetic field:
addition/subtraction/transfer, scalar multiply/divide, rate application, and
additive/multiplicative comparison.

The real scope risk is representation:

- Can the reader emit a chain of typed operations from scattered clauses while
  preserving all grounded quantities?
- Can the graph retain intermediate derived quantities when they share the same
  actor/unit as their source?
- Can a question bind to a missing operand, iteration count, or intermediate
  state instead of only terminal `Unknown(entity, unit)`?
- Can inverse/equation targets be solved under a disagreement rule and the
  ADR-0203 acyclicity invariant?

That makes the likely build a **binding-target / intermediate-symbol /
derivation-composer extension**, not a broad new solver primitive pack.

## Chain-Specific Notes

### Multi-step rate-sum

`apply_rate` is first-class: the solver's `_apply_rate` reads the actor's
denominator-unit state and writes numerator-unit state. The binding-graph
adapter synthesizes a rate symbol with composite unit `<num>_per_<denom>`, and
admissibility checks that the denominator cancels. Therefore simple rate-sum is
expressible as:

```text
duration/count fact -> apply_rate -> produced total
produced totals -> add/subtract -> final total
```

The unsafe part is not the operation. It is branch selection and scope:
overtime, tariffs, and "including today" require deciding which rate applies to
which event subset.

### Ratio chain

`compare_multiplicative` already gives a forward ratio operation. It refuses
when the reference actor has no quantity or multiple ambiguous units, which is
the right wrong=0 boundary. Binding target can label ratio-form questions.

The gap is inverse ratio. Current `Operation` is directional: it mutates the
actor from a known reference. If the reference is the unknown and the actor is
given, the solver has no inverse-equation mode.

### Accumulate-against-target

This is the clearest "needs new graph shape" target. A terminal state solver can
answer "what is the total after N weeks"; it cannot answer "what N reaches total
T" unless N is already present as a quantity and a divide operation has been
materialized by the reader. A safe implementation needs a target slot that names
the missing operand/iteration count and an admissibility/disagreement rule for
the inverse derivation.

### Percent/fraction mutation

Percent/fraction does not need a new arithmetic verb. It needs:

- scalar extraction (`75% -> 0.75`, `1/4 -> 0.25`);
- complement derivation when the text says "covers 80%" but the cost asks for
  the uncovered part;
- event/subset scoping ("after the first appointment", "subsequent visits");
- intermediate symbols when original principal/cost and derived interest/cost
  must both remain available.

The binding graph is the natural home for these intermediates because it already
has `BoundEquation`, dependency sets, unit proofs, question forms, and
acyclicity checks.

## Open Questions for the Claude Lane

- Does `apply_rate` overwriting `(actor, numerator_unit)` create a concrete
  hazard in rate-sum cases where the actor already holds money? If yes, the
  build needs derived result symbols before promotion.
- Should inverse target solving be introduced as a new `BoundUnknown` form, a
  new `BoundEquation` operation kind, or a separate proof/derivation rule over
  existing equations?
- Can forward ratio chains be admitted through `compare_multiplicative` without
  widening the parser's reference-actor ambiguity beyond the existing refusal
  discipline?
- What is the smallest executable probe set that distinguishes "new operation
  kind required" from "same operation, new intermediate symbol required" for
  percent/fraction mutations?
- When proof-DAG consumers and math binding graphs share
  `SemanticSymbolicBindingGraph`, should proposition-specific operation kinds
  remain isolated from math admissibility, or should the admissibility dispatcher
  split into math/proof entrypoints before more equation kinds are added?
