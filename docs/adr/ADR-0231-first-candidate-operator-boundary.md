# ADR-0231: First Candidate Operator Boundary

**Status:** Proposed

**Date:** 2026-06-23

**Scope:** Kernel diagnostics, candidate attempt construction, residual-gated practice loop

**Depends on:**

- ADR-0225 ContractResidual read model
- ADR-0226 Residual-Gated Practice Loop v1
- ADR-0227 ComputeBudgetPolicy envelope
- ADR-0228 GeometricSearchRun envelope
- ADR-0229 Contract/Proof Replay Adapter boundary
- ADR-0230 SealedPracticeTrace boundary
- PR #874 inert SealedPracticeTrace shell

## 1. Summary

This ADR defines the first deterministic candidate-operator boundary for the
Residual-Gated Practice Loop. The boundary authorizes one narrow operator to
produce one diagnostic candidate attempt from one eligible typed residual
context after the already-ratified diagnostic chain has produced gate, budget,
run, replay, and sealing evidence.

The current spine is:

```text
ContractAssessment
-> ContractResidual
-> SearchGateDecision
-> ComputeBudgetDecision
-> GeometricSearchRun
-> Contract/Proof Replay Adapter
-> SealedPracticeTrace
```

The new boundary sits between an initialized `GeometricSearchRun` identity and
the Contract/Proof Replay Adapter:

```text
GeometricSearchRun identity
-> CandidateOperator
-> CandidateAttempt-compatible candidate reconstruction
-> Contract/Proof Replay Adapter
-> SealedPracticeTrace
```

The boundary is intentionally not open-ended search. It permits:

```text
one deterministic operator
one eligible residual context
one attempt index
one candidate reconstruction
one diagnostic result or refusal
```

It does not permit:

```text
truth
answer production
repair
ranking
selection
serving
mutation
promotion
Workbench behavior
stochastic generation
open-ended search
```

The load-bearing invariant is:

```text
Candidate operators propose candidate attempts only.

A candidate operator has no truth authority.
A candidate operator has no answer authority.
A candidate operator has no repair authority.
A candidate operator has no selection/ranking authority.
A candidate operator has no mutation/promotion authority.

Every produced candidate must be replay-classified and sealed before it can
become evidence for any future reviewed promotion or display.
```

This ADR is documentation only. It adds no candidate-operator implementation,
no search execution, no replay execution, no sealed-trace execution, no
Workbench behavior, no runtime/serving behavior, and no mutation path.

## 2. Why this exists

ADR-0228 deliberately left `GeometricSearchRun` inert. Its v1 implementation can
validate gate and budget evidence, record a closed operator-set identity, and
emit an empty `exhausted_no_candidate` run when the operator set is empty.
ADR-0229 and ADR-0230 then define how any future candidate must be replay-classified
and sealed.

The missing bridge is the first lawful forward operator:

```text
typed residual obstruction
-> deterministic candidate reconstruction
-> replay and sealing obligations
```

Without a distinct candidate-operator boundary, a future implementation could
collapse residual diagnosis into repair, treat budget as permission to search
until success, let candidate construction masquerade as contract closure, or
write a candidate directly into serving, Workbench, teaching, packs, reports, or
policy.

The intrinsic state space is a typed residual field with one bounded forward
operator and a required corrective conjugate. The operator may propose one
candidate reconstruction. Contract/proof replay and sealing remain downstream
corrective boundaries.

## 3. Architectural directions considered

### 3.1 Open operator search

A general search engine could traverse a table of operators, expand multiple
candidates, adapt based on intermediate failures, and rank or select a best
candidate. This would collapse the first operator boundary into an unbounded
search policy and would make ordering, budget use, and authority difficult to
audit. Rejected.

### 3.2 Repair-in-place role binding

The operator could patch the original `ProblemFrame`, original
`ContractAssessment`, residuals, gate, budget, or run. This would destroy
upstream immutability and make candidate construction indistinguishable from
repair authority. Rejected.

### 3.3 Replay-integrated candidate producer

The operator could construct a candidate and immediately run contract/proof
replay, returning only replayed successes. This would combine proposal and
correction in one module and allow candidate-generation failure to masquerade
as semantic refusal. Rejected.

### 3.4 Immutable single-operator reconstruction boundary

The operator consumes already-produced residual, gate, budget, and run
identities; validates a closed operator-set identity; emits either one
candidate reconstruction/result or one refusal; and grants no downstream
authority. Replay, sealing, display, promotion, serving, and mutation remain
separate boundaries. Selected.

This selected shape makes illegal authority transitions visible in the output
type and keeps the first candidate-producing PR small enough to test
deterministically.

## 4. Decision

The v1 policy identity is conceptually:

```text
CANDIDATE_OPERATOR_POLICY_VERSION = "candidate_operator.v1"
```

The v1 operator-set version is conceptually:

```text
CANDIDATE_OPERATOR_SET_VERSION = "candidate_operators.v1"
```

The public conceptual outcome is:

```text
CandidateOperatorOutcome = CandidateOperatorResult | CandidateOperatorRefusal
```

`CandidateOperatorResult` exists only when one deterministic candidate
reconstruction was lawfully produced from an eligible residual under the closed
operator policy, matching gate, matching budget, and matching run identity.

`CandidateOperatorRefusal` exists when the operator cannot lawfully produce a
candidate because input, policy, residual kind, residual code, gate, budget,
run, evidence-span, or operator-set validation failed. A refusal is not a
partial candidate and must not masquerade as a replay result.

The operator may decide only:

```text
whether one deterministic candidate reconstruction can be produced from an
eligible residual under a bounded run/budget/operator policy
```

It may not decide:

```text
truth
answerability
proof closure
serving
promotion
learning
global uniqueness
candidate selection
ranking
fallback repair
mutation
```

Candidate closure remains exclusively downstream:

```text
CandidateAttempt
-> Contract/Proof Replay Adapter
-> SealedPracticeTrace
-> future read-only display / reviewed promotion path
```

## 5. Position in the loop

Dependency and authority remain one-way:

```text
ContractAssessment
-> ContractResidual
-> SearchGateDecision
-> ComputeBudgetDecision
-> GeometricSearchRun
-> CandidateOperator
-> CandidateAttempt-compatible reconstruction
-> Contract/Proof Replay Adapter
-> SealedPracticeTrace
-> future Workbench read-only projection
-> future reviewed promotion path
```

There is no reverse dependency. In particular:

- the operator does not create, mutate, or replace a `GeometricSearchRun`;
- residual, gate, budget, run, replay-adapter, and sealed-trace modules do not
  gain imports from this operator boundary unless a later implementation PR
  explicitly authorizes that direction;
- the operator emits candidate-attempt evidence only, not replay evidence;
- the replay adapter validates the candidate independently before calling any
  contract/proof authority; and
- the sealed trace validates replay/run/attempt identity before any future
  evidence can be displayed or reviewed.

The fact that this ADR follows the sealed-trace PR sequence does not place the
runtime candidate operator after `SealedPracticeTrace`. It defines the next
architectural boundary after the sealed-trace shell exists, while the operator's
runtime position remains upstream of replay and sealing.

## 6. First operator selection

The first authorized operator is:

```text
operator_family = "residual_missing_role"
operator_name = "missing_role_candidate"
operator_version = "missing_role_candidate.v1"
```

The operator is selected because the repo already has the following closed
vocabulary:

```text
ResidualKind.MISSING_ROLE -> "missing_role"
SearchGate reason_code -> "eligible_missing_role"
ComputeBudget reason_code -> "budget_allowed_missing_role"
```

V1 further narrows the operator to the smallest safe shell:

```text
allowed_residual_kinds = ("missing_role",)
allowed_candidate_organs = ("unary_delta_transition",)
allowed_residual_codes = ("direction_unbound",)
max_attempts_per_run = 1
budget_charge = BudgetCharge(candidates=1, steps=1)
depth = 1
serial only
```

This is intentionally narrower than all missing-role cases. The selected
residual code, `direction_unbound`, can be constrained to an organ-specific
typed rule: the operator may emit a candidate only when the supplied immutable
`ProblemFrame` or validated projection already contains exactly one
`GroundedUnaryDeltaCue` whose typed `direction` value and exact cue span are
available and whose span is already justified by residual/problem-frame
evidence. The operator may then propose a role-binding delta from that existing
typed cue into the missing direction role.

If the typed cue is absent, ambiguous, not source-grounded, not already covered
by lawful evidence spans, or inconsistent with the residual context, the
operator returns `CandidateOperatorRefusal`. It must not read source text again,
infer a direction from prose, synthesize a cue, repair a relation, or search for
alternative bindings.

Other `ResidualKind.MISSING_ROLE` residual codes remain refusals until
separately authorized. Other candidate organs remain refusals until separately
authorized. This preserves the first implementation PR as a small deterministic
shell rather than a general role-filling engine.

## 7. Inputs

### 7.1 CandidateOperatorPolicy

The conceptual policy schema is:

```python
@dataclass(frozen=True, slots=True)
class CandidateOperatorPolicy:
    operator_policy_version: str
    operator_family: str
    operator_name: str
    operator_version: str
    allowed_residual_kinds: tuple[str, ...]
    allowed_candidate_organs: tuple[str, ...]
    max_attempts_per_run: int
    determinism_requirements: tuple[str, ...]
    forbidden_authority_paths: tuple[str, ...]
```

An implementation may add policy fields only if they are deterministic, static,
and part of the canonical operator-set table. For the selected first operator,
the closed policy should additionally carry the residual-code constraint and
fixed budget charge:

```text
allowed_residual_codes = ("direction_unbound",)
budget_charge = {"candidates": 1, "steps": 1}
depth = 1
max_parallelism = 1
```

### 7.2 CandidateOperatorInput

The conceptual operator input is:

```python
@dataclass(frozen=True, slots=True)
class CandidateOperatorInput:
    input_digest: str
    operator_policy_version: str
    operator_name: str
    operator_version: str
    problem_frame_digest: str
    original_contract_assessment_id: str
    residual_id: str
    residual_kind: str
    search_gate_decision_id: str
    compute_budget_id: str
    geometric_search_run_id: str
    operator_set_id: str
    operator_set_version: str
    attempt_index: int
    schema_versions: tuple[tuple[str, str], ...]
    policy_versions: tuple[tuple[str, str], ...]
```

The input is accompanied by immutable values or validated identity-bearing
projections for:

- the original `ProblemFrame`;
- the original refused `ContractAssessment`;
- the selected `ContractResidual`;
- the `SearchGateDecision`;
- the `ComputeBudgetDecision`;
- the `GeometricSearchRun` or run identity required by the current shell; and
- the closed operator-set table.

Identities alone are not enough when the operator must inspect typed state.
Typed state alone is not enough when identities must bind the replay chain. The
implementation must have enough immutable content to recompute the digests it
depends on and enough typed content to apply the deterministic operator rule.

The input cannot contain an answer, preferred candidate, ranked list, repair
command, Workbench action, mutation target, hidden source text, callable, model
handle, path, plugin name, environment value, or runtime/session state.

### 7.3 Required preconditions

Before constructing a candidate, the operator must validate:

1. `operator_policy_version == "candidate_operator.v1"`.
2. `operator_name == "missing_role_candidate"`.
3. `operator_version == "missing_role_candidate.v1"`.
4. `residual_kind == "missing_role"`.
5. `candidate_organ == "unary_delta_transition"` on the residual/gate chain.
6. `residual_code == "direction_unbound"` for v1.
7. `SearchGateDecision.status == SearchGateStatus.ELIGIBLE`.
8. `SearchGateDecision.reason_code == "eligible_missing_role"`.
9. `ComputeBudgetDecision.status == ComputeBudgetStatus.BUDGET_ALLOWED`.
10. `ComputeBudgetDecision.reason_code == "budget_allowed_missing_role"`.
11. `ComputeBudgetDecision.gate_decision_id == SearchGateDecision.decision_id`.
12. `GeometricSearchRun.gate_decision_id == SearchGateDecision.decision_id`.
13. `GeometricSearchRun.budget_id == ComputeBudgetDecision.budget_id`.
14. `GeometricSearchRun.operator_set_id == operator_set_id`.
15. `GeometricSearchRun.operator_set_version == operator_set_version`.
16. `attempt_index >= 0`.
17. `attempt_index < ComputeBudgetDecision.max_candidates`.
18. `attempt_index < CandidateOperatorPolicy.max_attempts_per_run`.
19. The fixed operator charge fits within `max_candidates`, `max_depth`, and
    `max_steps`.
20. `ComputeBudgetDecision.max_parallelism == 1`.
21. Evidence spans are valid, exact, ordered, and already justified by the
    residual/problem-frame records.
22. `schema_versions` and `policy_versions` contain unique names in ascending
    lexical order.

Any failed validation returns `CandidateOperatorRefusal`; no partial candidate
record is emitted.

## 8. Outputs

### 8.1 CandidateReconstruction

The conceptual candidate reconstruction is:

```python
@dataclass(frozen=True, slots=True)
class CandidateReconstruction:
    candidate_digest: str
    candidate_reconstruction_digest: str
    candidate_organ: str
    candidate_payload: object
    evidence_spans: tuple[SourceSpan, ...]
    operator_name: str
    operator_version: str
    operator_provenance: tuple[tuple[str, str], ...]
    source_residual_id: str
    problem_frame_digest: str
    original_contract_assessment_id: str
```

For `missing_role_candidate.v1`, `candidate_payload` is an organ-specific,
deterministic reconstruction envelope. It may identify a single role-binding
delta such as:

```text
kind = "role_binding_delta"
candidate_organ = "unary_delta_transition"
relation_type = "state_change.unary_delta"
role = "direction"
source = "GroundedUnaryDeltaCue.direction"
```

This example is a schema obligation, not permission to invent a new parser or
generic patch engine. The payload must be sufficient for downstream replay to
reconstruct one exact candidate value or to refuse. It must not mutate the
original `ProblemFrame` or rewrite source evidence.

### 8.2 CandidateOperatorResult

The conceptual operator result is:

```python
@dataclass(frozen=True, slots=True)
class CandidateOperatorResult:
    operator_result_id: str
    operator_policy_version: str
    input_digest: str
    geometric_search_run_id: str
    attempt_id: str
    attempt_index: int
    candidate_digest: str
    candidate_reconstruction_digest: str
    candidate_organ: str
    operator_name: str
    operator_version: str
    reason_codes: tuple[str, ...]
    evidence_spans: tuple[SourceSpan, ...]
    explanation: str
```

The result is diagnostic evidence that candidate construction happened. It is
not replay evidence, proof evidence, answer evidence, or promotion evidence.

### 8.3 CandidateOperatorRefusal

The conceptual refusal is:

```python
@dataclass(frozen=True, slots=True)
class CandidateOperatorRefusal:
    operator_refusal_id: str
    operator_policy_version: str
    input_digest: str | None
    geometric_search_run_id: str | None
    residual_id: str | None
    operator_name: str
    reason_codes: tuple[str, ...]
    explanation: str
```

Malformed or unauthorized candidate construction must return a refusal, not a
partial candidate. Optional identities are populated only when they can be
validated without guessing.

### 8.4 Forbidden output fields

No candidate-operator output may contain:

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

Generated prose is explanatory only and excluded from identity.

## 9. Candidate identity and reconstruction identity

The identity split from ADR-0229 is preserved:

```text
candidate_digest
-> canonical digest of candidate content to be replayed

candidate_reconstruction_digest
-> canonical digest of the full reconstruction envelope:
   run_id
   attempt_id
   attempt_index
   operator_set_id
   operator_name
   operator_version
   residual identity
   candidate_digest
   evidence-span identity
   schema/policy versions
```

`candidate_digest` hashes candidate content only. For v1 this includes, at
minimum:

```text
original problem_frame_digest
candidate organ
organ-specific candidate payload
exact ordered evidence spans
```

`candidate_digest` excludes:

```text
attempt_id
attempt_index
operator_set_id
operator_name
operator_version
explanation
runtime identity
```

`candidate_reconstruction_digest` self-seals the complete reconstruction
envelope with its own digest field blanked. It includes the validated
`candidate_digest`, run/attempt/operator provenance, residual identity, exact
evidence-span identity, and schema/policy versions. It excludes `explanation`.

The two digests must not be collapsed. A future implementation must include a
test proving they differ for a valid candidate reconstruction.

## 10. Operator-set identity

`operator_set_id` is the canonical digest of the closed allowed operator table.
The table must include, for every operator row:

```text
operator_name
operator_version
allowed_residual_kinds
allowed_candidate_organs
max_attempts_per_run
schema_versions
policy_versions
```

The selected v1 table contains exactly one row:

| operator_name | operator_version | allowed_residual_kinds | allowed_candidate_organs | max_attempts_per_run |
|---|---|---|---|---|
| `missing_role_candidate` | `missing_role_candidate.v1` | `missing_role` | `unary_delta_transition` | `1` |

The table may carry additional static constraints such as:

```text
allowed_residual_codes = ("direction_unbound",)
budget_charge = {"candidates": 1, "steps": 1}
depth = 1
max_parallelism = 1
```

Those constraints participate in `operator_set_id` if present in the
implementation. The table must be static, closed, deterministic, and versioned.

Forbidden operator availability mechanisms:

```text
dynamic plugin discovery
filesystem scanning
entry-point enumeration
environment-variable configuration
model/runtime-dependent availability
session-memory availability
network discovery
Workbench configuration
```

Changing the table changes `operator_set_id` and therefore creates a distinct
run/reconstruction identity. No hidden fallback operator is permitted.

## 11. Budget and run constraints

The candidate operator obeys the already-assigned `ComputeBudgetDecision`. It
does not allocate budget.

The operator may execute only when:

```text
ComputeBudgetDecision.status == BUDGET_ALLOWED
SearchGateDecision.status == ELIGIBLE
attempt_index < ComputeBudgetDecision.max_candidates
attempt_index < CandidateOperatorPolicy.max_attempts_per_run
fixed candidate charge fits max_candidates/max_depth/max_steps
ComputeBudgetDecision.max_parallelism == 1
GeometricSearchRun.gate_decision_id == SearchGateDecision.decision_id
GeometricSearchRun.budget_id == ComputeBudgetDecision.budget_id
GeometricSearchRun.operator_set_id == operator_set_id
```

Budget exhaustion never implies correctness. Operator exhaustion never implies
closure. A budget refusal, zero budget, unassessable budget, run mismatch, or
attempt index beyond the ceiling returns `CandidateOperatorRefusal`.

The operator is not open-ended search. It must not:

```text
loop over arbitrary operators
recursively expand candidates
execute in parallel
adaptively choose operators
score operators
rank candidates
select candidates
mutate search trees
invoke fallback operators
retry until success
refund or inflate budget
```

Any future multi-operator, multi-attempt, recursive, parallel, or adaptive
search requires a separate ADR.

## 12. Replay and sealing obligations

Every produced candidate must be routed through:

```text
Contract/Proof Replay Adapter
-> SealedPracticeTrace
```

A `CandidateOperatorResult` alone is not evidence of correctness. It cannot be
displayed as a solution, promoted, served, or used for learning unless a later
reviewed path consumes a sealed trace that validates the full chain:

```text
original refused ContractAssessment
-> ContractResidual
-> SearchGateDecision
-> ComputeBudgetDecision
-> GeometricSearchRun
-> CandidateAttempt-compatible record
-> CandidateReconstruction
-> ReplayAdapterResult / ReplayAdapterRefusal
-> SealedPracticeTrace
```

The operator may not run contract replay, proof replay, replay-adapter
classification, or sealed-trace construction. It may only emit the diagnostic
candidate attempt evidence that those downstream stages must validate.

## 13. Evidence-span preservation

The operator must:

```text
preserve ordered evidence spans
preserve duplicate spans
use only source spans already justified by residual/problem-frame records
not synthesize spans
not dedupe spans
not sort spans independently
fail closed on malformed spans
```

For `missing_role_candidate.v1`, candidate evidence spans are copied from the
residual/problem-frame/cue evidence that authorizes the role-binding delta. If
the required span is absent or malformed, the operator refuses.

Evidence spans that participate in `candidate_digest`,
`candidate_reconstruction_digest`, `attempt_id`, or `operator_result_id` must
change those identities when reordered. Duplicate spans remain distinct entries
when upstream records preserved them as distinct entries.

The operator must not reread raw source text to recover missing provenance.

## 14. Determinism and canonical identity

All load-bearing identities use canonical JSON:

```python
json.dumps(
    payload,
    ensure_ascii=False,
    sort_keys=True,
    separators=(",", ":"),
)
```

The serialized string is encoded as UTF-8 and hashed with SHA-256. The digest is
the full lowercase hexadecimal encoding.

The following IDs are load-bearing:

```text
operator_set_id
CandidateOperatorInput.input_digest
candidate_digest
candidate_reconstruction_digest
attempt_id
operator_result_id
operator_refusal_id
```

`CandidateOperatorInput.input_digest` hashes the structural input fields other
than `input_digest` itself:

```text
operator_policy_version
operator_name
operator_version
problem_frame_digest
original_contract_assessment_id
residual_id
residual_kind
search_gate_decision_id
compute_budget_id
geometric_search_run_id
operator_set_id
operator_set_version
attempt_index
canonical schema_versions
canonical policy_versions
```

`attempt_id`, when a `CandidateAttempt`-compatible record is produced, hashes:

```text
attempt_index
parent_attempt_id
operator_id / operator_name
operator_version
input_digest
candidate_digest
budget_charge
depth
step_index
replay_status
replay_blockers
exact ordered evidence_spans
```

It uses the existing `CandidateAttempt` vocabulary:

```text
replay_status = CandidateReplayStatus.REPLAY_PENDING
replay_blockers = ()
budget_charge = BudgetCharge(candidates=1, steps=1)
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

Changing `explanation` must not change any ID.

## 15. Authority boundary

The candidate operator may decide only whether one deterministic candidate
reconstruction can be produced under the selected operator policy.

| Concern | Authority owner | Candidate operator authority |
|---|---|---|
| Original organ runnable/refused state | Existing `ContractAssessment` organ | None |
| Residual projection | `ContractResidual` | None |
| Search eligibility | `SearchGateDecision` | None |
| Compute allocation | `ComputeBudgetDecision` | None |
| Run envelope identity | `GeometricSearchRun` | None beyond consuming identity |
| Candidate reconstruction | This ADR's candidate operator | One deterministic proposal only |
| Contract/proof replay | Contract/Proof Replay Adapter | None |
| Trace integrity | `SealedPracticeTrace` | None |
| Answer production/selection | Future separately authorized result stage | None |
| Durable promotion | Existing reviewed/certificate paths | None |
| Workbench | Future read-only projection | None |

The operator has no authority to:

```text
decide truth
decide answerability
close contracts
close proofs
run proof replay
run contract replay
seal traces
select answers
rank candidates
repair source records
serve output
mutate artifacts
promote findings
edit packs
edit teaching data
edit policy
edit identity
edit eval reports
write Workbench state
```

No candidate-operator result changes durable epistemic standing. Source kind
(`operator`, `search`, `replay`, or `practice`) grants no promotion authority.

## 16. Forbidden imports/calls/effects

### 16.1 Allowed dependency surface

A future implementation may import only:

- standard-library immutable value, enum, canonical JSON, and SHA-256
  facilities;
- `SourceSpan` and existing identity-bearing `ProblemFrame` values or validated
  projections;
- `ContractAssessment` as a value type;
- `ContractResidual` and `ResidualKind` as value types;
- `SearchGateDecision` and `SearchGateStatus` as value types;
- `ComputeBudgetDecision` and `ComputeBudgetStatus` as value types;
- `GeometricSearchRun`, `CandidateAttempt`, `BudgetCharge`, and
  `CandidateReplayStatus` as value types; and
- local candidate-operator immutable value types and static operator-set
  manifests.

The implementation consumes upstream records for identity binding and
deterministic candidate reconstruction only. It does not invoke upstream
producers or downstream closure authorities.

### 16.2 Forbidden calls and effects

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
contract/proof replay execution
sealed trace writing
```

It also must not call:

```text
candidate generation outside the closed operator
open-ended search execution
repair
answer realization
field or algebra mutation
thread or process scheduling APIs
```

No hidden fallback is permitted. Missing upstream evidence, unsupported policy,
identity mismatch, budget denial, or malformed spans produce a typed operator
refusal.

## 17. Failure modes and fail-closed behavior

| Failure | Required outcome |
|---|---|
| Unsupported operator policy | `CandidateOperatorRefusal` |
| Unsupported operator name/version | `CandidateOperatorRefusal` |
| Unsupported residual kind | `CandidateOperatorRefusal` |
| Unsupported residual code | `CandidateOperatorRefusal` |
| Unsupported candidate organ | `CandidateOperatorRefusal` |
| Ineligible `SearchGateDecision` | `CandidateOperatorRefusal` |
| Non-allowed `ComputeBudgetDecision` | `CandidateOperatorRefusal` |
| Run identity mismatch | `CandidateOperatorRefusal` |
| Budget/run mismatch | `CandidateOperatorRefusal` |
| Gate/budget mismatch | `CandidateOperatorRefusal` |
| Missing residual fields required by operator | `CandidateOperatorRefusal` |
| Missing or ambiguous typed cue required by the v1 operator | `CandidateOperatorRefusal` |
| Malformed evidence spans | `CandidateOperatorRefusal` |
| Attempt index exceeds budget | `CandidateOperatorRefusal` |
| Attempt index exceeds `max_attempts_per_run` | `CandidateOperatorRefusal` |
| Fixed budget charge exceeds structural budget | `CandidateOperatorRefusal` |
| `max_parallelism != 1` | `CandidateOperatorRefusal` |
| Operator-set mismatch | `CandidateOperatorRefusal` |
| Candidate reconstruction cannot reproduce canonical identity | `CandidateOperatorRefusal` |

No failure may become:

```text
partial answer
best guess
soft proof
ranked candidate
serving fallback
promotion
teaching mutation
Unknown == False
```

A refusal does not consume a candidate attempt. A result consumes exactly the
declared fixed charge and still remains `replay_pending`.

## 18. Test obligations for future implementation PR

The future implementation must add executing tests that meaningfully fail for
each prohibited state:

1. Public API exports are exact.
2. Operator-set identity is deterministic.
3. Candidate operator input identity is deterministic.
4. Valid residual/gate/budget/run context produces one candidate operator
   result.
5. Candidate digest differs from candidate reconstruction digest.
6. Candidate reconstruction binds run, attempt, residual, operator set,
   operator name/version, and candidate digest.
7. Unsupported residual kind refuses.
8. Ineligible gate refuses.
9. Blocked/zero/unassessable budget refuses.
10. Attempt index beyond `max_candidates` refuses.
11. Run/gate/budget mismatch refuses.
12. Operator-set mismatch refuses.
13. Missing required residual field refuses.
14. Malformed evidence span refuses.
15. Duplicate evidence spans are preserved.
16. Evidence span reorder changes identity if spans participate in identity.
17. Explanation changes do not affect IDs.
18. No `answer`, `final_answer`, or `served_output` fields exist.
19. No `score`, `rank`, `priority`, `selected`, or `best` fields exist.
20. No candidate generation outside the closed operator, search, repair,
    replay, seal, serve, or mutation call is reachable.
21. No dynamic plugin, filesystem, network, time, random, environment, UUID,
    hostname, or path identity is reachable.
22. No reverse dependency from upstream modules into the operator module unless
    explicitly intended by the implementation PR.
23. Candidate result alone cannot be represented as closure.
24. Candidate result must be replayable through ADR-0229 and sealable through
    ADR-0230.
25. Focused tests and the repository smoke lane pass.

Additional required controls:

- tests independently recompute operator-set, input, candidate,
  reconstruction, attempt, result, and refusal hashes rather than calling the
  implementation's private hashing helper;
- static coupling tests parse the operator module and enforce the allowed
  import/call surface;
- tests prove only `missing_role_candidate.v1` is present in the v1 operator
  set;
- tests prove residual codes other than `direction_unbound` refuse in v1; and
- tests prove the produced `CandidateAttempt`-compatible record remains
  `CandidateReplayStatus.REPLAY_PENDING`.

## 19. Authorized next PR

This ADR authorizes exactly one next implementation PR:

```text
feat(kernel): implement missing-role candidate operator shell
```

That PR may only:

- add candidate-operator frozen dataclasses, closed enums/helpers, canonical
  hashing helpers, and a discriminated outcome type;
- add a static one-row operator-set identity for `missing_role_candidate.v1`;
- implement exactly one deterministic operator shell for
  `ResidualKind.MISSING_ROLE`, `candidate_organ="unary_delta_transition"`, and
  `residual_code="direction_unbound"`;
- emit one `CandidateAttempt`-compatible candidate reconstruction/result/refusal;
- keep `CandidateReplayStatus.REPLAY_PENDING` on produced attempts;
- validate residual/gate/budget/run/operator-set identity; and
- add tests only for the boundary behavior and isolation obligations in
  Section 18.

That PR explicitly excludes:

```text
multi-operator search
recursive search
parallel search
candidate ranking
candidate selection
repair
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

No other implementation PR is authorized by this ADR. Broader missing-role
coverage, missing-relation candidates, missing-proposal candidates, target
binding, multi-attempt search, replay execution, sealed practice execution,
Workbench display, answer production, serving, evaluation, and promotion each
remain separately gated.
