"""Diagnostic-only SearchGateDecision adapter over ContractResidual records.

This module is a read-only, fail-closed decision gate. It must not search,
allocate budget, generate candidates, repair frames, or mutate any serving or
runtime state. The dependency direction is:

    ContractAssessment -> ContractResidual -> SearchGateDecision
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum, unique

from generate.contract_residuals import ContractResidual, ResidualKind
from generate.kernel_facts import SourceSpan


@unique
class SearchGateStatus(str, Enum):
    ELIGIBLE = "eligible"
    INELIGIBLE = "ineligible"
    BLOCKED = "blocked"
    UNASSESSABLE = "unassessable"


@dataclass(frozen=True, slots=True)
class SearchGateDecision:
    decision_id: str
    residual_ids: tuple[str, ...]
    candidate_organ: str | None
    status: SearchGateStatus
    reason_code: str
    evidence_spans: tuple[SourceSpan, ...]
    explanation: str


_KIND_MAP: dict[ResidualKind, tuple[SearchGateStatus, str]] = {
    ResidualKind.MISSING_PROPOSAL: (
        SearchGateStatus.ELIGIBLE,
        "eligible_missing_proposal",
    ),
    ResidualKind.MISSING_RELATION: (
        SearchGateStatus.ELIGIBLE,
        "eligible_missing_relation",
    ),
    ResidualKind.MISSING_ROLE: (
        SearchGateStatus.ELIGIBLE,
        "eligible_missing_role",
    ),
    ResidualKind.TARGET_UNBOUND: (
        SearchGateStatus.ELIGIBLE,
        "eligible_target_unbound",
    ),
    ResidualKind.AMBIGUOUS_RELATION: (
        SearchGateStatus.BLOCKED,
        "blocked_ambiguous_relation",
    ),
    ResidualKind.AMBIGUOUS_ROLE: (
        SearchGateStatus.BLOCKED,
        "blocked_ambiguous_role",
    ),
    ResidualKind.INEXACT_PROVENANCE: (
        SearchGateStatus.BLOCKED,
        "blocked_inexact_provenance",
    ),
    ResidualKind.NONLOCAL_BINDING: (
        SearchGateStatus.BLOCKED,
        "blocked_nonlocal_binding",
    ),
    ResidualKind.UNSUPPORTED_TOPOLOGY: (
        SearchGateStatus.BLOCKED,
        "blocked_unsupported_topology",
    ),
    ResidualKind.UNIT_OBJECT_CONFLICT: (
        SearchGateStatus.BLOCKED,
        "blocked_unit_object_conflict",
    ),
    ResidualKind.HAZARD_BLOCKED: (
        SearchGateStatus.BLOCKED,
        "blocked_hazard",
    ),
    ResidualKind.CONTRACT_GAP_UNCLASSIFIED: (
        SearchGateStatus.BLOCKED,
        "blocked_unclassified_gap",
    ),
}

_BLOCKED_PRIORITY: dict[str, int] = {
    "blocked_hazard": 1,
    "blocked_unit_object_conflict": 2,
    "blocked_unsupported_topology": 3,
    "blocked_nonlocal_binding": 4,
    "blocked_inexact_provenance": 5,
    "blocked_ambiguous_relation": 6,
    "blocked_ambiguous_role": 7,
    "blocked_unclassified_gap": 8,
}

_ELIGIBLE_PRIORITY: dict[str, int] = {
    "eligible_missing_proposal": 1,
    "eligible_missing_relation": 2,
    "eligible_missing_role": 3,
    "eligible_target_unbound": 4,
}


def _map_residual(kind: ResidualKind) -> tuple[SearchGateStatus, str]:
    return _KIND_MAP.get(
        kind, (SearchGateStatus.INELIGIBLE, "blocked_unclassified_gap")
    )


def _span_payload(span: SourceSpan) -> dict[str, object]:
    return {
        "text": span.text,
        "start": span.start,
        "end": span.end,
        "sentence_index": span.sentence_index,
    }


def _decision_id(
    *,
    residual_ids: tuple[str, ...],
    candidate_organ: str | None,
    status: SearchGateStatus,
    reason_code: str,
    evidence_spans: tuple[SourceSpan, ...],
) -> str:
    payload = {
        "residual_ids": list(residual_ids),
        "candidate_organ": candidate_organ,
        "status": status.value,
        "reason_code": reason_code,
        "evidence_spans": [_span_payload(span) for span in evidence_spans],
    }
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def decide_search_gate(
    residuals: tuple[ContractResidual, ...],
) -> tuple[SearchGateDecision, ...]:
    """Assess eligibility of the residual context for future exploration.

    This function operates over a residual context/set, grouping residuals
    together, and fails closed if any residual blocks exploration.
    """
    if not residuals:
        status = SearchGateStatus.UNASSESSABLE
        reason_code = "unassessable_empty_context"
        candidate_organ = None
        residual_ids: tuple[str, ...] = ()
        evidence_spans: tuple[SourceSpan, ...] = ()
        explanation = "Empty residual context."
        decision_id = _decision_id(
            residual_ids=residual_ids,
            candidate_organ=candidate_organ,
            status=status,
            reason_code=reason_code,
            evidence_spans=evidence_spans,
        )
        return (
            SearchGateDecision(
                decision_id=decision_id,
                residual_ids=residual_ids,
                candidate_organ=candidate_organ,
                status=status,
                reason_code=reason_code,
                evidence_spans=evidence_spans,
                explanation=explanation,
            ),
        )

    # Context Grouping Check:
    organs = {r.candidate_organ for r in residuals}
    if len(organs) > 1:
        # Mixed candidate organs: Fail Closed
        status = SearchGateStatus.UNASSESSABLE
        reason_code = "unassessable_mixed_candidate_organs"
        candidate_organ = None
        sorted_res = sorted(residuals, key=lambda r: r.residual_id)
        residual_ids = tuple(r.residual_id for r in sorted_res)

        # Collect and deduplicate spans deterministically
        seen_spans = set()
        spans_list = []
        for r in sorted_res:
            for span in r.evidence_spans:
                span_key = (span.text, span.start, span.end, span.sentence_index)
                if span_key not in seen_spans:
                    seen_spans.add(span_key)
                    spans_list.append(span)
        evidence_spans = tuple(spans_list)
        explanation = "Mixed candidate organs in residual context."
        decision_id = _decision_id(
            residual_ids=residual_ids,
            candidate_organ=candidate_organ,
            status=status,
            reason_code=reason_code,
            evidence_spans=evidence_spans,
        )
        return (
            SearchGateDecision(
                decision_id=decision_id,
                residual_ids=residual_ids,
                candidate_organ=candidate_organ,
                status=status,
                reason_code=reason_code,
                evidence_spans=evidence_spans,
                explanation=explanation,
            ),
        )

    # Single organ context
    candidate_organ = residuals[0].candidate_organ
    sorted_res = sorted(residuals, key=lambda r: r.residual_id)
    residual_ids = tuple(r.residual_id for r in sorted_res)

    # Collect and deduplicate spans deterministically
    seen_spans = set()
    spans_list = []
    for r in sorted_res:
        for span in r.evidence_spans:
            span_key = (span.text, span.start, span.end, span.sentence_index)
            if span_key not in seen_spans:
                seen_spans.add(span_key)
                spans_list.append(span)
    evidence_spans = tuple(spans_list)

    mapped = [(_map_residual(r.residual_kind), r) for r in sorted_res]
    blocked_items = [
        item for item in mapped if item[0][0] != SearchGateStatus.ELIGIBLE
    ]

    if blocked_items:
        # Determine overall fail-closed status: BLOCKED or INELIGIBLE
        if any(
            status == SearchGateStatus.BLOCKED
            for (status, _), _ in blocked_items
        ):
            overall_status = SearchGateStatus.BLOCKED
        else:
            overall_status = SearchGateStatus.INELIGIBLE

        # Select highest-priority reason code
        def blocked_priority_key(item: tuple[tuple[SearchGateStatus, str], ContractResidual]) -> int:
            return _BLOCKED_PRIORITY.get(item[0][1], 99)

        best_blocked = min(blocked_items, key=blocked_priority_key)
        reason_code = best_blocked[0][1]
        explanation = f"Search gate blocked: {best_blocked[1].explanation}"
    else:
        # All residuals are eligible
        overall_status = SearchGateStatus.ELIGIBLE

        # Select highest-priority reason code
        def eligible_priority_key(item: tuple[tuple[SearchGateStatus, str], ContractResidual]) -> int:
            return _ELIGIBLE_PRIORITY.get(item[0][1], 99)

        best_eligible = min(mapped, key=eligible_priority_key)
        reason_code = best_eligible[0][1]
        explanation = f"Search gate eligible: {best_eligible[1].explanation}"

    decision_id = _decision_id(
        residual_ids=residual_ids,
        candidate_organ=candidate_organ,
        status=overall_status,
        reason_code=reason_code,
        evidence_spans=evidence_spans,
    )

    return (
        SearchGateDecision(
            decision_id=decision_id,
            residual_ids=residual_ids,
            candidate_organ=candidate_organ,
            status=overall_status,
            reason_code=reason_code,
            evidence_spans=evidence_spans,
            explanation=explanation,
        ),
    )


__all__ = [
    "SearchGateStatus",
    "SearchGateDecision",
    "decide_search_gate",
]
