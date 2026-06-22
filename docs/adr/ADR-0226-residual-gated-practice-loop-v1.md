# ADR-0226: Residual-Gated Practice Loop v1

**Status:** Proposed

**Date:** 2026-06-22

**Scope:** Kernel diagnostics, bounded contemplation, sealed practice, and read-only trace display

**Depends on:** ADR-0225 and PR #862

## 1. Summary

Residual-Gated Practice Loop v1 is the first proposed integrated,
deterministic improvement loop over CORE's existing problem-frame and contract
machinery:

```text
failed/refused contract
→ typed residual
→ eligibility gate
→ bounded compute
→ deterministic candidate exploration
→ contract replay
→ sealed practice trace
→ reviewed promotion only
```

The loop turns a refusal into inspectable, bounded practice evidence. It does
not turn a refusal into permission to guess. A candidate can produce an answer
only after the existing contract authority is replayed and the applicable proof
obligations close. If no candidate closes, the original refusal remains in
force.

This ADR defines the whole capability tranche and the authority boundaries
between its future components. It implements none of them.

## 2. Why this exists

CORE already has the machinery that this loop must connect:

- proposal-first construction hypotheses;
- exact `ProblemFrame` facts, bindings, and evidence spans;
- organ-specific `ContractAssessment` closure and refusal;
- the diagnostic-only `ContractResidual` projection implemented by PR #862;
- typed refusal and proof-gated answer disciplines;
- deterministic trace and replay conventions;
- sealed practice and reliability-ledger concepts;
- read-only contemplation miners that emit speculative, review-required
  findings;
- reviewed teaching and proposal mutation paths; and
- Workbench as an operator/auditor surface over persisted evidence.

None of those concepts is introduced by this ADR. The missing capability is a
safe composition law between them.

Without an explicit composition law, a future search implementation could
accidentally treat a residual as a repair command, let a budget grant become an
admission decision, promote an explored candidate without replay, or give a UI
execution authority. The purpose of v1 is to prevent those authority collapses
before implementation begins.

The intrinsic state space is not a bag of retries. It is a typed obstruction
space: `ContractResidual` identifies the exact axis on which a proposed
construction failed to close. The corresponding action is a bounded,
deterministic exploration over eligible candidate reconstructions. Its
conjugate is contract and proof replay. Only that corrective replay may remove
the obstruction.

## 3. Architectural directions considered

### 3.1 Monolithic practice controller

A single service could inspect residuals, choose a budget, search, validate,
and emit a result. This is operationally compact but structurally unsafe: the
same component would possess diagnostic, resource, exploration, and promotion
authority. A local implementation shortcut could silently convert “worth
examining” into “solved.” Rejected.

### 3.2 Practice-ledger-first orchestration

Exploration could begin in a sealed lane and be classified afterward. This
would preserve evidence, but it would allocate compute and create candidates
before residual eligibility was established. The gate would become
retrospective telemetry rather than an authority boundary. Rejected.

### 3.3 Workbench-orchestrated exploration

Workbench could expose residuals and directly launch or tune exploration. This
would make a display surface part of the execution and policy path, contrary to
its operator/auditor posture. Rejected for v1.

### 3.4 Typed evidence pipeline

Each stage receives a narrow immutable input, emits a deterministic evidence
record, and has no authority belonging to a later stage. Eligibility precedes
budget; budget precedes exploration; exploration precedes replay; replay
precedes any answer; sealing precedes review; review precedes durable
promotion. Selected.

This direction makes illegal authority transitions visible in type and module
boundaries. Downstream evidence may explain an upstream decision, but it may
not rewrite that decision.

## 4. Capability target

The target milestone is an end-to-end diagnostic and sealed-practice proof over
selected refused GSM8K-style/kernel problems.

For each case, CORE can show:

```text
- exact problem frame
- exact bindings
- exact contract assessment
- exact residuals
- whether bounded contemplation is allowed
- what budget would be available
- what candidates were considered
- why each candidate failed or closed
- whether a proof-gated answer was produced
- deterministic replay trace
- wrong_ids == []
```

The milestone is not “search finds more answers.” It is “every answer or
refusal is reconstructible from exact evidence, and no explored candidate can
bypass the same contracts that govern the original assessment.” Increased
closure is desirable only under the invariant that silent wrong answers remain
zero.

## 5. Mastery mapping

| Mastery dimension | Residual-Gated Practice Loop responsibility |
|---|---|
| **Articulation** | Present the frame, bindings, claims, residuals, disclosures, candidate dispositions, and trace explanation without collapsing raw evidence into the user-facing answer. |
| **Reasoning** | Preserve `ContractAssessment`, proof gates, entailment, and explicit refusal. `Unknown` remains unknown and is never coerced to `False`. |
| **Contemplation** | Admit only gated residual classes to bounded, deterministic candidate exploration. Contemplation proposes reconstructions; it does not assert conclusions. |
| **Practice** | Run in sealed, replayable lanes. Candidate and outcome artifacts remain provisional; ratified packs, policy, identity, and serving do not mutate without review. |
| **Problem solving** | Produce an answer only when a candidate reconstructs the required evidence, replays to contract closure, and satisfies the applicable proof obligations. Otherwise refuse. |

These dimensions are views of one evidence flow, not independent subsystems.
The same trace must explain both the forward exploration and its corrective
replay.

## 6. End-to-end flow

```text
ProblemFrame
  ↓
ContractAssessment ── runnable ───────────────────────────────→ existing path
  │ refused
  ↓
ContractResidual[]
  ↓
SearchGateDecision ── denied ────────────────────────────────→ refusal + trace
  │ allowed
  ↓
ComputeBudgetPolicy
  ↓
GeometricSearchRun
  ↓ candidates in deterministic order
ContractAssessment replay + applicable proof replay
  ├─ no closed candidate ────────────────────────────────────→ refusal + trace
  └─ exactly proven candidate ───────────────────────────────→ proof-gated result
  ↓
sealed practice trace
  ↓
review-required artifact, if any
  ↓
existing reviewed promotion path only

Workbench ← read-only projection of the sealed trace
```

The arrow into Workbench is deliberately lateral. Workbench observes the loop;
it is not a stage that advances it.

## 7. Components and boundaries

### A. `ContractResidual` — existing

PR #862 implemented `ContractResidual` as a deterministic, read-only projection
over refused `ContractAssessment` records.

It preserves existing blocker codes and exact evidence spans. It does not
assess contracts, declare truth, decide search eligibility, allocate compute,
repair a frame, derive an answer, mutate artifacts, or affect serving.

This ADR consumes that boundary unchanged.

### B. `SearchGateDecision` — future

`SearchGateDecision` is a read-only eligibility decision over one complete
residual context. It answers only whether a future bounded exploration run may
be considered.

Its minimum conceptual output is:

```text
decision_id
residual_ids
disposition: allowed | denied
reason_codes
policy_version
input_digest
```

The exact schema belongs to its implementation ADR/PR. Whatever schema is
chosen must be frozen, deterministic, and explicit about denial.

`SearchGateDecision`:

- does not search;
- does not allocate a budget;
- does not repair bindings, spans, relations, or targets;
- does not mutate a `ProblemFrame` or `ContractAssessment`;
- does not make a residual true, false, solved, or runnable;
- does not produce an answer;
- does not mutate teaching, policy, packs, identity, reports, or evals; and
- does not affect serving.

Eligibility is intentionally narrower than residual existence. In particular,
an unclassified fallback residual is not implicitly searchable.

### C. `ComputeBudgetPolicy` — future

`ComputeBudgetPolicy` produces a deterministic budget envelope only for an
allowed gate decision. It cannot be invoked as an alternate gate.

A future envelope must use structural units, such as maximum candidate count,
maximum expansion depth, maximum deterministic operator applications, or
maximum proof replays. Wall-clock duration alone is not a replay-stable budget.

The policy must provide:

- a stable policy/version identity;
- the allowed gate decision digest;
- explicit non-negative limits;
- a canonical budget digest; and
- a fail-closed disposition for unsupported or malformed input.

It must not contain hidden expansion, stochastic allocation, adaptive
unbounded loops, environment-dependent limits, or an override that permits a
denied residual to proceed.

Budget is a resource ceiling, not evidence, proof, or authority.

### D. `GeometricSearchRun` — future

`GeometricSearchRun` is the deterministic candidate-exploration envelope. It is
functional, bounded, and replayable:

```text
(exact input state, allowed gate, budget, operator set, versions)
  → ordered candidate attempts + run outcome
```

The word “geometric” denotes exploration in CORE's structured relational and
operator space. It does not authorize approximate nearest-neighbor retrieval,
cosine ranking, stochastic sampling, opaque model fallback, or unbounded graph
growth.

The run must:

- consume immutable input evidence;
- use an explicitly versioned, closed operator set;
- order candidates with stable deterministic tie-breaks;
- charge every expansion and replay against the budget envelope;
- preserve failed candidates and their blocker/proof dispositions;
- perform no pack, policy, identity, Vault, report, eval, or serving mutation;
- avoid mutation of shared input state during exploration; and
- return exhaustion as a typed refused outcome.

Exploration may reconstruct candidate frames or bindings in an isolated value
space. It may not promote any candidate. A candidate is merely an object for
the existing assessment and proof authorities to judge.

### E. Contract and proof replay — existing authorities, future adapter

Every candidate considered potentially closing must be replayed through the
same organ-specific `ContractAssessment` authority that judged the original
frame. Applicable proof/verifier obligations must then run over the candidate's
exact evidence.

Replay has three permitted dispositions:

```text
contract_refused
contract_closed_but_proof_refused
contract_and_proof_closed
```

Only `contract_and_proof_closed` may support answer production. A boolean,
score, heuristic rank, absence of a blocker, or exhausted budget is not a proof.
If candidates disagree, uniqueness or the relevant organ's existing
disagreement rule must close before an answer can be produced; otherwise the
result remains refused.

Replay must not patch the original assessment. It produces a new assessment
over an explicitly identified candidate reconstruction while retaining the
original assessment as immutable evidence.

### F. Sealed Practice Integration — future

Sealed practice captures the complete input, decisions, attempts, replays, and
outcome of the loop. The seal is tamper evidence and replay identity; it is not
proof that a candidate is correct and is not promotion authority.

A v1 trace must be sufficient to reconstruct:

- source/case identity without weakening existing sealed-data rules;
- exact `ProblemFrame`, binding, and proposal references;
- original `ContractAssessment` and projected residuals;
- gate decision and policy version;
- budget envelope and consumption;
- ordered candidate attempts and operator provenance;
- per-candidate contract and proof replay dispositions;
- selected proof-gated result or final refusal;
- canonical input, stage, and trace hashes; and
- schema and implementation versions required for deterministic replay.

Candidate failures are evidence and must not be discarded. Hashing must use a
canonical representation with stable ordering and no timestamp, random ID,
wall-clock result, memory address, or environment-dependent field in the
load-bearing payload.

The integration may emit a review-required artifact through an existing
proposal/review path. It must not mutate ratified packs, policy, identity,
serving, or durable epistemic standing. Practice evidence remains provisional
until an existing reviewed or certificate-bearing promotion authority accepts
it.

### G. Workbench Trace Display — future

Workbench v1 is a read-only projection of the sealed practice trace. It shows:

- frame and exact source spans;
- proposals and bindings;
- original assessment and residuals;
- gate disposition and reasons;
- budget grant and consumption;
- candidate ordering and per-candidate failures/closure;
- contract/proof replay hashes;
- final proof-gated answer or refusal; and
- missing-evidence or replay-divergence states.

Workbench must read a backend-owned persisted projection. It must not infer
missing stage evidence in the browser, rerun search to fill gaps, edit an
operator, tune a budget, repair a candidate, ratify an artifact, or mutate
runtime state in v1. Missing evidence is displayed as missing evidence, not as
a synthesized successful stage.

## 8. Authority boundaries

The following rules are normative:

1. `ContractAssessment` is the sole runnable/refused authority.
2. `ContractResidual` is explanation and projection only.
3. `SearchGateDecision` cannot make a residual true, false, solved, or
   runnable.
4. `ComputeBudgetPolicy` cannot authorize exploration unless SearchGate allowed
   it.
5. `GeometricSearchRun` cannot promote results or change durable standing.
6. Only contract replay plus the applicable proof replay can close a candidate
   for answer production.
7. `Unknown` remains unknown, never `False` by absence or exhaustion.
8. A denied or failed search preserves refusal unless proof closes a candidate.
9. A sealed trace proves trace integrity, not semantic truth.
10. Review may promote only through existing reviewed/certified paths; source
    kind (`search`, `practice`, or `miner`) grants no epistemic authority.
11. Workbench is a read surface, not an execution or mutation authority in v1.
12. No serving behavior changes in v1.

| Component | May decide | Must not decide |
|---|---|---|
| `ContractAssessment` | runnable/refused for its organ | search budget, promotion, review |
| `ContractResidual` | nothing; projection only | truth, eligibility, repair, serving |
| `SearchGateDecision` | eligibility for bounded exploration | runnable, solved, budget size, truth |
| `ComputeBudgetPolicy` | deterministic resource ceiling | eligibility, closure, promotion |
| `GeometricSearchRun` | ordered attempts within the envelope | truth, promotion, serving |
| Contract/proof replay | candidate closure under existing obligations | durable promotion |
| Sealed practice | trace integrity and replay identity | truth, ratification |
| Review path | disposition under existing review authority | retroactive fabrication of evidence |
| Workbench | display of persisted evidence | execution, repair, operator mutation |

## 9. Determinism, replay, and failure semantics

Given byte-equivalent input evidence, component versions, policy, operator set,
and budget, the loop must reproduce:

- the same residual ordering;
- the same gate decision and reasons;
- the same budget envelope;
- the same candidate sequence;
- the same per-candidate assessment and proof dispositions;
- the same selected result or refusal; and
- the same canonical trace hash.

Replay divergence is a failed equivalence check, not ignorable telemetry.
Malformed input, unknown policy versions, digest mismatch, unsupported residual
kinds, budget overrun, candidate disagreement, missing proof, or trace-seal
failure must fail closed with a typed reason.

The loop contains no retry-until-success behavior. Re-execution under identical
inputs is replay and must be identical. A new policy, operator set, or budget is
a new explicitly versioned run with a new trace identity.

## 10. Preservation of CORE invariants

This tranche is constrained by the existing invariants:

- **Field closure:** no component may weaken `versor_condition(F) < 1e-6` or
  introduce repair/normalization outside approved construction/algebra
  boundaries.
- **Exact geometry:** no cosine, ANN, HNSW, approximate recall, or stochastic
  candidate selection.
- **Wrong-zero:** proof/refusal gates remain load-bearing and evaluated lanes
  must retain `wrong_ids == []`.
- **Open-world truthfulness:** `Unknown` is not `False`; search exhaustion is
  not refutation.
- **Reviewed mutation:** candidate discovery, practice traces, and miner output
  remain provisional and cannot mutate durable packs, policy, identity, or
  epistemic standing without the existing review/certificate authority.
- **Serving isolation:** the diagnostic/practice tranche is off-serving until a
  separate ratified serving decision proves the required parity and safety
  obligations.
- **Evidence fidelity:** exact source spans and original assessments survive
  unchanged through the trace.
- **Replay:** load-bearing hashes use canonical, deterministic payloads.

## 11. PR ladder

The intended follow-on sequence is:

```text
#864 — ratify this ADR
#865 — implement diagnostic-only SearchGateDecision
#866 — implement deterministic ComputeBudgetPolicy envelope
#867 — implement inert GeometricSearchRun envelope
#868 — wire sealed practice trace capture
#869 — Workbench read-only trace display
#870 — evaluate on selected refused GSM8K/kernel examples
```

These numbers are provisional. Review may split, combine, reorder, or renumber
them if evidence reveals a safer boundary. Each PR remains independently
reviewed and must not borrow authority from a later rung.

In particular, #865 must not begin before this ADR is ratified, and no rung may
silently include serving integration or durable promotion.

## 12. Non-goals

This ADR:

- does not implement code;
- does not implement `SearchGateDecision`;
- does not implement `ComputeBudgetPolicy`;
- does not implement `GeometricSearchRun`;
- does not implement or modify Workbench;
- does not touch serving or runtime behavior;
- does not mutate teaching, proposal, report, eval, or sealed-practice
  artifacts;
- does not broaden `state_change.transition`;
- does not add a new construction family or derivation organ;
- does not permit stochastic fallback, opaque model calls, approximate recall,
  or unbounded exploration;
- does not authorize unreviewed learning or promotion;
- does not redefine `ContractAssessment` or `ContractResidual`; and
- does not claim a capability gain from documentation alone.

## 13. Acceptance criteria

This proposal is complete when:

1. The PR is docs-only and changes only this ADR.
2. Existing CORE machinery is distinguished explicitly from future adapters.
3. The complete tranche is defined, not only the next implementation PR.
4. `ContractAssessment` remains the sole runnable/refused authority.
5. Eligibility, budget, exploration, replay, sealing, review, and display have
   separate non-overlapping authority boundaries.
6. Failed exploration remains refusal unless contract and proof replay close a
   candidate.
7. `Unknown` is never coerced to `False`.
8. The wrong=0 doctrine and `wrong_ids == []` target are explicit.
9. Durable mutation remains reviewed or certificate-bearing through existing
   paths.
10. Replay inputs, ordering, failure semantics, and trace identity are
    deterministic.
11. No hidden normalization, stochastic fallback, approximate recall,
    unreviewed mutation, or serving change is authorized.
12. `git diff --check` passes and the changed-file surface is exactly:

    ```text
    docs/adr/ADR-0226-residual-gated-practice-loop-v1.md
    ```

No code tests are required for this documentation-only proposal beyond the
repository bootstrap smoke baseline and diff validation.
