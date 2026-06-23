"""Inert, diagnostic-only missing-role candidate operator shell."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum, unique

from generate.compute_budget import ComputeBudgetDecision, ComputeBudgetStatus
from generate.geometric_search_run import (
    BudgetCharge,
    CandidateAttempt,
    CandidateReplayStatus,
    GeometricSearchRun,
)
from generate.kernel_facts import SourceSpan
from generate.search_gate import SearchGateDecision, SearchGateStatus

CANDIDATE_OPERATOR_POLICY_VERSION = "candidate_operator.v1"
CANDIDATE_OPERATOR_SET_VERSION = "candidate_operators.v2"

MISSING_ROLE_CANDIDATE_OPERATOR_NAME = "missing_role_candidate"
MISSING_ROLE_CANDIDATE_OPERATOR_VERSION = "missing_role_candidate.v1"

MISSING_ROLE_RESIDUAL_KIND = "missing_role"
MISSING_ROLE_RESIDUAL_CODE = "direction_unbound"
MISSING_ROLE_CANDIDATE_ORGAN = "unary_delta_transition"

QUANTITY_ENTITY_BINDING_CANDIDATE_OPERATOR_NAME = "quantity_entity_binding_candidate"
QUANTITY_ENTITY_BINDING_CANDIDATE_OPERATOR_VERSION = "quantity_entity_binding_candidate.v1"
QUANTITY_ENTITY_BINDING_RESIDUAL_KIND = "missing_relation"
QUANTITY_ENTITY_BINDING_RESIDUAL_CODE = "local_binding_relation_unbound"
QUANTITY_ENTITY_BINDING_CANDIDATE_ORGAN = "quantity_entity_binding"

_OPERATOR_FAMILY = "residual_missing_role"
_SUPPORTED_DIRECTIONS = frozenset({"increase", "decrease"})
_FIXED_BUDGET_CHARGE = BudgetCharge(candidates=1, steps=1)
_OPERATOR_DEPTH = 1
_OPERATOR_MAX_PARALLELISM = 1
_DETERMINISM_REQUIREMENTS = (
    "canonical_json_sha256",
    "static_operator_table",
    "no_source_reread",
    "no_stochastic_generation",
)
_FORBIDDEN_AUTHORITY_PATHS = (
    "answer_production",
    "contract_replay",
    "proof_replay",
    "sealed_trace",
    "serving",
    "mutation",
    "promotion",
    "workbench",
    "repair",
    "open_ended_search",
)


@unique
class CandidateOperatorRefusalReason(str, Enum):
    UNSUPPORTED_OPERATOR_POLICY = "unsupported_operator_policy"
    UNSUPPORTED_OPERATOR = "unsupported_operator"
    UNSUPPORTED_RESIDUAL_KIND = "unsupported_residual_kind"
    UNSUPPORTED_RESIDUAL_CODE = "unsupported_residual_code"
    UNSUPPORTED_CANDIDATE_ORGAN = "unsupported_candidate_organ"
    INELIGIBLE_SEARCH_GATE = "ineligible_search_gate"
    NON_ALLOWED_BUDGET = "non_allowed_budget"
    GATE_BUDGET_MISMATCH = "gate_budget_mismatch"
    RUN_GATE_MISMATCH = "run_gate_mismatch"
    RUN_BUDGET_MISMATCH = "run_budget_mismatch"
    OPERATOR_SET_MISMATCH = "operator_set_mismatch"
    ATTEMPT_INDEX_EXCEEDS_BUDGET = "attempt_index_exceeds_budget"
    ATTEMPT_INDEX_EXCEEDS_OPERATOR_POLICY = "attempt_index_exceeds_operator_policy"
    BUDGET_CHARGE_EXCEEDS_BUDGET = "budget_charge_exceeds_budget"
    NON_SERIAL_BUDGET = "non_serial_budget"
    MISSING_TYPED_CUE = "missing_typed_cue"
    AMBIGUOUS_TYPED_CUE = "ambiguous_typed_cue"
    UNSUPPORTED_TYPED_CUE = "unsupported_typed_cue"
    MALFORMED_EVIDENCE_SPAN = "malformed_evidence_span"
    INVALID_OPERATOR_INPUT = "invalid_operator_input"
    UNSUPPORTED_SCHEMA_VERSION = "unsupported_schema_version"
    INVALID_QUANTITY_ENTITY_CUE_TYPE = "invalid_quantity_entity_cue_type"
    QUANTITY_ENTITY_CUE_COUNT_MISMATCH = "quantity_entity_cue_count_mismatch"
    EMPTY_QUANTITY_MENTION_ID = "empty_quantity_mention_id"
    EMPTY_ENTITY_MENTION_ID = "empty_entity_mention_id"
    EMPTY_QUANTITY_KIND = "empty_quantity_kind"
    EMPTY_UNIT_MENTION_ID = "empty_unit_mention_id"
    MISSING_EVIDENCE_SPANS = "missing_evidence_spans"


@dataclass(frozen=True, slots=True)
class CandidateOperatorPolicy:
    operator_policy_version: str
    operator_family: str
    operator_name: str
    operator_version: str
    allowed_residual_kinds: tuple[str, ...]
    allowed_residual_codes: tuple[str, ...]
    allowed_candidate_organs: tuple[str, ...]
    max_attempts_per_run: int
    budget_charge: BudgetCharge
    depth: int
    max_parallelism: int
    determinism_requirements: tuple[str, ...]
    forbidden_authority_paths: tuple[str, ...]


MISSING_ROLE_OPERATOR_POLICY = CandidateOperatorPolicy(
    operator_policy_version=CANDIDATE_OPERATOR_POLICY_VERSION,
    operator_family=_OPERATOR_FAMILY,
    operator_name=MISSING_ROLE_CANDIDATE_OPERATOR_NAME,
    operator_version=MISSING_ROLE_CANDIDATE_OPERATOR_VERSION,
    allowed_residual_kinds=(MISSING_ROLE_RESIDUAL_KIND,),
    allowed_residual_codes=(MISSING_ROLE_RESIDUAL_CODE,),
    allowed_candidate_organs=(MISSING_ROLE_CANDIDATE_ORGAN,),
    max_attempts_per_run=1,
    budget_charge=_FIXED_BUDGET_CHARGE,
    depth=_OPERATOR_DEPTH,
    max_parallelism=_OPERATOR_MAX_PARALLELISM,
    determinism_requirements=_DETERMINISM_REQUIREMENTS,
    forbidden_authority_paths=_FORBIDDEN_AUTHORITY_PATHS,
)


QUANTITY_ENTITY_BINDING_OPERATOR_POLICY = CandidateOperatorPolicy(
    operator_policy_version=CANDIDATE_OPERATOR_POLICY_VERSION,
    operator_family="residual_missing_relation",
    operator_name=QUANTITY_ENTITY_BINDING_CANDIDATE_OPERATOR_NAME,
    operator_version=QUANTITY_ENTITY_BINDING_CANDIDATE_OPERATOR_VERSION,
    allowed_residual_kinds=(QUANTITY_ENTITY_BINDING_RESIDUAL_KIND,),
    allowed_residual_codes=(QUANTITY_ENTITY_BINDING_RESIDUAL_CODE,),
    allowed_candidate_organs=(QUANTITY_ENTITY_BINDING_CANDIDATE_ORGAN,),
    max_attempts_per_run=1,
    budget_charge=_FIXED_BUDGET_CHARGE,
    depth=_OPERATOR_DEPTH,
    max_parallelism=_OPERATOR_MAX_PARALLELISM,
    determinism_requirements=_DETERMINISM_REQUIREMENTS,
    forbidden_authority_paths=_FORBIDDEN_AUTHORITY_PATHS,
)


@dataclass(frozen=True, slots=True)
class GroundedUnaryDeltaCue:
    direction: str
    evidence_spans: tuple[SourceSpan, ...]


@dataclass(frozen=True, slots=True)
class GroundedQuantityEntityCue:
    quantity_mention_id: str
    entity_mention_id: str
    quantity_kind: str
    evidence_spans: tuple[SourceSpan, ...]
    unit_mention_id: str | None = None


@dataclass(frozen=True, slots=True)
class CandidateOperatorInput:
    input_digest: str
    operator_policy_version: str
    operator_name: str
    operator_version: str
    problem_frame_digest: str
    original_contract_assessment_id: str
    residual_id: str
    residual_kind: str
    residual_code: str
    candidate_organ: str
    search_gate_decision_id: str
    compute_budget_id: str
    geometric_search_run_id: str
    operator_set_id: str
    operator_set_version: str
    attempt_index: int
    schema_versions: tuple[tuple[str, str], ...]
    policy_versions: tuple[tuple[str, str], ...]


@dataclass(frozen=True, slots=True)
class CandidateReconstruction:
    candidate_digest: str
    candidate_reconstruction_digest: str
    candidate_organ: str
    candidate_payload: tuple[tuple[str, str], ...]
    evidence_spans: tuple[SourceSpan, ...]
    operator_name: str
    operator_version: str
    operator_provenance: tuple[tuple[str, str], ...]
    source_residual_id: str
    problem_frame_digest: str
    original_contract_assessment_id: str


@dataclass(frozen=True, slots=True)
class CandidateOperatorResult:
    operator_result_id: str
    operator_policy_version: str
    input_digest: str
    geometric_search_run_id: str
    attempt_id: str
    attempt_index: int
    candidate_digest: str
    candidate_reconstruction_digest: str
    candidate_organ: str
    operator_name: str
    operator_version: str
    candidate_attempt: CandidateAttempt
    candidate_reconstruction: CandidateReconstruction
    reason_codes: tuple[str, ...]
    evidence_spans: tuple[SourceSpan, ...]
    explanation: str


@dataclass(frozen=True, slots=True)
class CandidateOperatorRefusal:
    operator_refusal_id: str
    operator_policy_version: str
    input_digest: str | None
    geometric_search_run_id: str | None
    residual_id: str | None
    operator_name: str
    reason_codes: tuple[str, ...]
    explanation: str


CandidateOperatorOutcome = CandidateOperatorResult | CandidateOperatorRefusal


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


def _enum_value(value: object) -> object:
    return getattr(value, "value", value)


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


def _operator_set_table_payload() -> dict[str, object]:
    return {
        "operator_set_version": CANDIDATE_OPERATOR_SET_VERSION,
        "operators": [
            {
                "operator_family": MISSING_ROLE_OPERATOR_POLICY.operator_family,
                "operator_name": MISSING_ROLE_OPERATOR_POLICY.operator_name,
                "operator_version": MISSING_ROLE_OPERATOR_POLICY.operator_version,
                "allowed_residual_kinds": list(
                    MISSING_ROLE_OPERATOR_POLICY.allowed_residual_kinds
                ),
                "allowed_residual_codes": list(
                    MISSING_ROLE_OPERATOR_POLICY.allowed_residual_codes
                ),
                "allowed_candidate_organs": list(
                    MISSING_ROLE_OPERATOR_POLICY.allowed_candidate_organs
                ),
                "max_attempts_per_run": MISSING_ROLE_OPERATOR_POLICY.max_attempts_per_run,
                "budget_charge": {
                    "candidates": MISSING_ROLE_OPERATOR_POLICY.budget_charge.candidates,
                    "steps": MISSING_ROLE_OPERATOR_POLICY.budget_charge.steps,
                },
                "depth": MISSING_ROLE_OPERATOR_POLICY.depth,
                "max_parallelism": MISSING_ROLE_OPERATOR_POLICY.max_parallelism,
            },
            {
                "operator_family": QUANTITY_ENTITY_BINDING_OPERATOR_POLICY.operator_family,
                "operator_name": QUANTITY_ENTITY_BINDING_OPERATOR_POLICY.operator_name,
                "operator_version": QUANTITY_ENTITY_BINDING_OPERATOR_POLICY.operator_version,
                "allowed_residual_kinds": list(
                    QUANTITY_ENTITY_BINDING_OPERATOR_POLICY.allowed_residual_kinds
                ),
                "allowed_residual_codes": list(
                    QUANTITY_ENTITY_BINDING_OPERATOR_POLICY.allowed_residual_codes
                ),
                "allowed_candidate_organs": list(
                    QUANTITY_ENTITY_BINDING_OPERATOR_POLICY.allowed_candidate_organs
                ),
                "max_attempts_per_run": QUANTITY_ENTITY_BINDING_OPERATOR_POLICY.max_attempts_per_run,
                "budget_charge": {
                    "candidates": QUANTITY_ENTITY_BINDING_OPERATOR_POLICY.budget_charge.candidates,
                    "steps": QUANTITY_ENTITY_BINDING_OPERATOR_POLICY.budget_charge.steps,
                },
                "depth": QUANTITY_ENTITY_BINDING_OPERATOR_POLICY.depth,
                "max_parallelism": QUANTITY_ENTITY_BINDING_OPERATOR_POLICY.max_parallelism,
            },
        ],
        "schema_versions": [],
        "policy_versions": [],
    }


def candidate_operator_set_id() -> str:
    """Return the canonical digest of the closed one-row operator table."""
    return _canonical_digest(_operator_set_table_payload())


def _candidate_payload(direction: str) -> tuple[tuple[str, str], ...]:
    return (
        ("candidate_organ", MISSING_ROLE_CANDIDATE_ORGAN),
        ("direction", direction),
        ("kind", "role_binding_delta"),
        ("relation_type", "state_change.unary_delta"),
        ("role", "direction"),
        ("source", "GroundedUnaryDeltaCue.direction"),
    )


def _quantity_entity_binding_candidate_payload(
    cue: GroundedQuantityEntityCue,
) -> tuple[tuple[str, str], ...]:
    return (
        ("binding_type", "quantity_entity"),
        ("candidate_organ", QUANTITY_ENTITY_BINDING_CANDIDATE_ORGAN),
        ("entity_mention_id", cue.entity_mention_id),
        ("kind", "mention_binding"),
        ("quantity_kind", cue.quantity_kind),
        ("quantity_mention_id", cue.quantity_mention_id),
        ("relation_type", "quantity_entity"),
        ("source", "GroundedQuantityEntityCue"),
        ("unit_mention_id", cue.unit_mention_id or ""),
    )


def _candidate_payload_dict(
    payload: tuple[tuple[str, str], ...],
) -> list[list[str]]:
    return [[key, value] for key, value in payload]


def _candidate_digest_payload(
    *,
    problem_frame_digest: str,
    candidate_organ: str,
    candidate_payload: tuple[tuple[str, str], ...],
    evidence_spans: tuple[SourceSpan, ...],
) -> dict[str, object]:
    return {
        "problem_frame_digest": problem_frame_digest,
        "candidate_organ": candidate_organ,
        "candidate_payload": _candidate_payload_dict(candidate_payload),
        "evidence_spans": [_span_payload(span) for span in evidence_spans],
    }


def _input_digest_payload(
    *,
    operator_policy_version: str,
    operator_name: str,
    operator_version: str,
    problem_frame_digest: str,
    original_contract_assessment_id: str,
    residual_id: str,
    residual_kind: str,
    residual_code: str,
    candidate_organ: str,
    search_gate_decision_id: str,
    compute_budget_id: str,
    geometric_search_run_id: str,
    operator_set_id: str,
    operator_set_version: str,
    attempt_index: int,
    schema_versions: tuple[tuple[str, str], ...],
    policy_versions: tuple[tuple[str, str], ...],
) -> dict[str, object]:
    return {
        "operator_policy_version": operator_policy_version,
        "operator_name": operator_name,
        "operator_version": operator_version,
        "problem_frame_digest": problem_frame_digest,
        "original_contract_assessment_id": original_contract_assessment_id,
        "residual_id": residual_id,
        "residual_kind": residual_kind,
        "residual_code": residual_code,
        "candidate_organ": candidate_organ,
        "search_gate_decision_id": search_gate_decision_id,
        "compute_budget_id": compute_budget_id,
        "geometric_search_run_id": geometric_search_run_id,
        "operator_set_id": operator_set_id,
        "operator_set_version": operator_set_version,
        "attempt_index": attempt_index,
        "schema_versions": _version_pairs_payload(schema_versions),
        "policy_versions": _version_pairs_payload(policy_versions),
    }


def _attempt_id_payload(
    *,
    attempt_index: int,
    parent_attempt_id: str | None,
    operator_id: str,
    operator_version: str,
    input_digest: str,
    candidate_digest: str,
    budget_charge: BudgetCharge,
    depth: int,
    step_index: int,
    replay_status: CandidateReplayStatus,
    replay_blockers: tuple[str, ...],
    evidence_spans: tuple[SourceSpan, ...],
) -> dict[str, object]:
    return {
        "attempt_id": "",
        "attempt_index": attempt_index,
        "parent_attempt_id": parent_attempt_id,
        "operator_id": operator_id,
        "operator_version": operator_version,
        "input_digest": input_digest,
        "candidate_digest": candidate_digest,
        "budget_charge": {
            "candidates": budget_charge.candidates,
            "steps": budget_charge.steps,
        },
        "depth": depth,
        "step_index": step_index,
        "replay_status": replay_status.value,
        "replay_blockers": list(replay_blockers),
        "evidence_spans": [_span_payload(span) for span in evidence_spans],
    }


def _reconstruction_digest_payload(
    *,
    geometric_search_run_id: str,
    attempt_id: str,
    attempt_index: int,
    operator_set_id: str,
    operator_set_version: str,
    operator_name: str,
    operator_version: str,
    residual_id: str,
    residual_kind: str,
    residual_code: str,
    candidate_digest: str,
    evidence_spans: tuple[SourceSpan, ...],
    schema_versions: tuple[tuple[str, str], ...],
    policy_versions: tuple[tuple[str, str], ...],
) -> dict[str, object]:
    return {
        "candidate_reconstruction_digest": "",
        "geometric_search_run_id": geometric_search_run_id,
        "attempt_id": attempt_id,
        "attempt_index": attempt_index,
        "operator_set_id": operator_set_id,
        "operator_set_version": operator_set_version,
        "operator_name": operator_name,
        "operator_version": operator_version,
        "residual_id": residual_id,
        "residual_kind": residual_kind,
        "residual_code": residual_code,
        "candidate_digest": candidate_digest,
        "evidence_spans": [_span_payload(span) for span in evidence_spans],
        "schema_versions": _version_pairs_payload(schema_versions),
        "policy_versions": _version_pairs_payload(policy_versions),
    }


def _operator_result_id_payload(
    *,
    operator_policy_version: str,
    input_digest: str,
    geometric_search_run_id: str,
    attempt_id: str,
    attempt_index: int,
    candidate_digest: str,
    candidate_reconstruction_digest: str,
    candidate_organ: str,
    operator_name: str,
    operator_version: str,
    reason_codes: tuple[str, ...],
    evidence_spans: tuple[SourceSpan, ...],
) -> dict[str, object]:
    return {
        "operator_result_id": "",
        "operator_policy_version": operator_policy_version,
        "input_digest": input_digest,
        "geometric_search_run_id": geometric_search_run_id,
        "attempt_id": attempt_id,
        "attempt_index": attempt_index,
        "candidate_digest": candidate_digest,
        "candidate_reconstruction_digest": candidate_reconstruction_digest,
        "candidate_organ": candidate_organ,
        "operator_name": operator_name,
        "operator_version": operator_version,
        "reason_codes": list(reason_codes),
        "evidence_spans": [_span_payload(span) for span in evidence_spans],
    }


def _operator_refusal_id_payload(
    *,
    operator_policy_version: str,
    input_digest: str | None,
    geometric_search_run_id: str | None,
    residual_id: str | None,
    operator_name: str,
    reason_codes: tuple[str, ...],
) -> dict[str, object]:
    return {
        "operator_refusal_id": "",
        "operator_policy_version": operator_policy_version,
        "input_digest": input_digest,
        "geometric_search_run_id": geometric_search_run_id,
        "residual_id": residual_id,
        "operator_name": operator_name,
        "reason_codes": list(reason_codes),
    }


def _refusal(
    *,
    input_digest: str | None,
    geometric_search_run_id: str | None,
    residual_id: str | None,
    reason_codes: tuple[str, ...],
) -> CandidateOperatorRefusal:
    operator_refusal_id = _canonical_digest(
        _operator_refusal_id_payload(
            operator_policy_version=CANDIDATE_OPERATOR_POLICY_VERSION,
            input_digest=input_digest,
            geometric_search_run_id=geometric_search_run_id,
            residual_id=residual_id,
            operator_name=MISSING_ROLE_CANDIDATE_OPERATOR_NAME,
            reason_codes=reason_codes,
        )
    )
    return CandidateOperatorRefusal(
        operator_refusal_id=operator_refusal_id,
        operator_policy_version=CANDIDATE_OPERATOR_POLICY_VERSION,
        input_digest=input_digest,
        geometric_search_run_id=geometric_search_run_id,
        residual_id=residual_id,
        operator_name=MISSING_ROLE_CANDIDATE_OPERATOR_NAME,
        reason_codes=reason_codes,
        explanation="Candidate operator refused: " + ", ".join(reason_codes) + ".",
    )


def _spans_grounded_in_residual(
    cue_spans: tuple[SourceSpan, ...],
    residual_spans: tuple[SourceSpan, ...],
) -> bool:
    if not cue_spans:
        return False
    for cue_span in cue_spans:
        if cue_span not in residual_spans:
            return False
    return True


def _valid_residual_record(residual: object) -> bool:
    required = (
        "residual_id",
        "candidate_organ",
        "residual_kind",
        "residual_code",
        "evidence_spans",
    )
    return all(_safe_getattr(residual, name) is not None for name in required)


def build_missing_role_candidate(
    *,
    residual: object,
    search_gate: SearchGateDecision,
    compute_budget: ComputeBudgetDecision,
    run: GeometricSearchRun,
    problem_frame_digest: str,
    original_contract_assessment_id: str,
    grounded_unary_delta_cues: tuple[GroundedUnaryDeltaCue, ...],
    attempt_index: int = 0,
    schema_versions: tuple[tuple[str, str], ...] = (),
    policy_versions: tuple[tuple[str, str], ...] = (),
    explanation: str = "",
) -> CandidateOperatorOutcome:
    """Construct one missing-role candidate or return a typed refusal."""

    operator_set_id = candidate_operator_set_id()
    reasons: list[str] = []

    residual_id = _safe_getattr(residual, "residual_id")
    residual_kind = _enum_value(_safe_getattr(residual, "residual_kind"))
    residual_code = _safe_getattr(residual, "residual_code")
    candidate_organ = _safe_getattr(residual, "candidate_organ")
    residual_spans = _safe_getattr(residual, "evidence_spans")

    gate_id = _safe_getattr(search_gate, "decision_id")
    gate_status = _safe_getattr(search_gate, "status")
    gate_reason = _safe_getattr(search_gate, "reason_code")
    gate_residual_ids = _safe_getattr(search_gate, "residual_ids")
    gate_candidate_organ = _safe_getattr(search_gate, "candidate_organ")

    budget_id = _safe_getattr(compute_budget, "budget_id")
    budget_status = _safe_getattr(compute_budget, "status")
    budget_reason = _safe_getattr(compute_budget, "reason_code")
    budget_gate_id = _safe_getattr(compute_budget, "gate_decision_id")
    max_candidates = _safe_getattr(compute_budget, "max_candidates")
    max_depth = _safe_getattr(compute_budget, "max_depth")
    max_steps = _safe_getattr(compute_budget, "max_steps")
    max_parallelism = _safe_getattr(compute_budget, "max_parallelism")

    run_id = _safe_getattr(run, "run_id")
    run_gate_id = _safe_getattr(run, "gate_decision_id")
    run_budget_id = _safe_getattr(run, "budget_id")
    run_operator_set_id = _safe_getattr(run, "operator_set_id")
    run_operator_set_version = _safe_getattr(run, "operator_set_version")
    run_problem_frame_digest = _safe_getattr(run, "problem_frame_digest")
    run_assessment_id = _safe_getattr(run, "contract_assessment_id")
    run_residual_ids = _safe_getattr(run, "residual_ids")

    if not _valid_residual_record(residual):
        reasons.append(CandidateOperatorRefusalReason.INVALID_OPERATOR_INPUT.value)
    if not isinstance(search_gate, SearchGateDecision):
        reasons.append(CandidateOperatorRefusalReason.INVALID_OPERATOR_INPUT.value)
    if not isinstance(compute_budget, ComputeBudgetDecision):
        reasons.append(CandidateOperatorRefusalReason.INVALID_OPERATOR_INPUT.value)
    if not isinstance(run, GeometricSearchRun):
        reasons.append(CandidateOperatorRefusalReason.INVALID_OPERATOR_INPUT.value)

    if not _nonempty_text(residual_id):
        reasons.append(CandidateOperatorRefusalReason.INVALID_OPERATOR_INPUT.value)
    if residual_kind != MISSING_ROLE_RESIDUAL_KIND:
        reasons.append(CandidateOperatorRefusalReason.UNSUPPORTED_RESIDUAL_KIND.value)
    if residual_code != MISSING_ROLE_RESIDUAL_CODE:
        reasons.append(CandidateOperatorRefusalReason.UNSUPPORTED_RESIDUAL_CODE.value)
    if candidate_organ != MISSING_ROLE_CANDIDATE_ORGAN:
        reasons.append(CandidateOperatorRefusalReason.UNSUPPORTED_CANDIDATE_ORGAN.value)
    if not _valid_spans(residual_spans):
        reasons.append(CandidateOperatorRefusalReason.MALFORMED_EVIDENCE_SPAN.value)

    if gate_status is not SearchGateStatus.ELIGIBLE:
        reasons.append(CandidateOperatorRefusalReason.INELIGIBLE_SEARCH_GATE.value)
    if gate_reason != "eligible_missing_role":
        reasons.append(CandidateOperatorRefusalReason.INELIGIBLE_SEARCH_GATE.value)
    if gate_candidate_organ != MISSING_ROLE_CANDIDATE_ORGAN:
        reasons.append(CandidateOperatorRefusalReason.UNSUPPORTED_CANDIDATE_ORGAN.value)

    if budget_status is not ComputeBudgetStatus.BUDGET_ALLOWED:
        reasons.append(CandidateOperatorRefusalReason.NON_ALLOWED_BUDGET.value)
    if budget_reason != "budget_allowed_missing_role":
        reasons.append(CandidateOperatorRefusalReason.NON_ALLOWED_BUDGET.value)

    if not _nonempty_text(budget_gate_id) or not _nonempty_text(gate_id):
        reasons.append(CandidateOperatorRefusalReason.GATE_BUDGET_MISMATCH.value)
    elif budget_gate_id != gate_id:
        reasons.append(CandidateOperatorRefusalReason.GATE_BUDGET_MISMATCH.value)

    if not _nonempty_text(run_gate_id) or not _nonempty_text(gate_id):
        reasons.append(CandidateOperatorRefusalReason.RUN_GATE_MISMATCH.value)
    elif run_gate_id != gate_id:
        reasons.append(CandidateOperatorRefusalReason.RUN_GATE_MISMATCH.value)

    if not _nonempty_text(run_budget_id) or not _nonempty_text(budget_id):
        reasons.append(CandidateOperatorRefusalReason.RUN_BUDGET_MISMATCH.value)
    elif run_budget_id != budget_id:
        reasons.append(CandidateOperatorRefusalReason.RUN_BUDGET_MISMATCH.value)

    if run_operator_set_id != operator_set_id:
        reasons.append(CandidateOperatorRefusalReason.OPERATOR_SET_MISMATCH.value)
    if run_operator_set_version != CANDIDATE_OPERATOR_SET_VERSION:
        reasons.append(CandidateOperatorRefusalReason.OPERATOR_SET_MISMATCH.value)

    if type(attempt_index) is not int or attempt_index < 0:
        reasons.append(CandidateOperatorRefusalReason.INVALID_OPERATOR_INPUT.value)
    if type(max_candidates) is not int:
        reasons.append(CandidateOperatorRefusalReason.INVALID_OPERATOR_INPUT.value)
    elif attempt_index >= max_candidates:
        reasons.append(
            CandidateOperatorRefusalReason.ATTEMPT_INDEX_EXCEEDS_BUDGET.value
        )
    if attempt_index >= MISSING_ROLE_OPERATOR_POLICY.max_attempts_per_run:
        reasons.append(
            CandidateOperatorRefusalReason.ATTEMPT_INDEX_EXCEEDS_OPERATOR_POLICY.value
        )

    if type(max_depth) is not int or type(max_steps) is not int:
        reasons.append(CandidateOperatorRefusalReason.INVALID_OPERATOR_INPUT.value)
    else:
        charge = MISSING_ROLE_OPERATOR_POLICY.budget_charge
        if charge.candidates > max_candidates:
            reasons.append(
                CandidateOperatorRefusalReason.BUDGET_CHARGE_EXCEEDS_BUDGET.value
            )
        if charge.steps > max_steps:
            reasons.append(
                CandidateOperatorRefusalReason.BUDGET_CHARGE_EXCEEDS_BUDGET.value
            )
        if MISSING_ROLE_OPERATOR_POLICY.depth > max_depth:
            reasons.append(
                CandidateOperatorRefusalReason.BUDGET_CHARGE_EXCEEDS_BUDGET.value
            )

    if type(max_parallelism) is not int or max_parallelism != 1:
        reasons.append(CandidateOperatorRefusalReason.NON_SERIAL_BUDGET.value)

    if not _valid_version_pairs(schema_versions):
        reasons.append(CandidateOperatorRefusalReason.UNSUPPORTED_SCHEMA_VERSION.value)
    if not _valid_version_pairs(policy_versions):
        reasons.append(CandidateOperatorRefusalReason.UNSUPPORTED_SCHEMA_VERSION.value)

    if not _sha256_text(problem_frame_digest):
        reasons.append(CandidateOperatorRefusalReason.INVALID_OPERATOR_INPUT.value)
    if not _nonempty_text(original_contract_assessment_id):
        reasons.append(CandidateOperatorRefusalReason.INVALID_OPERATOR_INPUT.value)
    if not _sha256_text(run_id):
        reasons.append(CandidateOperatorRefusalReason.INVALID_OPERATOR_INPUT.value)

    if (
        isinstance(residual_id, str)
        and isinstance(gate_residual_ids, tuple)
        and residual_id not in gate_residual_ids
    ):
        reasons.append(CandidateOperatorRefusalReason.INVALID_OPERATOR_INPUT.value)
    if (
        isinstance(residual_id, str)
        and isinstance(run_residual_ids, tuple)
        and residual_id not in run_residual_ids
    ):
        reasons.append(CandidateOperatorRefusalReason.INVALID_OPERATOR_INPUT.value)
    if (
        isinstance(problem_frame_digest, str)
        and isinstance(run_problem_frame_digest, str)
        and problem_frame_digest != run_problem_frame_digest
    ):
        reasons.append(CandidateOperatorRefusalReason.INVALID_OPERATOR_INPUT.value)
    if (
        isinstance(original_contract_assessment_id, str)
        and isinstance(run_assessment_id, str)
        and original_contract_assessment_id != run_assessment_id
    ):
        reasons.append(CandidateOperatorRefusalReason.INVALID_OPERATOR_INPUT.value)

    if len(grounded_unary_delta_cues) == 0:
        reasons.append(CandidateOperatorRefusalReason.MISSING_TYPED_CUE.value)
    elif len(grounded_unary_delta_cues) > 1:
        reasons.append(CandidateOperatorRefusalReason.AMBIGUOUS_TYPED_CUE.value)

    cue: GroundedUnaryDeltaCue | None = None
    if len(grounded_unary_delta_cues) == 1:
        cue = grounded_unary_delta_cues[0]
        if not _nonempty_text(cue.direction):
            reasons.append(CandidateOperatorRefusalReason.MISSING_TYPED_CUE.value)
        elif cue.direction not in _SUPPORTED_DIRECTIONS:
            reasons.append(CandidateOperatorRefusalReason.UNSUPPORTED_TYPED_CUE.value)
        if not _valid_spans(cue.evidence_spans):
            reasons.append(CandidateOperatorRefusalReason.MALFORMED_EVIDENCE_SPAN.value)
        elif isinstance(residual_spans, tuple) and not _spans_grounded_in_residual(
            cue.evidence_spans, residual_spans
        ):
            reasons.append(CandidateOperatorRefusalReason.MALFORMED_EVIDENCE_SPAN.value)

    input_digest: str | None = None
    if (
        not reasons
        and isinstance(residual_id, str)
        and isinstance(run_id, str)
        and isinstance(gate_id, str)
        and isinstance(budget_id, str)
        and type(attempt_index) is int
    ):
        input_digest = _canonical_digest(
            _input_digest_payload(
                operator_policy_version=CANDIDATE_OPERATOR_POLICY_VERSION,
                operator_name=MISSING_ROLE_CANDIDATE_OPERATOR_NAME,
                operator_version=MISSING_ROLE_CANDIDATE_OPERATOR_VERSION,
                problem_frame_digest=problem_frame_digest,
                original_contract_assessment_id=original_contract_assessment_id,
                residual_id=residual_id,
                residual_kind=MISSING_ROLE_RESIDUAL_KIND,
                residual_code=MISSING_ROLE_RESIDUAL_CODE,
                candidate_organ=MISSING_ROLE_CANDIDATE_ORGAN,
                search_gate_decision_id=gate_id,
                compute_budget_id=budget_id,
                geometric_search_run_id=run_id,
                operator_set_id=operator_set_id,
                operator_set_version=CANDIDATE_OPERATOR_SET_VERSION,
                attempt_index=attempt_index,
                schema_versions=schema_versions,
                policy_versions=policy_versions,
            )
        )

    if reasons:
        return _refusal(
            input_digest=input_digest,
            geometric_search_run_id=_text_or_none(run_id),
            residual_id=_text_or_none(residual_id),
            reason_codes=tuple(dict.fromkeys(reasons)),
        )

    assert cue is not None
    assert input_digest is not None
    assert isinstance(residual_id, str)
    assert isinstance(run_id, str)

    evidence_spans = cue.evidence_spans
    payload = _candidate_payload(cue.direction)
    candidate_digest = _canonical_digest(
        _candidate_digest_payload(
            problem_frame_digest=problem_frame_digest,
            candidate_organ=MISSING_ROLE_CANDIDATE_ORGAN,
            candidate_payload=payload,
            evidence_spans=evidence_spans,
        )
    )

    attempt_id = _canonical_digest(
        _attempt_id_payload(
            attempt_index=attempt_index,
            parent_attempt_id=None,
            operator_id=MISSING_ROLE_CANDIDATE_OPERATOR_NAME,
            operator_version=MISSING_ROLE_CANDIDATE_OPERATOR_VERSION,
            input_digest=input_digest,
            candidate_digest=candidate_digest,
            budget_charge=_FIXED_BUDGET_CHARGE,
            depth=_OPERATOR_DEPTH,
            step_index=attempt_index,
            replay_status=CandidateReplayStatus.REPLAY_PENDING,
            replay_blockers=(),
            evidence_spans=evidence_spans,
        )
    )

    candidate_reconstruction_digest = _canonical_digest(
        _reconstruction_digest_payload(
            geometric_search_run_id=run_id,
            attempt_id=attempt_id,
            attempt_index=attempt_index,
            operator_set_id=operator_set_id,
            operator_set_version=CANDIDATE_OPERATOR_SET_VERSION,
            operator_name=MISSING_ROLE_CANDIDATE_OPERATOR_NAME,
            operator_version=MISSING_ROLE_CANDIDATE_OPERATOR_VERSION,
            residual_id=residual_id,
            residual_kind=MISSING_ROLE_RESIDUAL_KIND,
            residual_code=MISSING_ROLE_RESIDUAL_CODE,
            candidate_digest=candidate_digest,
            evidence_spans=evidence_spans,
            schema_versions=schema_versions,
            policy_versions=policy_versions,
        )
    )

    operator_provenance = (
        ("operator_family", _OPERATOR_FAMILY),
        ("operator_name", MISSING_ROLE_CANDIDATE_OPERATOR_NAME),
        ("operator_version", MISSING_ROLE_CANDIDATE_OPERATOR_VERSION),
        ("operator_set_id", operator_set_id),
        ("operator_set_version", CANDIDATE_OPERATOR_SET_VERSION),
    )

    candidate_reconstruction = CandidateReconstruction(
        candidate_digest=candidate_digest,
        candidate_reconstruction_digest=candidate_reconstruction_digest,
        candidate_organ=MISSING_ROLE_CANDIDATE_ORGAN,
        candidate_payload=payload,
        evidence_spans=evidence_spans,
        operator_name=MISSING_ROLE_CANDIDATE_OPERATOR_NAME,
        operator_version=MISSING_ROLE_CANDIDATE_OPERATOR_VERSION,
        operator_provenance=operator_provenance,
        source_residual_id=residual_id,
        problem_frame_digest=problem_frame_digest,
        original_contract_assessment_id=original_contract_assessment_id,
    )

    candidate_attempt = CandidateAttempt(
        attempt_id=attempt_id,
        attempt_index=attempt_index,
        parent_attempt_id=None,
        operator_id=MISSING_ROLE_CANDIDATE_OPERATOR_NAME,
        operator_version=MISSING_ROLE_CANDIDATE_OPERATOR_VERSION,
        input_digest=input_digest,
        candidate_digest=candidate_digest,
        budget_charge=_FIXED_BUDGET_CHARGE,
        depth=_OPERATOR_DEPTH,
        step_index=attempt_index,
        replay_status=CandidateReplayStatus.REPLAY_PENDING,
        replay_blockers=(),
        evidence_spans=evidence_spans,
        explanation="",
    )

    reason_codes: tuple[str, ...] = ()
    operator_result_id = _canonical_digest(
        _operator_result_id_payload(
            operator_policy_version=CANDIDATE_OPERATOR_POLICY_VERSION,
            input_digest=input_digest,
            geometric_search_run_id=run_id,
            attempt_id=attempt_id,
            attempt_index=attempt_index,
            candidate_digest=candidate_digest,
            candidate_reconstruction_digest=candidate_reconstruction_digest,
            candidate_organ=MISSING_ROLE_CANDIDATE_ORGAN,
            operator_name=MISSING_ROLE_CANDIDATE_OPERATOR_NAME,
            operator_version=MISSING_ROLE_CANDIDATE_OPERATOR_VERSION,
            reason_codes=reason_codes,
            evidence_spans=evidence_spans,
        )
    )

    safe_explanation = explanation or (
        "Missing-role candidate constructed for residual "
        + residual_id
        + " with direction "
        + cue.direction
        + "."
    )
    return CandidateOperatorResult(
        operator_result_id=operator_result_id,
        operator_policy_version=CANDIDATE_OPERATOR_POLICY_VERSION,
        input_digest=input_digest,
        geometric_search_run_id=run_id,
        attempt_id=attempt_id,
        attempt_index=attempt_index,
        candidate_digest=candidate_digest,
        candidate_reconstruction_digest=candidate_reconstruction_digest,
        candidate_organ=MISSING_ROLE_CANDIDATE_ORGAN,
        operator_name=MISSING_ROLE_CANDIDATE_OPERATOR_NAME,
        operator_version=MISSING_ROLE_CANDIDATE_OPERATOR_VERSION,
        candidate_attempt=candidate_attempt,
        candidate_reconstruction=candidate_reconstruction,
        reason_codes=reason_codes,
        evidence_spans=evidence_spans,
        explanation=safe_explanation,
    )


__all__ = [
    "CANDIDATE_OPERATOR_POLICY_VERSION",
    "CANDIDATE_OPERATOR_SET_VERSION",
    "MISSING_ROLE_CANDIDATE_OPERATOR_NAME",
    "MISSING_ROLE_CANDIDATE_OPERATOR_VERSION",
    "MISSING_ROLE_RESIDUAL_KIND",
    "MISSING_ROLE_RESIDUAL_CODE",
    "MISSING_ROLE_CANDIDATE_ORGAN",
    "QUANTITY_ENTITY_BINDING_CANDIDATE_OPERATOR_NAME",
    "QUANTITY_ENTITY_BINDING_CANDIDATE_OPERATOR_VERSION",
    "QUANTITY_ENTITY_BINDING_RESIDUAL_KIND",
    "QUANTITY_ENTITY_BINDING_RESIDUAL_CODE",
    "QUANTITY_ENTITY_BINDING_CANDIDATE_ORGAN",
    "CandidateOperatorRefusalReason",
    "CandidateOperatorPolicy",
    "GroundedUnaryDeltaCue",
    "GroundedQuantityEntityCue",
    "CandidateOperatorInput",
    "CandidateReconstruction",
    "CandidateOperatorResult",
    "CandidateOperatorRefusal",
    "CandidateOperatorOutcome",
    "candidate_operator_set_id",
    "build_missing_role_candidate",
    "build_quantity_entity_binding_candidate",
]

def build_quantity_entity_binding_candidate(
    *,
    residual: object,
    search_gate: SearchGateDecision,
    compute_budget: ComputeBudgetDecision,
    run: GeometricSearchRun,
    problem_frame_digest: str,
    original_contract_assessment_id: str,
    grounded_quantity_entity_cues: tuple[GroundedQuantityEntityCue, ...],
    attempt_index: int = 0,
    schema_versions: tuple[tuple[str, str], ...] = (),
    policy_versions: tuple[tuple[str, str], ...] = (),
    explanation: str = "",
) -> CandidateOperatorOutcome:
    """Construct one quantity-entity binding candidate or return a typed refusal."""

    operator_set_id = candidate_operator_set_id()
    reasons: list[str] = []

    residual_id = _safe_getattr(residual, "residual_id")
    residual_kind = _enum_value(_safe_getattr(residual, "residual_kind"))
    residual_code = _safe_getattr(residual, "residual_code")
    candidate_organ = _safe_getattr(residual, "candidate_organ")
    residual_spans = _safe_getattr(residual, "evidence_spans")

    gate_id = _safe_getattr(search_gate, "decision_id")
    gate_status = _safe_getattr(search_gate, "status")
    gate_reason = _safe_getattr(search_gate, "reason_code")
    gate_residual_ids = _safe_getattr(search_gate, "residual_ids")
    gate_candidate_organ = _safe_getattr(search_gate, "candidate_organ")

    budget_id = _safe_getattr(compute_budget, "budget_id")
    budget_status = _safe_getattr(compute_budget, "status")
    budget_reason = _safe_getattr(compute_budget, "reason_code")
    budget_gate_id = _safe_getattr(compute_budget, "gate_decision_id")
    max_candidates = _safe_getattr(compute_budget, "max_candidates")
    max_depth = _safe_getattr(compute_budget, "max_depth")
    max_steps = _safe_getattr(compute_budget, "max_steps")
    max_parallelism = _safe_getattr(compute_budget, "max_parallelism")

    run_id = _safe_getattr(run, "run_id")
    run_gate_id = _safe_getattr(run, "gate_decision_id")
    run_budget_id = _safe_getattr(run, "budget_id")
    run_operator_set_id = _safe_getattr(run, "operator_set_id")
    run_operator_set_version = _safe_getattr(run, "operator_set_version")
    run_problem_frame_digest = _safe_getattr(run, "problem_frame_digest")
    run_assessment_id = _safe_getattr(run, "contract_assessment_id")
    run_residual_ids = _safe_getattr(run, "residual_ids")

    if not _valid_residual_record(residual):
        reasons.append(CandidateOperatorRefusalReason.INVALID_OPERATOR_INPUT.value)
    if not isinstance(search_gate, SearchGateDecision):
        reasons.append(CandidateOperatorRefusalReason.INVALID_OPERATOR_INPUT.value)
    if not isinstance(compute_budget, ComputeBudgetDecision):
        reasons.append(CandidateOperatorRefusalReason.INVALID_OPERATOR_INPUT.value)
    if not isinstance(run, GeometricSearchRun):
        reasons.append(CandidateOperatorRefusalReason.INVALID_OPERATOR_INPUT.value)

    if not _nonempty_text(residual_id):
        reasons.append(CandidateOperatorRefusalReason.INVALID_OPERATOR_INPUT.value)
    if residual_kind != QUANTITY_ENTITY_BINDING_RESIDUAL_KIND:
        reasons.append(CandidateOperatorRefusalReason.UNSUPPORTED_RESIDUAL_KIND.value)
    if residual_code != QUANTITY_ENTITY_BINDING_RESIDUAL_CODE:
        reasons.append(CandidateOperatorRefusalReason.UNSUPPORTED_RESIDUAL_CODE.value)
    if candidate_organ != QUANTITY_ENTITY_BINDING_CANDIDATE_ORGAN:
        reasons.append(CandidateOperatorRefusalReason.UNSUPPORTED_CANDIDATE_ORGAN.value)
    if not _valid_spans(residual_spans):
        reasons.append(CandidateOperatorRefusalReason.MALFORMED_EVIDENCE_SPAN.value)

    if gate_status is not SearchGateStatus.ELIGIBLE:
        reasons.append(CandidateOperatorRefusalReason.INELIGIBLE_SEARCH_GATE.value)
    if gate_reason != "eligible_missing_relation":
        reasons.append(CandidateOperatorRefusalReason.INELIGIBLE_SEARCH_GATE.value)
    if gate_candidate_organ != QUANTITY_ENTITY_BINDING_CANDIDATE_ORGAN:
        reasons.append(CandidateOperatorRefusalReason.UNSUPPORTED_CANDIDATE_ORGAN.value)

    if budget_status is not ComputeBudgetStatus.BUDGET_ALLOWED:
        reasons.append(CandidateOperatorRefusalReason.NON_ALLOWED_BUDGET.value)
    if budget_reason != "budget_allowed_missing_relation":
        reasons.append(CandidateOperatorRefusalReason.NON_ALLOWED_BUDGET.value)

    if not _nonempty_text(budget_gate_id) or not _nonempty_text(gate_id):
        reasons.append(CandidateOperatorRefusalReason.GATE_BUDGET_MISMATCH.value)
    elif budget_gate_id != gate_id:
        reasons.append(CandidateOperatorRefusalReason.GATE_BUDGET_MISMATCH.value)

    if not _nonempty_text(run_gate_id) or not _nonempty_text(gate_id):
        reasons.append(CandidateOperatorRefusalReason.RUN_GATE_MISMATCH.value)
    elif run_gate_id != gate_id:
        reasons.append(CandidateOperatorRefusalReason.RUN_GATE_MISMATCH.value)

    if not _nonempty_text(run_budget_id) or not _nonempty_text(budget_id):
        reasons.append(CandidateOperatorRefusalReason.RUN_BUDGET_MISMATCH.value)
    elif run_budget_id != budget_id:
        reasons.append(CandidateOperatorRefusalReason.RUN_BUDGET_MISMATCH.value)

    if run_operator_set_id != operator_set_id:
        reasons.append(CandidateOperatorRefusalReason.OPERATOR_SET_MISMATCH.value)
    if run_operator_set_version != CANDIDATE_OPERATOR_SET_VERSION:
        reasons.append(CandidateOperatorRefusalReason.OPERATOR_SET_MISMATCH.value)

    if type(attempt_index) is not int or attempt_index < 0:
        reasons.append(CandidateOperatorRefusalReason.INVALID_OPERATOR_INPUT.value)
    elif attempt_index != 0:
        reasons.append(CandidateOperatorRefusalReason.ATTEMPT_INDEX_EXCEEDS_BUDGET.value)
        
    if type(max_candidates) is not int:
        reasons.append(CandidateOperatorRefusalReason.INVALID_OPERATOR_INPUT.value)
    elif max_candidates < 1:
        reasons.append(CandidateOperatorRefusalReason.BUDGET_CHARGE_EXCEEDS_BUDGET.value)

    if attempt_index >= QUANTITY_ENTITY_BINDING_OPERATOR_POLICY.max_attempts_per_run:
        reasons.append(
            CandidateOperatorRefusalReason.ATTEMPT_INDEX_EXCEEDS_OPERATOR_POLICY.value
        )

    if type(max_depth) is not int or type(max_steps) is not int:
        reasons.append(CandidateOperatorRefusalReason.INVALID_OPERATOR_INPUT.value)
    else:
        charge = QUANTITY_ENTITY_BINDING_OPERATOR_POLICY.budget_charge
        if charge.candidates > max_candidates:
            reasons.append(
                CandidateOperatorRefusalReason.BUDGET_CHARGE_EXCEEDS_BUDGET.value
            )
        if charge.steps > max_steps:
            reasons.append(
                CandidateOperatorRefusalReason.BUDGET_CHARGE_EXCEEDS_BUDGET.value
            )
        if QUANTITY_ENTITY_BINDING_OPERATOR_POLICY.depth > max_depth:
            reasons.append(
                CandidateOperatorRefusalReason.BUDGET_CHARGE_EXCEEDS_BUDGET.value
            )

    if type(max_parallelism) is not int or max_parallelism != 1:
        reasons.append(CandidateOperatorRefusalReason.NON_SERIAL_BUDGET.value)

    if not _valid_version_pairs(schema_versions):
        reasons.append(CandidateOperatorRefusalReason.UNSUPPORTED_SCHEMA_VERSION.value)
    if not _valid_version_pairs(policy_versions):
        reasons.append(CandidateOperatorRefusalReason.UNSUPPORTED_SCHEMA_VERSION.value)

    if not _sha256_text(problem_frame_digest):
        reasons.append(CandidateOperatorRefusalReason.INVALID_OPERATOR_INPUT.value)
    if not _nonempty_text(original_contract_assessment_id):
        reasons.append(CandidateOperatorRefusalReason.INVALID_OPERATOR_INPUT.value)
    if not _sha256_text(run_id):
        reasons.append(CandidateOperatorRefusalReason.INVALID_OPERATOR_INPUT.value)

    if (
        isinstance(residual_id, str)
        and isinstance(gate_residual_ids, tuple)
        and residual_id not in gate_residual_ids
    ):
        reasons.append(CandidateOperatorRefusalReason.INVALID_OPERATOR_INPUT.value)
    if (
        isinstance(residual_id, str)
        and isinstance(run_residual_ids, tuple)
        and residual_id not in run_residual_ids
    ):
        reasons.append(CandidateOperatorRefusalReason.INVALID_OPERATOR_INPUT.value)
    if (
        isinstance(problem_frame_digest, str)
        and isinstance(run_problem_frame_digest, str)
        and problem_frame_digest != run_problem_frame_digest
    ):
        reasons.append(CandidateOperatorRefusalReason.INVALID_OPERATOR_INPUT.value)
    if (
        isinstance(original_contract_assessment_id, str)
        and isinstance(run_assessment_id, str)
        and original_contract_assessment_id != run_assessment_id
    ):
        reasons.append(CandidateOperatorRefusalReason.INVALID_OPERATOR_INPUT.value)

    if not isinstance(grounded_quantity_entity_cues, tuple):
        reasons.append(CandidateOperatorRefusalReason.INVALID_QUANTITY_ENTITY_CUE_TYPE.value)
    elif len(grounded_quantity_entity_cues) == 0:
        reasons.append(CandidateOperatorRefusalReason.MISSING_TYPED_CUE.value)
    elif len(grounded_quantity_entity_cues) > 1:
        reasons.append(CandidateOperatorRefusalReason.QUANTITY_ENTITY_CUE_COUNT_MISMATCH.value)

    cue: GroundedQuantityEntityCue | None = None
    if isinstance(grounded_quantity_entity_cues, tuple) and len(grounded_quantity_entity_cues) == 1:
        cue = grounded_quantity_entity_cues[0]
        if not isinstance(cue, GroundedQuantityEntityCue):
            reasons.append(CandidateOperatorRefusalReason.INVALID_QUANTITY_ENTITY_CUE_TYPE.value)
        else:
            if not _nonempty_text(cue.quantity_mention_id):
                reasons.append(CandidateOperatorRefusalReason.EMPTY_QUANTITY_MENTION_ID.value)
            if not _nonempty_text(cue.entity_mention_id):
                reasons.append(CandidateOperatorRefusalReason.EMPTY_ENTITY_MENTION_ID.value)
            if not _nonempty_text(cue.quantity_kind):
                reasons.append(CandidateOperatorRefusalReason.EMPTY_QUANTITY_KIND.value)
            if cue.unit_mention_id is not None and not _nonempty_text(cue.unit_mention_id):
                reasons.append(CandidateOperatorRefusalReason.EMPTY_UNIT_MENTION_ID.value)

            if not _valid_spans(cue.evidence_spans):
                reasons.append(CandidateOperatorRefusalReason.MALFORMED_EVIDENCE_SPAN.value)
            elif not cue.evidence_spans:
                reasons.append(CandidateOperatorRefusalReason.MISSING_EVIDENCE_SPANS.value)
            elif isinstance(residual_spans, tuple) and not _spans_grounded_in_residual(
                cue.evidence_spans, residual_spans
            ):
                reasons.append(CandidateOperatorRefusalReason.MALFORMED_EVIDENCE_SPAN.value)

    input_digest: str | None = None
    if (
        not reasons
        and isinstance(residual_id, str)
        and isinstance(run_id, str)
        and isinstance(gate_id, str)
        and isinstance(budget_id, str)
        and type(attempt_index) is int
    ):
        input_digest = _canonical_digest(
            _input_digest_payload(
                operator_policy_version=CANDIDATE_OPERATOR_POLICY_VERSION,
                operator_name=QUANTITY_ENTITY_BINDING_CANDIDATE_OPERATOR_NAME,
                operator_version=QUANTITY_ENTITY_BINDING_CANDIDATE_OPERATOR_VERSION,
                problem_frame_digest=problem_frame_digest,
                original_contract_assessment_id=original_contract_assessment_id,
                residual_id=residual_id,
                residual_kind=QUANTITY_ENTITY_BINDING_RESIDUAL_KIND,
                residual_code=QUANTITY_ENTITY_BINDING_RESIDUAL_CODE,
                candidate_organ=QUANTITY_ENTITY_BINDING_CANDIDATE_ORGAN,
                search_gate_decision_id=gate_id,
                compute_budget_id=budget_id,
                geometric_search_run_id=run_id,
                operator_set_id=operator_set_id,
                operator_set_version=CANDIDATE_OPERATOR_SET_VERSION,
                attempt_index=attempt_index,
                schema_versions=schema_versions,
                policy_versions=policy_versions,
            )
        )

    if reasons:
        operator_refusal_id = _canonical_digest(
            _operator_refusal_id_payload(
                operator_policy_version=CANDIDATE_OPERATOR_POLICY_VERSION,
                input_digest=input_digest,
                geometric_search_run_id=_text_or_none(run_id),
                residual_id=_text_or_none(residual_id),
                operator_name=QUANTITY_ENTITY_BINDING_CANDIDATE_OPERATOR_NAME,
                reason_codes=tuple(dict.fromkeys(reasons)),
            )
        )
        return CandidateOperatorRefusal(
            operator_refusal_id=operator_refusal_id,
            operator_policy_version=CANDIDATE_OPERATOR_POLICY_VERSION,
            input_digest=input_digest,
            geometric_search_run_id=_text_or_none(run_id),
            residual_id=_text_or_none(residual_id),
            operator_name=QUANTITY_ENTITY_BINDING_CANDIDATE_OPERATOR_NAME,
            reason_codes=tuple(dict.fromkeys(reasons)),
            explanation="Candidate operator refused: " + ", ".join(dict.fromkeys(reasons)) + ".",
        )

    assert cue is not None
    assert input_digest is not None
    assert isinstance(residual_id, str)
    assert isinstance(run_id, str)

    evidence_spans = cue.evidence_spans
    payload = _quantity_entity_binding_candidate_payload(cue)
    candidate_digest = _canonical_digest(
        _candidate_digest_payload(
            problem_frame_digest=problem_frame_digest,
            candidate_organ=QUANTITY_ENTITY_BINDING_CANDIDATE_ORGAN,
            candidate_payload=payload,
            evidence_spans=evidence_spans,
        )
    )

    attempt_id = _canonical_digest(
        _attempt_id_payload(
            attempt_index=attempt_index,
            parent_attempt_id=None,
            operator_id=QUANTITY_ENTITY_BINDING_CANDIDATE_OPERATOR_NAME,
            operator_version=QUANTITY_ENTITY_BINDING_CANDIDATE_OPERATOR_VERSION,
            input_digest=input_digest,
            candidate_digest=candidate_digest,
            budget_charge=_FIXED_BUDGET_CHARGE,
            depth=_OPERATOR_DEPTH,
            step_index=attempt_index,
            replay_status=CandidateReplayStatus.REPLAY_PENDING,
            replay_blockers=(),
            evidence_spans=evidence_spans,
        )
    )

    candidate_reconstruction_digest = _canonical_digest(
        _reconstruction_digest_payload(
            geometric_search_run_id=run_id,
            attempt_id=attempt_id,
            attempt_index=attempt_index,
            operator_set_id=operator_set_id,
            operator_set_version=CANDIDATE_OPERATOR_SET_VERSION,
            operator_name=QUANTITY_ENTITY_BINDING_CANDIDATE_OPERATOR_NAME,
            operator_version=QUANTITY_ENTITY_BINDING_CANDIDATE_OPERATOR_VERSION,
            residual_id=residual_id,
            residual_kind=QUANTITY_ENTITY_BINDING_RESIDUAL_KIND,
            residual_code=QUANTITY_ENTITY_BINDING_RESIDUAL_CODE,
            candidate_digest=candidate_digest,
            evidence_spans=evidence_spans,
            schema_versions=schema_versions,
            policy_versions=policy_versions,
        )
    )

    operator_provenance = (
        ("operator_family", QUANTITY_ENTITY_BINDING_OPERATOR_POLICY.operator_family),
        ("operator_name", QUANTITY_ENTITY_BINDING_CANDIDATE_OPERATOR_NAME),
        ("operator_version", QUANTITY_ENTITY_BINDING_CANDIDATE_OPERATOR_VERSION),
        ("operator_set_id", operator_set_id),
        ("operator_set_version", CANDIDATE_OPERATOR_SET_VERSION),
    )

    candidate_reconstruction = CandidateReconstruction(
        candidate_digest=candidate_digest,
        candidate_reconstruction_digest=candidate_reconstruction_digest,
        candidate_organ=QUANTITY_ENTITY_BINDING_CANDIDATE_ORGAN,
        candidate_payload=payload,
        evidence_spans=evidence_spans,
        operator_name=QUANTITY_ENTITY_BINDING_CANDIDATE_OPERATOR_NAME,
        operator_version=QUANTITY_ENTITY_BINDING_CANDIDATE_OPERATOR_VERSION,
        operator_provenance=operator_provenance,
        source_residual_id=residual_id,
        problem_frame_digest=problem_frame_digest,
        original_contract_assessment_id=original_contract_assessment_id,
    )

    candidate_attempt = CandidateAttempt(
        attempt_id=attempt_id,
        attempt_index=attempt_index,
        parent_attempt_id=None,
        operator_id=QUANTITY_ENTITY_BINDING_CANDIDATE_OPERATOR_NAME,
        operator_version=QUANTITY_ENTITY_BINDING_CANDIDATE_OPERATOR_VERSION,
        input_digest=input_digest,
        candidate_digest=candidate_digest,
        budget_charge=_FIXED_BUDGET_CHARGE,
        depth=_OPERATOR_DEPTH,
        step_index=attempt_index,
        replay_status=CandidateReplayStatus.REPLAY_PENDING,
        replay_blockers=(),
        evidence_spans=evidence_spans,
        explanation="",
    )

    reason_codes: tuple[str, ...] = ()
    operator_result_id = _canonical_digest(
        _operator_result_id_payload(
            operator_policy_version=CANDIDATE_OPERATOR_POLICY_VERSION,
            input_digest=input_digest,
            geometric_search_run_id=run_id,
            attempt_id=attempt_id,
            attempt_index=attempt_index,
            candidate_digest=candidate_digest,
            candidate_reconstruction_digest=candidate_reconstruction_digest,
            candidate_organ=QUANTITY_ENTITY_BINDING_CANDIDATE_ORGAN,
            operator_name=QUANTITY_ENTITY_BINDING_CANDIDATE_OPERATOR_NAME,
            operator_version=QUANTITY_ENTITY_BINDING_CANDIDATE_OPERATOR_VERSION,
            reason_codes=reason_codes,
            evidence_spans=evidence_spans,
        )
    )

    safe_explanation = explanation or (
        "Quantity-entity binding candidate constructed for residual "
        + residual_id
        + " linking "
        + cue.quantity_mention_id
        + " and "
        + cue.entity_mention_id
        + "."
    )
    return CandidateOperatorResult(
        operator_result_id=operator_result_id,
        operator_policy_version=CANDIDATE_OPERATOR_POLICY_VERSION,
        input_digest=input_digest,
        geometric_search_run_id=run_id,
        attempt_id=attempt_id,
        attempt_index=attempt_index,
        candidate_digest=candidate_digest,
        candidate_reconstruction_digest=candidate_reconstruction_digest,
        candidate_organ=QUANTITY_ENTITY_BINDING_CANDIDATE_ORGAN,
        operator_name=QUANTITY_ENTITY_BINDING_CANDIDATE_OPERATOR_NAME,
        operator_version=QUANTITY_ENTITY_BINDING_CANDIDATE_OPERATOR_VERSION,
        candidate_attempt=candidate_attempt,
        candidate_reconstruction=candidate_reconstruction,
        reason_codes=reason_codes,
        evidence_spans=evidence_spans,
        explanation=safe_explanation,
    )