"""Diagnostic organ-contract readiness derived only from ProblemFrame evidence."""
from __future__ import annotations

from dataclasses import dataclass

from generate.kernel_facts import BoundRelation, SourceSpan
from generate.problem_frame import ProblemFrame


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


def assess_percent_partition(frame: ProblemFrame) -> ContractAssessment:
    mentions = {mention.mention_id: mention for mention in frame.mentions}
    subgroups = [relation for relation in frame.bound_relations if relation.relation_type == "subgroup_partition"]
    percentages = [relation for relation in frame.bound_relations if relation.relation_type == "percent_of"]

    def role_target(relation: BoundRelation, role_name: str) -> str | None:
        return next((role.target_id for role in relation.roles if role.role == role_name), None)

    linked_pairs = []
    for subgroup in subgroups:
        subgroup_part = role_target(subgroup, "part")
        if subgroup_part is None or subgroup_part not in mentions:
            continue
        subgroup_surface = mentions[subgroup_part].surface.lower()
        for percent in percentages:
            percent_part = role_target(percent, "part")
            if percent_part is not None and percent_part in mentions and mentions[percent_part].surface.lower() == subgroup_surface:
                linked_pairs.append((subgroup, percent))

    missing: list[str] = []
    if not any(role_target(relation, "whole") for relation in subgroups):
        missing.append("grounded_whole_entity")
    if not subgroups:
        missing.append("grounded_partition_subgroup")
    if not linked_pairs:
        missing.append("percent_or_fraction_linked_to_subgroup")
    question_target = frame.bound_question_target
    if question_target is None or not question_target.grounded:
        missing.append("grounded_question_target")

    unresolved: set[str] = set()
    categories = {hazard.category for hazard in frame.hazards}
    if "grounded_whole_entity" in missing and "unbound_base_quantity" in categories:
        unresolved.add("unbound_base_quantity")
    if "grounded_partition_subgroup" in missing and "percent_change_vs_percent_of" in categories:
        unresolved.add("percent_change_vs_percent_of")
    runnable = not missing and not unresolved
    return ContractAssessment(
        candidate_organ="percent_partition",
        missing_bindings=tuple(missing),
        unresolved_hazards=tuple(sorted(unresolved)),
        runnable=runnable,
        explanation=(
            "all percent-partition roles and the question target are grounded"
            if runnable else "diagnostic candidate is not runnable: " + ", ".join((*missing, *sorted(unresolved)))
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
    """Return deterministic diagnostic assessments; never admits serving."""
    frame_names = {candidate.name for candidate in frame.process_frames}
    results: list[ContractAssessment] = []
    if frame_names & {"partition", "consumption"}:
        results.append(assess_percent_partition(frame))
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
