"""Read-only sealed-practice evidence projection helpers for Workbench.

This module is intentionally inert. It projects already-persisted practice evidence
for a turn into a Workbench-facing read model. It does not run geometric search,
execute candidate operators, run replay, seal traces, mutate journals, or grant
serving authority.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

PipelineEvidenceStatus = Literal["recorded", "missing_evidence"]
PracticeRecordKind = Literal["sealed_trace", "trace_refusal"]
PracticeCardKind = Literal[
    "problem_frame",
    "contract_assessment",
    "residuals",
    "search_gate",
    "compute_budget",
    "geometric_search_run",
    "candidate_attempts",
    "attempt_bindings",
    "replay_results",
    "replay_refusals",
    "sealed_trace",
    "trace_refusal",
]

PRACTICE_EVIDENCE_ABSENT = "sealed practice evidence was not persisted for this turn"


@dataclass(frozen=True, slots=True)
class PracticeSourceSpanView:
    text: str
    start: int
    end: int
    sentence_index: int | None = None


@dataclass(frozen=True, slots=True)
class PracticeEvidenceCard:
    """A read-only upstream identity card.

    `refs` are identity references only. They are not executable handles, mutation
    handles, or proof of serving authority.
    """

    kind: PracticeCardKind
    status: PipelineEvidenceStatus
    refs: list[str] = field(default_factory=list)
    summary: str = ""


@dataclass(frozen=True, slots=True)
class SealedPracticeTraceView:
    trace_id: str
    trace_policy_version: str
    input_digest: str
    problem_frame_digest: str
    original_contract_assessment_id: str
    residual_ids: list[str]
    search_gate_decision_id: str
    compute_budget_id: str
    geometric_search_run_id: str
    candidate_attempt_ids: list[str]
    candidate_attempt_binding_ids: list[str]
    replay_result_ids: list[str]
    replay_refusal_ids: list[str]
    upstream_identity_chain: list[str]
    practice_disposition: str
    trace_records: list[str]
    evidence_spans: list[PracticeSourceSpanView] = field(default_factory=list)
    created_by_policy: str = ""
    explanation: str = ""


@dataclass(frozen=True, slots=True)
class PracticeTraceRefusalView:
    trace_refusal_id: str
    trace_policy_version: str
    input_digest: str | None
    practice_disposition: str
    reason_codes: list[str]
    explanation: str = ""


@dataclass(frozen=True, slots=True)
class PracticeEvidence:
    """Workbench-facing sealed-practice evidence for one turn.

    This record is a projection only. The authority fields are deliberately
    load-bearing: Workbench may inspect this evidence, but this endpoint never
    runs replay, mutates journals, executes operators, or allows serving.
    """

    schema_version: Literal["practice_evidence_v1"]
    turn_id: int
    status: PipelineEvidenceStatus
    missing_reason: str | None
    record_kind: PracticeRecordKind | None
    practice_disposition: str | None
    chain: list[PracticeEvidenceCard] = field(default_factory=list)
    sealed_trace: SealedPracticeTraceView | None = None
    trace_refusal: PracticeTraceRefusalView | None = None
    diagnostic_only: bool = True
    serving_allowed: bool = False
    mutation_allowed: bool = False
    replay_execution_allowed: bool = False
    replay_executed_by_workbench: bool = False


def missing_practice_evidence(turn_id: int, reason: str) -> PracticeEvidence:
    """Return the honest absence state for legacy turns.

    Absence is not an error and not a failed proof. It means the selected turn has
    no persisted sealed-practice evidence to project.
    """

    return PracticeEvidence(
        schema_version="practice_evidence_v1",
        turn_id=turn_id,
        status="missing_evidence",
        missing_reason=reason,
        record_kind=None,
        practice_disposition=None,
        chain=[],
        sealed_trace=None,
        trace_refusal=None,
        diagnostic_only=True,
        serving_allowed=False,
        mutation_allowed=False,
        replay_execution_allowed=False,
        replay_executed_by_workbench=False,
    )


def practice_evidence_from_journal_entry(entry: Any) -> PracticeEvidence:
    """Project persisted sealed-practice evidence from a journal entry if present."""

    turn_id = int(getattr(entry, "turn_id"))
    payload = getattr(entry, "practice_evidence", None)
    if payload is None:
        return missing_practice_evidence(turn_id, PRACTICE_EVIDENCE_ABSENT)

    if isinstance(payload, PracticeEvidence):
        return payload

    try:
        return _practice_evidence_from_payload(turn_id, payload)
    except (KeyError, TypeError, ValueError) as exc:
        return missing_practice_evidence(
            turn_id,
            f"practice evidence payload projection failed: {exc}",
        )


def _practice_evidence_from_payload(turn_id: int, payload: Any) -> PracticeEvidence:
    schema_version = _field(payload, "schema_version")
    if schema_version == "practice_evidence_v1":
        status = _field(payload, "status")
        if status == "missing_evidence":
            return missing_practice_evidence(
                turn_id,
                _field(payload, "missing_reason") or PRACTICE_EVIDENCE_ABSENT,
            )
        if status != "recorded":
            return missing_practice_evidence(turn_id, f"unsupported status: {status}")
        sealed_payload = _field(payload, "sealed_trace")
        refusal_payload = _field(payload, "trace_refusal")
    elif _field(payload, "trace_id") is not None:
        sealed_payload = payload
        refusal_payload = None
    elif _field(payload, "trace_refusal_id") is not None:
        sealed_payload = None
        refusal_payload = payload
    else:
        return missing_practice_evidence(
            turn_id,
            "practice evidence payload has unsupported shape",
        )

    sealed_trace = _sealed_trace_view(sealed_payload) if sealed_payload is not None else None
    trace_refusal = _trace_refusal_view(refusal_payload) if refusal_payload is not None else None
    if sealed_trace is not None and trace_refusal is not None:
        return missing_practice_evidence(
            turn_id,
            "practice evidence payload cannot contain both sealed trace and trace refusal",
        )
    if sealed_trace is None and trace_refusal is None:
        return missing_practice_evidence(
            turn_id,
            "recorded practice evidence missing sealed trace/refusal payload",
        )

    return _recorded_practice_evidence(
        turn_id=turn_id,
        sealed_trace=sealed_trace,
        trace_refusal=trace_refusal,
    )


def _recorded_practice_evidence(
    *,
    turn_id: int,
    sealed_trace: SealedPracticeTraceView | None,
    trace_refusal: PracticeTraceRefusalView | None,
) -> PracticeEvidence:
    if sealed_trace is not None:
        return PracticeEvidence(
            schema_version="practice_evidence_v1",
            turn_id=turn_id,
            status="recorded",
            missing_reason=None,
            record_kind="sealed_trace",
            practice_disposition=sealed_trace.practice_disposition,
            chain=_sealed_trace_chain(sealed_trace),
            sealed_trace=sealed_trace,
            trace_refusal=None,
            diagnostic_only=True,
            serving_allowed=False,
            mutation_allowed=False,
            replay_execution_allowed=False,
            replay_executed_by_workbench=False,
        )
    assert trace_refusal is not None
    return PracticeEvidence(
        schema_version="practice_evidence_v1",
        turn_id=turn_id,
        status="recorded",
        missing_reason=None,
        record_kind="trace_refusal",
        practice_disposition=trace_refusal.practice_disposition,
        chain=_trace_refusal_chain(trace_refusal),
        sealed_trace=None,
        trace_refusal=trace_refusal,
        diagnostic_only=True,
        serving_allowed=False,
        mutation_allowed=False,
        replay_execution_allowed=False,
        replay_executed_by_workbench=False,
    )


def _sealed_trace_view(payload: Any) -> SealedPracticeTraceView:
    return SealedPracticeTraceView(
        trace_id=str(_required(payload, "trace_id")),
        trace_policy_version=str(_required(payload, "trace_policy_version")),
        input_digest=str(_required(payload, "input_digest")),
        problem_frame_digest=str(_required(payload, "problem_frame_digest")),
        original_contract_assessment_id=str(
            _required(payload, "original_contract_assessment_id")
        ),
        residual_ids=_str_list(_field(payload, "residual_ids", [])),
        search_gate_decision_id=str(_required(payload, "search_gate_decision_id")),
        compute_budget_id=str(_required(payload, "compute_budget_id")),
        geometric_search_run_id=str(_required(payload, "geometric_search_run_id")),
        candidate_attempt_ids=_str_list(_field(payload, "candidate_attempt_ids", [])),
        candidate_attempt_binding_ids=_str_list(
            _field(payload, "candidate_attempt_binding_ids", [])
        ),
        replay_result_ids=_str_list(_field(payload, "replay_result_ids", [])),
        replay_refusal_ids=_str_list(_field(payload, "replay_refusal_ids", [])),
        upstream_identity_chain=_str_list(_field(payload, "upstream_identity_chain", [])),
        practice_disposition=str(_enum_value(_required(payload, "practice_disposition"))),
        trace_records=_str_list(_field(payload, "trace_records", [])),
        evidence_spans=[_span_view(span) for span in _as_list(_field(payload, "evidence_spans", []))],
        created_by_policy=str(_field(payload, "created_by_policy", "")),
        explanation=str(_field(payload, "explanation", "")),
    )


def _trace_refusal_view(payload: Any) -> PracticeTraceRefusalView:
    input_digest = _field(payload, "input_digest")
    return PracticeTraceRefusalView(
        trace_refusal_id=str(_required(payload, "trace_refusal_id")),
        trace_policy_version=str(_required(payload, "trace_policy_version")),
        input_digest=None if input_digest is None else str(input_digest),
        practice_disposition=str(_enum_value(_required(payload, "practice_disposition"))),
        reason_codes=_str_list(_field(payload, "reason_codes", [])),
        explanation=str(_field(payload, "explanation", "")),
    )


def _sealed_trace_chain(trace: SealedPracticeTraceView) -> list[PracticeEvidenceCard]:
    return [
        PracticeEvidenceCard(
            kind="problem_frame",
            status="recorded",
            refs=[trace.problem_frame_digest],
            summary="Problem frame digest bound into the sealed practice trace.",
        ),
        PracticeEvidenceCard(
            kind="contract_assessment",
            status="recorded",
            refs=[trace.original_contract_assessment_id],
            summary="Original contract assessment identity recorded before practice.",
        ),
        PracticeEvidenceCard(
            kind="residuals",
            status="recorded" if trace.residual_ids else "missing_evidence",
            refs=trace.residual_ids,
            summary="Residual identities admitted as the practice target.",
        ),
        PracticeEvidenceCard(
            kind="search_gate",
            status="recorded",
            refs=[trace.search_gate_decision_id],
            summary="Search gate decision identity; Workbench does not rerun the gate.",
        ),
        PracticeEvidenceCard(
            kind="compute_budget",
            status="recorded",
            refs=[trace.compute_budget_id],
            summary="Compute budget decision identity; Workbench does not allocate budget.",
        ),
        PracticeEvidenceCard(
            kind="geometric_search_run",
            status="recorded",
            refs=[trace.geometric_search_run_id],
            summary="Geometric search run identity; Workbench does not execute search.",
        ),
        PracticeEvidenceCard(
            kind="candidate_attempts",
            status="recorded" if trace.candidate_attempt_ids else "missing_evidence",
            refs=trace.candidate_attempt_ids,
            summary="Candidate attempt identities recorded upstream.",
        ),
        PracticeEvidenceCard(
            kind="attempt_bindings",
            status="recorded" if trace.candidate_attempt_binding_ids else "missing_evidence",
            refs=trace.candidate_attempt_binding_ids,
            summary="Candidate attempt/run binding identities recorded upstream.",
        ),
        PracticeEvidenceCard(
            kind="replay_results",
            status="recorded" if trace.replay_result_ids else "missing_evidence",
            refs=trace.replay_result_ids,
            summary="Replay adapter result identities; Workbench does not run replay here.",
        ),
        PracticeEvidenceCard(
            kind="replay_refusals",
            status="recorded" if trace.replay_refusal_ids else "missing_evidence",
            refs=trace.replay_refusal_ids,
            summary="Replay adapter refusal identities; Workbench does not retry replay here.",
        ),
        PracticeEvidenceCard(
            kind="sealed_trace",
            status="recorded",
            refs=[trace.trace_id],
            summary="Sealed practice trace identity and disposition.",
        ),
    ]


def _trace_refusal_chain(refusal: PracticeTraceRefusalView) -> list[PracticeEvidenceCard]:
    refs = [refusal.trace_refusal_id]
    return [
        PracticeEvidenceCard(
            kind="trace_refusal",
            status="recorded",
            refs=refs,
            summary="Practice trace refused before a sealed practice trace could be projected.",
        )
    ]


def _span_view(payload: Any) -> PracticeSourceSpanView:
    sentence_index = _field(payload, "sentence_index")
    return PracticeSourceSpanView(
        text=str(_required(payload, "text")),
        start=int(_required(payload, "start")),
        end=int(_required(payload, "end")),
        sentence_index=None if sentence_index is None else int(sentence_index),
    )


def _field(payload: Any, name: str, default: Any = None) -> Any:
    if isinstance(payload, dict):
        return payload.get(name, default)
    return getattr(payload, name, default)


def _required(payload: Any, name: str) -> Any:
    value = _field(payload, name)
    if value is None:
        raise KeyError(name)
    return value


def _enum_value(value: Any) -> Any:
    return getattr(value, "value", value)


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return []


def _str_list(value: Any) -> list[str]:
    return [str(_enum_value(item)) for item in _as_list(value)]
