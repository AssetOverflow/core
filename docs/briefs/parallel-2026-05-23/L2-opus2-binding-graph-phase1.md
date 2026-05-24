# L2 brief — Opus#2 — Semantic-Symbolic Binding Graph, Phase 1 (data model only)

**Worktree setup (do this first, non-negotiable):**

```bash
git worktree add ../core-binding-graph-p1 -b feat/binding-graph-phase1 origin/main
cd ../core-binding-graph-p1
```

**Scope.** Ship Phase 1 *only* of the binding graph layer proposed in `docs/implementation/semantic-symbolic-binding-graph-proposal.md` (PR #170, now on main). Phase 1 is **data-model-only**: frozen dataclasses + invariants + tests. **No runtime wiring, no adapter, no equation binding, no parser change.** Phases 2–5 are deferred to follow-up PRs.

**Reference docs (read these, only these):**
1. `docs/implementation/semantic-symbolic-binding-graph-proposal.md` — your spec. The dataclass list under "Adds" is authoritative.
2. `generate/math_symbolic_normalizer.py` (post-#167) — only to see the existing `Polynomial` dataclass style (frozen, terms-dict, variables-tuple). Match its idiom; do **not** import from it.

**What to ship:**
- `generate/binding_graph/__init__.py` — public API surface.
- `generate/binding_graph/model.py` — frozen dataclasses per the proposal:
  - `SemanticSymbolicBindingGraph`
  - `SymbolBinding`
  - `BoundFact`
  - `BoundEquation`
  - `BoundUnknown`
  - `BoundConstraint`
  - `SourceSpanLink`
  Use `@dataclass(frozen=True, slots=True)`. All collections immutable (`tuple`, `frozenset`, `MappingProxyType` if needed). No mutation methods.
- `generate/binding_graph/allocation.py` — deterministic symbol allocator. Given a sorted iterable of NL noun-phrases, returns a stable `tuple[SymbolBinding, ...]`. Pure function. Deterministic across runs.
- `tests/test_binding_graph_model.py` — 30–50 tests covering: frozen invariants, equality, hashability where applicable, allocation determinism, refusal on bad input (empty span, duplicate binding id, etc.), `SourceSpanLink` round-trip.
- `docs/decisions/ADR-0132-binding-graph-data-model.md` — short ADR ratifying Phase 1; cite #170's proposal doc; explicit "Phase 2+ deferred" section.

**Hard constraints:**
- **Pure data layer.** No I/O, no parser calls, no algebra calls, no `numpy`, no runtime field touch.
- **Immutability.** Every field is immutable; every collection is `tuple`/`frozenset`. The "create new objects, never mutate" rule from coding-style.md is load-bearing here.
- **Deterministic allocation.** Same input order → same `SymbolBinding` ids → byte-equal serialization. Lane test asserts this.
- **Refusal-first.** Invalid construction raises a typed error (`BindingGraphError`, sibling of `SymbolicError`); never silently coerces.
- **No coupling to the symbolic normalizer.** The binding graph references symbolic expressions by *string canonical form*, not by importing `Polynomial`. Decoupling is the whole point of the layer.

**Out of scope (do not touch — these are Phase 2+):**
- Adapter from existing `MathProblemGraph` (Phase 2).
- Unit-aware equation binding (Phase 3).
- Question-target binding (Phase 4).
- Bounded grammar integration (Phase 5 / B3).
- Any change to `chat/`, `generate/intent.py`, `generate/realizer.py`.

**Target branch.** PR against `main`. Title: `feat(binding-graph): Phase 1 data model (ADR-0132)`. Body must reference #170 as parent and list Phase 2–5 as deferred follow-ups.

**Exit criterion.** PR opens with CI green, all new tests pass, `pyright` clean on new files, ADR-0132 included. Runtime behavior byte-identical to main (no integration yet, by design).

**Do not stack on another agent's branch.** Target main directly.
