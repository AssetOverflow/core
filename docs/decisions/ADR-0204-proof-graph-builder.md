# ADR-0204 — Proof-Graph Builder (proof_chain's first binding-graph consumer)

**Status:** Accepted (proof_chain phase 2.2 — structure only; ADR-0201 §Deferred)
**Date:** 2026-06-02
**Relates to:** ADR-0132 (binding-graph data model — the substrate this consumes),
ADR-0201 / ADR-0201.1 (canonicalizer + out-of-regime detector), ADR-0202
(proposition representation contract), ADR-0203 (acyclicity guard this exercises).
**Deferred to:** ADR-0205 (modus_ponens + disagreement rule), ADR-0206 (atom→carrier
grounding).

---

## Context

The ADR-0132 binding graph is the proof-DAG substrate; until now it had **zero
consumers**. Phase 2.2 makes `proof_chain` its first: a builder that translates a
propositional proof into a `SemanticSymbolicBindingGraph`. **Structure only** — no
inference rule (modus_ponens is 2.3). The builder constructs the DAG and lets the
substrate's guards fire; it asserts nothing about whether a step is *valid*.

## Decision

### One canonical proof input shape

`generate/proof_chain/model.py` defines the single committed proof representation —
the corpus surface shapes desugar onto it, so proof input never becomes a second
dialect (the ADR-0202 discipline, for proofs):

- `ProofNode(node_id, formula, depends_on, rule)` — `node_id` is a Python
  identifier (→ `symbol_id`); `formula` is an ADR-0202 propositional string;
  `depends_on` names derived-from nodes; `rule` is the inference label.
- `Proof(nodes, conclusion_id)`.
- `proof_from_premises(premises, conclusion, rule)` desugars the
  `premises`/`conclusion`/`rule` corpus shape (each premise → a `rule="premise"`
  node; the conclusion → one node depending on all premises).

### The mapping (every node → one symbol + one equation)

| ProofNode | Binding-graph target |
|---|---|
| `node_id` | `SymbolBinding.symbol_id` / `BoundEquation.lhs_symbol_id` |
| `canonicalize(formula).canonical_key` | `BoundEquation.rhs_canonical` |
| `depends_on` | `BoundEquation.dependencies` |
| `rule` | `BoundEquation.operation_kind` (`"premise"` for assumptions) |

Premises are equations with empty `dependencies` and `operation_kind="premise"` —
uniform, and every node thereby carries its proposition's canonical key in
`rhs_canonical` (which 2.3's rule check needs). Construction runs the ADR-0203
acyclicity guard + ADR-0132 referential integrity in `__post_init__`: a cyclic or
dangling proof **refuses there**, through the real builder path.

### Admissibility-dispatch confirmation (the operation_kind question)

The builder writes logic labels (`"premise"`, later `"modus_ponens"`) into
`operation_kind`, a field the math admissibility checker reads (closed arithmetic
vocab). **Confirmed by code + test that the dispatch handles unknown-to-math kinds
gracefully and never misroutes:** `check_admissibility` ends in
`raise AdmissibilityError("unknown_operation", kind)` — there is no default into
`_check_additive`. Empirically, on built proof equations: a `premise` (no deps)
reaches the dispatch → `unknown_operation`; a `modus_ponens` (unitless deps)
refuses at unit-resolution → `unit_unbound`. Neither returns a math `UnitProof`;
neither misroutes. Baked into `test_proof_operation_kinds_refuse_in_admissibility_never_misroute`.

**Named constraint carried to 2.3:** `check_admissibility` runs `_resolve_dep_units`
*before* the kind dispatch, so a proof equation with dependencies refuses with
`unit_unbound` first. The 2.3 `modus_ponens` check must therefore be wired to
**bypass unit resolution** (dispatch-on-kind before `_resolve_dep_units`, or a
separate proof-admissibility entry) — proofs have no units to resolve.

## Open items (named for 2.3, not "we'll see")

1. **Conclusion typing.** 2.2 tracks `ProofGraph.conclusion_symbol_id` (not a
   `BoundUnknown` — ADR-0135's `question_form` vocab does not fit "is this
   proven"). The 2.3 disagreement rule operates on the conclusion's canonical key
   and may need richer conclusion typing; **revisit conclusion typing in ADR-0205.**
2. **`semantic_role` for propositions.** Proposition symbols use
   `semantic_role="unknown"` because the **closed** ADR-0132 role vocab
   (`entity`/`quantity`/`rate`/…) has no `"proposition"` member. This is the
   role-field analog of the `operation_kind` situation. Extending `SEMANTIC_ROLES`
   would be an ADR-0132 closed-vocab change (its exact set is test-pinned); left as
   `"unknown"` for the additive 2.2 builder. **Decide whether to add a
   `"proposition"` role when proofs become load-bearing.**
3. **`unit_proof`.** Set to the `PROOF_NO_UNIT` sentinel — units are non-applicable
   to propositional proof steps. Composes with constraint (2) above for 2.3's
   admissibility wiring.

## Honesty boundary (load-bearing — every phase-2 ADR, 0203–0205)

Through phase 2.3, proof_chain is **sound over its declared atoms**, not grounded in
recognized input (grounding is 2.4 / ADR-0206). The builder is structure-only: it
builds and refuses cycles/malformed/out-of-regime formulas; it makes **no**
soundness or grounding claim. Out-of-regime node formulas inherit the
canonicalizer's typed `LogicRegimeError` refusal (no silent predicate-logic
admission).

## Evidence

- `tests/test_proof_chain_builder.py` — 9 tests: valid DAG (incl. PC-MP-001
  desugared) + multistep DAG construct; **PC-CYCLE-001 refuses through the real
  builder** (`circular_dependency`); canonical_key round-trips byte-identical +
  equivalent node formulas share `rhs_canonical`; admissibility-dispatch
  confirmation; self/dangling-dependency refusals; out-of-regime node formula
  refuses.
- **Mutation-verified:** neutering the `depends_on → dependencies` wiring makes
  PC-CYCLE-001 construct without refusal → the cycle test fails. The dep-wiring is
  load-bearing, not the guard alone.
- **First-consumer non-perturbation:** full binding-graph + admissibility surface
  green (the 392 intact); builder is purely additive (touches no math path).
- **Real corpus fixture:** PC-CYCLE-001 refuses through the builder; PC-MP-001/002/003
  structures construct (rule-check deferred to 2.3). Smoke: 67 passed.

## Deferred

- **2.3** — `modus_ponens` (`_check_modus_ponens` via ROBDD equivalence, wired to
  bypass unit-resolution per §named constraint) + the disagreement/uniqueness rule
  (the wrong=0 mechanism) — ADR-0205.
- **2.4** — atom→ADR-0144 `EpistemicNode` grounding — ADR-0206.
