# ADR-0233: Bound Practice Episode Sealing

**Status:** Proposed

**Date:** 2026-06-23

**Scope:** Kernel diagnostics, immutable bound practice evidence, residual-gated practice loop

**Depends on:**

- ADR-0230 SealedPracticeTrace boundary
- ADR-0231 First Candidate Operator boundary
- ADR-0232 CandidateAttempt Run-Binding boundary
- PR #878 inert run-attempt binding shell
- PR #879 bound replay adapter input

## 1. Summary

This ADR authorizes bound practice episode sealing: the bridge from
`CandidateAttemptRunBinding` and bound replay evidence into
`SealedPracticeTrace`.

The bound spine is:

```text
GeometricSearchRun
-> CandidateOperatorResult
-> CandidateAttemptRunBinding
-> ReplayAdapterInput
-> ReplayAdapterResult | ReplayAdapterRefusal
-> SealedPracticeTrace
```

`CandidateAttemptRunBinding` is **membership evidence only**. It is not truth,
not proof, not replay success, and not serving authority.

Sealed traces must preserve binding evidence explicitly through:

```text
candidate_attempt_binding_ids
```

The bound path must **not** mutate `GeometricSearchRun.candidate_attempts`.

The bound path must **not** call candidate operators, search, replay input
builders, replay classifiers, or binding producers. It consumes only
already-built upstream records:

```text
GeometricSearchRun
CandidateAttemptRunBinding
CandidateOperatorResult
ReplayAdapterResult | ReplayAdapterRefusal
```

The bound path emits only:

```text
PracticeTraceInput | PracticeTraceRefusal
SealedPracticeTrace | PracticeTraceRefusal
```

This boundary is diagnostic and inert. It does not answer, rank, select, serve,
promote, repair, teach, mutate packs, mutate policy, mutate identity, or write
artifacts.

## 2. Decision

Extend `PracticeTraceInput` and `SealedPracticeTrace` with
`candidate_attempt_binding_ids`.

Add:

```text
build_bound_practice_trace_input(...)
seal_bound_practice_trace(...)
```

Legacy `build_practice_trace_input(...)` and `seal_practice_trace(...)` remain
unchanged in authority and continue to use `candidate_attempt_binding_ids=()`
for run-embedded attempts.

Canonical trace digests include binding IDs in:

```text
input_digest
trace_id
upstream_identity_chain
```

Identity chain order:

```text
problem_frame_digest
original_contract_assessment_id
residual_ids
search_gate_decision_id
compute_budget_id
geometric_search_run_id
candidate_attempt_ids
candidate_attempt_binding_ids
replay_result_ids
replay_refusal_ids
```

## 3. Authorized next PR

This ADR authorizes exactly one implementation PR:

```text
docs+kernel: support bound practice episode sealing
```

That PR may add only:

- binding-aware trace input construction
- binding-aware trace sealing
- tests for the bound episode path
- this ADR

It explicitly excludes candidate operators, Workbench, serving, ranking,
promotion, teaching mutation, pack/policy/identity mutation, runtime
integration, and artifact writing.