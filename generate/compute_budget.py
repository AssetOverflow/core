"""Diagnostic-only compute budget projection over search-gate decisions."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum, unique

from generate.kernel_facts import SourceSpan
from generate.search_gate import SearchGateDecision, SearchGateStatus

COMPUTE_BUDGET_POLICY_VERSION = "compute_budget.v1"


@unique
class ComputeBudgetStatus(str, Enum):
    BUDGET_ALLOWED = "budget_allowed"
    BUDGET_BLOCKED = "budget_blocked"
    BUDGET_ZERO = "budget_zero"
    BUDGET_UNASSESSABLE = "budget_unassessable"


@dataclass(frozen=True, slots=True)
class ComputeBudgetDecision:
    budget_id: str
    policy_version: str
    gate_decision_id: str
    gate_policy_version: str
    gate_input_digest: str
    status: ComputeBudgetStatus
    reason_code: str
    max_candidates: int
    max_depth: int
    max_steps: int
    max_wallclock_ms: int | None
    max_parallelism: int
    evidence_spans: tuple[SourceSpan, ...]
    explanation: str


@dataclass(frozen=True, slots=True)
class _BudgetPolicyRow:
    reason_code: str
    max_candidates: int
    max_depth: int
    max_steps: int
    max_parallelism: int


_ELIGIBLE_POLICY: dict[str, _BudgetPolicyRow] = {
    "eligible_missing_role": _BudgetPolicyRow(
        reason_code="budget_allowed_missing_role",
        max_candidates=5,
        max_depth=2,
        max_steps=10,
        max_parallelism=1,
    ),
    "eligible_missing_relation": _BudgetPolicyRow(
        reason_code="budget_allowed_missing_relation",
        max_candidates=5,
        max_depth=2,
        max_steps=10,
        max_parallelism=1,
    ),
    "eligible_missing_proposal": _BudgetPolicyRow(
        reason_code="budget_allowed_missing_proposal",
        max_candidates=3,
        max_depth=1,
        max_steps=5,
        max_parallelism=1,
    ),
    "eligible_target_unbound": _BudgetPolicyRow(
        reason_code="budget_allowed_target_unbound",
        max_candidates=5,
        max_depth=2,
        max_steps=10,
        max_parallelism=1,
    ),
}

_ZERO_ROW = _BudgetPolicyRow(
    reason_code="",
    max_candidates=0,
    max_depth=0,
    max_steps=0,
    max_parallelism=0,
)


def _safe_getattr(value: object, name: str) -> object:
    try:
        return getattr(value, name, None)
    except Exception:
        return None


def _valid_nonempty_text(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        return bool(value.strip())
    except Exception:
        return False


def _text_or_empty(value: object) -> str:
    return value if isinstance(value, str) else ""


def _valid_span(span: object) -> bool:
    if not isinstance(span, SourceSpan):
        return False
    try:
        if not isinstance(span.text, str):
            return False
        if type(span.start) is not int or type(span.end) is not int:
            return False
        if span.start < 0 or span.end < span.start:
            return False
        return span.sentence_index is None or type(span.sentence_index) is int
    except Exception:
        return False


def _evidence_spans(value: object) -> tuple[SourceSpan, ...] | None:
    if not isinstance(value, tuple):
        return None
    if not all(_valid_span(span) for span in value):
        return None
    return value


def _span_payload(span: SourceSpan) -> dict[str, object]:
    return {
        "text": span.text,
        "start": span.start,
        "end": span.end,
        "sentence_index": span.sentence_index,
    }


def _budget_id(
    *,
    policy_version: str,
    gate_decision_id: str,
    gate_policy_version: str,
    gate_input_digest: str,
    status: ComputeBudgetStatus,
    reason_code: str,
    row: _BudgetPolicyRow,
    evidence_spans: tuple[SourceSpan, ...],
) -> str:
    payload = {
        "policy_version": policy_version,
        "gate_decision_id": gate_decision_id,
        "gate_policy_version": gate_policy_version,
        "gate_input_digest": gate_input_digest,
        "status": status.value,
        "reason_code": reason_code,
        "max_candidates": row.max_candidates,
        "max_depth": row.max_depth,
        "max_steps": row.max_steps,
        "max_parallelism": row.max_parallelism,
        "evidence_spans": [_span_payload(span) for span in evidence_spans],
    }
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _make_decision(
    *,
    gate_decision_id: str,
    gate_policy_version: str,
    gate_input_digest: str,
    status: ComputeBudgetStatus,
    reason_code: str,
    row: _BudgetPolicyRow,
    evidence_spans: tuple[SourceSpan, ...],
    explanation: str,
) -> ComputeBudgetDecision:
    budget_id = _budget_id(
        policy_version=COMPUTE_BUDGET_POLICY_VERSION,
        gate_decision_id=gate_decision_id,
        gate_policy_version=gate_policy_version,
        gate_input_digest=gate_input_digest,
        status=status,
        reason_code=reason_code,
        row=row,
        evidence_spans=evidence_spans,
    )
    return ComputeBudgetDecision(
        budget_id=budget_id,
        policy_version=COMPUTE_BUDGET_POLICY_VERSION,
        gate_decision_id=gate_decision_id,
        gate_policy_version=gate_policy_version,
        gate_input_digest=gate_input_digest,
        status=status,
        reason_code=reason_code,
        max_candidates=row.max_candidates,
        max_depth=row.max_depth,
        max_steps=row.max_steps,
        max_wallclock_ms=None,
        max_parallelism=row.max_parallelism,
        evidence_spans=evidence_spans,
        explanation=explanation,
    )


def _unassessable_decision(
    *,
    gate_decision_id: str,
    gate_policy_version: str,
    gate_input_digest: str,
    evidence_spans: tuple[SourceSpan, ...],
    reason_code: str,
) -> ComputeBudgetDecision:
    return _make_decision(
        gate_decision_id=gate_decision_id,
        gate_policy_version=gate_policy_version,
        gate_input_digest=gate_input_digest,
        status=ComputeBudgetStatus.BUDGET_UNASSESSABLE,
        reason_code=reason_code,
        row=_ZERO_ROW,
        evidence_spans=evidence_spans,
        explanation=f"Compute budget input is unassessable: {reason_code}.",
    )


def decide_compute_budget_for_gate(
    gate_decision: SearchGateDecision,
) -> ComputeBudgetDecision:
    raw_decision_id = _safe_getattr(gate_decision, "decision_id")
    raw_policy_version = _safe_getattr(gate_decision, "policy_version")
    raw_input_digest = _safe_getattr(gate_decision, "input_digest")
    raw_status = _safe_getattr(gate_decision, "status")
    raw_reason_code = _safe_getattr(gate_decision, "reason_code")
    raw_evidence_spans = _safe_getattr(gate_decision, "evidence_spans")

    gate_decision_id = _text_or_empty(raw_decision_id)
    gate_policy_version = _text_or_empty(raw_policy_version)
    gate_input_digest = _text_or_empty(raw_input_digest)
    validated_spans = _evidence_spans(raw_evidence_spans)
    evidence_spans = validated_spans if validated_spans is not None else ()

    if not _valid_nonempty_text(raw_decision_id):
        return _unassessable_decision(
            gate_decision_id=gate_decision_id,
            gate_policy_version=gate_policy_version,
            gate_input_digest=gate_input_digest,
            evidence_spans=evidence_spans,
            reason_code="budget_unassessable_missing_gate_decision_id",
        )
    if not _valid_nonempty_text(raw_policy_version):
        return _unassessable_decision(
            gate_decision_id=gate_decision_id,
            gate_policy_version=gate_policy_version,
            gate_input_digest=gate_input_digest,
            evidence_spans=evidence_spans,
            reason_code="budget_unassessable_missing_gate_policy_version",
        )
    if not _valid_nonempty_text(raw_input_digest):
        return _unassessable_decision(
            gate_decision_id=gate_decision_id,
            gate_policy_version=gate_policy_version,
            gate_input_digest=gate_input_digest,
            evidence_spans=evidence_spans,
            reason_code="budget_unassessable_missing_gate_input_digest",
        )
    if not any(raw_status is status for status in SearchGateStatus):
        return _unassessable_decision(
            gate_decision_id=gate_decision_id,
            gate_policy_version=gate_policy_version,
            gate_input_digest=gate_input_digest,
            evidence_spans=evidence_spans,
            reason_code="budget_unassessable_unknown_gate_status",
        )
    if validated_spans is None:
        return _unassessable_decision(
            gate_decision_id=gate_decision_id,
            gate_policy_version=gate_policy_version,
            gate_input_digest=gate_input_digest,
            evidence_spans=(),
            reason_code="budget_unassessable_malformed_evidence_spans",
        )

    if raw_status is not SearchGateStatus.ELIGIBLE:
        return _make_decision(
            gate_decision_id=gate_decision_id,
            gate_policy_version=gate_policy_version,
            gate_input_digest=gate_input_digest,
            status=ComputeBudgetStatus.BUDGET_BLOCKED,
            reason_code="budget_blocked_gate_not_eligible",
            row=_ZERO_ROW,
            evidence_spans=evidence_spans,
            explanation="Compute budget blocked because the gate is not eligible.",
        )

    policy_row = (
        _ELIGIBLE_POLICY.get(raw_reason_code)
        if isinstance(raw_reason_code, str)
        else None
    )
    if policy_row is None:
        return _unassessable_decision(
            gate_decision_id=gate_decision_id,
            gate_policy_version=gate_policy_version,
            gate_input_digest=gate_input_digest,
            evidence_spans=evidence_spans,
            reason_code="budget_unassessable_unknown_gate_reason",
        )

    return _make_decision(
        gate_decision_id=gate_decision_id,
        gate_policy_version=gate_policy_version,
        gate_input_digest=gate_input_digest,
        status=ComputeBudgetStatus.BUDGET_ALLOWED,
        reason_code=policy_row.reason_code,
        row=policy_row,
        evidence_spans=evidence_spans,
        explanation="Compute budget allowed by the closed v1 policy.",
    )


def decide_compute_budget(
    gate_decisions: tuple[SearchGateDecision, ...],
) -> tuple[ComputeBudgetDecision, ...]:
    return tuple(
        decide_compute_budget_for_gate(gate_decision)
        for gate_decision in gate_decisions
    )


__all__ = [
    "COMPUTE_BUDGET_POLICY_VERSION",
    "ComputeBudgetStatus",
    "ComputeBudgetDecision",
    "decide_compute_budget",
    "decide_compute_budget_for_gate",
]
