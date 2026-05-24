# L5 brief — Opus#2 — Binding Graph Phase 3 (unit-aware equation admissibility)

**Worktree setup (do this first, non-negotiable):**

```bash
git worktree add ../core-binding-graph-p3 -b feat/binding-graph-phase3-units origin/main
cd ../core-binding-graph-p3
```

**Scope.** Phase 3 of the binding-graph layer. Phase 1 (#171, ADR-0132) shipped the data model with `BoundEquation.unit_proof` as a placeholder. Phase 2 (#174, ADR-0133) shipped the `MathProblemGraph` adapter and explicitly left `unit_proof = None` as a Phase-3 gap. Close it: add **deterministic, refusal-first unit-aware admissibility checking** that populates `unit_proof` and stamps `admissibility_status` on every `BoundEquation` produced by the adapter (or constructed directly).

Still no runtime wiring outside `generate/binding_graph/` and no solver invocation — Phase 3 is structural and dimensional analysis only. Phase 4 (question-target binding refinement) and Phase 5 (B3 / bounded-grammar integration) remain deferred.

**Reference docs (read these, only these):**
1. `docs/decisions/ADR-0132-binding-graph-data-model.md` + `docs/decisions/ADR-0133-binding-graph-adapter.md` — your prior phases. The Phase-1 dataclass shape (`BoundEquation.unit_proof: UnitProof | None`, `admissibility_status: Literal[...]`) is the contract you're filling in.
2. `packs/en_units_v1/` (loaded into the runtime via ADR-0127) — the **canonical unit vocabulary**. Your unit algebra must be expressed in those units only; do not invent new ones. Read the pack's lexicon + relation files to identify the closed set of units and their dimensional families (length, time, mass, currency, count, rate-of-X-per-Y, etc.).

**What to ship:**
- `generate/binding_graph/units.py` — pure unit algebra. Functions:
  - `parse_unit(canonical_id: str) -> UnitVector` — convert a closed-vocab unit id into a frozen `UnitVector` (dimension exponents over the base dimensions in the units pack).
  - `unit_product(a: UnitVector, b: UnitVector) -> UnitVector`, `unit_quotient`, `unit_inverse` — algebra primitives.
  - `units_equal(a, b)` — strict equality on the dimension-exponent vector.
  - All pure, frozen, deterministic. No I/O at call time.
- `generate/binding_graph/admissibility.py` — `check_admissibility(equation: BoundEquation, *, symbols: Mapping[str, SymbolBinding]) -> AdmissibilityResult`. Returns a `UnitProof` on success; a typed `AdmissibilityError` reason on refusal. **Dispatch is on `operation_kind`** — the closed eight-string vocab is your full case table:
  - `add` / `subtract` / `compare_additive`: lhs unit ≡ rhs unit ≡ each operand unit; refuse if any disagree.
  - `multiply` / `divide`: lhs unit = product / quotient of operand units; no equality requirement among operands.
  - `transfer`: actor and target must share the same unit; lhs unit = that unit.
  - `apply_rate`: lhs unit = rate-unit × duration-unit (or equivalent); the rate must have form `X/Y` where Y is the operand's unit.
  - `compare_multiplicative`: lhs is dimensionless (ratio); operand units must be equal so they cancel.
  - Any operand whose unit is `None` (unbound) → refuse with `unit_unbound`.
  - Any equation whose `symbols` lookup is missing → refuse with `unknown_symbol`.
- `generate/binding_graph/adapter.py` (modify, surgically): wire `check_admissibility` into the adapter so every `BoundEquation` it produces carries either `admissibility_status="admissible"` + populated `unit_proof`, or `admissibility_status="refused"` + populated `refusal_reason`. **Do not change the adapter's input/output types or signature.** Existing 41 Phase-2 tests must still pass.
- Public surface: add `check_admissibility`, `UnitVector`, `UnitProof`, `AdmissibilityError`, `parse_unit` (and minimal algebra primitives) to `generate/binding_graph/__init__.py`.
- `tests/test_binding_graph_units.py` — 30–40 tests covering the algebra primitives (commutativity, inverse-of-inverse, refusal on unknown unit-id).
- `tests/test_binding_graph_admissibility.py` — 50–70 tests covering each operation kind's admissibility rules with both positive and negative cases, plus the typed-refusal contract.
- `tests/test_binding_graph_adapter_units.py` — 20–30 integration tests covering the adapter's Phase-3 behavior: every Phase-2 case still round-trips, but now `unit_proof` is populated (or refusal is typed); a few intentionally unit-mismatched `MathProblemGraph` inputs produce `admissibility_status="refused"` with the correct reason.
- `docs/decisions/ADR-0134-binding-graph-admissibility.md` — short ADR; cite ADR-0132 + ADR-0133 parents and ADR-0127 (units pack). Explicit "Phase 4–5 deferred" section.

**Hard constraints:**
- **Closed unit vocabulary.** Every unit id used in algebra must already exist in `en_units_v1`. If you find yourself wanting to invent or coerce, stop and refuse with `unknown_unit`.
- **Refusal-first.** Unit mismatches never silently coerce. The `BoundEquation` exits the adapter with `admissibility_status="refused"` and a typed `refusal_reason`. Never raise from the adapter on a unit mismatch — the data-model has a slot for it; use the slot.
- **Determinism.** `unit_product(a, b) == unit_product(b, a)` byte-equal; `bind_math_problem_graph(g)` byte-equal across runs (Phase-2 invariant must not regress).
- **Pure, no I/O.** Unit-pack data must be loaded at module import (or lazily memoized) and frozen; no per-call filesystem reads.
- **No solver coupling.** You're not solving equations. You're verifying the equation, if solved, would be dimensionally consistent.
- **Field invariant untouched.** Stay out of `algebra/`, `chat/`, `core/`, `generate/intent.py`, `generate/realizer.py`, runtime hot path.

**Out of scope (do not touch — Phase 4+):**
- Question-target binding refinement (Phase 4).
- Bounded-grammar / B3 integration (Phase 5).
- `MathProblemGraph` itself (input type — read-only here).
- Symbolic equivalence engine (#167, #169 — separate lane).

**Target branch.** PR against `main`. Title: `feat(binding-graph): Phase 3 unit-aware admissibility (ADR-0134)`. Body must reference ADR-0132, ADR-0133, ADR-0127 (units pack); list Phase 4–5 deferred; report test count (expect ~210 total: 110 from Phase 1+2 still passing, +100ish new).

**Exit criterion.** PR opens with CI green, all new + existing binding-graph tests pass, `pyright` clean on new files, ADR-0134 included. Runtime behavior byte-identical to main (no integration yet).

**Do not stack on another agent's branch.** Target main directly.
