# Authorization: Unary State-Change Delta Foundational Slice

**Status:** Authorized for one future diagnostic-only implementation PR after
this authorization PR merges
**Date:** 2026-06-21
**Authorized family:** `state_change.unary_delta`
**Broad family:** `state_change.transition` remains unauthorized and
unimplemented
**Serving status:** `diagnostic_only=True`, `serving_allowed=False`
**Governing doctrine:** ADR-0223, ADR-0224, PRs #851 and #853

## 1. Decision

Do not implement the broad `state_change.transition` family next.

Authorize only `state_change.unary_delta`: one explicit, local, count-valued
gain or loss event over one exactly grounded quantity/object pair. The first
cue inventory is deliberately closed:

| Exact cue | Direction disposition |
|---|---|
| `gained` | `increase` |
| `lost` | `decrease` |

The authorized construction recognizes that an explicit delta event is locally
present. It does not construct a before state, after state, owner state,
transfer, containment move, arithmetic equation, answer, or serving action.

The safe first relation is:

```text
one exact action cue
+ one exact scalar mention
+ one exact changed-object mention
+ one exact local quantity_entity edge
------------------------------------------------
one proposed unary-delta relation, assessed diagnostically
```

This is the exact capability unlocked by the hardened quantity-entity seam:
CORE can now distinguish a quantity-bearing object from an unbound number. The
next valid step is to bind that grounded pair to one explicit local change cue,
not to parse an entire story.

## 2. Serious design finding

`state_change.transition` is not one organ. The current constitutional spec
combines at least four distinct geometries:

1. unary delta: `gained/lost N object`;
2. containment movement: `put/took N object in/from container`;
3. binary transfer: `gave/sent N object to target`;
4. before/after state relation: `was N, now M`.

They do not share the same role topology. Unary delta has one changed object and
one signed delta. Transfer has at least two state owners plus a conservation
relation. Containment movement has source/target containers. Before/after has
two temporal states and may have no delta cue at all. Treating these as one
family would force optional roles to carry the semantics and would make illegal
partial states representable.

The current code confirms the split:

- `ProblemFrame` can expose exact scalar/object mentions and
  `MentionBinding(binding_type="quantity_entity")` for `Ana gained 3 marbles.`;
- it does not expose a typed exact event/action cue or a bound unary-delta
  relation;
- it already contains a separate narrow `BoundRelation(relation_type="transfer")`
  regex path for `Tom gave Ana 3 apples.`;
- `generate.derivation.state` contains a legacy arithmetic-oriented
  `SemanticLedger`, but it uses a different raw-text path, float quantities,
  loose subject/pronoun continuation, and a replay bridge to derivation
  candidates. It is not suitable as exact `ProblemFrame` grounding evidence.

Reusing the transfer relation would silently define every change as transfer.
Reusing the semantic ledger would bypass the proposal-first substrate and
couple diagnostic recognition to arithmetic candidate production. Both are
rejected.

## 3. Map: directions considered

The intrinsic space is not a story. It is a typed local event relation over an
already grounded scalar/object edge, with exact source coordinates and a
conjugate assessment that refuses incomplete topology.

| Direction | Structural effect | Decision |
|---|---|---|
| Implement broad `state_change.transition` | Mixes unary delta, transfer, containment, and temporal-state topology | Rejected |
| Reuse `generate.derivation.state.SemanticLedger` | Bypasses `ProblemFrame`; imports legacy raw parsing and arithmetic candidate semantics | Rejected |
| Add event-cue proposals only, with no closable relation | Safe but does not prove the new quantity/entity seam composes into a useful organ | Deferred as an internal stage, not the family boundary |
| Add one unary-delta relation over exact local evidence | Preserves proposal → grounding → assessment and has a closed first topology | Selected |

## 4. Safe capability ladder

The broad family is split into separately authorized rungs:

| Rung | Family | Status after this PR |
|---|---|---|
| SCT-0 | exact local action-cue publication | Internal prerequisite to SCT-1; no independent serving or assessment authority |
| SCT-1 | `state_change.unary_delta` | Authorized for one future diagnostic implementation PR |
| SCT-2 | containment movement | Not authorized |
| SCT-3 | binary transfer | Not authorized |
| SCT-4 | before/after state relation | Not authorized |
| SCT-5 | arithmetic state equation or answer production | Not authorized |

`state_change.transition` remains the broad constitutional umbrella only. Its
existing foundational registry entry must remain
`implementation_authorized=False`.

## 5. Why now, and why only after #853

#851 proved that a local quantity/object edge can be proposed, grounded, and
assessed. #853 then closed two authority leaks:

- `ConstructionProposal` can represent only `status="proposed"`;
- quantity-kind dispositions are emitted only inside their exact proposal
  boundary, so no-proposal percent, rate, pronoun, list, or transfer confusers
  receive quantity-family authority.

Those corrections are prerequisites. A state-change slice built before #853
could have mistaken proposal state for an assessment verdict or consumed a
quantity-kind disposition synthesized for a confuser. This authorization
therefore treats #853's hardened seam as immutable:

- no proposal carries `runnable`, `refused`, missing-role, or hazard authority;
- `ContractAssessment` is the sole diagnostic runnable/refused authority;
- the unary family must not widen `_quantity_entity_proposals()`;
- the unary family must not widen `_quantity_kind_dispositions()`;
- a raw `MentionBinding` may be consumed as grounding evidence, but the
  `binding.quantity_entity` proposal and assessment are not backdoored.

## 6. Family metadata

| Field | Authorized value |
|---|---|
| `family_id` | `state_change.unary_delta` |
| display name | Unary state-change delta |
| relation type | `unary_delta` |
| candidate organ | `unary_delta_transition` |
| proposal status | Always `proposed` |
| diagnostic posture | `diagnostic_only=True` |
| serving posture | `serving_allowed=False` |
| implementation authorization | Authorized only by this merged document for one future bounded PR |
| implementation status after this docs PR | Unimplemented; no runtime registry/catalog/dispatch change |
| relation to `binding.quantity_entity` | Consumes a compatible exact local `quantity_entity` edge; does not require or create its proposal, disposition, or assessment |

The future implementation may add a new descriptive foundational registry
entry for `state_change.unary_delta`. It must not flip the existing broad
`state_change.transition` entry to authorized.

## 7. Authority gradient

The only authorized flow is:

```text
exact lexical cue (`gained` or `lost`)
→ ConstructionProposal(
      family_id="state_change.unary_delta",
      status="proposed",
      diagnostic_only=True,
      serving_allowed=False,
  )
→ exact GroundedActionCue
→ existing exact GroundedScalar / GroundedMention / quantity_entity binding
→ BoundRelation(relation_type="unary_delta")
→ assess_unary_delta(frame)
→ ContractAssessment(runnable or refused)
```

The proposal is a hypothesis only. Exact role bindings ground it. The
assessment is its corrective/conjugate and is the only runnable/refused
authority. No step derives an answer.

## 8. Minimum evidence tuple

A proposed candidate may close only from this tuple:

```text
(
  action_cue_span,
  action_kind,
  explicit_direction,
  delta_quantity_mention,
  changed_object_mention,
  quantity_entity_binding,
)
```

Every member is source-backed. Every `SourceSpan` must satisfy:

```text
problem_text[span.start:span.end] == span.text
```

No composite or synthetic span may be manufactured by concatenating role
surfaces. A contiguous event envelope may be computed as offsets for locality
checking, but it is not a new semantic fact and must not replace the individual
role spans.

## 9. Required roles

| Role | Requirement |
|---|---|
| `action_cue` | Exactly one exact `gained` or `lost` span |
| `changed_object` | Exactly one local object mention targeted by the selected quantity/entity edge |
| `delta_quantity` | Exactly one source-grounded scalar mention |
| `direction` | Required in SCT-1 because the authorized cue itself explicitly states `increase` or `decrease`; it may not be inferred from context |
| `local_binding_relation` | Exactly one `MentionBinding(binding_type="quantity_entity")` joining the selected delta to the changed object |
| `local_event_containment` | Cue, quantity, and object occur in that order in one sentence/clause with no sentence boundary |
| `provenance_span` | Exact action, quantity, object, and binding evidence spans |

SCT-1 is count-valued only. A quantity/unit/object span collision, including
`3 pounds` where `pounds` is both unit and object under current extraction,
refuses. Measurement-valued state change requires a separate extension after
unit/property topology is designed.

## 10. Optional and deferred roles that must not be invented

`actor` is the only optional SCT-1 role. It may be carried only when an exact
actor mention is already grounded by the existing frame; the implementation is
not authorized to widen actor extraction to obtain it. Its absence does not
block the relation and does not license an owner inference.

The following are optional in the broader state-change problem space but are
not representable by SCT-1 at all:

- source;
- target;
- before quantity;
- after quantity;
- container or location;
- temporal marker;
- unit/measurement property.

Their presence therefore refuses or routes to a future family. In particular,
`Ana` in `Ana gained 3 marbles.` is not automatically asserted as a state owner.
SCT-1 asserts only that the local text contains an increase cue over the
explicitly quantified object `marbles`.

## 11. Non-inference rule

The family cannot infer or compute:

- an implicit source or target;
- a pronoun antecedent;
- a cross-sentence event binding;
- an initial, before, final, or after quantity;
- a total, remainder, result, or answer;
- a transfer partner or conservation law;
- ownership or possession continuity;
- a containment path;
- arithmetic sign application (`+N` or `-N`) to stored state;
- that `gave` subtracts from a giver or adds to a receiver;
- that `put` moves an object into a container;
- that `bought`, `received`, `ate`, `spent`, `added`, or `removed` are synonyms
  for an authorized cue;
- any event hidden behind passive voice, negation, modality, or temporal order.

Unknown is not false. Missing or ambiguous evidence refuses.

## 12. Relationship to quantity/entity grounding

The relationship is monotonic but non-authoritative:

1. Existing `GroundedScalar`, `GroundedMention`, and
   `MentionBinding(binding_type="quantity_entity")` may ground the delta and
   changed-object roles.
2. The presence of such a binding does not imply an event. `There are 12
   apples.` remains only a quantity/entity construction.
3. The presence of an event cue does not imply a valid delta relation. `Ana
   gained apples.` lacks an explicit quantity and must refuse.
4. A unary-delta proposal does not create a `binding.quantity_entity` proposal,
   `QuantityKindDisposition`, or quantity-entity assessment.
5. The quantity-entity family does not create a unary-delta proposal.
6. No-proposal quantity-entity confusers must continue to have no
   quantity-kind disposition, exactly as hardened by #853.

## 13. Interaction safety with existing families

The future implementation must preserve these families byte-for-byte in
behavior and authority:

- `proportional_change.decrease_to_fraction`;
- `partition.percent_partition`;
- `binding.quantity_entity`.

Unary delta must not propose when any of these competing surfaces are active:

- percent or percentage;
- rate, `per`, or `each`;
- comparison (`more than`, `less than`, `fewer than`, `times as`);
- proportional `decrease to`, `decrease by`, or fraction-scale language;
- plain quantity/entity binding with no authorized action cue;
- transfer, transaction, or containment movement;
- list/enumeration topology;
- more than one state-change cue.

The generic `consumption` process-frame candidate may coexist because `gained`
and `lost` currently surface it. No other process-frame family may coexist in
the first slice. The process frame is candidate context only; it is not the
proposal, relation, or assessment authority.

## 14. ContractAssessment obligations

The future `assess_unary_delta(frame)` may report `runnable=True` only when:

- exactly one unary-delta proposal exists;
- exactly one authorized exact action cue exists;
- exactly one scalar mention and one compatible quantity/entity binding exist;
- the binding selects exactly one changed object;
- the cue direction is explicit and unambiguous;
- cue, delta, and object are ordered locally in one sentence/clause;
- all role and relation spans are exact slices of `problem_text`;
- no unit/object collision exists;
- no competing family, actor coordination, object list, negation, modality,
  passive voice, temporal ambiguity, or second change cue is present.

The proposal must remain `status="proposed"` whether the assessment is runnable
or refused. A proposal-free frame must not dispatch the unary-delta contract.
The assessment grants diagnostic readiness only, never serving authority.

## 15. Stable refusal taxonomy

The first implementation must use stable organ-specific blocker/hazard codes.
The exact storage field follows current `ContractAssessment` conventions;
missing structural evidence belongs in `missing_bindings`, while active
ambiguity/context belongs in `unresolved_hazards`.

| Class | Required code | Expected locus |
|---|---|---|
| missing event cue | `unary_delta_proposal_required` / no proposal | No dispatch |
| missing quantity | `delta_quantity_unbound` | Proposed then refused |
| missing changed object | `changed_object_unbound` | Proposed then refused |
| multiple actors/coordination | `multiple_actor_surface` | No proposal or refused |
| multiple objects/list | `changed_object_ambiguous` / `list_context_ambiguous` | No proposal or refused |
| ambiguous direction | `delta_direction_ambiguous` | Refused |
| source/target ambiguity | `source_target_unlicensed` | Refused |
| pronoun without exact antecedent | `pronoun_antecedent_unresolved` | Refused |
| cross-sentence event | `cross_sentence_event` | Refused |
| implicit total | `implicit_total_unlicensed` | No proposal or refused |
| comparative phrasing | `comparative_context` | No proposal |
| rate phrasing | `rate_context` | No proposal |
| percent phrasing | `percent_context` | No proposal |
| unit conflict | `unit_object_conflict` | Refused |
| passive voice | `passive_voice_unsupported` | Refused |
| temporal ambiguity | `temporal_context_ambiguous` | Refused |
| quantity/entity binding but no event | no unary proposal or assessment | No dispatch |
| event cue but no grounded pair | `local_binding_relation_unbound` | Proposed then refused |
| transfer verb without explicit roles | `transfer_unlicensed` / no unary proposal | No dispatch |
| two state changes | `multiple_state_change_cues` | No proposal |
| chained state changes | `chained_state_changes` | No proposal |
| inexact/synthetic evidence | `provenance_span_inexact` | Refused |
| negated or modal event | `event_assertion_unlicensed` | Refused |

No blocker may be silently repaired by choosing the nearest mention.

## 16. Tiny positive seed set

These are illustrative future fixtures, not implementation in this PR:

| Surface | Expected diagnostic roles |
|---|---|
| `Ana gained 3 marbles.` | cue=`gained`, direction=`increase`, delta=`3`, changed_object=`marbles` |
| `The jar lost 2 cookies.` | cue=`lost`, direction=`decrease`, delta=`2`, changed_object=`cookies` |
| `The team gained 4 points.` | cue=`gained`, direction=`increase`, delta=`4`, changed_object=`points` |

The subject is not asserted as owner or actor. The result is not computed.

## 17. Negative and confuser set

The future PR must prove these dispositions:

| Surface | Required result |
|---|---|
| `There are 12 apples.` | No unary proposal: binding exists, event absent |
| `Tom has 12 apples.` | No unary proposal: state description, not change |
| `Tom gave Ana 3 apples.` | No unary proposal: binary transfer is deferred |
| `Tom gave her 3 apples.` | No unary proposal: transfer plus unresolved pronoun |
| `Tom gave Ana some apples.` | No unary proposal: no explicit quantity |
| `Tom had 12 apples and gave Ana 3.` | No unary proposal: transfer and unbound changed object |
| `Ana has 3 more apples than Tom.` | No unary proposal: comparison |
| `20% of the apples are red.` | No unary proposal: percent partition surface |
| `3 apples per child.` | No unary proposal: rate |
| `Tom bought 3 apples and 2 oranges.` | No unary proposal: transaction and list ambiguity |
| `The basket was filled with apples.` | No unary proposal: passive containment, no quantity |
| `The tank has 84 degrees.` | No unary proposal; existing quantity assessment remains refused |
| `There are 12 apples. Tom ate 3.` | No unary proposal: disallowed cue and cross-sentence binding |
| `Tom and Ana each got 3 apples.` | No unary proposal: multiple actors/rate-like `each` |
| `Tom moved 3 apples from the box to the bag.` | No unary proposal: containment movement |
| `The box now has 5 more pencils.` | No unary proposal: comparison/current-state surface |
| `Tom put 4 shells in the bag.` | No unary proposal: containment movement |
| `Ana gained apples.` | Proposal may exist; assessment refuses missing quantity |
| `Ana gained 3.` | Proposal may exist; assessment refuses missing object/binding |
| `Ana gained 3 apples and lost 2.` | No proposal: two/chained state-change cues |
| `Ana did not gain 3 apples.` | No proposal because `gain` is outside v1; future widening must also preserve negation refusal |
| `3 apples were gained by Ana.` | Proposal may exist; assessment refuses passive/order topology |
| `Ana gained 3 pounds.` | Proposal may exist; assessment refuses unit/object collision in count-only SCT-1 |

## 18. Explicit non-authorization

This PR does not authorize:

- `state_change.transition` implementation;
- the existing broad `state-change.md` required-role topology;
- source/target, ownership, possession, or conservation modeling;
- `gave`, `received`, `bought`, `sold`, `ate`, `spent`, `put`, `took`, `moved`,
  `added`, or `removed` cues;
- initial/final or before/after state binding;
- measurement-valued delta events;
- multiple events, multiple quantities, multiple objects, or coordinated actors;
- pronoun/coreference resolution;
- cross-sentence inference;
- `SemanticLedger` integration or derivation candidate production;
- arithmetic, answer production, eval score movement, report mutation, serving,
  teaching, memory, policy, identity, recall, Vault, field, or algebra changes.

## 19. Future implementation gates

The implementation PR may begin only after this authorization and its preflight
map merge. It must:

1. start from fresh `origin/main` and pass the startup guard;
2. add `state_change.unary_delta` without authorizing
   `state_change.transition`;
3. introduce only the minimum exact action-cue type and ProblemFrame publication
   path defined by the preflight;
4. preserve proposal-first ordering and #853's proposal schema;
5. keep all three current proposal-first families green;
6. prove deterministic replay and exact spans;
7. prove every confuser above refuses or does not propose as specified;
8. preserve train and holdout `wrong_ids == []` without updating reports;
9. avoid all serving and derivation paths;
10. stop if the positive cases require actor parsing, coreference, a broad verb
    parser, synthetic spans, or quantity-family widening.

## 20. Stop conditions

Stop implementation and return to design if any of these becomes necessary:

- changing `_quantity_entity_proposals()` or `_quantity_kind_dispositions()`;
- consuming `QuantityKindDisposition` without its quantity-family proposal;
- importing `generate.derivation.state` into the ProblemFrame path;
- adding a generic verb/event parser or universal event IR;
- inferring an actor, owner, source, target, initial value, or final value;
- accepting more than the exact `gained`/`lost` cue inventory;
- touching serving, eval/report artifacts, teaching, policy, identity, recall,
  Vault, field, or algebra;
- producing a runnable assessment with inexact, synthetic, ambiguous, or
  cross-sentence evidence;
- any non-empty wrong-ID list.

## 21. Justification: the masterstroke

The masterstroke is the refusal to model a story. The new organ models a local
field differential: a direction-bearing action cue is conjugated with one
grounded delta/object edge. The proposal propagates a hypothesis; exact role
bindings reconstruct its coordinates; `ContractAssessment` opposes and
corrects every incomplete topology.

This preserves the intrinsic geometry. Unary delta, transfer, containment, and
before/after state are not optional-role variants of one object. They are
different manifolds and receive separate future contracts. The resulting slice
is small enough to make illegal states unrepresentable, yet powerful enough to
establish the first event-bearing composition over the quantity/entity seam.

## 22. Remaining risks discovered

- `docs/sessions/workbench-proposal-first-alignment-scope-2026-06-20.md`
  predates #853 and still describes proposal statuses such as `partial`,
  `closed`, and `refused`. That text is stale and must not be copied into this
  implementation. Updating Workbench docs is a separate PR.
- The legacy semantic-state ledger is semantically adjacent and therefore a
  likely source of accidental coupling. The implementation preflight requires
  an explicit no-import/no-call proof.
- Existing mention extraction does not ground the subject of `gained/lost` as
  an actor. This is a deliberate first-slice limit, not a gap to repair in the
  implementation PR.
