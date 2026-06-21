# Foundational Family Specification: Unary State-Change Delta

**Family ID:** `state_change.unary_delta`
**Status:** Authorized for one future diagnostic-only implementation slice;
currently unimplemented
**Related ADRs:** ADR-0223, ADR-0224
**Controlling authorization:**
`docs/sessions/unary-state-change-delta-authorization-2026-06-21.md`
**Serving:** `diagnostic_only=True`, `serving_allowed=False`

## Purpose

This family represents the smallest locally groundable state-change event: one
explicit unary gain or loss cue applied to one explicit quantity/object pair.

It answers only this diagnostic question:

> Does this one local clause contain enough exact evidence to ground a unary
> delta relation?

It does not answer a word problem and does not construct a complete state
history. It is a subordinate family beneath the broad constitutional
`state_change.transition` idea. The broad family remains implementation-
unauthorized because transfer, containment movement, before/after state, and
unary delta have different role geometries.

## Family shape

```text
Signature:       unary_delta
Candidate organ: unary_delta_transition
Relation type:   unary_delta
```

The proposal-first chain is:

```text
exact action cue
→ ConstructionProposal(status="proposed")
→ exact cue + scalar/object binding
→ BoundRelation(relation_type="unary_delta")
→ ContractAssessment
→ diagnostic runnable/refused
```

`ConstructionProposal` is hypothesis only. `ContractAssessment` is the sole
runnable/refused authority.

## Allowed cue surface

The first implementation has a closed inventory:

| Surface | Action kind | Explicit direction |
|---|---|---|
| `gained` | `gain` | `increase` |
| `lost` | `loss` | `decrease` |

No stemming, lemmatization, synonym expansion, semantic similarity, or broad
verb classification is authorized. Exact lexical-boundary matching is allowed.

The following are explicitly outside the first inventory even when they may
describe change in ordinary language:

```text
gain, gains, gaining
lose, loses, losing
gave, received, bought, sold
ate, spent, used
put, took, moved
added, removed
grew, heated, cooled
was, became, now
```

Each widening requires evidence, confusers, and separate authorization.

## Required roles

| Role | Type and obligation |
|---|---|
| `action_cue` | Exactly one source-backed `GroundedUnaryDeltaCue` |
| `delta_quantity` | Exactly one quantity mention resolving to one exact `GroundedScalar` |
| `changed_object` | Exactly one exact local object mention |
| `direction` | `increase` or `decrease`, carried only by the explicit authorized cue |
| `local_binding_relation` | Exactly one existing `quantity_entity` edge from delta to changed object |
| `local_event_containment` | Cue, quantity, and object in that order inside one sentence/clause |
| `provenance_span` | Exact source spans for cue, scalar, object, binding, and relation |

The first slice is count-valued. Unit/object collision refuses.

## Optional and deferred roles

`actor` is the only catalog-visible optional SCT-1 role. It may be carried only
when exact grounded evidence already exists. The first implementation is not
required to publish it and may not add parsing to obtain it.

These are broader state-change roles, not roles in the first relation, and must
not be invented:

- owner;
- source;
- target;
- before quantity;
- after quantity;
- container or location;
- temporal marker.
- unit or measurement property.

They belong to future family geometries.

## Minimal typed cue

The future ProblemFrame may add one family-local frozen record:

```python
@dataclass(frozen=True, slots=True)
class GroundedUnaryDeltaCue:
    cue_id: str
    surface: str
    action_kind: Literal["gain", "loss"]
    direction: Literal["increase", "decrease"]
    span: SourceSpan
```

This is not a generic event IR. It cannot represent tense, modality, negation,
actors, source/target, temporal ordering, causality, or arithmetic effects.

## Bound relation

The future relation uses existing `BoundRelation` / `BoundRole`:

```text
BoundRelation(
  relation_type="unary_delta",
  roles=(
    action_cue      → GroundedUnaryDeltaCue.cue_id,
    delta_quantity  → GroundedMention(quantity).mention_id,
    changed_object  → GroundedMention(object).mention_id,
  ),
  evidence_spans=(action_span, quantity_span, object_span),
)
```

The relation carries no signed arithmetic operand. `increase` and `decrease`
are lexical event dispositions, not instructions to mutate state.

## Evidence span rules

Every evidence span must be an exact original-text slice:

```text
0 <= start <= end <= len(problem_text)
problem_text[start:end] == text
```

Additional rules:

- action, quantity, and object spans are non-overlapping;
- source order is `action < quantity < object`;
- no sentence terminator occurs between them;
- binding evidence is exactly `(quantity_span, object_span)`;
- relation evidence contains only exact role spans in deterministic order;
- proposal evidence is the action cue span only;
- no span is widened, concatenated, repaired, or synthesized;
- a computed event envelope is locality telemetry only and is not a semantic
  evidence replacement.

## Proposal conditions

A proposal may be created only when:

- exactly one authorized cue occurs;
- no second/repeated unary cue occurs;
- no explicit percent, rate, comparison, transfer, transaction, containment,
  actor-coordination, or list surface competes;
- the only compatible process-frame candidate is `consumption`.

A cue may propose even if downstream quantity/object evidence is missing. That
is the purpose of the proposal/assessment split. Missing evidence then refuses
at `ContractAssessment`.

## Assessment obligations

`assess_unary_delta(frame)` may report `runnable=True` only if:

1. exactly one proposal exists;
2. exactly one typed cue exists and is contained by proposal evidence;
3. cue surface, action kind, and direction match the closed mapping;
4. exactly one unary-delta bound relation exists;
5. the selected delta resolves to exactly one source-grounded scalar;
6. the selected changed object is exact and unambiguous;
7. exactly one existing `quantity_entity` edge joins them;
8. cue, delta, and object satisfy exact local order/containment;
9. every proposal, cue, binding, role, and relation span is exact;
10. no blocking context or ambiguity remains.

`runnable=True` means only that the diagnostic relation is role-complete. It
does not authorize a derived value, answer, state mutation, or serving path.

## Refusal classes

### Structural blockers

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

### Ambiguity/context hazards

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

No-proposal confusers do not dispatch the assessment. Direct assessment of a
malformed frame remains fail-closed.

## Relationship to `binding.quantity_entity`

The family may consume the existing exact scalar/object
`MentionBinding(binding_type="quantity_entity")` as grounding evidence.

It must not:

- create or require a `binding.quantity_entity` proposal;
- create or consume a quantity-family `QuantityKindDisposition` outside its
  proposal boundary;
- dispatch `assess_quantity_entity()`;
- make a plain quantity/entity surface look eventful;
- make an event cue sufficient without the exact binding.

This separation preserves #853. Shared evidence is not shared authority.

## Interaction exclusions

The family must not capture:

- `proportional_change.decrease_to_fraction`;
- `partition.percent_partition`;
- plain `binding.quantity_entity`;
- comparison language;
- percent or rate language;
- transfer or transaction language;
- containment movement;
- measurement changes;
- multiple or chained events.

## Positive examples

```text
Ana gained 3 marbles.
The jar lost 2 cookies.
The team gained 4 points.
```

For each, only cue, direction, delta quantity, and changed object are asserted.
No owner, before state, after state, or result is inferred.

## Negative examples

These must not propose:

```text
There are 12 apples.
Tom has 12 apples.
Tom gave Ana 3 apples.
Tom gave her 3 apples.
Tom gave Ana some apples.
Tom had 12 apples and gave Ana 3.
Ana has 3 more apples than Tom.
20% of the apples are red.
3 apples per child.
Tom bought 3 apples and 2 oranges.
The basket was filled with apples.
The tank has 84 degrees.
There are 12 apples. Tom ate 3.
Tom and Ana each got 3 apples.
Tom moved 3 apples from the box to the bag.
The box now has 5 more pencils.
Tom put 4 shells in the bag.
Ana gained 3 apples and lost 2.
```

These may propose from the exact cue but must refuse:

```text
Ana gained apples.             # no explicit delta
Ana gained 3.                  # no changed object/binding
3 apples were gained by Ana.   # passive/order topology
Ana gained 3 pounds.           # unit/object collision in count-only SCT-1
```

## Non-goals

- broad `state_change.transition`;
- event/story parsing;
- lemmatization or synonym expansion;
- actor/owner or pronoun resolution;
- source/target and transfer conservation;
- containment movement;
- before/after or initial/final state;
- multiple events;
- measurement-valued delta;
- arithmetic or answer production;
- `SemanticLedger` or derivation integration;
- serving, eval/report mutation, teaching, memory, packs, policy, identity,
  recall, Vault, field, or algebra changes.

## Implementation status and future gates

After this documentation PR:

- this family is authorized for one future bounded implementation PR;
- no code implements it;
- broad `state_change.transition` stays unauthorized;
- no serving behavior changes.

Implementation requires all gates in
`docs/sessions/unary-state-change-delta-preflight-2026-06-21.md`, including:

- fresh-base startup guard;
- exact proposal-first ordering;
- family-local cue type only;
- full positive/confuser tests;
- no legacy semantic-state imports;
- deterministic replay;
- exact span proof;
- current proposal-first family preservation;
- train and holdout `wrong_ids == []`;
- no governed report changes.

Any need to widen cue inventory, parse actors, infer cross-sentence roles, or
touch serving returns the work to design.
