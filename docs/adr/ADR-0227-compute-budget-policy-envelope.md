# ADR-0227: ComputeBudgetPolicy Envelope

**Status:** Proposed

**Date:** 2026-06-22

**Scope:** Kernel diagnostics, bounded contemplation, sealed practice

**Depends on:** ADR-0226 and PR #865

---

## 1. Summary

This ADR defines the diagnostic `ComputeBudgetPolicy` and its corresponding output record `ComputeBudgetDecision`. This is the next envelope in the Residual-Gated Practice Loop v1:

```text
ContractAssessment
→ ContractResidual
→ SearchGateDecision
→ ComputeBudgetDecision
```

`ComputeBudgetPolicy` specifies a deterministic, diagnostic-only resource ceiling for future bounded contemplation and candidate exploration. It does not execute search, rank candidates, repair frames, or mutate any assets.

---

## 2. Why this exists

Once a residual context has been assessed by the `SearchGateDecision` and gated as `eligible`, the cognitive engine requires a deterministic resource boundary before any exploration or candidate reconstruction run can be initialized.

Without a distinct, deterministic budget envelope, downstream exploration could easily drift into:
* **Unbounded retries:** looping indefinitely without a terminal condition;
* **Stochastic exploration:** consuming varying amounts of compute based on transient execution time or non-replayable resource state;
* **Implicit repair / compute-as-truth:** using search budget as an epistemological validator (i.e. "if search completes, the candidate must be correct") rather than requiring independent contract and proof replay.

A structured, non-authoritative budget envelope protects the engine from executing unbounded search while ensuring that resource limits are themselves fully replay-stable and inspectable.

---

## 3. Non-Authority Doctrine

To prevent authority collapse and maintain the core safety invariants of the cognitive engine, the budget policy operates under a strict non-authority boundary:

> [!IMPORTANT]
> **Core Non-Authority Rules:**
> * `ComputeBudgetDecision` cannot authorize serving.
> * `ComputeBudgetDecision` cannot authorize mutation.
> * `ComputeBudgetDecision` cannot authorize answer production.
> * `ComputeBudgetDecision` cannot make a candidate true, valid, or closed.
> * `ComputeBudgetDecision` cannot repair a `ProblemFrame`.
> * `ComputeBudgetDecision` cannot call or execute search.
> * `ComputeBudgetDecision` cannot call external models.
> * `ComputeBudgetDecision` cannot override `SearchGateDecision`.

If the associated `SearchGateDecision` status is anything other than `ELIGIBLE` (e.g. `INELIGIBLE`, `BLOCKED`, `UNASSESSABLE`), the compute budget **must** be zero/blocked.

---

## 4. Inputs

A `ComputeBudgetDecision` is mapped directly from a single `SearchGateDecision`.

### Context Grouping
The default grouping constraint is **one-to-one**: exactly one `ComputeBudgetDecision` is produced for each `SearchGateDecision`. Budgets are never aggregated across independent gate decisions or distinct candidate organs.

### Required Input Properties
The budget policy requires the following fields from the input `SearchGateDecision`:
* `decision_id`: str (deterministic gate identifier)
* `policy_version`: str (gate policy version)
* `input_digest`: str (hash of the underlying residual context)
* `status`: SearchGateStatus (must be `ELIGIBLE` to grant non-zero budget)
* `reason_code`: str (e.g. `eligible_missing_role`, `eligible_missing_relation`)
* `residual_ids`: tuple[str, ...] (the exact projected residuals)
* `candidate_organ`: str | None (the diagnostic organ context)
* `evidence_spans`: tuple[SourceSpan, ...] (ordered provenance spans)

---

## 5. Output Shape

We define the conceptual schema for `ComputeBudgetDecision` with the following fields:

```python
@dataclass(frozen=True, slots=True)
class ComputeBudgetDecision:
    budget_id: str
    policy_version: str
    gate_decision_id: str
    gate_policy_version: str
    gate_input_digest: str
    status: ComputeBudgetStatus
    reason_code: str
    max_candidates: int
    max_depth: int
    max_steps: int
    max_wallclock_ms: int | None
    max_parallelism: int
    evidence_spans: tuple[SourceSpan, ...]
    explanation: str
```
*(Note: This is documentation only. No Python classes are implemented in this PR.)*

### ComputeBudgetStatus
We define the closed enum `ComputeBudgetStatus` with the following allowed values:
* `BUDGET_ALLOWED`: Bounded resource limits are granted for the eligible gate decision.
* `BUDGET_BLOCKED`: The gate decision is ineligible or blocked; budget limits are explicitly set to zero.
* `BUDGET_ZERO`: Budget is successfully assessed but explicitly configured as zero.
* `BUDGET_UNASSESSABLE`: The input gate decision contains malformed or unassessable structures.

### Wall-Clock Time Separation
The field `max_wallclock_ms` is strictly **diagnostic metadata**. It is excluded from the deterministic execution authority to prevent environment, hardware, or load-dependent divergence during replay. Budgets are enforced primarily using deterministic structural limits: `max_candidates`, `max_depth`, and `max_steps`.

---

## 6. Deterministic Policy Version

To ensure version consistency and avoid un-tracked changes to the budget tables:

```python
COMPUTE_BUDGET_POLICY_VERSION = "compute_budget.v1"
```

The implementation must use this exact string to identify the v1 policy.

---

## 7. Deterministic Budget ID

The `budget_id` is a full lowercase SHA-256 hash over a canonical JSON payload representing the deterministic fields of the decision.

### Payload Fields
The hash input must include exactly:
1. `policy_version`
2. `gate_decision_id`
3. `gate_policy_version`
4. `gate_input_digest`
5. `status` (as string value)
6. `reason_code`
7. `max_candidates`
8. `max_depth`
9. `max_steps`
10. `max_parallelism`
11. `evidence_spans`: An ordered list of spans containing:
    * `text`
    * `start`
    * `end`
    * `sentence_index`

### Excluded Fields
To guarantee that the `budget_id` remains completely replay-stable across different processes, machines, and execution runs, the following fields **must not** be included in the hashed payload:
* `explanation` (localized or formatting-sensitive text)
* `max_wallclock_ms` (hardware-dependent value)
* Current system time, timestamps, or clocks
* Random numbers or UUIDs
* Environment variables, hostname, OS details, or CI run metadata
* File system paths

---

## 8. Budget Policy Table (v1)

We define a closed, static budget allocation table for version `compute_budget.v1`. Budgets must remain small and deterministic.

| SearchGateStatus | SearchGate reason_code | Budget Status | max_candidates | max_depth | max_steps | max_parallelism |
|---|---|---|---|---|---|---|
| **Any non-ELIGIBLE status**<br>(`BLOCKED`, `INELIGIBLE`, `UNASSESSABLE`) | *Any* | `BUDGET_BLOCKED` | 0 | 0 | 0 | 0 |
| `ELIGIBLE` | `eligible_missing_role` | `BUDGET_ALLOWED` | 5 | 2 | 10 | 1 |
| `ELIGIBLE` | `eligible_missing_relation` | `BUDGET_ALLOWED` | 5 | 2 | 10 | 1 |
| `ELIGIBLE` | `eligible_missing_proposal` | `BUDGET_ALLOWED` | 3 | 1 | 5 | 1 |
| `ELIGIBLE` | `eligible_target_unbound` | `BUDGET_ALLOWED` | 5 | 2 | 10 | 1 |
| `ELIGIBLE` | *Any unknown code* | `BUDGET_UNASSESSABLE`| 0 | 0 | 0 | 0 |

### Constraints:
* **No adaptive scaling:** The budget cannot self-increase, adapt dynamically to progress, or scale based on previous failures.
* **No "try until solved":** The limits are hard ceilings; exhaustion must immediately terminate the run as a refusal.
* **No concurrency bounds expansion:** `max_parallelism` is pinned to `1` in v1 to ensure deterministic candidate traversal.

---

## 9. Interaction with Future GeometricSearchRun

A future `GeometricSearchRun` component must consume `ComputeBudgetDecision` as a load-bearing constraint. The run must refuse to initialize or execute if:
* The budget status is `BUDGET_BLOCKED`, `BUDGET_ZERO`, or `BUDGET_UNASSESSABLE`.
* The budget limits are invalid or exhausted (`max_candidates == 0` or `max_steps == 0`).
* The `budget_id` does not match the canonical hash reconstructed from the inputs during replay.
* The `policy_version` is unsupported by the runner.

This ADR does not implement the `GeometricSearchRun`.

---

## 10. Practice and Workbench Implications

### Practice Loop
The Practice Loop may persist the `ComputeBudgetDecision` within the sealed trace for diagnostic and auditing purposes. The loop must treat the budget as a resource ceiling only; recording a budget decision does not change the epistemic status of any candidate or mutate any ratified packs.

### Workbench
Workbench may expose these budget decisions in a read-only viewer, allowing operators to audit:
* Why a particular budget was allowed or blocked;
* The specific limits applied (`max_candidates`, `max_depth`, `max_steps`).

There are no interactive tuning controls, edit forms, or operator override actions permitted in Workbench for this PR.

---

## 11. Non-Goals

This ADR explicitly does not cover:
* Implementing python code for `ComputeBudgetPolicy` or `ComputeBudgetDecision`.
* Implementing the `GeometricSearchRun` candidate search.
* Mutating or displaying in Workbench.
* Serving path alterations or runtime dispatch.
* Adding new contract labels or modifying the existing assessment logic.
* Mutating teaching proposals, training packs, or reliability-ledger counts.

---

## 12. Follow-on PRs

The proposed sequence of PRs after this ADR is:

```text
#867 — ratify ComputeBudgetPolicy envelope
#868 — implement diagnostic-only ComputeBudgetDecision
#869 — define inert GeometricSearchRun envelope
```

These numbers are provisional and subject to adjustment during code reviews.

---

## 13. Acceptance Criteria

This proposal is complete when:
1. The PR is docs-only and contains exactly this ADR file.
2. The role of the budget decision as a non-authoritative ceiling is stated explicitly.
3. The deterministic hashing scheme for `budget_id` is defined and excludes wall-clock/environment parameters.
4. The closed policy table for `compute_budget.v1` is defined.
5. Fail-closed semantics for invalid/denied gates are enforced.
6. `git diff --check` passes cleanly with no trailing whitespace or check errors.
