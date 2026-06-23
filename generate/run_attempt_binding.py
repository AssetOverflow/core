"""Inert CandidateAttempt run-binding shell per ADR-0232."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum, unique

from generate.candidate_operator import CandidateOperatorResult
from generate.geometric_search_run import (
    BudgetCharge,
    CandidateAttempt,
    CandidateReplayStatus,
    GeometricSearchRun,
)
from generate.kernel_facts import SourceSpan

CANDIDATE_ATTEMPT_RUN_BINDING_POLICY_VERSION = "candidate_attempt_run_binding.v1"


@unique
class RunAttemptBindingRefusalReason(str, Enum):
    INVALID_BINDING_INPUT = "invalid_binding_input"
    UNSUPPORTED_BINDING_POLICY = "unsupported_binding_policy"
    RUN_RESULT_MISMATCH = "run_result_mismatch"
    ATTEMPT_RESULT_MISMATCH = "attempt_result_mismatch"
    RECONSTRUCTION_RESULT_MISMATCH = "reconstruction_result_mismatch"
    REPLAY_STATUS_NOT_PENDING = "replay_status_not_pending"
    REPLAY_BLOCKERS_PRESENT = "replay_blockers_present"
    DUPLICATE_ATTEMPT_INDEX = "duplicate_attempt_index"
    DUPLICATE_ATTEMPT_ID = "duplicate_attempt_id"
    DUPLICATE_CANDIDATE_DIGEST = "duplicate_candidate_digest"
    BUDGET_CHARGE_EXCEEDS_REMAINING = "budget_charge_exceeds_remaining"
    OPERATOR_SET_MISMATCH = "operator_set_mismatch"
    RUN_IDENTITY_MISMATCH = "run_identity_mismatch"
    MALFORMED_EVIDENCE_SPAN = "malformed_evidence_span"
    UNSUPPORTED_SCHEMA_VERSION = "unsupported_schema_version"


@dataclass(frozen=True, slots=True)
class CandidateAttemptRunBindingInput:
    input_digest: str
    binding_policy_version: str
    original_run_id: str
    original_run_policy_version: str
    original_run_input_digest: str
    operator_result_id: str
    operator_policy_version: str
    candidate_attempt_id: str
    attempt_index: int
    candidate_digest: str
    candidate_reconstruction_digest: str
    operator_set_id: str
    operator_set_version: str
    budget_id: str
    gate_decision_id: str
    residual_ids: tuple[str, ...]
    problem_frame_digest: str
    original_contract_assessment_id: str
    schema_versions: tuple[tuple[str, str], ...]
    policy_versions: tuple[tuple[str, str], ...]


@dataclass(frozen=True, slots=True)
class CandidateAttemptRunBinding:
    binding_id: str
    binding_policy_version: str
    input_digest: str
    original_run_id: str
    operator_result_id: str
    candidate_attempt_id: str
    attempt_index: int
    candidate_digest: str
    candidate_reconstruction_digest: str
    candidate_attempt_ref: str
    budget_charge: BudgetCharge
    depth: int
    step_index: int
    run_attempt_membership: str
    evidence_spans: tuple[SourceSpan, ...]
    reason_codes: tuple[str, ...]
    explanation: str


@dataclass(frozen=True, slots=True)
class CandidateAttemptRunBindingRefusal:
    binding_refusal_id: str
    binding_policy_version: str
    input_digest: str | None
    original_run_id: str | None
    operator_result_id: str | None
    candidate_attempt_id: str | None
    reason_codes: tuple[str, ...]
    explanation: str


CandidateAttemptRunBindingOutcome = (
    CandidateAttemptRunBinding | CandidateAttemptRunBindingRefusal
)


def _canonical_digest(payload: dict[str, object]) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _span_payload(span: SourceSpan) -> dict[str, object]:
    return {
        "text": span.text,
        "start": span.start,
        "end": span.end,
        "sentence_index": span.sentence_index,
    }


def _budget_charge_payload(charge: BudgetCharge) -> dict[str, int]:
    return {"candidates": charge.candidates, "steps": charge.steps}


def _candidate_attempt_payload(attempt: CandidateAttempt) -> dict[str, object]:
    return {
        "attempt_id": attempt.attempt_id,
        "attempt_index": attempt.attempt_index,
        "parent_attempt_id": attempt.parent_attempt_id,
        "operator_id": attempt.operator_id,
        "operator_version": attempt.operator_version,
        "input_digest": attempt.input_digest,
        "candidate_digest": attempt.candidate_digest,
        "budget_charge": _budget_charge_payload(attempt.budget_charge),
        "depth": attempt.depth,
        "step_index": attempt.step_index,
        "replay_status": attempt.replay_status.value,
        "replay_blockers": list(attempt.replay_blockers),
        "evidence_spans": [_span_payload(span) for span in attempt.evidence_spans],
    }


def _version_pairs_payload(versions: tuple[tuple[str, str], ...]) -> list[list[str]]:
    return [[name, version] for name, version in versions]


def _valid_version_pairs(value: object) -> bool:
    if not isinstance(value, tuple):
        return False
    names: list[str] = []
    for entry in value:
        if not isinstance(entry, tuple) or len(entry) != 2:
            return False
        name, version = entry
        if not isinstance(name, str) or not name:
            return False
        if not isinstance(version, str) or not version:
            return False
        names.append(name)
    return len(names) == len(set(names)) and names == sorted(names)


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


def _valid_spans(spans: object) -> bool:
    return isinstance(spans, tuple) and all(_valid_span(span) for span in spans)


def _binding_input_payload(
    *,
    original_run: GeometricSearchRun,
    candidate_operator_result: CandidateOperatorResult,
    schema_versions: tuple[tuple[str, str], ...],
    policy_versions: tuple[tuple[str, str], ...],
) -> dict[str, object]:
    attempt = candidate_operator_result.candidate_attempt
    reconstruction = candidate_operator_result.candidate_reconstruction
    return {
        "binding_policy_version": CANDIDATE_ATTEMPT_RUN_BINDING_POLICY_VERSION,
        "original_run_id": original_run.run_id,
        "original_run_policy_version": original_run.run_policy_version,
        "original_run_input_digest": original_run.input_digest,
        "operator_result_id": candidate_operator_result.operator_result_id,
        "operator_policy_version": candidate_operator_result.operator_policy_version,
        "candidate_attempt_id": attempt.attempt_id,
        "attempt_index": attempt.attempt_index,
        "candidate_digest": attempt.candidate_digest,
        "candidate_reconstruction_digest": reconstruction.candidate_reconstruction_digest,
        "operator_set_id": original_run.operator_set_id,
        "operator_set_version": original_run.operator_set_version,
        "budget_id": original_run.budget_id,
        "gate_decision_id": original_run.gate_decision_id,
        "residual_ids": list(original_run.residual_ids),
        "problem_frame_digest": original_run.problem_frame_digest,
        "original_contract_assessment_id": original_run.contract_assessment_id,
        "schema_versions": _version_pairs_payload(schema_versions),
        "policy_versions": _version_pairs_payload(policy_versions),
    }


def _refusal_id_payload(
    *,
    input_digest: str | None,
    original_run_id: str | None,
    operator_result_id: str | None,
    candidate_attempt_id: str | None,
    reason_codes: tuple[str, ...],
) -> dict[str, object]:
    return {
        "binding_refusal_id": "",
        "binding_policy_version": CANDIDATE_ATTEMPT_RUN_BINDING_POLICY_VERSION,
        "input_digest": input_digest,
        "original_run_id": original_run_id,
        "operator_result_id": operator_result_id,
        "candidate_attempt_id": candidate_attempt_id,
        "reason_codes": list(reason_codes),
    }


def _refusal(
    *,
    reason: RunAttemptBindingRefusalReason,
    input_digest: str | None = None,
    original_run_id: str | None = None,
    operator_result_id: str | None = None,
    candidate_attempt_id: str | None = None,
) -> CandidateAttemptRunBindingRefusal:
    reason_codes = (reason.value,)
    binding_refusal_id = _canonical_digest(
        _refusal_id_payload(
            input_digest=input_digest,
            original_run_id=original_run_id,
            operator_result_id=operator_result_id,
            candidate_attempt_id=candidate_attempt_id,
            reason_codes=reason_codes,
        )
    )
    return CandidateAttemptRunBindingRefusal(
        binding_refusal_id=binding_refusal_id,
        binding_policy_version=CANDIDATE_ATTEMPT_RUN_BINDING_POLICY_VERSION,
        input_digest=input_digest,
        original_run_id=original_run_id,
        operator_result_id=operator_result_id,
        candidate_attempt_id=candidate_attempt_id,
        reason_codes=reason_codes,
        explanation="CandidateAttempt run binding refused: " + reason.value + ".",
    )


def _binding_id_payload(
    *,
    input_digest: str,
    original_run_id: str,
    operator_result_id: str,
    candidate_attempt_id: str,
    attempt_index: int,
    candidate_digest: str,
    candidate_reconstruction_digest: str,
    candidate_attempt_ref: str,
    budget_charge: BudgetCharge,
    depth: int,
    step_index: int,
    evidence_spans: tuple[SourceSpan, ...],
) -> dict[str, object]:
    return {
        "binding_id": "",
        "binding_policy_version": CANDIDATE_ATTEMPT_RUN_BINDING_POLICY_VERSION,
        "input_digest": input_digest,
        "original_run_id": original_run_id,
        "operator_result_id": operator_result_id,
        "candidate_attempt_id": candidate_attempt_id,
        "attempt_index": attempt_index,
        "candidate_digest": candidate_digest,
        "candidate_reconstruction_digest": candidate_reconstruction_digest,
        "candidate_attempt_ref": candidate_attempt_ref,
        "budget_charge": _budget_charge_payload(budget_charge),
        "depth": depth,
        "step_index": step_index,
        "run_attempt_membership": "structurally_bound",
        "evidence_spans": [_span_payload(span) for span in evidence_spans],
        "reason_codes": [],
    }


def _operator_provenance_has(
    provenance: tuple[tuple[str, str], ...], key: str, value: str
) -> bool:
    return (key, value) in provenance


def bind_candidate_attempt_to_run(
    *,
    original_run: GeometricSearchRun,
    candidate_operator_result: CandidateOperatorResult,
    schema_versions: tuple[tuple[str, str], ...] = (),
    policy_versions: tuple[tuple[str, str], ...] = (),
    explanation: str = "",
) -> CandidateAttemptRunBindingOutcome:
    """Bind an existing candidate operator result to one immutable run episode."""

    if not isinstance(original_run, GeometricSearchRun):
        return _refusal(reason=RunAttemptBindingRefusalReason.INVALID_BINDING_INPUT)
    if not isinstance(candidate_operator_result, CandidateOperatorResult):
        return _refusal(
            reason=RunAttemptBindingRefusalReason.INVALID_BINDING_INPUT,
            original_run_id=original_run.run_id,
        )

    attempt = candidate_operator_result.candidate_attempt
    reconstruction = candidate_operator_result.candidate_reconstruction

    if not isinstance(attempt, CandidateAttempt):
        return _refusal(
            reason=RunAttemptBindingRefusalReason.INVALID_BINDING_INPUT,
            original_run_id=original_run.run_id,
            operator_result_id=candidate_operator_result.operator_result_id,
        )

    if not _valid_version_pairs(schema_versions) or not _valid_version_pairs(
        policy_versions
    ):
        return _refusal(
            reason=RunAttemptBindingRefusalReason.UNSUPPORTED_SCHEMA_VERSION,
            original_run_id=original_run.run_id,
            operator_result_id=candidate_operator_result.operator_result_id,
            candidate_attempt_id=attempt.attempt_id,
        )

    if candidate_operator_result.geometric_search_run_id != original_run.run_id:
        return _refusal(
            reason=RunAttemptBindingRefusalReason.RUN_RESULT_MISMATCH,
            original_run_id=original_run.run_id,
            operator_result_id=candidate_operator_result.operator_result_id,
            candidate_attempt_id=attempt.attempt_id,
        )

    if candidate_operator_result.attempt_id != attempt.attempt_id:
        return _refusal(
            reason=RunAttemptBindingRefusalReason.ATTEMPT_RESULT_MISMATCH,
            original_run_id=original_run.run_id,
            operator_result_id=candidate_operator_result.operator_result_id,
            candidate_attempt_id=attempt.attempt_id,
        )
    if candidate_operator_result.attempt_index != attempt.attempt_index:
        return _refusal(
            reason=RunAttemptBindingRefusalReason.ATTEMPT_RESULT_MISMATCH,
            original_run_id=original_run.run_id,
            operator_result_id=candidate_operator_result.operator_result_id,
            candidate_attempt_id=attempt.attempt_id,
        )
    if candidate_operator_result.candidate_digest != attempt.candidate_digest:
        return _refusal(
            reason=RunAttemptBindingRefusalReason.ATTEMPT_RESULT_MISMATCH,
            original_run_id=original_run.run_id,
            operator_result_id=candidate_operator_result.operator_result_id,
            candidate_attempt_id=attempt.attempt_id,
        )
    if candidate_operator_result.input_digest != attempt.input_digest:
        return _refusal(
            reason=RunAttemptBindingRefusalReason.ATTEMPT_RESULT_MISMATCH,
            original_run_id=original_run.run_id,
            operator_result_id=candidate_operator_result.operator_result_id,
            candidate_attempt_id=attempt.attempt_id,
        )
    if candidate_operator_result.operator_name != attempt.operator_id:
        return _refusal(
            reason=RunAttemptBindingRefusalReason.ATTEMPT_RESULT_MISMATCH,
            original_run_id=original_run.run_id,
            operator_result_id=candidate_operator_result.operator_result_id,
            candidate_attempt_id=attempt.attempt_id,
        )
    if candidate_operator_result.operator_version != attempt.operator_version:
        return _refusal(
            reason=RunAttemptBindingRefusalReason.ATTEMPT_RESULT_MISMATCH,
            original_run_id=original_run.run_id,
            operator_result_id=candidate_operator_result.operator_result_id,
            candidate_attempt_id=attempt.attempt_id,
        )

    if reconstruction.candidate_digest != candidate_operator_result.candidate_digest:
        return _refusal(
            reason=RunAttemptBindingRefusalReason.RECONSTRUCTION_RESULT_MISMATCH,
            original_run_id=original_run.run_id,
            operator_result_id=candidate_operator_result.operator_result_id,
            candidate_attempt_id=attempt.attempt_id,
        )
    if (
        reconstruction.candidate_reconstruction_digest
        != candidate_operator_result.candidate_reconstruction_digest
    ):
        return _refusal(
            reason=RunAttemptBindingRefusalReason.RECONSTRUCTION_RESULT_MISMATCH,
            original_run_id=original_run.run_id,
            operator_result_id=candidate_operator_result.operator_result_id,
            candidate_attempt_id=attempt.attempt_id,
        )

    if attempt.replay_status is not CandidateReplayStatus.REPLAY_PENDING:
        return _refusal(
            reason=RunAttemptBindingRefusalReason.REPLAY_STATUS_NOT_PENDING,
            original_run_id=original_run.run_id,
            operator_result_id=candidate_operator_result.operator_result_id,
            candidate_attempt_id=attempt.attempt_id,
        )
    if attempt.replay_blockers != ():
        return _refusal(
            reason=RunAttemptBindingRefusalReason.REPLAY_BLOCKERS_PRESENT,
            original_run_id=original_run.run_id,
            operator_result_id=candidate_operator_result.operator_result_id,
            candidate_attempt_id=attempt.attempt_id,
        )

    if reconstruction.source_residual_id not in original_run.residual_ids:
        return _refusal(
            reason=RunAttemptBindingRefusalReason.RUN_IDENTITY_MISMATCH,
            original_run_id=original_run.run_id,
            operator_result_id=candidate_operator_result.operator_result_id,
            candidate_attempt_id=attempt.attempt_id,
        )
    if reconstruction.problem_frame_digest != original_run.problem_frame_digest:
        return _refusal(
            reason=RunAttemptBindingRefusalReason.RUN_IDENTITY_MISMATCH,
            original_run_id=original_run.run_id,
            operator_result_id=candidate_operator_result.operator_result_id,
            candidate_attempt_id=attempt.attempt_id,
        )
    if (
        reconstruction.original_contract_assessment_id
        != original_run.contract_assessment_id
    ):
        return _refusal(
            reason=RunAttemptBindingRefusalReason.RUN_IDENTITY_MISMATCH,
            original_run_id=original_run.run_id,
            operator_result_id=candidate_operator_result.operator_result_id,
            candidate_attempt_id=attempt.attempt_id,
        )

    if not _operator_provenance_has(
        reconstruction.operator_provenance,
        "operator_set_id",
        original_run.operator_set_id,
    ) or not _operator_provenance_has(
        reconstruction.operator_provenance,
        "operator_set_version",
        original_run.operator_set_version,
    ):
        return _refusal(
            reason=RunAttemptBindingRefusalReason.OPERATOR_SET_MISMATCH,
            original_run_id=original_run.run_id,
            operator_result_id=candidate_operator_result.operator_result_id,
            candidate_attempt_id=attempt.attempt_id,
        )

    if not _valid_spans(attempt.evidence_spans):
        return _refusal(
            reason=RunAttemptBindingRefusalReason.MALFORMED_EVIDENCE_SPAN,
            original_run_id=original_run.run_id,
            operator_result_id=candidate_operator_result.operator_result_id,
            candidate_attempt_id=attempt.attempt_id,
        )
    if candidate_operator_result.evidence_spans != attempt.evidence_spans:
        return _refusal(
            reason=RunAttemptBindingRefusalReason.MALFORMED_EVIDENCE_SPAN,
            original_run_id=original_run.run_id,
            operator_result_id=candidate_operator_result.operator_result_id,
            candidate_attempt_id=attempt.attempt_id,
        )
    if reconstruction.evidence_spans != attempt.evidence_spans:
        return _refusal(
            reason=RunAttemptBindingRefusalReason.MALFORMED_EVIDENCE_SPAN,
            original_run_id=original_run.run_id,
            operator_result_id=candidate_operator_result.operator_result_id,
            candidate_attempt_id=attempt.attempt_id,
        )

    for existing in original_run.candidate_attempts:
        if existing.attempt_index == attempt.attempt_index:
            return _refusal(
                reason=RunAttemptBindingRefusalReason.DUPLICATE_ATTEMPT_INDEX,
                original_run_id=original_run.run_id,
                operator_result_id=candidate_operator_result.operator_result_id,
                candidate_attempt_id=attempt.attempt_id,
            )
        if existing.attempt_id == attempt.attempt_id:
            return _refusal(
                reason=RunAttemptBindingRefusalReason.DUPLICATE_ATTEMPT_ID,
                original_run_id=original_run.run_id,
                operator_result_id=candidate_operator_result.operator_result_id,
                candidate_attempt_id=attempt.attempt_id,
            )
        if existing.candidate_digest == attempt.candidate_digest:
            return _refusal(
                reason=RunAttemptBindingRefusalReason.DUPLICATE_CANDIDATE_DIGEST,
                original_run_id=original_run.run_id,
                operator_result_id=candidate_operator_result.operator_result_id,
                candidate_attempt_id=attempt.attempt_id,
            )

    consumed = original_run.budget_consumed
    charge = attempt.budget_charge
    if charge.candidates < 0 or charge.steps < 0 or attempt.depth < 0:
        return _refusal(
            reason=RunAttemptBindingRefusalReason.BUDGET_CHARGE_EXCEEDS_REMAINING,
            original_run_id=original_run.run_id,
            operator_result_id=candidate_operator_result.operator_result_id,
            candidate_attempt_id=attempt.attempt_id,
        )
    if attempt.step_index < 0:
        return _refusal(
            reason=RunAttemptBindingRefusalReason.BUDGET_CHARGE_EXCEEDS_REMAINING,
            original_run_id=original_run.run_id,
            operator_result_id=candidate_operator_result.operator_result_id,
            candidate_attempt_id=attempt.attempt_id,
        )
    if consumed.candidates_considered + charge.candidates > consumed.max_candidates:
        return _refusal(
            reason=RunAttemptBindingRefusalReason.BUDGET_CHARGE_EXCEEDS_REMAINING,
            original_run_id=original_run.run_id,
            operator_result_id=candidate_operator_result.operator_result_id,
            candidate_attempt_id=attempt.attempt_id,
        )
    if consumed.steps_used + charge.steps > consumed.max_steps:
        return _refusal(
            reason=RunAttemptBindingRefusalReason.BUDGET_CHARGE_EXCEEDS_REMAINING,
            original_run_id=original_run.run_id,
            operator_result_id=candidate_operator_result.operator_result_id,
            candidate_attempt_id=attempt.attempt_id,
        )
    if max(consumed.depth_reached, attempt.depth) > consumed.max_depth:
        return _refusal(
            reason=RunAttemptBindingRefusalReason.BUDGET_CHARGE_EXCEEDS_REMAINING,
            original_run_id=original_run.run_id,
            operator_result_id=candidate_operator_result.operator_result_id,
            candidate_attempt_id=attempt.attempt_id,
        )
    if consumed.parallelism_used > consumed.max_parallelism:
        return _refusal(
            reason=RunAttemptBindingRefusalReason.BUDGET_CHARGE_EXCEEDS_REMAINING,
            original_run_id=original_run.run_id,
            operator_result_id=candidate_operator_result.operator_result_id,
            candidate_attempt_id=attempt.attempt_id,
        )

    input_payload = _binding_input_payload(
        original_run=original_run,
        candidate_operator_result=candidate_operator_result,
        schema_versions=schema_versions,
        policy_versions=policy_versions,
    )
    input_digest = _canonical_digest(input_payload)
    binding_input = CandidateAttemptRunBindingInput(
        input_digest=input_digest,
        residual_ids=original_run.residual_ids,
        schema_versions=schema_versions,
        policy_versions=policy_versions,
        **{
            key: value
            for key, value in input_payload.items()
            if key not in {"residual_ids", "schema_versions", "policy_versions"}
        },
    )
    candidate_attempt_ref = _canonical_digest(_candidate_attempt_payload(attempt))
    binding_id = _canonical_digest(
        _binding_id_payload(
            input_digest=binding_input.input_digest,
            original_run_id=original_run.run_id,
            operator_result_id=candidate_operator_result.operator_result_id,
            candidate_attempt_id=attempt.attempt_id,
            attempt_index=attempt.attempt_index,
            candidate_digest=attempt.candidate_digest,
            candidate_reconstruction_digest=reconstruction.candidate_reconstruction_digest,
            candidate_attempt_ref=candidate_attempt_ref,
            budget_charge=charge,
            depth=attempt.depth,
            step_index=attempt.step_index,
            evidence_spans=attempt.evidence_spans,
        )
    )
    return CandidateAttemptRunBinding(
        binding_id=binding_id,
        binding_policy_version=CANDIDATE_ATTEMPT_RUN_BINDING_POLICY_VERSION,
        input_digest=binding_input.input_digest,
        original_run_id=original_run.run_id,
        operator_result_id=candidate_operator_result.operator_result_id,
        candidate_attempt_id=attempt.attempt_id,
        attempt_index=attempt.attempt_index,
        candidate_digest=attempt.candidate_digest,
        candidate_reconstruction_digest=reconstruction.candidate_reconstruction_digest,
        candidate_attempt_ref=candidate_attempt_ref,
        budget_charge=charge,
        depth=attempt.depth,
        step_index=attempt.step_index,
        run_attempt_membership="structurally_bound",
        evidence_spans=attempt.evidence_spans,
        reason_codes=(),
        explanation=explanation
        or "CandidateAttempt structurally bound to GeometricSearchRun.",
    )


__all__ = [
    "CANDIDATE_ATTEMPT_RUN_BINDING_POLICY_VERSION",
    "RunAttemptBindingRefusalReason",
    "CandidateAttemptRunBindingInput",
    "CandidateAttemptRunBinding",
    "CandidateAttemptRunBindingRefusal",
    "CandidateAttemptRunBindingOutcome",
    "bind_candidate_attempt_to_run",
]
