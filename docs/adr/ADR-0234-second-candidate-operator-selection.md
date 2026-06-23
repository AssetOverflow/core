# ADR-0234: Second Candidate Operator Selection

**Status:** Proposed

**Date:** 2026-06-23

**Scope:** Kernel diagnostics, candidate operator set expansion, residual-gated practice loop

**Depends on:**

- ADR-0225 ContractResidual read model
- ADR-0226 Residual-Gated Practice Loop v1
- ADR-0227 ComputeBudgetPolicy envelope
- ADR-0228 GeometricSearchRun envelope
- ADR-0229 Contract/Proof Replay Adapter boundary
- ADR-0231 First Candidate Operator boundary
- ADR-0232 CandidateAttempt Run-Binding boundary
- ADR-0233 Bound Practice Episode Sealing

## 1. Summary

This ADR selects the second candidate operator after:

```text
missing_role_candidate.v1
```

The selected operator is:

```text
operator_family = "residual_missing_relation"
operator_name = "quantity_entity_binding_candidate"
operator_version = "quantity_entity_binding_candidate.v1"
candidate_organ = "quantity_entity_binding"
```

The operator consumes one eligible `ContractResidual`:

```text
residual_kind = "missing_relation"
residual_code = "local_binding_relation_unbound"
candidate_organ = "quantity_entity_binding"
```

It emits at most one deterministic candidate attempt that proposes one local
`quantity_entity` mention-binding edge from already-realized typed evidence. It
does not parse prose, call the rate reader, solve arithmetic, produce answers,
select candidates, rank candidates, mutate the original `ProblemFrame`, or
grant serving authority.

All candidates must still pass:

```text
CandidateOperatorResult
-> CandidateAttemptRunBinding
-> ReplayAdapterInput
-> ReplayAdapterResult | ReplayAdapterRefusal
-> SealedPracticeTrace
```

This is documentation and implementation planning only. It does not implement
the operator, alter runtime/kernel execution, mutate packs, change policy,
touch Workbench, add serving behavior, or add dynamic operator discovery.

## 2. Repo Evidence Inspected

The current candidate spine is inert and complete:

```text
CandidateOperatorResult
-> CandidateAttemptRunBinding
-> ReplayAdapterInput
-> ReplayAdapterResult | ReplayAdapterRefusal
-> SealedPracticeTrace
```

Files inspected:

- `generate/candidate_operator.py`
- `generate/run_attempt_binding.py`
- `generate/replay_adapter.py`
- `generate/sealed_practice_trace.py`
- `generate/contract_residuals.py`
- `generate/search_gate.py`
- `generate/compute_budget.py`
- `generate/problem_frame_contracts.py`
- `generate/problem_frame_builder.py`
- `generate/construction_affordances.py`
- `generate/foundational_families.py`
- `tests/test_candidate_operator.py`
- `tests/test_run_attempt_binding.py`
- `tests/test_replay_adapter_bound_attempt.py`
- `tests/test_sealed_practice_trace_bound_episode.py`
- `tests/test_quantity_entity_proposal.py`
- `tests/test_contract_residuals.py`
- `tests/test_search_gate.py`
- `tests/test_compute_budget.py`
- `tests/test_rate_reader.py`
- `tests/test_rate_units.py`
- `tests/test_rate_conversion_solving.py`
- `docs/specs/foundational-families/quantity-entity-binding.md`
- `docs/analysis/gsm8k-xhigh-capability-sprint13-lookback-2026-06-18.md`
- `docs/analysis/gsm8k-workstream-a-increment-2-rate-injection-ratification-2026-06-17.md`
- `docs/analysis/gsm8k-workstream-a-increment-3-lookback-2026-06-17.md`

Load-bearing observations:

1. `missing_role_candidate.v1` is a closed one-row static operator table with
   `candidate_operators.v1`, one attempt, one step, one depth, serial budget,
   canonical JSON SHA-256 identities, and no answer/proof/serving fields.
2. Run binding, replay input construction, replay classification, and practice
   sealing are operator-agnostic after a lawful `CandidateOperatorResult`.
3. `quantity_entity_binding` is already registry-backed in
   `generate/problem_frame_contracts.py`, proposal-first in
   `generate/construction_affordances.py`, and mirrored as diagnostic-only in
   `generate/foundational_families.py`.
4. The residual projector already classifies `local_binding_relation_unbound`
   as `ResidualKind.MISSING_RELATION`, and the search gate plus compute budget
   already authorize `eligible_missing_relation` and
   `budget_allowed_missing_relation`.
5. Direct rate surfaces exist in older serving/eval paths:
   `generate.rate_comprehension.*`, `generate.recognizer_anchor_inject`, and
   `generate.derivation.bounded_rate_projection`. Those are useful evidence,
   but they are not yet a registry-backed ProblemFrame contract/residual target
   for this candidate spine.
6. The only direct ProblemFrame rate assessment currently seen is the inline
   `labor_rate` skeleton with candidate organ `temporal_tariff`; its labels
   `worker`, `rate`, and `duration` currently project to
   `CONTRACT_GAP_UNCLASSIFIED`, which the search gate blocks.

## 3. Intrinsic Space

The next candidate operator should not be selected by surface frequency alone.
The intrinsic space is a residual field whose legal forward move is a bounded
candidate reconstruction, paired with corrective replay and sealing.

The second operator should therefore minimize structural distortion:

- consume an already-classified eligible residual;
- consume typed evidence already built by the ProblemFrame substrate;
- produce one bounded candidate reconstruction;
- preserve static operator-set identity;
- avoid parser, solver, model, time, filesystem, environment, network, and
  runtime authority; and
- widen candidate-generation breadth without widening truth authority.

Rate application is capability-attractive, but in the current repo it would
pull from a serving/eval reader path or require new rate residual taxonomy
before it can lawfully enter this spine. Quantity-entity binding is the smaller
operator because its residual, gate, budget, catalog, and diagnostic contract
already exist.

## 4. Candidate Comparison

| Option | Residual consumed | Candidate organ emitted | Evidence required | Attempt/budget charge | Replay target | Confusers to test | Existing substrates | Authority risk | Decision |
|---|---|---|---|---|---|---|---|---|---|
| A. `missing_quantity_candidate` | `missing_role` codes such as `quantity_unbound`, `delta_quantity_unbound`, `base_quantity_unbound`, `original_whole_unbound` | Varies by organ | One exact scalar mention plus role target evidence | 1 attempt, 1 candidate, 1 step if narrowed | Organ-specific | wrong residual kind/code, missing spans, ambiguous scalars, entity mismatch, unit mismatch, template/prose-only trigger | `ContractResidual`, ProblemFrame quantities, multiple contracts | Too broad across organs; can become parser/repair | Defer |
| B. `missing_rate_candidate` | Ideally `missing_role` rate code, but current `rate` label is unclassified | `temporal_tariff` or future rate organ | Bound numerator, denominator, actor/entity, duration basis | 1 attempt, likely 1 step after rate contract exists | Future rate contract target | ambiguous rates, unit mismatch, currency mismatch, reciprocal rate, duration mismatch | old rate reader/solver; inline `labor_rate` skeleton | Current residual is `CONTRACT_GAP_UNCLASSIFIED`; gate blocks | Defer |
| C. `rate_application_candidate` | Future `rate_application_unbound` or equivalent; not present today | future `rate_application` or registry-backed `temporal_tariff` | One grounded rate, one compatible duration/count, one target entity, one question target | 1 attempt per grounded rate residual, 1 candidate, 1 step | Future `problem_frame_contracts.rate_application` | all required confusers plus ambiguous multiple rates, direction/sign, currency-rate, target inversion | old `apply_rate` operation, rate units, rate_with_currency workstream | High if implemented now: could call legacy reader/solver or produce answers | Defer behind rate contract/residual PR |
| D. `quantity_entity_binding_candidate` | `missing_relation`, `local_binding_relation_unbound` | `quantity_entity_binding` | One exact quantity mention, one exact local entity mention, optional compatible unit, one proposal trace, source spans already covered by residual/problem-frame evidence | 1 attempt, 1 candidate, 1 step, depth 1, serial | `problem_frame_contracts.quantity_entity` | all required confusers, especially ambiguous entities, nonlocal binding, unit/currency mismatch, template-only trigger | registry-backed quantity-entity contract, residual map, gate, budget, foundational spec | Low if narrowed to one local edge and no parser | Selected |
| E. `arithmetic_transition_candidate` | Likely `target_unbound` or mixed missing-role residuals | future arithmetic transition organ or existing state-change organ | Bound operands, operator, direction, target, question | 1 attempt only after a complete arithmetic contract exists | Future arithmetic replay target | sign mismatch, unused numerals, operation ambiguity, answer leakage | derivation modules, math candidate graph | High answer/proof leakage risk | Defer |
| F. `unit_normalization_candidate` | `unit_object_conflict` or `unit_continuity_unproven` | future unit normalization organ | Reviewed conversion relation, source unit, target unit, dimension proof | 1 attempt if conversion table is static and reviewed | Future unit contract target | currency mismatch, incompatible dimensions, hidden conversion | rate units, language pack unit dimensions | Gate currently blocks conflicts; conversion can become hidden normalization | Defer |

## 5. Decision

Select:

```text
quantity_entity_binding_candidate.v1
```

Reject the default hypothesis, `rate_application_candidate.v1`, for this pass.
The rate family remains the right capability target, but the current candidate
spine lacks a registry-backed rate-application contract, a classified rate
residual code, and an eligible search-gate path. Implementing rate application
now would either consume the older reader/solver path or require upstream
contract/residual work in the same PR. Both distort this ADR's goal: the next
smallest operator addition should preserve the existing evidence spine.

Quantity-entity binding is the masterstroke because it is both foundational and
structurally ready. It improves GSM8K/math substrate breadth by proposing the
local binding that almost every later rate, partition, comparison, and state
change needs, while avoiding answer production and solver authority.

## 6. Selected Operator Specification

### 6.1 Identity

```text
operator_family = "residual_missing_relation"
operator_name = "quantity_entity_binding_candidate"
operator_version = "quantity_entity_binding_candidate.v1"
candidate_organ = "quantity_entity_binding"
```

The implementation should introduce:

```text
CANDIDATE_OPERATOR_SET_VERSION = "candidate_operators.v2"
```

The v2 static table contains exactly two rows:

```text
missing_role_candidate.v1
quantity_entity_binding_candidate.v1
```

No dynamic registry, plugin loading, filesystem discovery, environment reads,
or operator fan-out is authorized.

### 6.2 Supported residuals

Supported residual kind:

```text
missing_relation
```

Supported residual code:

```text
local_binding_relation_unbound
```

Supported candidate organ:

```text
quantity_entity_binding
```

All other residual kinds, residual codes, and candidate organs refuse.

### 6.3 Input record shape

Reuse the existing `CandidateOperatorInput` identity envelope and add only the
typed evidence argument needed by the builder function. The new evidence record
should be a frozen dataclass:

```python
@dataclass(frozen=True, slots=True)
class GroundedQuantityEntityCue:
    quantity_mention_id: str
    entity_mention_id: str
    quantity_kind: str
    evidence_spans: tuple[SourceSpan, ...]
    unit_mention_id: str | None = None
```

The builder should be conceptualized as:

```python
def build_quantity_entity_binding_candidate(
    *,
    residual: object,
    search_gate: SearchGateDecision,
    compute_budget: ComputeBudgetDecision,
    run: GeometricSearchRun,
    problem_frame_digest: str,
    original_contract_assessment_id: str,
    grounded_quantity_entity_cues: tuple[GroundedQuantityEntityCue, ...],
    attempt_index: int = 0,
    schema_versions: tuple[tuple[str, str], ...] = (),
    policy_versions: tuple[tuple[str, str], ...] = (),
    explanation: str = "",
) -> CandidateOperatorOutcome:
    ...
```

V1 requires exactly one cue. Zero cues refuse. Multiple cues refuse. Cue spans
must be valid `SourceSpan` values and must be grounded in the residual or
ProblemFrame evidence chain. The builder must not reread source text.

### 6.4 Output record shape

Reuse:

```text
CandidateOperatorResult
CandidateOperatorRefusal
CandidateReconstruction
CandidateAttempt
```

The candidate payload should be canonical tuple-pairs, not prose:

```text
("binding_type", "quantity_entity")
("candidate_organ", "quantity_entity_binding")
("entity_mention_id", <entity_mention_id>)
("kind", "mention_binding")
("quantity_kind", <count|measurement>)
("quantity_mention_id", <quantity_mention_id>)
("relation_type", "quantity_entity")
("source", "GroundedQuantityEntityCue")
("unit_mention_id", <unit_mention_id or "">)
```

The payload ordering is part of identity. Explanatory prose is excluded from
all canonical digests.

### 6.5 Budget and attempt count

```text
max_attempts_per_run = 1
budget_charge = BudgetCharge(candidates=1, steps=1)
depth = 1
max_parallelism = 1
attempt_index = 0 only
```

The builder must refuse if:

- `attempt_index >= ComputeBudgetDecision.max_candidates`;
- `attempt_index >= CandidateOperatorPolicy.max_attempts_per_run`;
- fixed charge exceeds `max_candidates`, `max_depth`, or `max_steps`; or
- `ComputeBudgetDecision.max_parallelism != 1`.

### 6.6 Operator-set identity impact

`candidate_operator_set_id()` changes under:

```text
candidate_operators.v2
```

The v2 table digest must be computed from the static table rows only:

```text
operator_family
operator_name
operator_version
allowed_residual_kinds
allowed_residual_codes
allowed_candidate_organs
max_attempts_per_run
budget_charge
depth
max_parallelism
```

No generated prose, examples, environment values, local paths, current time,
randomness, test order, or discovered files may enter the digest.

### 6.7 Replay target expectation

The expected replay target is:

```text
quantity_entity_binding -> problem_frame_contracts.quantity_entity
```

Current `generate/replay_adapter.py` does not yet allowlist
`quantity_entity_binding`. The implementation path should either:

1. keep the first operator PR limited to candidate construction and accept that
   replay input construction returns `ReplayAdapterRefusal` with
   `contract_replay_unavailable`; or
2. add the one-row replay target allowlist change in the same PR with a focused
   test, explicitly justified as the minimum needed for the selected operator
   to traverse the full replay-adapter input boundary.

No replay contract execution, proof execution, or serving behavior is
authorized by this ADR.

### 6.8 Forbidden authority

The selected operator may not read or write:

```text
packs
policy
identity
teaching
eval reports
runtime/session state
Workbench state
filesystem paths
environment variables
network
time
random
model calls
plugin registries
dynamic operator registries
```

It may not produce:

```text
answer
final_answer
served_output
proof
verdict
confidence
score
rank
selected_candidate
best_candidate
promotion
mutation
teaching_update
pack_update
policy_update
identity_update
```

Explicit preservation:

```text
candidate != truth
candidate != proof
candidate != answer
candidate != replay success
candidate != sealed evidence
candidate != learning
candidate != promotion
```

### 6.9 Confuser set

The implementation PR must include tests for:

- wrong residual kind;
- wrong residual code;
- unsupported candidate organ;
- missing evidence spans;
- ungrounded rate, unit, or entity;
- ambiguous multiple rates;
- entity mismatch;
- unit mismatch;
- currency mismatch;
- direction/sign mismatch;
- operator budget exceeded;
- non-deterministic ordering;
- attempt count greater than declared max;
- template/prose-only trigger;
- multiple quantity-entity cues;
- nonlocal entity binding;
- pronoun or alias entity binding;
- count/measurement unit-state conflict; and
- state-change, percent, comparison, rate, and currency-rate surfaces trying to
  backdoor a generic quantity-entity candidate.

## 7. Follow-up Implementation PR Brief

Suggested PR title:

```text
feat(kernel): add quantity-entity binding candidate operator shell
```

Suggested branch:

```text
codex/quantity-entity-binding-candidate-operator
```

Expected changed files:

```text
generate/candidate_operator.py
tests/test_candidate_operator_quantity_entity_binding.py
tests/test_candidate_operator.py
```

Optional, only if the PR explicitly includes the trivial replay target
allowlist:

```text
generate/replay_adapter.py
tests/test_replay_adapter_bound_attempt.py
```

New dataclasses:

```text
GroundedQuantityEntityCue
```

New constants:

```text
QUANTITY_ENTITY_BINDING_CANDIDATE_OPERATOR_NAME
QUANTITY_ENTITY_BINDING_CANDIDATE_OPERATOR_VERSION
QUANTITY_ENTITY_BINDING_RESIDUAL_KIND
QUANTITY_ENTITY_BINDING_RESIDUAL_CODE
QUANTITY_ENTITY_BINDING_CANDIDATE_ORGAN
QUANTITY_ENTITY_BINDING_OPERATOR_POLICY
```

Policy versions:

```text
CANDIDATE_OPERATOR_POLICY_VERSION remains "candidate_operator.v1"
CANDIDATE_OPERATOR_SET_VERSION becomes "candidate_operators.v2"
```

Candidate payload canonicalization:

- use tuple-pairs in fixed lexical/schema order;
- include `quantity_mention_id`, `entity_mention_id`, `quantity_kind`, and
  `unit_mention_id`;
- include exact evidence spans in existing span-payload format;
- exclude explanation prose.

Input digest canonicalization:

- include operator name and version;
- include residual kind/code/organ;
- include gate, budget, run, and operator-set identities;
- include attempt index;
- include sorted unique schema and policy version pairs;
- exclude typed-cue prose and explanations.

Operator result digest canonicalization:

- reuse the existing `_operator_result_id_payload` shape;
- use the new organ/operator identity;
- include candidate and reconstruction digests;
- include exact evidence spans;
- keep reason codes empty on success.

Budget charge:

```text
BudgetCharge(candidates=1, steps=1)
depth = 1
max_parallelism = 1
max_attempts_per_run = 1
```

Static authority guards:

- public dataclasses expose no answer/proof/score/rank/selected/mutation fields;
- AST/static tests prove no imports of runtime, Workbench, teaching, packs,
  random, time, os, pathlib discovery, network, subprocess, or model clients;
- no dynamic operator table construction;
- no filesystem/env/plugin loading;
- no solver or rate-reader calls;
- no hidden normalization;
- no updates outside the candidate/replay allowlist surfaces named above.

Focused validation commands:

```bash
uv run python -m pytest -q tests/test_candidate_operator.py
uv run python -m pytest -q tests/test_candidate_operator_quantity_entity_binding.py
uv run python -m pytest -q tests/test_run_attempt_binding.py
uv run python -m pytest -q tests/test_replay_adapter_bound_attempt.py
uv run python -m pytest -q tests/test_sealed_practice_trace_bound_episode.py
uv run ruff check generate/candidate_operator.py tests/test_candidate_operator*.py
uv run python -m compileall -q generate/candidate_operator.py tests/test_candidate_operator*.py
uv run python -m core.cli test --suite smoke -q
git diff --check
git diff --name-only origin/main...HEAD
```

If the replay allowlist is included in the same PR, also run:

```bash
uv run ruff check generate/replay_adapter.py tests/test_replay_adapter_bound_attempt.py
uv run python -m compileall -q generate/replay_adapter.py tests/test_replay_adapter_bound_attempt.py
```

## 8. Merge Blockers For The Implementation PR

The implementation PR must not merge if:

- the operator-set table is dynamic or discovered from files;
- more than two operator rows appear in `candidate_operators.v2`;
- `missing_role_candidate.v1` behavior changes except for the expected
  operator-set identity/version update;
- `quantity_entity_binding_candidate.v1` accepts any residual code other than
  `local_binding_relation_unbound`;
- it produces more than one attempt per run;
- explanation text affects any digest;
- candidate output contains answer/proof/score/rank/selection/mutation fields;
- state-change, rate, currency-rate, percent, comparison, or prose-only
  triggers produce a quantity-entity candidate;
- replay/binding/sealing behavior is weakened to accept malformed identity
  chains;
- `ReplayAdapterRefusal` for unavailable quantity-entity replay is hidden or
  coerced into success;
- any pack, teaching, policy, identity, runtime, Workbench, eval report, or
  serving path is touched; or
- validation commands above fail.

## 9. Deferred Work

Deferred explicitly:

- `rate_application_candidate.v1`;
- `missing_rate_candidate.v1`;
- rate contract registry and rate residual taxonomy;
- replay execution for quantity-entity beyond the existing adapter shell;
- multi-operator orchestration or search fan-out;
- ranking, scoring, best-candidate selection, or answer production;
- any candidate promotion, learning, or pack mutation;
- dynamic operator discovery;
- filesystem, environment, network, time, random, runtime, or model-call
  authority; and
- broad unit normalization or hidden conversion.

The natural next ADR after this one is a rate contract/residual authorization:

```text
rate_application contract
-> rate residual codes
-> eligible gate/budget rows
-> rate_application_candidate.v1
```

That sequence should reuse the evidence spine defined here rather than
shortcutting through the older reader/solver path.
