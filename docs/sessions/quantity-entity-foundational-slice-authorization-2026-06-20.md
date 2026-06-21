# Authorization: `binding.quantity_entity` Foundational Slice

**Status:** Authorized for one future diagnostic-only implementation PR after this
authorization PR merges
**Date:** 2026-06-20
**Family:** `binding.quantity_entity`
**Governing doctrine:** ADR-0223, ADR-0224, and the proposal-first fence landed
through PRs #841–#844
**Serving status:** Not serving; serving is not authorized

## 1. Purpose

This document authorizes a bounded implementation slice for
`binding.quantity_entity`. It is the first foundational grounding family because
a quantity is not merely a number: it is a typed counted or measured amount
attached to an entity, an explicit unit/kind disposition, exact source
provenance, and a local semantic role.

The family is a grounding primitive, not an answer-producing construction. Its
job is to expose whether one locally evidenced quantity can be bound to one
locally evidenced entity without ambiguity. Later state-change, partition,
rate, comparison, unit/science, chart-reading, and reading-comprehension
contracts may consume that binding. None of those later contracts are part of
this authorization.

This preserves ADR-0223's authority split:

```text
closeness proposes;
bindings ground;
contracts determine.
```

Here, "determine" means only that a diagnostic construction contract is
runnable from its stated evidence. It does not mean determining or emitting an
answer.

## 2. Map: intrinsic space and considered directions

The intrinsic space is a small, provenance-preserving bipartite relation:
grounded quantity mentions on one side, locally evidenced entity mentions on
the other, and typed `MentionBinding` edges between them. Ambiguity is not a
low score to optimize away; it is competing topology that prevents closure.

The invariant is therefore unique local binding under exact evidence, not
generic noun discovery.

| Direction | Geometry | Decision |
|---|---|---|
| Add a broad noun/entity parser | Expands an open world of possible referents before a bounded contract exists | Rejected: generic entity extraction and broad parsing are outside the family |
| Treat any existing `MentionBinding` as runnable | Collapses evidence and authority into one edge | Rejected: a binding may propose/ground, but only an organ-specific assessment may close |
| Add proposal-first local quantity/entity assessment over existing `ProblemFrame` facts | Preserves the proposal → binding → assessment authority gradient | Selected: smallest reusable and refusal-first slice |
| Begin with `state_change.transition` | Adds events, temporal order, actor continuity, and transition semantics | Rejected for this slice: it is a larger manifold with different confusers |

The selected direction is structurally minimal: reuse exact `GroundedScalar`,
`GroundedMention`, `GroundedUnit`, `MentionBinding`, and `SourceSpan` evidence;
add only the family declaration, proposal seam, and separate diagnostic
assessment necessary to make closure explicit.

## 3. Non-goals

The future implementation PR is not authorized to add or change:

- broad noun parsing or generic entity extraction;
- a universal IR, generic knowledge blob, or cross-domain entity ontology;
- benchmark-specific grammar, case-ID logic, answer mining, or a
  GSM8K-shaped substrate;
- serving admission, serving dispatch, committed answer production, or response
  realization;
- state-change recognition or `state_change.transition`;
- transaction, acquisition, transfer, consumption, or loss recognition;
- rate, percent, partition, proportional-change, or comparison logic;
- pronoun/coreference resolution or cross-sentence inference beyond exact local
  evidence;
- derivation-organ behavior or raw-prose parsing inside a derivation organ;
- sealed/eval/report artifacts, packs, policy, identity, recall, Vault, field,
  algebra, or runtime mutation;
- `determine(answer=False)` or any inference that absence means false.

No family may become runnable merely because a nearby token resembles a noun.
No score, proximity heuristic, or assessment result may synthesize a proposal.

## 4. Target seam and authority gradient

The future implementation must obey this one-way seam:

```text
surface quantity/entity cue
→ ConstructionProposal(status="proposed")
→ exact mention/entity/quantity binding
→ ContractAssessment
→ diagnostic runnable/refused
```

The phases have distinct authority:

1. **Proposal:** exact surface evidence may propose
   `binding.quantity_entity`. The proposal is born with
   `status == "proposed"`, `diagnostic_only is True`, and
   `serving_allowed is False`.
2. **Grounding:** existing `ProblemFrame` evidence binds a quantity mention to
   an entity mention through `MentionBinding(binding_type="quantity_entity")`.
   A unit, when present, is connected only through the existing
   `MentionBinding(binding_type="quantity_unit")` form.
3. **Assessment:** an organ-specific `ContractAssessment` checks cardinality,
   provenance, exact spans, kind/unit disposition, locality, and confusers.
4. **Disposition:** only the assessment may report diagnostic
   `runnable=True`; otherwise it reports typed missing bindings or unresolved
   hazards and refuses.

No proposal may be derived from `ContractAssessment` output. The legacy
assessment-backed `make_proposal()` adapter is not authorized for this family.
The family must enter through `propose_construction()` before its assessment is
dispatched. A frame with no `binding.quantity_entity` proposal must not dispatch
the family contract.

## 5. Minimal first implementation slice

The smallest allowed future PR may:

1. Register `binding.quantity_entity` in the diagnostic construction catalog,
   preserving `diagnostic_only=True` and `serving_allowed=False`.
2. Recognize only local quantity/entity evidence already exposed by
   `ProblemFrame`, `GroundedScalar`, `GroundedMention`, `GroundedUnit`, and
   `MentionBinding` machinery. It may not add a second raw-text parser.
3. Create a diagnostic-only `ConstructionProposal` from exact local source
   evidence before assessment, with initial `status="proposed"`.
4. Attach exact, non-synthetic `SourceSpan` evidence whose text equals the
   corresponding original-text slice.
5. Add one organ-specific `ContractAssessment` for this family.
6. Refuse if the entity span, quantity span, quantity kind/unit disposition, or
   provenance is missing, synthetic, conflicting, or ambiguous.
7. Produce no serving output and make no serving-path import or dispatch change.
8. Preserve `wrong_ids == []` on both serving train and holdout lanes.

The implementation may make a narrowly necessary type-only addition for a
closed quantity-kind disposition if existing types cannot represent the
obligation. Such a type must be local to this family, must not become a generic
entity ontology, and must not authorize new parsing. Otherwise, existing types
must be reused.

This documentation PR intentionally does not flip the descriptive
`FoundationalFamilySpec.implementation_authorized` field. That mechanical gate
remains false until the authorized implementation PR actually introduces the
bounded family seam. At that point only `binding.quantity_entity` may be set to
true; `state_change.transition` must remain false.

## 6. Roles and evidence obligations

The family must use existing names where the substrate already has them. It
must distinguish semantic roles from closure evidence so that provenance does
not masquerade as an entity role.

### 6.1 Catalog semantic roles

| Name | Obligation | Existing representation |
|---|---|---|
| `quantity` | Required. Exactly one quantity mention must link through `fact_id` to exactly one `GroundedScalar`. | `GroundedMention(kind="quantity")` + `GroundedScalar` |
| `entity` | Required. Exactly one local entity/object mention must be the target of the selected binding. | Existing `GroundedMention`; do not add a broad extractor |
| `unit` | Optional as a role, but its disposition is mandatory. If present it must be grounded and bound to the same quantity. | `GroundedMention(kind="unit")` + `GroundedUnit` + `quantity_unit` binding |

### 6.2 Required assessment evidence

| Name | Obligation |
|---|---|
| `quantity_kind` | Required closed disposition: `count` or `measurement`. It must be grounded by local evidence, not guessed from a missing unit. If neither can be justified, refuse. |
| `provenance_span` | Required exact `SourceSpan` evidence for the quantity, entity, and any unit; each span must be source-backed and equal to the corresponding original text slice. |
| `local_binding_relation` | Required existing `MentionBinding(binding_type="quantity_entity")` from the selected quantity mention to the selected entity mention, with its exact evidence spans. |

`quantity_kind`, `provenance_span`, and `local_binding_relation` are closure
obligations; they do not authorize a broad ontology or a new universal relation
model. "Unit explicitly absent" means the assessment records that no unit
mention participates in the bounded local evidence while `count` is positively
grounded. Mere absence of a unit token must not be converted into a count claim.

## 7. Closure conditions

The diagnostic assessment may report `runnable=True` only when all of the
following hold:

- exactly one `GroundedScalar` is selected;
- exactly one local entity/object `GroundedMention` is selected and bound;
- the selected quantity mention resolves to that scalar through `fact_id`;
- exactly one selected `quantity_entity` binding connects the quantity to the
  entity;
- all quantity, entity, binding, and unit evidence spans are exact,
  non-synthetic, ordered, within bounds, and equal to original text slices;
- quantity and entity provenance is preserved without replacement or widening;
- `quantity_kind` is positively grounded as `count` or `measurement`;
- a unit is either explicitly grounded through the selected quantity's
  `quantity_unit` binding or explicitly absent under a positively grounded
  count construction;
- no competing nearby entity or competing scalar creates another plausible
  local binding;
- the evidence requires no pronoun resolution, antecedent repair, or
  cross-sentence leap;
- the proposal already exists and remains separate from the assessment.

Closure is diagnostic readiness only. It does not verify a mathematical answer,
authorize a downstream construction, or admit anything to serving.

## 8. Refusal conditions

The assessment must refuse, with stable organ-specific blockers or hazards, on:

- multiple plausible entities for the quantity;
- a missing entity mention;
- a quantity without positively grounded count or measurement context;
- pronoun-only binding without independently established antecedent evidence;
- sentence- or clause-level ambiguity that prevents a unique local edge;
- unit/kind conflict or a unit bound to a different quantity;
- synthetic, widened, overlapping, out-of-bounds, or text-mismatched evidence
  spans;
- a cross-sentence entity leap;
- multiple plausible quantities for one entity when the local topology does not
  disambiguate them;
- list or enumeration topology with ambiguous pairing;
- percent, rate, comparison, partition, or transition evidence that requires
  another family to interpret;
- any benchmark-shaped shortcut, case-specific branch, or assessment-backed
  proposal synthesis.

Unknown or absent evidence remains unknown. Refusal is the correct result; the
implementation must not silently select the nearest candidate.

## 9. Mandatory confuser suite design

The future PR must add positive examples plus at least these refusal/confuser
cases:

1. quantity with no entity;
2. entity with no quantity;
3. two nearby entities and one number;
4. two numbers and one entity;
5. percent, rate, and comparison surfaces that must not close as generic
   `quantity_entity` evidence;
6. a state-change sentence that may expose a local quantity/entity binding but
   must not propose or dispatch `state_change.transition`;
7. pronoun reference without a resolved antecedent;
8. a cross-sentence entity leap;
9. a unit/kind conflict;
10. list/enumeration ambiguity.

The state-change confuser protects family separation: local quantity/entity
grounding may exist inside a sentence, but this family must neither interpret
the event nor become a transition contract.

## 10. Interaction with existing proposal-first families

`binding.quantity_entity` is foundational evidence that later contracts may
consume. It does not replace, wrap, or weaken:

- `proportional_change.decrease_to_fraction`; or
- `partition.percent_partition`.

The new family must not alter their proposal triggers, roles, assessments,
dispatch, statuses, blocker labels, or serving posture. It must not call their
contracts, backdoor into their relation types, or make either family runnable
by treating a quantity/entity edge as sufficient evidence. The
`_PROPOSAL_FIRST_FAMILIES` fence established by #844 remains load-bearing, and
all #841–#844 seam invariants must remain green.

Future composition, if separately authorized, must be explicit and monotonic:
those families may require a closed quantity/entity assessment as one input,
but retain their own independent obligations and authority.

## 11. Acceptance criteria for the future implementation PR

The future PR must prove all of the following:

- every proposal begins with `status == "proposed"`;
- every proposal has `diagnostic_only is True` and
  `serving_allowed is False`;
- `ContractAssessment` remains the separate and sole closure authority;
- no assessment output is used to construct or recover a proposal;
- a proposal-free frame does not dispatch the family contract;
- exact source spans equal the corresponding original-text slices;
- quantity, entity, unit/kind, locality, and provenance obligations are all
  positively closed before `runnable=True`;
- every mandatory confuser refuses without nearest-candidate fallback;
- no new raw-prose/local-regex derivation surface is added;
- only the `binding.quantity_entity` foundational registry entry changes its
  `implementation_authorized` gate; `state_change.transition` remains false;
- existing #841/#842/#843/#844 tests remain green;
- serving train and holdout retain `wrong_ids == []`;
- deterministic replay produces the same proposal, bindings, assessment, and
  ordering for the same input;
- no serving, derivation-organ, sealed/eval/report, pack, policy, identity,
  recall, Vault, field, or algebra file changes are present.

## 12. Required validation for the future implementation PR

Run:

```bash
uv run python -m pytest -q \
  tests/test_construction_affordances.py \
  tests/test_construction_proposal_seam.py \
  tests/test_foundational_families.py \
  tests/test_problem_frame_builder.py \
  tests/test_problem_frame_contracts.py \
  tests/test_proportional_decrease_proposal.py \
  tests/test_percent_partition_proposal.py \
  tests/test_kernel_no_new_legacy_derivation_surfaces.py

uv run python -m core.cli test --suite smoke -q

uv run python -m compileall -q \
  generate/construction_affordances.py \
  generate/foundational_families.py \
  generate/problem_frame.py \
  generate/problem_frame_builder.py \
  generate/problem_frame_contracts.py

uv run ruff check .

git diff --check
```

The future PR must also run the repository's canonical train and holdout serving
checks and report both `wrong_ids` lists explicitly. This authorization does not
permit writing or changing those eval artifacts.

## 13. Explicit authorization boundary

**This PR authorizes a future implementation slice for
`binding.quantity_entity` only.**

It does not authorize `state_change.transition`.
It does not authorize serving.
It does not authorize general entity extraction.
It does not authorize broad parsing.

Authorization becomes effective only after this document merges. Any widening
of family, parser surface, inference distance, serving posture, or mutation
surface requires a separate authorization.

## 14. Justification: the masterstroke

The key structural choice is to model ambiguity as non-closure of a local
relation, not as a classification error to be repaired by a broader parser.
That aligns the representation with the problem's intrinsic geometry: one
quantity node, one entity node, one provenance-preserving edge, and a conjugate
assessment that can oppose an unsafe proposal. Proposal and assessment form the
required forward/corrective pair. Exact bindings carry meaning forward;
refusal removes distortion when the topology is not unique.

The result is reusable without becoming universal: later families can consume
the grounded edge, but none inherit authority to answer, transition, compare,
partition, or serve.

## 15. Copy-paste brief for the next PR

> **PR title:** `feat(kernel): introduce diagnostic quantity-entity proposal seam`
>
> **Dependency:** Start only after
> `docs(kernel): authorize quantity-entity foundational implementation slice`
> has merged. Create a fresh worktree from current `origin/main` and prove the
> authorization commit is in the base before editing.
>
> Implement the first diagnostic-only proposal-first slice for
> `binding.quantity_entity`. Reuse only local evidence already exposed by
> `ProblemFrame`, `GroundedScalar`, `GroundedMention`, `GroundedUnit`, and
> `MentionBinding`. Register the family with required roles `quantity` and
> `entity`, optional role `unit`, and explicit closure obligations for
> `quantity_kind`, `provenance_span`, and `local_binding_relation`. Create
> `ConstructionProposal(status="proposed", diagnostic_only=True,
> serving_allowed=False)` from exact source evidence before assessment. Add a
> separate organ-specific `ContractAssessment`; dispatch it only when the
> proposal exists. Refuse on ambiguous entity/scalar topology, unresolved
> kind/unit disposition, non-exact or synthetic provenance, pronoun-only or
> cross-sentence binding, and every confuser listed in the authorization.
>
> Do not add broad noun/entity parsing, state-change/event semantics, a
> universal IR, benchmark-specific grammar, serving behavior, answer
> production, or any assessment-backed proposal path. Do not touch derivation
> organs, `generate/math_candidate_graph.py`, eval/sealed/report artifacts,
> packs, policy, identity, recall, Vault, field, algebra, or serving runtime.
> Preserve the #841–#844 seams and prove train/holdout `wrong_ids == []` using
> the validation commands in this authorization.
