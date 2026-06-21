# Preflight: `state_change.unary_delta` Implementation Map

**Status:** Design complete; implementation remains future work
**Date:** 2026-06-21
**Controlling authorization:**
`docs/sessions/unary-state-change-delta-authorization-2026-06-21.md`
**Target future PR:** `feat(kernel): introduce diagnostic unary-delta proposal seam`

## 1. Preflight result

The implementation is feasible without a broad story parser, but only after
splitting `state_change.transition` into the narrower
`state_change.unary_delta` family.

The current substrate already carries the scalar, object, and exact
`quantity_entity` edge needed by the two seed positives. It does not carry an
exact typed action cue. The minimum necessary type addition is therefore one
family-local cue record, not a universal event IR.

No implementation is present in this documentation PR.

## 2. Current relevant code map

### 2.1 Descriptive family gate

`generate/foundational_families.py`

- contains exactly two current registry entries;
- marks `binding.quantity_entity` implemented/authorized;
- keeps broad `state_change.transition` proposed and
  `implementation_authorized=False`;
- is descriptive metadata only and is not runtime dispatch.

Future action: add a third exact entry for `state_change.unary_delta`. Do not
authorize or repurpose `state_change.transition`.

### 2.2 Construction proposal catalog

`generate/construction_affordances.py`

- `ConstructionProposal.status` is structurally restricted to `"proposed"`;
- proposals cannot store missing roles or active hazards;
- all catalog entries are diagnostic-only and serving-disallowed;
- `propose_construction(family_id, evidence_spans)` has hypothesis-only inputs;
- `make_proposal()` rejects all current catalog families and must remain a
  loud legacy fence.

Future action: add `_UNARY_DELTA_FAMILY`, catalog it, and include it in the
proposal-first set. Do not change proposal schema or `make_proposal()`.

### 2.3 ProblemFrame types

`generate/problem_frame.py`

- carries exact mentions, bindings, bound relations, proposals, and
  quantity-kind dispositions;
- has no event/action cue record;
- has no unary-delta-specific state;
- `QuantityKindDisposition` is family-local to quantity/entity and is not
  available for state-change confusers after #853.

Future action: add one family-local `GroundedUnaryDeltaCue` and a
`ProblemFrame.unary_delta_cues` tuple with a matching builder method. Do not
widen `MentionKind` to a generic `event`/`action` universe.

### 2.4 Frame builder

`generate/problem_frame_builder.py::build_problem_frame`

Current order:

```text
scalars / units / hazards / process-frame candidates
→ proposal-first construction proposals
→ mentions / bindings / quantity disposition / bound relations / target
→ initial ProblemFrame
→ ContractAssessment dispatch
```

Relevant existing facts:

- `Ana gained 3 marbles.` produces one `consumption` process-frame candidate,
  one exact scalar mention, one exact object mention, and one exact
  `quantity_entity` binding; it produces no proposal or bound relation.
- `The jar lost 2 cookies.` has the same topology.
- `_quantity_entity_proposals()` intentionally refuses any active process
  frame, so the state-change positive has no quantity-family proposal.
- `_quantity_kind_dispositions()` now requires exactly one
  `binding.quantity_entity` proposal. This is the #853 hardening boundary and
  must not be widened.
- `_TRANSFER_RE` separately constructs a `transfer` relation for a narrow
  `gave` surface. It must not be reused as unary state change.

Future action: add one cue-proposal helper before mention binding, then publish
the exact cue and unary relation after mentions/bindings exist.

### 2.5 Contract assessment

`generate/problem_frame_contracts.py`

- `assess_contracts()` dispatches current catalog contracts only from an
  existing family proposal;
- dedicated assessment functions hold family-specific closure logic;
- `ContractAssessment` is the sole runnable/refused authority;
- output ordering is deterministic by `candidate_organ`.

Future action: register `unary_delta_transition`, implement
`assess_unary_delta(frame)`, and dispatch only when the exact proposal exists.

### 2.6 Process-frame candidates

`generate/process_frames.py`

- the broad `consumption` candidate frame includes both `gain*` and `lose*`;
- its own `not_licensed` declarations forbid deciding gain/loss without exact
  surface evidence and forbid computing remaining quantities;
- it is candidate context, not a grounded event role or contract.

Future action: allow the existing `consumption` candidate to coexist, but do
not treat it as cue, proposal, relation, or closure authority.

### 2.7 Legacy semantic-state derivation path

`generate/derivation/state/*`

- already models `set`, `gain`, and `loss` transitions for accumulation;
- parses raw clauses independently of `ProblemFrame`;
- stores numeric values as float-backed `SemanticQuantity` rather than exact
  `GroundedScalar` fractions;
- permits loose pronoun continuation;
- replays to `GroundedDerivation` candidates.

Future action: none. The new diagnostic family must not import, call, wrap,
compare against, or emit `SemanticLedger`, `StateTransition`, or
`GroundedDerivation`.

### 2.8 Callers and consumers

The import/call-site sweep found:

- `build_problem_frame()` and `assess_contracts()` are consumed by focused
  tests plus `scripts/gsm8k_problem_frame_adequacy.py` and
  `scripts/gsm8k_substrate_morphology.py`;
- no `calibration/` module directly consumes this seam;
- no serving module directly imports `problem_frame_contracts`;
- current proposal-first tests enforce proposal ordering, exact spans,
  diagnostic posture, and proposal-gated dispatch.

The future PR must preserve these callers and must not add a serving import.

## 3. Required type addition

Add only this family-local shape in `generate/problem_frame.py`:

```python
UnaryDeltaDirection = Literal["increase", "decrease"]
UnaryDeltaActionKind = Literal["gain", "loss"]

@dataclass(frozen=True, slots=True)
class GroundedUnaryDeltaCue:
    cue_id: str
    surface: str
    action_kind: UnaryDeltaActionKind
    direction: UnaryDeltaDirection
    span: SourceSpan
```

Construction obligations:

- `surface` must equal `span.text`;
- `gained` must map only to `action_kind="gain"`,
  `direction="increase"`;
- `lost` must map only to `action_kind="loss"`,
  `direction="decrease"`;
- no other cue value is constructible;
- the frame carries cues as `tuple[GroundedUnaryDeltaCue, ...]` in stable source
  order.

This type is intentionally not:

- a generic `EventMention`;
- a verb parse tree;
- an actor/source/target model;
- a temporal graph;
- a `SemanticLedger` transition;
- an arithmetic operator.

Do not add a new `SubstrateFact` variant or widen `MentionKind` in the first PR.

## 4. Closed cue inventory and recognition

The future builder owns one immutable mapping:

```text
gained → (gain, increase)
lost   → (loss, decrease)
```

Recognition rules:

1. enumerate exact lexical-boundary occurrences using the existing lexical
   boundary helper style;
2. zero hits: no proposal;
3. more than one hit, including repeated identical cues: no proposal;
4. one hit: use only its exact `SourceSpan` to create the proposal;
5. do not capture surrounding grammar or synthesize an event chunk;
6. block proposal creation when an explicit competing surface is already
   visible: percent, rate/per/each, comparison, transfer, transaction,
   containment, list coordination, or multiple event cues;
7. the only allowed process-frame set is empty or exactly `{"consumption"}`;
   the two authorized cues currently produce `consumption`.

The proposal helper must be a closed lexical recognizer, not a broad regex with
verb, subject, object, source, target, and clause capture groups.

## 5. Required frame publication path

The future build order is fixed:

```text
1. Existing scalar/unit/hazard/process-frame extraction
2. Detect exactly one authorized cue span
3. ConstructionProposal(status="proposed") from cue span only
4. Existing mention and MentionBinding extraction
5. GroundedUnaryDeltaCue from the proposal-backed exact cue
6. BoundRelation(relation_type="unary_delta") from cue + existing binding
7. ProblemFrame publication
8. Proposal-gated ContractAssessment
```

The unary relation uses existing `BoundRelation` / `BoundRole`:

| Bound role | Target |
|---|---|
| `action_cue` | `GroundedUnaryDeltaCue.cue_id`, kind `unary_delta_cue` |
| `delta_quantity` | selected quantity `GroundedMention.mention_id` |
| `changed_object` | selected object `GroundedMention.mention_id` |

`direction` is an explicit field of the exact cue. The construction catalog
still declares direction as a required semantic obligation; assessment checks
the cue's typed disposition.

Relation publication requirements:

- exactly one `quantity_entity` binding;
- its source resolves to exactly one source-grounded scalar mention;
- its target resolves to exactly one object mention;
- cue precedes quantity, which precedes object;
- no `.`, `?`, or `!` boundary lies between the three spans;
- relation evidence is the ordered tuple of exact cue, quantity, and object
  spans;
- no actor, owner, source, target, before, after, container, or temporal role
  is synthesized.

If any requirement fails, publish no bound relation. The proposal may still be
assessed and refused from the missing evidence.

## 6. Construction catalog addition

The future `_UNARY_DELTA_FAMILY` must declare:

```text
family_id:       state_change.unary_delta
relation_type:   unary_delta
candidate_organ: unary_delta_transition
required roles:  action_cue, changed_object, delta_quantity, direction,
                 local_binding_relation, local_event_containment,
                 provenance_span
optional roles:  actor
diagnostic_only: True
serving_allowed: False
```

`unit`, `source`, `target`, `before_quantity`, `after_quantity`, `container`,
and `temporal_marker` stay absent from the first catalog signature. Listing
them as optional would imply the first relation can lawfully carry those
states; it cannot. They remain future-family roles, not optional SCT-1 data.

## 7. Contract assessment path

Add:

```python
def assess_unary_delta(frame: ProblemFrame) -> ContractAssessment:
    ...
```

Assessment order:

1. require exactly one `state_change.unary_delta` proposal;
2. require exactly one `GroundedUnaryDeltaCue` contained by proposal evidence;
3. require exactly one `BoundRelation(relation_type="unary_delta")`;
4. require exactly one action, delta, and changed-object role target;
5. prove delta mention → scalar provenance;
6. prove the exact `quantity_entity` edge joins the selected mentions;
7. prove typed cue/action/direction consistency;
8. prove local ordering and sentence containment;
9. prove every proposal, cue, role, binding, and relation span is an exact
   `problem_text` slice;
10. reject unit/object collisions and all active competing contexts;
11. report `runnable=True` only if both blocker and hazard sets are empty.

The function does not calculate a signed number. It does not inspect a question
target. It does not produce a target value. Its meaning is only “this local
unary-delta construction is role-complete.”

## 8. Refusal code placement

### `missing_bindings`

- `unary_delta_proposal_required`
- `action_cue_unbound`
- `action_cue_ambiguous`
- `delta_quantity_unbound`
- `delta_quantity_ambiguous`
- `changed_object_unbound`
- `changed_object_ambiguous`
- `local_binding_relation_unbound`
- `local_binding_relation_ambiguous`
- `local_event_containment_unproven`
- `delta_direction_unbound`
- `unit_object_conflict`
- `provenance_span_inexact`

### `unresolved_hazards`

- `multiple_actor_surface`
- `delta_direction_ambiguous`
- `source_target_unlicensed`
- `pronoun_antecedent_unresolved`
- `cross_sentence_event`
- `implicit_total_unlicensed`
- `comparative_context`
- `rate_context`
- `percent_context`
- `passive_voice_unsupported`
- `temporal_context_ambiguous`
- `list_context_ambiguous`
- `transfer_unlicensed`
- `multiple_state_change_cues`
- `chained_state_changes`
- `event_assertion_unlicensed`

The implementation may use a strict subset on naturally unreachable
no-proposal paths, but direct assessment of a deliberately malformed frame must
remain fail-closed and legible.

## 9. Relationship to current quantity disposition

Do not reuse or widen `QuantityKindDisposition` in SCT-1.

Reason: #853 made that disposition valid only when an exact
`binding.quantity_entity` proposal exists. State-change text deliberately has a
process-frame context, so the quantity family does not propose. Making its
disposition generic again would recreate the authority leak #853 removed.

SCT-1 instead closes only a family-specific count-valued delta relation from
its own proposal plus the exact existing scalar/object binding. Measurement
support is deferred.

## 10. Required future code files

The bounded implementation is expected to touch only:

- `generate/foundational_families.py`
- `generate/construction_affordances.py`
- `generate/problem_frame.py`
- `generate/problem_frame_builder.py`
- `generate/problem_frame_contracts.py`
- focused tests listed below

Do not touch:

- `generate/derivation/*`
- `generate/math_candidate_graph.py`
- `evals/*` or reports
- runtime/serving paths
- teaching/proposals, packs, policy, identity, recall, Vault, field, algebra,
  sealed artifacts, or `report.json`

## 11. Likely test files

Extend:

- `tests/test_foundational_families.py`
- `tests/test_construction_affordances.py`
- `tests/test_construction_proposal_seam.py`
- `tests/test_problem_frame_builder.py`
- `tests/test_problem_frame_contracts.py`
- `tests/test_quantity_entity_proposal.py`
- `tests/test_proportional_decrease_proposal.py`
- `tests/test_percent_partition_proposal.py`

Add:

- `tests/test_unary_delta_proposal.py`

No eval fixture or report file is required.

## 12. Exact future tests

### Type and catalog

1. only `gained` and `lost` construct `GroundedUnaryDeltaCue`;
2. cue action kind/direction pairs cannot be mismatched;
3. catalog entry is diagnostic-only and serving-disallowed;
4. broad `state_change.transition` stays implementation-unauthorized;
5. `state_change.unary_delta` is a distinct foundational entry;
6. `ConstructionProposal` remains proposed-only.

### Ordering and authority

7. proposal is published before cue binding/relation assessment;
8. proposal-free frame does not dispatch `unary_delta_transition`;
9. positive proposal remains `status="proposed"` after runnable assessment;
10. legacy `make_proposal()` is never used;
11. direct malformed-frame assessment refuses with stable codes.

### Exact evidence

12. every proposal/cue/relation/assessment span equals its source slice;
13. synthetic proposal span refuses;
14. synthetic cue span refuses;
15. mismatched relation role target refuses;
16. cue/quantity/object crossing a sentence boundary refuses;
17. repeated build produces identical cue, proposal, relation, and assessment.

### Positive fixtures

18. `Ana gained 3 marbles.` is diagnostically runnable;
19. `The jar lost 2 cookies.` is diagnostically runnable;
20. `The team gained 4 points.` is diagnostically runnable;
21. no positive produces an answer, target, serving flag, or derivation candidate.

### Negative/confuser fixtures

22. every table entry in authorization §17 has the specified no-proposal or
    refusal disposition;
23. `Ana gained apples.` refuses `delta_quantity_unbound`;
24. `Ana gained 3.` refuses `changed_object_unbound`;
25. `3 apples were gained by Ana.` refuses passive/order topology;
26. `Ana gained 3 pounds.` refuses unit/object conflict;
27. `Ana gained 3 apples and lost 2.` has no proposal;
28. `Tom gave Ana 3 apples.` still has no quantity disposition and no unary
    proposal;
29. plain `There are 12 apples.` keeps its quantity proposal and gains no
    unary assessment;
30. current proportional-decrease and percent-partition positives remain
    unchanged.

### Structural firewall

31. an AST/import guard proves the new ProblemFrame/catalog/contract path does
    not import `generate.derivation.state`, `generate.derivation.accumulate`,
    `generate.derivation.pool`, or `generate.derivation.verify`;
32. no new raw-prose parser appears under `generate/derivation/`;
33. the existing no-new-legacy guard remains green.

## 13. Manual probe plan

For every seed/confuser, print only:

```text
process frame names
proposal family IDs + exact evidence spans
unary cue records
mention IDs/kinds/spans
quantity_entity bindings
unary bound roles + spans
ContractAssessment organ/runnable/blockers/hazards
```

Required assertions:

- positives: exactly one unary proposal, cue, relation, and assessment;
- no-proposal confusers: no unary cue authority, relation, or assessment;
- proposed/refused cases: proposal remains proposed and blockers are exact;
- no case produces a quantity-kind disposition unless the independent
  quantity-family proposal exists;
- no case touches or compares against legacy semantic-ledger output.

## 14. Validation plan

Run targeted tests first:

```bash
uv run python -m pytest -q \
  tests/test_foundational_families.py \
  tests/test_construction_affordances.py \
  tests/test_construction_proposal_seam.py \
  tests/test_problem_frame_builder.py \
  tests/test_problem_frame_contracts.py \
  tests/test_quantity_entity_proposal.py \
  tests/test_proportional_decrease_proposal.py \
  tests/test_percent_partition_proposal.py \
  tests/test_unary_delta_proposal.py \
  tests/test_kernel_no_new_legacy_derivation_surfaces.py

uv run python -m core.cli test --suite smoke -q

uv run python -m compileall -q generate tests

uv run ruff check \
  generate/foundational_families.py \
  generate/construction_affordances.py \
  generate/problem_frame.py \
  generate/problem_frame_builder.py \
  generate/problem_frame_contracts.py \
  tests/test_foundational_families.py \
  tests/test_construction_affordances.py \
  tests/test_construction_proposal_seam.py \
  tests/test_problem_frame_builder.py \
  tests/test_problem_frame_contracts.py \
  tests/test_quantity_entity_proposal.py \
  tests/test_proportional_decrease_proposal.py \
  tests/test_percent_partition_proposal.py \
  tests/test_unary_delta_proposal.py

git diff --check
```

Run the canonical train and holdout serving probes without writing reports.
Both must retain:

```text
wrong_ids == []
```

The PR must state any correct/refused count movement observed live, but it may
not update governed report artifacts.

## 15. Implementation stop conditions

Stop immediately if implementation requires:

- actor, owner, source, target, pronoun, or temporal resolution;
- more than the exact `gained`/`lost` cue inventory;
- a generic action/event parser;
- widening quantity-entity proposal or disposition generation;
- reusing `transfer` as unary delta;
- importing or invoking the semantic-state derivation ledger;
- synthetic spans or nearest-mention selection;
- question-target or arithmetic logic;
- serving, report, eval fixture, teaching, memory, policy, identity, recall,
  Vault, field, or algebra changes;
- a non-empty wrong-ID list.

If exact local topology cannot make both seed positives runnable under these
constraints, return to design. Do not widen the parser to make fixtures pass.

## 16. Copy-paste future implementation brief

> **PR title:** `feat(kernel): introduce diagnostic unary-delta proposal seam`
>
> **Dependency:** Begin only after
> `docs(kernel): authorize unary state-change delta slice` merges. Create a
> fresh worktree from current `origin/main`; run `source
> scripts/agent_startup.sh`; prove the authorization and preflight documents
> are in the base.
>
> Implement only `state_change.unary_delta`, not broad
> `state_change.transition`. Add a family-local frozen
> `GroundedUnaryDeltaCue` with the closed exact cue mapping `gained →
> gain/increase`, `lost → loss/decrease`. Create
> `ConstructionProposal(status="proposed", diagnostic_only=True,
> serving_allowed=False)` from the exact cue span before mention/relation
> binding. Reuse the existing exact `GroundedScalar`, `GroundedMention`, and
> `MentionBinding(binding_type="quantity_entity")` to publish one
> `BoundRelation(relation_type="unary_delta")` with action cue, delta quantity,
> and changed object roles. Add proposal-gated `assess_unary_delta(frame)` as
> the sole runnable/refused authority.
>
> Keep the first slice count-only, single-cue, single-scalar, single-object,
> and single-sentence. Do not assert actor/ownership, source/target,
> before/after values, containment, transfer, arithmetic, answers, or serving.
> Do not widen `_quantity_entity_proposals()` or
> `_quantity_kind_dispositions()`. Do not import or call
> `generate.derivation.state`. Use the exact refusal taxonomy, tests, manual
> probes, validation commands, and stop conditions in this preflight. Preserve
> every current proposal-first family and train/holdout `wrong_ids == []`.
