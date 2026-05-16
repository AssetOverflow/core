# Capability Roadmap — Progress Tracker

Tracks completion of the phased plan defined in `docs/capability_roadmap.md`
(ADR-0016). Updated as work lands.

---

## Phase 0 — Benchmark Methodology Lock-in

**Status:** Complete
**Started:** 2026-05-15
**Completed:** 2026-05-16

- [x] Promote roadmap to ADR-0016
- [x] Extract `docs/eval_methodology.md` from roadmap Part I
- [x] Create progress tracker (`docs/PROGRESS.md`)
- [x] Implement `evals/<lane>/` directory convention
- [x] Build generic eval framework (`evals/framework.py`)
- [x] Retrofit `core eval cognition` into new convention
  - [x] Split 45 cases into dev (13) / public v1 (13) / holdout (19)
  - [x] Write `evals/cognition/contract.md`
  - [x] Migrate `runner.py` to use framework
  - [x] Record v1 results under new layout
- [x] Generalize `core eval <lane>` CLI (dynamic lane discovery)
- [x] Implement holdout runner scaffold
- [x] Implement baseline runner scaffold
- [x] **Exit gate:** `core eval cognition` runs under new convention with v1 public + holdout + baseline

### Methodology issues discovered (Phase 0 audit)

1. **Pipeline turn_log crash:** `CognitiveTurnPipeline.run()` assumed `turn_log`
   was always populated after `chat()`, but the unknown-domain gate returns a
   stub without appending. Fixed with fallback to tokenizer output.
2. **Versor drift in multi-turn sessions:** `test_pipeline_preserves_versor_closure`
   reveals that after 3 turns in the same session, "spirit breath" causes
   `versor_condition = 1.12e-04` (threshold: 1e-6). Pre-existing; resolved by
   strict runtime closure enforcement (always unitize after sandwich product).
3. **Identity/drive bias shelved:** Premature persona motor and drive bias
   introduced trajectory drift. Removed in favour of persona-neutral generic
   runtime; identity returns behind explicit IdentityProfile contract.

---

## Phase 1 — Foundational Triple

**Status:** Complete ✓
**Started:** 2026-05-16
**Completed:** 2026-05-16
**Depends on:** Phase 0 exit

- [x] **grammatical-coverage** lane (v1 + v2 complete)
  - [x] Enumerate English v1 constructions (13 constructions: C01-C13)
  - [x] Write contract test pairs (PropositionGraph -> surface family)
  - [x] Implement v1 dev/public (~41/36 items)
  - [x] Implement holdout (52 items) — 100% pass
  - [x] Engineer `realizer.py` to pass v1 (dev=100%, public=100%, holdout=100%)
  - [x] Hebrew pack (`he_core_cognition_v1` with binyanim support)
  - [x] Koine Greek pack (`grc_logos_cognition_v1` with Greek morphology)
  - [x] Generate v2 on pass (deeper nesting, longer sentences, rarer vocabulary) — 36 cases (100% pass)
- [x] **zero-code-domain-acquisition** lane (v1 complete, zero engineering gaps)
  - [x] Define 3 surprise domains (kinship, calendar, color)
  - [x] Build pack-only authoring kits (vocabulary, relations, axioms, teaching examples, prompts)
  - [x] Test: author brings CORE to >=80% without Python edits (100% achieved)
  - [x] Log engineering gaps (ZERO — pack-only authoring contract is solid)
  - [x] v1 dev (30/30), v1 public (18/18 across all 3 domains), v1 holdout (21/21) — all 100% pass
- [x] **identity-divergence** lane (v1 complete)
  - [x] Define two identity axis sets (Axis A: Precision-first, Axis B: Generosity-first)
  - [x] Curate shared curriculum (93 teaching events across color/kinship/reasoning/spatial)
  - [x] Build divergence metric (>0.30 threshold): all pass (1.000)
  - [x] Build coherence metric (>0.85 threshold for A and B): all pass (1.000)
  - [x] Identity-stripped baseline with causal check: all pass (delta=1.000)
  - [x] v1 dev (5/5), v1 public (5/5), v1 holdout (5/5) — all 100% pass
- [x] **Exit gate:** All three lanes pass v1 public + holdout ✓

---

## Phase 2 — Structural Wins Made Visible

**Status:** In Progress
**Started:** 2026-05-16
**Depends on:** Phase 1 exit

- [x] **provenance** lane (v1 complete)
  - [x] Define Provenance dataclass + compute_provenance() (`core/cognition/provenance.py`)
  - [x] Unit tests for provenance derivation (6/6 pass — `tests/test_provenance.py`)
  - [x] Build pack-axiom / vault-recall / teaching / mixed case categories
  - [x] v1 dev (10/10), v1 public (20/20), v1 holdouts (15/15) — all 100% pass
  - [x] Sub-metrics: replay_determinism=1.0, source_attribution=1.0, source_validity=1.0, input_sensitivity=1.0
  - [x] Fixed shape regression in `generate/stream.py` score-weighted recall (np.eye → multivector identity)
  - [x] Replaced linear-blend rotor scaling with manifold-preserving `rotor_power` (`algebra/rotor.py`); 41 closure-preservation tests
  - [x] Restored `respond()`/`result.final_state` identity contract after anchor pull
- [x] **monotonic-learning** lane (v1 complete)
  - [x] Define contract: longitudinal regression check across ≥10 teaching cycles
  - [x] Implement runner: shared session, sorted ops, per-(cycle, domain) accuracy table
  - [x] Generator (`scripts/generate_monotonic_cases.py`) for cycle/probe corpora
  - [x] v1 dev (10 cycles), v1 public (12 cycles, 3 domains), v1 holdouts (12 cycles, 2 distinct domains)
  - [x] All splits: max_regression=0.00, floor_score=1.00, overall_pass=true
  - [x] Structural win demonstrated: zero regression across 34 total cycles / 7 distinct domains
- [x] **calibration** lane (v1 complete)
  - [x] Define contract: typed signals for no_grounding / coherent / correction_proposed
  - [x] Classification from `CognitiveTurnResult` (vault_hits + pack_mutation_proposal)
  - [x] Runner with per-case fresh pipeline (avoids cross-case field drift)
  - [x] v1 dev (12/12), v1 public (24/24), v1 holdouts (18/18) — all 100% pass
  - [x] Sub-metrics: no_grounding=1.0, coherent=1.0, correction_proposed=1.0
  - [x] Architectural finding documented (`evals/calibration/gaps.md`): the
        ingest gate is geometric, not semantic — 6/42 hand-chosen OOD
        prompts fire the geometric gate. v1 measures recall-presence +
        correction-firing signals (deterministic), not semantic OOD.
        Pipeline override of gate's safety surface is a separate gap.
- [x] **symbolic-logic** lane (v1 complete)
  - [x] Define contract: structural foundations for proposition-based inference
  - [x] Patterns: modus_ponens_chain, modus_tollens_chain, syllogism, negation, chain_recall
  - [x] Runner: per-case fresh pipeline + double-run replay check
  - [x] Sub-metrics: premise_recall=1.0, replay_determinism=1.0, proposal_storage=1.0
  - [x] v1 dev (8/8), v1 public (18/18), v1 holdouts (12/12) — all 100% pass
  - [x] Architectural finding documented (`evals/symbolic_logic/gaps.md`): CORE
        has no first-class inference operator yet. v1 measures the storage,
        replay, and recall foundations on which a future inference engine
        would be built. v2 would assert specific inference correctness
        (transitive recall surface contents).
- [x] **adversarial-identity** lane (v1 complete)
  - [x] Define contract: identity-override attacks rejected at review;
        legitimate corrections still accepted
  - [x] Cover all `_IDENTITY_MARKERS` families (you are / forget / pretend /
        override / ignore / your name / act as / from now / character /
        personality)
  - [x] Per-case fresh pipeline; prior question primes the review surface
  - [x] Sub-metrics: attack_rejection_rate=1.0, legitimate_acceptance_rate=1.0
  - [x] v1 dev (10/10), v1 public (25/25), v1 holdouts (18/18) — all 100% pass
- [x] **All five Phase 2 v1 lanes passing** ✓
- [x] Frontier baselines computed for all lanes (structural-zero floor)
  - [x] `docs/frontier_baselines.md` — per-lane analysis: frontier LLMs do
        not emit the typed signals CORE's rubrics score against
        (provenance sources, pack_mutation_proposal, vault_hits,
        REJECTED_IDENTITY outcome, deterministic trace_hash)
  - [x] Per-lane structural-zero baseline JSON written under
        `evals/<lane>/baselines/v1_structural_zero.json`
  - [x] `StructuralZeroBaseline` adapter in `evals/baseline_runner.py`
        — deterministic floor; live-API adapters can be added when
        keys are configured
- [x] v2 lanes: all five at 100% pass
  - monotonic-learning v2 — 20 cyc / 5 dom (public), 18 cyc / 4 dom (holdouts)
  - provenance v2 — 30 + 20 cases, all sub-metrics 1.0
  - adversarial-identity v2 — 35 + 22 cases, all 1.0
  - calibration v2 — 33 + 24 cases, all class accuracies 1.0
  - symbolic-logic v2 — 24 + 16 cases (chains up to 5 hops), all 1.0
- [ ] **Exit gate:** v3 lanes for at least two of the five

### Parallel eval infrastructure (2026-05-16)

- `evals/parallel.py` — `run_cases_parallel()` helper using
  `multiprocessing.Pool` with the `"spawn"` start method (avoids
  forking heavy parent state).  Default workers = `min(cpu_count, 8)`.
- Wired into the four per-case lanes (provenance, calibration,
  symbolic-logic, adversarial-identity).  `run_lane(..., workers=N)`
  controls parallelism; `workers=1` forces serial for debugging.
- Empirical speedup (adversarial-identity public/v1, 25 cases):
  serial 14.1s → parallel 3.1s (~4.5x).
- Monotonic-learning intentionally stays serial within a split
  (shared longitudinal session by design).

---

## Phase 3 — Reasoning Depth

**Status:** Not Started
**Depends on:** Phase 2 exit

- [ ] **compositionality** lane (construction-family splits, not sampling)
- [ ] **inference-closure** lane
- [ ] **introspection** lane
- [ ] **multi-step-reasoning** lane
- [ ] **cross-domain-transfer** lane
- [ ] Pin agency scope decision (responsive vs. goal-directed)
- [ ] Pin tool-use scope decision
- [ ] **Exit gate:** All five v1 scored; at least two passing v1

---

## Phase 4 — Scale and Efficiency

**Status:** Not Started
**Depends on:** Phase 3 exit

- [ ] **sample-efficiency** curves (>=10 concepts)
- [ ] **long-context-cost** curves (10^3 to 10^6 vault entries)
- [ ] **multi-agent-composition** (>=2 agents, replay preserved)
- [ ] Vault indexing strategy decided
- [ ] **Exit gate:** All curves published with confidence intervals

---

## Phase 5 — Curriculum Era

**Status:** Not Started
**Depends on:** Phase 4 exit

- [ ] 5.1 English fluency (grammatical-coverage v5 OOD)
- [ ] 5.2 Hebrew fluency
- [ ] 5.3 Koine Greek fluency
- [ ] 5.4 Elementary mathematics
- [ ] 5.5 Foundational physics
- [ ] 5.6 Foundational biology
- [ ] 5.7 Classical literature
- [ ] Phase 1-4 lanes re-run on every release (no regression)

---

## Open Scope Decisions

| Decision | Status | Deadline |
|----------|--------|----------|
| Agency (responsive vs. goal-directed) | Open | Before Phase 3 |
| Tool use (typed deterministic operators) | Open | Before Phase 3 |
| Code generation (first-class target) | Open | Before Phase 5 |
| Embodiment (sensorium gates) | Open | Phase 5 |
