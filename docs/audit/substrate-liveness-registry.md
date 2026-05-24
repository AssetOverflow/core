# Substrate Liveness Registry

**Scope:** [substrate-liveness-audit-scope](../decisions/substrate-liveness-audit-scope.md) (v2)
**Status:** Active audit — append-only as layers are completed.
**Discipline:** [feedback-adr-cross-reference-discipline](../../../.claude/projects/-Users-kaizenpro-Projects-core/memory/feedback-adr-cross-reference-discipline.md), [feedback-cleanup-as-you-find](../../../.claude/projects/-Users-kaizenpro-Projects-core/memory/feedback-cleanup-as-you-find.md)

## Audit progress

| Layer | Status | Verdict | Cleanup performed | Last audited |
|---|---|---|---|---|
| L0 — Algebra primitives | ✅ Audited | **CLOSED** | None — no dead code found | 2026-05-24 |
| L1 — Field substrate | ⏳ Pending | — | — | — |
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
