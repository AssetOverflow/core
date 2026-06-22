# ADR-0228: Inert GeometricSearchRun Envelope

**Status:** Proposed

**Date:** 2026-06-22

**Scope:** Kernel diagnostics, bounded candidate exploration envelope, residual-gated practice loop

**Depends on:**

- ADR-0225 ContractResidual read model
- ADR-0226 Residual-Gated Practice Loop v1
- ADR-0227 ComputeBudgetPolicy envelope
- PR #868 ComputeBudgetDecision

## 1. Summary

`GeometricSearchRun` is an inert diagnostic/practice envelope. It records an
ordered sequence of candidate attempts inside a pre-granted deterministic
budget. It is functional, bounded, deterministic, replayable, non-serving,
non-mutating, and non-authoritative for truth.

The envelope consumes exact identities for the problem frame, the refused
contract assessment, its residuals, an allowed search-gate decision, an allowed
compute-budget decision, a closed operator set, and the governing schema and
policy versions. It emits only content-addressed diagnostic evidence:

```text
run_id
run_policy_version
input_digest
budget_id
gate_decision_id
ordered CandidateAttempt records
budget_consumed
run_disposition
explanation
```

It does not emit or imply:

```text
answer
proof
verdict
promotion
mutation
serving_allowed
runnable
truth
score
confidence
rank
priority
```

This ADR defines schemas and boundaries only. It implements no search, operator,
repair, replay adapter, trace seal, serving behavior, or mutation path.

## 2. Why this exists

ADR-0226 places deterministic candidate exploration after eligibility and
budget, but before contract and proof replay. ADR-0227 makes the budget a hard,
non-authoritative resource ceiling. A distinct search-run envelope is needed to
preserve those boundaries before candidate exploration exists.

The intrinsic space is a finite operator graph over immutable, identified
evidence. A candidate attempt is a path element in that graph, not a proposed
answer. The forward operator is bounded exploration; its required conjugate is
later contract and proof replay. Exploration may expose a candidate, but only
replay may classify whether the candidate closes the existing obligations.

Without an inert envelope, a future implementation could accidentally search
without a valid budget, order candidates by non-replayable preference, discard
failed attempts, treat exhaustion as correctness, or let search repair source
evidence by authority. This ADR makes those states structurally inadmissible.

## 3. Architectural directions considered

### 3.1 Monolithic search controller

A controller could gate, allocate, explore, replay, and select in one service.
This collapses resource, exploration, and proof authority. A local success
condition could silently become an answer-production path. Rejected.

### 3.2 Free-form attempt log

An implementation could append arbitrary attempt dictionaries until a limit is
reached. This preserves some telemetry, but it cannot make budget overruns,
unstable ordering, incomplete identity, or authoritative fields unrepresentable.
Rejected.

### 3.3 Immutable run plus typed initialization refusal

A discriminated `SearchRunOutcome` separates failed initialization from a valid
`GeometricSearchRun`. The valid run carries exact input identity, a closed
operator-set identity, ordered attempts, structural budget accounting, and a
closed disposition. Replay remains a later authority. Selected.

This direction is the smallest boundary that preserves diagnostic usefulness
without authorizing exploration implementation.

## 4. Decision

The v1 policy identity is conceptually:

```text
GEOMETRIC_SEARCH_RUN_POLICY_VERSION = "geometric_search_run.v1"
```

The architecture defines:

```text
SearchRunOutcome = SearchRunRefusal | GeometricSearchRun
```

`SearchRunRefusal` represents fail-closed initialization. It may carry the
dispositions `not_started`, `blocked_by_budget`, `blocked_by_gate`, or
`invalid_input`, plus exact available input identities and typed reason codes.
It is not a run, has no candidate attempts, and consumes no budget.

`GeometricSearchRun` may be constructed only after every initialization
obligation in this ADR succeeds. Once constructed, it is an immutable value.
It may record ordered diagnostic attempts, but it cannot search freely, repair
by authority, produce an answer, mutate an artifact, or bypass contract/proof
replay.

The v1 operator set may be empty or placeholder-only. This ADR does not
authorize a candidate-producing operator. The only implementation authorized
by Section 18 is an inert trace shell that can produce a deterministic
zero-attempt terminal run for an empty operator set.

## 5. Envelope position in the loop

The dependency and authority direction is one-way:

```text
ContractAssessment
→ ContractResidual
→ SearchGateDecision
→ ComputeBudgetDecision
→ GeometricSearchRun
→ future Contract/Proof Replay Adapter
→ future SealedPracticeTrace
→ future Workbench read-only projection
```

There is no reverse dependency. `GeometricSearchRun` consumes already-produced
records; it does not call the assessment, residual projection, gate, or budget
producers. Downstream replay or display cannot rewrite the original run.

## 6. Inputs

The conceptual input is an immutable `GeometricSearchInput`:

```python
@dataclass(frozen=True, slots=True)
class GeometricSearchInput:
    problem_frame_digest: str
    contract_assessment_id: str
    residual_ids: tuple[str, ...]
    gate_decision_id: str
    gate_policy_version: str
    gate_input_digest: str
    budget_id: str
    budget_policy_version: str
    operator_set_id: str
    operator_set_version: str
    run_policy_version: str
    schema_version: str
```

The identifiers have load-bearing meaning:

- `problem_frame_digest` identifies the exact canonical `ProblemFrame`,
  including ordered facts, bindings, proposals, targets, hazards, and exact
  source spans required by the frame schema. A case label or raw filename is
  not a substitute.
- `contract_assessment_id` identifies the exact refused
  `ContractAssessment`. The assessment must remain immutable and refused.
- `residual_ids` is the complete canonical order consumed by the gate. No
  residual may be added, removed, deduplicated, or reordered by the run.
- `gate_decision_id`, `gate_policy_version`, and `gate_input_digest` identify
  the exact allowed `SearchGateDecision` and its residual context.
- `budget_id` and `budget_policy_version` identify the exact allowed
  `ComputeBudgetDecision` and its structural ceilings.
- `operator_set_id` and `operator_set_version` identify an explicit, closed,
  ordered allowlist. Discovery by import scan, filesystem enumeration, plugin
  registry, entry point, or environment configuration is forbidden.
- `run_policy_version` and `schema_version` make changes to construction,
  ordering, charging, or serialization explicit.

The run input is valid only when all identities are present, full lowercase
SHA-256 fields have exactly 64 hexadecimal characters where a digest is
required, the residual sequence matches the gate sequence exactly, the gate is
`ELIGIBLE`, the budget is `BUDGET_ALLOWED`, and the gate/budget cross-identities
and canonical hashes reproduce byte-for-byte.

`input_digest` is the SHA-256 digest of the canonical JSON object containing
exactly the fields above in their declared sequence values. It identifies the
run input, not a semantic truth claim.

## 7. Outputs

The conceptual initialized-run schema is:

```python
@dataclass(frozen=True, slots=True)
class GeometricSearchRun:
    run_id: str
    run_policy_version: str
    schema_version: str
    problem_frame_digest: str
    contract_assessment_id: str
    residual_ids: tuple[str, ...]
    gate_decision_id: str
    budget_id: str
    operator_set_id: str
    operator_set_version: str
    input_digest: str
    candidate_attempts: tuple[CandidateAttempt, ...]
    budget_consumed: BudgetConsumed
    run_disposition: RunDisposition
    exhaustion_code: RunExhaustionCode | None
    explanation: str
```

`SearchRunOutcome` is the public conceptual result. It is a discriminated union
so a blocked or invalid initialization cannot masquerade as a valid empty run.

The refusal branch is also immutable and diagnostic-only:

```python
@dataclass(frozen=True, slots=True)
class SearchRunRefusal:
    outcome_id: str
    run_policy_version: str
    input_digest: str | None
    gate_decision_id: str | None
    budget_id: str | None
    run_disposition: RunDisposition
    reason_codes: tuple[str, ...]
    explanation: str
```

`outcome_id` uses the same canonical hashing rules as the run and excludes
`explanation`. A refusal never receives a `run_id` because initialization did
not produce a run.

`RunDisposition` is a closed vocabulary:

```text
not_started
blocked_by_budget
blocked_by_gate
invalid_input
exhausted_no_candidate
candidate_replay_pending
candidate_replay_closed
candidate_replay_refused
```

The admissible type-state pairs are:

| Outcome type | Permitted dispositions |
|---|---|
| `SearchRunRefusal` | `not_started`, `blocked_by_budget`, `blocked_by_gate`, `invalid_input` |
| `GeometricSearchRun` | `exhausted_no_candidate`, `candidate_replay_pending`, `candidate_replay_closed`, `candidate_replay_refused` |

`candidate_replay_closed` does not mean the run produced a proof-gated answer.
It is reserved for a future immutable projection that records that an
independent, authorized replay adapter reported closure. This ADR and the next
authorized PR cannot emit it.

`RunExhaustionCode` is also closed:

```text
operator_set_empty
operator_space_depleted
max_candidates_reached
max_depth_reached
max_steps_reached
```

An exhausted run carries exactly one exhaustion code. Non-exhausted
dispositions carry `None`.

The run schema contains no answer, proof, verdict, promotion, mutation,
serving, runnable, truth, score, confidence, rank, or priority field.

## 8. CandidateAttempt record

The conceptual attempt schema is:

```python
@dataclass(frozen=True, slots=True)
class CandidateAttempt:
    attempt_id: str
    attempt_index: int
    parent_attempt_id: str | None
    operator_id: str
    operator_version: str
    input_digest: str
    candidate_digest: str
    budget_charge: BudgetCharge
    depth: int
    step_index: int
    replay_status: ReplayStatus
    replay_blockers: tuple[str, ...]
    evidence_spans: tuple[SourceSpan, ...]
    explanation: str
```

`ReplayStatus` is closed:

```text
replay_pending
replay_closed
replay_refused
```

For this ADR and its authorized next PR, replay is placeholder-only. A future
candidate-producing implementation must initialize every attempt as
`replay_pending` with no invented closure. Only the separately authorized
contract/proof replay adapter may report `replay_closed` or `replay_refused`.

`BudgetCharge` is a structural record:

```python
@dataclass(frozen=True, slots=True)
class BudgetCharge:
    candidates: int  # exactly 1 for every CandidateAttempt
    steps: int       # positive deterministic operator/replay applications
```

Each attempt is diagnostic evidence. It is not a proposal artifact, proof,
answer, ranking entry, confidence estimate, or mutation command. Its source
spans remain in supplied order and preserve duplicates. The run may not widen,
merge, synthesize, or deduplicate spans.

Each future operator must declare, in the closed operator-set manifest:

```text
operator_id
operator_version
allowed residual kinds
input obligations
output candidate shape
budget charge
deterministic ordering key
forbidden side effects
replay obligations
```

Operator declarations are constraints, not authority. No operator is
authorized by this ADR.

## 9. Budget consumption

No `GeometricSearchRun` may initialize unless
`ComputeBudgetDecision.status == BUDGET_ALLOWED`.

Initialization must fail closed when any of the following holds:

- the budget is blocked, zero, or unassessable;
- `max_candidates == 0` or `max_steps == 0`;
- any structural limit is negative;
- `max_parallelism != 1` in v1;
- `budget_id` does not reproduce from its canonical payload;
- the budget's `gate_decision_id` does not equal the supplied gate identity;
- the budget's gate policy version or gate input digest does not equal the
  supplied gate record;
- the gate's residual identities do not equal the supplied residual identities;
- the gate is not `ELIGIBLE`;
- the budget or run policy version is unsupported; or
- any required identity is malformed or absent.

The conceptual accounting record is:

```python
@dataclass(frozen=True, slots=True)
class BudgetConsumed:
    candidates_considered: int
    max_candidates: int
    depth_reached: int
    max_depth: int
    steps_used: int
    max_steps: int
    parallelism_used: int
    max_parallelism: int
    exhausted: bool
```

The `max_*` values are copied exactly from the validated budget decision. The
consumed values are non-negative and satisfy:

```text
candidates_considered == len(candidate_attempts)
candidates_considered == sum(attempt.budget_charge.candidates)
candidates_considered <= max_candidates
depth_reached == 0 when there are no attempts
depth_reached == max(attempt.depth) otherwise
depth_reached <= max_depth
steps_used == sum(attempt.budget_charge.steps)
steps_used <= max_steps
parallelism_used in {0, 1}
parallelism_used <= max_parallelism == 1
```

Every candidate attempt consumes exactly one candidate unit and a positive,
predeclared step charge. Before an attempt is materialized, its complete charge
must fit. Partial charging, negative credits, refunds, hidden retries, adaptive
budget increases, and “try until solved” are forbidden.

`BudgetConsumed.exhausted` is true only when a structural budget ceiling
prevents the next otherwise-admissible attempt. An empty or depleted operator
space uses `exhausted_no_candidate` with the corresponding operator exhaustion
code, but does not falsely claim that budget was consumed.

No v1 accounting field depends on wall-clock time. `max_wallclock_ms`, if
present on the upstream budget record, is diagnostic metadata and neither
authorizes execution nor participates in charging.

## 10. Determinism and identity

All load-bearing IDs use canonical JSON serialized with:

```python
json.dumps(
    payload,
    sort_keys=True,
    separators=(",", ":"),
    ensure_ascii=False,
).encode("utf-8")
```

The digest is the full lowercase SHA-256 hexadecimal encoding. NaN, Infinity,
floats, implicit object serialization, and locale-dependent values are
forbidden in hashed payloads.

The identities are layered:

- `operator_set_id` hashes the ordered operator manifest and its version.
- `input_digest` hashes the exact upstream identities and schema/policy
  versions described in Section 6.
- `candidate_digest` hashes the complete canonical candidate representation.
- `attempt_id` hashes `attempt_index`, `parent_attempt_id`, operator identity,
  `input_digest`, `candidate_digest`, `budget_charge`, `depth`, `step_index`,
  replay status/blockers, and exact evidence spans.
- `run_id` self-seals the complete structural `GeometricSearchRun` payload with
  `run_id` blanked. It includes ordered attempts, budget consumption,
  disposition, and exhaustion code.

`explanation` is excluded from every ID. IDs must also exclude:

```text
wall-clock time
timestamps
random values
UUIDs
environment variables
hostname
OS details
CI metadata
file paths
generated prose
memory addresses
thread or process identifiers
```

Candidate order is assigned before execution and is deterministic. Permitted
ordering inputs are:

```text
attempt_index
closed operator-set order
parent attempt order
canonical candidate digest
canonical residual/order context
```

Forbidden ordering inputs are:

```text
model preference
score
confidence
cosine similarity
nearest-neighbor rank
wall-clock completion order
thread scheduling order
filesystem order
hash-map iteration order unless canonicalized
randomness
```

Duplicate evidence spans are preserved. Re-execution with byte-equivalent
inputs, versions, operator manifest, and budget must reproduce every identity,
attempt position, charge, disposition, and output byte-for-byte.

## 11. Parallelism semantics

V1 is serial. `max_parallelism` must equal `1`; `parallelism_used` is `0` for a
zero-attempt run and `1` after the first attempt. A value greater than `1`
causes initialization refusal, even if the host could execute concurrently.

No parallel candidate execution is authorized in this tranche. A future ADR
may define deterministic parallel batches only if it assigns attempt indices,
parents, operator order, and complete budget reservations before execution;
merges by those canonical positions rather than completion order; preserves the
same output as serial execution; and proves that cancellation or scheduling
cannot change the trace. That future design is not implemented or implied here.

## 12. Replay boundary

Exploration and replay are distinct authority domains.
`GeometricSearchRun` may eventually enumerate candidates, but it cannot declare
one correct. The run does not invoke `ContractAssessment`, a verifier, a proof
engine, or an answer realizer.

Only a later, separately authorized contract/proof replay adapter may classify
a candidate as closed or refused. It must replay the same organ-specific
contract obligations and every applicable proof obligation over the candidate's
exact identified evidence. Its report is external evidence; it does not mutate
the original run or assessment.

No candidate closes by:

- ranking;
- absence of blockers;
- successful generation;
- semantic proximity;
- budget exhaustion;
- operator exhaustion; or
- any path lacking `ContractAssessment` replay and applicable proof replay.

For #869, `replay_status` is only a placeholder field. There is no replay
adapter, replay execution, sealed trace, or answer-production path in this PR.
The dispositions `candidate_replay_closed` and `candidate_replay_refused` are
reserved until that adapter is separately authorized.

## 13. Exhaustion and refusal semantics

Exhaustion is a typed diagnostic outcome. It is never hidden by retry, fallback,
selection, or prose.

If the operator space is empty, the future inert shell produces a deterministic
initialized run with:

```text
candidate_attempts == ()
budget_consumed.candidates_considered == 0
budget_consumed.steps_used == 0
budget_consumed.exhausted == false
run_disposition == exhausted_no_candidate
exhaustion_code == operator_set_empty
```

If a structural ceiling prevents the next otherwise-admissible attempt, the run
records the corresponding budget exhaustion code and
`budget_consumed.exhausted == true`.

When all available budget or operator space is exhausted without externally
reported replay closure:

- the original contract refusal remains in force;
- every failed or pending attempt remains visible in canonical order;
- exhaustion is recorded explicitly;
- no answer is produced; and
- no state or artifact is mutated.

Exhaustion cannot be converted into a best guess, partial answer, soft proof,
confidence score, serving fallback, proposal promotion, negative verdict, or
`Unknown == False` conclusion.

Initialization refusal also preserves the original refusal. It creates no
`GeometricSearchRun`, performs no operator work, and consumes no budget.

## 14. Authority boundary

`GeometricSearchRun` has no authority to:

- assess contracts;
- project residuals;
- decide search eligibility;
- allocate or widen compute budget;
- repair source evidence, spans, bindings, relations, targets, or frames;
- prove candidate correctness;
- produce or select an answer;
- mark a case runnable;
- serve output;
- mutate teaching, packs, policy, identity, Vault, reports, or evals;
- write sealed practice traces;
- promote findings or epistemic standing; or
- change Workbench state.

The term “geometric” means bounded deterministic exploration in CORE's
structured relational/operator space. It does not mean approximate
nearest-neighbor retrieval, cosine similarity ranking, embedding fallback,
semantic guessing, unbounded graph search, sampling, LLM scratchpad expansion,
best-of-N answer voting, or self-consistency voting.

The original `ProblemFrame`, `ContractAssessment`, residuals, gate, and budget
are immutable input evidence. A candidate is a separate identified value, never
an in-place repair.

## 15. Forbidden imports/calls/effects

A future inert implementation may depend only on:

- standard-library value, enum, canonical JSON, and SHA-256 facilities;
- `SourceSpan` and identity-bearing `ProblemFrame` schema values;
- the `ContractAssessment` record type, but not assessment functions;
- `ContractResidual` record types, but not projection functions;
- `SearchGateDecision` and `SearchGateStatus`, but not gate producers;
- `ComputeBudgetDecision` and `ComputeBudgetStatus`, but not budget producers;
  and
- local search-envelope value types and a closed operator-manifest schema.

Reverse imports from assessment, residual, gate, or budget modules into a
future search-run module are forbidden.

The module may not import or call runtime, serving, Workbench, teaching,
proposal, pack, Vault, recall, eval, report, calibration, field, algebra,
network, filesystem, subprocess, clock, random, UUID, environment, dynamic
import, external-model, or plugin-discovery facilities.

In particular, no operator may:

- mutate any upstream record or shared state;
- write, edit, move, delete, seal, or promote artifacts;
- call runtime or serving paths;
- call external tools or models;
- perform filesystem or network I/O;
- spawn processes or threads;
- read clocks, environment variables, host metadata, or filesystem order; or
- use randomness, sampling, approximate recall, or model preference.

## 16. Failure modes and fail-closed behavior

| Failure | Required outcome |
|---|---|
| Gate is blocked, ineligible, or unassessable | `SearchRunRefusal(blocked_by_gate)`; no run |
| Budget is blocked, zero, or unassessable | `SearchRunRefusal(blocked_by_budget)`; no run |
| Gate/budget identity or digest mismatch | `SearchRunRefusal(invalid_input)`; no run |
| Problem-frame, assessment, or residual identity mismatch | `SearchRunRefusal(invalid_input)`; no run |
| Unsupported schema, gate, budget, operator-set, or run policy version | `SearchRunRefusal(invalid_input)`; no run |
| Negative structural limit | `SearchRunRefusal(invalid_input)`; no run |
| `max_parallelism != 1` in v1 | `SearchRunRefusal(invalid_input)`; no run |
| Empty operator set | Deterministic zero-attempt `exhausted_no_candidate` run |
| Next charge would exceed a hard ceiling | Stop before the attempt; preserve prior attempts; typed exhaustion |
| Candidate digest or operator declaration cannot be reproduced | Stop fail-closed; no closure or answer |
| Replay is missing | `candidate_replay_pending`; original refusal remains |
| Future replay refuses all candidates | `candidate_replay_refused`; original refusal remains |
| Future replay reports closure | Record external closure only; the run still emits no answer |

No failure may be converted to a default candidate, best effort, silent skip,
retry loop, partial charge, or successful disposition.

## 17. Test obligations for future implementation PR

The later implementation PR must add executing tests that meaningfully fail
under each prohibited state:

1. Public API exports are exact and inert.
2. Initialization refuses blocked, zero, and unassessable budgets.
3. Initialization refuses gate/budget identity and digest mismatches.
4. Unsupported policy and schema versions fail closed.
5. Negative structural limits fail closed.
6. `max_parallelism > 1` fails closed in v1.
7. An empty operator set produces deterministic exhaustion with no attempts and
   no false budget consumption.
8. Candidate attempts are ordered deterministically.
9. Every candidate attempt consumes exactly one candidate unit and a positive
   deterministic step charge.
10. Budget exhaustion preserves all prior failed or pending attempts.
11. Run, attempt, and refusal schemas expose no answer, proof, verdict,
    promotion, serving, runnable, score, confidence, rank, or priority fields.
12. Canonical `input_digest`, `attempt_id`, and `run_id` exclude prose, time,
    environment, path, host, process, and random values.
13. Duplicate evidence spans and their order are preserved.
14. No runtime, serving, Workbench, teaching, proposal, pack, Vault, eval, or
    report mutation is reachable.
15. No filesystem, network, clock, random, environment, dynamic import,
    subprocess, or external-model use is reachable.
16. No reverse dependency exists from budget, gate, residual, or assessment
    modules into the search-run module.
17. Contract/proof replay remains placeholder-only until the separately
    authorized replay-adapter PR.

Tests must independently recompute canonical hashes rather than calling the
implementation's private hash helper. Structural coupling tests must parse the
implementation and enforce the allowed dependency surface. The focused tests
and the repository smoke lane must pass.

## 18. Authorized next PR

This ADR authorizes exactly one next implementation PR:

```text
feat(kernel): implement inert GeometricSearchRun trace shell
```

That PR may only:

- add inert `GeometricSearchRun`, `SearchRunOutcome`, `SearchRunRefusal`,
  `CandidateAttempt`, budget-accounting, and closed-enum value types/helpers;
- consume an already-produced `ComputeBudgetDecision` and the exact upstream
  identities;
- validate gate/budget identity and canonical digests;
- accept an explicit empty or placeholder-only closed operator set;
- produce a deterministic empty `exhausted_no_candidate` run for the v1 empty
  operator set;
- record the exact budget ceiling with zero consumption and an empty attempt
  list;
- emit canonical `input_digest` and `run_id`; and
- add tests only for envelope behavior and architectural isolation.

That PR explicitly excludes:

```text
candidate generation
operator implementation
repair
contract/proof replay adapter
sealed practice trace
Workbench
runtime/serving
teaching/proposal/report/eval mutation
answer production
```

No other implementation PR is authorized by this ADR. Candidate-producing
operators, replay, sealing, display, evaluation, serving, and promotion each
require their own reviewed authorization.
