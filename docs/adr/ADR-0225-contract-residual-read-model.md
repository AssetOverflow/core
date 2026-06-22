# ADR-0225: ContractResidual Read-Model

**Status:** Proposed
**Author:** Antigravity
**Date:** 2026-06-22

## Context

CORE has introduced a proposal-first diagnostic construction pipeline for representing mathematical word problems and relations within the semantic substrate. In this architecture:
* Surface and process evidence is scanned to produce hypothesis-only `ConstructionProposal` records with `status="proposed"`.
* Mentions, bindings, and local roles are bound to ground these proposals.
* `ContractAssessment` serves as the sole runnable/refused authority, verifying the algebraic and semantic validity of the candidate structures.
* PR #859 aligned the `state_change.unary_delta` (candidate organ `"unary_delta_transition"`) implementation with its accepted spec.

As the pipeline scales, downstream planning needs a deterministic, structured mechanism to understand *why* a particular contract was refused (i.e., why a diagnostic organ did not close), without introducing unreviewed search behavior, serving authority, or mutative repair loops.

## Problem

Currently, `ContractAssessment` records capture diagnostic failure information using:
* `candidate_organ`
* `missing_bindings`
* `unresolved_hazards`
* `runnable` (boolean status)
* `explanation` (prose description)
* `evidence_spans`

While this structure is sufficient for simple validation, downstream planning and operator reasoning require a normalized, structured **read-model** to classify failures into fine-grained, structured categories, such as:
* Missing required role bindings
* Ambiguity in roles or relations
* Inexact provenance spans
* Unsupported topologies
* Blocking hazards

This read-model must classify the diagnostics deterministically, without changing the underlying contract definitions, making search decisions, or granting compute budget.

## Decision

We propose the introduction of a scoped, read-only `ContractResidual` read-model.

### Normative Authority Rule
> [!IMPORTANT]
> `ContractAssessment` remains the sole runnable/refused authority.
> `ContractResidual` is a pure read-only projection over `ContractAssessment` records. It **never** authorizes serving, search, mutation, learning, answer production, or repair of the `ProblemFrame`.

### Conceptual Shape
The conceptual schema for `ContractResidual` is defined as follows:

```python
@dataclass(frozen=True, slots=True)
class ContractResidual:
    residual_id: str
    candidate_organ: str
    family_id: str | None
    residual_kind: ResidualKind
    residual_code: str
    source_axis: ResidualSourceAxis
    evidence_spans: tuple[SourceSpan, ...]
    explanation: str
```
*(Note: This is documentation only. The Python classes are not implemented in this PR.)*

## ResidualKind Taxonomy

We define a closed taxonomy of `ResidualKind` to classify existing `ContractAssessment` labels:

1. **MISSING_PROPOSAL**: The required construction proposal is absent.
2. **MISSING_RELATION**: The underlying relation edge (e.g., `quantity_entity`) is missing.
3. **MISSING_ROLE**: A required role slot on the relation is unbound.
4. **AMBIGUOUS_RELATION**: Multiple candidate relations exist with no unique resolution.
5. **AMBIGUOUS_ROLE**: A role binds to multiple candidate mentions ambiguously.
6. **INEXACT_PROVENANCE**: Spans or quantities lack exact, source-grounded provenance.
7. **NONLOCAL_BINDING**: The binding requires non-local references (e.g., pronoun resolution or cross-sentence leaps).
8. **UNSUPPORTED_TOPOLOGY**: The clause contains grammar or structure unsupported by the family (e.g., passive voice, multiple coordinate actors).
9. **UNIT_OBJECT_CONFLICT**: Grounded quantity units conflict with the object type (e.g., count vs. measurement mismatch).
10. **HAZARD_BLOCKED**: An active semantic confuser or hazard blocks the contract.
11. **TARGET_UNBOUND**: The question target cannot be bound or is missing.
12. **CONTRACT_GAP_UNCLASSIFIED**: A fallback classification for unmapped contract failures (non-searchable).

### Rules
* The taxonomy classifies existing `ContractAssessment` labels; it does not replace them.
* `residual_code` must preserve the original missing binding or unresolved hazard label exactly.
* `CONTRACT_GAP_UNCLASSIFIED` is restricted to non-searchable diagnostic fallback only.
* Broad, vague, or non-deterministic kinds (e.g., `MATH_FAILED`, `REASONING_FAILED`, `UNKNOWN_TRUTH`) are database-forbidden and structurally disallowed.

## ResidualSourceAxis

To decouple the *kind* of failure from the *structural layer* that produced it, we define `ResidualSourceAxis`:

1. **PROPOSAL**: Bounded proposal detection layer.
2. **RELATION**: Binding graph/relational edge layer.
3. **ROLE**: Slot-binding role layer.
4. **PROVENANCE**: Source-grounding and span layer.
5. **LOCALITY**: Clause and sentence distance bounds.
6. **TOPOLOGY**: Grammatical and structural patterns.
7. **HAZARD**: Cognitive/confuser hazard detection.
8. **TARGET**: Question target binding.
9. **UNIT_OBJECT**: Count/measurement unit boundary.
10. **UNKNOWN**: Fallback for unmapped boundaries.

## Mapping from Existing Labels

The mapping from existing contract labels (missing bindings and unresolved hazards) to `ResidualKind` and `ResidualSourceAxis` is deterministic. The following table maps the labels from current contract families:

| Existing Contract Label | ResidualKind | ResidualSourceAxis | Notes / Rationale |
|---|---|---|---|
| **Quantity Entity (`binding.quantity_entity`)** | | | |
| `quantity_entity_proposal_required` | `MISSING_PROPOSAL` | `PROPOSAL` | Missing the core proposal |
| `quantity_unbound` | `MISSING_ROLE` | `ROLE` | Missing the quantity role |
| `entity_unbound` | `MISSING_ROLE` | `ROLE` | Missing the entity role |
| `quantity_ambiguous` | `AMBIGUOUS_ROLE` | `ROLE` | Multiple candidate quantities |
| `entity_ambiguous` | `AMBIGUOUS_ROLE` | `ROLE` | Multiple candidate entities |
| `local_binding_relation_unbound` | `MISSING_RELATION` | `RELATION` | No linking relation |
| `local_binding_relation_ambiguous` | `AMBIGUOUS_RELATION` | `RELATION` | Multiple local bindings |
| `quantity_kind_unresolved` | `MISSING_ROLE` | `ROLE` | Missing type disposition |
| `unit_kind_conflict` | `UNIT_OBJECT_CONFLICT` | `UNIT_OBJECT` | Count vs. measure conflict |
| `provenance_span_inexact` | `INEXACT_PROVENANCE` | `PROVENANCE` | Spans do not match exactly |
| `quantity_entity_nonlocal` | `NONLOCAL_BINDING` | `LOCALITY` | Binding spans are non-local |
| `competing_family_context` | `HAZARD_BLOCKED` | `HAZARD` | Hazard from competing triggers |
| `percent_change_vs_percent_of` | `HAZARD_BLOCKED` | `HAZARD` | Percentage ambiguity hazard |
| **Fraction Decrease (`proportional_change.decrease_to_fraction`)** | | | |
| `decrease_relation_ambiguous` | `AMBIGUOUS_RELATION` | `RELATION` | Ambiguous relation path |
| `base_quantity_unbound` | `MISSING_ROLE` | `ROLE` | Missing base quantity role |
| `scale_unbound` | `MISSING_ROLE` | `ROLE` | Missing scale fraction role |
| `state_entity_unbound` | `MISSING_ROLE` | `ROLE` | Missing state entity role |
| `base_quantity_provenance_missing` | `INEXACT_PROVENANCE` | `PROVENANCE` | Base quantity lacks provenance |
| `scale_provenance_missing` | `INEXACT_PROVENANCE` | `PROVENANCE` | Scale lacks provenance |
| `unit_continuity_unproven` | `UNIT_OBJECT_CONFLICT` | `UNIT_OBJECT` | Mismatched units along continuity axis |
| `delta_decrease_target_unbound` | `TARGET_UNBOUND` | `TARGET` | Unbound decrease target |
| `delta_decrease_target_required` | `TARGET_UNBOUND` | `TARGET` | Required decrease target is missing |
| `state_entity_continuity_unproven` | `HAZARD_BLOCKED` | `HAZARD` | Ambiguity in entity tracking |
| `scale_out_of_range` | `HAZARD_BLOCKED` | `HAZARD` | Scale value outside (0, 1) bounds |
| **Percent Partition (`partition.percent_partition`)** | | | |
| `grounded_partition_subgroup` | `MISSING_ROLE` | `ROLE` | Missing partition part roles |
| `grounded_whole_entity` | `MISSING_ROLE` | `ROLE` | Missing whole role entity |
| `original_whole_unbound` | `MISSING_ROLE` | `ROLE` | Whole is unbound |
| `multiple_original_whole_candidates` | `AMBIGUOUS_ROLE` | `ROLE` | Ambiguity between whole candidates |
| `partition_subgroups_not_distinct` | `HAZARD_BLOCKED` | `HAZARD` | Subgroups share entities/mentions |
| `percent_subgroup_links_incomplete` | `UNSUPPORTED_TOPOLOGY` | `TOPOLOGY` | Incomplete partition topology |
| `grounded_question_target` | `TARGET_UNBOUND` | `TARGET` | Unbound question target |
| `forward_aggregate_target_required` | `TARGET_UNBOUND` | `TARGET` | Aggregate target required for partition |
| `inverse_topology_unlicensed` | `UNSUPPORTED_TOPOLOGY` | `TOPOLOGY` | Inverse query topology unsupported |
| **Unary Delta (`state_change.unary_delta`)** | | | |
| `unary_delta_proposal_required` | `MISSING_PROPOSAL` | `PROPOSAL` | Missing the core proposal |
| `unary_delta_relation_ambiguous` | `AMBIGUOUS_RELATION` | `RELATION` | Ambiguous relation path |
| `action_cue_unbound` | `MISSING_ROLE` | `ROLE` | Missing action cue role |
| `delta_quantity_unbound` | `MISSING_ROLE` | `ROLE` | Missing quantity role |
| `delta_quantity_ambiguous` | `AMBIGUOUS_ROLE` | `ROLE` | Multiple candidate quantities |
| `changed_object_unbound` | `MISSING_ROLE` | `ROLE` | Missing changed object role |
| `changed_object_ambiguous` | `AMBIGUOUS_ROLE` | `ROLE` | Multiple candidate objects |
| `local_binding_relation_unbound` | `MISSING_RELATION` | `RELATION` | No linking relation |
| `direction_unbound` | `MISSING_ROLE` | `ROLE` | Missing direction role |
| `quantity_kind_unresolved` | `MISSING_ROLE` | `ROLE` | Missing type disposition |
| `unit_object_conflict` | `UNIT_OBJECT_CONFLICT` | `UNIT_OBJECT` | Count vs. measure conflict |
| `provenance_span_inexact` | `INEXACT_PROVENANCE` | `PROVENANCE` | Spans do not match exactly |
| `quantity_entity_nonlocal` | `NONLOCAL_BINDING` | `LOCALITY` | Spans are non-local |
| `pronoun_antecedent_unresolved` | `NONLOCAL_BINDING` | `LOCALITY` | Pronoun requires reference resolution |
| `event_assertion_unlicensed` | `UNSUPPORTED_TOPOLOGY` | `TOPOLOGY` | Unlicensed event assertion topology |
| `passive_voice_unsupported` | `UNSUPPORTED_TOPOLOGY` | `TOPOLOGY` | Passive voice topology is unsupported |
| `multiple_actor_surface` | `UNSUPPORTED_TOPOLOGY` | `TOPOLOGY` | Multiple coordinate actors unsupported |

*(Note: No new runtime labels are created in this PR. If a label is unclear or needs modification, it must go through a formal preflight review before implementation.)*

## Non-Authority Guarantees

To prevent scope creep and preserve the deterministic nature of the cognitive engine:
* **No proposals:** Residuals describe why a candidate contract failed to close; they are never proposals and cannot be registered in the construction catalog.
* **No proofs:** Residuals carry no proof value and do not establish the validity of any mathematical assertion.
* **No search commands:** Residuals do not instruct the engine to expand the candidate graph, change search paths, or adjust retry strategies.
* **No budget grants:** Residuals do not allocate compute budget, trigger model-based retries, or define practice lanes.
* **No teaching proposals:** Residuals are not mutation proposals for training, packs, or policies.
* **No Workbench actions:** Residuals do not mutate the database or trigger execution. They are strictly read-only diagnostics for visual inspection.
* **No serving decisions:** Serving paths remain entirely frozen. Residuals cannot flip a contract to `runnable`, repair a `ProblemFrame`, or generate answers.

## Relationship to SearchGate

The boundary between `ContractResidual` and the future SearchGate is strictly delineated:
* **Future Input Only:** SearchGate may later consume `ContractResidual` records as input to make search decisions, but SearchGate is a separate future ADR/PR.
* **Forbidden on `ContractResidual`:**
  * No `search_eligible` boolean on `ContractResidual`.
  * No compute budget configuration.
  * No retry policy or loop rules.
  * No search run schema.
  * No candidate expansion or node generation algorithms.
  * No sealed or practice lane integration.

## Relationship to Workbench

The boundary between `ContractResidual` and Workbench is defined as:
* **Read-Only Display Only:** Workbench may later display `ContractResidual` records as read-only operator diagnostics.
* **Forbidden in Workbench:**
  * No UI implementation of fix actions (e.g., "fix this" buttons).
  * No mutation controls.
  * No editing of proposals from the residual interface.
  * No human feedback or interactive correction flow linked to residuals.

## Determinism and Replay

`ContractResidual` projections must be fully deterministic and replay-stable:
* **Stable IDs:** The `residual_id` must be constructed using a stable hashing mechanism from its constituent fields:
  ```text
  residual_id = stable_hash(candidate_organ, residual_kind, residual_code, ordered_evidence_spans)
  ```
  *(Note: Hashing code is not implemented in this PR.)*
* **Preserved Spans:** Source spans must be preserved exactly without widening, concatenation, or synthesis.
* **Deterministic Ordering:** Residuals must be ordered deterministically based on their `residual_id`.
* **No Side Effects:** Residual generation must not contain timestamps, random IDs, environment-dependent data, or model-generated text.

## Examples

### Example A: Missing Changed Object / Missing Relation
**Input:** `"Tom gained 3."`
* **Behavior:** A unary-delta proposal exists based on the exact cue `"gained"`.
* **Contract Assessment:** `ContractAssessment(candidate_organ="unary_delta_transition")` refuses due to a missing changed object and local relation.
* **Residual Projection:**
  ```python
  ContractResidual(
      residual_id="stable_hash_a",
      candidate_organ="unary_delta_transition",
      family_id="state_change.unary_delta",
      residual_kind=ResidualKind.MISSING_ROLE,
      residual_code="changed_object_unbound",
      source_axis=ResidualSourceAxis.ROLE,
      evidence_spans=(SourceSpan(text="gained", start=4, end=10),),
      explanation="The changed object role is unbound.",
  )
  ```
* **Status:** No answer/search/serving is triggered.

### Example B: Missing Delta Quantity
**Input:** `"Tom gained apples."`
* **Behavior:** The cue `"gained"` proposes. The quantity is missing.
* **Contract Assessment:** Refuses due to missing `delta_quantity`.
* **Residual Projection:**
  ```python
  ContractResidual(
      residual_id="stable_hash_b",
      candidate_organ="unary_delta_transition",
      family_id="state_change.unary_delta",
      residual_kind=ResidualKind.MISSING_ROLE,
      residual_code="delta_quantity_unbound",
      source_axis=ResidualSourceAxis.ROLE,
      evidence_spans=(SourceSpan(text="gained", start=4, end=10),),
      explanation="The delta quantity role is unbound.",
  )
  ```
* **Status:** No synthetic quantity is introduced; remains refused.

### Example C: Unsupported Passive Topology
**Input:** `"3 apples were gained by Tom."`
* **Behavior:** The passive voice cue structures are unsupported by the closed recognizer.
* **Contract Assessment:** Refuses due to passive topology / event assertion unlicensed.
* **Residual Projection:**
  ```python
  ContractResidual(
      residual_id="stable_hash_c",
      candidate_organ="unary_delta_transition",
      family_id="state_change.unary_delta",
      residual_kind=ResidualKind.UNSUPPORTED_TOPOLOGY,
      residual_code="passive_voice_unsupported",
      source_axis=ResidualSourceAxis.TOPOLOGY,
      evidence_spans=(SourceSpan(text="gained", start=14, end=20),),
      explanation="Passive voice topology is unsupported.",
  )
  ```
* **Status:** No role repair is attempted.

### Example D: Unit-Object Conflict
**Input:** `"Tom gained 3 degrees."`
* **Behavior:** Quantity unit `"degrees"` conflicts with object count/entity expectations.
* **Contract Assessment:** Refuses due to `unit_object_conflict`.
* **Residual Projection:**
  ```python
  ContractResidual(
      residual_id="stable_hash_d",
      candidate_organ="unary_delta_transition",
      family_id="state_change.unary_delta",
      residual_kind=ResidualKind.UNIT_OBJECT_CONFLICT,
      residual_code="unit_object_conflict",
      source_axis=ResidualSourceAxis.UNIT_OBJECT,
      evidence_spans=(SourceSpan(text="degrees", start=13, end=20),),
      explanation="Quantity unit conflicts with object type.",
  )
  ```
* **Status:** No arithmetic or state update is performed.

## Non-Goals

This ADR explicitly does not cover:
* Implementation of `ContractResidual` or Python dataclasses.
* Integration with SearchGate, ComputeBudgetPolicy, or GeometricSearchRun.
* Mutating or displaying in Workbench.
* Serving path alterations or runtime dispatch.
* Adding new contract labels or modifying the existing assessment logic.
* Adding tests, reports, evals, teaching loops, or semantic pack modifications.
* Performing arithmetic, answer derivation, or solving.

## Acceptance Criteria

This ADR is successfully ratified only if:
1. It is documentation-only.
2. It defines `ContractResidual` as a strict read-only projection.
3. It preserves `ContractAssessment` as the sole runnable authority.
4. It defines a small closed taxonomy for `ResidualKind` and `ResidualSourceAxis`.
5. It deterministically maps existing labels without inventing runtime labels.
6. It freezes SearchGate/ComputeBudget/Workbench implementation boundaries.
7. `git diff --check` passes cleanly.
