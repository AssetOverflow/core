"""Read-only registry of approved foundational-family specifications.

This module manually mirrors the constitutional family specifications approved
under ADR-0224.  It is descriptive metadata only: it does not read specification
documents, recognize constructions, assess ``ProblemFrame`` contracts, or route
proposals.  Authorization fields mirror reviewed implementation boundaries;
they never authorize serving.

The current registry deliberately contains only the reviewed foundational
families approved by the family-spec gate.  General substrate/CGA retrieval for
these families is not live.
"""
from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType


@dataclass(frozen=True, slots=True)
class FoundationalDomainEvidence:
    """One cross-domain example declared by a foundational-family spec."""

    domain: str
    example: str
    expected_roles: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class FoundationalFamilySpec:
    """Immutable descriptive mirror of an approved family specification.

    The fields state the future contract shape and its constitutional gates.
    They do not implement recognition, binding, assessment, verification, or
    serving behavior.
    """

    family_id: str
    display_name: str
    status: str
    related_adrs: tuple[str, ...]
    domains: tuple[str, ...]
    summary: str
    surface_chunk_patterns: tuple[str, ...]
    semantic_neighborhood: tuple[str, ...]
    construction_signatures: tuple[str, ...]
    required_roles: tuple[str, ...]
    optional_roles: tuple[str, ...]
    hazards_confusers: tuple[str, ...]
    frame_representation: tuple[str, ...]
    contract_readiness_criteria: tuple[str, ...]
    verification_style: tuple[str, ...]
    refusal_conditions: tuple[str, ...]
    cross_domain_evidence: tuple[FoundationalDomainEvidence, ...]
    current_state: str
    target_state: str
    serving_status: str
    serving_allowed: bool
    implementation_authorized: bool
    primary_relation_type: str
    future_adapter: str | None = None


_QUANTITY_ENTITY_BINDING = FoundationalFamilySpec(
    family_id="binding.quantity_entity",
    display_name="Quantity-Entity Binding",
    status="Implemented (diagnostic-only; non-serving)",
    related_adrs=("ADR-0223", "ADR-0224"),
    domains=(
        "arithmetic_quantitative",
        "physical_science",
        "charts_tables_data",
        "social_studies",
    ),
    summary=(
        "Binds a grounded scalar quantity to the entity, object, category, or "
        "measured property that it quantifies."
    ),
    surface_chunk_patterns=(
        "<number> <noun>",
        "<number> of the <noun>",
        "<noun>: <number>",
        "<number> <unit> of <material>",
    ),
    semantic_neighborhood=(
        "quantified_group",
        "measured_property",
        "category_cardinality",
        "resource_population",
    ),
    construction_signatures=("quantity_entity_binding",),
    required_roles=("quantity", "entity"),
    optional_roles=("unit",),
    hazards_confusers=(
        "PF-EN-002 quantity_entity_unbound",
        "PF-LX-004 span_collision",
        "PF-EN-005 role_alias_collision",
        "PF-HZ-005 conflict_auto_resolved",
    ),
    frame_representation=(
        "GroundedMention for the quantity and entity spans",
        "MentionBinding(binding_type='quantity_entity') from quantity to entity",
        "Optional MentionBinding(binding_type='quantity_unit') from quantity to unit",
    ),
    contract_readiness_criteria=(
        "Quantity is grounded to an exact parsed scalar.",
        "Entity is grounded to a valid noun phrase or category span.",
        "No active overlap or scalar span collision remains.",
        "No unresolved quantity-entity hazard remains.",
        "Independent verification and wrong-zero preservation are required before serving.",
    ),
    verification_style=(
        "Lexical-substitution invariance must preserve binding topology modulo spans.",
        "Comparative confusers must not be accepted as generic quantity-entity bindings.",
    ),
    refusal_conditions=(
        "Ambiguous referents remain unresolved while multiple entity candidates are active.",
        "Overlapping scalar spans cannot be deterministically ordered.",
    ),
    cross_domain_evidence=(
        FoundationalDomainEvidence(
            domain="physical_science",
            example="A block of iron has a mass of 12 grams.",
            expected_roles=("quantity", "entity", "unit"),
        ),
        FoundationalDomainEvidence(
            domain="charts_tables_data",
            example="The bar graph shows: Apples: 15, Bananas: 8.",
            expected_roles=("quantity", "entity"),
        ),
        FoundationalDomainEvidence(
            domain="social_studies",
            example="The town of Shelbyville has a population of 50,000 residents.",
            expected_roles=("quantity", "entity"),
        ),
    ),
    current_state=(
        "Implemented only as a bounded diagnostic proposal-first local binding; "
        "general entity extraction and substrate/CGA retrieval do not exist."
    ),
    target_state=(
        "Proposal-first quantity-entity binding with span grounding, contract assessment, "
        "independent verification, and cross-domain evidence."
    ),
    serving_status="Diagnostic-only implementation / not serving.",
    serving_allowed=False,
    implementation_authorized=True,
    primary_relation_type="quantity_entity",
    future_adapter="quantity_entity_adapter",
)


_STATE_CHANGE = FoundationalFamilySpec(
    family_id="state_change.transition",
    display_name="State Change",
    status="Proposed (gating specification)",
    related_adrs=("ADR-0223", "ADR-0224"),
    domains=(
        "arithmetic_proportional",
        "physical_science",
        "life_science",
        "reading_comprehension",
        "procedural_reasoning",
    ),
    summary=(
        "Represents an entity or system transitioning from an initial state to a "
        "final state through an event, action, or process."
    ),
    surface_chunk_patterns=(
        "<verb-change> to <value>",
        "<verb-change> by <value>",
        "originally <value>, now <value>",
        "after <event>, <actor> has <value>",
    ),
    semantic_neighborhood=(
        "possession_change",
        "proportional_scaling",
        "temperature_transition",
        "growth_stage",
        "procedural_step",
    ),
    construction_signatures=("state_change",),
    required_roles=("entity", "initial_state", "transition_event", "final_state"),
    optional_roles=("scale", "delta"),
    hazards_confusers=(
        "PF-BD-004 positional_binding",
        "PF-TG-004 target_direction_unknown",
        "PF-TP-006 state_transition_open",
        "PF-HZ-003 hazard_ignored_by_contract",
    ),
    frame_representation=(
        "BoundRelation(relation_type='state_change')",
        "RelationRole bindings for entity, initial_state, transition, and final_state",
        "Optional RelationRole bindings for scale or delta",
        "Exact SourceSpan evidence for the proposed transition",
    ),
    contract_readiness_criteria=(
        "The changing entity is bound with continuity across the transition span.",
        "Transition direction is explicitly resolved from grounded evidence.",
        "The question target names a mathematically closed variable.",
        "No unresolved 'by' versus 'to' directional hazard remains.",
        "Independent verification and wrong-zero preservation are required before serving.",
    ),
    verification_style=(
        "Validate the applicable state equation over grounded roles.",
        "Changing 'decreased to' to 'decreased by' must require rebinding and reverification.",
    ),
    refusal_conditions=(
        "Event order is missing or temporally ambiguous.",
        "The transition is open because initial, delta, and final values cannot close a target.",
    ),
    cross_domain_evidence=(
        FoundationalDomainEvidence(
            domain="physical_science",
            example="Water originally at 20 degrees Celsius is heated to 80 degrees Celsius.",
            expected_roles=("entity", "initial_state", "transition_event", "final_state"),
        ),
        FoundationalDomainEvidence(
            domain="life_science",
            example="The plant grew from 5 inches tall to 9 inches tall over the summer.",
            expected_roles=("entity", "initial_state", "transition_event", "final_state"),
        ),
        FoundationalDomainEvidence(
            domain="reading_comprehension",
            example=(
                "Before the storm, the streets were dry. After the storm, the streets "
                "were flooded."
            ),
            expected_roles=("entity", "initial_state", "transition_event", "final_state"),
        ),
        FoundationalDomainEvidence(
            domain="procedural_reasoning",
            example="Step 1: Set X to 10. Step 2: Decrement X by 2.",
            expected_roles=("entity", "initial_state", "transition_event", "delta"),
        ),
    ),
    current_state=(
        "Selected math constructions have assessment-backed diagnostic proposal traces. "
        "A general state-change adapter and non-math serving frames do not exist."
    ),
    target_state=(
        "Proposal-first state-change binding with role-complete contract assessment, "
        "independent verification, typed refusal, and cross-domain evidence."
    ),
    serving_status="Not implemented / not serving.",
    serving_allowed=False,
    implementation_authorized=False,
    primary_relation_type="state_change",
    future_adapter="state_change_adapter",
)


_UNARY_DELTA = FoundationalFamilySpec(
    family_id="state_change.unary_delta",
    display_name="Unary Delta State Change",
    status="Implemented (diagnostic-only; non-serving)",
    related_adrs=("ADR-0223", "ADR-0224"),
    domains=(
        "arithmetic_quantitative",
        "physical_science",
        "life_science",
        "reading_comprehension",
    ),
    summary=(
        "Represents one exact local gained/lost event as a unary quantity "
        "delta over a changed object, without asserting owner, before-state, "
        "after-state, or arithmetic closure."
    ),
    surface_chunk_patterns=(
        "<subject> gained <number> <object>",
        "<subject> lost <number> <object>",
    ),
    semantic_neighborhood=(
        "inventory_change",
        "resource_delta",
        "count_change",
        "local_event_delta",
    ),
    construction_signatures=("unary_delta",),
    required_roles=("action_cue", "delta_quantity", "changed_object", "direction"),
    optional_roles=("subject_surface",),
    hazards_confusers=(
        "PF-EN-002 quantity_entity_unbound",
        "PF-EN-005 role_alias_collision",
        "PF-HZ-003 hazard_ignored_by_contract",
        "PF-TG-004 target_direction_unknown",
    ),
    frame_representation=(
        "ConstructionProposal(status='proposed', family_id='state_change.unary_delta')",
        "BoundRelation(relation_type='unary_delta') with action_cue, delta_quantity, changed_object, and direction roles",
        "Exact SourceSpan evidence for cue, quantity, and object",
        "ContractAssessment(candidate_organ='unary_delta') as the sole runnable/refused authority",
    ),
    contract_readiness_criteria=(
        "Exactly one local gained/lost cue is grounded from the original text.",
        "Exactly one grounded scalar quantity and one grounded changed object are bound.",
        "Quantity/object grounding composes with exact local quantity_entity evidence.",
        "Direction is increase for gained and decrease for lost.",
        "No transfer, containment, comparison, rate, percent, passive, modal, negated, or cross-sentence reasoning is required.",
    ),
    verification_style=(
        "Cue substitution between gained and lost must flip direction without widening other roles.",
        "Synthetic or widened cue/quantity/object spans must refuse rather than normalize.",
    ),
    refusal_conditions=(
        "Cue, quantity, or changed object is missing or ambiguous.",
        "Object grounding would require pronoun repair, cross-sentence binding, or legacy semantic-state logic.",
    ),
    cross_domain_evidence=(
        FoundationalDomainEvidence(
            domain="physical_science",
            example="The jar lost 2 cookies.",
            expected_roles=("action_cue", "delta_quantity", "changed_object", "direction"),
        ),
        FoundationalDomainEvidence(
            domain="life_science",
            example="The sapling gained 3 leaves.",
            expected_roles=("action_cue", "delta_quantity", "changed_object", "direction"),
        ),
        FoundationalDomainEvidence(
            domain="reading_comprehension",
            example="Ana gained 3 marbles.",
            expected_roles=("action_cue", "delta_quantity", "changed_object", "direction"),
        ),
    ),
    current_state=(
        "Implemented only as a bounded diagnostic proposal-first gained/lost "
        "relation. No transfer semantics, owner assertion, state ledger, or "
        "serving adapter is authorized."
    ),
    target_state=(
        "Proposal-first unary-delta relation with exact cue/quantity/object grounding, "
        "typed refusal, and cross-domain evidence."
    ),
    serving_status="Diagnostic-only implementation / not serving.",
    serving_allowed=False,
    implementation_authorized=True,
    primary_relation_type="unary_delta",
    future_adapter="unary_delta_adapter",
)


_FAMILIES = (_QUANTITY_ENTITY_BINDING, _STATE_CHANGE, _UNARY_DELTA)
_BY_ID = MappingProxyType({family.family_id: family for family in _FAMILIES})
_BY_RELATION_TYPE = MappingProxyType(
    {family.primary_relation_type: family for family in _FAMILIES}
)


def iter_foundational_families() -> tuple[FoundationalFamilySpec, ...]:
    """Return all approved foundational-family specs in deterministic order."""

    return _FAMILIES


def get_foundational_family(family_id: str) -> FoundationalFamilySpec | None:
    """Return the registered spec for ``family_id``, if present."""

    return _BY_ID.get(family_id)


def require_foundational_family(family_id: str) -> FoundationalFamilySpec:
    """Return the registered spec or raise ``KeyError`` with a clear identifier."""

    family = get_foundational_family(family_id)
    if family is None:
        raise KeyError(f"unknown foundational family: {family_id!r}")
    return family


def get_foundational_family_by_relation_type(
    relation_type: str,
) -> FoundationalFamilySpec | None:
    """Return the spec whose primary relation type matches ``relation_type``."""

    return _BY_RELATION_TYPE.get(relation_type)


__all__ = (
    "FoundationalDomainEvidence",
    "FoundationalFamilySpec",
    "get_foundational_family",
    "get_foundational_family_by_relation_type",
    "iter_foundational_families",
    "require_foundational_family",
)
