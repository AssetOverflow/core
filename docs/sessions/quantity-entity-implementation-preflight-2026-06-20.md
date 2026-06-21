# PREFLIGHT: `binding.quantity_entity` Implementation Map

**Agent:** gpt55
**Date:** 2026-06-20
**Target Branch:** `docs/kernel-quantity-entity-implementation-preflight`
**Controlling Authorization:** `docs/sessions/quantity-entity-foundational-slice-authorization-2026-06-20.md`

This document maps the exact implementation paths and boundaries for the upcoming `binding.quantity_entity` diagnostic proposal-first slice. It ensures the xHigh agent implements only the bounded surface authorized, preventing leakage into serving, broad parsing, or state-change semantics.

## 1. Current Seam Map

The proposal-first construction seam is established and strictly governed by PRs #841–#844.

- **Construction Catalog (`generate/construction_affordances.py`):** Defines immutable `ConstructionFamily` records, holding required roles, hazards, target semantics, and the `diagnostic_only=True` / `serving_allowed=False` gates.
- **Proposal Factory (`propose_construction`):** Creates a `ConstructionProposal(status="proposed")` from exact surface evidence *before* assessment.
- **ProblemFrame Publication (`generate/problem_frame_builder.py`):** The `build_problem_frame()` pipeline currently generates `decrease_to_fraction` and `percent_partition` proposals by scanning raw text, then adds them to the `ProblemFrame` alongside extracted facts, mentions, and bindings.
- **Contract Dispatch (`generate/problem_frame_contracts.py`):** `assess_contracts()` checks `frame.proposals` for specific `family_id`s and routes them to their corresponding assessment functions (e.g., `assess_fraction_decrease`).
- **Assessment Authority:** The individual `ContractAssessment` function is the sole authority for reporting `runnable=True` or `runnable=False`. The proposal remains a hypothesis.
- **Legacy Fence:** `make_proposal()` explicitly blocks migrated proposal-first families.

## 2. Quantity-Entity Target Map

To implement the authorized slice without broadening parsers, the following targeted additions are needed:

1. **Foundational Registry (`generate/foundational_families.py`):**
   - Flip `implementation_authorized = True` for `_QUANTITY_ENTITY_BINDING` only.
2. **Construction Catalog (`generate/construction_affordances.py`):**
   - Add `_QUANTITY_ENTITY_FAMILY = ConstructionFamily(...)` mirroring the foundational spec.
   - Register it in `_CATALOG` and `_PROPOSAL_FIRST_FAMILIES`.
3. **Proposal Publication (`generate/problem_frame_builder.py`):**
   - Extract proposals directly from the *already existing* `MentionBinding(binding_type="quantity_entity")` records built by `_extract_bindings()`. Do not add a new regex parser for nouns.
   - For each valid quantity-entity binding, call `propose_construction("binding.quantity_entity", evidence_spans)`.
4. **Contract Assessment (`generate/problem_frame_contracts.py`):**
   - Add `assess_quantity_entity(frame: ProblemFrame) -> ContractAssessment`.
   - Update `_CONTRACT_REGISTRY` to map `quantity_entity` to this function.
   - In `assess_contracts()`, dispatch to `assess_quantity_entity(frame)` if the proposal exists.
5. **Test Extensions:**
   - Extend `tests/test_construction_affordances.py` and `tests/test_construction_proposal_seam.py`.
   - Create `tests/test_quantity_entity_proposal.py` for full boundary and confuser testing.

## 3. Existing Type Inventory

The implementation must exclusively use these existing structures:

- **`ProblemFrame`**: Exposes `.quantities`, `.units`, `.mentions`, `.bindings`, `.hazards`, and `.proposals`.
- **`GroundedScalar`**: Represents the numeric value (`.value`), exact `.provenance`, and `.fact_id`.
- **`GroundedMention`**: Represents the exact text matched (`.surface`), `.span`, `.kind` (`"quantity"`, `"object"`, `"unit"`), and the `.fact_id` it maps to.
- **`MentionBinding`**: Represents topological edges. `.binding_type` will be `"quantity_entity"` or `"quantity_unit"`, connecting `.source_mention_id` to `.target_mention_id`.
- **`SourceSpan`**: Provides the exact textual provenance (`.text`, `.start`, `.end`).
- **`ConstructionProposal`**: Created via `propose_construction()`, carrying `.role_obligations` and initialized with `.status="proposed"`.
- **`ContractAssessment`**: Yields `.missing_bindings`, `.unresolved_hazards`, and `.runnable`.

## 4. Implementation Hazards

The upcoming xHigh PR must actively avoid these known confusers:

- **Broad noun parsing / generic extraction:** Do not add NLP taggers or wide regexes to `_extract_mentions`. Rely entirely on the existing `_ENTITY_AFTER_QUANTITY_RE`, `_FRACTION_ENTITY_RE`, `_COPULAR_PARTITION_RE`, and `_TRANSFER_RE` behavior.
- **Synthetic spans:** Every `evidence_spans` element must perfectly slice the raw problem text. No string concatenation or synthetic gap-filling.
- **Cross-sentence inference / Pronoun leakage:** Do not attempt to resolve "it" or "them". If the exact local entity mention is not contiguous or clearly bound by existing heuristics, the contract must refuse.
- **State-change leakage:** A quantity/entity binding inside "He gained 5 pounds" is valid as grounding evidence, but it must not synthesize a `state_change.transition` proposal.
- **Derivation / serving leakage:** The assessment must remain diagnostic. Do not connect it to `generate/math_candidate_graph.py` or modify the canonical evaluation reports (train `wrong_ids` must remain `[]`).
- **Proposal mutation:** Do not use `make_proposal()`. The proposal is a hypothesis and remains unmodified by the assessment.

## 5. Fixture Inventory

Existing test phrases in `core` that provide safe local binding vs. mandatory refusal:

| Existing Phrase / Fixture | Expected Disposition | Reason |
|---|---|---|
| `"Tom gave Ana 3 marbles."` | **Runnable** | Quantity `"3"` bound to entity `"marbles"`. |
| `"There are 4 full boxes and 3 loose crayons."` | **Runnable** | Multiple valid bindings: `"4"` → `"boxes"`, `"3"` → `"crayons"`. |
| `"A block of iron has a mass of 12 grams."` | **Runnable** | Quantity `"12"`, unit `"grams"`, bound properly. |
| `"Mia spent 50% of her money."` | **Refusal** | `"50%"` triggers percent/partition; missing direct quantity/entity count. |
| `"A quarter of the class left."` | **Refusal / Ambiguous** | `"quarter"` is a scalar but acts as a percent/partition. |
| `"Marion has 1/4 more than what Yun currently has..."` | **Refusal** | Comparison operator (`"more than"`); `"1/4"` does not bind to a direct entity. |

## 6. Test Plan

The xHigh implementation must provide `tests/test_quantity_entity_proposal.py` mirroring the rigour of `test_percent_partition_proposal.py`:

1. **Catalog & Posture Check:** `test_supported_case_has_diagnostic_catalog_proposal` verifies `status="proposed"`, `diagnostic_only=True`, and `serving_allowed=False`.
2. **Execution Ordering:** `test_proposal_precedes_role_binding_and_contract_assessment` using `monkeypatch` to prove proposal happens before `ContractAssessment`.
3. **Legacy Fence:** `test_migrated_family_does_not_use_legacy_assessment_adapter` ensures `make_proposal` is not called.
4. **Authority:** `test_contract_assessment_remains_runnable_authority` ensures the proposal does not declare itself runnable.
5. **Exact Spans:** Verify `evidence_spans` exactly match original raw text slices.
6. **Confuser Rejection:**
   - Test a phrase with a quantity but no entity (e.g., `"The answer is 5."`).
   - Test a phrase with two numbers and one entity (e.g., `"The 2 boys have 3 dogs."`).
   - Test a percent/rate confuser (e.g., `"Increased by 20%"`).
   - Test unit/kind conflict (if practically verifiable with current types).
7. **Independence:** Run `test_percent_partition_proposal.py` and `test_proportional_decrease_proposal.py` to prove no regression in existing seam behavior.

## 7. Stop Conditions for Implementation

The xHigh agent must **STOP and refuse to write code** if any of the following occur:

- **No Local Evidence:** If the existing `_extract_bindings` logic cannot expose the needed entity without adding a broad noun regex, stop. Do not expand the parser.
- **Ambiguity Cannot Be Represented:** If `quantity_kind` (count vs. measurement) cannot be safely defaulted or extracted from existing `ProblemFrame` types without introducing a massive ontology, stop.
- **State/Pronoun Creep:** If binding a fixture requires pronoun resolution (`"he"`, `"they"`) or cross-sentence tracking, stop. The family requires exact local spans.
- **Serving Path Touch:** If forced to touch any serving API, `candidate_graph`, or eval artifact to make tests pass, stop immediately.

## 8. Copy-paste Next Implementation Brief Refinement

> **PR title:** `feat(kernel): introduce diagnostic quantity-entity proposal seam`
>
> **Dependency:** Start only after both `docs/sessions/quantity-entity-foundational-slice-authorization-2026-06-20.md` and `docs/sessions/quantity-entity-implementation-preflight-2026-06-20.md` have merged. Create a fresh worktree from `origin/main` and verify both commits are in the base.
>
> **Task:** Implement the bounded diagnostic proposal-first slice for `binding.quantity_entity`.
> - **Registry:** Flip `implementation_authorized = True` for this family in `generate/foundational_families.py`.
> - **Catalog:** Add `_QUANTITY_ENTITY_FAMILY` to `generate/construction_affordances.py`, enforcing `diagnostic_only=True` and `serving_allowed=False`.
> - **Proposals:** In `generate/problem_frame_builder.py`, iterate over existing `MentionBinding(binding_type="quantity_entity")` records to propose the construction using `propose_construction()`. Do not add new regex parsers for entities.
> - **Contracts:** Create `assess_quantity_entity(frame)` in `generate/problem_frame_contracts.py`. Enforce the exact closure obligations from the authorization doc (provenance spans, grounded scalar, local binding relation).
> - **Tests:** Create `tests/test_quantity_entity_proposal.py` to prove ordering, legacy adapter bypass, exact span slicing, diagnostic posture, and mandatory confuser refusal (quantity without entity, percent/comparison confusion).
>
> **Constraints:** Do not implement `state_change.transition`. Do not add broad noun parsing or pronoun resolution. Do not alter serving or derivation organs. Train and holdout `wrong_ids` must remain `[]`. If the exact local evidence is insufficient, the assessment must refuse; do not synthesize spans or bypass the preflight stop conditions.
