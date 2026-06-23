# ADR-0232: CandidateAttempt Run-Binding Boundary

Status: Proposed

Date: 2026-06-23

Scope: Kernel diagnostics, immutable run-attempt membership, residual-gated practice loop

Depends on:

- ADR-0225 ContractResidual read model
- ADR-0226 Residual-Gated Practice Loop v1
- ADR-0227 ComputeBudgetPolicy envelope
- ADR-0228 GeometricSearchRun envelope
- ADR-0229 Contract/Proof Replay Adapter boundary
- ADR-0230 SealedPracticeTrace boundary
- ADR-0231 First Candidate Operator boundary
- PR #876 missing-role candidate operator shell

## 1. Summary

This ADR defines the immutable boundary that binds one externally constructed
`CandidateAttempt`-compatible candidate to one existing `GeometricSearchRun`
episode.

The current loop can now construct one candidate operator result:

```text
ContractAssessment
-> ContractResidual
-> SearchGateDecision
-> ComputeBudgetDecision
-> GeometricSearchRun
-> CandidateOperatorResult from missing_role_candidate.v1
-> Contract/Proof Replay Adapter
-> SealedPracticeTrace
```

The missing joint is not another operator and not mutable insertion into
`GeometricSearchRun.candidate_attempts`. It is an immutable membership record:

```text
original GeometricSearchRun
+ CandidateOperatorResult
-> CandidateAttemptRunBinding
```

`CandidateAttemptRunBinding` is membership evidence only. It proves that a
candidate attempt is structurally admissible as a member of the identified run
episode. It does not prove correctness, run replay, seal a trace, produce an
answer, select a candidate, rank a candidate, mutate a run, or promote any
finding.

This ADR is documentation only. It adds no code, tests, generated reports,
search execution, replay execution, sealing behavior, serving behavior,
Workbench behavior, or mutation path.

## 2. Why this exists

ADR-0228 made `GeometricSearchRun` immutable. ADR-0231 then authorized the
first narrow candidate operator, `missing_role_candidate.v1`, which emits a
`CandidateOperatorResult` carrying:

```text
candidate_attempt
candidate_reconstruction
attempt_id
attempt_index
candidate_digest
candidate_reconstruction_digest
geometric_search_run_id
```

That result is not yet lawfully part of a replayable run episode. The existing
replay adapter shell validates attempts by membership in
`GeometricSearchRun.candidate_attempts`, while the first candidate operator
correctly does not mutate that tuple. Without a distinct binding boundary, the
next implementation could be tempted to:

```text
mutate GeometricSearchRun.candidate_attempts
smuggle operator output into replay
recompute run IDs after candidate construction
let candidate output masquerade as run evidence
```

All four collapse immutability and replay identity. The intrinsic space is a
relation between two immutable records: the original run envelope and the
operator-produced candidate. The lawful action is not mutation; it is a
content-addressed membership binding whose corrective stages are still replay
and sealing.

## 3. Architectural directions considered

### Option A: external binding record

```text
original GeometricSearchRun
+ CandidateOperatorResult
-> CandidateAttemptRunBinding
```

The original run remains byte-stable. The binding record carries the evidence
that the candidate attempt belongs to the run episode for downstream replay and
trace sealing. This is selected for v1 because it minimizes mutation risk and
does not reuse or alter `run_id` semantics.

### Option B: derived immutable run snapshot

```text
original GeometricSearchRun
+ CandidateOperatorResult
-> derived GeometricSearchRun(candidate_attempts=(attempt,))
```

This keeps Python values immutable but creates immediate ambiguity around
whether the derived snapshot inherits the original `run_id`, receives a new
`run_id`, or receives a continuation identity. The current replay and sealing
tests already fabricate such snapshots for fixtures, but production semantics
are not authorized. Rejected for this ADR.

### Option C: binding record first, future derived snapshot later

The loop may eventually need a derived run snapshot for compatibility, display,
or batch replay. That snapshot should consume the binding record and define a
new continuation identity under a separate ADR/PR. This ADR chooses only the
first half: the external binding record.

## 4. Decision

The selected record name is:

```text
CandidateAttemptRunBinding
```

The v1 policy identity is conceptually:

```text
CANDIDATE_ATTEMPT_RUN_BINDING_POLICY_VERSION = "candidate_attempt_run_binding.v1"
```

The public conceptual outcome is:

```text
CandidateAttemptRunBindingOutcome =
    CandidateAttemptRunBinding | CandidateAttemptRunBindingRefusal
```

The binding layer may decide only:

```text
whether a CandidateOperatorResult can be immutably associated with a specific
GeometricSearchRun episode
```

The binding layer may not decide:

```text
truth
answerability
proof closure
contract closure
serving
promotion
learning
global uniqueness
candidate ranking
candidate selection
repair
mutation
```

A successful binding means only:

```text
this candidate attempt is structurally admissible as a member of this run
episode
```

It does not mean:

```text
the candidate is correct
the candidate should be replayed automatically
the candidate should be sealed automatically
the candidate should be served
the candidate should be promoted
```

Binding produces a `binding_id` only. It does not produce a new `run_id`.
`GeometricSearchRun.run_id` remains stable and continues to identify the
original run envelope. A future derived immutable run snapshot or continuation
identity requires a separate ADR and implementation authorization.

## 5. Position in the loop

The dependency direction remains one-way:

```text
ContractAssessment
-> ContractResidual
-> SearchGateDecision
-> ComputeBudgetDecision
-> GeometricSearchRun
-> CandidateOperatorResult
-> CandidateAttemptRunBinding
-> future Replay Adapter compatibility input
-> future SealedPracticeTrace compatibility input
```

The binding boundary consumes existing records. It does not call upstream
producers and does not call downstream replay or sealing:

```text
project_contract_residuals
decide_search_gate
decide_compute_budget
initialize_geometric_search_run
build_missing_role_candidate
build_replay_adapter_input
classify_replay_result
build_practice_trace_input
seal_practice_trace
determine
```

The binding record is the lawful episode-composition medium. It lets replay and
sealing validate membership later without requiring mutation of
`GeometricSearchRun.candidate_attempts`.

This ADR does not broaden `missing_role_candidate.v1`. The operator remains:

```text
one attempt
one typed cue
no source reread
no search
no replay
no sealing
```

The binding layer consumes an already-produced `CandidateOperatorResult`. It
does not call or schedule the operator.

## 6. Input schema

The conceptual input is:

```python
@dataclass(frozen=True, slots=True)
class CandidateAttemptRunBindingInput:
    input_digest: str
    binding_policy_version: str
    original_run_id: str
    original_run_policy_version: str
    original_run_input_digest: str
    operator_result_id: str
    operator_policy_version: str
    candidate_attempt_id: str
    attempt_index: int
    candidate_digest: str
    candidate_reconstruction_digest: str
    operator_set_id: str
    operator_set_version: str
    budget_id: str
    gate_decision_id: str
    residual_ids: tuple[str, ...]
    problem_frame_digest: str
    original_contract_assessment_id: str
    schema_versions: tuple[tuple[str, str], ...]
    policy_versions: tuple[tuple[str, str], ...]
```

The input is accompanied by immutable values for:

- the original `GeometricSearchRun`;
- the `CandidateOperatorResult`;
- the result's `CandidateAttempt`;
- the result's `CandidateReconstruction`;
- identity-bearing `ComputeBudgetDecision` and `SearchGateDecision` projections
  when needed to verify structural budget and identity chain; and
- the residual and original assessment identities required by the run.

Identities are not substitutes for values that must be structurally checked.
Values are not substitutes for canonical identity. A future implementation may
consume validated projections only when they contain every field needed for the
checks in this ADR.

The input may not contain an answer, selected candidate, rank, score, repair
command, Workbench action, runtime/session state, mutable container, callable,
path, plugin name, model handle, environment value, or filesystem-derived
identity.

## 7. Output schema

The successful conceptual output is:

```python
@dataclass(frozen=True, slots=True)
class CandidateAttemptRunBinding:
    binding_id: str
    binding_policy_version: str
    input_digest: str
    original_run_id: str
    operator_result_id: str
    candidate_attempt_id: str
    attempt_index: int
    candidate_digest: str
    candidate_reconstruction_digest: str
    candidate_attempt_ref: str
    budget_charge: BudgetCharge
    depth: int
    step_index: int
    run_attempt_membership: str
    evidence_spans: tuple[SourceSpan, ...]
    reason_codes: tuple[str, ...]
    explanation: str
```

`candidate_attempt_ref` is a content identity or stable reference for the exact
`CandidateAttempt` value emitted by the operator result. It must not be a
mutable pointer, object address, path, or serialized object dump.

`run_attempt_membership` is a closed semantic tag. V1 should use:

```text
structurally_bound
```

The tag means "the candidate attempt is admissible as a member of this run
episode under `candidate_attempt_run_binding.v1`." It carries no replay,
truth, answer, selection, serving, promotion, or mutation authority.

The output copies the candidate attempt's structural charge fields:

```text
budget_charge
depth
step_index
```

Those copied fields are evidence for budget verification, not new budget
allocation.

## 8. Binding refusal schema

The refusal output is:

```python
@dataclass(frozen=True, slots=True)
class CandidateAttemptRunBindingRefusal:
    binding_refusal_id: str
    binding_policy_version: str
    input_digest: str | None
    original_run_id: str | None
    operator_result_id: str | None
    candidate_attempt_id: str | None
    reason_codes: tuple[str, ...]
    explanation: str
```

Optional identities are populated only when they can be validated without
guessing. Malformed input may therefore produce a refusal with `None`
identities. A refusal is never a partial binding.

No binding dataclass may contain any of these public fields:

```text
answer
final_answer
served_output
proof
verdict
promotion
mutation
teaching_update
pack_update
policy_update
identity_update
workbench_state
runtime_effect
confidence
score
rank
priority
selected
selected_candidate
best
best_candidate
serving_allowed
runnable
```

## 9. CandidateAttempt membership semantics

The binding layer must fail closed unless all of the following are true:

- `original_run` is a `GeometricSearchRun`.
- `candidate_operator_result` is a `CandidateOperatorResult`.
- `candidate_operator_result.geometric_search_run_id == original_run.run_id`.
- `candidate_operator_result.candidate_attempt.attempt_id ==
  candidate_operator_result.attempt_id`.
- `candidate_operator_result.candidate_attempt.candidate_digest ==
  candidate_operator_result.candidate_digest`.
- `candidate_operator_result.candidate_reconstruction.candidate_digest ==
  candidate_operator_result.candidate_digest`.
- `candidate_operator_result.candidate_reconstruction.candidate_reconstruction_digest
  == candidate_operator_result.candidate_reconstruction_digest`.
- `candidate_operator_result.candidate_attempt.replay_status ==
  CandidateReplayStatus.REPLAY_PENDING`.
- `candidate_operator_result.candidate_attempt.replay_blockers == ()`.
- `candidate_operator_result.attempt_index` matches
  `candidate_operator_result.candidate_attempt.attempt_index`.
- `attempt_index` is not already present in
  `original_run.candidate_attempts`.
- `attempt_id` is not already present in `original_run.candidate_attempts`.
- `candidate_digest` is not already present in
  `original_run.candidate_attempts` unless a later ADR explicitly defines
  duplicate-candidate semantics.
- The candidate `budget_charge` fits the remaining run budget.
- The candidate `depth` fits the remaining run depth.
- The candidate `step_index` and step charge fit the remaining run steps.
- `operator_set_id` matches `original_run.operator_set_id`.
- `operator_set_version` matches `original_run.operator_set_version`.
- The operator result input chain binds to the original run, gate, budget,
  residual identities, problem-frame digest, and original assessment identity.
- Evidence spans are valid, exact, ordered, and preserved.
- `schema_versions` and `policy_versions` are unique sorted name/version pairs.

If the original run already has attempts, membership is deterministic:

```text
existing attempts retain their original order
the new binding is admissible only at its declared attempt_index
gaps are allowed only when the declared index is explicitly supported by the
original run's deterministic attempt policy
duplicates by index or attempt_id are refused
duplicates by candidate_digest are refused in v1
```

V1 should be stricter than necessary: if an existing attempt set makes ordering
ambiguous, refuse. Do not infer a "next" position from tuple length unless that
position equals the candidate attempt's declared `attempt_index` and fits every
budget/depth/step rule.

## 10. Budget and run accounting

The binding layer does not allocate budget. It verifies consumption that was
already declared by the candidate attempt.

The future implementation must check:

```text
candidate_attempt.budget_charge.candidates
candidate_attempt.budget_charge.steps
candidate_attempt.depth
candidate_attempt.step_index
```

against:

```text
original_run.budget_consumed
ComputeBudgetDecision limits already embedded in the run
```

The run's copied ceilings are load-bearing:

```text
original_run.budget_consumed.max_candidates
original_run.budget_consumed.max_depth
original_run.budget_consumed.max_steps
original_run.budget_consumed.max_parallelism
```

Required checks:

- `budget_charge.candidates` is exactly the operator-declared charge and is
  positive.
- `budget_charge.steps` is exactly the operator-declared charge and is
  positive.
- `original_run.budget_consumed.candidates_considered +
  budget_charge.candidates <= original_run.budget_consumed.max_candidates`.
- `max(original_run.budget_consumed.depth_reached, candidate_attempt.depth) <=
  original_run.budget_consumed.max_depth`.
- `original_run.budget_consumed.steps_used + budget_charge.steps <=
  original_run.budget_consumed.max_steps`.
- `original_run.budget_consumed.max_parallelism == 1` in v1.
- `candidate_attempt.depth >= 0`.
- `candidate_attempt.step_index >= 0`.

No binding may make budget exhaustion imply correctness. No binding may inflate,
refund, reallocate, or mutate budget. No binding may modify the original
`ComputeBudgetDecision` or `GeometricSearchRun.budget_consumed`.

## 11. Replay adapter implications

The current replay adapter requires an attempt to be present in
`GeometricSearchRun.candidate_attempts`. That check remains correct for derived
run snapshots, but it cannot consume the first candidate operator result
without either mutation or a compatibility boundary.

This ADR authorizes a later compatibility patch, after the binding record
exists, where replay input construction can consume:

```text
original GeometricSearchRun
CandidateAttemptRunBinding
CandidateAttempt
CandidateReconstruction identity
```

rather than requiring the original run to contain the attempt in
`candidate_attempts`.

Replay must validate that:

- `CandidateAttemptRunBinding.original_run_id == GeometricSearchRun.run_id`;
- the binding's `candidate_attempt_id`, `attempt_index`,
  `candidate_digest`, and `candidate_reconstruction_digest` match the supplied
  attempt and reconstruction;
- the binding's operator result identity matches the candidate operator result
  if that result is supplied;
- the original run, binding, attempt, and reconstruction reproduce their
  canonical identities; and
- the binding policy/schema versions are supported.

The replay adapter still may not mutate the original run, mutate the binding,
run search, execute candidate operators, select candidates, seal traces,
produce answers, or serve output.

This ADR does not modify replay adapter code.

## 12. Sealed trace implications

A future sealed trace should bind:

```text
original GeometricSearchRun
CandidateOperatorResult
CandidateAttemptRunBinding
ReplayAdapterResult / ReplayAdapterRefusal
```

A `SealedPracticeTrace` may reference binding IDs as part of `trace_records`
and may add a binding identity sequence only after a separately authorized
implementation PR updates the trace schema.

Sealing must treat the binding as membership evidence only. A sealed trace may
derive an episode disposition from validated replay records, but not from
binding alone. A binding without replay remains pending membership evidence,
not candidate refusal, replay closure, answerability, or promotion.

This ADR does not implement sealing behavior.

## 13. Immutability and run identity

`GeometricSearchRun` remains immutable. The binding layer must not:

- append to `candidate_attempts`;
- replace `candidate_attempts`;
- update `budget_consumed`;
- update `run_disposition`;
- update `exhaustion_code`;
- recompute `run_id`;
- create a shadow run that reuses the original `run_id`; or
- alter any upstream gate, budget, residual, assessment, or operator result.

Binding produces:

```text
binding_id only
```

It does not produce a new `run_id`. The original run identity remains the
identity of the original exploration envelope. The binding identity is the
identity of the membership relation:

```text
membership(original_run_id, operator_result_id, candidate_attempt_id)
```

Any future derived immutable run snapshot must be separately authorized and
must define whether it receives a continuation ID, snapshot ID, or new run ID.

## 14. Evidence-span preservation

The binding layer must:

```text
preserve ordered evidence spans
preserve duplicate spans
not synthesize spans
not dedupe spans
not sort spans independently
fail closed on malformed spans
```

The binding's `evidence_spans` are copied from the candidate operator result
and must match the candidate attempt and candidate reconstruction spans exactly
when those records expose spans. If multiple upstream records expose evidence
spans, the future implementation must either require exact equality across the
operator result, attempt, and reconstruction, or refuse with an explicit reason
code. V1 should not merge span streams.

Evidence-span order participates in binding identity. Reordering spans changes
`binding_id`. Duplicate spans remain separate entries.

## 15. Determinism and canonical identity

All load-bearing IDs use canonical JSON:

```python
json.dumps(
    payload,
    ensure_ascii=False,
    sort_keys=True,
    separators=(",", ":"),
)
```

The serialized string is encoded as UTF-8 and hashed with SHA-256. The digest
is the full lowercase hexadecimal encoding.

Required IDs:

```text
CandidateAttemptRunBindingInput.input_digest
CandidateAttemptRunBinding.binding_id
CandidateAttemptRunBindingRefusal.binding_refusal_id
```

`CandidateAttemptRunBindingInput.input_digest` hashes the structural input
fields other than `input_digest` itself:

```text
binding_policy_version
original_run_id
original_run_policy_version
original_run_input_digest
operator_result_id
operator_policy_version
candidate_attempt_id
attempt_index
candidate_digest
candidate_reconstruction_digest
operator_set_id
operator_set_version
budget_id
gate_decision_id
ordered residual_ids
problem_frame_digest
original_contract_assessment_id
canonical schema_versions
canonical policy_versions
```

`binding_id` self-seals the structural binding payload with `binding_id`
blanked. It includes:

```text
binding_policy_version
input_digest
original_run_id
operator_result_id
candidate_attempt_id
attempt_index
candidate_digest
candidate_reconstruction_digest
candidate_attempt_ref
budget_charge
depth
step_index
run_attempt_membership
ordered evidence_spans
ordered reason_codes
```

`binding_refusal_id` self-seals the refusal payload with
`binding_refusal_id` blanked. It includes:

```text
binding_policy_version
input_digest or null
original_run_id or null
operator_result_id or null
candidate_attempt_id or null
ordered reason_codes
```

IDs must exclude:

```text
explanation
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
thread/process identifiers
filesystem order
hash-map iteration order unless canonicalized
user identity
model identity
machine identity
```

Changing `explanation` must not change any binding ID.

## 16. Authority boundary

`CandidateAttemptRunBinding` is membership evidence only.

It may decide:

```text
structural admissibility of one operator-produced candidate attempt as a member
of one existing run episode
```

It has no authority to:

```text
generate candidates
execute operators
execute search
repair source records
run contract replay
run proof replay
seal traces
produce answers
serve output
rank candidates
select candidates
mutate the original run
mutate budgets
mutate gates
mutate residuals
mutate operator results
promote findings
edit packs
edit teaching data
edit policy
edit identity
edit eval reports
write Workbench state
write files/artifacts
```

No binding result changes durable epistemic standing. Source kind
(`operator`, `binding`, `search`, `replay`, or `practice`) grants no promotion
authority.

## 17. Forbidden imports/calls/effects

The future implementation may import only:

- standard-library immutable value, enum, canonical JSON, and SHA-256
  facilities;
- `SourceSpan`;
- `GeometricSearchRun`, `CandidateAttempt`, `BudgetCharge`, and
  `CandidateReplayStatus` as value types;
- `CandidateOperatorResult` and `CandidateReconstruction` as value types;
- `ComputeBudgetDecision` and `SearchGateDecision` as value types when needed
  for identity checks; and
- local run-binding immutable value types and static policy constants.

The future implementation must not import or call:

```text
runtime
serving
Workbench
teaching/proposal mutation
pack/policy/identity mutation
eval/report mutation
Vault/recall mutation
filesystem writes
network I/O
subprocess
time/datetime/random/uuid/env/hostname/path identity
dynamic import/plugin discovery
external model/tool invocation
LLM generation
embedding/ANN/cosine/semantic-rank modules
determine answer production
candidate operator execution
contract/proof replay execution
sealed trace writing
answer realization
repair
```

It also must not call upstream or downstream producer functions:

```text
project_contract_residuals
decide_search_gate
decide_compute_budget
initialize_geometric_search_run
build_missing_role_candidate
build_replay_adapter_input
classify_replay_result
build_practice_trace_input
seal_practice_trace
determine
```

The binding layer consumes existing records only. No reverse dependency from
assessment, residual, gate, budget, search-run, candidate-operator,
replay-adapter, or sealed-trace modules into the binding module is authorized
unless a later PR explicitly names it.

## 18. Failure modes and fail-closed behavior

The future implementation must fail closed as follows:

| Failure | Required outcome |
|---|---|
| Malformed binding input | `CandidateAttemptRunBindingRefusal` |
| Unsupported binding policy | `CandidateAttemptRunBindingRefusal` |
| Candidate result does not bind to `run_id` | `CandidateAttemptRunBindingRefusal` |
| Candidate attempt does not match operator result | `CandidateAttemptRunBindingRefusal` |
| Candidate reconstruction does not match operator result | `CandidateAttemptRunBindingRefusal` |
| Attempt index duplicate | `CandidateAttemptRunBindingRefusal` |
| Attempt ID duplicate | `CandidateAttemptRunBindingRefusal` |
| Candidate digest duplicate in v1 | `CandidateAttemptRunBindingRefusal` |
| Budget charge exceeds remaining candidates | `CandidateAttemptRunBindingRefusal` |
| Budget charge exceeds remaining steps | `CandidateAttemptRunBindingRefusal` |
| Candidate depth exceeds remaining depth | `CandidateAttemptRunBindingRefusal` |
| Operator set mismatch | `CandidateAttemptRunBindingRefusal` |
| Operator result input chain does not bind to run/gate/budget/residual identities | `CandidateAttemptRunBindingRefusal` |
| Candidate replay status is not pending | `CandidateAttemptRunBindingRefusal` |
| Replay blockers are present | `CandidateAttemptRunBindingRefusal` |
| Malformed evidence spans | `CandidateAttemptRunBindingRefusal` |
| Duplicate or unsorted schema/policy version pairs | `CandidateAttemptRunBindingRefusal` |

No failure may become:

```text
partial binding
best guess
soft proof
replay closure
sealed trace
answer
rank
priority
serving fallback
promotion
teaching mutation
Unknown == False
```

An unbindable candidate preserves the original run and original refusal. It
does not consume additional budget and does not mutate any input record.

## 19. Test obligations for future implementation PR

The future implementation PR must add executing tests that meaningfully fail
under the prohibited states:

1. Public API exports are exact.
2. Valid original run plus candidate operator result produces deterministic
   binding.
3. Binding does not mutate original `GeometricSearchRun`.
4. Binding ID is deterministic and explanation-excluded.
5. Candidate result/run ID mismatch refuses.
6. Candidate attempt/result ID mismatch refuses.
7. Candidate attempt candidate digest mismatch refuses.
8. Candidate reconstruction candidate digest mismatch refuses.
9. Candidate reconstruction digest mismatch refuses.
10. Candidate replay status not pending refuses.
11. Replay blockers present refuses.
12. Duplicate attempt index in original run refuses.
13. Duplicate attempt ID in original run refuses.
14. Budget charge beyond remaining candidates/steps/depth refuses.
15. Operator-set mismatch refuses.
16. Evidence spans preserve order and duplicates.
17. Malformed evidence spans refuse.
18. Binding result contains no answer/proof/verdict/serving/promotion/rank/score
    fields.
19. Binding does not execute candidate operators.
20. Binding does not execute replay or sealing.
21. Binding does not call upstream producer functions.
22. No filesystem/network/time/random/env/UUID/hostname/path identity.
23. Static guards block forbidden imports/calls.
24. No reverse dependencies from upstream modules unless explicitly intended.
25. Focused tests and smoke lane pass.

Additional required controls:

- tests independently recompute input, binding, and refusal hashes rather than
  calling the implementation's private hash helper;
- static coupling tests parse the binding module and enforce the allowed
  import/call surface;
- tests prove the original run tuple and budget-consumed values are unchanged
  before and after binding;
- tests prove a binding alone cannot be consumed as replay closure or a sealed
  trace; and
- tests prove duplicate candidate digests refuse in v1.

## 20. Authorized next PR

This ADR authorizes exactly one next implementation PR:

```text
feat(kernel): implement inert run-attempt binding shell
```

Scope of the next PR:

```text
add run-attempt binding dataclasses/enums/helpers
consume GeometricSearchRun and CandidateOperatorResult
validate identity chain and budget/membership constraints
emit CandidateAttemptRunBinding or CandidateAttemptRunBindingRefusal
produce deterministic binding IDs
tests only for boundary behavior
```

The next PR explicitly excludes:

```text
candidate operator execution
search execution
run mutation
derived run snapshot
contract/proof replay execution
sealed trace execution
answer production
Workbench
runtime/serving
teaching/proposal/report/eval mutation
pack/policy/identity mutation
promotion
filesystem persistence
artifact writing
new proof engine
```

No other implementation PR is authorized by this ADR. A replay adapter overload
or compatibility patch, sealed-trace schema widening, derived immutable run
snapshot, multi-attempt search, candidate ranking/selection, answer production,
serving, Workbench display, and promotion each remain separately gated.
