"""Diagnostic-only SearchGateDecision adapter over ContractResidual records."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum, unique

from generate.contract_residuals import ContractResidual, ResidualKind
from generate.kernel_facts import SourceSpan

SEARCH_GATE_POLICY_VERSION = "search_gate.v1"


@unique
class SearchGateStatus(str, Enum):
    ELIGIBLE = "eligible"
    INELIGIBLE = "ineligible"
    BLOCKED = "blocked"
    UNASSESSABLE = "unassessable"


@dataclass(frozen=True, slots=True)
class SearchGateDecision:
    decision_id: str
    policy_version: str
    input_digest: str
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


def _enum_value(value: object) -> object:
    return getattr(value, "value", value)


def _map_residual(kind: object) -> tuple[SearchGateStatus, str]:
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


def _ordered_residuals(
    residuals: tuple[ContractResidual, ...],
) -> tuple[ContractResidual, ...]:
    return tuple(sorted(residuals, key=lambda residual: residual.residual_id))


def _collect_evidence_spans(
    residuals: tuple[ContractResidual, ...],
) -> tuple[SourceSpan, ...]:
    return tuple(
        span
        for residual in residuals
        for span in residual.evidence_spans
    )


def _residual_payload(residual: ContractResidual) -> dict[str, object]:
    return {
        "residual_id": residual.residual_id,
        "candidate_organ": residual.candidate_organ,
        "family_id": residual.family_id,
        "residual_kind": _enum_value(residual.residual_kind),
        "residual_code": residual.residual_code,
        "source_axis": _enum_value(residual.source_axis),
        "evidence_spans": [
            _span_payload(span) for span in residual.evidence_spans
        ],
    }


def _sha256_json(payload: dict[str, object]) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _input_digest(residuals: tuple[ContractResidual, ...]) -> str:
    return _sha256_json(
        {"residuals": [_residual_payload(residual) for residual in residuals]}
    )


def _decision_id(
    *,
    policy_version: str,
    input_digest: str,
    residual_ids: tuple[str, ...],
    candidate_organ: str | None,
    status: SearchGateStatus,
    reason_code: str,
    evidence_spans: tuple[SourceSpan, ...],
) -> str:
    return _sha256_json(
        {
            "policy_version": policy_version,
            "input_digest": input_digest,
            "residual_ids": list(residual_ids),
            "candidate_organ": candidate_organ,
            "status": status.value,
            "reason_code": reason_code,
            "evidence_spans": [_span_payload(span) for span in evidence_spans],
        }
    )


def _make_decision(
    *,
    ordered_residuals: tuple[ContractResidual, ...],
    candidate_organ: str | None,
    status: SearchGateStatus,
    reason_code: str,
    explanation: str,
) -> SearchGateDecision:
    residual_ids = tuple(residual.residual_id for residual in ordered_residuals)
    evidence_spans = _collect_evidence_spans(ordered_residuals)
    input_digest = _input_digest(ordered_residuals)
    decision_id = _decision_id(
        policy_version=SEARCH_GATE_POLICY_VERSION,
        input_digest=input_digest,
        residual_ids=residual_ids,
        candidate_organ=candidate_organ,
        status=status,
        reason_code=reason_code,
        evidence_spans=evidence_spans,
    )
    return SearchGateDecision(
        decision_id=decision_id,
        policy_version=SEARCH_GATE_POLICY_VERSION,
        input_digest=input_digest,
        residual_ids=residual_ids,
        candidate_organ=candidate_organ,
        status=status,
        reason_code=reason_code,
        evidence_spans=evidence_spans,
        explanation=explanation,
    )


def decide_search_gate(
    residuals: tuple[ContractResidual, ...],
) -> tuple[SearchGateDecision, ...]:
    if not residuals:
        return (
            _make_decision(
                ordered_residuals=(),
                candidate_organ=None,
                status=SearchGateStatus.UNASSESSABLE,
                reason_code="unassessable_empty_context",
                explanation="Empty residual context.",
            ),
        )

    ordered_residuals = _ordered_residuals(residuals)
    organs = {residual.candidate_organ for residual in ordered_residuals}
    if len(organs) > 1:
        return (
            _make_decision(
                ordered_residuals=ordered_residuals,
                candidate_organ=None,
                status=SearchGateStatus.UNASSESSABLE,
                reason_code="unassessable_mixed_candidate_organs",
                explanation="Mixed candidate organs in residual context.",
            ),
        )

    candidate_organ = ordered_residuals[0].candidate_organ
    mapped = [
        (_map_residual(residual.residual_kind), residual)
        for residual in ordered_residuals
    ]
    blocked_items = [
        item for item in mapped if item[0][0] != SearchGateStatus.ELIGIBLE
    ]

    if blocked_items:
        if any(
            status == SearchGateStatus.BLOCKED
            for (status, _), _ in blocked_items
        ):
            overall_status = SearchGateStatus.BLOCKED
        else:
            overall_status = SearchGateStatus.INELIGIBLE

        def blocked_priority_key(
            item: tuple[tuple[SearchGateStatus, str], ContractResidual],
        ) -> int:
            return _BLOCKED_PRIORITY.get(item[0][1], 99)

        best_blocked = min(blocked_items, key=blocked_priority_key)
        reason_code = best_blocked[0][1]
        explanation = f"Search gate blocked: {best_blocked[1].explanation}"
    else:
        overall_status = SearchGateStatus.ELIGIBLE

        def eligible_priority_key(
            item: tuple[tuple[SearchGateStatus, str], ContractResidual],
        ) -> int:
            return _ELIGIBLE_PRIORITY.get(item[0][1], 99)

        best_eligible = min(mapped, key=eligible_priority_key)
        reason_code = best_eligible[0][1]
        explanation = f"Search gate eligible: {best_eligible[1].explanation}"

    return (
        _make_decision(
            ordered_residuals=ordered_residuals,
            candidate_organ=candidate_organ,
            status=overall_status,
            reason_code=reason_code,
            explanation=explanation,
        ),
    )


__all__ = [
    "SearchGateStatus",
    "SearchGateDecision",
    "decide_search_gate",
]
