# CORE General Advancement Plan

**Status:** Proposed  
**Date:** 2026-05-26  
**Scope:** Documentation / planning only  
**Anchor context:** ADR-0163 GSM8K corridor, ADR-0161 HITL queue, ADR-0160/0162 Workbench, existing eval methodology

---

## Executive summary

CORE should not advance by chasing a broad external benchmark suite first.  The next master path is a three-lane sequence:

1. **Exploit the live ADR-0163 GSM8K corridor now** because it is the freshest, proven, end-to-end capability-growth mechanism.
2. **Instrument broader Tier-3 / generalization lanes in parallel** so general advancement is measured rather than assumed.
3. **Delay broad external benchmarks until they are diagnostic adapters**, not vanity refusal generators.

The governing principle is:

```text
truth before coverage
refusal before confabulation
replay before claims
```

CORE's current advantage is not raw benchmark breadth.  Its current advantage is that capability growth can be measured under deterministic replay, typed refusal, operator-ratified mutation, and `wrong == 0` discipline.  The plan below preserves that advantage while creating a route toward broader capability.

---

## Current pinned state

The current mainline state after the ADR-0163 corridor work is:

```text
GSM8K train_sample_v1:
  correct: 3
  refused: 47
  wrong: 0
  exit: failed, correct_min=10
```

Interpretation:

- This is the first measurable non-zero GSM8K lift.
- The `wrong == 0` invariant remains intact.
- The result is still far from an expert-capability claim.
- The latest question-grammar extension moved some cases from question-level refusal into solver-side refusal, which means the current bottleneck is no longer only grammar/admission; it is increasingly **solver composition over admitted anchors**.

The current refusal profile says the next capability work should target *composition semantics*, not broad benchmark breadth.

---

## Comparison of candidate plans

Three planning directions were considered:

| Direction | Strength | Failure mode |
|---|---|---|
| GSM8K-first corridor | Grounded in the freshest live mechanism; has clear measurable gates | Can become narrow if it ignores generalization lanes |
| Refusal-taxonomy / parser expansion | Correctly protects `wrong == 0` and focuses on admission gaps | Stale if it assumes the current result is still full refusal; newest work has moved some failures downstream |
| Tier-3 / generalization-first | Correctly asks whether progress transfers beyond math | Can become premature if lanes are stubbed or if operators are built before measured gaps are pinned |

The superior plan is a fused route:

```text
A. Finish the active GSM8K corridor to prove safe capability growth.
B. Build a CORE General Panel over existing lanes and Tier-3 readiness.
C. Populate missing Tier-3/generalization lanes with real numbers.
D. Build only the operators revealed by those measurements.
E. Add external benchmark adapters once they produce actionable deltas.
```

---

## Phase 1 — ADR-0163 Phase E: GSM8K lift history

### Branch recommendation

```bash
feat/adr-0163-phase-e-gsm8k-lift-history
```

### Purpose

Make every GSM8K improvement undeniable, versioned, and reviewable before further solver changes land.

### Deliverables

```text
evals/gsm8k_math/train_sample/v1/baselines/
evals/gsm8k_math/train_sample/v1/history/
evals/gsm8k_math/train_sample/v1/lift_report.schema.json
evals/gsm8k_math/train_sample/v1/build_lift_report.py
```

Each run should emit a `LiftReport` shaped roughly as:

```json
{
  "schema_version": 1,
  "base_sha": "...",
  "head_sha": "...",
  "counts_before": {"correct": 3, "refused": 47, "wrong": 0},
  "counts_after": {"correct": 0, "refused": 0, "wrong": 0},
  "delta": {"correct": 0, "refused": 0, "wrong": 0},
  "newly_correct_cases": [],
  "newly_wrong_cases": [],
  "refusal_shift_histogram": {},
  "trace_hash_stability": 1.0,
  "wrong_zero_preserved": true
}
```

### Acceptance gates

```text
wrong == 0
trace/run determinism stable
append-only history
case-level refusal shifts visible
current baseline pinned at 3/47/0
```

### Why this comes first

Without this, the next solver lift becomes narrative rather than evidence.  ADR-0163's power is the corridor: measure, widen, replay, ratify, re-measure.  Phase E makes that loop durable.

---

## Phase 2 — ADR-0163 D.5: solver composition over admitted anchors

### Branch recommendation

```bash
feat/adr-0163-d5-solver-composition
```

### Purpose

Convert already-admitted question/statement anchors into solvable graph state.

Recent question grammar work widened admissibility but did not lift correctness beyond `3/47/0`.  Several cases now reach `no branch produced a solvable graph`, showing the bottleneck has moved from grammar into solver-side composition.

### Target composition shapes, in priority order

| Target | Why first |
|---|---|
| earnings-rate composition | Common and checkable: `makes $18/hour`, `earns X per Y` |
| profit-target composition | Cost/revenue/target problems become solvable only when target arithmetic composes |
| unit partition composition | Common GSM8K surface: split into sections, groups, packs, bags |
| fractional transfer/change | Needed for `1/4 of`, `decrease to 3/4`, `half of` |
| comparative delta semantics | Must stay gated until `how many more` computes a difference, not a total |

### Acceptance gate

```text
GSM8K train_sample_v1:
  correct >= 10
  wrong == 0
```

This is ADR-0163 Round 1 exit.

### Non-negotiables

- No answer-producing fast path that bypasses verifier discipline.
- No broad regex widening that raises wrong risk without solver semantics.
- Comparative surfaces remain detection-gated until delta semantics are implemented.
- Any candidate that would increase `wrong` is rejected by replay, not accepted by operator judgment.

---

## Phase 3 — CORE General Panel v0

### Branch recommendation

```bash
feat/evals-core-general-v0
```

### Purpose

Create a broad internal measurement panel before using broad external benchmarks as steering targets.

### Proposed command

```bash
core eval panel core_general_v0 --json
```

### Panel contents

```text
core_general_v0:
  gsm8k_train_sample_v1
  math_capability_axes_G1_G5_S1
  cognition
  provenance
  calibration
  monotonic_learning
  symbolic_logic
  adversarial_identity
  refusal_taxonomy
  realizer_guard
  workbench_chat_smoke
  tier3_readiness
```

### Panel metrics

```text
correct
wrong
refused
decoded_unarticulated
trace_hash_stability
replay_equivalence_rate
versor_condition_max
unknown_domain_gate_honored
proposal_mutation_count
unratified_mutation_count
cross_case_determinism
```

### Acceptance gates

```text
single JSON report emitted
all included lane reports referenced by path/SHA
no fake pass for missing lanes
TBD/stub lanes represented as readiness gaps, not success
wrong == 0 across answer-producing lanes
```

### Why this matters

This creates an honest general dashboard without pretending CORE is already broad-benchmark-ready.  It gives the operator and engineers one panel to inspect capability growth, safety invariants, and lane readiness.

---

## Phase 4 — Tier-3 readiness and first numbers

### Branch recommendation

```bash
feat/evals-tier3-readiness-and-first-numbers
```

### Purpose

General advancement cannot be judged by GSM8K alone.  The missing question is whether CORE's learning and reasoning transfer.

### Lanes to classify and/or populate

| Lane | Question answered |
|---|---|
| `inference_closure` | Can CORE derive consequences rather than merely recall premises? |
| `multi_step_reasoning` | Can CORE preserve context through chained operations? |
| `symbolic_logic_v3+` | Can proposition structure become actual inference correctness? |
| `cross_domain_transfer` | Can a learned structure in one domain map into another? |
| `compositionality` | Can known smaller relations compose into unseen larger ones? |
| `sample_efficiency` | How many reviewed examples are required before lift? |

### Required classification

Every Tier-3 lane should be classified as one of:

```text
runnable_with_numbers
scaffold_only
missing_cases
missing_runner
missing_operator
```

### Deliverables

```text
1. classify every Tier-3 lane
2. run every runnable lane
3. for non-runnable lanes, add contract.md / minimal dev cases / gaps.md as appropriate
4. update core_general_v0 with tier3_readiness summary
```

### Acceptance gates

```text
no TBD row represented as progress
all runnable lanes have deterministic reports
all non-runnable lanes have explicit reason and next engineering dependency
```

---

## Phase 5 — Structural pattern recognizer v1

### Branch recommendation

```bash
feat/structural-pattern-recognizer-v1
```

### Purpose

Enable measured cross-domain transfer without hand-waving.

### Build order

1. **Structural pattern recognizer over PropositionGraph**
   - relation-shape extraction
   - variable role labeling
   - source/target domain separation
   - deterministic canonical pattern digest

2. **Matched-control transfer eval**
   - same structure, different vocabulary/domain
   - A-arm seeded, B-arm unseeded
   - require B-arm improvement only when structural isomorphism exists

3. **Cross-domain transfer operator**
   - only after matched-control evidence identifies the exact transfer gap

### Acceptance gates

```text
B-arm lift > 0
A-arm unchanged
wrong == 0
no unratified corpus mutation
trace hashes stable
canonical pattern digests stable
```

### Guardrail

Do not build a grand transfer operator before the structural recognizer and matched-control eval prove the shape of the gap.

---

## Phase 6 — Spatial / geometry OOD lane

### Branch recommendation

```bash
feat/evals-spatial-geometry-ood-v1
```

### Purpose

Test a domain where CORE's substrate should eventually have structural advantage rather than merely chase transformer-style text benchmarks.

### Start text-only

Do **not** start with image geometry.  Start with text-only spatial/geometric reasoning.

### Proposed cases

```text
relative position
containment
intersection
distance/order relations
simple geometric transformations
diagram-free Euclidean word problems
```

### Deliverables

```text
evals/spatial_geometry_ood/contract.md
evals/spatial_geometry_ood/dev/cases.jsonl
evals/spatial_geometry_ood/public/v1/cases.jsonl
evals/spatial_geometry_ood/runner.py
```

---

## External benchmark adapter ladder

External benchmarks should validate the internal substrate; they should not blindly steer development while the substrate is still missing operators.

| Stage | External benchmark | Use |
|---|---|---|
| Now | None as primary | Existing internal signals are more actionable |
| After GSM8K `>=10/50/0` | GSM8K public split | Same substrate, broader sample |
| After Tier-3 numbers exist | BBH-lite | Reasoning-shape diagnostic |
| After factuality lane exists | SimpleQA-lite | Maps cleanly to correct / incorrect / not attempted |
| After science packs mature | GPQA subset | Science reasoning diagnostic |
| After broad seeded knowledge exists | MMLU-Pro | Otherwise mostly measures missing lexicon |
| After code substrate exists | HumanEval / SWE-bench Verified | Requires code-generation / repo-repair substrate |
| After visual ingestion exists | MMMU | Requires multimodal substrate |
| After durable tool runtime exists | Tau-bench | Requires agent/tool action semantics |

---

## What not to do yet

1. **Do not make MMLU-Pro the next primary objective.**
   - It will mostly measure missing broad lexicon/domain packs at this stage.

2. **Do not run LiveBench as a primary steering metric yet.**
   - It is valuable later, but currently too broad to identify CORE-specific engineering deltas.

3. **Do not build SWE-bench / HumanEval lanes before code substrate exists.**
   - Otherwise the result is predictable refusal rather than useful diagnosis.

4. **Do not build MMMU before visual ingestion exists.**
   - It would test missing modality infrastructure, not reasoning.

5. **Do not broaden answer surfaces by weakening refusal discipline.**
   - A higher correct count with `wrong > 0` is a regression, not progress.

6. **Do not represent stubbed Tier-3 lanes as green.**
   - Readiness classification is acceptable; fake success is not.

---

## Recommended immediate PR sequence

### PR 1 — GSM8K Phase E lift history

```bash
feat/adr-0163-phase-e-gsm8k-lift-history
```

Exit:

```text
LiftReport exists
history append-only
current baseline pinned at 3/47/0
wrong == 0 preserved
```

### PR 2 — D.5 solver composition

```bash
feat/adr-0163-d5-solver-composition
```

Exit:

```text
GSM8K train_sample_v1 correct >= 10
wrong == 0
```

### PR 3 — CORE General Panel + Tier-3 readiness

```bash
feat/evals-core-general-v0-tier3-readiness
```

Exit:

```text
core eval panel core_general_v0 --json
Tier-3 lane readiness classified
all runnable Tier-3 lanes measured
no fake TBD rows represented as progress
```

### PR 4 — Structural recognizer v1

```bash
feat/structural-pattern-recognizer-v1
```

Exit:

```text
canonical pattern digests
matched-control transfer cases
no cross-domain wrong answers
```

---

## Final doctrine

The master path is:

```text
GSM8K corridor proves safe capability growth.
core_general_v0 proves broad internal measurement.
Tier-3 lanes reveal generalization bottlenecks.
Structural recognizer + transfer operator attack the measured bottleneck.
External benchmarks validate once they become actionable.
```

This keeps CORE aligned with its strongest architectural claim: deterministic, traceable, refusal-first cognition whose capability growth is replay-verifiable rather than merely asserted.
