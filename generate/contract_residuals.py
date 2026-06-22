"""Diagnostic-only ContractResidual projection over ContractAssessment outputs.

This module is a leaf read-model projector. It must not assess contracts, build
frames, search, repair, serve, mutate artifacts, or allocate compute. The only
dependency direction is:

    ContractAssessment -> ContractResidual
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum, unique

from generate.kernel_facts import SourceSpan
from generate.problem_frame_contracts import (
    ContractAssessment,
    get_contract_family_id,
)


@unique
class ResidualKind(str, Enum):
    MISSING_PROPOSAL = "missing_proposal"
    MISSING_RELATION = "missing_relation"
    MISSING_ROLE = "missing_role"
    AMBIGUOUS_RELATION = "ambiguous_relation"
    AMBIGUOUS_ROLE = "ambiguous_role"
    INEXACT_PROVENANCE = "inexact_provenance"
    NONLOCAL_BINDING = "nonlocal_binding"
    UNSUPPORTED_TOPOLOGY = "unsupported_topology"
    UNIT_OBJECT_CONFLICT = "unit_object_conflict"
    HAZARD_BLOCKED = "hazard_blocked"
    TARGET_UNBOUND = "target_unbound"
    CONTRACT_GAP_UNCLASSIFIED = "contract_gap_unclassified"


@unique
class ResidualSourceAxis(str, Enum):
    PROPOSAL = "proposal"
    RELATION = "relation"
    ROLE = "role"
    PROVENANCE = "provenance"
    LOCALITY = "locality"
    TOPOLOGY = "topology"
    UNIT_OBJECT = "unit_object"
    HAZARD = "hazard"
    TARGET = "target"
    UNKNOWN = "unknown"


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


_FALLBACK_CLASSIFICATION: tuple[ResidualKind, ResidualSourceAxis] = (
    ResidualKind.CONTRACT_GAP_UNCLASSIFIED,
    ResidualSourceAxis.UNKNOWN,
)

_LABEL_CLASSIFICATIONS: dict[str, tuple[ResidualKind, ResidualSourceAxis]] = {
    "quantity_entity_proposal_required": (
        ResidualKind.MISSING_PROPOSAL,
        ResidualSourceAxis.PROPOSAL,
    ),
    "unary_delta_proposal_required": (
        ResidualKind.MISSING_PROPOSAL,
        ResidualSourceAxis.PROPOSAL,
    ),
    "local_binding_relation_unbound": (
        ResidualKind.MISSING_RELATION,
        ResidualSourceAxis.RELATION,
    ),
    "quantity_unbound": (ResidualKind.MISSING_ROLE, ResidualSourceAxis.ROLE),
    "entity_unbound": (ResidualKind.MISSING_ROLE, ResidualSourceAxis.ROLE),
    "quantity_kind_unresolved": (
        ResidualKind.MISSING_ROLE,
        ResidualSourceAxis.ROLE,
    ),
    "base_quantity_unbound": (ResidualKind.MISSING_ROLE, ResidualSourceAxis.ROLE),
    "scale_unbound": (ResidualKind.MISSING_ROLE, ResidualSourceAxis.ROLE),
    "state_entity_unbound": (ResidualKind.MISSING_ROLE, ResidualSourceAxis.ROLE),
    "grounded_partition_subgroup": (
        ResidualKind.MISSING_ROLE,
        ResidualSourceAxis.ROLE,
    ),
    "grounded_whole_entity": (
        ResidualKind.MISSING_ROLE,
        ResidualSourceAxis.ROLE,
    ),
    "original_whole_unbound": (
        ResidualKind.MISSING_ROLE,
        ResidualSourceAxis.ROLE,
    ),
    "action_cue_unbound": (ResidualKind.MISSING_ROLE, ResidualSourceAxis.ROLE),
    "delta_quantity_unbound": (
        ResidualKind.MISSING_ROLE,
        ResidualSourceAxis.ROLE,
    ),
    "changed_object_unbound": (
        ResidualKind.MISSING_ROLE,
        ResidualSourceAxis.ROLE,
    ),
    "direction_unbound": (ResidualKind.MISSING_ROLE, ResidualSourceAxis.ROLE),
    "local_binding_relation_ambiguous": (
        ResidualKind.AMBIGUOUS_RELATION,
        ResidualSourceAxis.RELATION,
    ),
    "decrease_relation_ambiguous": (
        ResidualKind.AMBIGUOUS_RELATION,
        ResidualSourceAxis.RELATION,
    ),
    "unary_delta_relation_ambiguous": (
        ResidualKind.AMBIGUOUS_RELATION,
        ResidualSourceAxis.RELATION,
    ),
    "quantity_ambiguous": (ResidualKind.AMBIGUOUS_ROLE, ResidualSourceAxis.ROLE),
    "entity_ambiguous": (ResidualKind.AMBIGUOUS_ROLE, ResidualSourceAxis.ROLE),
    "multiple_original_whole_candidates": (
        ResidualKind.AMBIGUOUS_ROLE,
        ResidualSourceAxis.ROLE,
    ),
    "delta_quantity_ambiguous": (
        ResidualKind.AMBIGUOUS_ROLE,
        ResidualSourceAxis.ROLE,
    ),
    "changed_object_ambiguous": (
        ResidualKind.AMBIGUOUS_ROLE,
        ResidualSourceAxis.ROLE,
    ),
    "provenance_span_inexact": (
        ResidualKind.INEXACT_PROVENANCE,
        ResidualSourceAxis.PROVENANCE,
    ),
    "base_quantity_provenance_missing": (
        ResidualKind.INEXACT_PROVENANCE,
        ResidualSourceAxis.PROVENANCE,
    ),
    "scale_provenance_missing": (
        ResidualKind.INEXACT_PROVENANCE,
        ResidualSourceAxis.PROVENANCE,
    ),
    "quantity_entity_nonlocal": (
        ResidualKind.NONLOCAL_BINDING,
        ResidualSourceAxis.LOCALITY,
    ),
    "pronoun_antecedent_unresolved": (
        ResidualKind.NONLOCAL_BINDING,
        ResidualSourceAxis.LOCALITY,
    ),
    "percent_subgroup_links_incomplete": (
        ResidualKind.UNSUPPORTED_TOPOLOGY,
        ResidualSourceAxis.TOPOLOGY,
    ),
    "inverse_topology_unlicensed": (
        ResidualKind.UNSUPPORTED_TOPOLOGY,
        ResidualSourceAxis.TOPOLOGY,
    ),
    "event_assertion_unlicensed": (
        ResidualKind.UNSUPPORTED_TOPOLOGY,
        ResidualSourceAxis.TOPOLOGY,
    ),
    "passive_voice_unsupported": (
        ResidualKind.UNSUPPORTED_TOPOLOGY,
        ResidualSourceAxis.TOPOLOGY,
    ),
    "multiple_actor_surface": (
        ResidualKind.UNSUPPORTED_TOPOLOGY,
        ResidualSourceAxis.TOPOLOGY,
    ),
    "unit_kind_conflict": (
        ResidualKind.UNIT_OBJECT_CONFLICT,
        ResidualSourceAxis.UNIT_OBJECT,
    ),
    "unit_continuity_unproven": (
        ResidualKind.UNIT_OBJECT_CONFLICT,
        ResidualSourceAxis.UNIT_OBJECT,
    ),
    "unit_object_conflict": (
        ResidualKind.UNIT_OBJECT_CONFLICT,
        ResidualSourceAxis.UNIT_OBJECT,
    ),
    "competing_family_context": (
        ResidualKind.HAZARD_BLOCKED,
        ResidualSourceAxis.HAZARD,
    ),
    "percent_change_vs_percent_of": (
        ResidualKind.HAZARD_BLOCKED,
        ResidualSourceAxis.HAZARD,
    ),
    "state_entity_continuity_unproven": (
        ResidualKind.HAZARD_BLOCKED,
        ResidualSourceAxis.HAZARD,
    ),
    "scale_out_of_range": (
        ResidualKind.HAZARD_BLOCKED,
        ResidualSourceAxis.HAZARD,
    ),
    "partition_subgroups_not_distinct": (
        ResidualKind.HAZARD_BLOCKED,
        ResidualSourceAxis.HAZARD,
    ),
    "delta_decrease_target_unbound": (
        ResidualKind.TARGET_UNBOUND,
        ResidualSourceAxis.TARGET,
    ),
    "delta_decrease_target_required": (
        ResidualKind.TARGET_UNBOUND,
        ResidualSourceAxis.TARGET,
    ),
    "grounded_question_target": (
        ResidualKind.TARGET_UNBOUND,
        ResidualSourceAxis.TARGET,
    ),
    "forward_aggregate_target_required": (
        ResidualKind.TARGET_UNBOUND,
        ResidualSourceAxis.TARGET,
    ),
}


def _classify_label(label: str) -> tuple[ResidualKind, ResidualSourceAxis]:
    return _LABEL_CLASSIFICATIONS.get(label, _FALLBACK_CLASSIFICATION)


def _dedupe_codes(codes: tuple[str, ...]) -> tuple[str, ...]:
    seen: set[str] = set()
    unique: list[str] = []
    for code in codes:
        if code in seen:
            continue
        seen.add(code)
        unique.append(code)
    return tuple(unique)


def _span_payload(span: SourceSpan) -> dict[str, object]:
    return {
        "text": span.text,
        "start": span.start,
        "end": span.end,
        "sentence_index": span.sentence_index,
    }


def _residual_id(
    *,
    candidate_organ: str,
    residual_kind: ResidualKind,
    residual_code: str,
    evidence_spans: tuple[SourceSpan, ...],
) -> str:
    payload = {
        "candidate_organ": candidate_organ,
        "residual_kind": residual_kind.value,
        "residual_code": residual_code,
        "evidence_spans": [_span_payload(span) for span in evidence_spans],
    }
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _project_one(
    assessment: ContractAssessment,
    residual_code: str,
) -> ContractResidual:
    residual_kind, source_axis = _classify_label(residual_code)
    evidence_spans = assessment.evidence_spans
    return ContractResidual(
        residual_id=_residual_id(
            candidate_organ=assessment.candidate_organ,
            residual_kind=residual_kind,
            residual_code=residual_code,
            evidence_spans=evidence_spans,
        ),
        candidate_organ=assessment.candidate_organ,
        family_id=get_contract_family_id(assessment.candidate_organ),
        residual_kind=residual_kind,
        residual_code=residual_code,
        source_axis=source_axis,
        evidence_spans=evidence_spans,
        explanation=assessment.explanation,
    )


def project_contract_residuals(
    assessments: tuple[ContractAssessment, ...],
) -> tuple[ContractResidual, ...]:
    """Project refused contract assessments into non-authoritative residuals.

    Runnable assessments produce no residuals, even if a malformed assessment carries
    missing or unresolved labels. The residual projection is diagnostic only and
    must not be used as serving/search/mutation authority.
    """
    residuals: list[ContractResidual] = []
    for assessment in assessments:
        if assessment.runnable:
            continue
        codes = _dedupe_codes(
            (*assessment.missing_bindings, *assessment.unresolved_hazards)
        )
        residuals.extend(_project_one(assessment, code) for code in codes)
    return tuple(sorted(residuals, key=lambda residual: residual.residual_id))


__all__ = [
    "ResidualKind",
    "ResidualSourceAxis",
    "ContractResidual",
    "project_contract_residuals",
]
