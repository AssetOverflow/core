# ADR-0135 — Binding Graph Phase 4: question-target binding refinement

**Status:** Accepted.
**Parents:** [ADR-0132](ADR-0132-binding-graph-data-model.md),
[ADR-0133](ADR-0133-binding-graph-adapter.md),
[ADR-0134](ADR-0134-binding-graph-admissibility.md).
**Phase 5 (bounded-grammar / B3 integration):** deferred.

## Context

Phases 1–3 produced a `SemanticSymbolicBindingGraph` containing a
`BoundUnknown` that named the symbol the question targets — but only
the symbol *identity*, not its *temporal index* nor the *shape of the
expected answer*.

For "How many apples does Tina have?" with a three-operation
trajectory, the adapter's `BoundUnknown` did not distinguish between
Tina's apples at `t=0`, after the second operation, or at the terminal
state. Three different symbols, one ambiguous question.

Likewise, "How much faster did Tina run?" and "How many apples does
Tina have?" both compile down to a `BoundUnknown` pointing at a symbol,
but the *verdict shape* a downstream consumer should produce
(`difference` vs. `count`) is qualitatively different.

Phase 4 closes that ambiguity *deterministically* at the binding-graph
layer, without invoking a solver or grammar.

## Decision

### Two new required fields on `BoundUnknown`

- `state_index: StateIndex` — a closed tagged union:
  `Literal["initial", "terminal"]` or `Operation(operation_index: int)`,
  where `Operation` is a frozen dataclass (not a string) so the index
  is type-checked at construction.
- `question_form: Literal["count", "rate", "total", "difference",
  "ratio", "identity"]`.

Both fields are **required** — no defaults. Phase 1–3 fixtures that
construct `BoundUnknown` directly have been updated in the same PR.

### Pure-function resolvers — `generate/binding_graph/question_target.py`

- `resolve_state_index(g)` — `"terminal"` when `g.operations` is
  non-empty, `"initial"` otherwise. The `Operation` variant is reserved
  for future intermediate-state queries; this resolver does not yet
  produce it.
- `infer_question_form(g)` — closed dispatch over operations that
  *touch* the unknown's entity (actor / target / `Comparison`
  `reference_actor` matches). Precedence rule (deterministic):

  1. No operations touch → `"identity"`.
  2. Any `compare_multiplicative` touches → `"ratio"`.
  3. Any `compare_additive` touches → `"difference"`.
  4. Any `apply_rate` touches → `"total"` when `unknown.unit ==
     numerator_unit`; `"rate"` when `unknown.unit == denominator_unit`;
     otherwise refuse (`apply_rate_unit_mismatch`).
  5. All touching kinds in `{add, subtract, transfer, multiply,
     divide}` → `"count"`.
  6. Anything else → refuse (`unmappable_question_form`).

  The precedence is **closed and ordered**, not a heuristic. A graph
  mixing `compare_additive` with `add` returns `"difference"` because
  the comparison establishes the question's shape regardless of any
  downstream arithmetic.

- `bound_unknown_from_math_problem_graph(g)` — composes the above and
  yields a fully-populated `BoundUnknown`. The adapter (ADR-0133) calls
  this in place of its old ad-hoc mapping.

### Refusal-first via `QuestionTargetError`

Sibling of `AdapterError` and `AdmissibilityError`. Reasons are a
closed set:

- `not_a_math_problem_graph`
- `unknown_entity_not_in_entities`
- `apply_rate_unit_mismatch`
- `unmappable_question_form`

The resolver never silently coerces to a default — ambiguity refuses.

### Cross-collection guard

`SemanticSymbolicBindingGraph.__post_init__` adds: if any
`BoundUnknown.state_index` is an `Operation`, its `operation_index`
must be `< len(equations)`. Standalone `BoundUnknown` construction
checks only the sign (`>= 0`).

## Invariants preserved

- `bind_math_problem_graph(g)` remains pure and deterministic.
  Byte-equal across runs on a given `g`. The canonical-string emission
  changes shape (now includes `state=…` and `form=…` tokens), so
  hashes differ from Phase 3 main *by design* — not a regression.
- No runtime wiring. No solver coupling. No mutation of
  `MathProblemGraph`. No `algebra/`, `chat/`, `core/` edits.
- Field-invariant `versor_condition(F) < 1e-6` untouched.

## Phase 5 — deferred

Bounded-grammar / B3 integration remains out of scope. Phase 4 only
determines *which symbol* the question targets and *what form* the
answer takes; producing surface verdicts from those signals belongs to
a later phase.

## Trust boundary

`question_target.py` reads only frozen, validated `MathProblemGraph`
input. No filesystem access, no dynamic import, no user-controlled
formatting. All refusals are typed.

## Tests

- `tests/test_binding_graph_question_target.py` — unit-lane (~45 tests):
  every operation-kind family, precedence rule, refusal paths, typed
  `Operation` state-index guards.
- `tests/test_binding_graph_adapter_question_target.py` — integration
  (~25 tests): adapter round-trip, hash stability, refusal propagation,
  cross-collection bounds guard.
- Phase 1+2+3 fixtures updated where they constructed `BoundUnknown`
  directly (~5 sites).

## References

- ADR-0132 — data model.
- ADR-0133 — adapter.
- ADR-0134 — unit-aware admissibility.
- `generate/math_problem_graph.py` — input shape (ADR-0115).
