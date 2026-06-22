"""Inert, diagnostic-only envelope over an existing compute budget."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum, unique

from generate.compute_budget import ComputeBudgetDecision, ComputeBudgetStatus
from generate.kernel_facts import SourceSpan
from generate.search_gate import SearchGateDecision, SearchGateStatus

GEOMETRIC_SEARCH_RUN_POLICY_VERSION = "geometric_search_run.v1"
GEOMETRIC_SEARCH_RUN_SCHEMA_VERSION = "geometric_search_run.schema.v1"

_SEARCH_GATE_POLICY_VERSION = "search_gate.v1"
_COMPUTE_BUDGET_POLICY_VERSION = "compute_budget.v1"


@unique
class SearchRunDisposition(str, Enum):
    NOT_STARTED = "not_started"
    BLOCKED_BY_BUDGET = "blocked_by_budget"
    BLOCKED_BY_GATE = "blocked_by_gate"
    INVALID_INPUT = "invalid_input"
    EXHAUSTED_NO_CANDIDATE = "exhausted_no_candidate"
    CANDIDATE_REPLAY_PENDING = "candidate_replay_pending"
    CANDIDATE_REPLAY_CLOSED = "candidate_replay_closed"
    CANDIDATE_REPLAY_REFUSED = "candidate_replay_refused"


@unique
class RunExhaustionCode(str, Enum):
    OPERATOR_SET_EMPTY = "operator_set_empty"
    OPERATOR_SPACE_DEPLETED = "operator_space_depleted"
    MAX_CANDIDATES_REACHED = "max_candidates_reached"
    MAX_DEPTH_REACHED = "max_depth_reached"
    MAX_STEPS_REACHED = "max_steps_reached"


@unique
class CandidateReplayStatus(str, Enum):
    REPLAY_PENDING = "replay_pending"
    REPLAY_CLOSED = "replay_closed"
    REPLAY_REFUSED = "replay_refused"


@dataclass(frozen=True, slots=True)
class BudgetCharge:
    candidates: int
    steps: int


@dataclass(frozen=True, slots=True)
class BudgetConsumed:
    candidates_considered: int
    max_candidates: int
    depth_reached: int
    max_depth: int
    steps_used: int
    max_steps: int
    parallelism_used: int
    max_parallelism: int
    exhausted: bool


@dataclass(frozen=True, slots=True)
class CandidateAttempt:
    attempt_id: str
    attempt_index: int
    parent_attempt_id: str | None
    operator_id: str
    operator_version: str
    input_digest: str
    candidate_digest: str
    budget_charge: BudgetCharge
    depth: int
    step_index: int
    replay_status: CandidateReplayStatus
    replay_blockers: tuple[str, ...]
    evidence_spans: tuple[SourceSpan, ...]
    explanation: str


@dataclass(frozen=True, slots=True)
class SearchRunRefusal:
    outcome_id: str
    run_policy_version: str
    input_digest: str | None
    gate_decision_id: str | None
    budget_id: str | None
    run_disposition: SearchRunDisposition
    reason_codes: tuple[str, ...]
    explanation: str


@dataclass(frozen=True, slots=True)
class GeometricSearchRun:
    run_id: str
    run_policy_version: str
    schema_version: str
    problem_frame_digest: str
    contract_assessment_id: str
    residual_ids: tuple[str, ...]
    gate_decision_id: str
    budget_id: str
    operator_set_id: str
    operator_set_version: str
    input_digest: str
    candidate_attempts: tuple[CandidateAttempt, ...]
    budget_consumed: BudgetConsumed
    run_disposition: SearchRunDisposition
    exhaustion_code: RunExhaustionCode | None
    explanation: str


SearchRunOutcome = SearchRunRefusal | GeometricSearchRun
RunDisposition = SearchRunDisposition
ReplayStatus = CandidateReplayStatus


def _canonical_digest(payload: dict[str, object]) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _safe_getattr(value: object, name: str) -> object:
    try:
        return getattr(value, name, None)
    except Exception:
        return None


def _nonempty_text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _sha256_text(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and value == value.lower()
        and all(character in "0123456789abcdef" for character in value)
    )


def _text_or_none(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


def _valid_residual_ids(value: object) -> bool:
    return (
        isinstance(value, tuple)
        and all(_nonempty_text(residual_id) for residual_id in value)
    )


def _valid_span(span: object) -> bool:
    return (
        isinstance(span, SourceSpan)
        and isinstance(span.text, str)
        and type(span.start) is int
        and type(span.end) is int
        and span.start >= 0
        and span.end >= span.start
        and (
            span.sentence_index is None
            or type(span.sentence_index) is int
        )
    )


def _valid_spans(value: object) -> bool:
    return isinstance(value, tuple) and all(_valid_span(span) for span in value)


def _span_payload(span: SourceSpan) -> dict[str, object]:
    return {
        "text": span.text,
        "start": span.start,
        "end": span.end,
        "sentence_index": span.sentence_index,
    }


def _gate_id(gate_decision: SearchGateDecision) -> str:
    return _canonical_digest(
        {
            "policy_version": gate_decision.policy_version,
            "input_digest": gate_decision.input_digest,
            "residual_ids": list(gate_decision.residual_ids),
            "candidate_organ": gate_decision.candidate_organ,
            "status": gate_decision.status.value,
            "reason_code": gate_decision.reason_code,
            "evidence_spans": [
                _span_payload(span) for span in gate_decision.evidence_spans
            ],
        }
    )


def _budget_id(compute_budget: ComputeBudgetDecision) -> str:
    return _canonical_digest(
        {
            "policy_version": compute_budget.policy_version,
            "gate_decision_id": compute_budget.gate_decision_id,
            "gate_policy_version": compute_budget.gate_policy_version,
            "gate_input_digest": compute_budget.gate_input_digest,
            "status": compute_budget.status.value,
            "reason_code": compute_budget.reason_code,
            "max_candidates": compute_budget.max_candidates,
            "max_depth": compute_budget.max_depth,
            "max_steps": compute_budget.max_steps,
            "max_parallelism": compute_budget.max_parallelism,
            "evidence_spans": [
                _span_payload(span) for span in compute_budget.evidence_spans
            ],
        }
    )


def _input_payload(
    *,
    run_policy_version: str,
    schema_version: str,
    problem_frame_digest: str,
    contract_assessment_id: str,
    residual_ids: tuple[str, ...],
    gate_decision_id: str,
    gate_policy_version: str,
    gate_input_digest: str,
    budget_id: str,
    budget_policy_version: str,
    operator_set_id: str,
    operator_set_version: str,
) -> dict[str, object]:
    return {
        "problem_frame_digest": problem_frame_digest,
        "contract_assessment_id": contract_assessment_id,
        "residual_ids": list(residual_ids),
        "gate_decision_id": gate_decision_id,
        "gate_policy_version": gate_policy_version,
        "gate_input_digest": gate_input_digest,
        "budget_id": budget_id,
        "budget_policy_version": budget_policy_version,
        "operator_set_id": operator_set_id,
        "operator_set_version": operator_set_version,
        "run_policy_version": run_policy_version,
        "schema_version": schema_version,
    }


def _candidate_attempt_payload(attempt: CandidateAttempt) -> dict[str, object]:
    return {
        "attempt_id": attempt.attempt_id,
        "attempt_index": attempt.attempt_index,
        "parent_attempt_id": attempt.parent_attempt_id,
        "operator_id": attempt.operator_id,
        "operator_version": attempt.operator_version,
        "input_digest": attempt.input_digest,
        "candidate_digest": attempt.candidate_digest,
        "budget_charge": {
            "candidates": attempt.budget_charge.candidates,
            "steps": attempt.budget_charge.steps,
        },
        "depth": attempt.depth,
        "step_index": attempt.step_index,
        "replay_status": attempt.replay_status.value,
        "replay_blockers": list(attempt.replay_blockers),
        "evidence_spans": [
            _span_payload(span) for span in attempt.evidence_spans
        ],
    }


def _budget_consumed_payload(consumed: BudgetConsumed) -> dict[str, object]:
    return {
        "candidates_considered": consumed.candidates_considered,
        "max_candidates": consumed.max_candidates,
        "depth_reached": consumed.depth_reached,
        "max_depth": consumed.max_depth,
        "steps_used": consumed.steps_used,
        "max_steps": consumed.max_steps,
        "parallelism_used": consumed.parallelism_used,
        "max_parallelism": consumed.max_parallelism,
        "exhausted": consumed.exhausted,
    }


def _refusal(
    *,
    run_policy_version: object,
    input_digest: str | None,
    gate_decision_id: object,
    budget_id: object,
    disposition: SearchRunDisposition,
    reason_codes: tuple[str, ...],
) -> SearchRunRefusal:
    safe_policy_version = (
        run_policy_version if isinstance(run_policy_version, str) else ""
    )
    safe_gate_id = _text_or_none(gate_decision_id)
    safe_budget_id = _text_or_none(budget_id)
    outcome_id = _canonical_digest(
        {
            "outcome_id": "",
            "run_policy_version": safe_policy_version,
            "input_digest": input_digest,
            "gate_decision_id": safe_gate_id,
            "budget_id": safe_budget_id,
            "run_disposition": disposition.value,
            "reason_codes": list(reason_codes),
        }
    )
    return SearchRunRefusal(
        outcome_id=outcome_id,
        run_policy_version=safe_policy_version,
        input_digest=input_digest,
        gate_decision_id=safe_gate_id,
        budget_id=safe_budget_id,
        run_disposition=disposition,
        reason_codes=reason_codes,
        explanation="Geometric search run initialization refused: "
        + ", ".join(reason_codes)
        + ".",
    )


def initialize_geometric_search_run(
    *,
    problem_frame_digest: str,
    contract_assessment_id: str,
    residual_ids: tuple[str, ...],
    gate_decision: SearchGateDecision,
    compute_budget: ComputeBudgetDecision,
    operator_set_id: str,
    operator_set_version: str,
    run_policy_version: str = GEOMETRIC_SEARCH_RUN_POLICY_VERSION,
    schema_version: str = GEOMETRIC_SEARCH_RUN_SCHEMA_VERSION,
) -> SearchRunOutcome:
    """Validate existing gate/budget evidence and initialize no search work."""

    gate_id = _safe_getattr(gate_decision, "decision_id")
    gate_policy = _safe_getattr(gate_decision, "policy_version")
    gate_digest = _safe_getattr(gate_decision, "input_digest")
    gate_residual_ids = _safe_getattr(gate_decision, "residual_ids")
    gate_status = _safe_getattr(gate_decision, "status")
    gate_candidate_organ = _safe_getattr(gate_decision, "candidate_organ")
    gate_reason_code = _safe_getattr(gate_decision, "reason_code")
    gate_spans = _safe_getattr(gate_decision, "evidence_spans")

    budget_id = _safe_getattr(compute_budget, "budget_id")
    budget_policy = _safe_getattr(compute_budget, "policy_version")
    budget_gate_id = _safe_getattr(compute_budget, "gate_decision_id")
    budget_gate_policy = _safe_getattr(compute_budget, "gate_policy_version")
    budget_gate_digest = _safe_getattr(compute_budget, "gate_input_digest")
    budget_status = _safe_getattr(compute_budget, "status")
    budget_reason_code = _safe_getattr(compute_budget, "reason_code")
    max_candidates = _safe_getattr(compute_budget, "max_candidates")
    max_depth = _safe_getattr(compute_budget, "max_depth")
    max_steps = _safe_getattr(compute_budget, "max_steps")
    max_parallelism = _safe_getattr(compute_budget, "max_parallelism")
    budget_spans = _safe_getattr(compute_budget, "evidence_spans")

    reasons: list[str] = []
    if run_policy_version != GEOMETRIC_SEARCH_RUN_POLICY_VERSION:
        reasons.append("unsupported_run_policy_version")
    if schema_version != GEOMETRIC_SEARCH_RUN_SCHEMA_VERSION:
        reasons.append("unsupported_schema_version")
    if not _sha256_text(problem_frame_digest):
        reasons.append("invalid_problem_frame_digest")
    if not _nonempty_text(contract_assessment_id):
        reasons.append("missing_contract_assessment_id")
    if not _valid_residual_ids(residual_ids):
        reasons.append("invalid_residual_ids")
    if not _nonempty_text(operator_set_id):
        reasons.append("missing_operator_set_id")
    if not _nonempty_text(operator_set_version):
        reasons.append("missing_operator_set_version")

    if gate_policy != _SEARCH_GATE_POLICY_VERSION:
        reasons.append("unsupported_gate_policy_version")
    if not _sha256_text(gate_id):
        reasons.append("invalid_gate_decision_id")
    if not _sha256_text(gate_digest):
        reasons.append("invalid_gate_input_digest")
    if not _valid_residual_ids(gate_residual_ids):
        reasons.append("invalid_gate_residual_ids")
    if not any(gate_status is status for status in SearchGateStatus):
        reasons.append("invalid_gate_status")
    if not (
        gate_candidate_organ is None or isinstance(gate_candidate_organ, str)
    ):
        reasons.append("invalid_gate_candidate_organ")
    if not _nonempty_text(gate_reason_code):
        reasons.append("invalid_gate_reason_code")
    if not _valid_spans(gate_spans):
        reasons.append("invalid_gate_evidence_spans")

    if budget_policy != _COMPUTE_BUDGET_POLICY_VERSION:
        reasons.append("unsupported_budget_policy_version")
    if not _sha256_text(budget_id):
        reasons.append("invalid_budget_id")
    if not _nonempty_text(budget_gate_id):
        reasons.append("invalid_budget_gate_decision_id")
    if not _nonempty_text(budget_gate_policy):
        reasons.append("invalid_budget_gate_policy_version")
    if not _sha256_text(budget_gate_digest):
        reasons.append("invalid_budget_gate_input_digest")
    if not any(budget_status is status for status in ComputeBudgetStatus):
        reasons.append("invalid_budget_status")
    if not _nonempty_text(budget_reason_code):
        reasons.append("invalid_budget_reason_code")
    if not _valid_spans(budget_spans):
        reasons.append("invalid_budget_evidence_spans")

    structural_limits = (
        ("max_candidates", max_candidates),
        ("max_depth", max_depth),
        ("max_steps", max_steps),
        ("max_parallelism", max_parallelism),
    )
    for name, value in structural_limits:
        if type(value) is not int or value < 0:
            reasons.append(f"invalid_{name}")

    if not reasons:
        typed_gate = gate_decision
        typed_budget = compute_budget
        if typed_gate.decision_id != _gate_id(typed_gate):
            reasons.append("gate_decision_id_mismatch")
        if typed_budget.budget_id != _budget_id(typed_budget):
            reasons.append("budget_id_mismatch")
        if residual_ids != typed_gate.residual_ids:
            reasons.append("residual_ids_mismatch")
        if typed_budget.gate_decision_id != typed_gate.decision_id:
            reasons.append("gate_decision_id_budget_mismatch")
        if typed_budget.gate_policy_version != typed_gate.policy_version:
            reasons.append("gate_policy_version_budget_mismatch")
        if typed_budget.gate_input_digest != typed_gate.input_digest:
            reasons.append("gate_input_digest_budget_mismatch")

    input_digest: str | None = None
    if (
        isinstance(run_policy_version, str)
        and isinstance(schema_version, str)
        and isinstance(problem_frame_digest, str)
        and isinstance(contract_assessment_id, str)
        and _valid_residual_ids(residual_ids)
        and isinstance(gate_id, str)
        and isinstance(gate_policy, str)
        and isinstance(gate_digest, str)
        and isinstance(budget_id, str)
        and isinstance(budget_policy, str)
        and isinstance(operator_set_id, str)
        and isinstance(operator_set_version, str)
    ):
        input_digest = _canonical_digest(
            _input_payload(
                run_policy_version=run_policy_version,
                schema_version=schema_version,
                problem_frame_digest=problem_frame_digest,
                contract_assessment_id=contract_assessment_id,
                residual_ids=residual_ids,
                gate_decision_id=gate_id,
                gate_policy_version=gate_policy,
                gate_input_digest=gate_digest,
                budget_id=budget_id,
                budget_policy_version=budget_policy,
                operator_set_id=operator_set_id,
                operator_set_version=operator_set_version,
            )
        )

    if reasons:
        return _refusal(
            run_policy_version=run_policy_version,
            input_digest=input_digest,
            gate_decision_id=gate_id,
            budget_id=budget_id,
            disposition=SearchRunDisposition.INVALID_INPUT,
            reason_codes=tuple(reasons),
        )

    if gate_status is not SearchGateStatus.ELIGIBLE:
        return _refusal(
            run_policy_version=run_policy_version,
            input_digest=input_digest,
            gate_decision_id=gate_id,
            budget_id=budget_id,
            disposition=SearchRunDisposition.BLOCKED_BY_GATE,
            reason_codes=("gate_not_eligible",),
        )

    if budget_status is not ComputeBudgetStatus.BUDGET_ALLOWED:
        return _refusal(
            run_policy_version=run_policy_version,
            input_digest=input_digest,
            gate_decision_id=gate_id,
            budget_id=budget_id,
            disposition=SearchRunDisposition.BLOCKED_BY_BUDGET,
            reason_codes=("budget_not_allowed",),
        )

    allowed_budget_reasons: list[str] = []
    if max_candidates == 0:
        allowed_budget_reasons.append("zero_max_candidates")
    if max_steps == 0:
        allowed_budget_reasons.append("zero_max_steps")
    if max_parallelism != 1:
        allowed_budget_reasons.append("unsupported_max_parallelism")
    if allowed_budget_reasons:
        return _refusal(
            run_policy_version=run_policy_version,
            input_digest=input_digest,
            gate_decision_id=gate_id,
            budget_id=budget_id,
            disposition=SearchRunDisposition.INVALID_INPUT,
            reason_codes=tuple(allowed_budget_reasons),
        )

    assert input_digest is not None
    assert isinstance(gate_id, str)
    assert isinstance(budget_id, str)
    assert isinstance(max_candidates, int)
    assert isinstance(max_depth, int)
    assert isinstance(max_steps, int)
    assert isinstance(max_parallelism, int)

    consumed = BudgetConsumed(
        candidates_considered=0,
        max_candidates=max_candidates,
        depth_reached=0,
        max_depth=max_depth,
        steps_used=0,
        max_steps=max_steps,
        parallelism_used=0,
        max_parallelism=max_parallelism,
        exhausted=False,
    )
    disposition = SearchRunDisposition.EXHAUSTED_NO_CANDIDATE
    exhaustion_code = RunExhaustionCode.OPERATOR_SET_EMPTY
    attempts: tuple[CandidateAttempt, ...] = ()
    run_payload = {
        "run_id": "",
        "run_policy_version": run_policy_version,
        "schema_version": schema_version,
        "problem_frame_digest": problem_frame_digest,
        "contract_assessment_id": contract_assessment_id,
        "residual_ids": list(residual_ids),
        "gate_decision_id": gate_id,
        "budget_id": budget_id,
        "operator_set_id": operator_set_id,
        "operator_set_version": operator_set_version,
        "input_digest": input_digest,
        "candidate_attempts": [
            _candidate_attempt_payload(attempt) for attempt in attempts
        ],
        "budget_consumed": _budget_consumed_payload(consumed),
        "run_disposition": disposition.value,
        "exhaustion_code": exhaustion_code.value,
    }
    return GeometricSearchRun(
        run_id=_canonical_digest(run_payload),
        run_policy_version=run_policy_version,
        schema_version=schema_version,
        problem_frame_digest=problem_frame_digest,
        contract_assessment_id=contract_assessment_id,
        residual_ids=residual_ids,
        gate_decision_id=gate_id,
        budget_id=budget_id,
        operator_set_id=operator_set_id,
        operator_set_version=operator_set_version,
        input_digest=input_digest,
        candidate_attempts=attempts,
        budget_consumed=consumed,
        run_disposition=disposition,
        exhaustion_code=exhaustion_code,
        explanation="The explicit v1 operator set is empty; no candidate was produced.",
    )


__all__ = [
    "GEOMETRIC_SEARCH_RUN_POLICY_VERSION",
    "GEOMETRIC_SEARCH_RUN_SCHEMA_VERSION",
    "SearchRunDisposition",
    "RunDisposition",
    "RunExhaustionCode",
    "CandidateReplayStatus",
    "ReplayStatus",
    "BudgetCharge",
    "BudgetConsumed",
    "CandidateAttempt",
    "SearchRunRefusal",
    "GeometricSearchRun",
    "SearchRunOutcome",
    "initialize_geometric_search_run",
]
