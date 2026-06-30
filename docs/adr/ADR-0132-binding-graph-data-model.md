# ADR-0132 — Semantic-Symbolic Binding Graph: Phase 1 data model

**Status:** Accepted (Phase 1 only; Phases 2–5 deferred)
**Date:** 2026-05-23
**Parent proposal:** `docs/implementation/semantic-symbolic-binding-graph-proposal.md` (PR #170)
**Related:** ADR-0115..0118 (math parser/solver/verifier/realizer), ADR-0126
(candidate-graph parser), ADR-0127 (units pack), ADR-0131 (math-expert
rebench / proof corridor)

---

## Context

PR #170 proposed a `SemanticSymbolicBindingGraph` as the typed compiler
boundary between natural-language semantic parsing and symbolic /
equational solving. The proposal explicitly recommends shipping it in
phases, starting with a *data-model-only* first PR — no parser, solver,
adapter, or wiring — so the abstraction has a reviewable seam before any
runtime behavior depends on it.

This ADR ratifies that Phase 1 (`SSBG-1`) scope and pins the resulting
data model.

## Decision

Add a pure data layer under `generate/binding_graph/`:

- `model.py` — frozen, slots-bearing dataclasses:
  - `SourceSpanLink` — `(source_id, start, end, text)` with strict
    half-open-interval validation.
  - `SymbolBinding` — stable `symbol_id` (Python identifier), human-
    readable `name`, closed-vocabulary `semantic_role`, optional
    `entity` / `unit`, mandatory `source_span` + `introduced_by`.
  - `BoundFact` — `symbol_id = value [unit]` lifted from language.
  - `BoundEquation` — `lhs_symbol_id := rhs_canonical` with
    `dependencies: frozenset[str]`, `operation_kind`, `unit_proof`,
    closed-vocabulary `admissibility_status`, and a typed
    `refusal_reason` invariant (required iff `status == "refused"`).
  - `BoundUnknown` — question target bound to a known symbol.
  - `BoundConstraint` — canonical-string predicate over one symbol.
  - `SemanticSymbolicBindingGraph` — top-level container; enforces
    cross-collection referential integrity at construction.
- `allocation.py` — `allocate_symbols(noun_phrases, *, source_span,
  introduced_by, semantic_role, prefix)`. Pure, deterministic, refusal-
  first. Identical input → identical `tuple[SymbolBinding, ...]`,
  byte-for-byte.
- `__init__.py` — public API surface.

### Closed vocabularies

- `SEMANTIC_ROLES = {entity, quantity, rate, duration, count, total,
  difference, ratio, unknown}`
- `ADMISSIBILITY_STATUSES = {admitted, pending, refused}`

Extending either is a deliberate ADR change.

### Discipline (load-bearing)

1. **Pure data layer.** No I/O, no parser calls, no algebra calls, no
   `numpy`, no runtime field touch. The package is importable with zero
   side effects.
2. **Immutability.** Every dataclass is `@dataclass(frozen=True,
   slots=True)`. Every collection field is `tuple` or `frozenset`.
   `SourceSpanLink`/`SymbolBinding`/etc. are equality- and hash-stable.
3. **Refusal-first.** Invalid construction raises typed
   `BindingGraphError` (sibling of `SymbolicError`). Empty strings,
   non-identifier ids, unknown roles, empty/inverted spans, and
   missing/spurious `refusal_reason` all refuse.
4. **No coupling to the symbolic substrate.** `rhs_canonical` and
   `predicate` are *strings*. The binding graph does not import
   `Polynomial` from `generate.math_symbolic_normalizer` — decoupling is
   the entire point of the layer. The string contract aligns with
   ADR-0131's byte-equality discriminator.
5. **Deterministic allocation.** Symbol ids follow
   `{prefix}_{slug}_{index:03d}`; collisions are disambiguated by the
   numeric suffix, so same input → byte-equal output across runs.

### Cross-collection invariants

`SemanticSymbolicBindingGraph.__post_init__` enforces:

- `symbols` carries unique `symbol_id` values;
- every `BoundFact.symbol_id` references a known symbol;
- every `BoundEquation.lhs_symbol_id` and every dependency references a
  known symbol;
- every `BoundUnknown.symbol_id` references a known symbol;
- every `BoundConstraint.symbol_id` references a known symbol;
- every sub-collection is a `tuple` (lists are rejected at
  construction).

### Acceptance evidence

- 69 tests in `tests/test_binding_graph_model.py`, covering frozen
  invariants, slots enforcement, refusal paths, allocation determinism,
  canonical-string round-trip, and cross-collection integrity.
- `pyright` clean on new files.
- Runtime behavior byte-identical to `main`: nothing imports the new
  package yet.

## Consequences

- A reviewable seam for the binding graph exists without committing to
  any specific NL parser, unit algebra, or solver behavior.
- Subsequent phases (see below) can land independently behind the same
  typed boundary.
- The byte-equality discriminator from ADR-0131 is reinforced: the
  binding graph speaks the symbolic substrate by canonical string, so
  graph hashes are stable iff substrate canonicalization is stable.

## Phase 2+ deferred (explicitly out of scope here)

- **Phase SSBG-2** — adapter from existing `MathProblemGraph` into the
  binding graph; goal is representational parity with current bounded
  math behavior, no behavior change.
- **Phase SSBG-3** — unit-aware equation binding using the ratified
  units pack (ADR-0127); admit/refuse based on dimension algebra.
- **Phase SSBG-4** — question-target binding; refuse on ambiguous or
  unbound questions.
- **Phase SSBG-5** — integration with the bounded grammar lane
  (ADR-0131 Benchmark 3); each case carries expected binding-graph
  shape.

These phases land in separate PRs against `main`, each with its own
ADR, lane evidence, and refusal coverage. They will not be stacked on
this PR's branch.

## Non-goals (carried forward from PR #170)

This is not a general NL understanding system, not a chain-of-thought
generator, not a substitute for symbolic equivalence (ADR-0131.1.B),
not a reopening of arbitrary GSM8K parser expansion, and not a
promotion gate by itself.
