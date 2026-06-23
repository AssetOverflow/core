"""Diagnostic-only contract/proof replay adapter shell over one candidate attempt."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum, unique

from generate.candidate_operator import CandidateOperatorResult
from generate.geometric_search_run import CandidateAttempt, GeometricSearchRun
from generate.kernel_facts import SourceSpan
from generate.run_attempt_binding import CandidateAttemptRunBinding

CONTRACT_PROOF_REPLAY_POLICY_VERSION = "contract_proof_replay.v1"
REPLAY_ADAPTER_POLICY_VERSION = CONTRACT_PROOF_REPLAY_POLICY_VERSION

_CONTRACT_REPLAY_TARGET_ALLOWLIST: dict[str, str] = {
    "unary_delta_transition": "problem_frame_contracts.unary_delta",
    "fraction_decrease": "problem_frame_contracts.fraction_decrease",
    "percent_partition": "problem_frame_contracts.percent_partition",
}

VACUOUS_PROOF_DECLARATION: tuple[str, str] = (
    "proof_obligations",
    "none_applicable.v1",
)


@unique
class ReplayDisposition(str, Enum):
    CONTRACT_REFUSED = "contract_refused"
    CONTRACT_CLOSED_BUT_PROOF_REFUSED = "contract_closed_but_proof_refused"
    CONTRACT_AND_PROOF_CLOSED = "contract_and_proof_closed"


@unique
class ReplayRefusalReason(str, Enum):
    INVALID_REPLAY_INPUT = "invalid_replay_input"
    CANDIDATE_IDENTITY_MISMATCH = "candidate_identity_mismatch"
    CONTRACT_REPLAY_UNAVAILABLE = "contract_replay_unavailable"
    PROOF_REPLAY_UNAVAILABLE = "proof_replay_unavailable"
    UNSUPPORTED_REPLAY_POLICY = "unsupported_replay_policy"
    UNSUPPORTED_SCHEMA_VERSION = "unsupported_schema_version"
    UNSUPPORTED_PROOF_OBLIGATION = "unsupported_proof_obligation"


@dataclass(frozen=True, slots=True)
class ProofReplayRef:
    proof_obligation_id: str
    proof_obligation_version: str
    proof_replay_id: str
    closed: bool
    reason_code: str


@dataclass(frozen=True, slots=True)
class ReplayAdapterInput:
    input_digest: str
    replay_policy_version: str
    run_id: str
    run_policy_version: str
    attempt_id: str
    attempt_index: int
    candidate_digest: str
    candidate_reconstruction_digest: str
    problem_frame_digest: str
    original_contract_assessment_id: str
    candidate_organ: str
    residual_ids: tuple[str, ...]
    gate_decision_id: str
    budget_id: str
    operator_set_id: str
    operator_set_version: str
    contract_replay_target: str
    proof_obligation_refs: tuple[str, ...]
    schema_versions: tuple[tuple[str, str], ...]


@dataclass(frozen=True, slots=True)
class ReplayAdapterResult:
    replay_result_id: str
    replay_policy_version: str
    input_digest: str
    run_id: str
    attempt_id: str
    candidate_digest: str
    contract_replay_assessment_id: str
    proof_obligation_refs: tuple[str, ...]
    proof_replay_refs: tuple[ProofReplayRef, ...]
    replay_disposition: ReplayDisposition
    reason_codes: tuple[str, ...]
    evidence_spans: tuple[SourceSpan, ...]
    explanation: str


@dataclass(frozen=True, slots=True)
class ReplayAdapterRefusal:
    replay_refusal_id: str
    replay_policy_version: str
    input_digest: str | None
    run_id: str | None
    attempt_id: str | None
    candidate_digest: str | None
    replay_disposition: ReplayRefusalReason
    reason_codes: tuple[str, ...]
    explanation: str


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


def _text_or_none(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


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


def _proof_ref_payload(ref: ProofReplayRef) -> dict[str, object]:
    return {
        "proof_obligation_id": ref.proof_obligation_id,
        "proof_obligation_version": ref.proof_obligation_version,
        "proof_replay_id": ref.proof_replay_id,
        "closed": ref.closed,
        "reason_code": ref.reason_code,
    }


def _valid_proof_ref(ref: object) -> bool:
    if not isinstance(ref, ProofReplayRef):
        return False
    return (
        _nonempty_text(ref.proof_obligation_id)
        and _nonempty_text(ref.proof_obligation_version)
        and _nonempty_text(ref.proof_replay_id)
        and type(ref.closed) is bool
        and isinstance(ref.reason_code, str)
    )


def _valid_proof_refs(value: object) -> bool:
    return isinstance(value, tuple) and all(_valid_proof_ref(ref) for ref in value)


def _valid_string_tuple(value: object) -> bool:
    return isinstance(value, tuple) and all(_nonempty_text(item) for item in value)


def _schema_versions_payload(
    schema_versions: tuple[tuple[str, str], ...],
) -> list[list[str]]:
    return [[name, version] for name, version in schema_versions]


def _valid_schema_versions(value: object) -> bool:
    if not isinstance(value, tuple):
        return False
    if not value:
        return True
    names: list[str] = []
    for entry in value:
        if not isinstance(entry, tuple) or len(entry) != 2:
            return False
        name, version = entry
        if not _nonempty_text(name) or not _nonempty_text(version):
            return False
        names.append(name)
    if len(names) != len(set(names)):
        return False
    return names == sorted(names)


def _vacuous_proof_declared(schema_versions: tuple[tuple[str, str], ...]) -> bool:
    return VACUOUS_PROOF_DECLARATION in schema_versions


def _contract_replay_target(candidate_organ: str) -> str | None:
    return _CONTRACT_REPLAY_TARGET_ALLOWLIST.get(candidate_organ)


def _input_payload(
    *,
    replay_policy_version: str,
    run_id: str,
    run_policy_version: str,
    attempt_id: str,
    attempt_index: int,
    candidate_digest: str,
    candidate_reconstruction_digest: str,
    problem_frame_digest: str,
    original_contract_assessment_id: str,
    candidate_organ: str,
    residual_ids: tuple[str, ...],
    gate_decision_id: str,
    budget_id: str,
    operator_set_id: str,
    operator_set_version: str,
    contract_replay_target: str,
    proof_obligation_refs: tuple[str, ...],
    schema_versions: tuple[tuple[str, str], ...],
) -> dict[str, object]:
    return {
        "replay_policy_version": replay_policy_version,
        "run_id": run_id,
        "run_policy_version": run_policy_version,
        "attempt_id": attempt_id,
        "attempt_index": attempt_index,
        "candidate_digest": candidate_digest,
        "candidate_reconstruction_digest": candidate_reconstruction_digest,
        "problem_frame_digest": problem_frame_digest,
        "original_contract_assessment_id": original_contract_assessment_id,
        "candidate_organ": candidate_organ,
        "residual_ids": list(residual_ids),
        "gate_decision_id": gate_decision_id,
        "budget_id": budget_id,
        "operator_set_id": operator_set_id,
        "operator_set_version": operator_set_version,
        "contract_replay_target": contract_replay_target,
        "proof_obligation_refs": list(proof_obligation_refs),
        "schema_versions": _schema_versions_payload(schema_versions),
    }


def _refusal(
    *,
    replay_policy_version: str = CONTRACT_PROOF_REPLAY_POLICY_VERSION,
    input_digest: str | None,
    run_id: str | None,
    attempt_id: str | None,
    candidate_digest: str | None,
    replay_disposition: ReplayRefusalReason,
    reason_codes: tuple[str, ...],
) -> ReplayAdapterRefusal:
    replay_refusal_id = _canonical_digest(
        {
            "replay_refusal_id": "",
            "replay_policy_version": replay_policy_version,
            "input_digest": input_digest,
            "run_id": run_id,
            "attempt_id": attempt_id,
            "candidate_digest": candidate_digest,
            "replay_disposition": replay_disposition.value,
            "reason_codes": list(reason_codes),
        }
    )
    return ReplayAdapterRefusal(
        replay_refusal_id=replay_refusal_id,
        replay_policy_version=replay_policy_version,
        input_digest=input_digest,
        run_id=run_id,
        attempt_id=attempt_id,
        candidate_digest=candidate_digest,
        replay_disposition=replay_disposition,
        reason_codes=reason_codes,
        explanation="Replay adapter refused: "
        + replay_disposition.value
        + " ("
        + ", ".join(reason_codes)
        + ").",
    )


def _replay_input(
    *,
    replay_policy_version: str,
    run: GeometricSearchRun,
    attempt: CandidateAttempt,
    candidate_digest: str,
    candidate_reconstruction_digest: str,
    candidate_organ: str,
    contract_replay_target: str,
    proof_obligation_refs: tuple[str, ...],
    schema_versions: tuple[tuple[str, str], ...],
) -> ReplayAdapterInput:
    input_digest = _canonical_digest(
        _input_payload(
            replay_policy_version=replay_policy_version,
            run_id=run.run_id,
            run_policy_version=run.run_policy_version,
            attempt_id=attempt.attempt_id,
            attempt_index=attempt.attempt_index,
            candidate_digest=candidate_digest,
            candidate_reconstruction_digest=candidate_reconstruction_digest,
            problem_frame_digest=run.problem_frame_digest,
            original_contract_assessment_id=run.contract_assessment_id,
            candidate_organ=candidate_organ,
            residual_ids=run.residual_ids,
            gate_decision_id=run.gate_decision_id,
            budget_id=run.budget_id,
            operator_set_id=run.operator_set_id,
            operator_set_version=run.operator_set_version,
            contract_replay_target=contract_replay_target,
            proof_obligation_refs=proof_obligation_refs,
            schema_versions=schema_versions,
        )
    )
    return ReplayAdapterInput(
        input_digest=input_digest,
        replay_policy_version=replay_policy_version,
        run_id=run.run_id,
        run_policy_version=run.run_policy_version,
        attempt_id=attempt.attempt_id,
        attempt_index=attempt.attempt_index,
        candidate_digest=candidate_digest,
        candidate_reconstruction_digest=candidate_reconstruction_digest,
        problem_frame_digest=run.problem_frame_digest,
        original_contract_assessment_id=run.contract_assessment_id,
        candidate_organ=candidate_organ,
        residual_ids=run.residual_ids,
        gate_decision_id=run.gate_decision_id,
        budget_id=run.budget_id,
        operator_set_id=run.operator_set_id,
        operator_set_version=run.operator_set_version,
        contract_replay_target=contract_replay_target,
        proof_obligation_refs=proof_obligation_refs,
        schema_versions=schema_versions,
    )


def build_replay_adapter_input(
    *,
    run: GeometricSearchRun,
    attempt: CandidateAttempt,
    candidate_digest: str,
    candidate_reconstruction_digest: str,
    problem_frame_digest: str,
    original_contract_assessment_id: str,
    candidate_organ: str,
    proof_obligation_refs: tuple[str, ...] = (),
    schema_versions: tuple[tuple[str, str], ...] = (),
    replay_policy_version: str = CONTRACT_PROOF_REPLAY_POLICY_VERSION,
) -> ReplayAdapterInput | ReplayAdapterRefusal:
    """Validate run/attempt identity and emit a replay input or refusal."""

    safe_run_id = _text_or_none(_safe_getattr(run, "run_id"))
    safe_attempt_id = _text_or_none(_safe_getattr(attempt, "attempt_id"))
    safe_candidate_digest = _text_or_none(candidate_digest)

    if not isinstance(run, GeometricSearchRun):
        return _refusal(
            input_digest=None,
            run_id=safe_run_id,
            attempt_id=safe_attempt_id,
            candidate_digest=safe_candidate_digest,
            replay_disposition=ReplayRefusalReason.INVALID_REPLAY_INPUT,
            reason_codes=("invalid_run_type",),
        )
    if not isinstance(attempt, CandidateAttempt):
        return _refusal(
            input_digest=None,
            run_id=run.run_id,
            attempt_id=safe_attempt_id,
            candidate_digest=safe_candidate_digest,
            replay_disposition=ReplayRefusalReason.INVALID_REPLAY_INPUT,
            reason_codes=("invalid_attempt_type",),
        )

    if replay_policy_version != CONTRACT_PROOF_REPLAY_POLICY_VERSION:
        return _refusal(
            input_digest=None,
            run_id=run.run_id,
            attempt_id=attempt.attempt_id,
            candidate_digest=safe_candidate_digest,
            replay_policy_version=replay_policy_version,
            replay_disposition=ReplayRefusalReason.UNSUPPORTED_REPLAY_POLICY,
            reason_codes=("unsupported_replay_policy_version",),
        )

    reasons: list[str] = []

    if not _nonempty_text(run.run_id):
        reasons.append("missing_run_id")
    if not _nonempty_text(attempt.attempt_id):
        reasons.append("missing_attempt_id")
    if not _nonempty_text(candidate_digest):
        reasons.append("missing_candidate_digest")
    elif attempt.candidate_digest != candidate_digest:
        reasons.append("candidate_digest_mismatch")
    if not _nonempty_text(candidate_reconstruction_digest):
        reasons.append("missing_candidate_reconstruction_digest")
    if not _nonempty_text(problem_frame_digest):
        reasons.append("missing_problem_frame_digest")
    if not _nonempty_text(original_contract_assessment_id):
        reasons.append("missing_original_contract_assessment_id")
    if not _nonempty_text(candidate_organ):
        reasons.append("missing_candidate_organ")

    contract_replay_target = _contract_replay_target(candidate_organ)
    if contract_replay_target is None:
        reasons.append("unsupported_candidate_organ")

    if proof_obligation_refs and not _valid_string_tuple(proof_obligation_refs):
        reasons.append("invalid_proof_obligation_refs")
    if not _valid_schema_versions(schema_versions):
        reasons.append("unsupported_schema_version")

    attempts = run.candidate_attempts
    if not isinstance(attempts, tuple):
        reasons.append("invalid_candidate_attempts")

    matching_ids = [
        record
        for record in attempts
        if isinstance(record, CandidateAttempt)
        and record.attempt_id == attempt.attempt_id
    ]
    if len(matching_ids) != 1:
        reasons.append("ambiguous_or_missing_attempt_id")
    if attempt not in attempts:
        reasons.append("attempt_not_in_run")

    attempt_index = _safe_getattr(attempt, "attempt_index")
    if type(attempt_index) is not int or attempt_index < 0:
        reasons.append("invalid_attempt_index")
    elif not reasons and attempt_index >= len(attempts):
        reasons.append("attempt_index_out_of_range")
    elif not reasons and attempts[attempt_index] is not attempt:
        reasons.append("attempt_index_mismatch")

    if not reasons:
        if attempt.input_digest != run.input_digest:
            reasons.append("attempt_input_digest_mismatch")
        if problem_frame_digest != run.problem_frame_digest:
            reasons.append("problem_frame_digest_mismatch")
        if original_contract_assessment_id != run.contract_assessment_id:
            reasons.append("original_contract_assessment_id_mismatch")

    identity_mismatch_codes = {
        "candidate_digest_mismatch",
        "ambiguous_or_missing_attempt_id",
        "attempt_not_in_run",
        "attempt_index_mismatch",
        "attempt_index_out_of_range",
        "attempt_input_digest_mismatch",
        "problem_frame_digest_mismatch",
        "original_contract_assessment_id_mismatch",
    }
    if "unsupported_schema_version" in reasons:
        refusal_disposition = ReplayRefusalReason.UNSUPPORTED_SCHEMA_VERSION
    elif any(code in identity_mismatch_codes for code in reasons):
        refusal_disposition = ReplayRefusalReason.CANDIDATE_IDENTITY_MISMATCH
    else:
        refusal_disposition = ReplayRefusalReason.INVALID_REPLAY_INPUT

    if reasons:
        return _refusal(
            input_digest=None,
            run_id=run.run_id if _nonempty_text(run.run_id) else None,
            attempt_id=attempt.attempt_id if _nonempty_text(attempt.attempt_id) else None,
            candidate_digest=candidate_digest if _nonempty_text(candidate_digest) else None,
            replay_disposition=refusal_disposition,
            reason_codes=tuple(reasons),
        )

    assert isinstance(attempt_index, int)
    assert contract_replay_target is not None
    return _replay_input(
        replay_policy_version=replay_policy_version,
        run=run,
        attempt=attempt,
        candidate_digest=candidate_digest,
        candidate_reconstruction_digest=candidate_reconstruction_digest,
        candidate_organ=candidate_organ,
        contract_replay_target=contract_replay_target,
        proof_obligation_refs=proof_obligation_refs,
        schema_versions=schema_versions,
    )


def _bound_refusal(
    *,
    run: GeometricSearchRun | None,
    binding: CandidateAttemptRunBinding | None,
    result: CandidateOperatorResult | None,
    replay_disposition: ReplayRefusalReason,
    reason_code: str,
    replay_policy_version: str = CONTRACT_PROOF_REPLAY_POLICY_VERSION,
) -> ReplayAdapterRefusal:
    return _refusal(
        replay_policy_version=replay_policy_version,
        input_digest=None,
        run_id=run.run_id if isinstance(run, GeometricSearchRun) else None,
        attempt_id=binding.candidate_attempt_id
        if isinstance(binding, CandidateAttemptRunBinding)
        else _text_or_none(_safe_getattr(result, "attempt_id")),
        candidate_digest=binding.candidate_digest
        if isinstance(binding, CandidateAttemptRunBinding)
        else _text_or_none(_safe_getattr(result, "candidate_digest")),
        replay_disposition=replay_disposition,
        reason_codes=(reason_code,),
    )


def build_replay_adapter_input_from_binding(
    *,
    run: GeometricSearchRun,
    binding: CandidateAttemptRunBinding,
    candidate_operator_result: CandidateOperatorResult,
    proof_obligation_refs: tuple[str, ...] = (),
    schema_versions: tuple[tuple[str, str], ...] = (),
    replay_policy_version: str = CONTRACT_PROOF_REPLAY_POLICY_VERSION,
) -> ReplayAdapterInput | ReplayAdapterRefusal:
    """Build replay input from external CandidateAttemptRunBinding evidence."""

    if not isinstance(run, GeometricSearchRun):
        return _bound_refusal(
            run=None,
            binding=None,
            result=None,
            replay_disposition=ReplayRefusalReason.INVALID_REPLAY_INPUT,
            reason_code="invalid_run_type",
            replay_policy_version=replay_policy_version,
        )
    if not isinstance(binding, CandidateAttemptRunBinding):
        return _bound_refusal(
            run=run,
            binding=None,
            result=None,
            replay_disposition=ReplayRefusalReason.INVALID_REPLAY_INPUT,
            reason_code="invalid_binding_type",
            replay_policy_version=replay_policy_version,
        )
    if not isinstance(candidate_operator_result, CandidateOperatorResult):
        return _bound_refusal(
            run=run,
            binding=binding,
            result=None,
            replay_disposition=ReplayRefusalReason.INVALID_REPLAY_INPUT,
            reason_code="invalid_operator_result_type",
            replay_policy_version=replay_policy_version,
        )
    if replay_policy_version != CONTRACT_PROOF_REPLAY_POLICY_VERSION:
        return _bound_refusal(
            run=run,
            binding=binding,
            result=candidate_operator_result,
            replay_disposition=ReplayRefusalReason.UNSUPPORTED_REPLAY_POLICY,
            reason_code="unsupported_replay_policy_version",
            replay_policy_version=replay_policy_version,
        )
    if proof_obligation_refs and not _valid_string_tuple(proof_obligation_refs):
        return _bound_refusal(
            run=run,
            binding=binding,
            result=candidate_operator_result,
            replay_disposition=ReplayRefusalReason.INVALID_REPLAY_INPUT,
            reason_code="invalid_proof_obligation_refs",
        )
    if not _valid_schema_versions(schema_versions):
        return _bound_refusal(
            run=run,
            binding=binding,
            result=candidate_operator_result,
            replay_disposition=ReplayRefusalReason.UNSUPPORTED_SCHEMA_VERSION,
            reason_code="unsupported_schema_version",
        )

    attempt = candidate_operator_result.candidate_attempt
    reconstruction = candidate_operator_result.candidate_reconstruction

    if binding.original_run_id != run.run_id:
        return _bound_refusal(
            run=run,
            binding=binding,
            result=candidate_operator_result,
            replay_disposition=ReplayRefusalReason.CANDIDATE_IDENTITY_MISMATCH,
            reason_code="binding_run_mismatch",
        )
    if binding.operator_result_id != candidate_operator_result.operator_result_id:
        return _bound_refusal(
            run=run,
            binding=binding,
            result=candidate_operator_result,
            replay_disposition=ReplayRefusalReason.CANDIDATE_IDENTITY_MISMATCH,
            reason_code="binding_result_mismatch",
        )
    if binding.run_attempt_membership != "structurally_bound":
        return _bound_refusal(
            run=run,
            binding=binding,
            result=candidate_operator_result,
            replay_disposition=ReplayRefusalReason.CANDIDATE_IDENTITY_MISMATCH,
            reason_code="binding_not_structurally_bound",
        )
    if binding.reason_codes != ():
        return _bound_refusal(
            run=run,
            binding=binding,
            result=candidate_operator_result,
            replay_disposition=ReplayRefusalReason.CANDIDATE_IDENTITY_MISMATCH,
            reason_code="binding_not_successful",
        )
    if not _nonempty_text(binding.candidate_attempt_ref):
        return _bound_refusal(
            run=run,
            binding=binding,
            result=candidate_operator_result,
            replay_disposition=ReplayRefusalReason.CANDIDATE_IDENTITY_MISMATCH,
            reason_code="binding_missing_attempt_ref",
        )
    if candidate_operator_result.geometric_search_run_id != run.run_id:
        return _bound_refusal(
            run=run,
            binding=binding,
            result=candidate_operator_result,
            replay_disposition=ReplayRefusalReason.CANDIDATE_IDENTITY_MISMATCH,
            reason_code="result_run_mismatch",
        )
    if binding.candidate_attempt_id != candidate_operator_result.attempt_id:
        return _bound_refusal(
            run=run,
            binding=binding,
            result=candidate_operator_result,
            replay_disposition=ReplayRefusalReason.CANDIDATE_IDENTITY_MISMATCH,
            reason_code="binding_result_mismatch",
        )
    if binding.candidate_attempt_id != attempt.attempt_id:
        return _bound_refusal(
            run=run,
            binding=binding,
            result=candidate_operator_result,
            replay_disposition=ReplayRefusalReason.CANDIDATE_IDENTITY_MISMATCH,
            reason_code="binding_attempt_mismatch",
        )
    if binding.attempt_index != candidate_operator_result.attempt_index:
        return _bound_refusal(
            run=run,
            binding=binding,
            result=candidate_operator_result,
            replay_disposition=ReplayRefusalReason.CANDIDATE_IDENTITY_MISMATCH,
            reason_code="binding_result_mismatch",
        )
    if binding.attempt_index != attempt.attempt_index:
        return _bound_refusal(
            run=run,
            binding=binding,
            result=candidate_operator_result,
            replay_disposition=ReplayRefusalReason.CANDIDATE_IDENTITY_MISMATCH,
            reason_code="binding_attempt_mismatch",
        )
    if binding.candidate_digest != candidate_operator_result.candidate_digest:
        return _bound_refusal(
            run=run,
            binding=binding,
            result=candidate_operator_result,
            replay_disposition=ReplayRefusalReason.CANDIDATE_IDENTITY_MISMATCH,
            reason_code="binding_result_mismatch",
        )
    if binding.candidate_digest != attempt.candidate_digest:
        return _bound_refusal(
            run=run,
            binding=binding,
            result=candidate_operator_result,
            replay_disposition=ReplayRefusalReason.CANDIDATE_IDENTITY_MISMATCH,
            reason_code="binding_attempt_mismatch",
        )
    if binding.candidate_reconstruction_digest != candidate_operator_result.candidate_reconstruction_digest:
        return _bound_refusal(
            run=run,
            binding=binding,
            result=candidate_operator_result,
            replay_disposition=ReplayRefusalReason.CANDIDATE_IDENTITY_MISMATCH,
            reason_code="binding_result_mismatch",
        )
    if binding.candidate_reconstruction_digest != reconstruction.candidate_reconstruction_digest:
        return _bound_refusal(
            run=run,
            binding=binding,
            result=candidate_operator_result,
            replay_disposition=ReplayRefusalReason.CANDIDATE_IDENTITY_MISMATCH,
            reason_code="binding_reconstruction_mismatch",
        )
    if attempt.input_digest != candidate_operator_result.input_digest:
        return _bound_refusal(
            run=run,
            binding=binding,
            result=candidate_operator_result,
            replay_disposition=ReplayRefusalReason.CANDIDATE_IDENTITY_MISMATCH,
            reason_code="attempt_input_digest_mismatch",
        )
    if binding.evidence_spans != candidate_operator_result.evidence_spans:
        return _bound_refusal(
            run=run,
            binding=binding,
            result=candidate_operator_result,
            replay_disposition=ReplayRefusalReason.CANDIDATE_IDENTITY_MISMATCH,
            reason_code="binding_evidence_mismatch",
        )
    if binding.evidence_spans != attempt.evidence_spans:
        return _bound_refusal(
            run=run,
            binding=binding,
            result=candidate_operator_result,
            replay_disposition=ReplayRefusalReason.CANDIDATE_IDENTITY_MISMATCH,
            reason_code="attempt_evidence_mismatch",
        )
    if binding.evidence_spans != reconstruction.evidence_spans:
        return _bound_refusal(
            run=run,
            binding=binding,
            result=candidate_operator_result,
            replay_disposition=ReplayRefusalReason.CANDIDATE_IDENTITY_MISMATCH,
            reason_code="reconstruction_evidence_mismatch",
        )
    if reconstruction.problem_frame_digest != run.problem_frame_digest:
        return _bound_refusal(
            run=run,
            binding=binding,
            result=candidate_operator_result,
            replay_disposition=ReplayRefusalReason.CANDIDATE_IDENTITY_MISMATCH,
            reason_code="reconstruction_problem_frame_mismatch",
        )
    if reconstruction.original_contract_assessment_id != run.contract_assessment_id:
        return _bound_refusal(
            run=run,
            binding=binding,
            result=candidate_operator_result,
            replay_disposition=ReplayRefusalReason.CANDIDATE_IDENTITY_MISMATCH,
            reason_code="reconstruction_assessment_mismatch",
        )
    if reconstruction.source_residual_id not in run.residual_ids:
        return _bound_refusal(
            run=run,
            binding=binding,
            result=candidate_operator_result,
            replay_disposition=ReplayRefusalReason.CANDIDATE_IDENTITY_MISMATCH,
            reason_code="reconstruction_residual_mismatch",
        )

    contract_replay_target = _contract_replay_target(candidate_operator_result.candidate_organ)
    if contract_replay_target is None:
        return _bound_refusal(
            run=run,
            binding=binding,
            result=candidate_operator_result,
            replay_disposition=ReplayRefusalReason.INVALID_REPLAY_INPUT,
            reason_code="unsupported_candidate_organ",
        )

    return _replay_input(
        replay_policy_version=replay_policy_version,
        run=run,
        attempt=attempt,
        candidate_digest=binding.candidate_digest,
        candidate_reconstruction_digest=binding.candidate_reconstruction_digest,
        candidate_organ=candidate_operator_result.candidate_organ,
        contract_replay_target=contract_replay_target,
        proof_obligation_refs=proof_obligation_refs,
        schema_versions=schema_versions,
    )


def classify_replay_result(
    replay_input: ReplayAdapterInput,
    *,
    contract_replay_assessment_id: str | None,
    contract_closed: bool | None,
    proof_replay_refs: tuple[ProofReplayRef, ...] = (),
    evidence_spans: tuple[SourceSpan, ...] = (),
    reason_codes: tuple[str, ...] = (),
    explanation: str = "",
) -> ReplayAdapterResult | ReplayAdapterRefusal:
    """Classify one candidate replay disposition from injected authority seams."""

    if not isinstance(replay_input, ReplayAdapterInput):
        return _refusal(
            input_digest=None,
            run_id=None,
            attempt_id=None,
            candidate_digest=None,
            replay_disposition=ReplayRefusalReason.INVALID_REPLAY_INPUT,
            reason_codes=("invalid_replay_input_type",),
        )

    if replay_input.replay_policy_version != CONTRACT_PROOF_REPLAY_POLICY_VERSION:
        return _refusal(
            input_digest=replay_input.input_digest,
            run_id=replay_input.run_id,
            attempt_id=replay_input.attempt_id,
            candidate_digest=replay_input.candidate_digest,
            replay_policy_version=replay_input.replay_policy_version,
            replay_disposition=ReplayRefusalReason.UNSUPPORTED_REPLAY_POLICY,
            reason_codes=("unsupported_replay_policy_version",),
        )

    if not _valid_spans(evidence_spans):
        return _refusal(
            input_digest=replay_input.input_digest,
            run_id=replay_input.run_id,
            attempt_id=replay_input.attempt_id,
            candidate_digest=replay_input.candidate_digest,
            replay_disposition=ReplayRefusalReason.INVALID_REPLAY_INPUT,
            reason_codes=("invalid_evidence_spans",),
        )

    if not all(isinstance(code, str) for code in reason_codes):
        return _refusal(
            input_digest=replay_input.input_digest,
            run_id=replay_input.run_id,
            attempt_id=replay_input.attempt_id,
            candidate_digest=replay_input.candidate_digest,
            replay_disposition=ReplayRefusalReason.INVALID_REPLAY_INPUT,
            reason_codes=("invalid_reason_codes",),
        )

    if contract_replay_assessment_id is None or contract_closed is None:
        return _refusal(
            input_digest=replay_input.input_digest,
            run_id=replay_input.run_id,
            attempt_id=replay_input.attempt_id,
            candidate_digest=replay_input.candidate_digest,
            replay_disposition=ReplayRefusalReason.CONTRACT_REPLAY_UNAVAILABLE,
            reason_codes=("contract_replay_unavailable",),
        )

    if not _nonempty_text(contract_replay_assessment_id):
        return _refusal(
            input_digest=replay_input.input_digest,
            run_id=replay_input.run_id,
            attempt_id=replay_input.attempt_id,
            candidate_digest=replay_input.candidate_digest,
            replay_disposition=ReplayRefusalReason.CONTRACT_REPLAY_UNAVAILABLE,
            reason_codes=("invalid_contract_replay_assessment_id",),
        )

    if proof_replay_refs and not _valid_proof_refs(proof_replay_refs):
        return _refusal(
            input_digest=replay_input.input_digest,
            run_id=replay_input.run_id,
            attempt_id=replay_input.attempt_id,
            candidate_digest=replay_input.candidate_digest,
            replay_disposition=ReplayRefusalReason.INVALID_REPLAY_INPUT,
            reason_codes=("invalid_proof_replay_refs",),
        )

    if contract_closed is False:
        return _result(
            replay_input=replay_input,
            contract_replay_assessment_id=contract_replay_assessment_id,
            proof_replay_refs=(),
            replay_disposition=ReplayDisposition.CONTRACT_REFUSED,
            reason_codes=reason_codes,
            evidence_spans=evidence_spans,
            explanation=explanation,
        )

    obligations = replay_input.proof_obligation_refs
    if not obligations:
        if _vacuous_proof_declared(replay_input.schema_versions):
            return _result(
                replay_input=replay_input,
                contract_replay_assessment_id=contract_replay_assessment_id,
                proof_replay_refs=(),
                replay_disposition=ReplayDisposition.CONTRACT_AND_PROOF_CLOSED,
                reason_codes=reason_codes,
                evidence_spans=evidence_spans,
                explanation=explanation,
            )
        return _refusal(
            input_digest=replay_input.input_digest,
            run_id=replay_input.run_id,
            attempt_id=replay_input.attempt_id,
            candidate_digest=replay_input.candidate_digest,
            replay_disposition=ReplayRefusalReason.PROOF_REPLAY_UNAVAILABLE,
            reason_codes=("proof_replay_unavailable",),
        )

    if not proof_replay_refs:
        return _result(
            replay_input=replay_input,
            contract_replay_assessment_id=contract_replay_assessment_id,
            proof_replay_refs=(),
            replay_disposition=ReplayDisposition.CONTRACT_CLOSED_BUT_PROOF_REFUSED,
            reason_codes=reason_codes or ("missing_proof_replay_refs",),
            evidence_spans=evidence_spans,
            explanation=explanation,
        )

    if len(proof_replay_refs) != len(obligations):
        return _result(
            replay_input=replay_input,
            contract_replay_assessment_id=contract_replay_assessment_id,
            proof_replay_refs=proof_replay_refs,
            replay_disposition=ReplayDisposition.CONTRACT_CLOSED_BUT_PROOF_REFUSED,
            reason_codes=reason_codes or ("proof_replay_ref_count_mismatch",),
            evidence_spans=evidence_spans,
            explanation=explanation,
        )

    for index, obligation_id in enumerate(obligations):
        if proof_replay_refs[index].proof_obligation_id != obligation_id:
            return _refusal(
                input_digest=replay_input.input_digest,
                run_id=replay_input.run_id,
                attempt_id=replay_input.attempt_id,
                candidate_digest=replay_input.candidate_digest,
                replay_disposition=ReplayRefusalReason.UNSUPPORTED_PROOF_OBLIGATION,
                reason_codes=("unsupported_proof_obligation",),
            )

    if any(not ref.closed for ref in proof_replay_refs):
        return _result(
            replay_input=replay_input,
            contract_replay_assessment_id=contract_replay_assessment_id,
            proof_replay_refs=proof_replay_refs,
            replay_disposition=ReplayDisposition.CONTRACT_CLOSED_BUT_PROOF_REFUSED,
            reason_codes=reason_codes or ("proof_not_closed",),
            evidence_spans=evidence_spans,
            explanation=explanation,
        )

    return _result(
        replay_input=replay_input,
        contract_replay_assessment_id=contract_replay_assessment_id,
        proof_replay_refs=proof_replay_refs,
        replay_disposition=ReplayDisposition.CONTRACT_AND_PROOF_CLOSED,
        reason_codes=reason_codes,
        evidence_spans=evidence_spans,
        explanation=explanation,
    )


def _result(
    *,
    replay_input: ReplayAdapterInput,
    contract_replay_assessment_id: str,
    proof_replay_refs: tuple[ProofReplayRef, ...],
    replay_disposition: ReplayDisposition,
    reason_codes: tuple[str, ...],
    evidence_spans: tuple[SourceSpan, ...],
    explanation: str,
) -> ReplayAdapterResult:
    result_payload = {
        "replay_result_id": "",
        "replay_policy_version": replay_input.replay_policy_version,
        "input_digest": replay_input.input_digest,
        "run_id": replay_input.run_id,
        "attempt_id": replay_input.attempt_id,
        "candidate_digest": replay_input.candidate_digest,
        "contract_replay_assessment_id": contract_replay_assessment_id,
        "proof_obligation_refs": list(replay_input.proof_obligation_refs),
        "proof_replay_refs": [_proof_ref_payload(ref) for ref in proof_replay_refs],
        "replay_disposition": replay_disposition.value,
        "reason_codes": list(reason_codes),
        "evidence_spans": [_span_payload(span) for span in evidence_spans],
    }
    replay_result_id = _canonical_digest(result_payload)
    safe_explanation = explanation or (
        "Replay adapter classified candidate as " + replay_disposition.value + "."
    )
    return ReplayAdapterResult(
        replay_result_id=replay_result_id,
        replay_policy_version=replay_input.replay_policy_version,
        input_digest=replay_input.input_digest,
        run_id=replay_input.run_id,
        attempt_id=replay_input.attempt_id,
        candidate_digest=replay_input.candidate_digest,
        contract_replay_assessment_id=contract_replay_assessment_id,
        proof_obligation_refs=replay_input.proof_obligation_refs,
        proof_replay_refs=proof_replay_refs,
        replay_disposition=replay_disposition,
        reason_codes=reason_codes,
        evidence_spans=evidence_spans,
        explanation=safe_explanation,
    )


__all__ = [
    "CONTRACT_PROOF_REPLAY_POLICY_VERSION",
    "REPLAY_ADAPTER_POLICY_VERSION",
    "VACUOUS_PROOF_DECLARATION",
    "ReplayDisposition",
    "ReplayRefusalReason",
    "ProofReplayRef",
    "ReplayAdapterInput",
    "ReplayAdapterResult",
    "ReplayAdapterRefusal",
    "build_replay_adapter_input",
    "classify_replay_result",
]
