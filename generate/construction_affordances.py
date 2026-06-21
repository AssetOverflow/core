"""Diagnostic construction-affordance catalog.

Formalizes the constructional-affordance pattern proved by PR #835 so future
diagnostic families do not become scattered local parser patches.

This module contains declarations and proposal factories only.  It does NOT:
- claim CGA/substrate geometric retrieval (no manifold calls here);
- label local regex matching as substrate cognition;
- add any acquisition/transaction or transfer/loss/rate/comparison families;
- affect serving (all entries have ``serving_allowed=False``).

Every entry in this catalog is ``diagnostic_only=True``.  The catalog expresses
what a construction *means*, what roles it requires, what hazards it carries, and
what target semantics close it.  The assessment functions that check actual
ProblemFrame evidence live in ``generate/problem_frame_contracts.py``.

Design doctrine (from ADR-0223):
    Words and chunks are probes into the semantic substrate.
    They surface candidate affordances and relation families.
    Semantic closeness proposes.
    Exact span bindings ground.
    Organ-specific contracts determine.
    Unsupported or ambiguous cases refuse.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from generate.kernel_facts import SourceSpan


# ---------------------------------------------------------------------------
# Frozen typed structures
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RoleObligation:
    """A single role obligation for a construction.

    Args:
        role:        Role name that must be bound (e.g. ``"base_quantity"``).
        required:    If True, absence blocks contract closure.  If False, the
                     role is advisory only.
        description: Human-readable description of what this role represents.
    """

    role: str
    required: bool
    description: str


@dataclass(frozen=True, slots=True)
class ConstructionHazard:
    """An ambiguity or confuser hazard associated with a construction family.

    Args:
        hazard_category: Matches ``KernelHazard.category`` in the frame.
        blocking:        If True, the presence of this hazard blocks closure.
        description:     Explanation of what the hazard represents.
    """

    hazard_category: str
    blocking: bool
    description: str


@dataclass(frozen=True, slots=True)
class ConstructionSignature:
    """The relational signature of a construction: its type, organ, and roles.

    Args:
        relation_type:  The ``BoundRelation.relation_type`` value that carries
                        this construction (e.g. ``"decrease_to_fraction"``).
        candidate_organ: The assessment organ identifier produced by the
                         corresponding contract (e.g. ``"fraction_decrease"``).
        required_roles:  Roles that must be bound for the contract to be
                         declared runnable.
        optional_roles:  Roles that improve precision but are not blocking.
    """

    relation_type: str
    candidate_organ: str
    required_roles: tuple[RoleObligation, ...]
    optional_roles: tuple[RoleObligation, ...]


@dataclass(frozen=True, slots=True)
class ConstructionFamily:
    """A reviewed construction-affordance family declaration.

    Args:
        family_id:       Stable dotted identifier, e.g.
                         ``"proportional_change.decrease_to_fraction"``.
        display_name:    Short human-readable label.
        signature:       Relational signature (roles, organ, type).
        hazards:         Known hazards and confusers for this family.
        target_semantics: Required (operator, state, direction) values for the
                         bound question target (free-form strings matching
                         ``BoundQuestionTarget`` fields).
        contract_labels: Stable blocker code strings used in
                         ``ContractAssessment.missing_bindings``.
        diagnostic_only: Always True in this PR; the construction may produce
                         diagnostic assessments but must not change serving.
        serving_allowed: Always False in this PR.  No construction may be
                         promoted to serving without a separate reviewed PR.
    """

    family_id: str
    display_name: str
    signature: ConstructionSignature
    hazards: tuple[ConstructionHazard, ...]
    target_semantics: tuple[str, ...]
    contract_labels: tuple[str, ...]
    diagnostic_only: bool
    serving_allowed: bool

    def __post_init__(self) -> None:
        if self.serving_allowed:
            raise ValueError(
                f"ConstructionFamily {self.family_id!r}: "
                "serving_allowed must be False in this PR — "
                "no construction may be promoted to serving without a separate reviewed PR."
            )
        if not self.diagnostic_only:
            raise ValueError(
                f"ConstructionFamily {self.family_id!r}: "
                "diagnostic_only must be True — "
                "catalog constructions do not authorize serving."
            )


@dataclass(frozen=True, slots=True)
class ConstructionContract:
    """Registry entry binding a ConstructionFamily to its assessment function.

    Args:
        family:          The construction family declaration.
        assess_fn_name:  Name of the assessment function in
                         ``generate.problem_frame_contracts`` (for introspection
                         only; the function is not called through this struct).
    """

    family: ConstructionFamily
    assess_fn_name: str


@dataclass(frozen=True, slots=True)
class ConstructionProposal:
    """Lightweight diagnostic-only trace of a construction proposal.

    Represents the evidence chain::

        chunk/surface evidence
        → proposed construction family
        → proposed relation type
        → role obligations
        → hazards
        → status

    A proposal is created from exact surface evidence before contract
    assessment.  It does not affect serving.  Its initial ``status`` is
    ``"proposed"``; assessment remains a separate, downstream judgment.

    Args:
        family_id:       Catalog family identifier, e.g.
                         ``"proportional_change.decrease_to_fraction"``.
        relation_type:   The ``BoundRelation.relation_type`` that was searched.
        candidate_organ: The organ this proposal targets.
        evidence_spans:  Source spans that motivated the proposal.
        status:          One of ``"proposed"``, ``"partial"``, ``"closed"``,
                         ``"refused"``.  ``"closed"`` means the contract
                         assessment was runnable.
        missing_roles:   Role obligation names that were absent at assessment time.
        active_hazards:  Hazard categories that were unresolved at assessment time.
        role_obligations: Catalog-declared roles that downstream binding and
                          assessment must ground or explicitly refuse.
        diagnostic_only: True for every proposal in the current catalog.
        serving_allowed: False for every proposal in the current catalog.
    """

    family_id: str
    relation_type: str
    candidate_organ: str
    evidence_spans: tuple[SourceSpan, ...]
    status: str
    missing_roles: tuple[str, ...]
    active_hazards: tuple[str, ...]
    role_obligations: tuple[RoleObligation, ...] = ()
    diagnostic_only: bool = True
    serving_allowed: bool = False

    _VALID_STATUSES: frozenset[str] = frozenset({
        "proposed", "partial", "closed", "refused"
    })

    def __post_init__(self) -> None:
        if self.status not in self._VALID_STATUSES:
            raise ValueError(
                f"ConstructionProposal.status must be one of "
                f"{sorted(self._VALID_STATUSES)}, got {self.status!r}"
            )
        if not self.diagnostic_only or self.serving_allowed:
            raise ValueError(
                "ConstructionProposal must remain diagnostic-only and serving-disallowed"
            )


# ---------------------------------------------------------------------------
# Catalog entries
# ---------------------------------------------------------------------------

_DECREASE_TO_FRACTION_FAMILY = ConstructionFamily(
    family_id="proportional_change.decrease_to_fraction",
    display_name="Proportional decrease to fraction",
    signature=ConstructionSignature(
        relation_type="decrease_to_fraction",
        candidate_organ="fraction_decrease",
        required_roles=(
            RoleObligation(
                "base_quantity",
                required=True,
                description="The quantity whose value will decrease (the current/initial state).",
            ),
            RoleObligation(
                "scale",
                required=True,
                description=(
                    "Fraction p/q in (0, 1) exclusive: the new value is scale × base_quantity. "
                    "Values of 0, 1, or > 1 are rejected."
                ),
            ),
            RoleObligation(
                "state_entity",
                required=True,
                description=(
                    "The entity (object or actor) whose state undergoes the decrease. "
                    "Must match the question-target entity for state_entity_continuity."
                ),
            ),
            RoleObligation(
                "transition",
                required=True,
                description='Span anchor for the "decrease to" trigger phrase.',
            ),
        ),
        optional_roles=(
            RoleObligation(
                "unit",
                required=False,
                description=(
                    "Unit of the base quantity. When present, unit_continuity is checked: "
                    "the unit binding on base_quantity must match this role."
                ),
            ),
        ),
    ),
    hazards=(
        ConstructionHazard(
            hazard_category="unbound_base_quantity",
            blocking=True,
            description=(
                "The base quantity cannot be uniquely identified. "
                "Multiple candidates or no 'current/now' sentence context."
            ),
        ),
        ConstructionHazard(
            hazard_category="percent_change_vs_percent_of",
            blocking=False,
            description=(
                "Percent-change surfaces may co-occur; they do not trigger this construction "
                "because this family only recognises exact fraction (p/q) scale triggers."
            ),
        ),
    ),
    target_semantics=(
        "operator:difference",
        "state:delta",
        "direction:decrease",
    ),
    contract_labels=(
        "decrease_relation_ambiguous",
        "base_quantity_unbound",
        "scale_unbound",
        "state_entity_unbound",
        "base_quantity_provenance_missing",
        "scale_provenance_missing",
        "unit_continuity_unproven",
        "delta_decrease_target_unbound",
        "delta_decrease_target_required",
        "state_entity_continuity_unproven",
        "scale_out_of_range",
    ),
    diagnostic_only=True,
    serving_allowed=False,
)

_PERCENT_PARTITION_FAMILY = ConstructionFamily(
    family_id="partition.percent_partition",
    display_name="Percent-based partition of a whole",
    signature=ConstructionSignature(
        relation_type="percent_of",  # primary relation type checked in contracts
        candidate_organ="percent_partition",
        required_roles=(
            RoleObligation(
                "whole",
                required=True,
                description=(
                    "The original numeric whole that the partition subdivides. "
                    "Must appear before the partition event in text."
                ),
            ),
            RoleObligation(
                "part",
                required=True,
                description=(
                    "A distinct subgroup of the whole. At least two distinct "
                    "subgroup-part IDs are required to prove complementary coverage."
                ),
            ),
            RoleObligation(
                "scale",
                required=True,
                description=(
                    "Percentage or fraction linking part to whole via percent_of relation. "
                    "Each distinct part must have its own linked scale."
                ),
            ),
        ),
        optional_roles=(),
    ),
    hazards=(
        ConstructionHazard(
            hazard_category="unbound_base_quantity",
            blocking=True,
            description=(
                "No numeric whole quantity is bound before the partition event. "
                "Without a provenance-bearing original whole, closure is refused."
            ),
        ),
        ConstructionHazard(
            hazard_category="percent_change_vs_percent_of",
            blocking=True,
            description=(
                "Percent-change surface ambiguity: 'percent' could indicate a change "
                "rather than a partition fraction. Topology proof resolves this."
            ),
        ),
    ),
    target_semantics=(
        "operator:count",
        "state:aggregate",
        "direction:forward",
    ),
    contract_labels=(
        "grounded_partition_subgroup",
        "grounded_whole_entity",
        "original_whole_unbound",
        "multiple_original_whole_candidates",
        "partition_subgroups_not_distinct",
        "percent_subgroup_links_incomplete",
        "grounded_question_target",
        "forward_aggregate_target_required",
        "inverse_topology_unlicensed",
    ),
    diagnostic_only=True,
    serving_allowed=False,
)

_QUANTITY_ENTITY_FAMILY = ConstructionFamily(
    family_id="binding.quantity_entity",
    display_name="Local quantity-entity binding",
    signature=ConstructionSignature(
        relation_type="quantity_entity",
        candidate_organ="quantity_entity_binding",
        required_roles=(
            RoleObligation(
                "quantity",
                required=True,
                description="Exactly one source-grounded scalar mention.",
            ),
            RoleObligation(
                "entity",
                required=True,
                description="Exactly one local source-grounded entity mention.",
            ),
            RoleObligation(
                "quantity_kind",
                required=True,
                description="A positively grounded count or measurement disposition.",
            ),
            RoleObligation(
                "provenance_span",
                required=True,
                description="Exact non-synthetic quantity, entity, and optional unit spans.",
            ),
            RoleObligation(
                "local_binding_relation",
                required=True,
                description="The unique local quantity_entity MentionBinding edge.",
            ),
        ),
        optional_roles=(
            RoleObligation(
                "unit",
                required=False,
                description=(
                    "An exact grounded unit bound to the same quantity when the "
                    "quantity kind is measurement."
                ),
            ),
        ),
    ),
    hazards=(
        ConstructionHazard(
            hazard_category="quantity_entity_ambiguous",
            blocking=True,
            description="More than one local scalar, entity, or binding remains plausible.",
        ),
        ConstructionHazard(
            hazard_category="quantity_kind_unresolved",
            blocking=True,
            description="Count or measurement kind is not positively grounded.",
        ),
        ConstructionHazard(
            hazard_category="quantity_entity_nonlocal",
            blocking=True,
            description="The binding requires pronoun repair or a cross-sentence leap.",
        ),
    ),
    target_semantics=(
        "locality:single_sentence",
        "authority:diagnostic_only",
    ),
    contract_labels=(
        "quantity_entity_proposal_required",
        "quantity_unbound",
        "entity_unbound",
        "quantity_ambiguous",
        "entity_ambiguous",
        "local_binding_relation_unbound",
        "local_binding_relation_ambiguous",
        "quantity_kind_unresolved",
        "unit_kind_conflict",
        "provenance_span_inexact",
        "quantity_entity_nonlocal",
        "competing_family_context",
        "percent_change_vs_percent_of",
    ),
    diagnostic_only=True,
    serving_allowed=False,
)

# The catalog.  Keys are family_id strings.  Sorted for deterministic iteration.
_CATALOG: dict[str, ConstructionFamily] = {
    _DECREASE_TO_FRACTION_FAMILY.family_id: _DECREASE_TO_FRACTION_FAMILY,
    _PERCENT_PARTITION_FAMILY.family_id: _PERCENT_PARTITION_FAMILY,
    _QUANTITY_ENTITY_FAMILY.family_id: _QUANTITY_ENTITY_FAMILY,
}

# Secondary indices for O(1) lookup by organ or relation type.
_BY_ORGAN: dict[str, ConstructionFamily] = {
    family.signature.candidate_organ: family
    for family in _CATALOG.values()
}
_BY_RELATION_TYPE: dict[str, ConstructionFamily] = {
    family.signature.relation_type: family
    for family in _CATALOG.values()
}

_PROPOSAL_FIRST_FAMILIES: frozenset[str] = frozenset({
    "binding.quantity_entity",
    "proportional_change.decrease_to_fraction",
    "partition.percent_partition",
})


# ---------------------------------------------------------------------------
# Public accessors
# ---------------------------------------------------------------------------


def lookup_family(family_id: str) -> ConstructionFamily | None:
    """Return the ConstructionFamily for *family_id*, or None if not registered."""
    return _CATALOG.get(family_id)


def lookup_by_organ(candidate_organ: str) -> ConstructionFamily | None:
    """Return the ConstructionFamily whose signature.candidate_organ matches."""
    return _BY_ORGAN.get(candidate_organ)


def lookup_by_relation_type(relation_type: str) -> ConstructionFamily | None:
    """Return the ConstructionFamily whose signature.relation_type matches.

    Note: ``percent_partition`` uses two relation types (``percent_of`` and
    ``subgroup_partition``) in its assessment logic, but the catalog entry
    declares the primary relation type (``percent_of``) as the lookup key.
    """
    return _BY_RELATION_TYPE.get(relation_type)


def all_diagnostic_families() -> tuple[ConstructionFamily, ...]:
    """Return all registered diagnostic families in deterministic (family_id) order."""
    return tuple(_CATALOG[key] for key in sorted(_CATALOG))


def propose_construction(
    family_id: str,
    evidence_spans: tuple[SourceSpan, ...],
) -> ConstructionProposal:
    """Create a catalog-backed proposal from pre-assessment surface evidence.

    This factory deliberately has no assessment inputs.  It records the
    construction hypothesis and its catalog obligations; bound relations and
    ``ContractAssessment`` remain responsible for grounding and determination.

    Raises:
        KeyError: If *family_id* is not registered in the catalog.
    """
    family = _CATALOG[family_id]
    return ConstructionProposal(
        family_id=family.family_id,
        relation_type=family.signature.relation_type,
        candidate_organ=family.signature.candidate_organ,
        evidence_spans=evidence_spans,
        status="proposed",
        missing_roles=(),
        active_hazards=(),
        role_obligations=(
            *family.signature.required_roles,
            *family.signature.optional_roles,
        ),
        diagnostic_only=family.diagnostic_only,
        serving_allowed=family.serving_allowed,
    )


def make_proposal(
    family_id: str,
    evidence_spans: tuple[SourceSpan, ...],
    assessment_runnable: bool,
    missing_roles: tuple[str, ...],
    active_hazards: tuple[str, ...],
) -> ConstructionProposal:
    """Map assessment evidence onto a proposal for legacy catalog paths.

    Migrated proposal-first families must enter through
    :func:`propose_construction`.  This adapter remains only for explicitly
    unmigrated catalog paths that still synthesize proposals from assessments.

    Args:
        family_id:           Catalog family identifier.
        evidence_spans:      Source spans from the contract assessment.
        assessment_runnable: Whether the corresponding ContractAssessment.runnable
                             was True.
        missing_roles:       ContractAssessment.missing_bindings contents.
        active_hazards:      ContractAssessment.unresolved_hazards contents.

    Returns:
        A ConstructionProposal with status derived from the assessment:
        - ``"closed"``   if runnable and no missing roles/hazards;
        - ``"partial"``  if some roles are bound but closure is incomplete;
        - ``"refused"``  if active hazards block closure;
        - ``"proposed"`` otherwise (construction proposed but not evaluated).

    Raises:
        KeyError: If *family_id* is not registered in the catalog.
        ValueError: If *family_id* has already migrated to the proposal-first seam.
    """
    if family_id in _PROPOSAL_FIRST_FAMILIES:
        raise ValueError(
            f"{family_id} is proposal-first; use propose_construction before assessment"
        )
    proposal = propose_construction(family_id, evidence_spans)

    if assessment_runnable:
        status = "closed"
    elif active_hazards:
        status = "refused"
    elif missing_roles:
        status = "partial"
    else:
        status = "proposed"

    return replace(
        proposal,
        status=status,
        missing_roles=missing_roles,
        active_hazards=active_hazards,
    )
