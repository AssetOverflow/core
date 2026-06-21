"""Diagnostic organ-contract readiness derived only from ProblemFrame evidence.

Contract dispatch is deliberately narrow:
- ``assess_contracts()`` routes to three diagnostic assessment functions.
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
    _QUANTITY_ENTITY_FAMILY,
    _UNARY_DELTA_FAMILY,
)
from generate.kernel_facts import BoundRelation, GroundedMention, SourceSpan
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
    "quantity_entity_binding": ConstructionContract(
        family=_QUANTITY_ENTITY_FAMILY,
        assess_fn_name="assess_quantity_entity",
    ),
    "unary_delta": ConstructionContract(
        family=_UNARY_DELTA_FAMILY,
        assess_fn_name="assess_unary_delta",
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


def _role_spans(relation: BoundRelation, role_name: str) -> tuple[SourceSpan, ...]:
    role = next((item for item in relation.roles if item.role == role_name), None)
    return () if role is None else role.evidence_spans


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


_UNRESOLVED_ENTITY_SURFACES: frozenset[str] = frozenset({
    "he", "her", "hers", "him", "his", "it", "its", "one", "ones",
    "she", "their", "theirs", "them", "these", "they", "this", "those",
})


def _span_is_exact(frame: ProblemFrame, span: SourceSpan) -> bool:
    return (
        bool(frame.problem_text)
        and 0 <= span.start <= span.end <= len(frame.problem_text)
        and bool(span.text)
        and frame.problem_text[span.start:span.end] == span.text
    )


def _spans_are_local(
    problem_text: str,
    first: SourceSpan,
    second: SourceSpan,
) -> bool:
    left, right = sorted((first, second), key=lambda span: span.start)
    if left.end > right.start:
        return False
    return not any(marker in problem_text[left.end:right.start] for marker in ".!?")


def _unique_evidence(spans: tuple[SourceSpan, ...]) -> tuple[SourceSpan, ...]:
    unique = {
        (span.start, span.end, span.text): span
        for span in spans
    }
    return tuple(unique[key] for key in sorted(unique))


def _entity_mentions(frame: ProblemFrame) -> tuple[GroundedMention, ...]:
    return tuple(
        mention
        for mention in frame.mentions
        if mention.kind in {"entity", "object", "actor"}
    )


def assess_quantity_entity(frame: ProblemFrame) -> ContractAssessment:
    """Assess one proposal-backed local quantity/entity edge.

    This contract is deliberately stricter than generic mention extraction: it
    closes only one exact scalar, one exact entity, one exact local edge, and a
    positively grounded count/measurement disposition.  It derives neither an
    answer nor serving authority.
    """

    proposals = tuple(
        proposal
        for proposal in frame.proposals
        if proposal.family_id == _QUANTITY_ENTITY_FAMILY.family_id
    )
    bindings = tuple(
        binding
        for binding in frame.bindings
        if binding.binding_type == "quantity_entity"
    )
    mentions = {mention.mention_id: mention for mention in frame.mentions}
    quantity_facts = {quantity.fact_id: quantity for quantity in frame.quantities}

    missing: list[str] = []
    unresolved: set[str] = set()
    if len(proposals) != 1:
        missing.append("quantity_entity_proposal_required")
    proposal = proposals[0] if len(proposals) == 1 else None

    if not bindings:
        missing.append("local_binding_relation_unbound")
    elif len(bindings) != 1:
        missing.append("local_binding_relation_ambiguous")
    binding = bindings[0] if len(bindings) == 1 else None

    quantity = (
        mentions.get(binding.source_mention_id)
        if binding is not None
        else None
    )
    entity = (
        mentions.get(binding.target_mention_id)
        if binding is not None
        else None
    )
    if quantity is None or quantity.kind != "quantity":
        missing.append("quantity_unbound")
    elif quantity.fact_id is None or quantity.fact_id not in quantity_facts:
        missing.append("quantity_unbound")
    if len(frame.quantities) != 1:
        missing.append("quantity_ambiguous")

    if entity is None or entity.kind not in {"entity", "object"}:
        missing.append("entity_unbound")
    elif entity.surface.lower() in _UNRESOLVED_ENTITY_SURFACES:
        missing.append("entity_unbound")
        unresolved.add("quantity_entity_nonlocal")

    if quantity is not None and entity is not None:
        competing_entities = tuple(
            mention
            for mention in _entity_mentions(frame)
            if mention.mention_id != entity.mention_id
            and _spans_are_local(frame.problem_text, entity.span, mention.span)
        )
        if competing_entities:
            missing.append("entity_ambiguous")
        if not _spans_are_local(frame.problem_text, quantity.span, entity.span):
            missing.append("quantity_entity_nonlocal")

    if proposal is not None and quantity is not None and entity is not None:
        cue_contains_binding = any(
            cue.start <= quantity.span.start
            and entity.span.end <= cue.end
            for cue in proposal.evidence_spans
        )
        if not cue_contains_binding:
            missing.append("local_binding_relation_unbound")

    dispositions = tuple(
        disposition
        for disposition in frame.quantity_kind_dispositions
        if quantity is not None
        and entity is not None
        and disposition.quantity_mention_id == quantity.mention_id
        and disposition.entity_mention_id == entity.mention_id
    )
    if len(dispositions) != 1:
        missing.append("quantity_kind_unresolved")
    disposition = dispositions[0] if len(dispositions) == 1 else None

    unit_bindings = tuple(
        binding
        for binding in frame.bindings
        if quantity is not None
        and binding.binding_type == "quantity_unit"
        and binding.source_mention_id == quantity.mention_id
    )
    if len(unit_bindings) > 1:
        missing.append("unit_kind_conflict")
    unit_binding = unit_bindings[0] if len(unit_bindings) == 1 else None
    unit = (
        mentions.get(unit_binding.target_mention_id)
        if unit_binding is not None
        else None
    )
    if disposition is not None:
        if disposition.quantity_kind == "count" and unit_binding is not None:
            missing.append("unit_kind_conflict")
        elif disposition.quantity_kind == "measurement":
            if (
                unit_binding is None
                or disposition.unit_mention_id != unit_binding.target_mention_id
                or unit is None
                or unit.kind != "unit"
            ):
                missing.append("unit_kind_conflict")
    elif unit_binding is not None:
        missing.append("unit_kind_conflict")

    if unit is not None and entity is not None and unit.span == entity.span:
        missing.append("unit_kind_conflict")

    evidence = _unique_evidence(tuple(
        span
        for group in (
            (() if proposal is None else proposal.evidence_spans),
            (() if binding is None else binding.evidence_spans),
            (() if disposition is None else disposition.evidence_spans),
            (() if unit_binding is None else unit_binding.evidence_spans),
        )
        for span in group
    ))
    exact_evidence = evidence
    if quantity is not None:
        exact_evidence = _unique_evidence((*exact_evidence, quantity.span))
        quantity_fact = (
            quantity_facts.get(quantity.fact_id)
            if quantity.fact_id is not None
            else None
        )
        if (
            quantity_fact is None
            or quantity.span not in quantity_fact.provenance.source_spans
        ):
            missing.append("provenance_span_inexact")
    if entity is not None:
        exact_evidence = _unique_evidence((*exact_evidence, entity.span))
    if unit is not None:
        exact_evidence = _unique_evidence((*exact_evidence, unit.span))
        unit_fact = next(
            (
                grounded
                for grounded in frame.units
                if unit.fact_id == grounded.fact_id
            ),
            None,
        )
        if unit_fact is None or unit.span not in unit_fact.provenance.source_spans:
            missing.append("provenance_span_inexact")

    if binding is not None and quantity is not None and entity is not None:
        if binding.evidence_spans != (quantity.span, entity.span):
            missing.append("provenance_span_inexact")
    if unit_binding is not None and quantity is not None and unit is not None:
        if unit_binding.evidence_spans != (quantity.span, unit.span):
            missing.append("provenance_span_inexact")
    if not exact_evidence or not all(
        _span_is_exact(frame, span)
        for span in exact_evidence
    ):
        missing.append("provenance_span_inexact")

    competing_families = {candidate.name for candidate in frame.process_frames}
    if competing_families:
        missing.append("competing_family_context")
    categories = {hazard.category for hazard in frame.hazards}
    if "percent_change_vs_percent_of" in categories:
        unresolved.add("percent_change_vs_percent_of")

    missing_bindings = tuple(dict.fromkeys(missing))
    unresolved_hazards = tuple(sorted(unresolved))
    runnable = not missing_bindings and not unresolved_hazards
    return ContractAssessment(
        candidate_organ="quantity_entity_binding",
        missing_bindings=missing_bindings,
        unresolved_hazards=unresolved_hazards,
        runnable=runnable,
        explanation=(
            "one exact local quantity/entity binding is grounded diagnostically"
            if runnable
            else "diagnostic candidate is not runnable: "
            + ", ".join((*missing_bindings, *unresolved_hazards))
        ),
        evidence_spans=exact_evidence,
    )


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


def assess_unary_delta(frame: ProblemFrame) -> ContractAssessment:
    proposals = tuple(
        proposal
        for proposal in frame.proposals
        if proposal.family_id == _UNARY_DELTA_FAMILY.family_id
    )
    relations = tuple(
        relation
        for relation in frame.bound_relations
        if relation.relation_type == "unary_delta"
    )
    mentions = _mention_map(frame)
    dispositions = tuple(frame.quantity_kind_dispositions)

    missing: list[str] = []
    unresolved: set[str] = set()

    if len(proposals) != 1:
        missing.append("unary_delta_proposal_required")
    proposal = proposals[0] if len(proposals) == 1 else None

    if len(relations) != 1:
        missing.append("unary_delta_relation_ambiguous")
    relation = relations[0] if len(relations) == 1 else None

    cue_spans = _role_spans(relation, "action_cue") if relation is not None else ()
    quantity_id = _role_target(relation, "delta_quantity") if relation is not None else None
    object_id = _role_target(relation, "changed_object") if relation is not None else None
    direction = _role_target(relation, "direction") if relation is not None else None

    if len(cue_spans) != 1:
        missing.append("action_cue_unbound")
    cue_span = cue_spans[0] if len(cue_spans) == 1 else None
    if cue_span is not None and cue_span.text not in {"gained", "lost"}:
        missing.append("action_cue_unbound")

    quantity = mentions.get(quantity_id) if quantity_id is not None else None
    if quantity is None or quantity.kind != "quantity":
        missing.append("delta_quantity_unbound")

    changed_object = mentions.get(object_id) if object_id is not None else None
    if changed_object is None or changed_object.kind != "object":
        missing.append("changed_object_unbound")

    expected_direction = None
    if cue_span is not None:
        expected_direction = "increase" if cue_span.text == "gained" else "decrease"
    if direction is None or direction != expected_direction:
        missing.append("direction_unbound")

    if quantity is not None and changed_object is not None:
        matching_dispositions = tuple(
            disposition
            for disposition in dispositions
            if disposition.quantity_mention_id == quantity.mention_id
            and disposition.entity_mention_id == changed_object.mention_id
        )
        if len(matching_dispositions) != 1:
            missing.append("quantity_kind_unresolved")

    exact_evidence = _unique_evidence(tuple(
        span
        for group in (
            (() if proposal is None else proposal.evidence_spans),
            (() if cue_span is None else (cue_span,)),
            (() if quantity is None else (quantity.span,)),
            (() if changed_object is None else (changed_object.span,)),
        )
        for span in group
    ))
    if proposal is not None and cue_span is not None and proposal.evidence_spans != (cue_span,):
        missing.append("provenance_span_inexact")
    if relation is not None and quantity is not None and changed_object is not None and cue_span is not None:
        if relation.evidence_spans != (cue_span, quantity.span, changed_object.span):
            missing.append("provenance_span_inexact")
    if not exact_evidence or not all(_span_is_exact(frame, span) for span in exact_evidence):
        missing.append("provenance_span_inexact")

    if cue_span is not None and changed_object is not None and not _spans_are_local(
        frame.problem_text,
        cue_span,
        changed_object.span,
    ):
        missing.append("quantity_entity_nonlocal")
    if cue_span is not None and quantity is not None and not _spans_are_local(
        frame.problem_text,
        cue_span,
        quantity.span,
    ):
        missing.append("quantity_entity_nonlocal")

    missing_bindings = tuple(dict.fromkeys(missing))
    unresolved_hazards = tuple(sorted(unresolved))
    runnable = not missing_bindings and not unresolved_hazards
    return ContractAssessment(
        candidate_organ="unary_delta",
        missing_bindings=missing_bindings,
        unresolved_hazards=unresolved_hazards,
        runnable=runnable,
        explanation=(
            "one exact local unary gained/lost delta is grounded diagnostically"
            if runnable
            else "diagnostic candidate is not runnable: "
            + ", ".join((*missing_bindings, *unresolved_hazards))
        ),
        evidence_spans=exact_evidence,
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
    1. ``quantity_entity`` — triggered by its proposal-first foundational
       family in ``frame.proposals``.  Routes to
       ``assess_quantity_entity``, which closes only exact local evidence.
       Registry key: ``_CONTRACT_REGISTRY["quantity_entity_binding"]``.
    2. ``decrease_to_fraction`` — triggered by its proposal-first catalog
       family in ``frame.proposals``.  Routes to ``assess_fraction_decrease``,
       which still determines closure from bound frame evidence.
       Registry key: ``_CONTRACT_REGISTRY["fraction_decrease"]``.
    3. ``unary_delta`` — triggered by its proposal-first catalog family in
       ``frame.proposals``. Routes to ``assess_unary_delta``, which closes
       only exact local gained/lost cue, quantity, and object evidence.
       Registry key: ``_CONTRACT_REGISTRY["unary_delta"]``.
    4. ``percent_partition`` — triggered by its proposal-first catalog family
       in ``frame.proposals``.  Routes to ``assess_percent_partition``, which
       still determines closure from bound frame evidence.
       Registry key: ``_CONTRACT_REGISTRY["percent_partition"]``.
    5. ``container_packing`` / ``labor_rate`` — inline skeleton assessments;
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
    if _QUANTITY_ENTITY_FAMILY.family_id in proposed_family_ids:
        # Catalog: _CONTRACT_REGISTRY["quantity_entity_binding"]
        results.append(assess_quantity_entity(frame))
    if _DECREASE_TO_FRACTION_FAMILY.family_id in proposed_family_ids:
        # Catalog: _CONTRACT_REGISTRY["fraction_decrease"]
        results.append(assess_fraction_decrease(frame))
    if _UNARY_DELTA_FAMILY.family_id in proposed_family_ids:
        # Catalog: _CONTRACT_REGISTRY["unary_delta"]
        results.append(assess_unary_delta(frame))
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
