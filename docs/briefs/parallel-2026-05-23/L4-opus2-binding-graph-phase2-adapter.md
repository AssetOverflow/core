# L4 brief — Opus#2 — Binding Graph Phase 2 (adapter from `MathProblemGraph`)

**Worktree setup (do this first, non-negotiable):**

```bash
git worktree add ../core-binding-graph-p2 -b feat/binding-graph-phase2-adapter origin/main
cd ../core-binding-graph-p2
```

**Scope.** Phase 2 of the binding-graph layer (ADR-0132 ratified Phase 1; #171 merged). Add a **pure-function adapter** that converts an existing `generate.math_problem_graph.MathProblemGraph` into a `SemanticSymbolicBindingGraph`. Still no runtime wiring — Phase 2 is structural translation only. Phases 3 (unit-aware equation binding), 4 (question-target binding), and 5 (bounded-grammar integration / B3) remain deferred to follow-up PRs.

**Reference docs (read these, only these):**
1. `docs/decisions/ADR-0132-binding-graph-data-model.md` — your Phase 1 ADR; the data model is the codomain of the adapter.
2. `generate/math_problem_graph.py` — the input type. Note its determinism guarantees (frozen+slots, order-of-introduction tuples, `canonical_bytes`). The adapter must preserve those.

**What to ship:**
- `generate/binding_graph/adapter.py` — `bind_math_problem_graph(g: MathProblemGraph) -> SemanticSymbolicBindingGraph`. Pure function. Deterministic: byte-equal input graph → byte-equal output binding graph (assert via `canonical_bytes`-style round-trip in tests).
- Mapping discipline (lock these as constants at the top of `adapter.py`):
  - Each entity → one `SymbolBinding` with `semantic_role="entity"`, `symbol_id = entity_<slug>`.
  - Each `InitialPossession` → one `SymbolBinding` with `semantic_role="quantity"` and a `BoundFact` (`q_<entity>_<unit>_t0 = value [unit]`).
  - Each `Operation` → at minimum one `BoundEquation` capturing the operand semantics, with `dependencies` referencing the source-state symbols. `operation_kind` mirrors the `MathProblemGraph` op kind verbatim (string passthrough — the closed vocab is shared by design).
  - `Unknown` → one `BoundUnknown` referencing the bound symbol whose value the solver must determine.
- Public surface: add `bind_math_problem_graph` to `generate/binding_graph/__init__.py`.
- `tests/test_binding_graph_adapter.py` — 30–40 tests covering: every operation kind round-trips, entity/quantity mapping is deterministic across orderings (introduction-order preserved), unknown-binding is single-target, `source_span` propagation when the `MathProblemGraph` carries span info (skip span fields cleanly when absent), refusal-first on malformed input (`AdapterError` typed exception, sibling of `BindingGraphError`), and a hash-stability test (`bind(g) == bind(g)` byte-equal across runs).
- `docs/decisions/ADR-0133-binding-graph-adapter.md` — short ADR ratifying Phase 2; cite ADR-0132 parent and ADR-0115 (`MathProblemGraph` origin). Explicit "Phase 3+ deferred" section.

**Hard constraints:**
- **Pure function, pure data.** No I/O, no parser calls, no solver calls, no `numpy`. The adapter is a deterministic translation.
- **No mutation.** Output is a new `SemanticSymbolicBindingGraph`; input is not touched (it can't be — frozen — but assert the invariant in tests anyway).
- **Operation-kind passthrough.** Do not invent a new closed vocab. The `MathProblemGraph.VALID_OPERATION_KINDS` set is authoritative; `BoundEquation.operation_kind` accepts the same eight strings. If you find yourself wanting to translate or rename, stop and refuse.
- **Determinism is load-bearing.** The tuples in the output BindingGraph must reflect introduction order from the input. Two `MathProblemGraph` instances that hash-equal must produce two `SemanticSymbolicBindingGraph` instances that hash-equal.
- **Unit-aware *equation binding* is Phase 3, not Phase 2.** In Phase 2 it is acceptable for `BoundEquation` to carry `unit_proof = None` or a placeholder; do not attempt dimensional analysis. (Confirm in the ADR that this gap is by design and the next ADR closes it.)
- **Field invariant untouched.** Don't go near `versor_condition`, `algebra/`, or anything in the runtime hot path.

**Out of scope (do not touch — Phase 3+):**
- Unit-aware equation admissibility checks (Phase 3 / ADR-0134).
- Question-target binding refinement (Phase 4).
- Bounded-grammar / B3 integration (Phase 5).
- Any change to `chat/`, `core/`, `generate/intent.py`, `generate/realizer.py`, `generate/math_problem_graph.py` itself.
- B1.B (PR #169 — separate lane).
- B2 teaching-corpus eval (L1 — Gemini's lane).
- B1 sealed holdout (L3 — undispatched).

**Target branch.** PR against `main`. Title: `feat(binding-graph): Phase 2 adapter from MathProblemGraph (ADR-0133)`. Body must reference #170 (proposal), #171 (Phase 1), and explicitly list Phase 3–5 as deferred.

**Exit criterion.** PR opens with CI green, all new tests pass, `pyright` clean on new files, ADR-0133 included. Runtime behavior byte-identical to main (no integration yet, by design).

**Do not stack on another agent's branch.** Target main directly. If main does not yet contain ADR-0132 + Phase 1, stop and flag — Phase 2 requires that foundation.
