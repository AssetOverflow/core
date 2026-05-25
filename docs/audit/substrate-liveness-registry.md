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
| L4 — Recognition | ✅ Audited | **PARTIAL** | None — flagged connector/storage/integration as wiring debt | 2026-05-24 |
| L5 — Cognition pipeline | ✅ Audited | **PARTIAL** | `generate/render.py` deleted; `explain.py` / `provenance.py` flagged as wiring debt | 2026-05-24 |
| L6 — Chat runtime + surface composition | ✅ Audited | **PARTIAL** | None — no unambiguous dead chat code found | 2026-05-24 |
| L7 — Teaching loop | ✅ Audited | **PARTIAL** | None — no unambiguously dead modules found | 2026-05-24 |
| L8 — Inter-session memory + contemplation | ✅ Audited | **PARTIAL** | None — no unambiguously dead memory/contemplation modules found | 2026-05-24 |
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

## L4 — Recognition

**Audit date:** 2026-05-24
**Auditor:** Codex
**Verdict:** **PARTIAL**

### Scope-hypothesis correction (per audit step 0)

The scope's layering table cited ADR-0143 and ADR-0144 as starting
points. Reality: L4 also has a boundary dependency on ADR-0142, because
the recognition outcome and carrier emit the ADR-0142 epistemic-state
vocabulary. Dispatch trace has no standalone ADR; it is an ADR-0142
implementation-debt closure that landed in `chat/dispatch_trace.py` and
`chat/runtime.py`.

### ADRs in scope for L4

Triaged from recognition / anti-unification / epistemic / proposition
graph / feature-bundle / dispatch-trace keyword grep against
`docs/decisions/`:

| ADR | Title | Status | Belongs at L4? |
|---|---|---|---|
| ADR-0142 | Epistemic State Taxonomy — First-Class Vocabulary | Accepted | Boundary-only — defines states that recognition may emit and names dispatch trace as provenance debt |
| ADR-0143 | Teaching-Derived Structural Recognition via Multi-Resolution Anti-Unification | Accepted | Yes — defines `RecognitionOutcome`, `DerivedRecognizer`, `derive_recognizer()`, `recognize()`, refusal layers, and byte-identity guarantees |
| ADR-0144 | PropositionGraph — Epistemic Carrier and Recognition Integration Gate | Accepted | Yes — defines `EpistemicGraph`, connector, pipeline recognizer parameter, and opt-in recognition-grounded graph |

Related scope docs in this layer, not ADRs: `teaching-derived-recognition-scope.md`,
`proposition-graph-scope.md`, `recognizer-storage-scope.md`, and
`epistemic-state-taxonomy-scope.md`.

Other ADRs surfaced by the grep but assigned to other layers: ADR-0021
(general epistemic grade policy / teaching safety), ADR-0115 / ADR-0126 /
ADR-0132..0136 (math candidate/proposition graph corridor), ADR-0127 /
ADR-0128 (pack-typed units/numerics recognition for math parser), and
ADR-0131.G.3 / ADR-0131.G.3.1 (literal-recognition axes). These are not
the teaching-derived L4 recognition mechanism audited here.

### Modules in scope for L4

| Module | Lines | Live-import sites (outside own package, outside `tests/`) | Test-import sites | Status |
|---|---:|---:|---:|---|
| `recognition.__init__` | 11 | 0 | 0 | Re-export shim; no external direct consumers |
| `recognition.anti_unifier` | 628 | 1 (`core/cognition/pipeline.py`) | 3 | Mechanism coded; live only when a recognizer is explicitly supplied |
| `recognition.outcome` | 367 | 0 outside `recognition/`; 3 package-internal live consumers | 3 | Contract coded; live through `anti_unifier` / `carrier` / `connector` |
| `recognition.carrier` | 128 | 2 (`core/cognition/pipeline.py`, `core/cognition/result.py`) | 1 | Carrier coded; live result field exists |
| `recognition.connector` | 66 | 1 (`core/cognition/pipeline.py`) | 1 | Connector coded; live only under opt-in flag and supplied recognizer |
| `chat.dispatch_trace` | 13 | 1 outside `chat/` (`core/cognition/result.py`), plus `chat/runtime.py` live consumer | 1 | Live in `ChatRuntime` and surfaced through `CognitiveTurnResult` |

No unambiguously dead code was found. `recognition/connector.py` is
exactly the connector-style module the recognizer-storage scope warns
about: it is coded and imported by the pipeline, but its meaningful path
requires a supplied `DerivedRecognizer` and `recognition_grounded_graph=True`.
Flagged, not deleted.

### Caller-trace evidence

- `core/cognition/pipeline.py:38-40` imports `DerivedRecognizer`,
  `recognize`, `EpistemicGraph`, `EpistemicNode`, and
  `epistemic_node_to_graph_node`.
- `core/cognition/pipeline.py:117-127` accepts
  `recognizer: DerivedRecognizer | None = None` and stores it on
  `self._recognizer`.
- `core/cognition/pipeline.py:152-169` tokenizes once and calls
  `recognize(self._recognizer, raw_tokens)` only when a recognizer was
  attached. Admitted outcomes become a per-turn `EpistemicGraph`.
- `core/cognition/pipeline.py:201-211` invokes the connector only when
  `self.runtime.config.recognition_grounded_graph` is true and an
  `epistemic_graph` exists.
- `core/cognition/result.py:105-115` exposes `epistemic_graph` and
  `dispatch_trace` on `CognitiveTurnResult`.
- `core/config.py:245-250` defines `recognition_grounded_graph: bool = False`.
- `chat/runtime.py:46,840-1134,1656-1686,1901-1986` builds dispatch
  attempts and selected-source traces; `chat/runtime.py:415` exposes
  the trace on `ChatResponse`.
- All non-test `CognitiveTurnPipeline(...)` constructions found in
  `scripts/`, `benchmarks/`, and `evals/` omit the `recognizer` argument.
  `core chat` constructs `ChatRuntime`, not a `CognitiveTurnPipeline`
  with a recognizer.

The recognizer branch is therefore present in the cognitive spine but has
no normal runtime constructor that supplies a derived recognizer. The
mechanism is coded; integration into normal operation is absent.

### Exercising suite lane

- `core test --suite smoke` exercises the default cognitive pipeline and
  verifies pre-existing behavior with `recognizer=None`.
  ```bash
  python3 -m core.cli test --suite smoke -q
  ```
  **Verification:** 67 passed.
- Direct L4 tests exercise the recognition mechanism, carrier, connector,
  and dispatch trace:
  ```bash
  python3 -m pytest tests/test_epistemic_carrier.py tests/test_recognition_phase1.py tests/test_recognition_phase2.py tests/test_dispatch_trace.py -q
  ```
  **Verification:** 28 passed.
- `scripts/verify_lane_shas.py` still matches all pinned evidence lanes:
  ```bash
  python3 scripts/verify_lane_shas.py
  ```
  **Verification:** lanes: 7/7 match pinned SHAs.

**Lane gap:** the direct L4 tests are not named in any curated
`core test --suite {smoke|cognition|teaching|packs|runtime|algebra}`
alias except the broad `full` alias. `smoke` covers the default
`recognizer=None` path, but no documented curated lane exercises
`CognitiveTurnPipeline(..., recognizer=...)`.

### Cross-layer contract check

**Pass 1 — mechanical (consumer-exists per exposed symbol):**

| Exposed symbol / field | Consumer evidence |
|---|---|
| `derive_recognizer()` | Direct tests only (`tests/test_recognition_phase1.py`, `tests/test_recognition_phase2.py`, `tests/test_epistemic_carrier.py`); no live constructor derives a recognizer |
| `DerivedRecognizer` | Type-consumed by `core/cognition/pipeline.py:121`; no non-test caller passes an instance |
| `recognize()` | `core/cognition/pipeline.py:160`, but only when `_recognizer is not None`; direct tests call it heavily |
| `RecognitionOutcome` / `FeatureBundle` / typed refusals | Consumed by `recognition.anti_unifier`, `recognition.carrier`, `recognition.connector`, and direct tests |
| `EpistemicGraph` | Produced by `core/cognition/pipeline.py:166-169`, stored on `CognitiveTurnResult.epistemic_graph`; no downstream live consumer reads it yet |
| `EpistemicNode.with_transition()` | Direct tests only; no verifier/vault transition caller yet (ADR-0144 explicitly defers verifier/vault transitions) |
| `epistemic_node_to_graph_node()` | `core/cognition/pipeline.py:207-210` under opt-in flag; direct connector tests |
| `RuntimeConfig.recognition_grounded_graph` | Read by `core/cognition/pipeline.py:206`; default false |
| `DispatchTrace` / `DispatchAttempt` | Built in `chat/runtime.py`, surfaced on `ChatResponse.dispatch_trace` and `CognitiveTurnResult.dispatch_trace`, asserted by `tests/test_dispatch_trace.py` |

**Mechanical closure gaps:**

- No non-test caller derives, stores, loads, or passes a
  `DerivedRecognizer` into `CognitiveTurnPipeline`.
- The ADR-0144 refusal path is incomplete in the pipeline: refused
  recognition produces no carrier, but `_rec_outcome.refusal_reason` is
  not copied into `CognitiveTurnResult.refusal_reason`; that field is
  populated from `ChatResponse.refusal_reason` instead.
- `EpistemicGraph` is exposed on the turn result but has no live
  downstream consumer beyond tests.

**Pass 2 — semantic (three L4 invariants checked):**

1. **Recognizer integration into live turn loop:** Confirmed partial.
   The pipeline accepts a recognizer and can call it, but every normal
   constructor found in scripts, benchmarks, evals, and tests outside
   L4-specific direct fixtures omits `recognizer=...`. No main/runtime
   path constructs or persists one. L4 is therefore at most **PARTIAL**.
2. **Anti-unifier determinism:** Mostly satisfied by construction and
   tests. `DerivedRecognizer.to_json()` sorts keys with compact JSON;
   `FeatureBundle.from_mapping()` sorts features; allowed verb phrases
   are sorted before serialization and matching; ignored prefix tokens
   are sorted. `teaching_set_id` is SHA-256 of
   `json.dumps(sorted(token_sequences), ensure_ascii=False,
   separators=(",", ":"))`, so example order does not affect the id.
   Caveat: the hash covers token sequences only, not the full feature
   bundles. Same tokens with different taught feature values would share
   a `teaching_set_id`; this is a semantic identity mismatch against the
   phrase "same teaching examples" if "example" includes labels/bundles.
3. **Vocabulary source:** Recognition does **not** consume L3's compiled
   `VocabManifold`, domain namespaces, or pack-resident lexicon. Grep
   across `recognition/` found no `VocabManifold`, `language_packs`,
   `load_pack`, `compiled`, `lexicon`, or `vocab` references except a
   prose comment in `outcome.py`. `derive_recognizer()` operates on raw
   token sequences plus taught `FeatureBundle` evidence.

### Semantic mismatches flagged for human review

- **Teaching-set hash scope:** ADR-0143 says `teaching_set_id` is a hash
  of the teaching set. The implementation hashes only sorted token
  sequences, not the feature bundles. If two reviewed teaching sets share
  tokens but differ in feature labels, values, or evidence, they collide
  at the recognizer identity layer even though the derived recognizer may
  differ.
- **L3 vocabulary bypass:** Per L3's forward note, L4 does not use the
  compiled vocabulary/domain namespaces from `VocabManifold`. This may be
  acceptable for the token-level spike, but it means L4 recognition is
  not yet grounded in L3's pack-resident domain schema.
- **Recognition refusal observability:** ADR-0144 describes typed
  recognition refusal materialization on the turn result. The current
  pipeline discards `_rec_outcome.refusal_reason` on refused recognition
  and leaves `CognitiveTurnResult.refusal_reason` to the generation/chat
  path.

### Closure criteria scorecard

| Criterion | Status | Evidence |
|---|---|---|
| 1. Design artifact | ✅ | ADR-0142 boundary vocabulary, ADR-0143, ADR-0144 |
| 2. Code artifact | ✅ | `recognition/{anti_unifier,outcome,carrier,connector}.py`, `chat/dispatch_trace.py`, pipeline/result/config fields |
| 3. Live caller | ⚠️ PARTIAL | Pipeline imports and conditionally calls recognizer, but no normal runtime constructor supplies one; dispatch trace is live |
| 4. Exercised by suite lane | ⚠️ PARTIAL | `smoke` exercises default no-recognizer path; direct L4 tests pass but are not in a curated lane except `full` |
| 5. Cross-layer consistency | ⚠️ PARTIAL | Carrier/result fields exist; recognizer storage/loading absent; refusal reason not propagated; L3 vocabulary not consumed |

**Verdict:** **PARTIAL** (mechanism and carrier are coded; dispatch trace
is live; derived recognizer storage/construction and normal turn-loop
integration are absent).

### Cleanup performed

**None.** No unambiguously dead, redundant, superseded, or orphaned code
was found. Connector-style modules are flagged as wiring debt rather than
deleted because the recognizer-storage scope explicitly leaves these
awaiting integration/storage ADRs.

### Findings / notes for downstream layers

- **L5 (Cognition pipeline) auditor:** The pipeline has a recognition
  branch, but it is cold unless a caller supplies `DerivedRecognizer`.
  Verify whether L5's current verdict should treat this as an optional
  observability branch or an unclosed live cognitive step. Also check the
  recognition-refusal drop: `_rec_outcome.refusal_reason` is not folded
  into the turn result.
- **L6 (Chat runtime) auditor:** Dispatch trace is live in `ChatRuntime`
  and surfaced through `ChatResponse` / `CognitiveTurnResult`, but it is
  observability only and not folded into trace hash. Confirm whether L6
  contracts require trace-hash participation or only operator-visible
  provenance.
- **L7 (Teaching loop) auditor:** Recognition refusals are intended to be
  teaching signals, but the live pipeline currently discards typed
  recognizer refusals. If teaching-derived recognition is to feed review,
  L7 needs a concrete consumer or the L4/L7 boundary remains open.
- **Recognizer-storage ADR:** This audit confirms the storage scope's
  core finding: `DerivedRecognizer` is serializable and accepted by the
  pipeline, but nothing in main constructs, persists, loads, shares, or
  reactivates one across sessions.

---

## L5 — Cognition pipeline

**Audit date:** 2026-05-24
**Auditor:** primary agent (Gemini)
**Verdict:** **PARTIAL**

### Scope-hypothesis correction (per audit step 0)

The scope's layering table cited `core/cognition/` and `generate/` concerns: intent classification, ratification, articulation target, deterministic realizer, proposition graph planner, cold-start grounding sources. Reality: the concerns are split across two packages: `core/cognition/` (orchestration, result, trace, surface resolution) and `generate/` (intent classification, intent ratification, realizer, templates, graph planner, admissibility, attention, salience, and stream walk). The scope ranges omitted key admissibility and classification ADRs. `generate/render.py` was found to be completely dormant (0 imports, 0 references, 0 tests) and was deleted during cleanup. `core/cognition/explain.py` and `core/cognition/provenance.py` were found to have 0 live production callers, and are flagged as dormant/partially live wiring debt.

### ADRs in scope for L5

| ADR | Title | Status | Belongs at L5? |
|---|---|---|---|
| ADR-0022 | Forward Semantic Control | Accepted | Yes — `classify_intent` and `ratify_intent` at the pipeline step |
| ADR-0023 | Forward Semantic Control Proof | Accepted | Yes — verifies ratification execution and rates |
| ADR-0024 | Inner-Loop Per-Rotor Admissibility | Accepted | Yes — defines admissibility regions, `check_transition`, `InnerLoopExhaustion` |
| ADR-0025 | Rotor / Frame Admissibility | Accepted | Yes — rotor effect on current field against frame cone |
| ADR-0026 | Ranked Admissibility with Margin | Accepted | Yes — margin-mode checks |
| ADR-0046 | PropositionGraph as Forward Admissibility Constraint | Accepted | Yes — proposition graph planning constraints |
| ADR-0047 | Wire the Forward Graph Constraint into the Chat Hot Path | Accepted | Yes — wires forward constraint |
| ADR-0048 | Pack-Grounded Surface for Cold-Start DEFINITION / RECALL | Accepted | Yes |
| ADR-0049 | Intent Classifier Head-Noun Subject Extraction | Accepted | Yes |
| ADR-0050 | Pack-Grounded Surface for Cold-Start COMPARISON | Accepted | Yes |
| ADR-0051 | Trust-Boundary Hardening Pass | Accepted | Yes |
| ADR-0052 | Teaching-Grounded Surface for Cold-Start CAUSE / VERIFICATION | Accepted | Yes |
| ADR-0053 | Cognition Lane Closure | Accepted | Yes |
| ADR-0058 | `forward_graph_constraint`: Engaged but Inert | Accepted | Yes |
| ADR-0061 | PROCEDURE Intent Routes to Pack-Grounded Surface | Accepted | Yes |
| ADR-0069 | Realizer register parameter | Accepted | Yes |
| ADR-0075 | Realizer slot-type guard | Accepted | Yes |
| ADR-0142 | Epistemic State Taxonomy | Accepted | Boundary-only — L5/L9 boundary |
| ADR-0143 | Recognition Spike | Accepted | Boundary-only — L4 output is L5 input |
| ADR-0144 | PropositionGraph: Epistemic Carrier & Gate | Accepted | Yes — carrier integration with L4/L9 |

### Modules in scope for L5

| Module | Lines | Live-import sites (outside own package, outside `tests/`) | Test-import sites | Status |
|---|---|---|---|---|
| `core/cognition/pipeline.py` | 727 | 3 (`chat/runtime.py`, `core/cli.py`, `evals/run_cognition_eval.py`) | 12 | Live |
| `core/cognition/result.py` | 139 | 3 | 11 | Live |
| `core/cognition/trace.py` | 153 | 3 | 11 | Live |
| `core/cognition/surface_resolution.py` | 108 | 1 (`pipeline.py`) | 3 | Live |
| `core/cognition/explain.py` | 124 | 0 (only re-exported in `core/cognition/__init__.py`) | 1 | Dormant (no live production callers) |
| `core/cognition/provenance.py` | 101 | 0 (used by `evals/provenance/runner.py`) | 1 | Partially live (evals/verification only) |
| `generate/intent.py` | 662 | 8 | 15 | Live |
| `generate/intent_bridge.py` | 350 | 2 | 2 | Live |
| `generate/intent_ratifier.py` | 241 | 1 | 4 | Live |
| `generate/realizer.py` | 272 | 3 | 7 | Live |
| `generate/templates.py` | 232 | 3 | 3 | Live |
| `generate/graph_planner.py` | 300 | 4 | 7 | Live |
| `generate/admissibility.py` | 668 | 2 | 11 | Live |
| `generate/graph_constraint.py` | 159 | 2 | 2 | Live |
| `generate/stream.py` | 648 | 2 | 12 | Live |
| `generate/proposition.py` | 417 | 1 | 2 | Live |
| `generate/salience.py` | 62 | 2 | 2 | Live |
| `generate/attention.py` | 43 | 1 | 1 | Live |
| `generate/bridge_trace.py` | 292 | 1 | 1 | Live |
| `generate/render.py` | — | — | — | **DELETED — 0 imports, 0 references, 0 tests** |

### Caller-trace evidence

The live chat/cognition trace is:
`ChatRuntime.chat()` → `CognitiveTurnPipeline.run()` → `_ratify_intent()` → `graph_from_intent()` → `plan_articulation()` → `realize_semantic()` → delegated walk → `generate()` → `resolve_surface()` → `compute_trace_hash()`.

### Exercising suite lane

- `core test --suite cognition` — **120 passed, 1 skipped**.
- `core test --suite smoke` — **67 passed**.
- `core eval cognition` — **13/13 passed** (100% intent_accuracy, surface_groundedness, versor_closure_rate).
- `scripts/verify_lane_shas.py` — **7/7 lanes match pinned SHAs**.

### Cross-layer contract check

**Pass 1 — mechanical (consumer-exists per exposed symbol):**

| Exposed symbol | Consumer evidence |
|---|---|
| `CognitiveTurnPipeline` | `chat/runtime.py:27`, `core/cli.py:446`, `evals/run_cognition_eval.py` |
| `CognitiveTurnResult` | `chat/runtime.py:27`, `core/cognition/pipeline.py`, tests |
| `resolve_surface` | `core/cognition/pipeline.py:23` |
| `compute_trace_hash` | `core/cognition/pipeline.py:24` |
| `classify_compound_intent` | `core/cognition/pipeline.py:25` |
| `ratify_intent` | `core/cognition/pipeline.py:30` |
| `graph_from_intent` | `core/cognition/pipeline.py:34` |
| `realize_semantic` | `core/cognition/pipeline.py:41` |
| `generate` | `chat/runtime.py:88` |
| `build_graph_constraint` | `chat/runtime.py:88` |

**Pass 2 — semantic (four invariants checked):**

1. **Surface contract.** Verified `resolve_surface` in `core/cognition/surface_resolution.py` preserves the user-facing `surface` vs raw walk telemetry `walk_surface` split. User-facing `surface` is the semantic realizer output folded with deterministic walk/compose suffixes; raw manifold-walk telemetry goes strictly to `walk_surface`.
2. **Normalization-site discipline.** `generate/stream.py` is a FORBIDDEN normalization site except for the documented final-state closure: `_close_final_state(state)` calls `unitize_versor(state.F)` when sealing the final state at the generation boundary. No other normalization has crept into `generate/`. `generate/admissibility.py` explicitly documents that its composed blades are *not* unitized to honor the CLAUDE.md discipline.
3. **`refusal_reason` materialization.** Wiring exists: `ChatResponse` has the field, `CognitiveTurnPipeline` reads it, and it is folded into `trace_hash` when non-empty. **However:** `InnerLoopExhaustion` exceptions raised during generation are NOT caught in `ChatRuntime.chat()`, so `refusal_reason` is never populated with the machine-readable `RefusalReason` taxonomy during live runs (it propagates as an unhandled exception).
4. **RatificationOutcome PASSTHROUGH split.** Confirmed sub-values (`PASSTHROUGH_NO_FIELD`, `PASSTHROUGH_NO_VOCAB`, `PASSTHROUGH_NO_VERSOR`) collapse to `"passthrough"` before trace hashing in `core/cognition/pipeline.py`. Byte-identity of existing trace hashes preserved exactly.

### Semantic mismatches flagged for human review

- **`InnerLoopExhaustion` propagation gap.** Inner-loop refusal exceptions are never caught in main `ChatRuntime.chat()` execution, meaning refusal reasons for admissibility exhaustions are never materialized to `ChatResponse.refusal_reason` during live execution. They cause unhandled exceptions unless caught externally.
- **`explain.py` and `provenance.py` dormancy.** `core/cognition/explain.py` has 0 live production callers outside its test file. `core/cognition/provenance.py` is only used in tests and `evals/provenance/runner.py`. Review whether these should be fully wired to the live REPL or are reserved for offline audit tools.

### Closure criteria scorecard

| Criterion | Status | Evidence |
|---|---|---|
| 1. Design artifact | ✅ | ADR-0022..0026, ADR-0046..0053, ADR-0142..0144 |
| 2. Code artifact | ✅ | `core/cognition/`, `generate/` (after deleting unused `render.py`) |
| 3. Live caller | ⚠️ PARTIAL | Orchestration pipeline, ratification, realizer, stream walk live; `explain.py` dormant; inner-loop refusal exceptions unwired |
| 4. Exercised by suite lane | ✅ | `cognition` + `smoke` pass; `eval cognition` 100% |
| 5. Cross-layer consistency | ⚠️ PARTIAL | Hashing + surface contracts consistent; `refusal_reason` propagation from generator unwired |

**Verdict:** **PARTIAL** (dormant `explain.py`, partial `provenance.py`, unwired `InnerLoopExhaustion` exception materialization).

### Cleanup performed

- **`generate/render.py` deleted** — completely unused module (0 production imports, 0 test imports, 0 references). Tests + SHAs confirmed intact post-deletion. First cleanup-as-found of the audit per [[feedback-cleanup-as-you-find]].

### Findings / notes for downstream layers

- **L6 (Chat runtime) auditor:** Wire the `InnerLoopExhaustion` exceptions caught in the turn loop to populate the `ChatResponse.refusal_reason` field so machine-readable refusal codes are folded into the trace hash and result objects.
- **L7 (Teaching loop) / L8 (Memory) auditor:** `core/cognition/explain.py` is dormant. If teaching correction review requires a natural-language explanation of what was decoded on a turn, wire `explain()` to the REPL or CLI proposal commands.
- **L9 (Epistemic state) auditor:** ADR-0142 implementation debt #3 (wiring refusal reason) is the primary blocker for full epistemic refusal tracking. Fix this boundary in L6/L9.

---

## L6 — Chat runtime + surface composition

**Audit date:** 2026-05-24
**Auditor:** Codex
**Verdict:** **PARTIAL**

### Scope-hypothesis correction (per audit step 0)

The scope's L6 range `ADR-0058..0099` is directionally right but too
wide. Reality: the live L6 surface is centered on `chat/runtime.py` and
the `chat/` composer/telemetry helpers, with several boundary ADRs
already audited at L5 (`generate/realizer.py`, `core/cognition/*`) or
belonging downstream to L7/L8/L9. The L1 forward note on
`session/context.py` is confirmed relevant to L6 because
`ChatRuntime.chat()` finalizes every turn through `SessionContext`.

### ADRs in scope for L6

Triaged from chat runtime / surface / grounding dispatch / telemetry /
verdict / register / anchor-lens / cross-pack keyword grep against
`docs/decisions/` and `docs/adr/`:

| ADR | Title | Status | Belongs at L6? |
|---|---|---|---|
| ADR-0035 | Turn-Loop Verdict Surfacing | Accepted | Yes — SafetyCheck/EthicsCheck invocation in `ChatRuntime` |
| ADR-0036 | Safety-Only Typed Refusal Policy | Accepted | Yes — fail-closed runtime surface replacement |
| ADR-0037 | Per-Predicate Ethics Refusal Opt-In | Accepted | Yes — ethics refusal trigger policy |
| ADR-0038 | Hedge Injection as Runtime Affordance | Accepted | Yes — runtime surface transformation |
| ADR-0039 | Audit Completeness / `TurnVerdicts` Bundle | Accepted | Yes — response/event verdict bundle and stub-path events |
| ADR-0040 | Structured-Logging Sink | Accepted | Yes — `TurnEventSink` fan-out target |
| ADR-0041 | CLI Verdicts and Fan-Out | Accepted | Yes — `core chat --show-verdicts` and sink surface |
| ADR-0048 | Pack-Grounded Surface for Cold-Start DEFINITION / RECALL | Accepted | Boundary-shared L5/L6 — implemented by chat pack composer |
| ADR-0050 | Pack-Grounded Surface for Cold-Start COMPARISON | Accepted | Boundary-shared L5/L6 |
| ADR-0052 | Teaching-Grounded Surface for Cold-Start CAUSE / VERIFICATION | Accepted | Boundary-shared L6/L7 reader side |
| ADR-0058 | `forward_graph_constraint`: Engaged but Inert | Accepted | Boundary-only — L5 constraint, L6 carries telemetry/use |
| ADR-0059 | Correction-Pass Telemetry Emission | Accepted | Boundary-only — L6 emits, L7 owns correction semantics |
| ADR-0060 | CORRECTION Acknowledgement Carries Topic Lemma | Accepted | Boundary-only — L6 surface path, L7 correction loop |
| ADR-0061 | PROCEDURE Intent Routes to Pack-Grounded Surface | Accepted | Yes |
| ADR-0062 | Composed Teaching-Grounded Surface | Accepted | Yes — composed reader/composer path |
| ADR-0063 | Cross-pack Surface Resolver | Accepted | Yes — reader-side cross-pack composition |
| ADR-0064 | Cross-pack Teaching Chains | Accepted | Yes — reader-side corpus resolution |
| ADR-0065 | OOV Gradient + Relations v2 | Accepted | Yes — OOV invitation surface and discovery signal |
| ADR-0066 | Turn-Level Composition | Accepted | Yes — anaphora, narrative/example composers, thread context |
| ADR-0067 | Cross-pack Teaching Chains | Accepted | Yes — cross-pack fall-through and narrative/example aggregation |
| ADR-0068 | Register Pack Class | Accepted | Boundary-shared L3/L6 — L6 loads and applies pack |
| ADR-0069 | Realizer Register Parameter | Accepted | Yes — trace-invariant register threading |
| ADR-0070 | `terse_v1` Register Pack | Accepted | Boundary-shared L3/L6 |
| ADR-0071 | Seeded Surface Variation | Accepted | Yes — post-composition decoration |
| ADR-0072 | Register Telemetry + Operator Surface | Accepted | Yes |
| ADR-0073 | Anchor Lens Substrate | Accepted | Boundary-shared L3/L6 |
| ADR-0073b | Anchor Lens Class + Loader | Accepted | Boundary-shared L3/L6 |
| ADR-0073c | Anchor Lens Composer Wiring | Accepted | Yes |
| ADR-0073d | Anchor-Lens Telemetry, CLI, Tour | Accepted | Yes |
| ADR-0075 | Realizer Slot-Type Guard | Accepted | Yes — final surface guard in runtime |
| ADR-0076 | Confirmation-Tag Normalization | Accepted | Yes — surface normalization contract |
| ADR-0077 | Substantive Register Knobs | Ratified | Yes — substantive post-composer transform |
| ADR-0078 | Composer/Graph Atom Equivalence Telemetry | Ratified | Yes — observability in `TurnEvent` / `ChatResponse` |
| ADR-0083 | Transitive Chain Surface | Accepted | Yes — multi-hop teaching reader surface |
| ADR-0087 | Rhetorical Style Axis | Proposed | Boundary-only — design signal; no required runtime closure yet |
| ADR-0088 | Realizer-Grounded Authority | Proposed | Boundary-only — L5/L6 surface authority handoff |
| ADR-0089 | Compound-Intent Pipeline Dispatch | Proposed | Boundary-only — C1 telemetry live, C2 not required yet |
| ADR-0090 | Unified Ingest + Batched Recall | Proposed | Yes — flag-gated L6 turn-loop path |
| ADR-0096 | Fabrication-Control Eval Lane | Accepted | Boundary-only — verifies L6/L9 honesty surface |
| ADR-0098 | Demo Composition Contract | Accepted | Boundary-only — demo composition, not core turn-loop closure |
| ADR-0099 | Public Showcase Demo | Accepted | Boundary-only — demo surface, not core turn-loop closure |
| ADR-0144 | PropositionGraph Epistemic Carrier & Gate | Accepted | Boundary-only — L4/L5 carrier; L6 dispatch trace remains observability-only |

### Modules in scope for L6

| Module | Lines | Live-import sites (outside module, outside `tests/`) | Test-import sites | Status |
|---|---|---|---|---|
| `chat/runtime.py` | 2217 | 68 | 82 | Live |
| `chat/pack_grounding.py` | 1094 | 5 | 17 | Live |
| `chat/teaching_grounding.py` | 638 | 15 | 13 | Live reader-side surface path; L7 owns mutation/review semantics |
| `chat/cross_pack_grounding.py` | 287 | 6 | 3 | Live reader-side cross-pack path |
| `chat/pack_resolver.py` | 245 | 16 | 19 | Live |
| `chat/pack_surface_candidate.py` | 82 | 1 | 0 | Live through `pack_grounding.py` |
| `chat/register_substantive.py` | 244 | 1 | 1 | Live |
| `chat/register_variation.py` | 184 | 2 | 1 | Live |
| `chat/example_surface.py` | 131 | 1 | 2 | Live |
| `chat/narrative_surface.py` | 184 | 1 | 2 | Live |
| `chat/partial_surface.py` | 115 | 1 | 1 | Live |
| `chat/oov_surface.py` | 137 | 1 | 1 | Live |
| `chat/anaphora.py` | 94 | 1 | 1 | Live |
| `chat/thread_context.py` | 181 | 2 | 2 | Live |
| `chat/articulation_telemetry.py` | 198 | 2 | 2 | Live |
| `chat/telemetry.py` | 411 | 4 | 7 | Live |
| `chat/refusal.py` | 177 | 2 | 4 | Live |
| `chat/atom_equivalence.py` | 80 | 1 | 1 | Live |
| `chat/dispatch_trace.py` | 13 | 2 | 1 | Live observability |
| `chat/verdicts.py` | 49 | 1 | 3 | Live |
| `chat/__main__.py` | 39 | 0 | 0 | CLI module entrypoint (`python -m chat`) |
| `session/context.py` | 347 | 1 (`chat/runtime.py`) | 5 | Live L6 session-finalization boundary |

No unambiguously dead L6 module was found. `chat/__init__.py` is a
3-line re-export shim and is not counted as a liveness concern.

### Caller-trace evidence

The live L6 trace is:
`core chat` / `core trace` → `ChatRuntime.chat()` → `SessionContext`
probe/commit/finalize → `_maybe_pack_grounded_surface()` dispatch →
pack/teaching/cross-pack/partial/OOV composers → refusal/hedge/guard →
substantive register → seeded register decoration → anchor-lens
telemetry extraction → `TurnEvent` / `ChatResponse` / telemetry sinks →
`CognitiveTurnPipeline.run()` consumes the response surface and
observability fields.

Representative live callers:

- `core/cli.py:218-256` — REPL creates `ChatRuntime`, prints
  `ChatResponse.surface`, optionally prints verdict summary.
- `core/cli.py:424-435` — trace command runs one chat turn and reports
  surface, walk, articulation, and field telemetry.
- `core/cognition/pipeline.py` — wraps `ChatRuntime.chat()` and carries
  `dispatch_trace`, register surfaces, refusal fields, and trace hash
  material into `CognitiveTurnResult`.
- `evals/*` and `benchmarks/*` — use `ChatRuntime` for audit tours,
  demo composition, register diagnostics, cost, and replay comparisons.
- `chat/runtime.py:848-1135` — dispatches pack, teaching, cross-pack,
  partial, and OOV surface candidates.
- `chat/runtime.py:1371-1619` and `1621-2151` — stub and main paths
  both build verdicts, enforce safety refusal surface replacement,
  run register/anchor-lens/guard seams, append `TurnEvent`, and return
  `ChatResponse`.

### Exercising suite lane

- `core test --suite smoke -q` — **67 passed**.
- `core test --suite cognition -q` — **120 passed, 1 skipped**.
- `core test --suite runtime -q` — **19 passed**.
- `scripts/verify_lane_shas.py` — **7/7 lanes match pinned SHAs**.

The runtime suite exists in `core/cli.py` and covers
`tests/test_chat_runtime.py`, `tests/test_achat.py`, and
`tests/test_runtime_config.py`. L6-specific tests also appear in the
smoke/cognition lanes: dispatch trace, turn-loop verdicts, register,
anchor lens, surface composition, cross-pack grounding, partial/OOV
surface, and telemetry fan-out.

### Cross-layer contract check

**Pass 1 — mechanical (consumer-exists per exposed symbol):**

| Exposed symbol / field | Consumer evidence |
|---|---|
| `ChatRuntime.chat()` | `core/cli.py`, `core/cognition/pipeline.py`, evals, benchmarks, tests |
| `ChatResponse.surface` | CLI print path, `CognitiveTurnPipeline`, tests/evals |
| `ChatResponse.walk_surface` | `core/cli.py` trace payload, `CognitiveTurnPipeline`, telemetry tests |
| `ChatResponse.articulation_surface` | `core/cli.py`, `CognitiveTurnPipeline`, trace hash construction |
| `ChatResponse.grounding_source` | `CognitiveTurnPipeline`, discovery/OOV candidate emission, tests |
| `safety_verdict` / `ethics_verdict` / `verdicts` | CLI verdict summary, telemetry formatter, turn-loop verdict tests |
| `pre_decoration_surface` / `register_canonical_surface` | `CognitiveTurnPipeline` trace-hash preservation; register invariant tests |
| `register_id` / `register_variant_id` | telemetry formatter, register CLI/tour/tests |
| `anchor_lens_id` / `anchor_lens_mode_label` | telemetry formatter, anchor-lens CLI/tour/tests |
| `realizer_guard_status` / `realizer_guard_rule` | telemetry formatter, guard runtime seam tests |
| `composer_graph_atom_*` | telemetry formatter, atom-equivalence tests |
| `recalled_words` | `CognitiveTurnPipeline` realizer-grounded-authority seam |
| `refusal_reason` | `CognitiveTurnPipeline` / `compute_trace_hash` when non-empty |
| `dispatch_trace` | `core/cognition/result.py`, `CognitiveTurnPipeline`, `tests/test_dispatch_trace.py` |
| `SessionContext.finalize_turn()` | `ChatRuntime.chat()`, `SessionContext.respond()`, session tests |

No L6 response/event field with a documented downstream consumer was
found missing from the live `ChatResponse` construction paths.

**Pass 2 — semantic (L6-specific invariants checked):**

1. **`session/context.py` post-generation unitize discipline.**
   Confirmed `SessionContext.finalize_turn()` applies hemisphere
   correction plus `_anchor_pull()`, and `_anchor_pull()` calls
   `unitize_versor()` after slerp. This is suite-protected by
   `tests/test_session_coherence.py`, and the static invariant only
   forbids `unitize_versor()` in propagation/generation/vault. However,
   no ADR was found that designates session finalization as an allowed
   closure/construction boundary. This is a documented-code/tested
   behavior but an ADR discipline gap.
2. **`InnerLoopExhaustion` propagation.** L5's W-012 finding survives.
   `ChatRuntime.chat()` calls `generate(...)` directly with no
   `except InnerLoopExhaustion` / `except ValueError` materialization.
   Reproduction with `chat.runtime.generate` patched to raise
   `InnerLoopExhaustion(reason=INNER_LOOP_EXHAUSTION, region_label="audit-l6")`
   produced `PROPAGATED inner_loop_exhaustion audit-l6 -1`, not a
   `ChatResponse.refusal_reason`.
3. **`dispatch_trace` trace-hash policy.** Confirmed
   `DispatchTrace` is carried on `ChatResponse` and
   `CognitiveTurnResult` but is not included in
   `compute_trace_hash()` / `trace_hash_from_result()`. This matches
   the code contract in `core/cognition/result.py`: dispatch trace is
   observability-only. Manual branch scan of `_maybe_pack_grounded_surface()`
   found every early admit/fall-through path appends a
   `DispatchAttempt`; final fallbacks add explicit pack/teaching/
   partial/OOV/universal-disclosure attempts. `tests/test_dispatch_trace.py`
   pins pack, universal-disclosure, determinism, and pipeline carriage.
4. **Cross-pack composition discipline.** Reader-side L6 paths
   (`chat/cross_pack_grounding.py`, narrative/example aggregation,
   runtime fall-through) read JSONL corpora and compose surfaces. The
   grep found no runtime pack/corpus mutation in these L6 reader paths;
   mutation remains proposal/review-owned downstream. `chat/telemetry.py`
   and candidate sinks are append-only telemetry, not pack state.
5. **Verdict-surface fail-closed.** Confirmed both stub and main paths
   call `build_refusal_surface(...)`; when it returns a surface,
   `response_surface` is replaced, `_last_refusal_was_typed=True`, and
   downstream dispatch attempts are skipped with `reason="refusal_emitted"`.
   This satisfies ADR-0036/0037 fail-closed runtime replacement for
   safety violations and opted-in ethics violations.

### Semantic mismatches flagged for human review

- **W-012 / `InnerLoopExhaustion` materialization gap.** The typed
  refusal taxonomy exists and trace-hash folding exists, but live
  `ChatRuntime.chat()` does not catch generator refusal exceptions and
  therefore cannot populate `ChatResponse.refusal_reason` for that path.
- **Session finalization closure boundary is not ADR-backed.**
  `session/context.py` performs post-generation anchor pull with
  `unitize_versor()`. The code has comments and tests, and it is not in
  the three forbidden hot-path modules, but the allowed-boundary list
  in project instructions does not name session finalization and no
  ADR documenting that exception was found.
- **`dispatch_trace` is observability-only by implementation.** This
  appears consistent with the current carrier/observability comments,
  but if operators expect dispatch provenance to participate in replay
  equality, an ADR amendment is needed before changing trace-hash
  payloads.

### Closure criteria scorecard

| Criterion | Status | Evidence |
|---|---|---|
| 1. Design artifact | ✅ | ADR-0035..0041, ADR-0048/0050/0052, ADR-0061..0078, ADR-0083, ADR-0090 |
| 2. Code artifact | ✅ | `chat/` modules plus `session/context.py` finalization boundary |
| 3. Live caller | ⚠️ PARTIAL | Main runtime and composer paths live; generator refusal path propagates instead of producing `ChatResponse` |
| 4. Exercised by suite lane | ✅ | smoke/cognition/runtime lanes pass; L6-specific tests present in documented lanes |
| 5. Cross-layer consistency | ⚠️ PARTIAL | Surfaces/verdicts/register/anchor/cross-pack mostly consistent; `InnerLoopExhaustion` and session closure-boundary ADR gap remain |

**Verdict:** **PARTIAL** (`InnerLoopExhaustion` refusal materialization
is unwired in `ChatRuntime.chat()`, and the session-finalization
`unitize_versor()` boundary is tested but not ADR-documented).

### Cleanup performed

**None.** Cleanup-as-found found no unambiguously dead L6 code.
Several modules are small single-consumer helpers, but each has a live
runtime/composer caller or a module-entry role. Wiring debt was flagged
rather than deleted.

### Findings / notes for downstream layers

- **L7 (Teaching loop) auditor:** L6 reads teaching/cross-pack corpora
  and emits discovery/OOV candidates, but no L6 reader path mutates
  pack state. Verify L7 remains the only reviewed mutation/replay path,
  especially for correction acknowledgement and proposal promotion.
- **L8 (Inter-session memory + contemplation) auditor:** L6 emits
  append-only telemetry and discovery/articulation observations. Verify
  contemplation consumes those streams deterministically and does not
  treat L6 reader surfaces as durable learning without review.
- **L9 (Epistemic state + verdicts) auditor:** W-012 blocks full
  refusal-state closure: `InnerLoopExhaustion` reasons do not reach
  `ChatResponse.refusal_reason` or trace hashes live. Also verify
  whether `dispatch_trace` must remain observability-only under
  ADR-0144/epistemic carrier policy.

## L7 — Teaching loop

**Audit date:** 2026-05-24
**Auditor:** primary agent (Gemini)
**Verdict:** **PARTIAL**

### Scope-hypothesis correction (per audit step 0)

The scope's layering table cited Layer L7 concerns as: correction extraction, review, proposal log, replay-equivalence, teaching corpus, pointing to `teaching/correction.py`, `teaching/review.py`, `teaching/store.py`, `teaching/replay.py`. Reality: L7 also encompasses the full offline/curriculum promotion pipeline, discovery candidate sinks, gap detection, OOV queue compilation, supersession history, and relational triple parsing.

### ADRs in scope for L7

| ADR | Title | Status | Belongs at L7? |
|---|---|---|---|
| ADR-0014 | `train/` Learning Loop | Accepted | Yes — specifications for memory tier promotion |
| ADR-0021 | Epistemic status taxonomy | Accepted | Yes — defines `EpistemicStatus` values (COHERENT / SPECULATIVE / CONTESTED / FALSIFIED) |
| ADR-0052 | Teaching-Grounded Surface for Cold-Start CAUSE / VERIFICATION | Accepted | Yes — active teaching corpus loader and resolver |
| ADR-0055 | Inter-Session Memory Discovery & Promotion | Accepted | Yes — four-tier memory and proposal-only corpus mutation path |
| ADR-0057 | Teaching-Chain Proposal + Review + Replay-Equivalence | Accepted | Yes — primary L7 design document (replay-equivalence and proposal state machine) |
| ADR-0059 | Correction-Pass Telemetry | Accepted | Yes — telemetry specs for correction turn |
| ADR-0060 | CORRECTION Acknowledgement Carries the Corrected-Topic Lemma | Accepted | Yes — topic-extraction policy for correction acknowledgement |
| ADR-0064 | Cross-Pack Teaching Corpora Registry | Accepted | Yes — multi-corpus registry and single-pack boundaries |
| ADR-0067 | Cross-pack teaching chains (Plan Phase 4) | Accepted | Yes — multi-pack teaching chain layout and loader |
| ADR-0094 | Proposal Source Provenance | Accepted | Yes — proposal source schema (operator / miner / curriculum) |
| ADR-0095 | Miner-Sourced Teaching Proposals | Accepted | Yes — miner candidate promotion logic |
| ADR-0104 | Curriculum-Sourced Teaching Proposals | Accepted | Yes — curriculum candidate promotion logic |
| ADR-0129 | Spaced-Correction Replay | Deferred | Yes — deferred spaced-replay strategy |
| ADR-0131.2 | Teaching Corpus Eval | Accepted | Yes — math teaching corpus evaluation runner |

### Modules in scope for L7

| Module | Lines | Live-import sites (outside `teaching/`, outside `tests/`) | Test-import sites | Status |
|---|---|---|---|---|
| `teaching/__init__.py` | 33 | 0 | 2 | Live (Re-export shim) |
| `teaching/audit.py` | 313 | 2 (`core/cli.py`, `teaching/supersede.py`) | 1 | Live |
| `teaching/contemplation.py` | 505 | 1 (`core/cli.py` / `core/contemplation/__main__.py`) | 1 | Live |
| `teaching/correction.py` | 64 | 4 (`core/cognition/pipeline.py`, `core/cognition/result.py`, `formation/promote.py`, `chat/pack_grounding.py`) | 3 | Live |
| `teaching/cross_pack_supersede.py` | 206 | 1 (`core/cli.py`) | 1 | Live |
| `teaching/discovery.py` | 326 | 2 (`teaching/proposals.py`, `core/cli.py`) | 2 | Live |
| `teaching/discovery_sink.py` | 105 | 1 (`core/contemplation/__main__.py`) | 3 | Live |
| `teaching/epistemic.py` | 56 | 6 (`core/cognition/pipeline.py`, `generate/proposition.py`, `vault/store.py`, `session/context.py`, `language_packs/compiler.py`, `formation/promote.py`) | 6 | Live |
| `teaching/from_curriculum.py` | 275 | 0 | 1 | Partially live (test-only logic) |
| `teaching/from_miner.py` | 370 | 0 | 1 | Partially live (test-only logic) |
| `teaching/gaps.py` | 206 | 1 (`core/cli.py`) | 1 | Live |
| `teaching/metric_set.py` | 14 | 1 (`teaching/replay.py`) | 0 | Live |
| `teaching/migrate_proposals_source_field.py` | 123 | 0 | 0 | Live (One-shot migration CLI) |
| `teaching/oov_gaps.py` | 170 | 1 (`core/cli.py`) | 1 | Live |
| `teaching/oov_promotion.py` | 119 | 1 (`core/cli.py`) | 1 | Live |
| `teaching/oov_sink.py` | 160 | 1 (`chat/runtime.py`) | 1 | Live |
| `teaching/promotion.py` | 132 | 1 (`core/cli.py`) | 1 | Live |
| `teaching/proposals.py` | 565 | 1 (`core/cli.py`) | 2 | Live |
| `teaching/provenance.py` | 88 | 3 (`teaching/proposals.py`, `teaching/audit.py`, `teaching/supersede.py`) | 1 | Live |
| `teaching/relation_parse.py` | 128 | 3 (`teaching/store.py`, `formation/forge.py`, `formation/smelter.py`) | 2 | Live |
| `teaching/replay.py` | 173 | 1 (`teaching/proposals.py`) | 1 | Live |
| `teaching/review.py` | 307 | 2 (`core/cognition/pipeline.py`, `formation/promote.py`) | 3 | Live |
| `teaching/source.py` | 137 | 1 (`teaching/proposals.py`) | 1 | Live |
| `teaching/store.py` | 301 | 1 (`core/cognition/pipeline.py`) | 2 | Live |
| `teaching/supersede.py` | 196 | 1 (`core/cli.py`) | 1 | Live |

### Caller-trace evidence

The live turn-by-turn chat runtime captures corrections:
`ChatRuntime.chat()` → `CognitiveTurnPipeline.run()` → `_run_teaching` → `extract_correction` → `review_correction` → `TeachingStore.add`. This builds a memory-resident `PackMutationProposal` with `SPECULATIVE` or `CONTESTED` status on the fly.

The offline / curriculum loop writes and processes proposals:
`TurnEvent` / `CognitiveTurnResult` → `extract_discovery_candidates` → written to disk via `DiscoveryMonthlyFileSink`.
`core teaching propose` (CLI command) → `propose_from_candidate` → runs `run_replay_equivalence` → appends to `proposals.jsonl` on disk.
`core teaching review <proposal_id> --accept` (CLI command) → `accept_proposal` → `append_chain_to_corpus` → appends the chain with operator provenance to `teaching/cognition_chains/cognition_chains_v1.jsonl`.
Subsequent engine invocations parse the new active corpus via `chat.teaching_grounding._all_chains_index()`, grounding relevant `CAUSE` / `VERIFICATION` prompts.

### Exercising suite lane

- Direct L7 tests:
  ```bash
  python3 -m core.cli test --suite teaching -q
  ```
  **Verification:** 17 passed.
- Cross-layer regressions:
  ```bash
  python3 -m core.cli test --suite smoke -q
  ```
  **Verification:** 67 passed.
- Lane SHAs match:
  ```bash
  python3 scripts/verify_lane_shas.py
  ```
  **Verification:** 7/7 match pinned SHAs.

### Cross-layer contract check

**Pass 1 — mechanical (consumer-exists per exposed symbol):**

| Exposed symbol / field | Consumer evidence |
|---|---|
| `extract_correction` / `CorrectionCandidate` | `core/cognition/pipeline.py:50,568`, `core/cognition/result.py:21`, `chat/pack_grounding.py` |
| `review_correction` / `ReviewedTeachingExample` | `core/cognition/pipeline.py:52,578` |
| `TeachingStore` | `core/cognition/pipeline.py:53,120` |
| `EpistemicStatus` / `ADMISSIBLE_AS_EVIDENCE` | `core/cognition/pipeline.py:51`, `vault/store.py:21`, `session/context.py:24`, `generate/proposition.py:23` |
| `parse_triple` | `teaching/store.py:179`, `formation/forge.py:54`, `formation/smelter.py:37` |
| `run_replay_equivalence` | `teaching/proposals.py:472`, `evals/math_teaching_corpus/v1/runner.py:155`, direct tests |
| `propose_from_candidate` | `core/cli.py:1208`, `benchmarks/teaching_loop.py:161`, evals and tests |
| `accept_proposal` / `reject_proposal` / `withdraw_proposal` | `core/cli.py:1263,1271,1274`, direct tests |
| `DiscoveryMonthlyFileSink` | `core/contemplation/__main__.py:75`, `tests/test_discovery_candidates.py` |
| `OOVMonthlyFileSink` | `chat/runtime.py:700`, `tests/test_oov_pipeline.py` |

**Pass 2 — semantic (six L7 invariants checked):**

1. **Replay-equivalence gate liveness.** Verified. The replay-equivalence gate (`run_replay_equivalence`) is called in the operator-driven CLI flow (`core teaching propose` which calls `propose_from_candidate`), and accepted proposals are verified in `accept_proposal`. It is not run during live turn execution because running the full cognition split twice is slow. This matches the design of ADR-0057.
2. **Append-only proposal log.** Verified. `teaching/proposals.py:``ProposalLog` writes using `"a"` mode and never rewrites or truncates `proposals.jsonl`. Replaying the log from the top reconstructs the review-state view. The active corpus `cognition_chains_v1.jsonl` is also written using append-only `"a"` mode, with old entries retired using the `superseded_by` tag at load time.
3. **Pack-mutation proposal-only discipline.** Verified. No code in `teaching/` directly writes or mutates packs on disk. The queue generators (`oov_promotion.py`, `promotion.py`) suggest mutations for packs but leave the application to the operator.
4. **Teaching corpus content invariant.** Verified. `chat/teaching_grounding.py` loads single-pack and cross-pack teaching chains and filters them against their respective declared packs. Any chain referencing missing lemmas is silently dropped.
5. **HITL ratification synchronousness.** Confirmed. Replay-equivalence and proposal review are synchronous CLI workflows run by the operator between session iterations. The asynchronous queue is documented as future work (W-009).
6. **Recognition-refusal consumer.** Confirmed. There is no consumer of recognition-refusal signals within `teaching/` today (this matches the W-011 gap).

### Semantic mismatches flagged for human review

- **Dormant `explain()` wiring.** `core/cognition/explain.py` is dormant. It is not consumed by the teaching review loop or proposal commands. Natural-language turn explanations for reviewed corrections remain unwired.
- **Unconsumed recognition refusals.** Recognition-refusal signals are discarded by the pipeline and do not feed the correction/review loop.

### Closure criteria scorecard

| Criterion | Status | Evidence |
|---|---|---|
| 1. Design artifact | ✅ | ADR-0014, ADR-0021, ADR-0052, ADR-0055, ADR-0057, ADR-0059, ADR-0060, ADR-0064, ADR-0067, ADR-0094, ADR-0095, ADR-0104, ADR-0129, ADR-0131.2 |
| 2. Code artifact | ✅ | `teaching/` python modules and CLI commands |
| 3. Live caller | ⚠️ PARTIAL | In-memory correction capture, review, and proposal tracking are live; recognition-refusal and explain() integrations are dormant |
| 4. Exercised by suite lane | ✅ | `teaching` suite lane passes; `smoke` lane passes; `verify_lane_shas.py` is 7/7 |
| 5. Cross-layer consistency | ⚠️ PARTIAL | Core schema and invariants consistent; lack of recognition-refusal consumer leaves L4/L7 boundary open |

### Cleanup performed

**None.** No modules were found to be unambiguously dead, redundant, or orphaned. Curriculum/miner proposal builders are test-live and key to curriculum/miner integration; one-shot migration script is kept on disk for documentation.

### Findings / notes for downstream layers

- **L8 (Inter-session memory + contemplation) / L10 (Runtime model) auditor:** W-009 is the primary gap for memory queueing: the async queue is not implemented, and the current teaching loop is synchronous. Document this as a constraint when building inter-session memory promotion.
- **L9 (Epistemic state) / L4 (Recognition) auditor:** W-011 is open. Integrate recognition-refusal signals as teaching candidates or review signals in the next layer's audit.

---

## L8 — Inter-session memory + contemplation

**Audit date:** 2026-05-24
**Auditor:** primary agent (Codex)
**Verdict:** **PARTIAL**

### Scope-hypothesis correction (per audit step 0)

The scope's layering table cited Layer L8 concerns as: discovery, contemplation, and multi-tier memory. Reality: L8 spans four distinct surfaces that are only partially joined: live turn-loop discovery/OOV emission, opt-in inline DiscoveryCandidate contemplation, operator-run ADR-0080 report contemplation, and the four-tier memory promotion model. L7 already audited the proposal review, replay-equivalence, and corpus-mutation machinery; this L8 pass treats that path only as the downstream promotion target.

### ADRs in scope for L8

| ADR | Title | Status | Belongs at L8? |
|---|---|---|---|
| ADR-0039 | Audit Completeness — `TurnVerdicts` Bundle, Stub-Path `TurnEvent`, `hedge_injected` Signal | Accepted | Yes — makes Tier 2 turn-event evidence complete enough to mine |
| ADR-0040 | Telemetry Sink | Accepted | Yes — durable JSONL sink for the Tier 2 audit trail |
| ADR-0041 | CLI Verdicts and Fan-out | Accepted | Yes — operator-readable / fan-out telemetry plumbing for Tier 2 |
| ADR-0055 | Inter-Session Memory Discovery & Promotion | Phase A + B Accepted; C-E Proposed | Yes — primary four-tier memory and discovery-promotion design |
| ADR-0056 | Contemplation Loop C1 | Accepted | Yes — DiscoveryCandidate enrichment / question decomposition |
| ADR-0057 | Teaching-Chain Proposal + Review + Replay-Equivalence | Accepted | Boundary only — downstream L7 promotion gate consumed by L8 |
| ADR-0064 | Cross-Pack Teaching Corpora Registry | Accepted | Yes — discovery gate and teaching read path widened beyond one corpus |
| ADR-0065 | OOV Gradient + Relations v2 | Accepted | Yes — OOV gap signal feeding pack-vocabulary promotion |
| ADR-0067 | Cross-pack teaching chains | Accepted | Yes — cross-pack memory read path and supersession semantics |
| ADR-0080 | Contemplation Loop | Accepted | Yes — read-only, SPECULATIVE-only self-contemplation over explicit evidence files |
| ADR-0094 | Proposal Source Provenance | Accepted | Yes — source schema for operator / miner / curriculum / contemplation provenance |
| ADR-0095 | Miner-Sourced Teaching Proposals | Accepted | Yes — miner findings can become reviewed proposals without source authority |
| ADR-0104 | Curriculum-Sourced Teaching Proposals | Accepted | Yes — curriculum findings can become reviewed proposals without source authority |

### Modules in scope for L8

| Module | Lines | Live-import sites (outside `teaching/`, outside `tests/`) | Test-import sites | Status |
|---|---|---|---|---|
| `teaching/contemplation.py` | 505 | 1 (`chat/runtime.py`) | 1 | Live, but opt-in and no live vault probe |
| `teaching/discovery.py` | 326 | 1 (`chat/runtime.py`) | 2 | Live |
| `teaching/discovery_sink.py` | 105 | 1 (`core/contemplation/__main__.py`) | 3 | Live |
| `teaching/oov_sink.py` | 160 | 1 (`chat/runtime.py`) | 1 | Live |
| `teaching/oov_gaps.py` | 170 | 1 (`core/cli.py`) | 1 | Live |
| `teaching/oov_promotion.py` | 119 | 1 (`core/cli.py`) | 1 | Live |
| `teaching/from_miner.py` | 370 | 0 | 1 | Partially live (test-only proposal conversion) |
| `teaching/from_curriculum.py` | 275 | 0 | 1 | Partially live (test-only proposal conversion) |
| `teaching/gaps.py` | 206 | 1 (`core/cli.py`) | 1 | Live |
| `teaching/audit.py` | 313 | 2 (`core/cli.py`, `teaching/supersede.py`) | 1 | Live |
| `teaching/supersede.py` | 196 | 1 (`core/cli.py`) | 1 | Live |
| `teaching/cross_pack_supersede.py` | 206 | 1 (`core/cli.py`) | 1 | Live |
| `core/contemplation/__main__.py` | 94 | 1 (`core/cli.py`) | 0 | Live operator CLI |
| `core/contemplation/runner.py` | 193 | 1 (`core/contemplation/__main__.py`) | 2 | Live operator runner |
| `core/contemplation/schema.py` | 231 | 5 (`core/contemplation/*`, `teaching/from_miner.py`) | 4 | Live |
| `core/contemplation/snapshot.py` | 77 | 1 (`core/contemplation/runner.py`) | 1 | Live |
| `core/contemplation/plan_preflight.py` | 246 | 1 (`chat/runtime.py`) | 2 | Live, opt-in |
| `core/contemplation/plan_metrics.py` | 247 | 1 (`chat/runtime.py`) | 2 | Live, opt-in |
| `core/contemplation/miners/frontier_compare.py` | 75 | 1 (`core/contemplation/runner.py`) | 1 | Live operator miner |
| `core/contemplation/miners/contradiction_detection.py` | 111 | 1 (`core/contemplation/runner.py`) | 1 | Live operator miner |
| `core/contemplation/miners/articulation_quality.py` | 352 | 0 | 2 | Partially live (runtime emits observations; miner is test-only/offline API today) |
| `vault/store.py` | 300 | 4 (`session/context.py`, `chat/runtime.py`, `generate/stream.py`, `vault/decompose.py`) | 7 | Live Tier 1 store/read substrate |
| `core/cognition/explain.py` | 124 | 0 | 1 | Dormant |

### Caller-trace evidence

Live discovery and OOV emission are attached to the turn loop but require explicit sinks:
`ChatRuntime.chat()` stub/cold path → `TurnEvent` → `_emit_discovery_candidates` → `extract_discovery_candidates` → optional `teaching.contemplation.contemplate` when `attach_contemplation(enabled=True)` was called → attached `DiscoveryCandidateSink.emit`.
For OOV turns, the same block calls `_emit_oov_candidate` → `OOVCandidate` → attached `OOVCandidateSink.emit`. `OOVMonthlyFileSink` is a live consumer from `chat/runtime.py:700` when an operator attaches it.

ADR-0080 report contemplation is operator/batch, not live-turn autonomous:
`core contemplation <reports...>` → `core.contemplation.__main__.main` → `contemplate_frontier_reports` / `contemplate_contradiction_reports` → optional `DiscoveryMonthlyFileSink`. The runner reads explicit report paths and may emit findings to the same monthly discovery sink, but it does not crawl live runtime state and does not promote findings.

Plan contemplation is live only under opt-in runtime configuration:
`RuntimeConfig(discourse_contemplation=True)` → `ChatRuntime._maybe_apply_discourse_planner` → `contemplate_plan` + `compute_plan_metrics` → read-only `last_plan_findings` / `last_plan_metrics`. With both `discourse_contemplation=True` and `attach_articulation_sink(sink)`, the runtime emits `ArticulationObservation` JSONL for the offline articulation-quality miner.

Four-tier memory currently flows as:
Tier 1 session vault is written and read during a session through `SessionContext` / `VaultStore`.
Tier 2 turn audit exists in memory (`turn_log`) and optionally JSONL telemetry.
Tier 3 reviewed teaching corpus is loaded by `chat.teaching_grounding` / cross-pack loaders and appended only by L7's reviewed proposal paths.
Tier 4 ratified packs are read by pack resolvers and pack grounding. Pack mutation remains proposal-only.

### Exercising suite lane

- Direct L8/L7 shared tests:
  ```bash
  python3 -m core.cli test --suite teaching -q
  ```
  **Verification:** 17 passed.
- Cross-layer regressions:
  ```bash
  python3 -m core.cli test --suite smoke -q
  ```
  **Verification:** 67 passed.
- Lane SHAs match:
  ```bash
  python3 scripts/verify_lane_shas.py
  ```
  **Verification:** 7/7 match pinned SHAs.

### Cross-layer contract check

**Pass 1 — mechanical (consumer-exists per exposed symbol):**

| Exposed symbol / field | Consumer evidence |
|---|---|
| `VaultStore.store` / `VaultStore.recall` / `VaultStore.recall_batch` | `SessionContext`, `ChatRuntime`, `generate/stream.py`, `vault/decompose.py`, direct tests |
| `TurnEvent` / `format_turn_event_jsonl` | `ChatRuntime._emit_turn_event`, telemetry sinks, telemetry tests |
| `extract_discovery_candidates` / `DiscoveryCandidate` | `ChatRuntime._emit_discovery_candidates`, `teaching.proposals`, direct tests |
| `DiscoveryMonthlyFileSink` | `core/contemplation/__main__.py`, direct discovery/contemplation tests |
| `OOVCandidate` / `OOVMonthlyFileSink` | `ChatRuntime._emit_oov_candidate`, OOV pipeline tests |
| `teaching.contemplation.contemplate` | `ChatRuntime._emit_discovery_candidates` when `attach_contemplation(enabled=True)`, direct tests |
| `contemplate_frontier_reports` / `contemplate_contradiction_reports` | `core contemplation` CLI, contemplation-loop tests |
| `contemplate_plan` / `compute_plan_metrics` | `ChatRuntime._maybe_apply_discourse_planner` when `discourse_contemplation=True`, runtime tests |
| `mine_articulation_observations` | Direct tests; runtime produces its input stream via `attach_articulation_sink` |
| `supersede_cross_pack_chain` | `core teaching supersede --cross-pack`, cross-pack supersede tests |
| `ProposalSource` | `teaching.proposals`, `teaching.store.PackMutationProposal`, `teaching/from_miner.py`, `teaching/from_curriculum.py`, source tests |
| `core.cognition.explain.explain` | Direct tests only; no runtime / teaching / contemplation consumer |

**Pass 2 — semantic (five L8 invariants checked):**

1. **Four-tier model liveness (ADR-0055).** **PARTIAL.** T1 session vault storage and readback are live (`VaultStore.store` / `recall`). T2 turn-event audit is live in `turn_log` and optionally JSONL telemetry. T3 reviewed teaching corpus is live as a read path and can be appended only through L7's reviewed proposal flow. T4 ratified packs are live as pack-grounding / resolver substrate, with mutation still proposal-only. The missing ADR-0055 link remains: no automated T1/T2 → T3 promotion exists. Discovery candidates are emitted from `TurnEvent` evidence, but not from direct vault scans, and contemplation receives no live vault probe by default.
2. **Contemplation loop liveness.** **PARTIAL.** `teaching.contemplation.contemplate` can run inline during live turns, but only after an operator attaches a discovery sink and separately enables contemplation. ADR-0080 `core/contemplation` is CLI/batch-only over explicit report files. Plan contemplation is live-turn-integrated only behind `RuntimeConfig.discourse_contemplation=True`; default runtime leaves it off.
3. **Discovery candidate sink wiring.** Verified. `ChatRuntime.attach_discovery_sink` wires live-turn `DiscoveryCandidate` JSONL emission. `DiscoveryMonthlyFileSink` itself is consumed by the `core contemplation` CLI; live runtime accepts any sink satisfying the same protocol. `OOVMonthlyFileSink` is live-compatible through `ChatRuntime.attach_oov_sink`, with `_emit_oov_candidate` importing `teaching.oov_sink` at `chat/runtime.py:700`.
4. **Cross-pack supersession.** Verified. `teaching/cross_pack_supersede.py` is CLI-live through `core teaching supersede --cross-pack`; it appends a replacement entry and verifies reload. Runtime load drops any cross-pack chain whose `chain_id` appears as another entry's `superseded_by`, so older chains are retired at load time while disk history remains append-only.
5. **Proposal source provenance (ADR-0094).** Mechanically verified, semantically partial. `ProposalSource` is required on created proposals; `ProposalLog.current_state()` rejects missing or malformed `source`; `teaching/proposals/proposals.jsonl` has 11/11 created proposals with valid `source`. Miner and curriculum builders stamp `kind="miner"` / `kind="curriculum"` respectively. However, source kind currently does not grant authority or change review semantics; it is enforced provenance and audit routing, not differentiated downstream behavior.

### Four-tier model liveness map

| Tier | Storage live? | Promotion to it live? | Read path live? | L8 verdict |
|---|---|---|---|---|
| T1 — session vault | ✅ `VaultStore` via `SessionContext` | ✅ live session ingest/finalization writes session entries | ✅ exact CGA recall in runtime/generation/decomposition | Live |
| T2 — turn-event audit trail | ✅ `turn_log`; optional telemetry JSONL sink | ✅ every chat turn appends a `TurnEvent`; stub path participates | ✅ telemetry readers/tests and discovery extraction over current turn | Live, sink opt-in |
| T3 — reviewed teaching corpus | ✅ JSONL corpora under `teaching/*_chains*` | ⚠️ reviewed append via L7 is live; automated T1/T2 discovery promotion remains absent | ✅ teaching/cross-pack grounding loaders | PARTIAL |
| T4 — ratified packs | ✅ `packs/*`, `language_packs/data/*` | ⚠️ pack mutation is proposal-only; ratification is outside L8 live turn loop | ✅ pack resolver / grounding / contemplation pack probes | PARTIAL by design |

### Semantic mismatches flagged for human review

- **No live T1 vault probe in DiscoveryCandidate contemplation.** `teaching.contemplation` has an injectable `vault_probe`, and tests prove coherent vault evidence can contribute, but `ChatRuntime._emit_discovery_candidates` calls `contemplate(c)` with no probe. Inline contemplation therefore operates on pack + reviewed corpus only.
- **ADR-0055 automated T1/T2 → T3 promotion is still absent.** Discovery candidates and contemplated findings are evidence streams; promotion still requires L7's synchronous operator proposal/review flow.
- **ADR-0080 contemplation is not an autonomous runtime loop.** It is an operator command over explicit report files. Live plan contemplation exists, but is opt-in and observation-only.
- **`core/cognition/explain.py` remains dormant.** L8 does not consume `explain()` for teaching/contemplation summaries of decoded turns.
- **`from_miner.py` and `from_curriculum.py` remain test-live only.** They correctly build source-stamped proposals, but no CLI/runtime command currently invokes them.

### Closure criteria scorecard

| Criterion | Status | Evidence |
|---|---|---|
| 1. Design artifact | ✅ | ADR-0039, ADR-0040, ADR-0041, ADR-0055, ADR-0056, ADR-0057, ADR-0064, ADR-0065, ADR-0067, ADR-0080, ADR-0094, ADR-0095, ADR-0104 |
| 2. Code artifact | ✅ | `vault/`, `chat/runtime.py`, `teaching/discovery*`, `teaching/oov*`, `teaching/contemplation.py`, `core/contemplation/` |
| 3. Live caller | ⚠️ PARTIAL | Discovery/OOV and opt-in plan contemplation are live; ADR-0080 is operator CLI; miner/curriculum proposal builders are test-only |
| 4. Exercised by suite lane | ✅ | `teaching` suite lane passes; `smoke` lane passes; `verify_lane_shas.py` is 7/7 |
| 5. Cross-layer consistency | ⚠️ PARTIAL | T1/T2 evidence exists and T3/T4 reads exist; automated T1/T2 → T3/T4 promotion is not wired |

### Cleanup performed

**None.** No L8 module was unambiguously dead across both L7 and L8 perspectives. `from_miner.py` and `from_curriculum.py` remain test-live and structurally important for source-stamped proposal construction. `core/cognition/explain.py` is dormant but still directly tested and is the natural future hook for turn explanation.

### Findings / notes for downstream layers

- **L9 (Epistemic state + verdicts) auditor:** L8 intentionally did not touch safety/ethics/verdict files. Discovery candidate emission computes `boundary_clean` from refusal/hedge state and carries `source_turn_trace`; verify whether L9 verdict surfaces should become explicit discovery/contemplation evidence, or remain audit-only.
- **L9 (Epistemic state + verdicts) auditor:** Proposal source kind is provenance, not authority. Verify that any future epistemic policy does not treat `miner` or `curriculum` sources as more coherent than `operator` without review.
- **L10 (Runtime model) auditor:** W-009 remains the memory-queue constraint. The promotion path is synchronous/operator-driven; no async queue or background promotion loop exists.
- **Future L8 work:** If ADR-0055 Phase D is implemented, wire a live coherent-only vault probe into `teaching.contemplation.contemplate` and prove that SPECULATIVE / CONTESTED / FALSIFIED vault entries cannot promote.

---
