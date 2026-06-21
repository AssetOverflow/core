"""Diagnostic organ-contract readiness derived only from ProblemFrame evidence.

Contract dispatch is deliberately narrow:
- ``assess_contracts()`` routes to two diagnostic assessment functions.
- The ``_CONTRACT_REGISTRY`` provides catalog metadata for introspection and
  proposal-trace generation; it does not replace the structural logic inside
  each assessment function.
- All registered contracts have ``serving_allowed=False``; this module must
  never be imported from serving dispatch paths.
"""
from __future__ import annotations

from dataclasses import dataclass

from generate.construction_affordances import (
    ConstructionContract,
    _DECREASE_TO_FRACTION_FAMILY,
    _PERCENT_PARTITION_FAMILY,
)
from generate.kernel_facts import BoundRelation, SourceSpan
from generate.problem_frame import ProblemFrame


# ---------------------------------------------------------------------------
# Contract registry
#
# Maps candidate_organ -> ConstructionContract.  This registry provides
# metadata for proposal-trace generation and external introspection.  It does
# not replace the per-assessment dispatch logic in assess_contracts(); the
# structural proof obligations for each family live inside the dedicated
# assess_* functions below.
#
# Why not route dispatch through the registry?
# assess_fraction_decrease and assess_percent_partition each contain
# construction-specific structural logic (role iteration, topology proofs,
# hazard escalation) that cannot be generalised behind a single callable
# without introducing a forced abstraction boundary.  The registry expresses
# *what* a construction is; the assessment functions express *how* its
# obligations are checked.  Both layers are needed and should remain separate.
# ---------------------------------------------------------------------------

_CONTRACT_REGISTRY: dict[str, ConstructionContract] = {
    "fraction_decrease": ConstructionContract(
        family=_DECREASE_TO_FRACTION_FAMILY,
        assess_fn_name="assess_fraction_decrease",
    ),
    "percent_partition": ConstructionContract(
        family=_PERCENT_PARTITION_FAMILY,
        assess_fn_name="assess_percent_partition",
    ),
}


def get_contract_family_id(candidate_organ: str) -> str | None:
    """Return the catalog family ID for a candidate organ, if registered."""
    contract = _CONTRACT_REGISTRY.get(candidate_organ)
    return contract.family.family_id if contract else None



@dataclass(frozen=True, slots=True)
class ContractAssessment:
    candidate_organ: str
    missing_bindings: tuple[str, ...]
    unresolved_hazards: tuple[str, ...]
    runnable: bool
    explanation: str
    evidence_spans: tuple[SourceSpan, ...]


def _roles(frame: ProblemFrame, relation_type: str) -> set[str]:
    return {
        role.role
        for relation in frame.bound_relations
        if relation.relation_type == relation_type
        for role in relation.roles
    }


def _evidence(frame: ProblemFrame, relation_type: str) -> tuple[SourceSpan, ...]:
    spans = {
        (span.start, span.end, span.text): span
        for relation in frame.bound_relations
        if relation.relation_type == relation_type
        for span in relation.evidence_spans
    }
    if frame.bound_question_target is not None:
        for span in frame.bound_question_target.evidence_spans:
            spans[(span.start, span.end, span.text)] = span
    return tuple(spans[key] for key in sorted(spans))


def _role_target(relation: BoundRelation, role_name: str) -> str | None:
    return next((role.target_id for role in relation.roles if role.role == role_name), None)


def _mention_map(frame: ProblemFrame) -> dict[str, object]:
    return {mention.mention_id: mention for mention in frame.mentions}


def _quantity_value_by_mention_id(frame: ProblemFrame) -> dict[str, object]:
    quantities = {quantity.fact_id: quantity for quantity in frame.quantities}
    return {
        mention.mention_id: quantities[mention.fact_id]
        for mention in frame.mentions
        if mention.fact_id is not None and mention.fact_id in quantities
    }


def _quantity_entity_bindings(frame: ProblemFrame) -> tuple[tuple[str, str], ...]:
    return tuple(
        (binding.source_mention_id, binding.target_mention_id)
        for binding in frame.bindings
        if binding.binding_type == "quantity_entity"
    )


def _quantity_unit_bindings(frame: ProblemFrame) -> dict[str, str]:
    return {
        binding.source_mention_id: binding.target_mention_id
        for binding in frame.bindings
        if binding.binding_type == "quantity_unit"
    }


def assess_fraction_decrease(frame: ProblemFrame) -> ContractAssessment:
    mentions = _mention_map(frame)
    quantities = _quantity_value_by_mention_id(frame)
    quantity_units = _quantity_unit_bindings(frame)
    relations = [relation for relation in frame.bound_relations if relation.relation_type == "decrease_to_fraction"]
    question_target = frame.bound_question_target

    missing: list[str] = []
    unresolved: set[str] = set()
    if len(relations) != 1:
        missing.append("decrease_relation_ambiguous")
    relation = relations[0] if len(relations) == 1 else None

    base_id = _role_target(relation, "base_quantity") if relation is not None else None
    scale_id = _role_target(relation, "scale") if relation is not None else None
    state_id = _role_target(relation, "state_entity") if relation is not None else None
    unit_id = _role_target(relation, "unit") if relation is not None else None

    if base_id is None:
        missing.append("base_quantity_unbound")
    if scale_id is None:
        missing.append("scale_unbound")
    if state_id is None:
        missing.append("state_entity_unbound")
    if base_id is not None and base_id not in quantities:
        missing.append("base_quantity_provenance_missing")
    if scale_id is not None and scale_id not in quantities:
        missing.append("scale_provenance_missing")
    if unit_id is not None and base_id is not None and quantity_units.get(base_id) != unit_id:
        missing.append("unit_continuity_unproven")

    if question_target is None or not question_target.grounded:
        missing.append("delta_decrease_target_unbound")
    else:
        if not (
            question_target.target_operator == "difference"
            and question_target.target_state == "delta"
            and question_target.target_direction == "decrease"
        ):
            missing.append("delta_decrease_target_required")
        if state_id is not None and state_id in mentions and question_target.target_mention_id in mentions:
            relation_state = mentions[state_id]
            target_state = mentions[question_target.target_mention_id]
            if relation_state.surface.lower() != target_state.surface.lower():
                missing.append("state_entity_continuity_unproven")

    scale = quantities.get(scale_id) if scale_id is not None else None
    if scale is not None and not (0 < scale.value < 1):
        missing.append("scale_out_of_range")

    categories = {hazard.category for hazard in frame.hazards}
    if any(item.startswith("base_quantity") for item in missing) and "unbound_base_quantity" in categories:
        unresolved.add("unbound_base_quantity")

    evidence_spans = (
        _evidence(frame, "decrease_to_fraction")
        if relation is None
        else tuple(
            sorted(
                {
                    (span.start, span.end, span.text): span
                    for span in (*relation.evidence_spans, *(question_target.evidence_spans if question_target else ()))
                }.values(),
                key=lambda span: (span.start, span.end, span.text),
            )
        )
    )
    runnable = not missing and not unresolved
    return ContractAssessment(
        candidate_organ="fraction_decrease",
        missing_bindings=tuple(dict.fromkeys(missing)),
        unresolved_hazards=tuple(sorted(unresolved)),
        runnable=runnable,
        explanation=(
            "all fraction-decrease roles and delta target obligations are grounded"
            if runnable else "diagnostic candidate is not runnable: " + ", ".join((*dict.fromkeys(missing), *sorted(unresolved)))
        ),
        evidence_spans=evidence_spans,
    )


def assess_percent_partition(frame: ProblemFrame) -> ContractAssessment:
    mentions = {mention.mention_id: mention for mention in frame.mentions}
    quantities = _quantity_value_by_mention_id(frame)
    quantity_entity = _quantity_entity_bindings(frame)
    subgroups = [relation for relation in frame.bound_relations if relation.relation_type == "subgroup_partition"]
    percentages = [relation for relation in frame.bound_relations if relation.relation_type == "percent_of"]
    linked_pairs: list[tuple[BoundRelation, BoundRelation]] = []
    subgroup_part_ids: set[str] = set()
    shared_whole_ids: set[str] = set()
    original_whole_quantities: set[str] = set()

    for subgroup in subgroups:
        subgroup_part = _role_target(subgroup, "part")
        subgroup_whole = _role_target(subgroup, "whole")
        if subgroup_part is None or subgroup_whole is None:
            continue
        subgroup_part_ids.add(subgroup_part)
        shared_whole_ids.add(subgroup_whole)
        relation_start = min(span.start for span in subgroup.evidence_spans)
        original_whole_quantities.update(
            quantity_id
            for quantity_id, entity_id in quantity_entity
            if entity_id == subgroup_whole
            and quantity_id in mentions
            and quantity_id in quantities
            and mentions[quantity_id].span.start < relation_start
        )
        for percent in percentages:
            percent_part = _role_target(percent, "part")
            percent_whole = _role_target(percent, "whole")
            if percent_part == subgroup_part and percent_whole == subgroup_whole:
                linked_pairs.append((subgroup, percent))

    missing: list[str] = []
    if not subgroups:
        missing.append("grounded_partition_subgroup")
    if not shared_whole_ids:
        missing.append("grounded_whole_entity")
    if not original_whole_quantities:
        missing.append("original_whole_unbound")
    elif len(original_whole_quantities) != 1:
        missing.append("multiple_original_whole_candidates")
    if len(subgroup_part_ids) < 2:
        missing.append("partition_subgroups_not_distinct")
    if len(linked_pairs) < 2:
        missing.append("percent_subgroup_links_incomplete")
    question_target = frame.bound_question_target
    if question_target is None or not question_target.grounded:
        missing.append("grounded_question_target")
    elif not (
        question_target.target_operator == "count"
        and question_target.target_state == "aggregate"
        and question_target.target_direction == "forward"
    ):
        if question_target.target_state == "initial" and question_target.target_direction == "inverse":
            missing.extend(("inverse_topology_unlicensed", "forward_aggregate_target_required"))
        else:
            missing.append("forward_aggregate_target_required")

    unresolved: set[str] = set()
    categories = {hazard.category for hazard in frame.hazards}
    if any(item in missing for item in ("grounded_whole_entity", "original_whole_unbound")) and "unbound_base_quantity" in categories:
        unresolved.add("unbound_base_quantity")
    if any(item in missing for item in ("grounded_partition_subgroup", "percent_subgroup_links_incomplete")) and "percent_change_vs_percent_of" in categories:
        unresolved.add("percent_change_vs_percent_of")
    runnable = not missing and not unresolved
    return ContractAssessment(
        candidate_organ="percent_partition",
        missing_bindings=tuple(dict.fromkeys(missing)),
        unresolved_hazards=tuple(sorted(unresolved)),
        runnable=runnable,
        explanation=(
            "all percent-partition roles and the question target are grounded"
            if runnable else "diagnostic candidate is not runnable: " + ", ".join((*dict.fromkeys(missing), *sorted(unresolved)))
        ),
        evidence_spans=tuple(sorted(
            {
                (span.start, span.end, span.text): span
                for pair in linked_pairs
                for relation in pair
                for span in relation.evidence_spans
            }.values(),
            key=lambda span: (span.start, span.end, span.text),
        )) + (() if question_target is None else question_target.evidence_spans),
    )


def assess_contracts(frame: ProblemFrame) -> tuple[ContractAssessment, ...]:
    """Return deterministic diagnostic assessments; never admits serving.

    Dispatch order:
    1. ``decrease_to_fraction`` — triggered by its proposal-first catalog
       family in ``frame.proposals``.  Routes to ``assess_fraction_decrease``,
       which still determines closure from bound frame evidence.
       Registry key: ``_CONTRACT_REGISTRY["fraction_decrease"]``.
    2. ``percent_partition`` — triggered by its proposal-first catalog family
       in ``frame.proposals``.  Routes to ``assess_percent_partition``, which
       still determines closure from bound frame evidence.
       Registry key: ``_CONTRACT_REGISTRY["percent_partition"]``.
    3. ``container_packing`` / ``labor_rate`` — inline skeleton assessments;
       not yet in the catalog registry (added to registry when obligations are
       fully specified).

    The registry provides catalog metadata for proposal traces; it does not
    replace the structural logic inside each assess_* function.  See module
    docstring for rationale.
    """
    frame_names = {candidate.name for candidate in frame.process_frames}
    results: list[ContractAssessment] = []

    # Registry-backed diagnostic families
    proposed_family_ids = {proposal.family_id for proposal in frame.proposals}
    if _DECREASE_TO_FRACTION_FAMILY.family_id in proposed_family_ids:
        # Catalog: _CONTRACT_REGISTRY["fraction_decrease"]
        results.append(assess_fraction_decrease(frame))
    if _PERCENT_PARTITION_FAMILY.family_id in proposed_family_ids:
        # Catalog: _CONTRACT_REGISTRY["percent_partition"]
        results.append(assess_percent_partition(frame))

    # Skeleton families not yet in the catalog registry
    if "container_packing" in frame_names and frame.bound_question_target is not None:
        roles = _roles(frame, "container_packing")
        missing = tuple(name for name in ("container", "content", "count_per") if name not in roles)
        results.append(ContractAssessment(
            "nested_fraction_remainder_total", missing, (), not missing,
            "container contract grounded" if not missing else "missing container bindings: " + ", ".join(missing),
            _evidence(frame, "container_packing"),
        ))
    if "labor_rate" in frame_names:
        roles = _roles(frame, "labor_rate")
        missing = tuple(name for name in ("worker", "rate", "duration") if name not in roles)
        results.append(ContractAssessment(
            "temporal_tariff", missing, (), not missing,
            "temporal tariff contract grounded" if not missing else "missing tariff bindings: " + ", ".join(missing),
            _evidence(frame, "labor_rate"),
        ))
    return tuple(sorted(results, key=lambda item: item.candidate_organ))


def recommended_migration_target(assessments: tuple[ContractAssessment, ...]) -> str:
    runnable = [item.candidate_organ for item in assessments if item.runnable]
    if runnable:
        return sorted(runnable)[0]
    if assessments:
        best = min(assessments, key=lambda item: (len(item.missing_bindings) + len(item.unresolved_hazards), item.candidate_organ))
        return f"substrate:contract_gap:{best.candidate_organ}"
    return "substrate:problem_frame_builder"
