# Substrate Liveness Registry

**Scope:** [substrate-liveness-audit-scope](../decisions/substrate-liveness-audit-scope.md) (v2)
**Status:** Active audit — append-only as layers are completed.
**Discipline:** [feedback-adr-cross-reference-discipline](../../../.claude/projects/-Users-kaizenpro-Projects-core/memory/feedback-adr-cross-reference-discipline.md), [feedback-cleanup-as-you-find](../../../.claude/projects/-Users-kaizenpro-Projects-core/memory/feedback-cleanup-as-you-find.md)

## Audit progress

| Layer | Status | Verdict | Cleanup performed | Last audited |
|---|---|---|---|---|
| L0 — Algebra primitives | ✅ Audited | **CLOSED** | None — no dead code found | 2026-05-24 |
| L1 — Field substrate | ✅ Audited | **PARTIAL** | None — no dead code found | 2026-05-24 |
| L2 — Vault | ✅ Audited | **PARTIAL** | None — flagged learning as wiring debt | 2026-05-24 |
| L3 — Language packs | ✅ Audited | **PARTIAL** | None — flagged readback as wiring debt | 2026-05-24 |
| L4 — Recognition | ⏳ Pending | — | — | — |
| L5 — Cognition pipeline | ⏳ Pending | — | — | — |
| L6 — Chat runtime + surface composition | ⏳ Pending | — | — | — |
| L7 — Teaching loop | ⏳ Pending | — | — | — |
| L8 — Inter-session memory + contemplation | ⏳ Pending | — | — | — |
| L9 — Epistemic state + verdicts | ⏳ Pending | — | — | — |

L10 / L11 are not audit targets (no design to audit; flagged in scope as
gaps the audit will surface need for).

---

## L0 — Algebra primitives

**Audit date:** 2026-05-24
**Auditor:** primary agent (Claude)
**Verdict:** **CLOSED**

### Scope-hypothesis correction (per audit step 0)

The scope's layering table cited `algebra/backend/` (directory). Reality:
`algebra/backend.py` (single 267-line file). Hypothesis drift, not a
finding — recorded so the scope's layering map can be amended if it
matters elsewhere.

### ADRs in scope for L0

Triaged from the broader algebra/versor/CGA keyword grep against
`docs/decisions/`:

| ADR | Title | Status | Belongs at L0? |
|---|---|---|---|
| ADR-0001 | VocabManifold Versor Invariant | Accepted | Yes — defines the `versor_condition < 1e-6` invariant L0 must preserve |
| ADR-0003 | Coordinate System Dissolution | Accepted | Yes — algebraic foundation |
| ADR-0004 | Rotor as Operator, Not Vocabulary Property | Accepted | Yes — defines rotors as L0 primitives |
| ADR-0009 | Compositional Physics | Accepted | Yes — versor composition rules |

Other ADRs surfaced by the grep but assigned to higher layers (not
audited at L0): ADR-0006 (L1), ADR-0019 (L2), ADR-0010 (L3 identity),
ADR-0021/0022/0023/0024/0025 (L5 policy), ADR-0020 (cross-cutting Rust
parity, audit when relevant).

### Modules in scope for L0

| Module | Lines | Live-import sites (outside `algebra/`, outside `tests/`) | Test-import sites |
|---|---|---|---|
| `algebra/__init__.py` | 5 | (re-export shim) | — |
| `algebra/backend.py` | 267 | 21 | 16 |
| `algebra/cga.py` | 84 | 16 | 17 |
| `algebra/cl41.py` | 165 | 8 | 10 |
| `algebra/holonomy.py` | 100 | 2 | 5 |
| `algebra/rotor.py` | 179 | 5 | 8 |
| `algebra/versor.py` | 180 | 20 | 19 |

Every module has at least 2 live-import sites outside `algebra/`. No
dormant modules at L0.

### Caller-trace evidence

Sample of live callers (full grep: `grep -rn "from algebra\|import algebra" --include="*.py" | grep -v "^algebra/" | grep -v "tests/"` — 38 distinct caller files):

- `field/propagate.py:23` — versor application during field propagation (L1 → L0)
- `ingest/gate.py:33` — versor/energy at injection boundary (L1 → L0)
- `language_packs/compiler.py:14` — versor construction during pack compilation (L3 → L0)
- `chat/runtime.py` — versor operations in the live turn loop (L6 → L0)
- `generate/intent_ratifier.py`, `generate/admissibility.py`, `generate/proposition.py` — versor-gated generation (L5 → L0)
- `core/cli.py:446-469` — versor diagnostics surfaced to operator (CLI → L0)

Every live caller traces back to the runtime entry through at least one
of: `core chat`, `core eval cognition`, or the field/ingest pipeline.

### Exercising suite lane

`core test --suite algebra` — 13 test files, every L0 module covered:

| Module | Tests in algebra suite |
|---|---|
| `versor.py` | test_versor_closure, test_holonomy, test_energy, test_motor, test_versor_condition_rust_parity, test_versor_apply_rust_parity |
| `rotor.py` | test_versor_closure, test_energy |
| `holonomy.py` | test_holonomy, test_holonomy_resonance |
| `cga.py` | test_holonomy_resonance, test_null_cone, test_vault_recall |
| `cl41.py` | test_vault_recall_vectorised |
| `backend.py` | test_vault_recall_vectorised, test_vault_recall_rust_parity, test_cga_inner_rust_parity, test_geometric_product_rust_parity, test_versor_condition_rust_parity, test_versor_apply_rust_parity |

**Verification:** `python3 -m core.cli test --suite algebra -q` →
**82 passed, 50 skipped** (skipped are Rust-parity tests on a Python-
only environment; not a closure gap).

### Cross-layer contract check

**Pass 1 — mechanical (consumer-exists per exposed symbol):**

| Exposed symbol | Consumer evidence |
|---|---|
| `versor_apply` | `field/propagate.py`, `generate/stream.py`, `chat/runtime.py` (3+ live consumers) |
| `versor_condition` | `core/cognition/trace.py:34`, `evals/cognition/runner.py:60` (gated in evals at `< 1e-6`) |
| `normalize_to_versor` | `generate/intent_ratifier.py`, `generate/admissibility.py` |
| `cga_inner` | `vault/store.py`, `algebra/backend.py` (`_CGA_INNER_METRIC`), `evals/lab/vault_epistemic_trace.py` |
| `embed_point`, `is_null`, `null_project` | `vault/store.py`, `language_packs/compiler.py`, `field/operators.py` |
| `using_rust`, `vault_recall` (backend) | `vault/store.py`, all Rust-parity tests |
| `word_transition_rotor`, `make_rotor_from_angle` | `field/operators.py`, `generate/intent_ratifier.py` |
| `holonomy_encode`, `holonomy_similarity` | `vault/store.py`, `evals/lab/` |
| `N_COMPONENTS` (cl41) | `algebra/backend.py`, `algebra/cga.py` |

No exposed L0 symbol with zero downstream consumers.

**Pass 2 — semantic (judgment-required):**

ADR-0001's `versor_condition < 1e-6` invariant is the primary semantic
contract. Verified:

- **Measured per turn:** L0's `versor_condition()` is computed and
  folded into the deterministic trace payload (`core/cognition/trace.py:34,70`)
  on every turn.
- **Surfaced to operator:** displayed by `core chat` and `core` info
  commands (`core/cli.py:398,461,469`).
- **Gated at eval boundary:** evals refuse to count a turn as
  `versor_ok` if `versor_condition >= 1e-6` (`evals/cognition/runner.py:60`,
  `evals/run_cognition_eval.py:54`).
- **NOT enforced inline as exception:** a turn with `vc >= 1e-6` still
  completes; the violation is visible in trace + eval, not raised as
  an error. This matches CLAUDE.md's discipline ("Do not weaken this
  threshold to make tests pass. Fix the operator/construction
  boundary that violated it.") — violations are surfaced for fix,
  not catastrophically refused at runtime.

**Semantic mismatches flagged for human review:** none. The contract
is consistently consumed.

### Closure criteria scorecard

| Criterion | Status | Evidence |
|---|---|---|
| 1. Design artifact | ✅ | ADR-0001, ADR-0003, ADR-0004, ADR-0009 |
| 2. Code artifact | ✅ | `algebra/{backend,cga,cl41,holonomy,rotor,versor}.py` |
| 3. Live caller | ✅ | 38 distinct caller files outside `algebra/` and `tests/` |
| 4. Exercised by suite lane | ✅ | `core test --suite algebra` — 82/82 non-skipped pass; every L0 module covered |
| 5. Cross-layer consistency | ✅ | All exposed symbols consumed; `versor_condition` invariant measured + traced + gated |

**Verdict:** **CLOSED.**

### Cleanup performed

**None.** Audit found no dead, redundant, superseded, or orphaned code
at L0. Every module has live callers; every exposed symbol is consumed;
the suite lane exercises every module; the invariant is preserved
end-to-end.

### Findings / notes for downstream layers

- **L1 (Field substrate) auditor:** L0's `versor_condition` is consumed
  at L5 (trace) and at the eval boundary, but L1 itself does not appear
  to enforce the invariant — L1's propagation produces field states
  that may later violate the invariant, with measurement deferred to
  L5. Worth verifying that L1's propagation correctness is itself
  tested independently of L5's downstream measurement.
- **L2 (Vault) auditor:** `vault/store.py` is one of the heaviest
  consumers of L0 (cga_inner, embed_point, is_null, holonomy_encode).
  L2's closure depends on L0's exact-CGA-recall guarantees; the L2
  audit should verify the vault honors the exact-match discipline
  end-to-end, not just at the algebra layer.
- **L6 (Chat runtime) auditor:** ADR-0020 (Phase 5 / Rust Parity
  Sequencing) is cross-cutting; the 50 skipped tests in the algebra
  suite are Rust-parity tests skipped in a Python-only environment.
  Audit ADR-0020 wherever Rust integration is live (when it lands)
  rather than at any single layer.

### Audit method footnote

This entry follows the per-layer audit format established here:
ADRs in scope → modules in scope → caller traces → suite lane
exercise → cross-layer contract (mechanical + semantic) → closure
scorecard → cleanup → notes for downstream. Subsequent layers should
follow the same format so the registry is uniformly machine- and
human-scannable.

---

## L1 — Field substrate

**Audit date:** 2026-05-24
**Auditor:** Codex
**Verdict:** **PARTIAL**

### Scope-hypothesis correction (per audit step 0)

The scope's layering table cited ADR-0006 as the starting point. Reality:
L1 also depends on ADR-0002 / ADR-0012 for injection-gate and single-
normalization-site discipline, plus ADR-0024 / ADR-0025 as explicit
negative-placement ADRs that keep admissibility out of `field/propagate.py`.
`field/operators.py` is L1-shaped substrate code for `core pulse`, but it
is not on the current `ChatRuntime` / `CognitiveTurnPipeline` path.

### ADRs in scope for L1

Triaged from the broader field / propagation / injection / normalization /
energy keyword grep against `docs/decisions/`:

| ADR | Title | Status | Belongs at L1? |
|---|---|---|---|
| ADR-0002 | Ingest Layer Architecture | Accepted | Yes — original injection-boundary design; superseded by ADR-0012 but still relevant historical design |
| ADR-0006 | The Field Energy Operator (Hamiltonian Companion Field) | Implemented | Yes — defines `EnergyClass`, `EnergyProfile`, `FieldEnergyOperator`, `FieldState.energy`, and propagation recomputation |
| ADR-0012 | `core_ingest` Governance Layer | Accepted | Yes — preserves `ingest/gate.py` as the single normalization site |
| ADR-0024 | Inner-Loop Per-Rotor Admissibility | Accepted | Boundary-only for L1 — explicitly keeps admissibility upstream of `propagate_step()` and adds no normalization site |
| ADR-0025 | Rotor / Frame Admissibility | Accepted | Boundary-only for L1 — explicitly rejects `field/propagate.py` as the admissibility home |

Other ADRs surfaced by the grep but assigned to other layers (not audited
at L1): ADR-0007 (valence layer; orthogonal companion to energy, but not
part of this brief's L1 concern set), ADR-0013 (sensorium upstream of the
gate), ADR-0014 / ADR-0054 (L2 vault / learning), ADR-0022 / ADR-0023 /
ADR-0026 (L5 generation admissibility), ADR-0038 and later surface ADRs
(L6/L7 surface and teaching concerns).

### Modules in scope for L1

| Module | Lines | Live-import sites (outside own package, outside `tests/`) | Test-import sites |
|---|---|---|---|
| `ingest/gate.py` | 351 | 4 | 6 |
| `field/propagate.py` | 72 | 3 | 1 |
| `field/state.py` | 122 | 18 actual imports (raw grep also found one prose false positive) | 11 |
| `field/operators.py` | 289 | 3 (`core pulse` / benchmark path, not chat runtime) | 4 |
| `core/physics/energy.py` | 119 | 8 | 1 |

No module is imported by nothing outside its own package. No
unambiguously dead module was found. `field/operators.py` is live through
`scripts/run_pulse.py` and `benchmarks/run_benchmarks.py`, but not through
the current chat/cognition turn loop.

### Caller-trace evidence

Sample of live callers (full greps used the required shape, e.g.
`grep -rn "from field.propagate\|import field.propagate" --include="*.py" . | grep -v "^./field/" | grep -v "^./tests/"`):

- `chat/runtime.py:89` and `session/context.py:20` — live turn ingest
  calls `ingest.gate.inject()` (L6/session → L1).
- `generate/stream.py:19,628` — generation walk applies `propagate_step()`
  for each emitted token (L5 → L1).
- `generate/stream.py:18`, `core/cognition/pipeline.py:21`,
  `core/cognition/result.py:13`, `chat/runtime.py:80`, and
  `session/context.py:15` — live `FieldState` consumers.
- `language_packs/compiler.py:14,72` and `ingest/gate.py:33,292` —
  `FieldEnergyOperator` computes pack/injection energy.
- `vocab/manifold.py:36,74,227`, `generate/salience.py:44`, and
  `packs/common/runtime_rules.py:113,120` — energy profile/class consumers.
- `scripts/run_pulse.py:40-41` — `ManifoldState`,
  `GraphDiffusionOperator`, and `ConstraintCorrectionOperator` are live
  through the `core pulse` CLI path, not through `core chat`.

The live chat/cognition trace is:

`core chat` / `ChatRuntime` → `SessionContext.commit_ingest()` →
`ingest.gate.inject()` → `FieldState` → `generate.stream.generate()` →
`field.propagate.propagate_step()` → `GenerationResult.final_state` →
`CognitiveTurnPipeline` trace/result.

### Exercising suite lane

Two documented suite lanes are relevant:

| Suite lane | What it exercises | Verification |
|---|---|---|
| `core test --suite smoke` | Live chat/pipeline reach path plus architectural normalization doctrine (`tests/test_architectural_invariants.py`) | `python3 -m core.cli test --suite smoke -q` → **67 passed** |
| `core test --suite algebra` | ADR-0006 energy operator and `propagate_step()` energy recomputation independent of L5 trace measurement (`tests/test_energy.py`) | `python3 -m core.cli test --suite algebra -q` → **82 passed, 50 skipped** |

Additional evidence for the pulse-only field-operator path:
`python3 -m core.cli test --suite pulse -q` → **24 passed**.

### Cross-layer contract check

**Pass 1 — mechanical (consumer-exists per exposed symbol):**

| Exposed symbol | Consumer evidence |
|---|---|
| `inject` | `chat/runtime.py`, `session/context.py`, `core/cli.py`, `evals/lab/rotor_manifold_explorer.py` |
| `propagate_step` | `generate/stream.py`; lab probes in `evals/lab/` |
| `FieldState.F` | `generate/stream.py`, `session/context.py`, `chat/runtime.py`, `core/cognition/trace.py` via result path |
| `FieldState.node` / `FieldState.step` | `generate/stream.py`, `generate/salience.py`, `session/context.py`, tests in smoke/cognition lanes |
| `FieldState.holonomy` / `energy` / `valence` | carried by `session/context.py` and `generate/stream.py`; `energy` also consumed by `generate/salience.py` through vocab energy and by runtime surface helpers |
| `EnergyClass` / `EnergyProfile.energy_class` | `ingest/gate.py`, `packs/common/runtime_rules.py`, `core_ingest/compiler.py`, `core/physics/learning.py` |
| `EnergyClass.vault_candidate` | `core/physics/learning.py` (L2 follow-up; internal physics import, not a live L1 turn-loop consumer) |
| `FieldEnergyOperator.compute` | `ingest/gate.py`, `language_packs/compiler.py`, `field/propagate.py` |
| `aspect_weight` | Internal to `FieldEnergyOperator.compute`; direct tests only |
| `FieldState.advance` | Tests only (`tests/test_energy.py`) |
| `ManifoldState.with_fields` / `ManifoldState.advance` | Tests only (`tests/test_manifold_state.py`) |
| `GraphDiffusionOperator` / `ConstraintCorrectionOperator` | `scripts/run_pulse.py`, `benchmarks/run_benchmarks.py`, pulse/proof tests |

Mechanical gaps: `FieldState.advance`, `ManifoldState.with_fields`, and
`ManifoldState.advance` have no non-test consumer. They are small helpers
on public dataclasses, so they were not deleted as unambiguous dead code.

**Pass 2 — semantic (judgment-required):**

ADR-0012's single-normalization-site contract is mostly honored:

- `ingest/gate.py` is the only production call site for
  `normalize_to_versor()` in the L1 live path (`ingest/gate.py:237,342`).
- `field/propagate.py` has no normalization, unitization, projection,
  repair, monitor, or `versor_condition()` check. It calls only
  `versor_apply()` and recomputes energy (`field/propagate.py:47-71`).
- `tests/test_architectural_invariants.py` mechanically guards
  `normalize_to_versor()` call sites and forbids `unitize_versor()` in
  `field/`, `generate/`, and `vault/` except the existing
  `generate/stream.py` final-state closure exception.

ADR-0006 energy propagation is independently tested:

- `tests/test_energy.py` covers all energy classes, aspect weights,
  anchor-adjacent escalation, `requires_architect_review`, `FieldState`
  energy storage, and `propagate_step()` recomputation.
- This directly answers the L0 note: L1 propagation correctness is not
  tested only through L5's downstream `versor_condition` trace/eval
  measurement.

Cross-layer consistency gaps:

- **Gate threshold mismatch:** `ingest/gate.py` documents
  `versor_condition(F) < 1e-6` at the gate contract (`ingest/gate.py:22-24`)
  but raises only when `cond > 1e-5` (`ingest/gate.py:344-345`).
  `tests/test_architectural_invariants.py` also pins the weaker
  `< 1e-5` post-condition (`tests/test_architectural_invariants.py:339-367`).
  This conflicts mechanically with the project/L0 hard invariant
  `versor_condition(F) < 1e-6`.
- **ADR-0006 threshold drift:** ADR-0006 specifies E2 begins at raw
  `0.38`, while code classifies E2 at `raw >= 0.37`
  (`core/physics/energy.py:104-105`). Tests exercise the code behavior,
  not the exact ADR table boundary.

**Semantic mismatches flagged for human review:**

- `field/operators.py` contains a private `_unitize_f32()` and uses it in
  graph diffusion / correction (`field/operators.py:69-118,190,272`).
  This is not `field/propagate.py`, and it is reached through `core pulse`
  rather than the live chat/cognition turn loop. It is nevertheless
  field-substrate code that re-projects blended fields, so the operator
  should decide whether it is an allowed construction boundary, a
  pulse-only legacy path, or a normalization-site violation.
- `session/context.py` performs final-turn hemisphere correction and
  anchor pull with `unitize_versor()` (`session/context.py:207-246`).
  This is outside L1 and was not verdicted here, but it is a forward
  note for the L6 runtime auditor because it changes live session field
  state after generation.

### Closure criteria scorecard

| Criterion | Status | Evidence |
|---|---|---|
| 1. Design artifact | ✅ | ADR-0002, ADR-0006, ADR-0012; ADR-0024/0025 for negative placement at the propagation seam |
| 2. Code artifact | ✅ | `ingest/gate.py`, `field/propagate.py`, `field/state.py`, `core/physics/energy.py`; pulse-only `field/operators.py` |
| 3. Live caller | ✅ | Chat runtime/session/generation callers for gate/state/propagate/energy; pulse callers for graph operators |
| 4. Exercised by suite lane | ✅ | `smoke` walks live turn path; `algebra` independently tests ADR-0006 propagation; `pulse` covers graph operators |
| 5. Cross-layer consistency | ⚠️ | Gate/test threshold is `< 1e-5` while project/L0 invariant is `< 1e-6`; ADR-0006 E2 boundary drifts by 0.01; several dataclass helpers are test-only |

**Verdict:** **PARTIAL.**

### Cleanup performed

**None.** Audit found no module that was unambiguously dead, redundant,
superseded, or orphaned. Test-only helper methods and pulse-only field
operators are ambiguous rather than safe deletion candidates.

### Findings / notes for downstream layers

- **L2 (Vault) auditor:** ADR-0006 says vault recall re-activates a region
  to E2 transiently and lets it cool. L1 verifies the energy operator exists
  and is used at injection/propagation, but did not trace a live vault-recall
  path that updates energy on recall. Audit this in L2.
- **L5 (Cognition/generation) auditor:** `generate/stream.py` has an
  explicit final-state `unitize_versor()` closure exception. L1 did not
  verdict it because it belongs to generation, but it is adjacent to the
  normalization-site discipline.
- **L6 (Chat runtime) auditor:** `session/context.py` performs live
  post-generation field orientation and anchor pull, including
  `unitize_versor()`. Verify whether that runtime correction boundary is
  documented and suite-protected.
- **Future scope cleanup:** Decide whether `field/operators.py` is still a
  first-class pulse substrate, a benchmark-only substrate, or legacy code.
  It is live through `core pulse`, so this audit did not delete it.

---

## L2 — Vault

**Audit date:** 2026-05-24
**Auditor:** primary agent (Gemini)
**Verdict:** **PARTIAL**

### Scope-hypothesis correction (per audit step 0)

None. The scope's layering table correctly maps Layer L2 concerns (exact CGA recall, indexing, batching, promotion gate) to `vault/store.py` and `core/physics/learning.py`.

### ADRs in scope for L2

Triaged from Keyword grep (vault / recall / crystallization / promotion / settled / coherence-residual) against `docs/decisions/`:

| ADR | Title | Status | Belongs at L2? |
|---|---|---|---|
| ADR-0014 | `train/` Learning Loop | Accepted (Stub) | Yes — specifies learning constraints and the Supervised Seeding Epoch (which owns `VaultPromotionPolicy`) |
| ADR-0019 | Exact Vault Recall Acceleration | Accepted | Yes — defines Stages 1-3 of vectorised scan, norm-bucketing, and layered store |
| ADR-0054 | Vault Recall: Matrix-Cache Indexing + Batched API; Holdout Split Wired | Accepted | Yes — defines `VaultStore` matrix cache, batched recall API, and `--split holdout` |

Other ADRs/Scope files surfaced and assigned to adjacent layers:
- ADR-0006: Implemented. Belongs at L1, but specifies L2 integration points (vault recall transiently raising region to E2).
- ADR-0045: Accepted. Belongs at L6/Evals, but provides needle-in-a-haystack verification of exact recall.
- ADR-0055: Accepted. Belongs at L8, but catalogs Tier 1 (VaultStore) as session memory.

### Modules in scope for L2

| Module | Lines | Live-import sites (outside `vault/`, outside `tests/`) | Test-import sites |
|---|---|---|---|
| `vault/__init__.py` | 10 | (re-export shim) | — |
| `vault/store.py` | 301 | 1 (`session/context.py`) | 7 |
| `vault/decompose.py` | 224 | 1 (`chat/runtime.py`) | 1 |
| `core/physics/learning.py` | 33 | 0 (re-exported in `core/physics/__init__.py` but not imported downstream) | 0 |

`core/physics/learning.py` (`VaultPromotionPolicy` / `PromotionDecision`) is confirmed dormant with 0 live callers outside its own package and 0 test callers. Per the L2-specific cleanup instruction, it is retained as future-wiring debt instead of being deleted.

### Caller-trace evidence

Sample of live callers (grep: `grep -rn "from vault\|import vault" --include="*.py" | grep -v "^vault/" | grep -v "tests/"`):

- `session/context.py:25` — imports `VaultStore` for ephemeral session-level storage, storing input/output states and performing exact recall.
- `chat/runtime.py:94` — imports `default_decomposer` and `default_gate` to perform check gates before planning.
- `generate/stream.py:169` — invokes `vault.recall` during generation walk telemetry.
- `vault/decompose.py:124, 179` — invokes `vault.recall` during fallback grade-split decomposition and domain gate checks.

Every live caller traces back to the runtime entry through `core chat`, `core trace`, `core eval`, or the session/dialogue pipeline.

### Exercising suite lane

- `core test --suite algebra` — Exercises `tests/test_vault_recall.py`, `tests/test_vault_recall_vectorised.py`, and `tests/test_vault_recall_rust_parity.py`.
- `core test --suite full` — Exercises `tests/test_vault_store.py` and `tests/test_vault_recall_indexing_batch.py`.

**Verification:**
- `python3 -m core.cli test --suite algebra -q` → **82 passed, 50 skipped**
- `python3 -m pytest tests/test_vault_*.py -q` → **42 passed, 4 skipped**

### Cross-layer contract check

**Pass 1 — mechanical (consumer-exists per exposed symbol):**

| Exposed symbol | Consumer evidence |
|---|---|
| `VaultStore` | `session/context.py:25` |
| `VaultStore.store` | `session/context.py:149, 289, 300` |
| `VaultStore.recall` | `session/context.py:347`, `chat/runtime.py:1643`, `generate/stream.py:169`, `vault/decompose.py:124, 179` |
| `VaultStore.recall_batch` | None (exposed for batched querying, e.g. for offline evaluation or future batching) |
| `VaultStore.reproject` | `session/context.py:125` |
| `FieldDecomposer`, `default_decomposer` | `chat/runtime.py:94, 1649` |
| `UnknownDomainGate`, `default_gate` | `chat/runtime.py:94, 1645` |
| `VaultPromotionPolicy` | None (dormant) |

No exposed L2 symbol other than the batched API (`recall_batch`) and the dormant `VaultPromotionPolicy` lacks consumption. Note that `recall_batch` is fully tested and verified in `tests/test_vault_recall_indexing_batch.py` but not called in the main production path (which uses single-query `recall` at runtime).

**Pass 2 — semantic:**

We verified three load-bearing invariants:
1. **Exact-CGA-recall**: Checked `vault/store.py` and `algebra/backend.py`'s `vault_recall` and `vault_recall_batch`. There are no ANN, HNSW, cosine similarity, or other approximations on the recall path. It strictly uses vectorised exact scans via diagonal CGA inner-product metric, satisfying CLAUDE.md and ADR-0019/0054.
2. **Promotion-path liveness**: Confirmed that `VaultPromotionPolicy` (`core/physics/learning.py`) has 0 live/test callers. Flagged clearly as wiring debt. Verdict is **PARTIAL**.
3. **Re-thaw path**: Traced `vault.recall` callers to check if recall transiently raises the energy profile of a region to E2 (per ADR-0006 §"Integration Points"). Checked `vault/store.py` and its callers (`session/context.py`, `chat/runtime.py`). Verified that recall does **not** update or re-raise the energy class/profile of recalled entries. Flagged as `specified-not-verified-live`.

### Semantic mismatches flagged for human review

- **Re-thaw path integration**: The spec in ADR-0006 for vault recall to "transiently raise region to E2, then let it cool again" is not currently implemented. The system operates on exact recall returning data structures without modifying their companion field energy values or re-injecting them into the propagating field state. Flagged for review on whether this integration is needed or if the design has moved on.
- **Batched recall usage**: `VaultStore.recall_batch` is implemented and verified but has no caller in the main runtime path. Review if it should be wired to support batch processing of turn sequences.

### Closure criteria scorecard

| Criterion | Status | Evidence |
|---|---|---|
| 1. Design artifact | ✅ | ADR-0014, ADR-0019, ADR-0054 |
| 2. Code artifact | ✅ | `vault/store.py`, `vault/decompose.py`, `core/physics/learning.py` |
| 3. Live caller | ⚠️ PARTIAL | `session/context.py` and `chat/runtime.py` consume store/decompose; but `core/physics/learning.py` has no live caller |
| 4. Exercised by suite lane | ✅ | `algebra` suite lane exercises recall; `full` lane exercises store/indexing |
| 5. Cross-layer consistency | ⚠️ PARTIAL | Exchanged symbols match expectations, but `VaultPromotionPolicy` is dormant and the re-thaw path is not wired |

**Verdict:** **PARTIAL** (due to dormant promotion policy and unwired re-thaw path).

### Cleanup performed

**None.** Checked `vault/` files (`store.py`, `decompose.py`). Both modules have live callers and tests. `core/physics/learning.py` is dormant but retained as future-wiring debt per L2-specific cleanup rules.

### Findings / notes for downstream layers

- **L3 (Language packs) auditor**: Lexicons and identity packs specify aspect-class weights (e.g. yiqtol, qatal) which feed into field energy calculation (ADR-0006). Since the L2 vault recall does not currently implement the re-thaw path (raising energy back to E2), downstream language readback rules receive vaulted E0 crystalline concepts rather than transiently warmed E2 concepts. The L3 audit should look at whether language readback rules actually handle E0 vs E2 correctly at the surface.
- **L8 (Inter-session memory + contemplation) auditor**: ADR-0055 details Tier 1 session vault (`vault/store.py`) and its relation to Tier 3/4 memory. Contemplation and memory discovery will need to query the session vault. Ensure that the lack of re-thaw path and the dormant `VaultPromotionPolicy` do not block Tier 1 to Tier 3/4 promotion/crystallization logic when those layers are audited.

---

## L3 — Language packs

**Audit date:** 2026-05-24
**Auditor:** primary agent (Gemini)
**Verdict:** **PARTIAL**

### Scope-hypothesis correction (per audit step 0)

The scope's layering table cited `packs/` directories and ADRs ADR-0027..0047, ADR-0070..0073. Reality: L3 primary concerns also extend to ADR-0005 (language pack contract), ADR-0015 (linguistic manifolds & holonomy resonance), ADR-0091 / ADR-0093 (domain pack contract & implementation), ADR-0102 / ADR-0103 (Hebrew/Greek textual reasoning and fluency), and proposed-only/substrate-only ADR-0084 (definitional layer) and ADR-0087 (rhetorical style axis).

### ADRs in scope for L3

Triaged from Keyword grep against `docs/decisions/`:

| ADR | Title | Status | Belongs at L3? |
|---|---|---|---|
| ADR-0005 | Language Pack Contract | Accepted | Yes — defines `language_packs/` format, schemas, and loader contract |
| ADR-0015 | Language Packs as Compiled Linguistic Manifolds | Accepted | Yes — compiled linguistic manifolds and holonomy resonance |
| ADR-0027 | Identity Packs — Load-Bearing, Swappable, Ratified | Accepted | Yes — defines swappable, ratified identity packs |
| ADR-0028 | Identity Surface Wiring | Accepted | Boundary-only — L3 compiles/loads identity packs; realizer/composition is L6 |
| ADR-0029 | Safety Packs — Always-Loaded, Never-Replaceable Boundaries | Accepted | Yes — always-loaded safety boundaries |
| ADR-0030 | Depth-Language Hedge Wiring | Accepted | Boundary-only — L3 compiles safety/hedging lemmas; realizer is L6 |
| ADR-0033 | Ethics Packs — Swappable Domain Commitments | Accepted | Yes — swappable ethics domain commitments |
| ADR-0043 | Phase-2 pack measurements: claims -> numbers | Accepted | Yes — compiles claims to numbers/weights |
| ADR-0044 | Medical / clinical ethics pack | Accepted | Yes — worked-example domain pack |
| ADR-0051 | Trust-Boundary Hardening Pass | Accepted | Yes — defines `PackMutationProposal` validation and compiler trust rules |
| ADR-0068 | Register pack class | Accepted | Yes — specifies RegisterPack class and cataloging |
| ADR-0070 | Second ratified register pack: `terse_v1` | Accepted | Yes — register pack definition |
| ADR-0073 | Anchor lens: substrate-driven substantive variation | Accepted | Yes — anchor lens pack layout and structure |
| ADR-0073a | Anchor lens content phase | Accepted | Yes — anchor lens content |
| ADR-0073b | Anchor lens class + loader | Accepted | Yes — loader class for anchor lens |
| ADR-0073c | First non-trivial lenses + composer wiring | Accepted | Boundary-only — L3 compiles anchor lenses; composer is L6 |
| ADR-0073d | Anchor-lens telemetry, CLI, and tour demo | Accepted | Boundary-only — CLI/telemetry is L6 |
| ADR-0084 | Definitional Layer for Lexicon Packs | Proposed | Yes — optional definitional block for glosses and primitives |
| ADR-0087 | Rhetorical Style as Selection Axis | Proposed | Yes — rhetorical style pack loader and catalog |
| ADR-0091 | Domain Pack Contract v1 | Accepted | Yes — domain pack schema |
| ADR-0093 | Domain Pack Contract v1 Implementation | Accepted | Yes — compiler validation for domain packs |
| ADR-0102 | Hebrew-Greek Textual-Reasoning Reasoning-Capable Ratification | Accepted | Yes — multi-pack ratification for Greek/Hebrew |
| ADR-0103 | Fluency Lane Attachment for ADR-0102 | Accepted | Boundary-only — L3 compiles Greek/Hebrew fluency lanes; runner/gate is L6 |

### Modules in scope for L3

| Module | Lines | Live-import sites (outside own package, outside `tests/`) | Test-import sites | Status |
|---|---|---|---|---|
| `language_packs` | 74 | 31 | 53 | Live |
| `language_packs.__main__` | 157 | 0 | 0 | Live (CLI entrypoint) |
| `language_packs.compiler` | 620 | 7 | 31 | Live |
| `language_packs.definitions` | 312 | 0 | 4 | Dormant (ADR-0084 proposed) |
| `language_packs.domain_contract` | 217 | 3 | 1 | Live |
| `language_packs.en_seeder` | 276 | 1 | 0 | Live (Scripts/run_pulse) |
| `language_packs.evidence` | 64 | 0 | 1 | Dormant (ADR-0015 test only) |
| `language_packs.loader` | 387 | 5 | 3 | Live |
| `language_packs.numerics_loader` | 459 | 3 | 3 | Live |
| `language_packs.schema` | 202 | 6 | 4 | Live |
| `packs.anchor_lens` | 25 | 3 | 4 | Live |
| `packs.anchor_lens.loader` | 422 | 3 | 2 | Live |
| `packs.common.runtime_rules` | 122 | 8 | 0 | Live |
| `packs.common.validator` | 133 | 4 | 0 | Live |
| `packs.el.lift_rules` | 14 | 0 | 0 | Live (Dynamic) |
| `packs.el.readback_rules` | 9 | 0 | 0 | Live (Dynamic) |
| `packs.el.validators` | 19 | 0 | 0 | Live (Dynamic) |
| `packs.en.lift_rules` | 14 | 0 | 0 | Live (Dynamic) |
| `packs.en.readback_rules` | 9 | 0 | 0 | Live (Dynamic) |
| `packs.en.validators` | 19 | 0 | 0 | Live (Dynamic) |
| `packs.ethics` | 38 | 3 | 13 | Live |
| `packs.ethics.check` | 408 | 2 | 8 | Live |
| `packs.ethics.loader` | 409 | 1 | 5 | Live |
| `packs.grc.lift_rules` | 14 | 0 | 0 | Live (Dynamic) |
| `packs.grc.readback_rules` | 9 | 0 | 0 | Live (Dynamic) |
| `packs.grc.validators` | 19 | 0 | 0 | Live (Dynamic) |
| `packs.he.lift_rules` | 14 | 0 | 0 | Live (Dynamic) |
| `packs.he.readback_rules` | 9 | 0 | 0 | Live (Dynamic) |
| `packs.he.validators` | 19 | 0 | 0 | Live (Dynamic) |
| `packs.identity` | 14 | 3 | 4 | Live |
| `packs.identity.loader` | 494 | 3 | 4 | Live |
| `packs.primitives` | 33 | 0 | 3 | Dormant (ADR-0084 proposed) |
| `packs.primitives.loader` | 285 | 0 | 2 | Dormant (ADR-0084 proposed) |
| `packs.register` | 24 | 11 | 7 | Live |
| `packs.register.loader` | 608 | 11 | 7 | Live |
| `packs.rhetorical_style` | 36 | 0 | 3 | Dormant (ADR-0087 proposed) |
| `packs.rhetorical_style.loader` | 425 | 0 | 2 | Dormant (ADR-0087 proposed) |
| `packs.safety` | 39 | 3 | 13 | Live |
| `packs.safety.check` | 332 | 2 | 9 | Live |
| `packs.safety.loader` | 259 | 1 | 4 | Live |

*Note: Individual language-pack rule files (`packs/<lang>/lift_rules.py`, `readback_rules.py`, `validators.py`) are loaded dynamically by `packs/common/validator.py` and `core/cli.py` via `importlib.util` (registered under local dynamic paths), hence having 0 static Python import sites.*

### Caller-trace evidence

Exposed symbols of the layer are cleanly resolved through static imports across multiple layers:
- `language_packs.compiler.load_pack` is called by `chat/runtime.py` to mount the live vocabulary.
- `language_packs.compiler.load_mounted_packs` is used in `tests/test_oov_grounding_cache.py` and `tests/test_dialogue.py`.
- `language_packs.loader.lookup_unit` is consumed by the math parsers `generate/math_parser.py:120` and `generate/math_candidate_parser.py:660`.
- `language_packs.loader.lookup_cardinal` / `parse_compound_cardinal` are consumed in `generate/math_roundtrip.py:377,400`.
- `packs.common.validator.validate_pack_dir` is called by every pack-specific validation entrypoint (`packs/<lang>/validators.py`).

### Exercising suite lane

- `core test --suite packs` — Exercises pack loading, compilation, and ratification checks:
  ```bash
  python3 -m core.cli test --suite packs -q
  ```
  **Verification:** 13 passed, 0 skipped.
- `core test --suite smoke` — Exercises the end-to-end turn loop pipeline mounting default packs:
  ```bash
  python3 -m core.cli test --suite smoke -q
  ```
  **Verification:** 67 passed, 0 skipped.
- `verify_lane_shas.py` — Exercises all 7 pinned lanes:
  ```bash
  python3 scripts/verify_lane_shas.py
  ```
  **Verification:** lanes: 7/7 match pinned SHAs.

### Cross-layer contract check

**Pass 1 — mechanical (consumer-exists per exposed symbol):**

| Exposed symbol | Consumer evidence |
|---|---|
| `compile_entries_to_manifold` | `tests/test_epistemic_phase3_state_tagging.py:84`, `tests/test_holonomy_resonance.py:93` |
| `load_pack` | `chat/runtime.py`, `scripts/run_pulse.py:78`, `tests/test_proof_properties.py:24` |
| `load_mounted_packs` | `chat/runtime.py`, `tests/test_dialogue.py:11`, `tests/test_oov_grounding_cache.py:10` |
| `lookup_unit` | `generate/math_parser.py:121`, `generate/math_candidate_parser.py:661` |
| `lookup_cardinal` | `generate/math_roundtrip.py:377,402` |
| `validate_pack_dir` | `packs/he/validators.py:7`, `packs/grc/validators.py:7`, `packs/el/validators.py:7`, `packs/en/validators.py:7` |

**Pass 2 — semantic (three load-bearing invariants checked):**
1. **Pack manifest checksums match bytes on disk:** Verified in `language_packs/compiler.py` and `language_packs/__main__.py` that manifest checksums are computed using `hashlib.sha256(Path(...).read_bytes()).hexdigest()`. This ensures byte-level disk hashing instead of serialization of Python strings, fully respecting CLAUDE.md guidelines.
2. **Pack mutation is proposal-only:** Grep scans confirm that no production runtime code path in `language_packs/` or `packs/` writes to or mutates on-disk ratified packs. Changes are strictly proposed via `PackMutationProposal` / `TeachingChainProposal` and applied via offline reviewed CLI commands (e.g. `core teaching review --accept`).
3. **E0 vs E2 readback handling:** Checked `readback_from_intent` in `packs/common/runtime_rules.py`. While it receives `field_state.energy` and places its value into the `SurfaceRealization` metadata dataclass, it silently treats E0 identically to active E1/E2/E3 regions, returning the raw requested surface without modulating tense, framing, or hedging. This is a semantic inconsistency with ADR-0006/0007.

### Semantic mismatches flagged for human review

- **Dormant Readback rules:** The local `readback` logic (`packs/<lang>/readback_rules.py`) is completely unwired and has 0 callers outside validation checks (`packs/common/validator.py`). Surface generation is performed by `generate/realizer.py` instead of the local pack readback functions.
- **E0/E2 Readback modulation mismatch:** Readback rules do not implement the energy-based tense or hedging modulations specified in ADR-0006/0007. E0 (recalled vault crystal) is formatted the same as E2/E3 (warmed/active field regions) at the pack level.

### Closure criteria scorecard

| Criterion | Status | Evidence |
|---|---|---|
| 1. Design artifact | ✅ | ADR-0005, ADR-0015, ADR-0027, ADR-0029, ADR-0033, ADR-0051, ADR-0068, ADR-0070, ADR-0073, ADR-0091, ADR-0093, ADR-0102 |
| 2. Code artifact | ✅ | `language_packs/` (compiler, loader, schema), `packs/` (common rules, check loaders, register loader) |
| 3. Live caller | ⚠️ PARTIAL | Live turn loop mounts packs and resolves vocabulary, but local pack readback rules are dormant and unwired |
| 4. Exercised by suite lane | ✅ | `packs` exercises compilation/ratification; `smoke` exercises turn pipeline e2e |
| 5. Cross-layer consistency | ⚠️ PARTIAL | Local readback rules silently treat E0/E2/E3 identically, conflicting with ADR-0006/0007 modulation rules |

**Verdict:** **PARTIAL** (due to dormant readback rules and unwired E0 vs E2 surface modulation).

### Cleanup performed

**None.** Audit found no unambiguously dead code. All dormant modules are either CLI entrypoints, proposed-only substrates (ADR-0084 definitions, ADR-0087 rhetorical styles), or dynamically loaded pack boundary scripts (lift, readback, validators).

### Findings / notes for downstream layers

- **L4 (Recognition) auditor:** L3 domain/lexicon schemas provide the foundational vocabulary. Ensure recognition anti-unification uses the compiled domain namespaces from the VocabManifold.
- **L5 (Cognition pipeline) / L6 (Chat runtime) auditor:** Note that the local readback rules within packs are dormant. Downstream surface generation utilizes `generate/realizer.py`. If future work activates local pack-driven readback or requires energy-modulated surface forms, the readback rules must be wired in and updated to differentiate E0 (vault recall) vs E2 (transiently warmed) states.

---
