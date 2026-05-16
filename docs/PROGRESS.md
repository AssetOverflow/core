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

**Status:** In Progress
**Started:** 2026-05-16
**Depends on:** Phase 0 exit

- [ ] **grammatical-coverage** lane
  - [x] Enumerate English v1 constructions (13 constructions: C01-C13)
  - [x] Write contract test pairs (PropositionGraph -> surface family)
  - [x] Implement v1 dev/public (~41/36 items)
  - [ ] Implement holdout (~50 items)
  - [ ] Engineer `realizer.py` to pass v1 (baseline: dev=24%, public=19%)
  - [ ] Generate v2 on pass
  - [ ] Hebrew pack
  - [ ] Koine Greek pack
- [ ] **zero-code-domain-acquisition** lane
  - [ ] Define 3 surprise domains
  - [ ] Build pack-only authoring kits
  - [ ] Test: author brings CORE to >=80% without Python edits
  - [ ] Log engineering gaps
- [ ] **identity-divergence** lane
  - [ ] Define two identity axis sets
  - [ ] Curate shared curriculum (~100 teaching events)
  - [ ] Build divergence + coherence metrics
  - [ ] Identity-stripped baseline
- [ ] **Exit gate:** All three lanes pass v1 public + holdout

---

## Phase 2 — Structural Wins Made Visible

**Status:** Not Started
**Depends on:** Phase 1 exit

- [ ] **provenance** lane
- [ ] **monotonic-learning** lane
- [ ] **calibration** lane
- [ ] **symbolic-logic** lane
- [ ] **adversarial-identity** lane
- [ ] Frontier baselines computed for all lanes
- [ ] **Exit gate:** All five v1+v2 with baselines; at least two have v3

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
