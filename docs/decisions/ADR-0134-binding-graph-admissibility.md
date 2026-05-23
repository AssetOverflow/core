# ADR-0134 — Binding Graph Phase 3: Unit-Aware Equation Admissibility

**Status:** accepted
**Parents:** [ADR-0132](ADR-0132-binding-graph-data-model.md) (data model), [ADR-0133](ADR-0133-binding-graph-adapter.md) (adapter), [ADR-0127](ADR-0127-units-pack-and-units-aware-parser.md) (units pack)
**Date:** 2026-05-23

## Context

Phase 1 (ADR-0132) shipped the binding-graph data model with
`BoundEquation.unit_proof` declared as a non-empty `str` and an
`admissibility_status` drawn from `{admitted, pending, refused}`.
Phase 2 (ADR-0133) shipped the `MathProblemGraph → SemanticSymbolicBindingGraph`
adapter and explicitly emitted every equation with the placeholder
`unit_proof="deferred_to_phase_3"` + `admissibility_status="pending"`.

Phase 3 closes that gap. Every emitted equation must now carry either:

- `admissibility_status="admitted"` + a populated `unit_proof` derived
  from dimensional analysis over the closed `en_units_v1` vocabulary
  (ADR-0127); or
- `admissibility_status="refused"` + a typed `refusal_reason` drawn from
  a closed vocabulary, with `unit_proof` set to a sentinel.

This is the wrong-answer firewall: the binding graph never silently
admits a dimensionally inconsistent equation, and never invents or
coerces a unit outside the pack.

## Decision

Add three deliverables under `generate/binding_graph/`:

1. **`units.py`** — pure unit algebra over an integer exponent vector
   on six base dimensions (`length, time, mass, money, count,
   temperature`). The closed vocabulary is loaded once from
   `language_packs/data/en_units_v1/lexicon.jsonl` at first call and
   memoized. Composite unit ids of the form `"<num>_per_<denom>"`
   resolve recursively as `unit_quotient(parse_unit(num),
   parse_unit(denom))`. `parse_unit` refuses with
   `UnitAlgebraError("unknown_unit: …")` on any other input — including
   after a conservative depluralization pass (`apples → apple` etc.).

2. **`admissibility.py`** — `check_admissibility(equation, *, symbols)`
   dispatches on `BoundEquation.operation_kind` against the closed
   eight-string vocab:

   | kind | rule |
   |---|---|
   | `add` / `subtract` / `compare_additive` / `transfer` | all dep units equal; lhs == that unit |
   | `compare_multiplicative` | dep units cancel; lhs dimensionless |
   | `multiply` | lhs == product of dep units |
   | `divide` | requires one dividend + one `*__divisor` literal; lhs == quotient |
   | `apply_rate` | dep with `semantic_role='rate'` carries `X/Y`; other dep carries `Y`; lhs == `X` |

   Refusal is typed: every `AdmissibilityError` carries a `reason` from
   `ADMISSIBILITY_REASONS = {unit_mismatch, unknown_unit, unit_unbound,
   unknown_symbol, unknown_operation, operand_arity, rate_form_invalid}`.
   Success returns a frozen `UnitProof(operation_kind, lhs_unit,
   operand_units)` whose `to_canonical_string()` is stored in
   `BoundEquation.unit_proof`.

3. **`adapter.py`** (surgical wiring) — for each `Operation` the
   adapter:
   - synthesizes any operand-literal symbols the verifier needs
     (`op<NNN>__multiplicand` for `multiply`,
     `op<NNN>__divisor` for `divide`,
     `op<NNN>__rate` with `semantic_role='rate'` and unit
     `"<num>_per_<denom>"` for `apply_rate`);
   - constructs a shell `BoundEquation` and calls `check_admissibility`;
   - stamps the final equation `admitted` + proof on success, or
     `refused` + typed `refusal_reason` on `AdmissibilityError`.

   No new equations; no change to `bind_math_problem_graph`'s
   input/output types. `compare_multiplicative` deliberately adds no
   synthesized symbols (Phase-2 invariant: dependencies remain
   `frozenset()`).

The public surface in `generate/binding_graph/__init__.py` gains
`check_admissibility`, `UnitProof`, `UnitVector`, `parse_unit`,
`unit_product`, `unit_quotient`, `unit_inverse`, `units_equal`,
`AdmissibilityError`, `UnitAlgebraError`, `ADMISSIBILITY_REASONS`,
`BASE_DIMENSIONS`, `DIMENSIONLESS`, and `REFUSED_UNIT_PROOF`. The
placeholder constants `PHASE_2_UNIT_PROOF` / `PHASE_2_ADMISSIBILITY`
are removed (their role is now served by real proofs + typed refusals).

## Trust Boundaries

- **Closed unit vocabulary.** Every unit id used in admissibility must
  resolve to a lemma in `en_units_v1` (after conservative
  depluralization, or via the `X_per_Y` composite path). Anything else
  is refused with `unknown_unit`. There is no coercion, no invention,
  and no "best-effort" fallback.
- **Refusal-first.** Dimensional mismatches never raise from the
  adapter; they are stamped onto the equation's `refusal_reason` slot.
  The data model already reserves the slot — this ADR uses it.
- **Pure, no I/O at call time.** The pack lexicon is read once at first
  `parse_unit` call and memoized into an immutable mapping. Subsequent
  calls do not touch the filesystem (test `test_unit_algebra_no_io_at_call_time`
  pins this behavior).
- **No solver coupling.** The verifier checks that the equation, *if
  solved*, would be dimensionally consistent. It does not import
  `Polynomial`, does not invoke any solver, and does not depend on the
  symbolic substrate.

## Invariants

- `unit_product(a, b) == unit_product(b, a)` byte-equal (commutativity
  on integer addition).
- `unit_inverse(unit_inverse(v)) == v` (involution).
- `unit_quotient(v, v) == DIMENSIONLESS` (cancellation).
- `bind_math_problem_graph(g)` is byte-equal across runs (Phase-2
  invariant preserved; deterministic dep iteration via sorted symbol
  ids).
- `bg.equations[i].admissibility_status ∈ {admitted, refused}` for every
  equation produced by the adapter — `pending` is no longer reachable
  via `bind_math_problem_graph`.
- Phase-2 cases using units outside `en_units_v1` (e.g. `apples`,
  `widgets`) now produce typed `refused` equations with
  `refusal_reason="unknown_unit"`. The structural shape of the binding
  graph (entity / fact / equation / unknown counts) is preserved.

## Field Invariant

Unchanged. This ADR adds no algebra/, chat/, core/, generate/intent.py,
generate/realizer.py, or runtime-hot-path code; the field invariant
`versor_condition(F) < 1e-6` is not touched.

## Tests

- `tests/test_binding_graph_units.py` (47 tests) — algebra primitives,
  pack-driven `parse_unit`, depluralization, composite resolution,
  refusal coverage, no-I/O-after-warmup.
- `tests/test_binding_graph_admissibility.py` (40 tests) — per-kind
  dispatch (positive + negative), typed-refusal vocab, `UnitProof`
  contract, sorted-dep determinism.
- `tests/test_binding_graph_adapter_units.py` (29 tests) — adapter
  Phase-3 integration: every Phase-2 case still round-trips (now with
  populated `unit_proof` or typed `refusal_reason`); pack-grounded
  happy paths admit with the expected dimensional surface; the eight
  operation kinds all carry Phase-3 admissibility status; canonical
  string is byte-equal across runs.
- `tests/test_binding_graph_adapter.py` (38 tests) — Phase-2 tests
  unchanged in structure; the two placeholder-equality tests have been
  rewritten to assert the Phase-3 contract (`refused` + typed reason on
  out-of-vocab units; `admitted` + populated proof on pack-grounded
  units).
- `tests/test_binding_graph_model.py` (61 tests) — unchanged.

Total binding-graph lane: **215 tests** (110 pre-existing + 116 new;
the brief's expected ~210 is comfortably exceeded). All green;
`pyright` clean on all new files.

## Phase 4–5 Deferred

The following remain explicitly out of scope:

- **Phase 4 — question-target binding refinement.** The `BoundUnknown`
  currently records `expected_unit` verbatim from the source `Unknown`.
  Phase 4 will reconcile this with the admitted lhs unit of the
  question-resolving equation chain.
- **Phase 5 — bounded-grammar / B3 integration.** No runtime wiring of
  the binding graph outside `generate/binding_graph/`. The pipeline,
  realizer, and chat surfaces remain untouched.
- **Symbolic equivalence engine** (issues #167, #169) — separate lane.
- **`MathProblemGraph` itself** — read-only input here; its operand
  vocabulary (Quantity / Rate / Comparison) is unchanged.

## Runtime Impact

None. The binding graph still has no runtime wiring outside
`generate/binding_graph/`. `chat/runtime.py`, the cognition eval lane,
the field invariant, the algebra backend, and every other production
hot path are unaffected. Cognition eval lane byte-equal to main.
