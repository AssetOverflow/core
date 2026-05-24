# L7 brief — Opus#2 — Binding Graph Phase 4 (question-target binding refinement)

**Worktree setup (do this first, non-negotiable):**

```bash
git worktree add ../core-binding-graph-p4 -b feat/binding-graph-phase4-question-target origin/main
cd ../core-binding-graph-p4
```

**Scope.** Phase 4 of the binding-graph layer. Phase 1 (#171, ADR-0132) introduced `BoundUnknown` as the question target. Phase 2 (#174, ADR-0133) mapped `MathProblemGraph.Unknown` to a `BoundUnknown` referencing the entity/unit pair. Phase 3 (#176, ADR-0134) added unit-aware admissibility on equations. **Phase 4 refines `BoundUnknown` from "the symbol whose value the solver determines" to "the symbol at a specific temporal/state index with a specific question-form."**

Concretely: the question "How many apples does Tina have?" doesn't currently bind to a unique symbol — Tina-apples at `t=0`, after operation 3, and at the terminal state are three different symbols. Phase 4 deterministically resolves *which* of those the unknown refers to, and stamps the question form (count / rate / total / difference / ratio / identity) so downstream consumers know what verdict shape to produce.

Still no runtime wiring, still no solver invocation. Phase 5 (bounded-grammar / B3 integration) remains deferred.

**Reference docs (read these, only these):**
1. `docs/decisions/ADR-0132-binding-graph-data-model.md`, `ADR-0133-binding-graph-adapter.md`, `ADR-0134-binding-graph-admissibility.md` — your prior phases. `BoundUnknown` and the adapter's `Unknown → BoundUnknown` mapping are the contract you're refining.
2. `generate/math_problem_graph.py` — input shape; the operation sequence drives the state-index resolution.

**What to ship:**
- `generate/binding_graph/model.py` (modify, surgically): extend `BoundUnknown` with two new mandatory fields:
  - `state_index: StateIndex` — a closed-vocab tagged union: `Literal["initial"]`, `Literal["terminal"]`, or `Operation(operation_index=int)` (a frozen dataclass — not a string — so the operation index is type-checked).
  - `question_form: Literal["count", "rate", "total", "difference", "ratio", "identity"]`.
  Both fields **required** — no `None` defaults. Update `__post_init__` to validate (`operation_index` ≥ 0 and < graph operation count when used inside a `SemanticSymbolicBindingGraph`; cross-collection check belongs to the graph constructor).
  Phase 1–3 tests that construct `BoundUnknown` directly will need the new fields supplied; expect ~5–10 test fixture updates inside the binding_graph test files (Phase 1+2+3 by you). Mark those edits explicitly in the PR diff so the reconciliation is auditable.
- `generate/binding_graph/question_target.py` (new) — pure-function resolver:
  - `resolve_state_index(g: MathProblemGraph) -> StateIndex` — walks the operation sequence, returns `terminal` when operations exist, `initial` when not.
  - `infer_question_form(g: MathProblemGraph) -> Literal[...]` — closed-vocab dispatch on the operation kinds touching the unknown's entity/unit; e.g. all-`add`/`subtract`/`transfer` → `count`; presence of `apply_rate` → `total` or `rate` depending on which symbol the unknown binds; `compare_additive` → `difference`; `compare_multiplicative` → `ratio`; no operations → `identity`.
  - `bound_unknown_from_math_problem_graph(g: MathProblemGraph) -> BoundUnknown` — the new public entry point that the adapter uses; deterministic, refusal-first via a typed `QuestionTargetError` (sibling of `AdapterError`/`AdmissibilityError`).
- `generate/binding_graph/adapter.py` (modify, surgically): replace the existing `Unknown → BoundUnknown` mapping with a call to `bound_unknown_from_math_problem_graph(g)`. Do not change `bind_math_problem_graph`'s signature; do not change the equation/fact/symbol mapping.
- Public surface: add `StateIndex`, `Operation` (state-index variant), `resolve_state_index`, `infer_question_form`, `bound_unknown_from_math_problem_graph`, `QuestionTargetError` to `generate/binding_graph/__init__.py`.
- `tests/test_binding_graph_question_target.py` — 50–70 tests covering: each operation-kind family producing the expected `question_form`; `state_index` resolution at boundary cases (0 operations, 1 operation, many operations, unknown referencing an entity that no operation touches); refusal-first on the typed `QuestionTargetError` paths (unknown entity not in `entities`, ambiguous form when multiple operation kinds touch the same symbol with no clear precedence — pick one closed rule and document it).
- `tests/test_binding_graph_adapter_question_target.py` — 30–40 integration tests covering: every Phase-2 adapter test case still round-trips with the refined `BoundUnknown`; new cases exercising `state_index` and `question_form` end-to-end; hash-stability across runs (Phase 2 invariant must not regress); a few intentionally-ambiguous `MathProblemGraph` inputs produce `QuestionTargetError`.
- `docs/decisions/ADR-0135-binding-graph-question-target.md` — short ADR. Cite ADR-0132, ADR-0133, ADR-0134 parents. Explicit "Phase 5 deferred" section. Document the closed `question_form` vocabulary and the precedence rule when multiple operation kinds touch the same symbol.

**Hard constraints:**
- **Closed `question_form` vocabulary.** Exactly the six values above; do not invent more. If a `MathProblemGraph` shape doesn't fit any, refuse with `QuestionTargetError(reason="unmappable_question_form")`. Never silently coerce to "count" as a default.
- **Closed `state_index` vocabulary.** `initial`, `terminal`, or `Operation(operation_index=N)`. No "midway", no negative indices, no strings outside that set.
- **Refusal-first.** Ambiguity refuses with a typed reason; never picks arbitrarily. The precedence rule (when multiple op-kinds touch the unknown's symbol) must be deterministic and documented in the ADR.
- **Pure, no I/O.** No filesystem reads at call time.
- **Determinism.** `bind_math_problem_graph(g)` byte-equal across runs after the Phase 4 wiring (Phase 2 invariant). The `BoundUnknown`'s new fields are stable functions of the input.
- **No solver coupling.** You're determining *which symbol* the question targets and *what form* the answer takes — not solving anything.
- **No mutation of `MathProblemGraph`.** Input is read-only (frozen anyway, but assert in tests).
- **Field invariant untouched.** Stay out of `algebra/`, `chat/`, `core/`, runtime hot path.

**Compatibility / fixture migration:**
- The two new required fields on `BoundUnknown` will break ~5–10 Phase 1+2+3 test fixtures that construct `BoundUnknown` directly. Update them in the same PR. Do not add default values to keep them backward-compat — required fields are load-bearing.
- The Phase 2 adapter's behavior changes (`Unknown → BoundUnknown` now populates the new fields). The byte-equal hash-stability invariant must continue to hold on a fresh-run basis (hash will differ from Phase 3 main, by design — that's not a regression).

**Out of scope (do not touch — Phase 5):**
- Bounded-grammar / B3 integration.
- Any change to `chat/`, `core/`, `generate/intent.py`, `generate/realizer.py`, `generate/math_problem_graph.py`.
- B1.B and B1.S follow-ups (separate lanes).
- B2 v1.B enrichment (L6, Gemini's lane).
- Promotion-gate wiring (ADR-0131.4).

**Target branch.** PR against `main`. Title: `feat(binding-graph): Phase 4 question-target binding (ADR-0135)`. Body must reference ADR-0132 / -0133 / -0134; list Phase 5 deferred; report test count (expect ~300+ total: 226 from Phase 1+2+3 still passing, +80ish new).

**Exit criterion.** PR opens with CI green, all new + existing binding-graph tests pass, `pyright` clean on new files, ADR-0135 included. Runtime behavior byte-identical to main (no integration yet).

**Do not stack on another agent's branch.** Target main directly. If main does not yet contain ADR-0132 + -0133 + -0134, stop and flag — Phase 4 requires all three.
