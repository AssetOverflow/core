# ADR-0230: SealedPracticeTrace Boundary

**Status:** Proposed

**Date:** 2026-06-22

**Scope:** Kernel diagnostics, immutable practice evidence, residual-gated practice loop

**Depends on:**

- ADR-0225 ContractResidual read model
- ADR-0226 Residual-Gated Practice Loop v1
- ADR-0227 ComputeBudgetPolicy envelope
- ADR-0228 GeometricSearchRun envelope
- ADR-0229 Contract/Proof Replay Adapter boundary
- PR #872 diagnostic replay adapter shell

## 1. Summary

`SealedPracticeTrace` is an immutable diagnostic evidence envelope. It is the
first boundary after the Contract/Proof Replay Adapter that may bind a complete
residual-gated practice episode into one replay-stable, audit-native artifact.

The trace consumes immutable identities for the original `ProblemFrame`, the
original refused `ContractAssessment`, projected `ContractResidual` records, the
`SearchGateDecision`, the `ComputeBudgetDecision`, the `GeometricSearchRun`,
every `CandidateAttempt`, every `ReplayAdapterResult`, every
`ReplayAdapterRefusal`, and the governing policy/schema versions. It emits
either a sealed trace or a trace refusal.

A sealed trace records:

```text
trace_id
trace_policy_version
input_digest
upstream_identity_chain
practice_disposition
trace_records / record_refs
evidence_spans
explanation
```

It does not emit or imply:

```text
answer
final_answer
served_output
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
selected_candidate
best_candidate
serving_allowed
runnable
```

The trace is evidence only. It does not decide truth, answerability, serving,
promotion, or learning.

This ADR defines the boundary before any sealed-trace implementation exists. It
adds no code, trace persistence, candidate generation, search execution,
operator implementation, repair, replay execution, answer production, serving
behavior, Workbench behavior, or mutation path.

## 2. Why this exists

PR #872 implemented the diagnostic Contract/Proof Replay Adapter shell
authorized by ADR-0229. CORE can now represent per-candidate replay
classifications and adapter refusals, but there is not yet a single sealed
artifact that binds the complete practice episode:

```text
original refused assessment
→ residuals
→ gate
→ budget
→ run
→ candidate attempts
→ replay results/refusals
→ final practice disposition
```

Without a sealed trace, future candidate generation would produce local
diagnostic records but no durable, replay-stable evidence package that a
reviewer, Workbench projection, or promotion authority could inspect as one
unit.

The sealed trace is the bridge from:

```text
bounded practice attempt
```

to:

```text
reviewable learning evidence
```

It is not learning itself. It is not promotion. It is not serving. It is not
Workbench behavior. It is the immutable evidence envelope future
review/promotion/Workbench systems may read.

The intrinsic state space is not a final verdict. It is a typed binding between
already-produced upstream records and a practice disposition that summarizes
what happened without collapsing exploration into truth.

## 3. Architectural directions considered

### 3.1 Monolithic trace, answer, and promotion controller

A single controller could seal the episode, select an answer, and emit a
promotion proposal. This would combine evidence packaging, answer production,
and durable mutation authority. A local replay closure could silently become a
user-facing assertion or reviewed promotion. Rejected.

### 3.2 Trace inferred from mutable run state

The trace could be derived by mutating `GeometricSearchRun`,
`CandidateAttempt.replay_status`, or upstream gate/budget records after replay.
This would destroy the immutability of exploration evidence and create reverse
dependencies from sealing into search and replay. Rejected.

### 3.3 Partial trace on best-effort assembly

A malformed or incomplete episode could still produce a partial sealed trace with
soft defaults for missing replay records or orphan attempts. This would let
incomplete evidence masquerade as a complete practice episode. Rejected.

### 3.4 Immutable evidence envelope with explicit refusal

The trace validates the full upstream identity chain, binds every replay
outcome by identity, preserves exact evidence spans, emits a closed practice
disposition, and fails closed into `PracticeTraceRefusal` when sealing is not
lawful. Answer production, serving, promotion, and Workbench remain later
boundaries. Selected.

This direction makes trace failure distinct from candidate refusal and makes
illegal authority transitions visible in the output type.

## 4. Decision

The v1 policy identity is conceptually:

```text
SEALED_PRACTICE_TRACE_POLICY_VERSION = "sealed_practice_trace.v1"
```

The public conceptual outcome is a discriminated union:

```text
PracticeTraceOutcome = SealedPracticeTrace | PracticeTraceRefusal
```

`SealedPracticeTrace` exists only when the complete upstream identity chain was
validated and the episode can be sealed as immutable diagnostic evidence.

`PracticeTraceRefusal` exists when the trace cannot lawfully seal the episode
because input, identity, policy, schema, upstream completeness, or evidence-span
validation failed. A refusal is not a partial sealed trace and must not
masquerade as a practice success disposition.

The trace may decide only:

```text
whether a complete practice episode can be sealed as immutable diagnostic evidence
```

It does not decide that the problem is solved. It does not select an answer. It
does not alter any upstream authority record. It is evidence packaging, not
authority beyond trace integrity.

## 5. Position in the loop

Dependency and authority remain one-way:

```text
ContractAssessment
→ ContractResidual
→ SearchGateDecision
→ ComputeBudgetDecision
→ GeometricSearchRun
→ Contract/Proof Replay Adapter
→ SealedPracticeTrace
→ future Workbench read-only projection
→ future reviewed promotion path
```

There is no reverse dependency. In particular:

- the trace does not create or alter any upstream record;
- assessment, residual, gate, budget, run, and replay-adapter modules do not
  import the sealed-trace module;
- Workbench may later display a persisted trace but may not invoke, repair, or
  override sealing; and
- no stage in this chain gains serving authority from its position in the
  chain.

The trace is episode-in and one-outcome-out. Multi-episode orchestration belongs
to a later boundary if separately authorized.

## 6. Inputs

### 6.1 PracticeTraceInput

The conceptual trace input is:

```python
@dataclass(frozen=True, slots=True)
class PracticeTraceInput:
    input_digest: str
    trace_policy_version: str
    problem_frame_digest: str
    original_contract_assessment_id: str
    residual_ids: tuple[str, ...]
    search_gate_decision_id: str
    compute_budget_id: str
    geometric_search_run_id: str
    candidate_attempt_ids: tuple[str, ...]
    replay_result_ids: tuple[str, ...]
    replay_refusal_ids: tuple[str, ...]
    schema_versions: tuple[tuple[str, str], ...]
    policy_versions: tuple[tuple[str, str], ...]
```

The input is accompanied by immutable values for the identified original
`ProblemFrame`, refused original `ContractAssessment`, residual records, gate
decision, budget decision, `GeometricSearchRun` or lawful `SearchRunRefusal`,
every bound `CandidateAttempt`, every supplied `ReplayAdapterResult`, and every
supplied `ReplayAdapterRefusal`. An implementation may consume validated
identity-bearing projections when those projections contain every field required
to reproduce the identity and cross-chain checks.

The input binds to one complete practice episode. It cannot contain a preferred
candidate, a hidden answer, a serving decision, or a promotion target.

The following validations are mandatory before sealing:

1. `problem_frame_digest` reproduces from the supplied immutable frame.
2. `original_contract_assessment_id` reproduces, its `runnable` state is
   refused, and it assesses the supplied frame identity.
3. Every `residual_id` reproduces and binds to that refused assessment.
4. `search_gate_decision_id` reproduces and binds to the supplied residual
   context.
5. `compute_budget_id` reproduces and binds to the allowed gate decision.
6. `geometric_search_run_id` reproduces from the supplied run or lawful run
   refusal envelope required by the episode shape.
7. Every `candidate_attempt_id` reproduces, belongs to the run, and appears in
   canonical `GeometricSearchRun.candidate_attempts` order when a run exists.
8. Every `replay_result_id` and `replay_refusal_id` reproduces and binds to an
   identified run, attempt, and candidate identity.
9. No orphan replay result, orphan replay refusal, orphan attempt, orphan
   budget, orphan gate, or residual from a different assessment is accepted.
10. Every schema and policy version is supported explicitly.
11. `schema_versions` and `policy_versions` contain unique names in ascending
    lexical order; missing, duplicate, or reordered entries are invalid.
12. Evidence spans required by the trace policy are exact, ordered, and
    malformed spans fail closed.
13. `input_digest` reproduces from the complete structural payload defined in
    Section 12.

Any failed validation produces `PracticeTraceRefusal`; no sealed trace is
emitted.

### 6.2 Upstream record binding

The trace consumes upstream records by identity. It does not re-execute
contract assessment, residual projection, gate evaluation, budget allocation,
search, or replay classification.

When the episode includes a `SearchRunRefusal` instead of a
`GeometricSearchRun`, the trace may still seal only if the refusal identity,
gate/budget bindings, and episode shape are lawful under this ADR. Such an
episode cannot claim candidate attempts or replay outcomes that were never
produced.

## 7. Outputs

### 7.1 SealedPracticeTrace

```python
@dataclass(frozen=True, slots=True)
class SealedPracticeTrace:
    trace_id: str
    trace_policy_version: str
    input_digest: str
    problem_frame_digest: str
    original_contract_assessment_id: str
    residual_ids: tuple[str, ...]
    search_gate_decision_id: str
    compute_budget_id: str
    geometric_search_run_id: str
    candidate_attempt_ids: tuple[str, ...]
    replay_result_ids: tuple[str, ...]
    replay_refusal_ids: tuple[str, ...]
    upstream_identity_chain: tuple[str, ...]
    practice_disposition: PracticeDisposition
    trace_records: tuple[str, ...]
    evidence_spans: tuple[SourceSpan, ...]
    created_by_policy: str
    explanation: str
```

`upstream_identity_chain` is the ordered, canonical list of load-bearing
upstream identities validated during sealing. It exists so a reviewer can verify
the binding without re-deriving it from scattered fields.

`trace_records` holds content identities for the sealed upstream and replay
records referenced by the trace. It is evidence reference, not mutation.

`created_by_policy` is a static policy identifier, not a user, model, or process
identity.

`evidence_spans` copies the exact ordered spans required by the trace policy from
upstream records. The trace does not merge, widen, synthesize, sort, or dedupe
spans.

### 7.2 PracticeTraceRefusal

```python
@dataclass(frozen=True, slots=True)
class PracticeTraceRefusal:
    trace_refusal_id: str
    trace_policy_version: str
    input_digest: str | None
    practice_disposition: PracticeDisposition
    reason_codes: tuple[str, ...]
    explanation: str
```

`input_digest` is populated only when it can be validated without guessing. A
malformed input may therefore produce a refusal with `None` input digest.

### 7.3 Forbidden output fields

Neither output type may emit or contain:

```text
answer
final_answer
served_output
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
selected_candidate
best_candidate
serving_allowed
runnable
```

Generated prose is explanatory only and excluded from identity.

## 8. PracticeDisposition vocabulary

`PracticeDisposition` is closed.

Sealed-trace dispositions:

```text
sealed_original_refusal
sealed_exhausted_no_candidate
sealed_all_candidates_refused
sealed_replay_unavailable
sealed_contract_closed_proof_refused
sealed_candidate_replay_closed
```

Trace-refusal dispositions:

```text
trace_invalid_input
trace_identity_mismatch
trace_policy_unsupported
trace_upstream_incomplete
```

The output type constrains the vocabulary:

| Output type | Permitted dispositions |
|---|---|
| `SealedPracticeTrace` | `sealed_original_refusal`, `sealed_exhausted_no_candidate`, `sealed_all_candidates_refused`, `sealed_replay_unavailable`, `sealed_contract_closed_proof_refused`, `sealed_candidate_replay_closed` |
| `PracticeTraceRefusal` | `trace_invalid_input`, `trace_identity_mismatch`, `trace_policy_unsupported`, `trace_upstream_incomplete` |

### 8.1 Sealed disposition semantics

The trace derives practice disposition only from validated upstream and replay
records. It does not invent new semantic meaning for replay outcomes.

```text
Gate denied or lawful run refusal before candidate exploration
→ sealed_original_refusal

No candidate attempts and run exhausted/no candidate
→ sealed_exhausted_no_candidate

Candidate attempts exist but every lawful replay result is contract_refused
→ sealed_all_candidates_refused

Replay adapter refusals only, with no lawful candidate replay result
→ sealed_replay_unavailable

At least one contract_closed_but_proof_refused and no contract_and_proof_closed
→ sealed_contract_closed_proof_refused

At least one contract_and_proof_closed
→ sealed_candidate_replay_closed
```

`sealed_original_refusal` means the episode never advanced beyond the original
refused assessment in a way that produced candidate exploration or replay
evidence. It preserves the original refusal posture; it does not authorize
answer production, serving, or promotion.

`sealed_exhausted_no_candidate` means exploration ran under a lawful budget but
produced no candidate attempts before exhaustion. Budget or operator exhaustion
is not correctness.

`sealed_all_candidates_refused` means every lawful replay result reported
`contract_refused`. Adapter refusals do not count as lawful candidate replay
results.

`sealed_replay_unavailable` means candidate attempts exist, but every supplied
replay record is an adapter refusal and no lawful `ReplayAdapterResult` exists.

`sealed_contract_closed_proof_refused` means at least one lawful replay result
reported `contract_closed_but_proof_refused` and none reported
`contract_and_proof_closed`.

`sealed_candidate_replay_closed` means at least one lawful replay result reported
`contract_and_proof_closed` under ADR-0229. It does not mean answer production,
serving eligibility, promotion, or global uniqueness. It is replay evidence only
and is input to a future answer-realization/result stage that must be separately
authorized.

If multiple candidates report `contract_and_proof_closed` and disagree, the
sealed trace preserves every replay result and may record a future
disagreement flag when that schema is separately authorized. It must not select
a winner, rank candidates, or collapse disagreement into an answer field.

## 9. Identity-chain binding requirements

The trace must verify the complete chain:

```text
residuals bind to original refused ContractAssessment
SearchGateDecision binds to residual context
ComputeBudgetDecision binds to SearchGateDecision
GeometricSearchRun binds to SearchGateDecision and ComputeBudgetDecision
CandidateAttempt records bind to GeometricSearchRun
ReplayAdapterResult / ReplayAdapterRefusal records bind to CandidateAttempt / run / candidate identity
SealedPracticeTrace binds all of the above
```

The trace must fail closed if any required identity does not match.

The trace must not accept:

```text
orphan replay results
orphan replay refusals
orphan attempts
orphan budgets
orphan gates
residuals from a different assessment
replay results from a different run
attempts out of canonical run order when order is load-bearing
```

Identities must be recomputed independently; equality of user-supplied strings
alone is insufficient.

## 10. Replay result/refusal binding

The trace must preserve the ADR-0229 distinction between:

```text
ReplayAdapterResult
```

and:

```text
ReplayAdapterRefusal
```

A replay refusal means the adapter could not lawfully classify the candidate. It
is not candidate semantic refusal.

A replay result with `contract_refused` means the existing contract authority
ran and refused the candidate.

A replay result with `contract_closed_but_proof_refused` means contract closure
did not satisfy the applicable proof obligations.

A replay result with `contract_and_proof_closed` is replay evidence only.

The sealed trace may summarize these outcomes in `practice_disposition`, but may
not change their meaning, reorder proof obligations, discard failed candidates,
or convert adapter failure into semantic refusal.

Every replay result or refusal bound into the trace must identify:

```text
run_id
attempt_id
candidate_digest
replay_policy_version
replay disposition or refusal disposition
```

A replay record that cannot bind to a supplied run, attempt, and candidate
identity yields `PracticeTraceRefusal(trace_identity_mismatch)`.

When candidate attempts exist and replay records are required by the episode
shape, absence of every required replay record yields
`PracticeTraceRefusal(trace_upstream_incomplete)`.

## 11. Evidence and source-span preservation

The trace must:

```text
preserve ordered evidence spans
preserve duplicate spans
preserve source text references
preserve upstream record order where semantically meaningful
```

The trace must not:

```text
synthesize spans
dedupe spans
sort spans independently unless the ordering rule is explicitly canonical and non-semantic
add provenance not already present
```

Malformed evidence spans must fail closed into
`PracticeTraceRefusal(trace_invalid_input)`.

Evidence spans that participate in trace identity must change `trace_id` when
reordered. Duplicate spans remain distinct entries when upstream records
preserved them as distinct entries.

The trace copies spans from upstream frame, assessment, residual, attempt, and
replay records as required by policy. It does not read raw source text again to
infer missing roles.

## 12. Immutability and canonical identity

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
the full lowercase hexadecimal encoding. Floats, NaN, Infinity, implicit object
serialization, locale-dependent values, and unordered iteration are forbidden
in identity payloads.

### 12.1 Input digest

`input_digest` hashes exactly the structural `PracticeTraceInput` fields other
than `input_digest` itself:

```text
trace_policy_version
problem_frame_digest
original_contract_assessment_id
ordered residual_ids
search_gate_decision_id
compute_budget_id
geometric_search_run_id
ordered candidate_attempt_ids
ordered replay_result_ids
ordered replay_refusal_ids
canonical schema_versions
canonical policy_versions
```

### 12.2 Trace and refusal identities

`trace_id` self-seals the structural sealed-trace payload with its own field
blanked. It includes:

```text
trace_policy_version
input_digest
problem_frame_digest
original_contract_assessment_id
ordered residual_ids
search_gate_decision_id
compute_budget_id
geometric_search_run_id
ordered candidate_attempt_ids
ordered replay_result_ids
ordered replay_refusal_ids
ordered upstream_identity_chain
practice_disposition
ordered trace_records
exact ordered evidence_spans
created_by_policy
```

`trace_refusal_id` self-seals the structural refusal payload with its own field
blanked. It includes the trace policy version, available input digest, refusal
disposition, and ordered reason codes.

`explanation` is excluded from every identity. IDs also exclude:

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
filesystem order
hash-map iteration order unless canonicalized
user identity
model identity
machine identity
```

The trace may include static policy identifiers and schema versions, but not
runtime process identity.

### 12.3 Immutability rule

Once constructed, a `SealedPracticeTrace` is immutable.

Future systems may reference it, compare it, display it, or submit it for
review, but may not mutate it in place.

If a correction is needed, create a new trace that references the prior trace by
ID and explains the correction path. Do not edit the old trace.

Sealing byte-equivalent inputs, upstream records, replay outcomes, and policy
versions must reproduce the same outcome type, disposition, reason codes,
evidence ordering, references, and IDs byte-for-byte.

## 13. Trace refusal semantics

| Failure or outcome | Required trace outcome |
|---|---|
| Malformed trace input | `PracticeTraceRefusal(trace_invalid_input)` |
| Unsupported trace policy version | `PracticeTraceRefusal(trace_policy_unsupported)` |
| Missing required upstream record | `PracticeTraceRefusal(trace_upstream_incomplete)` |
| Upstream identity mismatch | `PracticeTraceRefusal(trace_identity_mismatch)` |
| Replay result/refusal does not bind to run/attempt/candidate | `PracticeTraceRefusal(trace_identity_mismatch)` |
| Malformed evidence spans | `PracticeTraceRefusal(trace_invalid_input)` |
| No replay records where replay records are required | `PracticeTraceRefusal(trace_upstream_incomplete)` |

A malformed or inconsistent trace input must produce a trace refusal record,
not a partial sealed trace.

No trace refusal may become:

```text
best guess
partial answer
soft proof
confidence score
rank
priority
serving fallback
proposal promotion
Unknown == False
```

## 14. Authority boundary

The trace may decide only whether a complete practice episode can be sealed as
immutable diagnostic evidence.

| Concern | Authority owner | SealedPracticeTrace authority |
|---|---|---|
| Original organ runnable/refused state | Existing `ContractAssessment` organ | None; preserves original record identity |
| Residual projection | `ContractResidual` | None; binds identities only |
| Search eligibility | `SearchGateDecision` | None |
| Compute allocation | `ComputeBudgetDecision` | None |
| Candidate generation/order | `GeometricSearchRun` and future authorized operators | None |
| Replay classification | Contract/Proof Replay Adapter | None; binds replay outcomes only |
| Cross-candidate uniqueness | Existing organ-specific disagreement authority | None |
| Answer production/selection | Future separately authorized result stage | None |
| Trace integrity | `SealedPracticeTrace` | Seals immutable evidence only |
| Durable promotion | Existing review/certificate paths | None |
| Workbench | Read-only future projection | None |

The trace has no authority to:

```text
generate candidates
execute search
execute operators
repair inputs
run contract replay
run proof replay
classify replay results
rank candidates
select final answers
serve output
mutate upstream records
allocate budget
change search eligibility
promote findings
edit packs
edit teaching data
edit policy
edit identity
edit eval reports
change Workbench state
write files/artifacts
```

No practice disposition changes durable epistemic standing. Source kind
(`search`, `replay`, or `practice`) grants no promotion authority.

## 15. Forbidden imports/calls/effects

### 15.1 Allowed dependency surface

A future boundary implementation may import only:

- standard-library immutable value, enum, canonical JSON, and SHA-256
  facilities;
- `SourceSpan` and existing identity-bearing `ProblemFrame` values;
- `ContractAssessment` as a value type;
- `ContractResidual` as a value type;
- `SearchGateDecision` as a value type;
- `ComputeBudgetDecision` as a value type;
- `GeometricSearchRun`, `SearchRunRefusal`, `CandidateAttempt`, and their value
  enums/types;
- `ReplayAdapterResult`, `ReplayAdapterRefusal`, and replay-adapter value
  enums/types; and
- local sealed-trace immutable value types and static policy manifests.

The implementation consumes upstream records for identity binding and trace
construction only. It does not invoke contract replay, proof replay, search,
operators, serving, teaching, Vault, or Workbench.

### 15.2 Forbidden calls and effects

The sealed-trace module may not import or call:

```text
candidate generation
search execution
operator execution
repair
contract replay execution
proof replay execution
serving/runtime
teaching or proposal mutation
pack, policy, or identity mutation
eval or report mutation
Workbench mutation
Vault or recall mutation
filesystem or network I/O
subprocess or shell execution
clock or timestamp APIs
randomness or UUID generation
environment or hostname inspection
dynamic import or plugin discovery
external model or tool invocation
```

No reverse import from assessment, residual, gate, budget, run, or replay-adapter
modules into the sealed-trace module is permitted.

No hidden fallback is permitted. Missing upstream evidence, unsupported policy,
identity mismatch, or malformed spans produce a typed trace refusal.

## 16. Failure modes and fail-closed behavior

| Failure or outcome | Required trace outcome |
|---|---|
| Malformed trace input | `PracticeTraceRefusal(trace_invalid_input)` |
| Unsupported trace policy version | `PracticeTraceRefusal(trace_policy_unsupported)` |
| Missing upstream record | `PracticeTraceRefusal(trace_upstream_incomplete)` |
| Upstream identity mismatch | `PracticeTraceRefusal(trace_identity_mismatch)` |
| Replay result orphaned from run/attempt/candidate | `PracticeTraceRefusal(trace_identity_mismatch)` |
| Evidence span mismatch/malformed evidence | `PracticeTraceRefusal(trace_invalid_input)` |
| No replay records where replay records are required | `PracticeTraceRefusal(trace_upstream_incomplete)` |

No failure may become:

```text
answer
best guess
soft proof
confidence score
rank
priority
serving fallback
reviewed promotion
teaching mutation
Unknown == False
```

Search or budget exhaustion has no special sealing meaning beyond the sealed
dispositions defined in Section 8. It cannot create an answer field and cannot
change the original refusal into truth.

## 17. Test obligations for future implementation PR

The future implementation must add executing tests that meaningfully fail for
each prohibited state:

1. Public API exports are exact.
2. Valid full practice chain seals a deterministic trace.
3. Original refusal-only/no-candidate episode seals as
   `sealed_exhausted_no_candidate` or `sealed_original_refusal` as applicable.
4. All candidate contract refusals seal as `sealed_all_candidates_refused`.
5. Replay refusals only seal as `sealed_replay_unavailable` or fail closed, per
   this ADR.
6. Contract-closed/proof-refused results seal as
   `sealed_contract_closed_proof_refused`.
7. Contract-and-proof-closed result seals as `sealed_candidate_replay_closed`
   without answer fields.
8. Missing upstream record returns `PracticeTraceRefusal`.
9. Gate/budget/run/replay identity mismatch returns `PracticeTraceRefusal`.
10. Orphan replay result/refusal fails closed.
11. Candidate disagreement is preserved and not resolved.
12. Duplicate evidence spans are preserved.
13. Evidence span reorder changes trace identity if spans participate in
    identity.
14. Trace IDs are canonical and exclude prose/time/env/path/random.
15. Explanation changes do not affect IDs.
16. No answer/proof-as-answer/serving/promotion fields exist.
17. No candidate generation, search execution, repair, replay execution, or
    proof engine call is reachable.
18. No runtime/serving/Workbench/teaching/eval/report mutation is reachable.
19. No reverse dependency from upstream modules into sealed trace module.
20. No filesystem/network/time/random/subprocess/env/UUID/hostname/path identity
    is reachable.
21. Focused tests and the repository smoke lane pass.

Additional required controls:

- tests independently recompute input, trace, and refusal hashes rather than
  calling the implementation's private hashing helper;
- static coupling tests parse the sealed-trace module and enforce the allowed
  import/call surface;
- disagreement tests construct at least two independently closed, conflicting
  replay results and prove the trace provides no selection API; and
- tests prove `sealed_candidate_replay_closed` does not create answer,
  serving, or promotion fields.

## 18. Authorized next PR

This ADR authorizes exactly one next implementation PR:

```text
feat(kernel): implement inert SealedPracticeTrace shell
```

That PR may only:

- add sealed-practice-trace frozen dataclasses, closed enums, canonical hashing
  helpers, and a discriminated outcome type;
- consume existing upstream diagnostic records produced by the residual-gated
  practice loop shells;
- validate the complete upstream identity chain;
- represent `PracticeTraceRefusal` and `SealedPracticeTrace` records;
- derive closed `practice_disposition` values without changing replay meaning;
- produce deterministic input, trace, and refusal IDs; and
- add tests only for the boundary and isolation obligations in Section 17.

That PR explicitly excludes:

```text
candidate generation
operator implementation
search execution
repair
contract replay execution
proof replay execution
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

The shell may prove the state machine with constructed upstream fixtures, but it
cannot claim live practice capture, Workbench display, answer production,
serving integration, or durable promotion until separately reviewed PRs authorize
those boundaries.

No other implementation PR is authorized by this ADR. Candidate-producing
operators, production replay wiring, multi-episode orchestration, Workbench
display, answer production, serving, evaluation, and promotion each remain
separately gated.