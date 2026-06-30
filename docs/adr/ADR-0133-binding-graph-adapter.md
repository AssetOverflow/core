# ADR-0133 — Semantic-Symbolic Binding Graph: Phase 2 adapter from `MathProblemGraph`

**Status:** Accepted (Phase 2 only; Phases 3–5 deferred)
**Date:** 2026-05-23
**Parent:** ADR-0132 (Phase 1 data model, PR #171)
**Related:** ADR-0115 (`MathProblemGraph` origin), ADR-0126 (candidate-graph
parser), ADR-0127 (units pack), ADR-0131 (math-expert rebench / proof corridor),
PR #170 (binding-graph proposal)

---

## Context

ADR-0132 (PR #171) ratified Phase 1 of the binding-graph layer: a pure data
model under `generate/binding_graph/` with frozen dataclasses, deterministic
symbol allocation, refusal-first construction, and no coupling to the symbolic
substrate (`Polynomial`) — symbolic expressions are referenced by canonical
string form only.

The proposal in PR #170 recommends shipping the binding graph in phases. With
the data model locked, the next reviewable seam is a **pure-function adapter**
from the existing ADR-0115 `MathProblemGraph` (the math-word-problem parser's
output) into a `SemanticSymbolicBindingGraph`. Adding the adapter without
runtime wiring keeps the abstraction reviewable in isolation before any
runtime behavior depends on it.

## Decision

Add `generate/binding_graph/adapter.py` exposing
`bind_math_problem_graph(g) -> SemanticSymbolicBindingGraph` and a typed
`AdapterError` (sibling of `BindingGraphError` — both `ValueError` subclasses,
refusal-first by design).

The adapter is **pure**: no I/O, no parser calls, no solver calls, no algebra,
no `numpy`. It performs structural translation only. Mapping discipline is
locked as module-level constants:

| Source (`MathProblemGraph`)            | Output (`SemanticSymbolicBindingGraph`)                                                                                          |
| --------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| each `entity` (str)                     | one `SymbolBinding` with `semantic_role="entity"`, `symbol_id="entity_<slug>"`                                                   |
| each `InitialPossession`                | one `SymbolBinding` (`semantic_role="quantity"`, `symbol_id="q_<entity>_<unit>_t0"`) plus one `BoundFact(value=str(value))`      |
| each `Operation` (index `i`)            | one fresh `SymbolBinding` (`symbol_id="op_{i:03d}_result"`) plus one `BoundEquation` with `operation_kind` **verbatim** from source |
| `Unknown`                               | one synthesized `SymbolBinding` (`semantic_role="unknown"`) plus one `BoundUnknown` referencing it                              |

**Operation-kind passthrough.** The closed vocab
`MathProblemGraph.VALID_OPERATION_KINDS` is shared by design — the adapter
emits `BoundEquation.operation_kind` as a verbatim string passthrough. No
translation, no renaming.

**Dependency wiring.** `BoundEquation.dependencies` references the t0
quantity symbol(s) of the actor (and, where applicable, of
`Operation.target` for `transfer` and of `Comparison.reference_actor` for
`compare_*`), keyed on the unit hint derived from the operand. When no
matching t0 symbol exists (e.g. an actor that started at implicit zero),
the dependency set silently omits it — Phase 2 wires only what the source
graph already pins.

**Synthetic source spans.** `MathProblemGraph` carries no native source-text
spans, so every span the adapter emits is synthesized with
`source_id == "math_problem_graph"`. The brief calls for "skip span fields
cleanly when absent" — Phase 2 implements this by anchoring every
`SourceSpanLink` to a deterministic surface text derived from the binding's
own identity. If a future revision of `MathProblemGraph` carries real spans,
the adapter is the natural site to propagate them.

**Determinism is load-bearing.** Two `MathProblemGraph` instances that compare
equal produce two `SemanticSymbolicBindingGraph` instances that compare equal
and serialize byte-identically via `to_canonical_string()`. This is asserted
by `tests/test_binding_graph_adapter.py` via a hash-stability test that calls
`bind_math_problem_graph` twice and compares both the structure and the
canonical string.

**Refusal-first.** The adapter accepts `object` at the signature boundary and
refuses anything that is not a `MathProblemGraph` with a typed `AdapterError`.
Cross-collection invariants violated downstream (these can only fire if the
adapter itself has a bug) are re-raised as `AdapterError`, so callers see a
single refusal type at the adapter boundary.

## Phase 3+ deferred (explicit)

The following remain out of scope for this ADR and are deferred to follow-up
PRs:

- **Phase 3 — Unit-aware equation admissibility (ADR-0134).** Every
  `BoundEquation` Phase 2 emits carries
  `unit_proof == "deferred_to_phase_3"` and
  `admissibility_status == "pending"`. This is by design — dimensional
  analysis is the substance of Phase 3, not Phase 2, and the placeholder
  makes the gap unambiguous in artifact form. Phase 3's first commit
  should be a test that asserts no equation carries the placeholder
  anywhere except in this adapter's output, then the loop that closes
  the gap.
- **Phase 4 — Question-target binding refinement.** Phase 2 binds the
  `Unknown` to a synthesized `SymbolBinding` (`semantic_role="unknown"`)
  rather than to any prior t0 / result symbol. Phase 4 will resolve the
  unknown against the operation chain when possible.
- **Phase 5 — Bounded-grammar / B3 integration.** No runtime wiring;
  `chat/`, `core/`, `generate/intent.py`, and `generate/realizer.py`
  are untouched.

## Trust boundary

The adapter consumes a frozen, self-validating `MathProblemGraph` — already a
trust-boundary-checked artifact (ADR-0115 refuses malformed input at
construction time). The adapter introduces no new arbitrary-code execution,
no filesystem access, no dynamic imports. The only widening of the trust
boundary is at the signature: `g: object` accepts any caller input and the
adapter is responsible for refusing non-`MathProblemGraph` inputs with a
typed `AdapterError`. Tests pin this refusal.

## Field invariant

Untouched. The adapter never reaches `algebra/`, `field/`, or any runtime
hot-path; `versor_condition` cannot be affected by this change.

## Evidence

- `generate/binding_graph/adapter.py` — adapter (≈300 lines, pure functions,
  module-level mapping constants).
- `generate/binding_graph/__init__.py` — public surface adds
  `bind_math_problem_graph` and `AdapterError`.
- `tests/test_binding_graph_adapter.py` — 41 tests covering: refusal on
  non-graph input, all eight `VALID_OPERATION_KINDS` round-tripping verbatim,
  dependency wiring (transfer, apply_rate, compare_additive), introduction
  order preservation, hash-stability across runs, input immutability,
  frozen-output invariants, Phase-2 placeholder constants
  (`PHASE_2_UNIT_PROOF`, `PHASE_2_ADMISSIBILITY`), and cross-collection
  reference invariants. Full lane `tests/test_binding_graph_model.py +
  tests/test_binding_graph_adapter.py`: **110/0/0**. `pyright` clean on
  new files.
- Runtime byte-identical to main: no runtime integration introduced.

## PR checklist

- **Capability added:** typed, deterministic translation from
  `MathProblemGraph` (ADR-0115) to `SemanticSymbolicBindingGraph` (ADR-0132).
  No runtime wiring yet — Phase 2 is structural translation only.
- **Invariant proven:** `bind(g) == bind(g)` byte-for-byte; two equal
  `MathProblemGraph`s produce two equal binding graphs (hash-stability test).
  All cross-collection references in the emitted binding graph resolve
  against the emitted symbol table.
- **CLI / suite:** `python3 -m pytest tests/test_binding_graph_model.py
  tests/test_binding_graph_adapter.py` — 110 passed.
- **Avoided:** hidden normalization, stochastic fallback, approximate
  recall, dimensional-analysis-by-stealth, `Polynomial` coupling.
- **Trust boundary:** widened only at the adapter signature (`g: object` →
  refusal-first `AdapterError`); no new dynamic execution, no new
  filesystem access.
