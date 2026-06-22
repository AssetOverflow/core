# ADR-0229: Contract/Proof Replay Adapter Boundary

**Status:** Proposed

**Date:** 2026-06-22

**Scope:** Kernel diagnostics, candidate replay classification, residual-gated practice loop

**Depends on:**

- ADR-0225 ContractResidual read model
- ADR-0226 Residual-Gated Practice Loop v1
- ADR-0227 ComputeBudgetPolicy envelope
- ADR-0228 GeometricSearchRun envelope
- PR #870 inert GeometricSearchRun shell

## 1. Summary

The Contract/Proof Replay Adapter is a diagnostic replay classifier. It is the
first boundary after `GeometricSearchRun` that may classify one exact candidate
attempt under the existing organ-specific contract and proof authorities.

The adapter consumes an immutable run identity, one attempt from that run, the
exact immutable candidate reconstruction, the complete upstream identity chain,
the organ-specific contract replay target, the applicable proof obligations,
and explicit policy/schema versions. It emits either an immutable replay result
or an immutable replay refusal.

Successful replay has exactly three semantic dispositions:

```text
contract_refused
contract_closed_but_proof_refused
contract_and_proof_closed
```

These dispositions are replay evidence. Even
`contract_and_proof_closed` is not an answer, serving decision, promotion,
mutation, global uniqueness decision, or sealed practice trace.

This ADR defines the boundary before any replay implementation exists. It adds
no code, replay execution, candidate generation, operator implementation,
repair, answer production, serving behavior, or mutation path.

## 2. Why this exists

PR #870 implemented the inert `GeometricSearchRun` shell authorized by
ADR-0228. That shell can represent a bounded run, ordered candidate attempts,
operator provenance, structural budget consumption, and replay-pending state.
It deliberately cannot decide whether a candidate is contract-refused,
contract-closed, proven, answerable, promotable, or serveable.

The missing boundary is:

```text
candidate attempt + exact candidate reconstruction
→ same organ-specific ContractAssessment replay
→ applicable proof/verifier replay
→ replay disposition evidence
```

Without a separate adapter, future code could collapse exploration into truth:
successful candidate construction could be mistaken for contract closure,
absence of blockers could be mistaken for proof, or a search run could be
mutated after the fact to claim that it had solved the problem. A dedicated
adapter preserves the duality required by the loop: candidate reconstruction is
the forward proposal; contract and proof replay are its corrective conjugates.

The intrinsic state space is therefore not a list of candidate scores. It is a
typed relation between one identified attempt, one exact reconstruction, the
original obstruction chain, and the unchanged authorities that can close or
refuse the obligations.

## 3. Architectural directions considered

### 3.1 Monolithic replay, selection, and answer controller

A single controller could replay contracts and proofs, compare candidates,
select an answer, and serve it. This would combine diagnostic classification,
uniqueness, answer selection, and serving authority. A local replay success
could silently become a user-facing assertion. Rejected.

### 3.2 Closure inferred from blocker absence or generation success

The run could classify a candidate as closed when candidate construction
succeeds or no known blocker remains. This avoids replay cost but changes the
meaning of `ContractAssessment`: failure to observe a blocker is not execution
of the existing contract, and a generated candidate is not proof. Rejected.

### 3.3 Replay state written back into `GeometricSearchRun`

The adapter could mutate `CandidateAttempt.replay_status` or replace the run
with an updated run. This would destroy the immutability of the exploration
evidence and make the replay classifier a retroactive author of its own input.
It would also create a reverse dependency from replay into search. Rejected.

### 3.4 Immutable one-attempt replay classifier

The adapter validates one exact run/attempt/reconstruction chain, invokes only
the already-authoritative contract and proof seams, and emits a separate
content-addressed result or refusal. Candidate comparison, answer production,
sealing, display, serving, and promotion remain later boundaries. Selected.

This direction makes adapter failure distinct from candidate refusal and makes
illegal authority transitions visible in the output type.

## 4. Decision

The v1 policy identity is conceptually:

```text
CONTRACT_PROOF_REPLAY_POLICY_VERSION = "contract_proof_replay.v1"
```

The public conceptual outcome is a discriminated union:

```text
ReplayAdapterOutcome = ReplayAdapterResult | ReplayAdapterRefusal
```

`ReplayAdapterResult` exists only when the input identity chain was validated
and the required replay authorities ran far enough to produce a semantic
candidate classification.

`ReplayAdapterRefusal` exists when the adapter cannot lawfully classify the
candidate because input, identity, policy, schema, authority, or obligation
validation failed. A refusal is not a partial replay result and must not
masquerade as `contract_refused`.

The adapter may decide only:

```text
candidate replay disposition under existing contract/proof obligations
```

It does not decide that the problem is globally solved. It does not select an
answer. It does not alter the original `ContractAssessment` authority. It is
evidence, not authority beyond replay classification.

## 5. Position in the loop

Dependency and authority remain one-way:

```text
ContractAssessment
→ ContractResidual
→ SearchGateDecision
→ ComputeBudgetDecision
→ GeometricSearchRun
→ Contract/Proof Replay Adapter
→ future SealedPracticeTrace
→ future Workbench read-only projection
```

There is no reverse dependency. In particular:

- the adapter does not create or alter a `GeometricSearchRun`;
- the run, budget, gate, residual, and assessment modules do not import the
  adapter;
- a future sealed trace may reference replay results but may not rewrite them;
- Workbench may later display persisted replay evidence but may not invoke,
  repair, or override replay; and
- no stage in this chain gains serving authority from its position in the
  chain.

The adapter is one-attempt-in and one-outcome-out. Batch traversal and ordering
belong to a later orchestrator. If such an orchestrator is authorized, it must
visit attempts in the canonical `GeometricSearchRun.candidate_attempts` order.

## 6. Inputs

### 6.1 Candidate reconstruction boundary

Candidate reconstruction is a separate immutable value. It is never an
in-place repair of the original `ProblemFrame`.

The conceptual reconstruction contains enough canonical state to replay the
candidate without consulting hidden mutable state:

```python
@dataclass(frozen=True, slots=True)
class CandidateReconstruction:
    candidate_reconstruction_digest: str
    run_id: str
    attempt_id: str
    original_problem_frame_digest: str
    candidate_problem_frame_digest: str | None
    frame_delta_digest: str | None
    candidate_bindings: tuple[object, ...]
    candidate_relations: tuple[object, ...]
    candidate_targets: tuple[object, ...]
    evidence_spans: tuple[SourceSpan, ...]
    operator_set_id: str
    operator_set_version: str
    operator_id: str
    operator_version: str
```

This is a conceptual schema, not an implementation instruction to introduce a
universal intermediate representation. A future implementation must reuse the
existing typed `ProblemFrame` values that the relevant organ consumes. The
schema names the identity obligations; it does not authorize a new parser,
candidate format, operator, or frame-delta engine.

Exactly one of `candidate_problem_frame_digest` or `frame_delta_digest` must be
present unless a later organ-specific schema explicitly requires both. Any
frame delta must reconstruct to one exact candidate `ProblemFrame` before
contract replay. Reconstruction cannot read source text again to infer missing
roles.

The candidate may carry:

```text
candidate ProblemFrame or frame-delta identity
candidate bindings
candidate relations
candidate targets
candidate evidence spans
operator provenance
attempt identity
```

The candidate may not:

```text
overwrite the original frame
alter source text
synthesize evidence spans
deduplicate evidence spans
repair upstream records in place
claim hidden provenance
```

### 6.2 ReplayAdapterInput

The conceptual adapter input is:

```python
@dataclass(frozen=True, slots=True)
class ReplayAdapterInput:
    input_digest: str
    replay_policy_version: str
    run_id: str
    run_policy_version: str
    attempt_id: str
    attempt_index: int
    candidate_digest: str
    candidate_reconstruction_digest: str
    problem_frame_digest: str
    original_contract_assessment_id: str
    candidate_organ: str
    residual_ids: tuple[str, ...]
    gate_decision_id: str
    budget_id: str
    operator_set_id: str
    operator_set_version: str
    contract_replay_target: str
    proof_obligation_refs: tuple[str, ...]
    schema_versions: tuple[tuple[str, str], ...]
```

The input is accompanied by immutable values for the identified original
`ProblemFrame`, refused original `ContractAssessment`, residual context, gate,
budget, `GeometricSearchRun`, exact `CandidateAttempt`, and exact
`CandidateReconstruction`. An implementation may consume a validated
identity-bearing projection instead of a complete upstream value when that
projection contains every field required to reproduce the identity and
cross-chain checks. Identities are not substitutes for values that the
contract/proof authorities must evaluate; values are not substitutes for
canonical identities.

The input binds to one candidate attempt from one exact run. It cannot contain
a batch, a candidate range, a preferred candidate, or a fallback candidate.

The following validations are mandatory before replay:

1. `run_id` reproduces from the supplied immutable run.
2. `attempt_index` is in range and the attempt at that index is structurally
   identical to the supplied attempt.
3. `attempt_id` reproduces canonically and belongs to `run_id`.
4. `CandidateAttempt.input_digest == GeometricSearchRun.input_digest`.
5. `candidate_digest` equals both the attempt's candidate digest and the
   independently recomputed digest of the canonical candidate content: the
   candidate frame/delta, bindings, relations, targets, and exact spans.
6. `candidate_reconstruction_digest` reproduces from the complete supplied
   reconstruction envelope, including its run/attempt/operator provenance and
   the validated `candidate_digest`.
7. Candidate evidence spans equal the supplied reconstruction spans exactly,
   in order, including duplicates.
8. Candidate operator id/version equal the attempt operator id/version, and
   the reconstruction's operator-set id/version equal the run's closed
   operator-set identity.
9. Problem-frame, assessment, residual, gate, and budget identities equal the
   original chain bound into the run input.
10. The original assessment identity reproduces, its `runnable` state is
    refused, and its `candidate_organ` equals the input `candidate_organ`.
11. `contract_replay_target` is the statically allowlisted authority for that
    candidate organ. No dynamic target lookup is permitted.
12. `proof_obligation_refs` exactly equal the obligations declared by the
    existing organ/proof policy. The adapter cannot add, remove, reorder, or
    deduplicate them.
13. Every schema and policy version is supported explicitly.
14. `schema_versions` contains unique schema names in ascending lexical order;
    missing, duplicate, or reordered entries are invalid.
15. `input_digest` reproduces from the complete structural payload defined in
    Section 13.

Any failed validation produces `ReplayAdapterRefusal`; no contract or proof
authority is called.

## 7. Outputs

### 7.1 ReplayAdapterResult

```python
@dataclass(frozen=True, slots=True)
class ReplayAdapterResult:
    replay_result_id: str
    replay_policy_version: str
    input_digest: str
    run_id: str
    attempt_id: str
    candidate_digest: str
    contract_replay_assessment_id: str
    proof_obligation_refs: tuple[str, ...]
    proof_replay_refs: tuple[str, ...]
    replay_disposition: ReplayDisposition
    reason_codes: tuple[str, ...]
    evidence_spans: tuple[SourceSpan, ...]
    explanation: str
```

`contract_replay_assessment_id` is an adapter-owned content identity over the
new diagnostic `ContractAssessment` replay output, or an equivalent immutable
diagnostic reference if that authority already exposes one. It does not add an
ID field to, mutate, or replace the existing `ContractAssessment` type.

`proof_replay_refs` identify the exact existing verifier/proof outcomes in the
same order as `proof_obligation_refs`. They are references to replay evidence,
not newly invented proofs.

`evidence_spans` copies the candidate reconstruction's exact ordered spans.
Contract and proof records retain their own evidence references. The adapter
does not merge, widen, synthesize, sort, or deduplicate spans.

### 7.2 ReplayAdapterRefusal

```python
@dataclass(frozen=True, slots=True)
class ReplayAdapterRefusal:
    replay_refusal_id: str
    replay_policy_version: str
    input_digest: str | None
    run_id: str | None
    attempt_id: str | None
    candidate_digest: str | None
    replay_disposition: ReplayDisposition
    reason_codes: tuple[str, ...]
    explanation: str
```

Optional identities are populated only when they can be validated without
guessing. A malformed input may therefore produce a refusal with `None`
identities. The refusal never carries a replay assessment or proof replay
reference because no complete semantic replay result exists.

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
Workbench_state
runtime_effect
confidence
score
rank
priority
selected_candidate
serving_allowed
```

Generated prose is explanatory only and excluded from identity.

## 8. ReplayDisposition vocabulary

`ReplayDisposition` is closed.

Semantic result dispositions, inherited from ADR-0226:

```text
contract_refused
contract_closed_but_proof_refused
contract_and_proof_closed
```

Adapter-refusal dispositions:

```text
invalid_replay_input
candidate_identity_mismatch
contract_replay_unavailable
proof_replay_unavailable
unsupported_replay_policy
unsupported_schema_version
unsupported_proof_obligation
```

The output type constrains the vocabulary:

| Output type | Permitted dispositions |
|---|---|
| `ReplayAdapterResult` | `contract_refused`, `contract_closed_but_proof_refused`, `contract_and_proof_closed` |
| `ReplayAdapterRefusal` | `invalid_replay_input`, `candidate_identity_mismatch`, `contract_replay_unavailable`, `proof_replay_unavailable`, `unsupported_replay_policy`, `unsupported_schema_version`, `unsupported_proof_obligation` |

The separation is load-bearing:

- `contract_refused` means the existing contract authority ran successfully
  over the exact candidate and refused it.
- `contract_replay_unavailable` means the adapter could not run the required
  authority. It says nothing about whether the candidate would close.
- `contract_closed_but_proof_refused` means contract replay closed, but at
  least one applicable proof authority returned a typed refused or unavailable
  obligation outcome.
- `proof_replay_unavailable` means no lawful proof replay could be performed at
  all because the authority or its identity was absent, malformed, or failed
  before producing an identity-bearing outcome.

An exception, missing callback, unknown target, malformed return value, or
infrastructure failure is adapter refusal, never semantic candidate refusal.

## 9. Contract replay obligations

Every candidate considered potentially closing must replay through the same
organ-specific `ContractAssessment` authority that judged the original frame.

The adapter must bind the replay target from the original assessment's
`candidate_organ` through a static, versioned allowlist. It may call the
existing organ function over the exact reconstructed candidate `ProblemFrame`.
It may not use dynamic imports, filesystem discovery, plugin registries, naming
conventions, or a generic fallback authority.

The replayed contract assessment is a new diagnostic record over the candidate
reconstruction. Its identity includes, at minimum, the candidate organ,
ordered missing bindings, ordered unresolved hazards, runnable/refused state,
and exact ordered evidence spans. Its explanation is excluded from identity.

The adapter may not:

```text
reuse the original refused assessment as if it assessed the candidate
patch the original assessment
mutate the original ProblemFrame
mutate the original ContractAssessment
mutate ContractResidual
mutate SearchGateDecision
mutate ComputeBudgetDecision
mutate GeometricSearchRun
declare contract closure without replay
declare closure from absent blockers
declare closure from candidate generation success
declare closure from semantic proximity
declare closure from budget exhaustion
```

Contract replay outcomes map as follows:

- `runnable == False` produces
  `ReplayAdapterResult(contract_refused)`. Exact missing-binding and hazard
  codes are preserved in authority-defined order as reason evidence. Proof
  replay is not called and `proof_replay_refs` is empty.
- `runnable == True` advances to the applicable proof obligations. It does not
  itself produce `contract_and_proof_closed`.
- a malformed result, target mismatch, exception, or missing authority
  produces `ReplayAdapterRefusal(contract_replay_unavailable)`.

The adapter cannot redefine or weaken the organ contract. Any change to an
organ's obligations belongs to that organ's separately reviewed contract PR.

## 10. Proof replay obligations

Proof replay begins only after the existing contract replay closes.

The adapter receives the exact ordered `proof_obligation_refs` declared by the
existing organ/proof policy. It cannot add a proof obligation by intuition,
remove one for convenience, substitute a weaker verifier, or interpret an
unknown obligation as optional.

The rules are:

```text
If contract replay refuses, proof replay does not run and cannot convert the
candidate into closure.

If contract replay closes but an applicable proof obligation returns a typed
refusal or identity-bearing unavailable outcome, the result is
contract_closed_but_proof_refused.

Only when contract replay closes and every declared applicable proof obligation
closes may the result be contract_and_proof_closed.
```

An empty proof-obligation set may close only when the existing versioned
organ/proof policy explicitly declares that no additional proof obligation is
applicable. Absence of discovered obligations is not such a declaration.

If an obligation reference is unsupported, the adapter returns
`ReplayAdapterRefusal(unsupported_proof_obligation)` before proof execution. If
the proof authority cannot be invoked or fails before returning a lawful typed
outcome, the adapter returns
`ReplayAdapterRefusal(proof_replay_unavailable)`, not a partial result.

`contract_and_proof_closed` is still not answer production. It is per-candidate
replay evidence for a later result/trace stage that remains separately
authorized.

This ADR introduces no proof engine, verifier, theorem prover, solver,
arithmetic organ, or proof-obligation discovery mechanism.

## 11. Candidate identity and reconstruction boundary

The adapter must prove that the supplied candidate is exactly the candidate
claimed by the run attempt before any replay authority is called.

Required checks are:

```text
attempt_id belongs to run_id
attempt_index addresses that exact attempt
candidate_digest matches the supplied candidate reconstruction
candidate reconstruction binds back to the original ProblemFrame identity
candidate evidence spans are exact and ordered
duplicate evidence spans are preserved
operator id/version match the attempt
operator provenance matches the run's closed operator-set identity
input identities match the original residual/gate/budget/run chain
```

The adapter must recompute identities independently; equality of user-supplied
strings alone is insufficient. A mismatch yields
`ReplayAdapterRefusal(candidate_identity_mismatch)` and invokes neither
contract nor proof replay.

Reconstruction must be pure and deterministic. It cannot read files, query a
database, call a model, inspect environment configuration, reparse raw prose,
or infer omitted fields. The original source text and source spans remain
immutable. A candidate that lacks enough exact state to reconstruct is invalid;
the adapter does not repair it.

The adapter cannot mutate `CandidateAttempt.replay_status`. Its result is a
separate immutable record. A future trace may relate the two records by
identity, but the original run remains byte-stable.

## 12. Uniqueness and disagreement semantics

Replay closure is per candidate. It is not global proof that the problem is
solved.

The one-attempt adapter has no candidate-selection authority and cannot observe
or resolve a set of competing replay results. Therefore:

- if multiple candidates close but disagree, no answer-producing stage may
  proceed unless an existing organ-specific uniqueness or disagreement rule
  closes over the complete candidate set;
- if no such rule exists or it refuses, the overall problem remains refused;
- a candidate that closes one contract target or proof obligation does not
  close unrelated targets or obligations;
- multiple `contract_and_proof_closed` records do not authorize voting,
  majority selection, best-of-N selection, score comparison, or arbitrary
  tie-breaking; and
- the adapter reports each candidate independently and never marks one as
  selected, preferred, final, or answerable.

Any later multi-candidate orchestrator must preserve run order, group results
under the exact run identity, invoke only an existing explicitly applicable
uniqueness/disagreement authority, and emit a separate result. That stage is
not authorized here.

## 13. Determinism and identity

All load-bearing identities use canonical JSON:

```python
json.dumps(
    payload,
    ensure_ascii=False,
    sort_keys=True,
    separators=(",", ":"),
)
```

The serialized string is encoded as UTF-8 and hashed with SHA-256. The digest
is the full lowercase hexadecimal encoding. Floats, NaN, Infinity, implicit
object serialization, locale-dependent values, and unordered iteration are
forbidden in identity payloads.

### 13.1 Candidate reconstruction digest

`candidate_digest` hashes the canonical candidate content: original/candidate
frame identities, frame delta when present, exact typed bindings, relations,
targets, and exact ordered evidence spans. It excludes the attempt and operator
envelope so it retains the candidate-content meaning established by ADR-0228.

`candidate_reconstruction_digest` self-seals the complete reconstruction
envelope. It includes the validated `candidate_digest`, run/attempt identity,
operator-set identity, and operator id/version in addition to the canonical
candidate content. Its own digest field is blanked during self-sealing.

For v1, `CandidateAttempt.candidate_digest` must equal the independently
recomputed candidate-content digest, and the reconstruction digest must bind
that value to the supplied run/attempt/operator provenance. A future schema may
layer these identities differently only through a new ADR/version.

### 13.2 Input digest

`input_digest` hashes exactly the structural `ReplayAdapterInput` fields other
than `input_digest` itself:

```text
replay_policy_version
run_id
run_policy_version
attempt_id
attempt_index
candidate_digest
candidate_reconstruction_digest
problem_frame_digest
original_contract_assessment_id
candidate_organ
ordered residual_ids
gate_decision_id
budget_id
operator_set_id
operator_set_version
contract_replay_target
ordered proof_obligation_refs
canonical schema_versions
```

In-memory record objects and callable objects are represented only through
their validated content identities and static authority/version identifiers.
Callable identity, object address, or function `repr` never participates.

### 13.3 Result and refusal identities

`replay_result_id` self-seals the structural result payload with its own field
blanked. It includes:

```text
replay_policy_version
input_digest
run_id
attempt_id
candidate_digest
contract_replay_assessment_id
ordered proof_obligation_refs
ordered proof_replay_refs
replay_disposition
ordered reason_codes
exact ordered evidence_spans
```

`replay_refusal_id` self-seals the structural refusal payload with its own
field blanked. It includes all available optional identities, the replay policy
version, refusal disposition, and ordered reason codes.

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
```

Replay of byte-equivalent inputs, authorities, policy/schema versions, and
obligation results must reproduce the same outcome type, disposition, reason
codes, evidence ordering, references, and IDs byte-for-byte.

## 14. Authority boundary

The adapter may decide only the replay disposition of one candidate under
existing obligations.

| Concern | Authority owner | Replay adapter authority |
|---|---|---|
| Original organ runnable/refused state | Existing `ContractAssessment` organ | None; preserves original record |
| Candidate contract replay | Same existing organ authority | Classifies its new diagnostic result |
| Candidate proof replay | Existing applicable verifier/proof authority | Classifies its typed outcomes |
| Search eligibility | `SearchGateDecision` | None |
| Compute allocation | `ComputeBudgetDecision` | None |
| Candidate generation/order | `GeometricSearchRun` and future authorized operators | None |
| Cross-candidate uniqueness | Existing organ-specific disagreement authority | None in this one-attempt adapter |
| Answer production/selection | Future separately authorized result stage | None |
| Sealed trace integrity | Future `SealedPracticeTrace` | None |
| Durable promotion | Existing review/certificate paths | None |
| Workbench | Read-only future projection | None |

The adapter has no authority to:

```text
generate candidates
rank candidates
select final answers
serve output
mutate original assessments
mutate frames
mutate residuals
mutate gate/budget/run records
allocate budget
change search eligibility
write sealed traces
promote findings
edit packs
edit teaching data
edit policy
edit identity
edit eval reports
change Workbench state
```

No replay disposition changes durable epistemic standing. Source kind
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
- `GeometricSearchRun`, `CandidateAttempt`, and their value enums/types; and
- local replay-adapter immutable value types and static authority manifests.

An actual organ-specific contract replay function or applicable existing
proof/verifier function may be called only when a separately reviewed
implementation PR names that function explicitly and proves the dependency
surface. There is no generic dispatch, dynamic plugin discovery, entry-point
scan, or fallback target.

The next shell authorized in Section 18 may use injected deterministic mock
contract/proof callbacks in tests to prove the classification state machine. It
does not authorize production replay wiring by implication.

### 15.2 Forbidden calls and effects

The adapter may not import or call:

```text
candidate generation
search execution
operator execution
repair
answer realization
serving/runtime
teaching or proposal mutation
pack, policy, or identity mutation
eval or report mutation
Workbench mutation
sealed-trace writing
Vault or recall
field or algebra mutation
filesystem or network I/O
subprocess or shell execution
clock or timestamp APIs
randomness or UUID generation
environment or hostname inspection
dynamic import or plugin discovery
external model or tool invocation
```

No reverse import from assessment, residual, gate, budget, or search-run
modules into the replay-adapter module is permitted.

No hidden fallback is permitted. An unavailable authority, unsupported
obligation, malformed return value, or execution failure produces a typed
replay refusal.

## 16. Failure modes and fail-closed behavior

| Failure or outcome | Required adapter outcome |
|---|---|
| Malformed replay input | `ReplayAdapterRefusal(invalid_replay_input)` |
| Attempt not found at the claimed position in the run | `ReplayAdapterRefusal(candidate_identity_mismatch)` |
| Attempt identity does not reproduce or belong to the run | `ReplayAdapterRefusal(candidate_identity_mismatch)` |
| Candidate digest or reconstruction digest mismatch | `ReplayAdapterRefusal(candidate_identity_mismatch)` |
| Candidate evidence span mismatch, reorder, synthesis, or deduplication | `ReplayAdapterRefusal(candidate_identity_mismatch)` |
| Operator provenance does not match attempt/run operator-set identity | `ReplayAdapterRefusal(candidate_identity_mismatch)` |
| Residual, gate, budget, assessment, or frame chain mismatch | `ReplayAdapterRefusal(candidate_identity_mismatch)` |
| Unsupported replay policy version | `ReplayAdapterRefusal(unsupported_replay_policy)` |
| Unsupported schema version | `ReplayAdapterRefusal(unsupported_schema_version)` |
| Unsupported proof obligation reference | `ReplayAdapterRefusal(unsupported_proof_obligation)` |
| Missing, mismatched, failed, or malformed contract replay authority | `ReplayAdapterRefusal(contract_replay_unavailable)` |
| Contract replay refuses | `ReplayAdapterResult(contract_refused)`; proof replay is not called |
| Contract closes but no lawful proof replay can start | `ReplayAdapterRefusal(proof_replay_unavailable)` |
| Contract closes but an invoked proof obligation returns typed unavailable/refused | `ReplayAdapterResult(contract_closed_but_proof_refused)` |
| Contract and every declared applicable proof obligation close | `ReplayAdapterResult(contract_and_proof_closed)` |

A malformed input must return a refusal record, not raise an ordinary public
exception and not emit a partial result pretending to be replay evidence.

No failure may become:

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

Search or budget exhaustion has no special replay meaning. It cannot create a
replay result and cannot change the original refusal.

## 17. Test obligations for future implementation PR

The future implementation must add executing tests that meaningfully fail for
each prohibited state:

1. Public API exports are exact.
2. Malformed input returns replay refusal, not exception or partial result.
3. Attempt/run identity mismatch fails closed.
4. Candidate digest mismatch fails closed.
5. Evidence span mismatch fails closed, including reorder or deduplication.
6. Unsupported replay policy fails closed.
7. Missing contract replay authority fails closed.
8. Contract-refused replay yields `contract_refused` and never calls proof
   replay.
9. Contract-closed/proof-refused yields
   `contract_closed_but_proof_refused`.
10. Contract-and-proof-closed yields `contract_and_proof_closed`.
11. `contract_and_proof_closed` does not create an answer field or answer
    value.
12. Multiple candidate disagreement is not resolved by the adapter.
13. Replay IDs are canonical and exclude prose, time, environment, path, host,
    process, and random values.
14. Duplicate evidence spans are preserved exactly and participate in
    identity.
15. No candidate generation, search execution, operator execution, or repair
    is reachable.
16. No runtime, serving, Workbench, teaching, proposal, eval, report, pack,
    policy, or identity mutation is reachable.
17. No reverse dependency exists from assessment, residual, gate, budget, or
    run modules into the replay adapter.
18. No filesystem, network, time, random, subprocess, environment, UUID,
    hostname, dynamic-plugin, or path identity is reachable.
19. The adapter never mutates the original frame, assessment, residual, gate,
    budget, run, attempt, or candidate reconstruction.
20. Focused tests and the repository smoke lane pass.

Additional required controls:

- tests independently recompute candidate, input, result, and refusal hashes
  rather than calling the implementation's private hashing helper;
- static coupling tests parse the adapter and enforce the allowed import/call
  surface;
- test callbacks are deterministic, side-effect-free, and identity-bearing;
- a callback exception proves the adapter-failure versus candidate-refusal
  distinction; and
- disagreement tests construct at least two independently closed, conflicting
  results and prove the one-attempt adapter provides no selection API.

## 18. Authorized next PR

This ADR authorizes exactly one next implementation PR:

```text
feat(kernel): implement diagnostic replay adapter shell
```

That PR may only:

- add replay-adapter frozen dataclasses, closed enums, canonical hashing
  helpers, and a discriminated outcome type;
- consume one existing `GeometricSearchRun` and one exact
  `CandidateAttempt` identity;
- consume one immutable candidate reconstruction value;
- validate run/attempt/candidate/upstream identity consistency;
- represent `ReplayAdapterRefusal` and `ReplayAdapterResult` records;
- support injected deterministic mock contract/proof replay callbacks for
  boundary tests only if needed;
- produce deterministic input, result, and refusal IDs; and
- add tests only for the boundary and isolation obligations in Section 17.

That PR explicitly excludes:

```text
candidate generation
operator implementation
search execution
operator execution
repair
production replay wiring
answer production
candidate selection or disagreement resolution
sealed practice trace
Workbench
runtime/serving
teaching/proposal/report/eval mutation
pack/policy/identity mutation
promotion
new proof engine
```

The shell may prove the state machine with injected test doubles, but it cannot
claim live replay capability until existing organ-specific contract and proof
functions are explicitly named and authorized in a later reviewed PR.

No other implementation PR is authorized by this ADR. Candidate-producing
operators, production replay wiring, multi-candidate orchestration, sealed
practice, Workbench display, answer production, serving, evaluation, and
promotion each remain separately gated.
