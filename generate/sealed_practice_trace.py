"""Inert, diagnostic-only sealed practice trace shell over upstream loop records."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum, unique

from generate.geometric_search_run import (
    GeometricSearchRun,
    SearchRunDisposition,
    SearchRunRefusal,
)
from generate.kernel_facts import SourceSpan
from generate.replay_adapter import ReplayAdapterRefusal, ReplayAdapterResult, ReplayDisposition

SEALED_PRACTICE_TRACE_POLICY_VERSION = "sealed_practice_trace.v1"
CREATED_BY_POLICY = SEALED_PRACTICE_TRACE_POLICY_VERSION


@unique
class PracticeDisposition(str, Enum):
    SEALED_ORIGINAL_REFUSAL = "sealed_original_refusal"
    SEALED_EXHAUSTED_NO_CANDIDATE = "sealed_exhausted_no_candidate"
    SEALED_ALL_CANDIDATES_REFUSED = "sealed_all_candidates_refused"
    SEALED_REPLAY_UNAVAILABLE = "sealed_replay_unavailable"
    SEALED_CONTRACT_CLOSED_PROOF_REFUSED = "sealed_contract_closed_proof_refused"
    SEALED_CANDIDATE_REPLAY_CLOSED = "sealed_candidate_replay_closed"
    TRACE_INVALID_INPUT = "trace_invalid_input"
    TRACE_IDENTITY_MISMATCH = "trace_identity_mismatch"
    TRACE_POLICY_UNSUPPORTED = "trace_policy_unsupported"
    TRACE_UPSTREAM_INCOMPLETE = "trace_upstream_incomplete"


_SEALED_DISPOSITIONS = frozenset(
    {
        PracticeDisposition.SEALED_ORIGINAL_REFUSAL,
        PracticeDisposition.SEALED_EXHAUSTED_NO_CANDIDATE,
        PracticeDisposition.SEALED_ALL_CANDIDATES_REFUSED,
        PracticeDisposition.SEALED_REPLAY_UNAVAILABLE,
        PracticeDisposition.SEALED_CONTRACT_CLOSED_PROOF_REFUSED,
        PracticeDisposition.SEALED_CANDIDATE_REPLAY_CLOSED,
    }
)

_ORIGINAL_REFUSAL_RUN_DISPOSITIONS = frozenset(
    {
        SearchRunDisposition.BLOCKED_BY_GATE,
        SearchRunDisposition.BLOCKED_BY_BUDGET,
        SearchRunDisposition.NOT_STARTED,
        SearchRunDisposition.INVALID_INPUT,
    }
)


@dataclass(frozen=True, slots=True)
class PracticeTraceInput:
    input_digest: str
    trace_policy_version: str
    problem_frame_digest: str
    original_contract_assessment_id: str
    residual_ids: tuple[str, ...]
    search_gate_decision_id: str
    compute_budget_id: str
    geometric_search_run_id: str
    candidate_attempt_ids: tuple[str, ...]
    candidate_attempt_binding_ids: tuple[str, ...]
    replay_result_ids: tuple[str, ...]
    replay_refusal_ids: tuple[str, ...]
    schema_versions: tuple[tuple[str, str], ...]
    policy_versions: tuple[tuple[str, str], ...]


@dataclass(frozen=True, slots=True)
class SealedPracticeTrace:
    trace_id: str
    trace_policy_version: str
    input_digest: str
    problem_frame_digest: str
    original_contract_assessment_id: str
    residual_ids: tuple[str, ...]
    search_gate_decision_id: str
    compute_budget_id: str
    geometric_search_run_id: str
    candidate_attempt_ids: tuple[str, ...]
    candidate_attempt_binding_ids: tuple[str, ...]
    replay_result_ids: tuple[str, ...]
    replay_refusal_ids: tuple[str, ...]
    upstream_identity_chain: tuple[str, ...]
    practice_disposition: PracticeDisposition
    trace_records: tuple[str, ...]
    evidence_spans: tuple[SourceSpan, ...]
    created_by_policy: str
    explanation: str


@dataclass(frozen=True, slots=True)
class PracticeTraceRefusal:
    trace_refusal_id: str
    trace_policy_version: str
    input_digest: str | None
    practice_disposition: PracticeDisposition
    reason_codes: tuple[str, ...]
    explanation: str


PracticeTraceOutcome = SealedPracticeTrace | PracticeTraceRefusal


def _canonical_digest(payload: dict[str, object]) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _nonempty_text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _sha256_text(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and value == value.lower()
        and all(character in "0123456789abcdef" for character in value)
    )


def _valid_span(span: object) -> bool:
    return (
        isinstance(span, SourceSpan)
        and isinstance(span.text, str)
        and type(span.start) is int
        and type(span.end) is int
        and span.start >= 0
        and span.end >= span.start
        and (span.sentence_index is None or type(span.sentence_index) is int)
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


def _version_pairs_payload(
    versions: tuple[tuple[str, str], ...],
) -> list[list[str]]:
    return [[name, version] for name, version in versions]


def _valid_version_pairs(value: object) -> bool:
    if not isinstance(value, tuple):
        return False
    names: list[str] = []
    for entry in value:
        if not isinstance(entry, tuple) or len(entry) != 2:
            return False
        name, version = entry
        if not _nonempty_text(name) or not _nonempty_text(version):
            return False
        names.append(name)
    return len(names) == len(set(names)) and names == sorted(names)


def _input_digest_payload(
    *,
    trace_policy_version: str,
    problem_frame_digest: str,
    original_contract_assessment_id: str,
    residual_ids: tuple[str, ...],
    search_gate_decision_id: str,
    compute_budget_id: str,
    geometric_search_run_id: str,
    candidate_attempt_ids: tuple[str, ...],
    candidate_attempt_binding_ids: tuple[str, ...],
    replay_result_ids: tuple[str, ...],
    replay_refusal_ids: tuple[str, ...],
    schema_versions: tuple[tuple[str, str], ...],
    policy_versions: tuple[tuple[str, str], ...],
) -> dict[str, object]:
    return {
        "trace_policy_version": trace_policy_version,
        "problem_frame_digest": problem_frame_digest,
        "original_contract_assessment_id": original_contract_assessment_id,
        "residual_ids": list(residual_ids),
        "search_gate_decision_id": search_gate_decision_id,
        "compute_budget_id": compute_budget_id,
        "geometric_search_run_id": geometric_search_run_id,
        "candidate_attempt_ids": list(candidate_attempt_ids),
        "candidate_attempt_binding_ids": list(candidate_attempt_binding_ids),
        "replay_result_ids": list(replay_result_ids),
        "replay_refusal_ids": list(replay_refusal_ids),
        "schema_versions": _version_pairs_payload(schema_versions),
        "policy_versions": _version_pairs_payload(policy_versions),
    }


def _trace_id_payload(
    *,
    trace_policy_version: str,
    input_digest: str,
    problem_frame_digest: str,
    original_contract_assessment_id: str,
    residual_ids: tuple[str, ...],
    search_gate_decision_id: str,
    compute_budget_id: str,
    geometric_search_run_id: str,
    candidate_attempt_ids: tuple[str, ...],
    candidate_attempt_binding_ids: tuple[str, ...],
    replay_result_ids: tuple[str, ...],
    replay_refusal_ids: tuple[str, ...],
    upstream_identity_chain: tuple[str, ...],
    practice_disposition: PracticeDisposition,
    trace_records: tuple[str, ...],
    evidence_spans: tuple[SourceSpan, ...],
    created_by_policy: str,
) -> dict[str, object]:
    return {
        "trace_id": "",
        "trace_policy_version": trace_policy_version,
        "input_digest": input_digest,
        "problem_frame_digest": problem_frame_digest,
        "original_contract_assessment_id": original_contract_assessment_id,
        "residual_ids": list(residual_ids),
        "search_gate_decision_id": search_gate_decision_id,
        "compute_budget_id": compute_budget_id,
        "geometric_search_run_id": geometric_search_run_id,
        "candidate_attempt_ids": list(candidate_attempt_ids),
        "candidate_attempt_binding_ids": list(candidate_attempt_binding_ids),
        "replay_result_ids": list(replay_result_ids),
        "replay_refusal_ids": list(replay_refusal_ids),
        "upstream_identity_chain": list(upstream_identity_chain),
        "practice_disposition": practice_disposition.value,
        "trace_records": list(trace_records),
        "evidence_spans": [_span_payload(span) for span in evidence_spans],
        "created_by_policy": created_by_policy,
    }


def _refusal(
    *,
    trace_policy_version: str = SEALED_PRACTICE_TRACE_POLICY_VERSION,
    input_digest: str | None,
    disposition: PracticeDisposition,
    reason_codes: tuple[str, ...],
) -> PracticeTraceRefusal:
    trace_refusal_id = _canonical_digest(
        {
            "trace_refusal_id": "",
            "trace_policy_version": trace_policy_version,
            "input_digest": input_digest,
            "practice_disposition": disposition.value,
            "reason_codes": list(reason_codes),
        }
    )
    return PracticeTraceRefusal(
        trace_refusal_id=trace_refusal_id,
        trace_policy_version=trace_policy_version,
        input_digest=input_digest,
        practice_disposition=disposition,
        reason_codes=reason_codes,
        explanation="Practice trace refused: "
        + disposition.value
        + " ("
        + ", ".join(reason_codes)
        + ").",
    )


def _run_identity(run: GeometricSearchRun | SearchRunRefusal) -> str:
    if isinstance(run, GeometricSearchRun):
        return run.run_id
    if isinstance(run, SearchRunRefusal):
        return run.outcome_id
    return ""


def _validate_run_bindings(
    *,
    run: GeometricSearchRun | SearchRunRefusal,
    problem_frame_digest: str,
    original_contract_assessment_id: str,
    residual_ids: tuple[str, ...],
    search_gate_decision_id: str,
    compute_budget_id: str,
) -> list[str]:
    reasons: list[str] = []
    if isinstance(run, GeometricSearchRun):
        if run.problem_frame_digest != problem_frame_digest:
            reasons.append("problem_frame_digest_run_mismatch")
        if run.contract_assessment_id != original_contract_assessment_id:
            reasons.append("contract_assessment_id_run_mismatch")
        if run.residual_ids != residual_ids:
            reasons.append("residual_ids_run_mismatch")
        if run.gate_decision_id != search_gate_decision_id:
            reasons.append("gate_decision_id_run_mismatch")
        if run.budget_id != compute_budget_id:
            reasons.append("budget_id_run_mismatch")
    elif isinstance(run, SearchRunRefusal):
        if run.gate_decision_id != search_gate_decision_id:
            reasons.append("gate_decision_id_refusal_mismatch")
        if run.budget_id != compute_budget_id:
            reasons.append("budget_id_refusal_mismatch")
    else:
        reasons.append("invalid_run_type")
    return reasons


def _validate_replay_record_identity(
    record: ReplayAdapterResult | ReplayAdapterRefusal,
) -> str | None:
    if isinstance(record, ReplayAdapterResult):
        return None if _sha256_text(record.replay_result_id) else "invalid_replay_result_id"
    if isinstance(record, ReplayAdapterRefusal):
        return None if _sha256_text(record.replay_refusal_id) else "invalid_replay_refusal_id"
    return "invalid_replay_record_type"


def _validate_replay_bindings(
    *,
    run: GeometricSearchRun,
    replay_results: tuple[ReplayAdapterResult, ...],
    replay_refusals: tuple[ReplayAdapterRefusal, ...],
) -> list[str]:
    reasons: list[str] = []
    attempt_by_id = {attempt.attempt_id: attempt for attempt in run.candidate_attempts}
    attempt_ids = {attempt.attempt_id for attempt in run.candidate_attempts}
    digest_by_attempt = {
        attempt.attempt_id: attempt.candidate_digest for attempt in run.candidate_attempts
    }

    for record in (*replay_results, *replay_refusals):
        identity_reason = _validate_replay_record_identity(record)
        if identity_reason is not None:
            reasons.append(identity_reason)
        run_id = record.run_id
        attempt_id = record.attempt_id
        candidate_digest = record.candidate_digest
        if run_id != run.run_id:
            reasons.append("replay_run_id_mismatch")
        if attempt_id is None or not _nonempty_text(attempt_id):
            reasons.append("replay_missing_attempt_id")
        elif attempt_id not in attempt_ids:
            reasons.append("replay_orphan_attempt_id")
        if candidate_digest is not None and _nonempty_text(candidate_digest):
            if attempt_id in digest_by_attempt and candidate_digest != digest_by_attempt[attempt_id]:
                reasons.append("replay_candidate_digest_mismatch")
        elif attempt_id in attempt_by_id:
            reasons.append("replay_missing_candidate_digest")

    return reasons


def _derive_disposition(
    *,
    run: GeometricSearchRun | SearchRunRefusal,
    replay_results: tuple[ReplayAdapterResult, ...],
    replay_refusals: tuple[ReplayAdapterRefusal, ...],
) -> PracticeDisposition | None:
    if isinstance(run, SearchRunRefusal):
        if run.run_disposition in _ORIGINAL_REFUSAL_RUN_DISPOSITIONS:
            return PracticeDisposition.SEALED_ORIGINAL_REFUSAL
        return None

    if not run.candidate_attempts:
        if run.run_disposition is SearchRunDisposition.EXHAUSTED_NO_CANDIDATE:
            return PracticeDisposition.SEALED_EXHAUSTED_NO_CANDIDATE
        if run.run_disposition in _ORIGINAL_REFUSAL_RUN_DISPOSITIONS:
            return PracticeDisposition.SEALED_ORIGINAL_REFUSAL
        return None

    if not replay_results and not replay_refusals:
        return None

    if any(
        result.replay_disposition is ReplayDisposition.CONTRACT_AND_PROOF_CLOSED
        for result in replay_results
    ):
        return PracticeDisposition.SEALED_CANDIDATE_REPLAY_CLOSED

    if any(
        result.replay_disposition
        is ReplayDisposition.CONTRACT_CLOSED_BUT_PROOF_REFUSED
        for result in replay_results
    ):
        return PracticeDisposition.SEALED_CONTRACT_CLOSED_PROOF_REFUSED

    if replay_results and all(
        result.replay_disposition is ReplayDisposition.CONTRACT_REFUSED
        for result in replay_results
    ):
        return PracticeDisposition.SEALED_ALL_CANDIDATES_REFUSED

    if replay_refusals and not replay_results:
        return PracticeDisposition.SEALED_REPLAY_UNAVAILABLE

    return None


def _upstream_identity_chain(
    *,
    problem_frame_digest: str,
    original_contract_assessment_id: str,
    residual_ids: tuple[str, ...],
    search_gate_decision_id: str,
    compute_budget_id: str,
    geometric_search_run_id: str,
    candidate_attempt_ids: tuple[str, ...],
    candidate_attempt_binding_ids: tuple[str, ...],
    replay_result_ids: tuple[str, ...],
    replay_refusal_ids: tuple[str, ...],
) -> tuple[str, ...]:
    return (
        problem_frame_digest,
        original_contract_assessment_id,
        *residual_ids,
        search_gate_decision_id,
        compute_budget_id,
        geometric_search_run_id,
        *candidate_attempt_ids,
        *candidate_attempt_binding_ids,
        *replay_result_ids,
        *replay_refusal_ids,
    )


def _failure_disposition(reasons: list[str]) -> PracticeDisposition:
    identity_mismatch_codes = {
        "problem_frame_digest_run_mismatch",
        "contract_assessment_id_run_mismatch",
        "residual_ids_run_mismatch",
        "gate_decision_id_run_mismatch",
        "budget_id_run_mismatch",
        "gate_decision_id_refusal_mismatch",
        "budget_id_refusal_mismatch",
        "geometric_search_run_id_mismatch",
        "candidate_attempt_ids_mismatch",
        "candidate_attempt_binding_ids_mismatch",
        "invalid_binding_type",
        "invalid_candidate_operator_result_type",
        "binding_result_count_mismatch",
        "binding_run_mismatch",
        "binding_result_mismatch",
        "binding_attempt_mismatch",
        "binding_reconstruction_mismatch",
        "binding_not_structurally_bound",
        "binding_not_successful",
        "binding_evidence_mismatch",
        "operator_result_run_mismatch",
        "operator_reconstruction_run_mismatch",
        "duplicate_candidate_attempt_binding_id",
        "duplicate_candidate_attempt_id",
        "duplicate_candidate_digest",
        "replay_run_id_mismatch",
        "replay_orphan_attempt_id",
        "replay_candidate_digest_mismatch",
        "replay_result_ids_mismatch",
        "replay_refusal_ids_mismatch",
        "invalid_replay_result_id",
        "invalid_replay_refusal_id",
    }
    if "unsupported_trace_policy_version" in reasons:
        return PracticeDisposition.TRACE_POLICY_UNSUPPORTED
    if any(reason in identity_mismatch_codes for reason in reasons):
        return PracticeDisposition.TRACE_IDENTITY_MISMATCH
    if "missing_replay_records" in reasons:
        return PracticeDisposition.TRACE_UPSTREAM_INCOMPLETE
    return PracticeDisposition.TRACE_INVALID_INPUT


def build_practice_trace_input(
    *,
    problem_frame_digest: str,
    original_contract_assessment_id: str,
    residual_ids: tuple[str, ...],
    search_gate_decision_id: str,
    compute_budget_id: str,
    run: GeometricSearchRun | SearchRunRefusal,
    replay_results: tuple[ReplayAdapterResult, ...] = (),
    replay_refusals: tuple[ReplayAdapterRefusal, ...] = (),
    schema_versions: tuple[tuple[str, str], ...] = (),
    policy_versions: tuple[tuple[str, str], ...] = (),
    trace_policy_version: str = SEALED_PRACTICE_TRACE_POLICY_VERSION,
) -> PracticeTraceInput | PracticeTraceRefusal:
    """Validate upstream identities and emit a trace input or refusal."""

    if trace_policy_version != SEALED_PRACTICE_TRACE_POLICY_VERSION:
        return _refusal(
            input_digest=None,
            trace_policy_version=trace_policy_version,
            disposition=PracticeDisposition.TRACE_POLICY_UNSUPPORTED,
            reason_codes=("unsupported_trace_policy_version",),
        )

    reasons: list[str] = []
    if not _sha256_text(problem_frame_digest):
        reasons.append("invalid_problem_frame_digest")
    if not _nonempty_text(original_contract_assessment_id):
        reasons.append("missing_original_contract_assessment_id")
    if not isinstance(residual_ids, tuple) or not all(
        _nonempty_text(residual_id) for residual_id in residual_ids
    ):
        reasons.append("invalid_residual_ids")
    if not _sha256_text(search_gate_decision_id):
        reasons.append("invalid_search_gate_decision_id")
    if not _sha256_text(compute_budget_id):
        reasons.append("invalid_compute_budget_id")
    if not _valid_version_pairs(schema_versions):
        reasons.append("invalid_schema_versions")
    if not _valid_version_pairs(policy_versions):
        reasons.append("invalid_policy_versions")

    geometric_search_run_id = _run_identity(run)
    if not _sha256_text(geometric_search_run_id):
        reasons.append("invalid_geometric_search_run_id")

    candidate_attempt_ids: tuple[str, ...] = ()
    if isinstance(run, GeometricSearchRun):
        attempts = run.candidate_attempts
        if not isinstance(attempts, tuple):
            reasons.append("invalid_candidate_attempts")
        else:
            candidate_attempt_ids = tuple(attempt.attempt_id for attempt in attempts)
            if not all(_nonempty_text(attempt_id) for attempt_id in candidate_attempt_ids):
                reasons.append("invalid_candidate_attempt_id")
    elif isinstance(run, SearchRunRefusal):
        if replay_results or replay_refusals:
            reasons.append("replay_records_with_run_refusal")
    else:
        reasons.append("invalid_run_type")

    if not reasons:
        reasons.extend(
            _validate_run_bindings(
                run=run,
                problem_frame_digest=problem_frame_digest,
                original_contract_assessment_id=original_contract_assessment_id,
                residual_ids=residual_ids,
                search_gate_decision_id=search_gate_decision_id,
                compute_budget_id=compute_budget_id,
            )
        )

    replay_result_ids = tuple(result.replay_result_id for result in replay_results)
    replay_refusal_ids = tuple(refusal.replay_refusal_id for refusal in replay_refusals)

    if isinstance(run, GeometricSearchRun) and not reasons:
        reasons.extend(
            _validate_replay_bindings(
                run=run,
                replay_results=replay_results,
                replay_refusals=replay_refusals,
            )
        )

    if reasons:
        return _refusal(
            input_digest=None,
            disposition=_failure_disposition(reasons),
            reason_codes=tuple(reasons),
        )

    input_digest = _canonical_digest(
        _input_digest_payload(
            trace_policy_version=trace_policy_version,
            problem_frame_digest=problem_frame_digest,
            original_contract_assessment_id=original_contract_assessment_id,
            residual_ids=residual_ids,
            search_gate_decision_id=search_gate_decision_id,
            compute_budget_id=compute_budget_id,
            geometric_search_run_id=geometric_search_run_id,
            candidate_attempt_ids=candidate_attempt_ids,
            candidate_attempt_binding_ids=(),
            replay_result_ids=replay_result_ids,
            replay_refusal_ids=replay_refusal_ids,
            schema_versions=schema_versions,
            policy_versions=policy_versions,
        )
    )
    return PracticeTraceInput(
        input_digest=input_digest,
        trace_policy_version=trace_policy_version,
        problem_frame_digest=problem_frame_digest,
        original_contract_assessment_id=original_contract_assessment_id,
        residual_ids=residual_ids,
        search_gate_decision_id=search_gate_decision_id,
        compute_budget_id=compute_budget_id,
        geometric_search_run_id=geometric_search_run_id,
        candidate_attempt_ids=candidate_attempt_ids,
        candidate_attempt_binding_ids=(),
        replay_result_ids=replay_result_ids,
        replay_refusal_ids=replay_refusal_ids,
        schema_versions=schema_versions,
        policy_versions=policy_versions,
    )


def seal_practice_trace(
    trace_input: PracticeTraceInput,
    *,
    run: GeometricSearchRun | SearchRunRefusal,
    replay_results: tuple[ReplayAdapterResult, ...] = (),
    replay_refusals: tuple[ReplayAdapterRefusal, ...] = (),
    evidence_spans: tuple[SourceSpan, ...] = (),
    explanation: str = "",
) -> SealedPracticeTrace | PracticeTraceRefusal:
    """Seal a validated practice episode as immutable diagnostic evidence."""

    if not isinstance(trace_input, PracticeTraceInput):
        return _refusal(
            input_digest=None,
            disposition=PracticeDisposition.TRACE_INVALID_INPUT,
            reason_codes=("invalid_trace_input_type",),
        )
    if trace_input.trace_policy_version != SEALED_PRACTICE_TRACE_POLICY_VERSION:
        return _refusal(
            input_digest=trace_input.input_digest,
            trace_policy_version=trace_input.trace_policy_version,
            disposition=PracticeDisposition.TRACE_POLICY_UNSUPPORTED,
            reason_codes=("unsupported_trace_policy_version",),
        )
    if not _valid_spans(evidence_spans):
        return _refusal(
            input_digest=trace_input.input_digest,
            disposition=PracticeDisposition.TRACE_INVALID_INPUT,
            reason_codes=("invalid_evidence_spans",),
        )

    reasons: list[str] = []
    geometric_search_run_id = _run_identity(run)
    if geometric_search_run_id != trace_input.geometric_search_run_id:
        reasons.append("geometric_search_run_id_mismatch")

    replay_result_ids = tuple(result.replay_result_id for result in replay_results)
    replay_refusal_ids = tuple(refusal.replay_refusal_id for refusal in replay_refusals)
    if replay_result_ids != trace_input.replay_result_ids:
        reasons.append("replay_result_ids_mismatch")
    if replay_refusal_ids != trace_input.replay_refusal_ids:
        reasons.append("replay_refusal_ids_mismatch")

    if not reasons:
        reasons.extend(
            _validate_run_bindings(
                run=run,
                problem_frame_digest=trace_input.problem_frame_digest,
                original_contract_assessment_id=trace_input.original_contract_assessment_id,
                residual_ids=trace_input.residual_ids,
                search_gate_decision_id=trace_input.search_gate_decision_id,
                compute_budget_id=trace_input.compute_budget_id,
            )
        )

    if isinstance(run, GeometricSearchRun) and not reasons:
        attempt_ids = tuple(attempt.attempt_id for attempt in run.candidate_attempts)
        if attempt_ids != trace_input.candidate_attempt_ids:
            reasons.append("candidate_attempt_ids_mismatch")
        reasons.extend(
            _validate_replay_bindings(
                run=run,
                replay_results=replay_results,
                replay_refusals=replay_refusals,
            )
        )
        if run.candidate_attempts and not replay_results and not replay_refusals:
            reasons.append("missing_replay_records")

    if reasons:
        return _refusal(
            input_digest=trace_input.input_digest,
            disposition=_failure_disposition(reasons),
            reason_codes=tuple(reasons),
        )

    recomputed_input_digest = _canonical_digest(
        _input_digest_payload(
            trace_policy_version=trace_input.trace_policy_version,
            problem_frame_digest=trace_input.problem_frame_digest,
            original_contract_assessment_id=trace_input.original_contract_assessment_id,
            residual_ids=trace_input.residual_ids,
            search_gate_decision_id=trace_input.search_gate_decision_id,
            compute_budget_id=trace_input.compute_budget_id,
            geometric_search_run_id=trace_input.geometric_search_run_id,
            candidate_attempt_ids=trace_input.candidate_attempt_ids,
            candidate_attempt_binding_ids=trace_input.candidate_attempt_binding_ids,
            replay_result_ids=trace_input.replay_result_ids,
            replay_refusal_ids=trace_input.replay_refusal_ids,
            schema_versions=trace_input.schema_versions,
            policy_versions=trace_input.policy_versions,
        )
    )
    if recomputed_input_digest != trace_input.input_digest:
        return _refusal(
            input_digest=trace_input.input_digest,
            disposition=PracticeDisposition.TRACE_IDENTITY_MISMATCH,
            reason_codes=("input_digest_mismatch",),
        )

    practice_disposition = _derive_disposition(
        run=run,
        replay_results=replay_results,
        replay_refusals=replay_refusals,
    )
    if practice_disposition is None or practice_disposition not in _SEALED_DISPOSITIONS:
        return _refusal(
            input_digest=trace_input.input_digest,
            disposition=PracticeDisposition.TRACE_UPSTREAM_INCOMPLETE,
            reason_codes=("unsupported_practice_disposition",),
        )

    identity_chain = _upstream_identity_chain(
        problem_frame_digest=trace_input.problem_frame_digest,
        original_contract_assessment_id=trace_input.original_contract_assessment_id,
        residual_ids=trace_input.residual_ids,
        search_gate_decision_id=trace_input.search_gate_decision_id,
        compute_budget_id=trace_input.compute_budget_id,
        geometric_search_run_id=trace_input.geometric_search_run_id,
        candidate_attempt_ids=trace_input.candidate_attempt_ids,
        candidate_attempt_binding_ids=trace_input.candidate_attempt_binding_ids,
        replay_result_ids=trace_input.replay_result_ids,
        replay_refusal_ids=trace_input.replay_refusal_ids,
    )
    trace_records = identity_chain
    trace_id = _canonical_digest(
        _trace_id_payload(
            trace_policy_version=trace_input.trace_policy_version,
            input_digest=trace_input.input_digest,
            problem_frame_digest=trace_input.problem_frame_digest,
            original_contract_assessment_id=trace_input.original_contract_assessment_id,
            residual_ids=trace_input.residual_ids,
            search_gate_decision_id=trace_input.search_gate_decision_id,
            compute_budget_id=trace_input.compute_budget_id,
            geometric_search_run_id=trace_input.geometric_search_run_id,
            candidate_attempt_ids=trace_input.candidate_attempt_ids,
            candidate_attempt_binding_ids=trace_input.candidate_attempt_binding_ids,
            replay_result_ids=trace_input.replay_result_ids,
            replay_refusal_ids=trace_input.replay_refusal_ids,
            upstream_identity_chain=identity_chain,
            practice_disposition=practice_disposition,
            trace_records=trace_records,
            evidence_spans=evidence_spans,
            created_by_policy=CREATED_BY_POLICY,
        )
    )

    safe_explanation = explanation or (
        "Sealed practice trace disposition: " + practice_disposition.value + "."
    )
    return SealedPracticeTrace(
        trace_id=trace_id,
        trace_policy_version=trace_input.trace_policy_version,
        input_digest=trace_input.input_digest,
        problem_frame_digest=trace_input.problem_frame_digest,
        original_contract_assessment_id=trace_input.original_contract_assessment_id,
        residual_ids=trace_input.residual_ids,
        search_gate_decision_id=trace_input.search_gate_decision_id,
        compute_budget_id=trace_input.compute_budget_id,
        geometric_search_run_id=trace_input.geometric_search_run_id,
        candidate_attempt_ids=trace_input.candidate_attempt_ids,
        candidate_attempt_binding_ids=trace_input.candidate_attempt_binding_ids,
        replay_result_ids=trace_input.replay_result_ids,
        replay_refusal_ids=trace_input.replay_refusal_ids,
        upstream_identity_chain=identity_chain,
        practice_disposition=practice_disposition,
        trace_records=trace_records,
        evidence_spans=evidence_spans,
        created_by_policy=CREATED_BY_POLICY,
        explanation=safe_explanation,
    )


def _valid_binding_record(binding: object) -> bool:
    required = (
        "binding_id",
        "original_run_id",
        "operator_result_id",
        "candidate_attempt_id",
        "attempt_index",
        "candidate_digest",
        "candidate_reconstruction_digest",
        "run_attempt_membership",
        "reason_codes",
        "evidence_spans",
    )
    return all(hasattr(binding, name) for name in required)


_BOUND_STRUCTURAL_REASON_CODES = frozenset(
    {
        "invalid_run_type",
        "invalid_binding_type",
        "invalid_candidate_operator_result_type",
        "invalid_replay_result_type",
        "invalid_replay_refusal_type",
        "binding_result_count_mismatch",
    }
)


def _has_bound_structural_failure(reasons: list[str]) -> bool:
    return any(reason in _BOUND_STRUCTURAL_REASON_CODES for reason in reasons)


def _valid_operator_result_record(operator_result: object) -> bool:
    required = (
        "operator_result_id",
        "attempt_id",
        "attempt_index",
        "candidate_digest",
        "candidate_reconstruction_digest",
        "geometric_search_run_id",
        "evidence_spans",
        "candidate_attempt",
        "candidate_reconstruction",
    )
    return all(hasattr(operator_result, name) for name in required)


def _validate_bound_binding_pair(
    *,
    run: GeometricSearchRun,
    binding: object,
    operator_result: object,
) -> list[str]:
    reasons: list[str] = []
    attempt = operator_result.candidate_attempt
    reconstruction = operator_result.candidate_reconstruction

    if binding.original_run_id != run.run_id:
        reasons.append("binding_run_mismatch")
    if binding.operator_result_id != operator_result.operator_result_id:
        reasons.append("binding_result_mismatch")
    if binding.candidate_attempt_id != operator_result.attempt_id:
        reasons.append("binding_attempt_mismatch")
    if binding.candidate_attempt_id != attempt.attempt_id:
        reasons.append("binding_attempt_mismatch")
    if binding.attempt_index != operator_result.attempt_index:
        reasons.append("binding_attempt_mismatch")
    if binding.attempt_index != attempt.attempt_index:
        reasons.append("binding_attempt_mismatch")
    if binding.candidate_digest != operator_result.candidate_digest:
        reasons.append("binding_reconstruction_mismatch")
    if binding.candidate_digest != attempt.candidate_digest:
        reasons.append("binding_reconstruction_mismatch")
    if (
        binding.candidate_reconstruction_digest
        != operator_result.candidate_reconstruction_digest
    ):
        reasons.append("binding_reconstruction_mismatch")
    if (
        binding.candidate_reconstruction_digest
        != reconstruction.candidate_reconstruction_digest
    ):
        reasons.append("binding_reconstruction_mismatch")
    if binding.run_attempt_membership != "structurally_bound":
        reasons.append("binding_not_structurally_bound")
    if binding.reason_codes != ():
        reasons.append("binding_not_successful")
    if binding.evidence_spans != operator_result.evidence_spans:
        reasons.append("binding_evidence_mismatch")
    if binding.evidence_spans != attempt.evidence_spans:
        reasons.append("binding_evidence_mismatch")
    if binding.evidence_spans != reconstruction.evidence_spans:
        reasons.append("binding_evidence_mismatch")
    if operator_result.geometric_search_run_id != run.run_id:
        reasons.append("operator_result_run_mismatch")
    if reconstruction.problem_frame_digest != run.problem_frame_digest:
        reasons.append("operator_reconstruction_run_mismatch")
    if reconstruction.original_contract_assessment_id != run.contract_assessment_id:
        reasons.append("operator_reconstruction_run_mismatch")
    if reconstruction.source_residual_id not in run.residual_ids:
        reasons.append("operator_reconstruction_run_mismatch")
    return reasons


def _validate_bound_replay_bindings(
    *,
    run: GeometricSearchRun,
    bindings: tuple[object, ...],
    replay_results: tuple[ReplayAdapterResult, ...],
    replay_refusals: tuple[ReplayAdapterRefusal, ...],
) -> list[str]:
    reasons: list[str] = []
    attempt_ids = {binding.candidate_attempt_id for binding in bindings}  # type: ignore[attr-defined]
    digest_by_attempt = {
        binding.candidate_attempt_id: binding.candidate_digest  # type: ignore[attr-defined]
        for binding in bindings
    }

    for record in (*replay_results, *replay_refusals):
        identity_reason = _validate_replay_record_identity(record)
        if identity_reason is not None:
            reasons.append(identity_reason)
        run_id = record.run_id
        attempt_id = record.attempt_id
        candidate_digest = record.candidate_digest
        if run_id != run.run_id:
            reasons.append("replay_run_id_mismatch")
        if attempt_id is None or not _nonempty_text(attempt_id):
            reasons.append("replay_orphan_attempt_id")
        elif attempt_id not in attempt_ids:
            reasons.append("replay_orphan_attempt_id")
        if candidate_digest is not None and _nonempty_text(candidate_digest):
            if (
                attempt_id in digest_by_attempt
                and candidate_digest != digest_by_attempt[attempt_id]
            ):
                reasons.append("replay_candidate_digest_mismatch")
        elif attempt_id in digest_by_attempt:
            reasons.append("replay_candidate_digest_mismatch")

    return reasons


def _derive_bound_disposition(
    *,
    replay_results: tuple[ReplayAdapterResult, ...],
    replay_refusals: tuple[ReplayAdapterRefusal, ...],
) -> PracticeDisposition | None:
    if not replay_results and not replay_refusals:
        return None

    if any(
        result.replay_disposition is ReplayDisposition.CONTRACT_AND_PROOF_CLOSED
        for result in replay_results
    ):
        return PracticeDisposition.SEALED_CANDIDATE_REPLAY_CLOSED

    if any(
        result.replay_disposition
        is ReplayDisposition.CONTRACT_CLOSED_BUT_PROOF_REFUSED
        for result in replay_results
    ):
        return PracticeDisposition.SEALED_CONTRACT_CLOSED_PROOF_REFUSED

    if replay_results and all(
        result.replay_disposition is ReplayDisposition.CONTRACT_REFUSED
        for result in replay_results
    ):
        return PracticeDisposition.SEALED_ALL_CANDIDATES_REFUSED

    if replay_refusals and not replay_results:
        return PracticeDisposition.SEALED_REPLAY_UNAVAILABLE

    return None


def build_bound_practice_trace_input(
    *,
    problem_frame_digest: str,
    original_contract_assessment_id: str,
    residual_ids: tuple[str, ...],
    search_gate_decision_id: str,
    compute_budget_id: str,
    run: GeometricSearchRun,
    bindings: tuple[object, ...],
    candidate_operator_results: tuple[object, ...],
    replay_results: tuple[ReplayAdapterResult, ...] = (),
    replay_refusals: tuple[ReplayAdapterRefusal, ...] = (),
    schema_versions: tuple[tuple[str, str], ...] = (),
    policy_versions: tuple[tuple[str, str], ...] = (),
    trace_policy_version: str = SEALED_PRACTICE_TRACE_POLICY_VERSION,
) -> PracticeTraceInput | PracticeTraceRefusal:
    """Validate bound episode identities and emit a trace input or refusal."""

    if trace_policy_version != SEALED_PRACTICE_TRACE_POLICY_VERSION:
        return _refusal(
            input_digest=None,
            trace_policy_version=trace_policy_version,
            disposition=PracticeDisposition.TRACE_POLICY_UNSUPPORTED,
            reason_codes=("unsupported_trace_policy_version",),
        )

    reasons: list[str] = []
    if not isinstance(run, GeometricSearchRun):
        reasons.append("invalid_run_type")
    if not isinstance(bindings, tuple) or not all(
        _valid_binding_record(binding) for binding in bindings
    ):
        reasons.append("invalid_binding_type")
    if not isinstance(candidate_operator_results, tuple) or not all(
        _valid_operator_result_record(result) for result in candidate_operator_results
    ):
        reasons.append("invalid_candidate_operator_result_type")
    if not isinstance(replay_results, tuple) or not all(
        isinstance(result, ReplayAdapterResult) for result in replay_results
    ):
        reasons.append("invalid_replay_result_type")
    if not isinstance(replay_refusals, tuple) or not all(
        isinstance(refusal, ReplayAdapterRefusal) for refusal in replay_refusals
    ):
        reasons.append("invalid_replay_refusal_type")

    if not _sha256_text(problem_frame_digest):
        reasons.append("invalid_problem_frame_digest")
    if not _nonempty_text(original_contract_assessment_id):
        reasons.append("missing_original_contract_assessment_id")
    if not isinstance(residual_ids, tuple) or not all(
        _nonempty_text(residual_id) for residual_id in residual_ids
    ):
        reasons.append("invalid_residual_ids")
    if not _sha256_text(search_gate_decision_id):
        reasons.append("invalid_search_gate_decision_id")
    if not _sha256_text(compute_budget_id):
        reasons.append("invalid_compute_budget_id")
    if not _valid_version_pairs(schema_versions):
        reasons.append("invalid_schema_versions")
    if not _valid_version_pairs(policy_versions):
        reasons.append("invalid_policy_versions")

    geometric_search_run_id = run.run_id if isinstance(run, GeometricSearchRun) else ""
    if not _sha256_text(geometric_search_run_id):
        reasons.append("invalid_geometric_search_run_id")

    if isinstance(bindings, tuple) and isinstance(candidate_operator_results, tuple):
        if len(bindings) != len(candidate_operator_results):
            reasons.append("binding_result_count_mismatch")

    if _has_bound_structural_failure(reasons):
        return _refusal(
            input_digest=None,
            disposition=_failure_disposition(reasons),
            reason_codes=tuple(dict.fromkeys(reasons)),
        )

    if not reasons and isinstance(run, GeometricSearchRun):
        reasons.extend(
            _validate_run_bindings(
                run=run,
                problem_frame_digest=problem_frame_digest,
                original_contract_assessment_id=original_contract_assessment_id,
                residual_ids=residual_ids,
                search_gate_decision_id=search_gate_decision_id,
                compute_budget_id=compute_budget_id,
            )
        )

        binding_ids: list[str] = []
        attempt_ids: list[str] = []
        candidate_digests: list[str] = []
        for binding, operator_result in zip(bindings, candidate_operator_results, strict=True):
            if not _sha256_text(binding.binding_id):
                reasons.append("invalid_candidate_attempt_binding_id")
            if binding.binding_id in binding_ids:
                reasons.append("duplicate_candidate_attempt_binding_id")
            binding_ids.append(binding.binding_id)
            if binding.candidate_attempt_id in attempt_ids:
                reasons.append("duplicate_candidate_attempt_id")
            attempt_ids.append(binding.candidate_attempt_id)
            if binding.candidate_digest in candidate_digests:
                reasons.append("duplicate_candidate_digest")
            candidate_digests.append(binding.candidate_digest)
            reasons.extend(
                _validate_bound_binding_pair(
                    run=run,
                    binding=binding,
                    operator_result=operator_result,
                )
            )

        reasons.extend(
            _validate_bound_replay_bindings(
                run=run,
                bindings=bindings,
                replay_results=replay_results,
                replay_refusals=replay_refusals,
            )
        )

    candidate_attempt_ids = tuple(binding.candidate_attempt_id for binding in bindings)
    candidate_attempt_binding_ids = tuple(binding.binding_id for binding in bindings)
    replay_result_ids = tuple(result.replay_result_id for result in replay_results)
    replay_refusal_ids = tuple(refusal.replay_refusal_id for refusal in replay_refusals)

    if reasons:
        return _refusal(
            input_digest=None,
            disposition=_failure_disposition(reasons),
            reason_codes=tuple(dict.fromkeys(reasons)),
        )

    input_digest = _canonical_digest(
        _input_digest_payload(
            trace_policy_version=trace_policy_version,
            problem_frame_digest=problem_frame_digest,
            original_contract_assessment_id=original_contract_assessment_id,
            residual_ids=residual_ids,
            search_gate_decision_id=search_gate_decision_id,
            compute_budget_id=compute_budget_id,
            geometric_search_run_id=geometric_search_run_id,
            candidate_attempt_ids=candidate_attempt_ids,
            candidate_attempt_binding_ids=candidate_attempt_binding_ids,
            replay_result_ids=replay_result_ids,
            replay_refusal_ids=replay_refusal_ids,
            schema_versions=schema_versions,
            policy_versions=policy_versions,
        )
    )
    return PracticeTraceInput(
        input_digest=input_digest,
        trace_policy_version=trace_policy_version,
        problem_frame_digest=problem_frame_digest,
        original_contract_assessment_id=original_contract_assessment_id,
        residual_ids=residual_ids,
        search_gate_decision_id=search_gate_decision_id,
        compute_budget_id=compute_budget_id,
        geometric_search_run_id=geometric_search_run_id,
        candidate_attempt_ids=candidate_attempt_ids,
        candidate_attempt_binding_ids=candidate_attempt_binding_ids,
        replay_result_ids=replay_result_ids,
        replay_refusal_ids=replay_refusal_ids,
        schema_versions=schema_versions,
        policy_versions=policy_versions,
    )


def seal_bound_practice_trace(
    trace_input: PracticeTraceInput,
    *,
    run: GeometricSearchRun,
    bindings: tuple[object, ...],
    candidate_operator_results: tuple[object, ...],
    replay_results: tuple[ReplayAdapterResult, ...] = (),
    replay_refusals: tuple[ReplayAdapterRefusal, ...] = (),
    evidence_spans: tuple[SourceSpan, ...] = (),
    explanation: str = "",
) -> SealedPracticeTrace | PracticeTraceRefusal:
    """Seal a validated bound practice episode as immutable diagnostic evidence."""

    if not isinstance(trace_input, PracticeTraceInput):
        return _refusal(
            input_digest=None,
            disposition=PracticeDisposition.TRACE_INVALID_INPUT,
            reason_codes=("invalid_trace_input_type",),
        )
    if trace_input.trace_policy_version != SEALED_PRACTICE_TRACE_POLICY_VERSION:
        return _refusal(
            input_digest=trace_input.input_digest,
            trace_policy_version=trace_input.trace_policy_version,
            disposition=PracticeDisposition.TRACE_POLICY_UNSUPPORTED,
            reason_codes=("unsupported_trace_policy_version",),
        )
    if not _valid_spans(evidence_spans):
        return _refusal(
            input_digest=trace_input.input_digest,
            disposition=PracticeDisposition.TRACE_INVALID_INPUT,
            reason_codes=("invalid_evidence_spans",),
        )

    reasons: list[str] = []
    if not isinstance(run, GeometricSearchRun):
        reasons.append("invalid_run_type")
    if not isinstance(bindings, tuple) or not all(
        _valid_binding_record(binding) for binding in bindings
    ):
        reasons.append("invalid_binding_type")
    if not isinstance(candidate_operator_results, tuple) or not all(
        _valid_operator_result_record(result) for result in candidate_operator_results
    ):
        reasons.append("invalid_candidate_operator_result_type")

    if run.run_id != trace_input.geometric_search_run_id:
        reasons.append("geometric_search_run_id_mismatch")

    replay_result_ids = tuple(result.replay_result_id for result in replay_results)
    replay_refusal_ids = tuple(refusal.replay_refusal_id for refusal in replay_refusals)
    if replay_result_ids != trace_input.replay_result_ids:
        reasons.append("replay_result_ids_mismatch")
    if replay_refusal_ids != trace_input.replay_refusal_ids:
        reasons.append("replay_refusal_ids_mismatch")

    if _has_bound_structural_failure(reasons):
        return _refusal(
            input_digest=trace_input.input_digest,
            disposition=_failure_disposition(reasons),
            reason_codes=tuple(dict.fromkeys(reasons)),
        )

    binding_ids = tuple(binding.binding_id for binding in bindings)
    attempt_ids = tuple(binding.candidate_attempt_id for binding in bindings)
    if binding_ids != trace_input.candidate_attempt_binding_ids:
        reasons.append("candidate_attempt_binding_ids_mismatch")
    if attempt_ids != trace_input.candidate_attempt_ids:
        reasons.append("candidate_attempt_ids_mismatch")

    if not reasons:
        reasons.extend(
            _validate_run_bindings(
                run=run,
                problem_frame_digest=trace_input.problem_frame_digest,
                original_contract_assessment_id=trace_input.original_contract_assessment_id,
                residual_ids=trace_input.residual_ids,
                search_gate_decision_id=trace_input.search_gate_decision_id,
                compute_budget_id=trace_input.compute_budget_id,
            )
        )
        if len(bindings) != len(candidate_operator_results):
            reasons.append("binding_result_count_mismatch")
        elif not reasons:
            for binding, operator_result in zip(
                bindings,
                candidate_operator_results,
                strict=True,
            ):
                reasons.extend(
                    _validate_bound_binding_pair(
                        run=run,
                        binding=binding,
                        operator_result=operator_result,
                    )
                )
            reasons.extend(
                _validate_bound_replay_bindings(
                    run=run,
                    bindings=bindings,
                    replay_results=replay_results,
                    replay_refusals=replay_refusals,
                )
            )
            if bindings and not replay_results and not replay_refusals:
                reasons.append("missing_replay_records")

    if reasons:
        return _refusal(
            input_digest=trace_input.input_digest,
            disposition=_failure_disposition(reasons),
            reason_codes=tuple(dict.fromkeys(reasons)),
        )

    recomputed_input_digest = _canonical_digest(
        _input_digest_payload(
            trace_policy_version=trace_input.trace_policy_version,
            problem_frame_digest=trace_input.problem_frame_digest,
            original_contract_assessment_id=trace_input.original_contract_assessment_id,
            residual_ids=trace_input.residual_ids,
            search_gate_decision_id=trace_input.search_gate_decision_id,
            compute_budget_id=trace_input.compute_budget_id,
            geometric_search_run_id=trace_input.geometric_search_run_id,
            candidate_attempt_ids=trace_input.candidate_attempt_ids,
            candidate_attempt_binding_ids=trace_input.candidate_attempt_binding_ids,
            replay_result_ids=trace_input.replay_result_ids,
            replay_refusal_ids=trace_input.replay_refusal_ids,
            schema_versions=trace_input.schema_versions,
            policy_versions=trace_input.policy_versions,
        )
    )
    if recomputed_input_digest != trace_input.input_digest:
        return _refusal(
            input_digest=trace_input.input_digest,
            disposition=PracticeDisposition.TRACE_IDENTITY_MISMATCH,
            reason_codes=("input_digest_mismatch",),
        )

    practice_disposition = _derive_bound_disposition(
        replay_results=replay_results,
        replay_refusals=replay_refusals,
    )
    if practice_disposition is None or practice_disposition not in _SEALED_DISPOSITIONS:
        return _refusal(
            input_digest=trace_input.input_digest,
            disposition=PracticeDisposition.TRACE_UPSTREAM_INCOMPLETE,
            reason_codes=("unsupported_bound_practice_disposition",),
        )

    identity_chain = _upstream_identity_chain(
        problem_frame_digest=trace_input.problem_frame_digest,
        original_contract_assessment_id=trace_input.original_contract_assessment_id,
        residual_ids=trace_input.residual_ids,
        search_gate_decision_id=trace_input.search_gate_decision_id,
        compute_budget_id=trace_input.compute_budget_id,
        geometric_search_run_id=trace_input.geometric_search_run_id,
        candidate_attempt_ids=trace_input.candidate_attempt_ids,
        candidate_attempt_binding_ids=trace_input.candidate_attempt_binding_ids,
        replay_result_ids=trace_input.replay_result_ids,
        replay_refusal_ids=trace_input.replay_refusal_ids,
    )
    trace_records = identity_chain
    trace_id = _canonical_digest(
        _trace_id_payload(
            trace_policy_version=trace_input.trace_policy_version,
            input_digest=trace_input.input_digest,
            problem_frame_digest=trace_input.problem_frame_digest,
            original_contract_assessment_id=trace_input.original_contract_assessment_id,
            residual_ids=trace_input.residual_ids,
            search_gate_decision_id=trace_input.search_gate_decision_id,
            compute_budget_id=trace_input.compute_budget_id,
            geometric_search_run_id=trace_input.geometric_search_run_id,
            candidate_attempt_ids=trace_input.candidate_attempt_ids,
            candidate_attempt_binding_ids=trace_input.candidate_attempt_binding_ids,
            replay_result_ids=trace_input.replay_result_ids,
            replay_refusal_ids=trace_input.replay_refusal_ids,
            upstream_identity_chain=identity_chain,
            practice_disposition=practice_disposition,
            trace_records=trace_records,
            evidence_spans=evidence_spans,
            created_by_policy=CREATED_BY_POLICY,
        )
    )

    safe_explanation = explanation or (
        "Sealed bound practice trace disposition: " + practice_disposition.value + "."
    )
    return SealedPracticeTrace(
        trace_id=trace_id,
        trace_policy_version=trace_input.trace_policy_version,
        input_digest=trace_input.input_digest,
        problem_frame_digest=trace_input.problem_frame_digest,
        original_contract_assessment_id=trace_input.original_contract_assessment_id,
        residual_ids=trace_input.residual_ids,
        search_gate_decision_id=trace_input.search_gate_decision_id,
        compute_budget_id=trace_input.compute_budget_id,
        geometric_search_run_id=trace_input.geometric_search_run_id,
        candidate_attempt_ids=trace_input.candidate_attempt_ids,
        candidate_attempt_binding_ids=trace_input.candidate_attempt_binding_ids,
        replay_result_ids=trace_input.replay_result_ids,
        replay_refusal_ids=trace_input.replay_refusal_ids,
        upstream_identity_chain=identity_chain,
        practice_disposition=practice_disposition,
        trace_records=trace_records,
        evidence_spans=evidence_spans,
        created_by_policy=CREATED_BY_POLICY,
        explanation=safe_explanation,
    )


__all__ = [
    "SEALED_PRACTICE_TRACE_POLICY_VERSION",
    "PracticeDisposition",
    "PracticeTraceInput",
    "SealedPracticeTrace",
    "PracticeTraceRefusal",
    "PracticeTraceOutcome",
    "build_practice_trace_input",
    "seal_practice_trace",
    "build_bound_practice_trace_input",
    "seal_bound_practice_trace",
]
