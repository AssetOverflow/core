<!-- CANONICAL | docs/analysis/field-reasoner-wedge-design-and-falsification-2026-06-04.md | 2026-06-04 | research/design+falsification | the source-grounded design of the field↔symbol coherence-gate wedge, corrected by adversarial review into a falsifiable experiment with a sanctioned negative outcome | verified: all load-bearing claims confirmed against source (file:line cited); produced by an 11-agent adversarial research workflow + first-hand substrate read -->

# The field-reasoner wedge — design, adversarial correction, and the falsification it must pass

This is the load-bearing research record that turns the deferred keystone of the
universal-structure plan
([`universal-structure-and-field-symbol-coherence-gate-2026-06-04.md`](./universal-structure-and-field-symbol-coherence-gate-2026-06-04.md))
into a concrete, *falsifiable* experiment. It is planning-and-research only: it
assigns no ADR number, changes no serving path, and introduces no capability claim.

**Provenance.** Compiled from (a) a first-hand read of the CL(4,1)/field/binding-graph/
reliability-gate substrate, and (b) an 11-agent adversarial research workflow (4 substrate
mappers + 2 external-literature researchers → 1 design synthesis → 3 adversarial verifiers →
1 integrator). Every load-bearing claim below is confirmed against source with a `file:line`
citation. The recommended design returned **"revise" on all three adversarial lenses**
(decoration/independence, sub-enumeration, wrong=0); their required fixes are folded in.

**The one-sentence finding.** The CL(4,1) field has exactly **one** exact native strength
relevant to reasoning — the conformal distance metric — and **none** of the incidence,
solver, or independent-reading machinery a metric reasoner needs; so the inevitable next
move is not "make the field the reasoner," it is **the cheapest honest test of whether a
metric *encoding* buys any genuine reading-independence at all**, wired so a negative result
cleanly lands the field back as a servant without polluting `wrong = 0`.

---

## 1. The inevitable next level

The architecture has exhausted the cheap moves and pinned the next one. Four constraints
intersect to a single design shape:

1. The only verified reasoning capability today is **propositional entailment** (ROBDD,
   `generate/proof_chain/entail.py`, holdout 500/500 `wrong=0` vs an independent
   truth-table oracle). A clean geometric decoder of *logic* was already shown to be
   `O(2^n)` truth-table enumeration in algebraic clothing — **the field cannot earn its
   reasoning role on combinatorial logic**. Redirect to a **metric-continuous** domain
   (distance, proportion) where CGA has real purchase.
2. **Independence must live in the *reading*, not the *solving*.** Two solvers over the
   same extracted structure is fake independence; the `wrong=0` risk lives in
   comprehension. For quantitative/NL problems the *reading* (text → structure) is the
   unsound step — unlike logic, whose input is already a formula (independence there is
   cheap: two parsers).
3. **`wrong = 0` is structural, not aspirational.** Whatever the field produces is admitted
   only through a *checkable* gate.
4. The dormant reliability-gate lever `checker="t2_precision"` (`core/reliability_gate/gate.py:22,48-53`)
   can fire only when **two structurally-distinct derivations converge on one
   `commitment_key`** — and no genuinely-independent second derivation exists.

Their intersection collapses the design space to one shape: **an independent metric
*reading* of quantitative-relational problem text, packaged as the field-side
`OperatorEvidence` for the existing `verify_tier2_agreement` seam, scored against a third,
code-disjoint gold registered as a new `INDEPENDENT_GOLD_LANE`.** And the inevitable *first
step* is the cheapest falsifiable version of it — because every heavier design **and the
null** branch off its result.

---

## 2. What the substrate actually supports today (source-verified ledger)

| Capability | Status | Evidence |
|---|---|---|
| Exact conformal distance metric `cga_inner(embed_point(a), embed_point(b)) = −½‖a−b‖²` | **REAL, exact** | `algebra/cga.py:30-37, 65-84`; docstring `:11-17` ("the ONLY distance metric") |
| Null-preserving conformal transforms (versors act correctly on encoded points) | **REAL** (dual-path: null input → raw sandwich) | `algebra/versor.py:160-186, 149-157` |
| Parameterized conformal motions (rotor slerp / transition rotor) | **REAL** but wired to word→word transitions, not point transforms | `algebra/rotor.py:75-144, 147-179` |
| `embed_point` precision | **f32-HARDCODED** — unusable at GSM8K scale; needs an f64 reimplementation | `algebra/cga.py:72,76,82,83`; v=12345 → 12344.99996 in f32 |
| Incidence/flat/round constructors (line/plane/sphere via wedge) | **ABSENT** | `algebra/cga.py` exports only `cga_inner / outer_product / is_null / null_project / embed_point` |
| `meet / join / dual / cross_ratio / betweenness` | **ABSENT** (zero construction hits across `algebra/field/generate/core`) | substrate audit |
| A constraint-propagation **solver** | **ABSENT** — `field/propagate.py` is a fixed-rotor walk ("no correction, no branching"); `field/operators.py::ConstraintCorrectionOperator` is **damped diffusion to a fixed prompt centroid**, NOT algebraic constraint satisfaction (the name is a trap) | `field/propagate.py:1-20,47`; `field/operators.py:153-281` |
| `versor_condition` | **unit-versor closure residual**, NOT a constraint-satisfaction measure | `algebra/versor.py:189-204` |
| Any runtime path embedding problem quantities as conformal points | **ABSENT** — `embed_point` used only in `evals/lab/` probes | substrate audit |
| Reasoning readers import field/algebra | **NONE** (`generate/derivation`, `generate/proof_chain`, `core/reliability_gate` import zero `versor_apply/cga_inner/holonomy/field.propagate`) | grep, confirmed |
| Binding-graph interlingua (`SemanticSymbolicBindingGraph`) | **EXISTS, frozen, INERT** — 6 sub-collections, refusal-first, acyclic, unit-aware, `SourceSpanLink` provenance, INV-26 neutral; derived FROM `MathProblemGraph` by `adapter.py` (so it carries no *independent* reading) | `generate/binding_graph/model.py:397-507`; `adapter.py` |
| Agreement-gate seam | **EXISTS** — `verify_tier2_agreement` admits iff ≥2 distinct `structural_signature`s collapse to one `commitment_key` | `core/reasoning/evidence.py:169-205` |
| Independence firewall on the gate's two readers | **DOES NOT EXIST** — the seam checks only `len(set(signatures)) < 2`, a free-form **label-string** test; INV-25 governs only the *oracle*, and its import check is **single-level / non-transitive** | `core/reasoning/evidence.py:180-187`; `tests/test_architectural_invariants.py:1115-1136` |
| `t2_precision` lever | **WIRED, dead** — nothing populates `t2_verified`; no serving call site passes `checker="t2_precision"`; no serving consumer of proposals | `core/reliability_gate/gate.py:22,48-53`; `propose.py:66-103`; `core/learning_arena/engine.py:80-99` |
| Independent-gold template | **EXISTS, proven** — `deductive_logic` + `dimensional` lanes (oracle shares no SUT code; gold frozen at generation; runner counts correct/wrong/refused) | `evals/deductive_logic/{oracle,generate,runner}.py`; `evals/dimensional/{oracle,runner}.py`; `INDEPENDENT_GOLD_LANES` at `tests/test_architectural_invariants.py:1088-1106` |

**Ledger in one line:** one real native strength (the conformal distance metric); everything
else load-bearing must be built, and the precision substrate must move to f64.

---

## 3. The recommended wedge — corrected form

**Design C1 — the number-line incidence reader, sealed to forward-substitutable relations,
packaged as the field-side evidence for the existing t2 seam.** It is the smallest design
that exercises the one real substrate strength. The adversarial review did not kill it; it
corrected three things that, left unfixed, would have made it decoration or breached
`wrong=0`.

### 3.1 The independent reading — and the honest size of the claim

A **new allowlisted bridge** `generate/binding_graph/field_adapter.py` maps **raw problem
text** to conformal points. Its number detection, clause segmentation, unit assignment, and
relational-cue classification are an **independent reimplementation keyed off relational
phrase schemas** ("more than", "times as many", "in total", "ratio of"), importing **none**
of `generate.derivation`, `generate.math_candidate_parser`, `generate.math_roundtrip`,
`WORD_NUMBERS`, or `state/bind`.

**Honest downgrade (required by all three lenses):** this is a *second hand-written reader*,
**not a categorically different comprehension mechanism.** There is no existing
quantity-preserving text→geometry map. By Knight–Leveson, two architecturally-disjoint
readers of the same text are exactly the regime where **correlated comprehension failure
persists** (~half of N-version faults correlate through the shared specification).
Therefore:

- The ADR/code states independence is **a hypothesis the experiment is designed to refute**,
  never a property held by construction. **Do not cite McGilchrist as evidence** — design
  metaphor only; the only falsifiable form is the checkable gate.
- The independence firewall is made real and **transitive**: a new architectural invariant
  follows the import graph transitively and applies to **both** readers feeding the t2 gate
  (today's `_module_imports` is single-level and would miss a helper that re-pulls
  `math_roundtrip`). The existing `len(set(signatures)) < 2` check is a label test and
  proves nothing.

The geometric encoding does add **one genuine marginal check the symbolic regex lacks**: for
an *over-determined* collinear configuration the read points must form a consistent set with
non-contradictory distances, so a relation the regex silently accepts can produce an
*incoherent* configuration the field refuses. That signal is **real but narrow** — vacuous
on a single unary relation, and it does **not** catch a *coherent* misreading. The margin is
measured, not asserted.

### 3.2 The sub-enumeration argument (sealed)

For the **forward-additive / part-whole** core the encoding is genuinely sub-enumeration and
not the logic wedge's `O(2^n)` trap:

- "A is k more than B" → translation versor `T_k`, `A = versor_apply(T_k, B)`.
- part-whole → collinear metric sum.
- a chain of unary relations (`A = B+3; C = 2A; …`) is **one-shot closed-form forward
  composition** of versors — `O(1)` per constraint, no Boolean assignment lattice. Values
  live in a continuous metric space; that is the categorical difference from logic.

Required fixes that keep this true:

1. **Seal the micro-domain to forward-substitutable (triangular) relations.** The property
   holds only where each relation pins one new unknown from already-resolved points. A
   **coupled/over-determined** system is meet-of-hyperplanes = Gaussian elimination =
   `O(n³)` and needs `meet/join/dual` primitives that **do not exist**. The generator and
   gold exclude coupled systems.
2. **Drop the "propagate to `versor_condition<1e-6`" framing.** A forward chain has no
   iterative solve and no residual; `versor_condition` measures the *operator's* closure,
   not constraint satisfaction. Conflating them invites a **forbidden** hot-path normalizer
   (CLAUDE.md forbids drift repair in `field/propagate.py`).
3. **The win is a sub-*enumeration encoding*, never a *solving* speedup.** Never pitch the
   field as faster than Gaussian elimination.

### 3.3 Correct answer read-back (the wrong=0 bug the verdicts caught)

The naive read-back — "answer = signed distance from origin via `cga_inner`" — is
**mathematically wrong** for any weight-changing operator. A dilation (the multiplicative
case) yields a **weighted** null vector: dilating x=2 by k=4 gives e1=2.0, n_o-weight 0.25,
i.e. `0.25·embed_point([8,0,0])`; naive distance-from-origin returns 4.0 for true coordinate
8.0. **Fix:** read by **projective dehomogenization** — `answer = e1_coefficient /
n_o_weight` — verified exact (8.0). This is the read-back for **all** operators, since
composed motors change weight.

Two further metric hazards the *read side* must own (not the geometry):

- **`cga_inner` is sign-/orientation-blind** (`−d²/2` cannot distinguish A=2B from A=−2B, nor
  enforce betweenness order). Orientation is a separate read-side decision the geometry does
  not verify. Either add an explicit signed-coefficient orientation invariant **or refuse
  all sign-ambiguous configurations.**
- **"k times" via dilation-about-origin / cross-ratio needs a non-degenerate 4-point frame**;
  collinear configs are ill-conditioned. The additive/part-whole core is the load-bearing
  claim; the multiplicative case is **fenced** as the conditioning risk.

### 3.4 The wrong=0 admission contract (honest)

The "three loud-failing layers" was inflated; two are decoration:

- **"Geometric coherence"** on one number line is collinearity-by-construction + non-
  contradictory distances — it catches *contradictory* readings, not a *single coherent
  wrong* relation.
- **"Exact integer round-trip"** is decoration as a *comprehension* guard (confirmed:
  `embed_point([103]), [300], [7]` each round-trip residual 0.0). A coherent misreading (300
  vs 103) passes trivially. Per CLAUDE.md's schema-defined-proof-obligation rule, demote it
  to a **float-sanity guard**, not a `wrong=0` layer.

**The real, load-bearing protection is exactly two checks:**

1. **field⟂symbol agreement** on the **exact** `commitment_key` = (integer value +
   `UnitVector` dimension). Float-tolerant equality is **never** the admit criterion — that
   is precisely what sank `resolve_pooled` (right/wrong float readings indistinguishable).
2. **Scoring vs an independent gold** — a third oracle code-disjoint from **both** readers,
   importing no field/algebra so it cannot agree with the field by construction.

Plus **f64 + a pinned magnitude ceiling**: an f64 reimplementation of `X = x + n_o +
½|x|²·n_inf`, refusing any quantity above an *empirically pinned* bound (GSM8K reaches
thousands; ½|x|² ≈ 1e7; f64 recovers integers exactly to ~1e7, but the ceiling is pinned by
measurement, not assumed). Above the ceiling → refuse.

### 3.5 The asymmetric refinement (the right second step, not the first)

The literature's strongest guarantee is **producer/checker asymmetry** (certifying
algorithms / translation validation): an untrusted producer emits a *witness* a simpler,
code-disjoint *checker* validates without redoing the work. Symmetric "two decodings agree"
is weaker (exposed to correlated error). CORE already has an asymmetric checker for the
dimensional sub-check — `generate/binding_graph/units.py`'s `unit_proof` is free and
code-disjoint. **Use the asymmetric check where one exists** (a C2-style certifying-witness
for the dimensional component); reserve symmetric agreement only where no independent checker
is constructible. This is the correct step *after* the wedge proves the field lands a
coherent configuration at all — **not** premature surface area to build first.

### 3.6 If the experiment fails — the sanctioned alternative (C3)

The field stays a servant in its current cognition-turn role, and quantitative-relational
capability is carried by a **second fully-symbolic, code-disjoint reading** (a
relational-schema parser) agreeing with the existing candidate-graph reader at exact-integer
`commitment_key`s. C3 sidesteps every float/precision/orientation hazard and is the cleanest
`wrong=0` story. Its honest weakness: two symbolic readers are the closest analogue to
Knight–Leveson's refuted-independence case. **C3 is the correct landing iff the wedge shows
the field shares the symbolic reader's blind spots** — a *success*, because it answers the
field-as-reasoner question with evidence instead of deferring it.

---

## 4. The falsifiable experiment (cheapest decisive test)

**Build only:** the f64 number-line reader + four constraint versors (additive/part-whole
load-bearing; multiplicative/ratio fenced) + projective-dehomogenization read-back + the
ablation/diversity instrument. **Do not** build the C2 certifying checker yet.

**Dataset:** ~150 seeded two/three-quantity problems ("k more than", "k times", part-whole),
gold from a **third hand-authored arithmetic oracle** sharing no code with either reader,
registered in `INDEPENDENT_GOLD_LANES`. Split into generation and a **held-out** set; measure
on held-out only (anti-overfit firewall — never tune to the 150 templates).

**Three pass/fail measurements, wired as the gate (not diagnostics):**

1. **Field-alone correctness** — does the field's projective-dehomogenized integer answer
   equal the independent gold on committed cases, **`wrong=0`** on held-out?
2. **Ablation** — run the `wrong=0` gate **with the field vote removed** vs **with it**. The
   admitted set **must CHANGE** (the field must refuse ≥1 comprehension error the symbol path
   alone admits). Unchanged ⇒ **the field is decoration → land C3.**
3. **Diversity, reported PER relation class** — double-fault rate / Q-statistic /
   coincident-failure diversity must clear a pinned threshold. **Aggregate is forbidden** (it
   could net out signal while the field is decoration on the cases that matter). Field credit
   only on classes where it demonstrably refuses an error the symbol path admits.

**A negative result is sanctioned and expected-possible.** If (1) breaches `wrong=0` at
scale, or (2) shows an unchanged admitted set, or (3) shows high coincident failure (Q≈1),
the field is a servant here → land C3, and that result *confirms* the thesis that genuine
reading-diversity needs a categorically different mechanism — justifying a later deeper
research bet rather than this cheap wedge. No unfalsifiable "the field knows" claim is ever
permitted.

---

## 5. Phased path

> Each phase: **entry gate · exit gate · independent gold · `wrong=0` guard.** No phase
> begins until the prior phase's exit gate is green. A lookback review runs at each boundary.

### Phase 0 — foundation (build regardless of the wedge result)
- **Build:** (a) f64 `embed_point` reimplementation + magnitude-ceiling refusal; (b) the
  **transitive reader-disjointness invariant** applied to *both* readers feeding the t2 gate;
  (c) replace the `verify_tier2_agreement` label-string distinctness check with a mechanistic
  one (distinct signatures must be provably unable to come from the same decoding pathway);
  (d) the independent-gold lane scaffolding (third arithmetic oracle, `INDEPENDENT_GOLD_LANES`
  registration).
- **Exit:** all four shipped, full-suite green, INV-25/INV-26 still green; no serving path
  touched. These are net hardening even if the field never reasons.

### Phase W — field-alone metric reader + decoration instrument
- **Entry:** Phase 0 green; micro-domain sealed to forward-substitutable relations;
  projective-dehomogenization read-back implemented.
- **Exit:** the three §4 measurements pass on held-out (field-alone `wrong=0`; ablation
  changes the admitted set; per-class diversity above threshold) **OR** they fail → land C3
  and stop.
- **Independent gold:** third hand-authored arithmetic oracle, code-disjoint from both
  readers, imports no field/algebra.
- **`wrong=0` guard:** exact integer + `UnitVector` `commitment_key` (no float tolerance);
  f64 + refuse-above-ceiling; refuse sign-ambiguous configs.

### Phase 3 — activate `t2_precision` (the dormant lever)
- **Entry:** Phase W exit green; field and symbol each emit `OperatorEvidence` with the same
  exact `commitment_key` and **genuinely distinct** signatures (proven by the non-decoration
  test, not by label).
- **Exit:** in sealed practice, `ClassTally.t2_precision` rises past `N_MIN`+ to the chosen θ
  (PROPOSE=0.85 staging before SERVE=0.99); `propose_from_ledger(..., checker="t2_precision")`
  emits a proposal; **and** a concrete serving consumer of `checker="t2_precision"` exists and
  **refuses on disagreement** (close the ratify-vs-consume gap with an eval delta, not an
  artifact append).
- **Independent gold:** the GoldTether earning t2_precision is independent of **both** readers
  (INV-25 generalized to two SUTs). Re-using the symbolic answer as gold collapses the
  firewall.
- **`wrong=0` guard:** practice scoring is gold-gated, so agree-on-wrong scores
  `t2_verified=1, t2_agrees_gold=0` and **lowers** the license. The residual hazard lives
  in the unbuilt serving consumer: pin its contract now — admit iff (agreement AND class
  licensed); disagreement or field-refusal → deterministic refuse; no float tolerance
  anywhere. The Wilson floor at θ=0.99 demands ~657 perfect committed agreements/class — the
  coverage wall is the binding constraint.

### Phase 4 — GSM8K on the structure (held-out / sealed)
- **Entry:** Phase 3 exit green; the field reader generalizes from seeded templates to **real
  GSM8K** forward-substitutable relational cases (validate on `train_sample`/`holdout_dev`,
  never the 150 templates).
- **Exit:** on a **sealed** GSM8K split, the agreement gate admits with **`wrong=0`**;
  ablation still shows the field changing the admitted set on real cases.
- **Independent gold:** GSM8K reference answers; the gate's gold kept independent of both
  readers.
- **`wrong=0` guard:** the serving-frozen lane (`scripts/verify_lane_shas.py`, `CLAIMS.md`) —
  no bridge re-enables a reader without a sealed/independent `wrong=0` run. The standing
  warning is `resolve_pooled` (2 right / 87 wrong): never admit a reader that cannot
  distinguish its right readings from its wrong ones.

### Phase 5 — cross-domain anti-overfit panel
- **Entry:** Phase 4 green; the field reader is a **third** golded domain alongside
  `deductive_logic` and `dimensional`.
- **Exit:** registered in `INDEPENDENT_GOLD_LANES` with a code-disjoint oracle
  (forbidden-prefix entries for **both** readers); INV-25 sub-properties hold; INV-26 green
  (field→graph translation lives in the bridge, never in `model.py/units.py/admissibility.py`).
- **`wrong=0` guard:** full panel `wrong=0` across all three domains; a deliberately-unsound
  engine must disagree with each oracle (non-vacuity).

### And beyond
The deferred keystone remains deferred: a **categorically different comprehension mechanism**
(Gentner-style structure-mapping over a path that does not pass through any lexeme extractor)
that would make field⟂symbol independence *real by construction* rather than measured. The
wedge does **not** deliver that; it tests whether a metric *encoding* buys any independence on
the one real substrate strength. If Phase W lands C3, the "beyond" is a dedicated research
track on the comprehension mechanism — out of the near-term sequence, never licensed to
displace it.

---

## 6. Risks, honest tensions, and STOP conditions

**Tensions (named, not waved):**
- **Independence is architectural-only, not mechanistic.** A second hand-written parser is
  precisely where correlated comprehension failure survives (Knight–Leveson). The claim is a
  hypothesis the experiment refutes, not a property; the current firewall (a label-string
  distinctness test) does not enforce it.
- **Symmetric agreement is weaker than producer/checker asymmetry.** Use the asymmetric
  (certifying-witness) check where one exists (dimensional `unit_proof`); reserve symmetric
  agreement only where no checker is constructible.
- **The metric is sign-/orientation-blind and the substrate has no incidence primitives.**
  "Incidence" is faked via distance arithmetic; orientation is a read-side decision the
  geometry does not verify — thinning the independent signal exactly on multiplicative/ratio
  cases.

**STOP (and land C3 or the servant null):**
1. Ablation shows an **unchanged admitted set** — the field is decoration.
2. Per-class diversity **collapses** (double-fault high / Q≈1) — fake independence.
3. **f64 + ceiling cannot preserve exact distance at GSM8K scale** — restrict to a band so
   narrow it is not the comprehension layer, or stop.
4. **The seal cannot hold** — if real cases force coupled/over-determined systems, the
   sub-enumeration claim degrades to `O(n³)` on primitives that do not exist; do **not**
   fabricate `meet/join/dual`.
5. **A float coherence threshold gets reconciled with the exact admit gate by tolerance** —
   the `resolve_pooled` failure mode; stop immediately, this breaches `wrong=0`.
6. **Any "the field knows" claim, or a McGilchrist-as-evidence citation, appears in code/ADR
   without the checkable gate behind it** — that imports an unfalsifiable claim; revert.

**Bottom line, without overclaim:** the field has one real, exact strength (the conformal
distance metric) and none of the reasoning machinery around it. The wedge is the cheapest
honest test of whether a metric *encoding* buys genuine reading-independence on
quantitative-relational structure. If it does — `wrong=0`, ablation-positive, diverse — it
activates the dormant `t2_precision` lever as the genuine second derivation. If it does not,
**the field stays a servant, a second code-disjoint symbolic reading carries the next level,
and that negative result is the success.**
