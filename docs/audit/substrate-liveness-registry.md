# Substrate Liveness Registry

**Scope:** [substrate-liveness-audit-scope](../decisions/substrate-liveness-audit-scope.md) (v2)
**Status:** Active audit — append-only as layers are completed.
**Discipline:** [feedback-adr-cross-reference-discipline](../../../.claude/projects/-Users-kaizenpro-Projects-core/memory/feedback-adr-cross-reference-discipline.md), [feedback-cleanup-as-you-find](../../../.claude/projects/-Users-kaizenpro-Projects-core/memory/feedback-cleanup-as-you-find.md)

## Audit progress

| Layer | Status | Verdict | Cleanup performed | Last audited |
|---|---|---|---|---|
| L0 — Algebra primitives | ✅ Audited | **CLOSED** | None — no dead code found | 2026-05-24 |
| L1 — Field substrate | ✅ Audited | **PARTIAL** | None — no dead code found | 2026-05-24 |
| L2 — Vault | ⏳ Pending | — | — | — |
| L3 — Language packs | ⏳ Pending | — | — | — |
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
