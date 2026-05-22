# Capability Roadmap — Phased Plan to the Verifiable Competence Gates

**Status:** Draft, derived from `docs/sessions/SESSION-2026-05-15-capability-gates.md`
**Owner:** Joshua Shay
**Last updated:** 2026-05-22 (Phase 6 added; status update appended below)

## Status update — 2026-05-17

Work landed since the 2026-05-15 draft (each item is a roadmap input, not yet
a roadmap rewrite — that pass is queued):

* **Forward Semantic Control chain** — ADR-0022 through ADR-0026 accepted;
  inner-loop admissibility, rotor/frame admissibility, and ranked-with-margin
  gates implemented and CI-enforced. See README §"Forward Semantic Control".
* **Epistemic schema closure** — three leaks closed, four new lanes, three new
  architectural invariants (INV-21/22/23). Realizer-side refusal calibration
  and contradiction-coherence checker landed.
* **Formation pipeline (back half)** — Phases 1–7 implemented; 138/138
  formation tests pass. See `docs/formation_pipeline_plan.md`.
* **FSC v3 50-case threshold proof matrix** — landed on
  `feat/fsc-proof-suite-demo-rebased`; PR pending.
* **Cost benchmark** — `bench cost` lane reports $/1000 turns + latency with
  disclosed assumptions; current measurement is 48–149× cheaper per turn than
  frontier LLMs.
* **`core pulse` import fix** — 2026-05-17 hex-literal bug in
  `language_packs/en_seeder.py` repaired; pulse path is operational again.

Closed gates (vs the Phase 1 "Foundational Triple"):

* `identity-divergence` — lane runner, axes, 93-event shared curriculum, dev /
  public / holdout splits all present.
* `grammatical-coverage` — partial; v1 work in flight, no formal contract yet.
* `zero-code-domain-acquisition` — not started.

A full rewrite of the phase exit-criteria against current state is queued for
the next planning pass.

## Status update — 2026-05-22

Phase 5 (Curriculum Era) work landed in volume during the 2026-05-17 → 2026-05-22 window. The roadmap gains a new Part-II phase (**Phase 6 — Evidence-Governed Domain Layer**, see below) that did not exist in the 2026-05-15 draft because the substrate it ratifies (multi-domain packs, signed reviewer registry, expert-demo gate) did not yet exist either. The phase is documented here as accepted and partially landed, not proposed.

Major chains accepted since 2026-05-17:

* **Pack-layer chain — ADR-0027 through ADR-0045.** Identity packs (0027/0028), safety packs (0029), ethics packs (0033/0036/0037), reviewed verdicts (0035), audit completeness (0039), telemetry sink (0040), CLI verdicts + fan-out (0041), audit-tour demo (0042), pack measurements (0043), medical-ethics worked example (0044), long-context comparison evidence (0045).
* **Forward graph constraint → pack-grounded surface — ADR-0046 through ADR-0070.** PropositionGraph becomes AdmissibilityRegion before generate (0046/0047); pack-grounded surface composers for DEFINITION/RECALL/COMPARISON/PROCEDURE/CORRECTION/NARRATIVE/EXAMPLE intents (0048–0066); cross-pack resolver and teaching-corpus chain (0063/0064); register terse v1 (0070); seeded variation (0071); register telemetry + tour (0072).
* **Anchor lens substrate — ADR-0073 + sub-ADRs.** Substantive variation axis sibling to register, with the opposite invariant (lens moves trace_hash DISTINCT; register holds it CONSTANT). Both orthogonal-axis demos CI-pinned simultaneously.
* **Transitive chain surface and definitional groundwork — ADR-0078–0089.** Composer/graph atom equivalence telemetry (0078); transitive chain surface (0083); compound-intent dispatch + discourse planner (0089).
* **Contemplation Loop Phase 1 — ADR-0080 (accepted 2026-05-22).** Read-only frontier-compare miner emits `SPECULATIVE` findings only; routes through `teaching/review.py`; no pack mutation. The first system-emitted gap-finding surface.
* **Evidence-governed domain layer — ADR-0091 through ADR-0110.** See Phase 6 below.

A full Phase 0–5 exit-criteria rewrite against this expanded state remains queued; that pass is independent of the Phase 6 documentation.

This document walks CORE from its present state through the gating framework defined in the 2026-05-15 session. It is organized into six phases (now seven with Phase 6 below). Each phase has entry criteria, work items, exit criteria, and a benchmark discipline contract.

The benchmark discipline is the spine of the plan. Without it, the phases become aspirational. With it, "are we there yet" becomes a CLI question.

---

## Part I — Benchmark Discipline (read first)

The gates are only meaningful if the evals that prove them are honest. Five rules govern every eval lane in this roadmap. They apply uniformly; no exceptions per phase.

### Rule 1 — Three-set split per lane

Every lane maintains three disjoint corpora:

- **Dev set.** Freely visible during development. Used to iterate.
- **Public test set.** Visible, but tuning against it is forbidden. Scored at version-cut time only. Drift in dev-vs-public scores is a red flag for overfitting.
- **Private holdout.** Sealed. Never read by Claude, never committed in plaintext, only scored by a clean-room runner at release events. Stored encrypted in `evals/holdouts/` with key held by the human reviewer.

If a lane has only a dev set, it does not count as a gate. It is exploration.

### Rule 2 — Versioned difficulty escalation

Each lane has versions: `v1`, `v2`, `v3`, … with monotonically harder distributions. Passing a version is not a terminal state; it is a checkpoint that unlocks generating the next version.

- **v1** — baseline competence demonstration. The construction is shown clearly.
- **v2** — distributional shift: longer chains, deeper nesting, rarer vocabulary, paraphrased surface forms.
- **v3** — adversarial: items generated specifically by inspecting model failures on v2.
- **v4+** — out-of-distribution: items drawn from domains, registers, or constructions not present at training time.

Score is always reported as a tuple `(v1_score, v2_score, v3_score, …)`, never collapsed to a single number. A model that scores 99% on v1 and 12% on v3 is not a "99% model."

### Rule 3 — Adversarial regeneration on pass

When a model passes a version (e.g., ≥95% on the public test set with ≥90% on private holdout), the next version is *generated by adversarial process*:

- Human review finds construction families the model handled accidentally rather than structurally.
- A separate generator (could be a different model, could be programmatic) produces items targeting the weakest decile of the previous version.
- The new version is reviewed for legitimacy — no impossible items, no ambiguous items, no items that depend on world knowledge the system was never given.

This is the protection against silent overfitting: every passed version triggers the construction of a harder one, so "progress" requires continuously rising scores against continuously harder tests.

### Rule 4 — Frontier baseline tracking

For each lane, a baseline score is computed for at least one frontier transformer-based model (e.g., Claude Opus 4.7, GPT-5, Gemini 3 Ultra) on the *same* public test set. Baselines are:

- Re-scored every time a version is cut.
- Published alongside CORE's score.
- Never tuned, never prompted-engineered to maximize — the prompt is the eval task as written.

This serves two purposes: (a) it makes CORE's structural wins visible (frontier models score near zero on provenance, monotonic learning, etc.); (b) it prevents self-congratulation on lanes where CORE merely matches an LLM that was given no advantage.

### Rule 5 — Honest reporting

- Failures are reported with the same prominence as passes.
- Confidence intervals on every score (bootstrapped over the test set).
- Per-construction breakdowns published — never a single aggregate hiding structural failures.
- Regressions across versions are surfaced, never silently dropped.
- "Did not test" is a valid result; "tested and failed" is preferred over "did not test."

If a number cannot be reported honestly under these rules, the lane is not ready. Do not ship the lane.

### Eval contract template

Every eval lane lives in `evals/<lane_name>/` with this layout:

```
evals/<lane_name>/
  contract.md           # what the lane measures, scoring rubric, pass thresholds
  dev/                  # dev set, freely visible
  public/v1/            # public test set, version 1
  public/v2/            # public test set, version 2
  ...
  holdouts/             # encrypted, sealed
  runner.py             # deterministic scorer
  baselines/            # frontier model scores per version
  results/              # CORE scores per version per release
```

A lane without a `contract.md` does not run.

---

## Part II — The Phases

### Phase 0 — Benchmark methodology lock-in

**Entry criteria.** Today.

**Goal.** Build the discipline infrastructure before building any new eval. Doing this first prevents the entire roadmap from drifting into vibes-based progress.

**Work items.**

1. Implement `evals/` layout convention above.
2. Implement `core eval <lane>` CLI subcommand that loads contracts, runs the runner, writes results.
3. Implement the holdout-runner: a sandboxed process that decrypts the sealed test set, scores, writes only the aggregate score (never item-level results) back to the working tree.
4. Implement baseline-runner: a thin adapter that queries a frontier model on the public test set and records its score.
5. Write the methodology page in `docs/eval_methodology.md` (this Part I, extracted).
6. Pick one *existing* eval (the current `core eval cognition`) and retrofit it into the new convention as a forcing function. Versions become explicit; holdout is split out; results are reported per-version.

**Exit criteria.**

- `core eval cognition` runs under the new convention, with v1 public + private holdout + baseline.
- No new lane is allowed to be merged that does not follow the convention.
- The retrofit revealed at least one item-level methodology issue (silent ambiguity, leaked dev item, unstated assumption) — caught and documented. If the retrofit found nothing, the audit was not real.

**Duration estimate.** 1–2 weeks of focused work.

---

### Phase 1 — Foundational Triple

**Entry criteria.** Phase 0 exit complete.

**Goal.** Implement and pass the three gates that determine whether CORE is ready to move from engineering into curriculum:

- **grammatical-coverage** (fluency)
- **zero-code-domain-acquisition** (engineering-vs-learning phase shift)
- **identity-divergence** (identity is load-bearing)

**Work items.**

**1.1 grammatical-coverage**

- Enumerate target grammatical constructions for English v1: simple declarative, negation, conjunction, disjunction, embedded clause, relative clause, quantification (universal/existential), basic tense (past/present/future), basic aspect (perfective/imperfective).
- For each construction, write contract test pairs: `PropositionGraph → expected surface family`. "Expected surface family" is a set of acceptable surfaces, not a single string, with a deterministic acceptance predicate.
- Implement v1 dev/public/holdout (target: ~50/50/50 items).
- Engineer `realizer.py` to pass v1.
- Once v1 ≥95% public and ≥90% holdout, generate v2 (deeper nesting, rare vocabulary substitution, longer sentences).
- Repeat for Hebrew and Koine Greek using their respective pack morphology.

**1.2 zero-code-domain-acquisition**

- Define three "surprise domains" never touched in development: pick from {kinship relations, basic arithmetic, simple spatial relations, color taxonomy, calendar relations}.
- Each domain has a pack-only authoring kit: vocabulary, relation predicates, axiom list, ~20 reviewed teaching examples, ~30 articulation prompts.
- Test: an author who knows the system but is forbidden from editing Python attempts to bring CORE to ≥80% articulation accuracy on the prompts using only pack + teaching loop.
- Each Python edit required is a logged "engineering gap" that goes onto the closing list.

**1.3 identity-divergence**

- Define two identity axis sets, deliberately oriented to produce different stances on the same proposition (e.g., axis-A weights novelty highly, axis-B weights tradition highly; or axis-A is precision-first, axis-B is generosity-first).
- Curate a shared curriculum: ~100 reviewed teaching events, identical for both agents.
- Curate a prompt set where identity should produce measurably different articulations.
- Scoring: an automated divergence metric (e.g., proposition-graph difference) plus a coherence metric (each output must be internally consistent with its own axes).
- Pass: divergence above floor, coherence above floor, *both required*.
- Also: identity-stripped baseline. The same curriculum with identity disabled should produce articulations whose divergence is at noise floor — proving identity is doing the work.

**Exit criteria.**

- All three lanes pass v1 on public + holdout.
- The engineering-gap list from 1.2 is either empty or has a documented closing plan.
- v2 generation has been attempted for at least one of the three.

**Duration estimate.** 4–8 weeks. The realizer work in 1.1 is the bottleneck and may expose deeper engineering gaps.

---

### Phase 2 — Structural Wins Made Visible

**Entry criteria.** Phase 1 exit complete.

**Goal.** Build the lanes where CORE's architecture wins by design. These should pass relatively early *for CORE* and fail catastrophically *for frontier baselines*. The purpose is to publish the contrast.

**Lanes:**

- **provenance** — every articulated claim back-points to vault entries / teaching events / pack axioms; replay reproduces trace bit-for-bit.
- **monotonic-learning** — after N teaching cycles across unrelated domains, competence on domain 1 does not regress. Longitudinal: ≥10 teaching cycles, scored at each step.
- **calibration** — out-of-pack queries produce typed "no grounding" responses; in-pack queries do not. Distinguish "I don't know" / "incoherent" / "contradicts known."
- **symbolic-logic** — nested negation, modal operators (must/may/possible/necessary), counterfactual conditionals. Target ≥99% on v1.
- **adversarial-identity** — 1,000-turn red-team corpus; identity drift below noise floor.

**Work items.**

- Build each lane following the convention.
- Compute frontier baselines for each. Expected outcomes:
  - **provenance** — CORE: pass. Frontier: near-zero (no model can produce verifiable per-claim provenance).
  - **monotonic-learning** — CORE: pass by construction. Frontier: regression visible after fine-tuning rounds (this requires the frontier baseline to actually be fine-tuned, which complicates the comparison — may be reported as "not directly comparable, structural argument applies").
  - **calibration** — CORE: high if calibration is wired; frontier: confabulates on most OOD prompts.
  - **symbolic-logic** — CORE: target ≥99% v1; frontier: ~80% v1, collapses on v3.
  - **adversarial-identity** — CORE: target drift below noise; frontier: persona erodes within ~50–100 turns.
- Publish results page with per-lane comparison.

**Anti-overfitting note.** The structural wins are *structural* — the temptation to declare victory after v1 is large. Discipline: v2 and v3 must still be generated and scored. A "structural win" that fails on v3 is a structural claim that was actually a v1 coincidence.

**Exit criteria.**

- All five lanes have v1 + v2 results published with frontier baselines.
- At least two lanes have v3 results.
- The contrast page is honest about which results are "directly comparable" vs. "structural argument."

**Duration estimate.** 8–12 weeks. provenance and monotonic-learning may require new instrumentation in `vault/` and `teaching/`.

---

### Phase 3 — Reasoning Depth

**Entry criteria.** Phase 2 exit complete. This is the hardest phase. Expect engineering surprises.

**Goal.** Lanes that probe whether CORE actually *thinks* rather than retrieves and articulates.

**Lanes:**

- **compositionality** — novel combinations of taught primitives. SCAN/COGS-style splits adapted to proposition graphs.
- **inference-closure** — derive entailments never directly asserted (transitive, spatial, temporal, causal chains).
- **introspection** — `explain(turn_id)` produces a natural-language account that round-trips: a separate run conditioned on the explanation predicts the same articulation.
- **multi-step-reasoning** — pipeline produces and consumes intermediate proposition-graph states for problems whose solution requires ≥3 inferential hops.
- **cross-domain-transfer** — competence in domain B rises after teaching only in domain A, via shared structural elements.

**Work items.**

These will almost certainly expose engineering gaps. Expected gaps:

- `generate/graph_planner.py` may need an intermediate-state stack rather than a single planning pass (multi-step-reasoning).
- `field/propagate.py` may need to expose derivable-but-not-asserted recall paths (inference-closure).
- A new `cognition/explain.py` module may be needed for introspection.
- Cross-domain transfer may require examining how proposition graphs share structural sub-units, which may be a pack-design question more than a code question.

For each gap discovered, the work splits: (a) write the eval, (b) confirm it fails, (c) close the engineering gap, (d) re-run.

**Anti-overfitting note.** Compositionality is *the* lane most vulnerable to overfitting. The training-test split must be done by *construction family*, not by sampling. If the model has seen `R(A,B)` and `R(C,D)`, the test set must use a *novel relation R'* applied to seen entities — not a fresh `(A,B)` pair under a seen `R`.

**Exit criteria.**

- All five lanes have v1 results with honest scores (which may be failing — that's acceptable for v1).
- Each failure has either a closed engineering gap or a documented architectural deferral.
- At least two lanes are passing v1 by phase exit.

**Duration estimate.** 12–24 weeks. This is the phase that decides whether CORE's design lives up to its philosophical claims.

---

### Phase 4 — Scale and Efficiency

**Entry criteria.** Phase 3 exit complete. Phases 1–3 are pass/fail; this phase is *quantitative curves*.

**Goal.** Make CORE's quantitative behavior visible: how fast does it learn, how does cost scale, how does it compose at scale.

**Lanes:**

- **sample-efficiency** — corrections-to-competence curves across ten unrelated concepts. Plot, do not threshold.
- **long-context-cost** — vault size vs. per-turn latency curve at 10³, 10⁴, 10⁵, 10⁶ entries. Identify the asymptotic complexity. Decide indexing strategy if super-linear.
- **multi-agent-composition** — two CORE instances with different identities cooperate on a shared task; each maintains its own deterministic replay. Measure: task completion, replay determinism preserved per agent, no identity bleed.

**Work items.**

- Build infrastructure for longitudinal measurement (Phase 2's monotonic-learning runner is a starting point).
- Sample-efficiency requires running the teaching loop programmatically with controlled correction budgets.
- Long-context-cost may surface that the current `vault/store.py` is insufficient at scale — the response is exact indexing (B-tree, suffix array, signature-based bucketing), not approximate recall.
- Multi-agent composition surfaces orchestration questions that may justify a new module (`society/` or similar) — defer unless the eval forces it.

**Anti-overfitting note.** Curves don't overfit the way thresholds do, but they can be selectively reported. Discipline: publish the full curve, not just the best operating point. Confidence intervals at each data point.

**Exit criteria.**

- Sample-efficiency curves published for ≥10 concepts.
- Vault cost curve published with asymptotic analysis. Indexing strategy decided.
- Multi-agent composition demonstrated for ≥2-agent cooperation with replay preserved.

**Duration estimate.** 8–16 weeks.

---

### Phase 5 — Curriculum Era

**Entry criteria.** Phase 4 exit complete. From this point forward, engineering changes are exceptional, not routine. The work is curriculum design, reviewed teaching, and domain-specific evals.

**Goal.** Acquire human-comparable competence across school-level subjects, classical literature, foundational sciences, and the three foundational languages at fluency.

**Structure.**

The phase has no single exit criterion. Instead, each domain becomes its own sub-phase with its own evals:

- **5.1 English fluency** — pack + curriculum sufficient that grammatical-coverage v5 (out-of-distribution registers: legal, poetic, technical, conversational) passes.
- **5.2 Hebrew fluency** — analogous, with attention to root-and-pattern morphology.
- **5.3 Koine Greek fluency** — analogous, with attention to case and aspect.
- **5.4 Elementary mathematics** — number, arithmetic, basic algebra, geometry. Each topic becomes a pack + a domain-specific competence eval.
- **5.5 Foundational physics** — kinematics, conservation, basic mechanics.
- **5.6 Foundational biology** — taxonomy, cell, system.
- **5.7 Classical literature** — reading comprehension at increasing complexity, eventually approaching the John 1:1–2 grounding case as a depth probe.
- *(further sub-phases as curriculum expands)*

**Discipline during this phase.**

- Every new domain ships with its own competence eval following the convention.
- The Phase 1–4 lanes are re-run on every release. A new domain that causes regression in a foundational gate is a curriculum bug, not a curriculum success.
- Frontier baselines are re-scored periodically; the contrast remains visible.

**This phase has no estimated duration.** It is the phase the project lives in after the engineering era ends. Frontier-LLM parity on breadth happens *inside* this phase if it happens at all — likely measured in years, not weeks, and at whatever sample efficiency Phase 4 demonstrated.

### Phase 6 — Evidence-Governed Domain Layer

**Entry criteria:** Phase 5 corpus flywheel operational (curriculum + miner sourcing actively producing reviewed proposals); pack-layer chain (ADR-0027..0045) closed; forward-graph-constraint and surface-composer chains (ADR-0046..0089) shipping.

**Goal.** Distinguish *contract-passing* from *demonstrated* at the ledger surface. A pack that satisfies the nine ADR-0091 predicates earns a `reasoning-capable` ledger row; promotion to `expert_demo=true` requires a reviewer-signed evidence-bundle digest that reproduces byte-for-byte from on-disk lane results.

**Substrate (all accepted as of 2026-05-22):**

| Layer | What it ratifies | ADR |
|---|---|---|
| Domain Pack Contract v1 | Nine predicate checks on every ratified pack. | 0091 |
| Reviewer Registry v1 | Schema-validated reviewer roster; primary vs. domain-scoped. | 0092 |
| Domain Contract v1 implementation | Validator + ledger enforcement at runtime. | 0093 |
| Proposal source provenance | Discriminated `ProposalSource(kind=...)` for every teaching proposal. | 0094 |
| Miner-sourced proposals | `teaching/from_miner.py`; SHA-pinned `miner_loop_closure` lane. | 0095 |
| Fabrication-control eval lane | Phantom / cross-pack / sibling-collapse refusals must clean. | 0096 |
| Demo composition contract | Demos compose from shipped modules; no parallel mechanism. | 0098 |
| Public showcase demo | Deterministic, byte-equal, <30s. | 0099 |
| Reasoning-capable ratifications | `mathematics_logic` (0097), `physics` (0100), `systems_software` (0101), `hebrew_greek_textual_reasoning` (0102). |
| Fluency lane attachment | Hebrew + Koine Greek lanes attached to ADR-0102 packs with dev/public/holdout. | 0103 |
| Curriculum-sourced proposals | `teaching/from_curriculum.py`; SHA-pinned `curriculum_loop_closure` lane. | 0104 |
| Sealed-holdout encryption | age-based; dev-mode plaintext fallback preserved. | 0105 |
| **Expert-demo promotion contract** | **Domain-aware, reviewer-signed, replay-deterministic gate.** | **0106** |
| Lane-shape registry | 8 lane ids dispatch to 5 shapes; unknown lanes fail-closed. | 0109 (amends 0106) |

**Worked promotion narrative.** The contract has been demonstrated end-to-end:

1. **ADR-0107** — first promotion attempt (`mathematics_logic`) honestly refused by the contract on two named blockers (metric-shape uniformity assumption; `inference_closure` substantively failing at 40% pass).
2. **ADR-0109** — threshold rules amended with explicit lane-shape registry; cognition-shape thresholds preserved bit-identical; four new shapes added (`accuracy_shape`, `inference_shape`, `refusal_shape`, `symbolic_logic_shape`); unknown lanes fail-closed.
3. PR #117 fixed the intent-classifier regression that had broken `inference_closure`.
4. **ADR-0110** — `mathematics_logic` promoted to `expert_demo=true` under the amended contract. Signed claim digest reproduces from on-disk lane results; first domain at expert-demo.

**Exit criteria (cumulative; each can land independently of the others):**

- ☑ Contract definition (ADR-0091..0093) and reviewer trust root (ADR-0092) accepted.
- ☑ Negative-control fabrication lane (ADR-0096) ratified and SHA-pinned.
- ☑ Four reasoning-capable domain ratifications (ADR-0097/0100/0101/0102).
- ☑ Expert-demo promotion contract accepted (ADR-0106 + ADR-0109 amendment).
- ☑ First worked promotion lands (ADR-0110 — `mathematics_logic`).
- ☐ Second worked promotion lands (next domain: TBD; `physics` / `systems_software` / `hebrew_greek_textual_reasoning` all eligible under the now-amended contract).
- ☐ Multi-reviewer signing (currently single-recipient; the open candidate frontier item from ADR-0105).

**Why this is its own phase.** Phases 1–5 measure capability *internally*. Phase 6 is the first layer that measures *what the system has actually demonstrated to an external reader* and forces the ledger to distinguish the two. Every prior phase makes claims about the substrate; Phase 6 makes the substrate's claims auditable.

**This phase has no estimated duration.** Each new domain promotion is a discrete unit of work; the contract is the durable artifact.

---

## Part III — Cross-Cutting Considerations

### Versioning of the framework itself

This roadmap is `v1`. As phases complete, the framework may itself need amendment — new lanes added, methodology refined. Treat the roadmap with the same discipline as the evals: version it, never silently rewrite it. Each amendment is dated and explained.

### Scope decisions deferred

Two scope decisions named in the 2026-05-15 session remain open and will be pinned before they cause drift:

- **Agency** — responsive vs. goal-directed. Defaulting to *responsive* for Phases 0–4. Phase 5 may revisit.
- **Embodiment** — symbolic-only vs. sensorimotor. ADR-0013 establishes the sensorium protocol; this roadmap does not assume sensorium-dependent gates in Phases 0–4. Phase 5 may add sensorium-dependent sub-phases.

Two further questions emerged during Phase planning that should be decided early:

- **Tool use.** Is the pipeline extensible to typed deterministic operators (calculator, search, code execution)? Decision needed before Phase 3, since multi-step-reasoning may benefit from operator delegation.
- **Code generation.** Is code a first-class proposition-graph articulation target? Decision needed before Phase 5 if computer-science is a curriculum domain.

### What this roadmap is not

- Not a list of features. The features fall out of the gates.
- Not a competitive roadmap against frontier LLMs. The contrast is a side effect, not a target.
- Not a commitment to dates. The duration estimates are calibration aids, not deliverable schedules.
- Not a substitute for the work-sequencing list in `CLAUDE.md`. That list governs daily work; this document governs the arc.

### Failure modes to watch for

- **Vibes-based progress.** "It feels smarter" is not a gate.
- **Demo-driven development.** Crafting a single impressive interaction is not progress; passing a sealed holdout is.
- **Teaching-set leakage.** If the same content appears in pack, teaching, and eval, scores are uninterpretable.
- **Frontier envy.** Trying to match frontier LLMs on lanes where they structurally win (e.g., long-tail stylistic breadth) compromises the lanes where CORE structurally wins.
- **Lane proliferation.** Adding lanes is cheap; maintaining honest holdouts is expensive. Resist new lanes unless they probe a distinct capability.

---

## Part IV — Immediate Next Actions

1. Decide whether this roadmap is promoted to an ADR (likely `ADR-0016`).
2. Stub `docs/eval_methodology.md` as the extracted Part I (it's the contract every lane inherits).
3. Begin Phase 0: implement `evals/` convention, retrofit `core eval cognition` into it.
4. Pin the *agency* scope decision in writing before Phase 3 begins.
5. Pin the *tool use* scope decision in writing before Phase 3 begins.

Phase 0 starts when the human reviewer signs off on this roadmap. The first measurable signal of progress is the `core eval cognition` retrofit landing under the new convention.
