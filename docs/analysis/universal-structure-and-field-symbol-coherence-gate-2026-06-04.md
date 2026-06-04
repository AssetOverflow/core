<!-- CANONICAL | docs/analysis/universal-structure-and-field-symbol-coherence-gate-2026-06-04.md | 2026-06-04 | strategy/architecture-plan | the universal comprehension->structure->solve->verify spine, the binding-graph interlingua, and the field<->symbol coherence gate | verified: planning-only, no ADR number assigned; Phase 0 (INV-25) shipped -->

# Universal structure + the field↔symbol coherence gate

A plan for the most robust, clean, logical, and masterful path to **breaking
reading and inputs of any modality into a logical structure** — so the engine can
comprehend, articulate, and solve a problem in any field for which it has adequate
packs. GSM8K (math logic) is the first proving ground; the same spine must lift
GSM8K *and* be confirmed by independent problem-solving in other fields.

This document is planning-only. It assigns no ADR number, changes no serving path,
and introduces no capability claim. It records the architecture so later, gated
PRs can build it without re-deriving the rationale.

## 0. End goal

```text
input (any modality)
  -> comprehended into ONE logical structure
  -> reasoned over to produce a solution AND an articulated "understanding"
       (what the problem is, the approach)
  -> verified against INDEPENDENT gold
  -> refuses when grounding is incomplete
```

Success = held-out GSM8K rises **drastically** with `wrong == 0`, **and** the
identical machinery clears an independent gold in ≥2 other fields.

## 1. The honest grounding (what exists today)

**The bottleneck is comprehension→structure, not arithmetic.** The GSM8K composer
is epistemically *unsafe* on real data (`resolve_pooled` = 2 right / 87 wrong on
holdout); bespoke per-shape readers do not compose. Capability is *real* only where
the conclusion is **checkable against independent gold** — deductive propositional
entailment (ROBDD) vs. an independent truth-table oracle: dev 200/200, holdout
500/500, `wrong = 0`.

**There are several disjoint problem-structure representations:**

- `generate/math_problem_graph.py::MathProblemGraph` — the GSM8K candidate-graph solver IR.
- `generate/derivation/model.py::GroundedDerivation` — the (unsafe-as-serving) derivation reader IR.
- `generate/binding_graph/SemanticSymbolicBindingGraph` (ADR-0132/0133/0134/0135) —
  a **field-agnostic, unit-aware, provenance-carrying, acyclic, refusal-first**
  semantic-symbolic DAG. It already unifies two domains: math (`bind_math_problem_graph`)
  and proofs (`generate/proof_chain/builder.py`, ADR-0204 — "the binding graph's first consumer").
- `generate/proof_chain` + `generate/logic_canonical.py` (ROBDD) — the deductive decision IR.
- `generate/graph_planner.py::PropositionGraph -> ArticulationTarget` — the *articulation* IR (for saying the answer), separate from reasoning.

**The reasoning readers have zero field/algebra dependency.** `generate/derivation`,
`generate/proof_chain`, `math_solver`, `math_candidate_graph` import no
`versor_apply` / `cga_inner` / `holonomy` / `field.propagate`. The CL(4,1) field
engine participates in the **cognition turn loop** (capture field state, ratify
intent, recall, identity) — **not** in problem reasoning. Any claim of
"field-as-reasoner" is therefore currently *unverified*.

**The dormant lever.** The reliability gate (ADR-0175) already exposes
`checker="t2_precision"` ("widening past gold"), but it is inert: no genuinely
structurally-distinct second derivation exists, and nothing consumes it.

## 2. The synthesis — field comprehends, structure bridges, symbol verifies

The correct architecture is not "field OR symbol." It is a precise division of
labor with a **checkable handshake**:

- **Field/manifold engine = comprehension & constraint-resolution master (right-mode).**
  A problem's entities/relations embed as geometric objects in CGA; solving =
  propagating constraints via `versor_apply` until the configuration is *coherent*
  (`versor_condition < 1e-6`). The converged field **is** the holistic understanding —
  apprehended as a whole, context-first, in CORE's *native* operations.
- **Binding-graph DAG = interlingua / corpus callosum.** The typed, unit-checked,
  provenance-carrying form the field configuration is read **into and out of**: the
  inspectable, checkable commitment where holistic apprehension hands off to analysis
  and analysis hands corrections back. Not master, not mere servant.
- **Symbolic servants (parser, ROBDD, solver, oracle) = analyze & dispose.** They
  verify the structure against independent gold, refute incoherence, articulate.
  They never originate truth.

### 2.1 Why this is correct, not a compromise

**The field-derivation and the symbolic-derivation are two structurally-distinct
canonical decodings of the same problem. Their *agreement* is the `wrong = 0` gate.**

1. **It operationalizes the deepest axiom — "Truth is coherent."** Two independent
   canonical decodings (geometric field + algebraic ROBDD) agreeing is coherence
   across vantage points. Agreement → admit; disagreement → **refuse**. This is
   exactly McGilchrist's "right apprehends, left analyzes, right re-integrates."
2. **It is the genuine second derivation that is currently missing.** The Tier-2
   spine and `t2_precision` lever are inert because solver-vs-verifier shares
   structure (decoration) and the two GSM8K readers never co-fire. **Field ⟂ symbol
   is that second derivation.** Activating the field as a reasoner is *what unblocks
   the dormant capability lever* — mechanism, not metaphor.
3. **It makes the field earn its role checkably (conforms to `wrong = 0` / no
   decoration).** The field is load-bearing *only where its answer agrees with an
   independent symbolic/gold derivation*. It can never serve an unagreed answer —
   disagreement refuses. This is INV-25 (Phase 0) generalized.

### 2.2 Conformance to the governing axes

| Axis | Conformance |
|---|---|
| Philosophical ("decoding, not generating") | Field & symbol are two canonical decodings of a reality that already is; agreement = it tracks the canonical form. |
| Axiomatic | Reasoning *is* `versor_apply` + `cga_inner` + `versor_condition` (the actual primitives); exact recall stays exact. |
| Ethical / `wrong = 0` | The field never serves an unagreed answer; refusal is the correction surface. |
| Mechanical sympathy | Field does vectorized geometric propagation (native strength, Rust-parity-ready); symbol does discrete checks. |
| Logical per "intelligence" | Holistic grasp + analytic check + refuse-on-incoherence is what integrated understanding *is*, with the non-negotiable twist that both modes must cohere or it declines. |

## 3. The earning path (the field must *prove* it reasons)

Today the readers have zero field dependency, so field-as-reasoner is a research arc
that earns its role on the **safest checkable micro-domain first**. A negative
result is an acceptable, honest outcome: where the field cannot earn agreement, it
**stays a servant** and the symbolic path carries that domain, refusing where it
cannot verify. **No unfalsifiable "the field knows" claim ever enters the codebase.**

**The wedge (Phase 1.5) — FINDING (2026-06-04): logic is the wrong first domain.**
The original wedge asked whether the field could decide *propositional entailment*
geometrically and agree with the ROBDD oracle. A bounded experiment settled it: the
cleanest geometric/algebraic encoding (the commuting-idempotent *function-algebra*,
each formula → its function on the `2^n` minterms) **agrees 716/716 with the oracle
but is `O(2^n)`** — it is truth-table enumeration in algebraic clothing, *not* a
genuine sub-enumeration reduction the way the ROBDD is. So a geometric decoder for
logic would either re-encode enumeration (adding no independence the oracle does not
already provide) or be decoration. **Propositional logic is combinatorial
(all-assignments), not geometric/metric** — the field engine's native strength
(distance, incidence, proportion, betweenness) has no purchase there.

**Corrected wedge — quantitative-relational structure.** The field must first earn
its reasoning role where the structure is genuinely *metric*: quantitative-relational
problems (`A is twice B`, `A is 3 more than B`, part-whole, ratios) — exactly where
GSM8K *comprehension* lives. There, the field derivation (solve the linear/metric
relation system by propagation) and the symbolic derivation (step-by-step arithmetic)
are two genuinely distinct decodings, and their agreement on the dataset answer is a
real second derivation. Logic keeps its independent gold (ROBDD ⟂ truth-table oracle)
as a *symbolic* second derivation; the *field* earns its role in the metric domains.
This is the plan working as designed: the field earned nothing it did not deserve,
and we learned the right domain cheaply.

## 4. Phased plan

- **Phase 0 — independent-gold discipline. ✅ SHIPPED.** INV-25
  (`tests/test_architectural_invariants.py`): no capability claim without an
  independent gold sharing no code with the SUT; deductive lane SHA-pinned
  (`deductive_logic_v1`). The foundation every later phase rides on.
- **Phase 1 — canonize the universal structure. ✅ SHIPPED.**
  `SemanticSymbolicBindingGraph` is the documented problem-structure interlingua;
  **INV-26** enforces its neutrality (the interlingua imports no field/eval/runtime,
  and its core imports no domain reader — only allowlisted bridges may). Deferred:
  resolving the closed-vocab placeholder (`semantic_role="unknown"`) until a
  load-bearing consumer defines it; the stronger "servant may not bypass consistency
  checks" rule (the checkable neutrality half shipped; the rest stays doctrine until
  a checkable form exists).
- **Phase 1.5 — the keystone wedge. ✅ RUN (logic ruled out; wedge redirected).**
  The propositional-logic wedge was settled by experiment (§3): a clean geometric
  encoding is enumeration-class, so logic cannot prove field-as-reasoner. The wedge
  is redirected to **quantitative-relational** structure, where the field
  (metric/proportion propagation) and the symbol (step arithmetic) are genuinely
  distinct decodings. The dedicated quantitative wedge is the next field-reasoner
  experiment.
- **Phase 2 — comprehension compiler → binding graph.** **✅ FIRST SLICE SHIPPED:**
  the finite-entity grounding compiler (`evals/deductive_logic/grounding.py`) lowers
  a typed finite-entity problem (entities + unary predicates + single-var universal
  rules) into the propositional regime, refusal-first, gated by `engine == oracle ==
  gold` — the first reader proving a *different problem shape* compiles into the same
  checkable substrate. **The diversity panel starts here** (see cross-cutting):
  finite-entity is the second golded domain, so the compiler is validated against ≥2
  structurally-distinct domains from its first commit and cannot overfit to one
  shape. Remaining Phase 2: target the binding-graph interlingua directly and add
  **field ⟂ symbol agreement** as the admission gate once the quantitative wedge lands.
- **Phase 3 — activate `t2_precision`.** The field⟂symbol agreement *is* the t2
  signal; wire the propose-loop consuming `checker="t2_precision"`. No invented
  second derivation needed — it is real now.
- **Phase 4 — GSM8K on the universal structure** (the drastic-lift phase), gated by
  field⟂symbol agreement + independent gold + held-out/sealed validation (never
  train_sample — the overfit firewall). Safe by construction.
- **Phase 5 — cross-domain confirmation.** Systems/software arena (execution = a
  third independent decoding; ADR-0199's first non-math arena), then a second
  non-executable field with a proof-checker gold. The generalization proof.
- **Phase 6 — multimodal grounding.** Connect the sensorium modality compilers
  (`sensorium/compiler` `CompilerLike`/`CompilationUnitLike`) → binding graph. A
  modality becomes "just another reader" grounding into the universal structure;
  stays afferent/gated per ADR-0198.

### Cross-cutting (every phase) — diversity panel, checkable budgets, adjoints, phenomenology

- **Structurally-diverse checkable panel (the anti-overfit instrument) — woven in
  from Phase 2, not deferred to Phase 5.** Multi-domain diversity is not a morale
  tool bolted onto the plan; it *is* the experiment that confirms or refutes the
  central thesis (that *different* subjects compile into the *same* universal
  structure and are handled by the *same* solve/verify machinery). The defining
  failure of this project was a single gameable ruler (the 50-case train_sample)
  hiding unsoundness for weeks; the antidote is a panel of **structurally distinct**
  domains, each with a **genuine independent gold** (the INV-25 bar — a verifier
  sharing no code with the engine). Adding a domain *without* real independent gold
  is worse than useless: it is another gameable ruler. The cheap, strong starting
  panel (logic / grounding / dimensional / execution / constraint, all with real
  gold):
  - **deductive logic** (ROBDD vs. truth-table oracle) — shipped.
  - **finite-entity grounding** (ROBDD/oracle gold; Phase 2).
  - **units / dimensional analysis** — *nearly free*: the binding graph already
    carries dimensional algebra, so "does the answer's dimension check out" is an
    independent structural gold.
  - **systems/software** (execution = gold; Phase 5) — the strongest verifier.
  - **a small constraint/scheduling domain** (brute-force/SMT gold).

  **The discipline (adopt now):** *a capability change must move ≥2 structurally-
  distinct domains, or it is suspected overfitting until proven otherwise.* Make the
  panel a first-class CI signal alongside GSM8K so progress is never read from one
  flat number. Honesty note: a domain with no adequate pack yet simply refuses
  everything — that is a *coverage* signal (a breadth map), not a *capability*
  signal. Capability credit counts only where there is a real pack **and** a real
  gold **and** committed (non-refused) agreement.

- **Distortion budgets as first-class CI gates**, but *only checkable ones*:
  grounding completeness %, unit-proof coverage, acyclicity, and **structural
  perturbation stability** (paraphrase/reorder the input → the binding graph and
  answer are invariant, or it refuses). Regressions gate the build as hard as
  accuracy. This is the antidote to metric-capture (the train_sample trap).
- **Adjoint-per-operator.** Every new transform ships with its verifier/correction
  pass + a test that it reduces a *structural* error, not just a string.
- **Phenomenology harness.** Sample full structured articulations (the
  "understanding": problem restatement + approach) for periodic trusted review;
  qualitative depth as an explicit but *subordinate* signal (never a new truth
  criterion — that would re-open left-mode capture under a different name).

## 5. Risks & honest tensions

- **HIGH — Phase 4 `wrong = 0`.** GSM8K serving breached it before. Mitigation:
  agreement gate + independent gold + held-out/sealed + pre-push verification
  (auto-merge pipeline).
- **MEDIUM — field-reasoning may not pan out** in a given domain. Expected and
  acceptable: it stays a servant there; the symbolic path carries it, refusing where
  unverifiable.
- **MEDIUM — McGilchrist over-reach.** "Field as master of reasoning" is realized
  only through the *checkable* agreement gate; never asserted as unfalsifiable fact.
- **MEDIUM — IR convergence cost.** Converge the disjoint reasoning IRs incrementally
  (adapters first, direct targeting later), never a big-bang rewrite.

## 6. What this supersedes

The earlier 554/555/556 sequence is reframed: 554 (Tier-2 verifier) was inert →
Phase 3 done *right* (field⟂symbol is the genuine second derivation); 555
(target-slot composition) was unsafe via the composer → Phase 4 (comprehension on
the universal structure, gated); 556 (systems/software arena) → Phase 5.
