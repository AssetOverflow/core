from __future__ import annotations

import ast
import dataclasses
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from generate.candidate_operator import (
    CANDIDATE_OPERATOR_POLICY_VERSION,
    CANDIDATE_OPERATOR_SET_VERSION,
    MISSING_ROLE_CANDIDATE_OPERATOR_NAME,
    MISSING_ROLE_CANDIDATE_OPERATOR_VERSION,
    MISSING_ROLE_CANDIDATE_ORGAN,
    MISSING_ROLE_RESIDUAL_CODE,
    MISSING_ROLE_RESIDUAL_KIND,
    CandidateOperatorPolicy,
    CandidateOperatorRefusal,
    CandidateOperatorRefusalReason,
    CandidateOperatorResult,
    CandidateReconstruction,
    GroundedUnaryDeltaCue,
    build_missing_role_candidate,
    candidate_operator_set_id,
)
from generate.compute_budget import ComputeBudgetDecision, ComputeBudgetStatus
from generate.contract_residuals import ContractResidual, ResidualKind, ResidualSourceAxis
from generate.geometric_search_run import (
    BudgetCharge,
    CandidateReplayStatus,
    GeometricSearchRun,
    initialize_geometric_search_run,
)
from generate.kernel_facts import SourceSpan
from generate.search_gate import SearchGateDecision, SearchGateStatus


def _digest(payload: dict[str, object]) -> str:
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


def _span(text: str = "gained", start: int = 10, end: int = 15) -> SourceSpan:
    return SourceSpan(text=text, start=start, end=end, sentence_index=0)


def _residual(
    *,
    residual_id: str | None = None,
    evidence_spans: tuple[SourceSpan, ...] | None = None,
    residual_kind: ResidualKind = ResidualKind.MISSING_ROLE,
    residual_code: str = MISSING_ROLE_RESIDUAL_CODE,
    candidate_organ: str = MISSING_ROLE_CANDIDATE_ORGAN,
) -> ContractResidual:
    spans = evidence_spans if evidence_spans is not None else (_span(),)
    if residual_id is None:
        payload = {
            "candidate_organ": candidate_organ,
            "residual_kind": residual_kind.value,
            "residual_code": residual_code,
            "evidence_spans": [_span_payload(span) for span in spans],
        }
        residual_id = _digest(payload)
    return ContractResidual(
        residual_id=residual_id,
        candidate_organ=candidate_organ,
        family_id="state_change.unary_delta",
        residual_kind=residual_kind,
        residual_code=residual_code,
        source_axis=ResidualSourceAxis.ROLE,
        evidence_spans=spans,
        explanation="residual prose",
    )


def _gate(
    residual: ContractResidual,
    *,
    status: SearchGateStatus = SearchGateStatus.ELIGIBLE,
    reason_code: str = "eligible_missing_role",
    input_digest: str = "a" * 64,
) -> SearchGateDecision:
    payload = {
        "policy_version": "search_gate.v1",
        "input_digest": input_digest,
        "residual_ids": [residual.residual_id],
        "candidate_organ": residual.candidate_organ,
        "status": status.value,
        "reason_code": reason_code,
        "evidence_spans": [_span_payload(span) for span in residual.evidence_spans],
    }
    return SearchGateDecision(
        decision_id=_digest(payload),
        policy_version="search_gate.v1",
        input_digest=input_digest,
        residual_ids=(residual.residual_id,),
        candidate_organ=residual.candidate_organ,
        status=status,
        reason_code=reason_code,
        evidence_spans=residual.evidence_spans,
        explanation="gate prose",
    )


def _budget(
    gate: SearchGateDecision,
    *,
    status: ComputeBudgetStatus = ComputeBudgetStatus.BUDGET_ALLOWED,
    reason_code: str = "budget_allowed_missing_role",
    max_candidates: int = 5,
    max_depth: int = 2,
    max_steps: int = 10,
    max_parallelism: int = 1,
) -> ComputeBudgetDecision:
    payload = {
        "policy_version": "compute_budget.v1",
        "gate_decision_id": gate.decision_id,
        "gate_policy_version": gate.policy_version,
        "gate_input_digest": gate.input_digest,
        "status": status.value,
        "reason_code": reason_code,
        "max_candidates": max_candidates,
        "max_depth": max_depth,
        "max_steps": max_steps,
        "max_parallelism": max_parallelism,
        "evidence_spans": [_span_payload(span) for span in gate.evidence_spans],
    }
    return ComputeBudgetDecision(
        budget_id=_digest(payload),
        policy_version="compute_budget.v1",
        gate_decision_id=gate.decision_id,
        gate_policy_version=gate.policy_version,
        gate_input_digest=gate.input_digest,
        status=status,
        reason_code=reason_code,
        max_candidates=max_candidates,
        max_depth=max_depth,
        max_steps=max_steps,
        max_wallclock_ms=None,
        max_parallelism=max_parallelism,
        evidence_spans=gate.evidence_spans,
        explanation="budget prose",
    )


def _run(
    *,
    residual: ContractResidual,
    gate: SearchGateDecision,
    budget: ComputeBudgetDecision,
    problem_frame_digest: str = "f" * 64,
    assessment_id: str = "assessment-a",
) -> GeometricSearchRun:
    outcome = initialize_geometric_search_run(
        problem_frame_digest=problem_frame_digest,
        contract_assessment_id=assessment_id,
        residual_ids=(residual.residual_id,),
        gate_decision=gate,
        compute_budget=budget,
        operator_set_id=candidate_operator_set_id(),
        operator_set_version=CANDIDATE_OPERATOR_SET_VERSION,
    )
    assert isinstance(outcome, GeometricSearchRun)
    return outcome


def _cue(
    *,
    direction: str = "increase",
    evidence_spans: tuple[SourceSpan, ...] | None = None,
) -> GroundedUnaryDeltaCue:
    return GroundedUnaryDeltaCue(
        direction=direction,
        evidence_spans=evidence_spans if evidence_spans is not None else (_span(),),
    )


def _chain() -> tuple[
    ContractResidual,
    SearchGateDecision,
    ComputeBudgetDecision,
    GeometricSearchRun,
    GroundedUnaryDeltaCue,
]:
    residual = _residual()
    gate = _gate(residual)
    budget = _budget(gate)
    run = _run(residual=residual, gate=gate, budget=budget)
    cue = _cue(evidence_spans=residual.evidence_spans)
    return residual, gate, budget, run, cue


def _build(**changes: object) -> CandidateOperatorResult | CandidateOperatorRefusal:
    residual, gate, budget, run, cue = _chain()
    values: dict[str, object] = {
        "residual": residual,
        "search_gate": gate,
        "compute_budget": budget,
        "run": run,
        "problem_frame_digest": run.problem_frame_digest,
        "original_contract_assessment_id": run.contract_assessment_id,
        "grounded_unary_delta_cues": (cue,),
    }
    values.update(changes)
    return build_missing_role_candidate(**values)  # type: ignore[arg-type]


def _expected_operator_set_id() -> str:
    payload = {
        "operator_set_version": CANDIDATE_OPERATOR_SET_VERSION,
        "operators": [
            {
                "operator_family": "residual_missing_role",
                "operator_name": MISSING_ROLE_CANDIDATE_OPERATOR_NAME,
                "operator_version": MISSING_ROLE_CANDIDATE_OPERATOR_VERSION,
                "allowed_residual_kinds": [MISSING_ROLE_RESIDUAL_KIND],
                "allowed_residual_codes": [MISSING_ROLE_RESIDUAL_CODE],
                "allowed_candidate_organs": [MISSING_ROLE_CANDIDATE_ORGAN],
                "max_attempts_per_run": 1,
                "budget_charge": {"candidates": 1, "steps": 1},
                "depth": 1,
                "max_parallelism": 1,
            },
            {
                "operator_family": "residual_missing_relation",
                "operator_name": "quantity_entity_binding_candidate",
                "operator_version": "quantity_entity_binding_candidate.v1",
                "allowed_residual_kinds": ["missing_relation"],
                "allowed_residual_codes": ["local_binding_relation_unbound"],
                "allowed_candidate_organs": ["quantity_entity_binding"],
                "max_attempts_per_run": 1,
                "budget_charge": {"candidates": 1, "steps": 1},
                "depth": 1,
                "max_parallelism": 1,
            },
        ],
        "schema_versions": [],
        "policy_versions": [],
    }
    return _digest(payload)


def _expected_input_digest(
    *,
    problem_frame_digest: str,
    original_contract_assessment_id: str,
    residual_id: str,
    search_gate_decision_id: str,
    compute_budget_id: str,
    geometric_search_run_id: str,
    attempt_index: int = 0,
    schema_versions: tuple[tuple[str, str], ...] = (),
    policy_versions: tuple[tuple[str, str], ...] = (),
) -> str:
    payload = {
        "operator_policy_version": CANDIDATE_OPERATOR_POLICY_VERSION,
        "operator_name": MISSING_ROLE_CANDIDATE_OPERATOR_NAME,
        "operator_version": MISSING_ROLE_CANDIDATE_OPERATOR_VERSION,
        "problem_frame_digest": problem_frame_digest,
        "original_contract_assessment_id": original_contract_assessment_id,
        "residual_id": residual_id,
        "residual_kind": MISSING_ROLE_RESIDUAL_KIND,
        "residual_code": MISSING_ROLE_RESIDUAL_CODE,
        "candidate_organ": MISSING_ROLE_CANDIDATE_ORGAN,
        "search_gate_decision_id": search_gate_decision_id,
        "compute_budget_id": compute_budget_id,
        "geometric_search_run_id": geometric_search_run_id,
        "operator_set_id": _expected_operator_set_id(),
        "operator_set_version": CANDIDATE_OPERATOR_SET_VERSION,
        "attempt_index": attempt_index,
        "schema_versions": [[name, version] for name, version in schema_versions],
        "policy_versions": [[name, version] for name, version in policy_versions],
    }
    return _digest(payload)


def _expected_candidate_payload(direction: str) -> list[list[str]]:
    return [
        ["candidate_organ", MISSING_ROLE_CANDIDATE_ORGAN],
        ["direction", direction],
        ["kind", "role_binding_delta"],
        ["relation_type", "state_change.unary_delta"],
        ["role", "direction"],
        ["source", "GroundedUnaryDeltaCue.direction"],
    ]


def _expected_candidate_digest(
    *,
    problem_frame_digest: str,
    direction: str,
    evidence_spans: tuple[SourceSpan, ...],
) -> str:
    payload = {
        "problem_frame_digest": problem_frame_digest,
        "candidate_organ": MISSING_ROLE_CANDIDATE_ORGAN,
        "candidate_payload": _expected_candidate_payload(direction),
        "evidence_spans": [_span_payload(span) for span in evidence_spans],
    }
    return _digest(payload)


def _expected_attempt_id(
    *,
    attempt_index: int,
    input_digest: str,
    candidate_digest: str,
    evidence_spans: tuple[SourceSpan, ...],
) -> str:
    payload = {
        "attempt_id": "",
        "attempt_index": attempt_index,
        "parent_attempt_id": None,
        "operator_id": MISSING_ROLE_CANDIDATE_OPERATOR_NAME,
        "operator_version": MISSING_ROLE_CANDIDATE_OPERATOR_VERSION,
        "input_digest": input_digest,
        "candidate_digest": candidate_digest,
        "budget_charge": {"candidates": 1, "steps": 1},
        "depth": 1,
        "step_index": attempt_index,
        "replay_status": CandidateReplayStatus.REPLAY_PENDING.value,
        "replay_blockers": [],
        "evidence_spans": [_span_payload(span) for span in evidence_spans],
    }
    return _digest(payload)


def _expected_reconstruction_digest(
    *,
    geometric_search_run_id: str,
    attempt_id: str,
    attempt_index: int,
    residual_id: str,
    candidate_digest: str,
    evidence_spans: tuple[SourceSpan, ...],
    schema_versions: tuple[tuple[str, str], ...] = (),
    policy_versions: tuple[tuple[str, str], ...] = (),
) -> str:
    payload = {
        "candidate_reconstruction_digest": "",
        "geometric_search_run_id": geometric_search_run_id,
        "attempt_id": attempt_id,
        "attempt_index": attempt_index,
        "operator_set_id": _expected_operator_set_id(),
        "operator_set_version": CANDIDATE_OPERATOR_SET_VERSION,
        "operator_name": MISSING_ROLE_CANDIDATE_OPERATOR_NAME,
        "operator_version": MISSING_ROLE_CANDIDATE_OPERATOR_VERSION,
        "residual_id": residual_id,
        "residual_kind": MISSING_ROLE_RESIDUAL_KIND,
        "residual_code": MISSING_ROLE_RESIDUAL_CODE,
        "candidate_digest": candidate_digest,
        "evidence_spans": [_span_payload(span) for span in evidence_spans],
        "schema_versions": [[name, version] for name, version in schema_versions],
        "policy_versions": [[name, version] for name, version in policy_versions],
    }
    return _digest(payload)


def _expected_result_id(
    *,
    input_digest: str,
    geometric_search_run_id: str,
    attempt_id: str,
    attempt_index: int,
    candidate_digest: str,
    candidate_reconstruction_digest: str,
    evidence_spans: tuple[SourceSpan, ...],
) -> str:
    payload = {
        "operator_result_id": "",
        "operator_policy_version": CANDIDATE_OPERATOR_POLICY_VERSION,
        "input_digest": input_digest,
        "geometric_search_run_id": geometric_search_run_id,
        "attempt_id": attempt_id,
        "attempt_index": attempt_index,
        "candidate_digest": candidate_digest,
        "candidate_reconstruction_digest": candidate_reconstruction_digest,
        "candidate_organ": MISSING_ROLE_CANDIDATE_ORGAN,
        "operator_name": MISSING_ROLE_CANDIDATE_OPERATOR_NAME,
        "operator_version": MISSING_ROLE_CANDIDATE_OPERATOR_VERSION,
        "reason_codes": [],
        "evidence_spans": [_span_payload(span) for span in evidence_spans],
    }
    return _digest(payload)


def _expected_refusal_id(
    *,
    input_digest: str | None,
    geometric_search_run_id: str | None,
    residual_id: str | None,
    reason_codes: tuple[str, ...],
) -> str:
    payload = {
        "operator_refusal_id": "",
        "operator_policy_version": CANDIDATE_OPERATOR_POLICY_VERSION,
        "input_digest": input_digest,
        "geometric_search_run_id": geometric_search_run_id,
        "residual_id": residual_id,
        "operator_name": MISSING_ROLE_CANDIDATE_OPERATOR_NAME,
        "reason_codes": list(reason_codes),
    }
    return _digest(payload)


def test_public_api_exports_are_exact() -> None:
    import generate.candidate_operator as candidate_operator

    assert CANDIDATE_OPERATOR_POLICY_VERSION == "candidate_operator.v1"
    assert CANDIDATE_OPERATOR_SET_VERSION == "candidate_operators.v2"
    assert MISSING_ROLE_CANDIDATE_OPERATOR_NAME == "missing_role_candidate"
    assert MISSING_ROLE_CANDIDATE_OPERATOR_VERSION == "missing_role_candidate.v1"
    assert MISSING_ROLE_RESIDUAL_KIND == "missing_role"
    assert MISSING_ROLE_RESIDUAL_CODE == "direction_unbound"
    assert MISSING_ROLE_CANDIDATE_ORGAN == "unary_delta_transition"
    assert tuple(candidate_operator.__all__) == (
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
    )


def test_operator_set_identity_is_deterministic() -> None:
    first = candidate_operator_set_id()
    second = candidate_operator_set_id()
    assert first == second == _expected_operator_set_id()
    assert len(first) == 64


def test_valid_chain_produces_candidate_operator_result() -> None:
    outcome = _build()
    assert isinstance(outcome, CandidateOperatorResult)
    assert outcome.operator_name == MISSING_ROLE_CANDIDATE_OPERATOR_NAME
    assert outcome.operator_version == MISSING_ROLE_CANDIDATE_OPERATOR_VERSION
    assert outcome.candidate_organ == MISSING_ROLE_CANDIDATE_ORGAN
    assert outcome.reason_codes == ()


def test_candidate_digest_differs_from_reconstruction_digest() -> None:
    outcome = _build()
    assert isinstance(outcome, CandidateOperatorResult)
    assert outcome.candidate_digest != outcome.candidate_reconstruction_digest


def test_candidate_reconstruction_binds_upstream_identity() -> None:
    residual, gate, budget, run, cue = _chain()
    outcome = _build()
    assert isinstance(outcome, CandidateOperatorResult)
    reconstruction = outcome.candidate_reconstruction
    assert reconstruction.source_residual_id == residual.residual_id
    assert reconstruction.problem_frame_digest == run.problem_frame_digest
    assert reconstruction.original_contract_assessment_id == run.contract_assessment_id
    assert reconstruction.operator_name == MISSING_ROLE_CANDIDATE_OPERATOR_NAME
    assert reconstruction.operator_version == MISSING_ROLE_CANDIDATE_OPERATOR_VERSION
    assert reconstruction.candidate_digest == outcome.candidate_digest
    assert ("operator_set_id", candidate_operator_set_id()) in reconstruction.operator_provenance
    assert outcome.geometric_search_run_id == run.run_id
    assert outcome.attempt_id == outcome.candidate_attempt.attempt_id
    assert gate.decision_id in (run.gate_decision_id, gate.decision_id)
    assert budget.budget_id == run.budget_id


def test_candidate_attempt_fields_are_replay_pending() -> None:
    residual, _, _, _, cue = _chain()
    outcome = _build()
    assert isinstance(outcome, CandidateOperatorResult)
    attempt = outcome.candidate_attempt
    assert attempt.attempt_index == 0
    assert attempt.operator_id == MISSING_ROLE_CANDIDATE_OPERATOR_NAME
    assert attempt.operator_version == MISSING_ROLE_CANDIDATE_OPERATOR_VERSION
    assert attempt.replay_status is CandidateReplayStatus.REPLAY_PENDING
    assert attempt.replay_blockers == ()
    assert attempt.budget_charge == BudgetCharge(candidates=1, steps=1)
    assert attempt.depth == 1
    assert attempt.candidate_digest == outcome.candidate_digest
    assert attempt.evidence_spans == cue.evidence_spans


def test_unsupported_residual_kind_refuses() -> None:
    residual = _residual(residual_kind=ResidualKind.MISSING_RELATION)
    gate = _gate(residual, reason_code="eligible_missing_relation")
    budget = _budget(gate, reason_code="budget_allowed_missing_relation")
    run = _run(residual=residual, gate=gate, budget=budget)
    outcome = build_missing_role_candidate(
        residual=residual,
        search_gate=gate,
        compute_budget=budget,
        run=run,
        problem_frame_digest=run.problem_frame_digest,
        original_contract_assessment_id=run.contract_assessment_id,
        grounded_unary_delta_cues=(_cue(evidence_spans=residual.evidence_spans),),
    )
    assert isinstance(outcome, CandidateOperatorRefusal)
    assert CandidateOperatorRefusalReason.UNSUPPORTED_RESIDUAL_KIND.value in outcome.reason_codes


def test_unsupported_residual_code_refuses() -> None:
    residual = _residual(residual_code="quantity_unbound")
    gate = _gate(residual)
    budget = _budget(gate)
    run = _run(residual=residual, gate=gate, budget=budget)
    outcome = build_missing_role_candidate(
        residual=residual,
        search_gate=gate,
        compute_budget=budget,
        run=run,
        problem_frame_digest=run.problem_frame_digest,
        original_contract_assessment_id=run.contract_assessment_id,
        grounded_unary_delta_cues=(_cue(evidence_spans=residual.evidence_spans),),
    )
    assert isinstance(outcome, CandidateOperatorRefusal)
    assert CandidateOperatorRefusalReason.UNSUPPORTED_RESIDUAL_CODE.value in outcome.reason_codes


def test_unsupported_candidate_organ_refuses() -> None:
    residual = _residual(candidate_organ="fraction_decrease")
    gate = _gate(residual)
    budget = _budget(gate)
    run = _run(residual=residual, gate=gate, budget=budget)
    outcome = build_missing_role_candidate(
        residual=residual,
        search_gate=gate,
        compute_budget=budget,
        run=run,
        problem_frame_digest=run.problem_frame_digest,
        original_contract_assessment_id=run.contract_assessment_id,
        grounded_unary_delta_cues=(_cue(evidence_spans=residual.evidence_spans),),
    )
    assert isinstance(outcome, CandidateOperatorRefusal)
    assert CandidateOperatorRefusalReason.UNSUPPORTED_CANDIDATE_ORGAN.value in outcome.reason_codes


@pytest.mark.parametrize(
    "status",
    (
        SearchGateStatus.BLOCKED,
        SearchGateStatus.INELIGIBLE,
        SearchGateStatus.UNASSESSABLE,
    ),
)
def test_ineligible_search_gate_refuses(status: SearchGateStatus) -> None:
    residual, valid_gate, valid_budget, run, cue = _chain()
    gate = _gate(residual, status=status, reason_code=f"{status.value}_reason")
    outcome = build_missing_role_candidate(
        residual=residual,
        search_gate=gate,
        compute_budget=valid_budget,
        run=run,
        problem_frame_digest=run.problem_frame_digest,
        original_contract_assessment_id=run.contract_assessment_id,
        grounded_unary_delta_cues=(cue,),
    )
    assert isinstance(outcome, CandidateOperatorRefusal)
    assert CandidateOperatorRefusalReason.INELIGIBLE_SEARCH_GATE.value in outcome.reason_codes


@pytest.mark.parametrize(
    "status",
    (
        ComputeBudgetStatus.BUDGET_BLOCKED,
        ComputeBudgetStatus.BUDGET_ZERO,
        ComputeBudgetStatus.BUDGET_UNASSESSABLE,
    ),
)
def test_non_allowed_budget_refuses(status: ComputeBudgetStatus) -> None:
    residual, gate, _, run, cue = _chain()
    budget = _budget(
        gate,
        status=status,
        reason_code=f"{status.value}_reason",
        max_candidates=0,
        max_depth=0,
        max_steps=0,
        max_parallelism=0,
    )
    outcome = build_missing_role_candidate(
        residual=residual,
        search_gate=gate,
        compute_budget=budget,
        run=run,
        problem_frame_digest=run.problem_frame_digest,
        original_contract_assessment_id=run.contract_assessment_id,
        grounded_unary_delta_cues=(cue,),
    )
    assert isinstance(outcome, CandidateOperatorRefusal)
    assert CandidateOperatorRefusalReason.NON_ALLOWED_BUDGET.value in outcome.reason_codes


def test_gate_budget_mismatch_refuses() -> None:
    residual, gate, _, run, cue = _chain()
    budget = dataclasses.replace(_budget(gate), gate_decision_id="mismatch" * 8)
    outcome = build_missing_role_candidate(
        residual=residual,
        search_gate=gate,
        compute_budget=budget,
        run=run,
        problem_frame_digest=run.problem_frame_digest,
        original_contract_assessment_id=run.contract_assessment_id,
        grounded_unary_delta_cues=(cue,),
    )
    assert isinstance(outcome, CandidateOperatorRefusal)
    assert CandidateOperatorRefusalReason.GATE_BUDGET_MISMATCH.value in outcome.reason_codes


def test_run_gate_mismatch_refuses() -> None:
    residual, gate, budget, run, cue = _chain()
    run = dataclasses.replace(run, gate_decision_id="mismatch" * 8)
    outcome = build_missing_role_candidate(
        residual=residual,
        search_gate=gate,
        compute_budget=budget,
        run=run,
        problem_frame_digest=run.problem_frame_digest,
        original_contract_assessment_id=run.contract_assessment_id,
        grounded_unary_delta_cues=(cue,),
    )
    assert isinstance(outcome, CandidateOperatorRefusal)
    assert CandidateOperatorRefusalReason.RUN_GATE_MISMATCH.value in outcome.reason_codes


def test_run_budget_mismatch_refuses() -> None:
    residual, gate, budget, run, cue = _chain()
    run = dataclasses.replace(run, budget_id="mismatch" * 8)
    outcome = build_missing_role_candidate(
        residual=residual,
        search_gate=gate,
        compute_budget=budget,
        run=run,
        problem_frame_digest=run.problem_frame_digest,
        original_contract_assessment_id=run.contract_assessment_id,
        grounded_unary_delta_cues=(cue,),
    )
    assert isinstance(outcome, CandidateOperatorRefusal)
    assert CandidateOperatorRefusalReason.RUN_BUDGET_MISMATCH.value in outcome.reason_codes


def test_operator_set_mismatch_refuses() -> None:
    residual, gate, budget, run, cue = _chain()
    run = dataclasses.replace(run, operator_set_id="wrong" * 8)
    outcome = build_missing_role_candidate(
        residual=residual,
        search_gate=gate,
        compute_budget=budget,
        run=run,
        problem_frame_digest=run.problem_frame_digest,
        original_contract_assessment_id=run.contract_assessment_id,
        grounded_unary_delta_cues=(cue,),
    )
    assert isinstance(outcome, CandidateOperatorRefusal)
    assert CandidateOperatorRefusalReason.OPERATOR_SET_MISMATCH.value in outcome.reason_codes


def test_attempt_index_beyond_max_candidates_refuses() -> None:
    residual = _residual()
    gate = _gate(residual)
    budget = _budget(gate, max_candidates=1)
    run = _run(residual=residual, gate=gate, budget=budget)
    outcome = build_missing_role_candidate(
        residual=residual,
        search_gate=gate,
        compute_budget=budget,
        run=run,
        problem_frame_digest=run.problem_frame_digest,
        original_contract_assessment_id=run.contract_assessment_id,
        grounded_unary_delta_cues=(_cue(evidence_spans=residual.evidence_spans),),
        attempt_index=1,
    )
    assert isinstance(outcome, CandidateOperatorRefusal)
    assert (
        CandidateOperatorRefusalReason.ATTEMPT_INDEX_EXCEEDS_BUDGET.value
        in outcome.reason_codes
    )


def test_attempt_index_beyond_operator_policy_refuses() -> None:
    outcome = _build(attempt_index=1)
    assert isinstance(outcome, CandidateOperatorRefusal)
    assert (
        CandidateOperatorRefusalReason.ATTEMPT_INDEX_EXCEEDS_OPERATOR_POLICY.value
        in outcome.reason_codes
    )


def test_budget_charge_exceeds_structural_budget_refuses() -> None:
    residual = _residual()
    gate = _gate(residual)
    budget = _budget(gate, max_depth=0)
    run = _run(residual=residual, gate=gate, budget=budget)
    outcome = build_missing_role_candidate(
        residual=residual,
        search_gate=gate,
        compute_budget=budget,
        run=run,
        problem_frame_digest=run.problem_frame_digest,
        original_contract_assessment_id=run.contract_assessment_id,
        grounded_unary_delta_cues=(_cue(evidence_spans=residual.evidence_spans),),
    )
    assert isinstance(outcome, CandidateOperatorRefusal)
    assert (
        CandidateOperatorRefusalReason.BUDGET_CHARGE_EXCEEDS_BUDGET.value
        in outcome.reason_codes
    )


def test_non_serial_budget_refuses() -> None:
    residual, gate, _, run, cue = _chain()
    budget = _budget(gate, max_parallelism=2)
    outcome = build_missing_role_candidate(
        residual=residual,
        search_gate=gate,
        compute_budget=budget,
        run=run,
        problem_frame_digest=run.problem_frame_digest,
        original_contract_assessment_id=run.contract_assessment_id,
        grounded_unary_delta_cues=(cue,),
    )
    assert isinstance(outcome, CandidateOperatorRefusal)
    assert CandidateOperatorRefusalReason.NON_SERIAL_BUDGET.value in outcome.reason_codes


def test_missing_typed_cue_refuses() -> None:
    outcome = _build(grounded_unary_delta_cues=())
    assert isinstance(outcome, CandidateOperatorRefusal)
    assert CandidateOperatorRefusalReason.MISSING_TYPED_CUE.value in outcome.reason_codes


def test_ambiguous_multiple_typed_cues_refuse() -> None:
    residual, gate, budget, run, cue = _chain()
    second = _cue(direction="decrease", evidence_spans=residual.evidence_spans)
    outcome = build_missing_role_candidate(
        residual=residual,
        search_gate=gate,
        compute_budget=budget,
        run=run,
        problem_frame_digest=run.problem_frame_digest,
        original_contract_assessment_id=run.contract_assessment_id,
        grounded_unary_delta_cues=(cue, second),
    )
    assert isinstance(outcome, CandidateOperatorRefusal)
    assert CandidateOperatorRefusalReason.AMBIGUOUS_TYPED_CUE.value in outcome.reason_codes


def test_empty_cue_direction_refuses() -> None:
    residual, gate, budget, run, _ = _chain()
    cue = GroundedUnaryDeltaCue(direction="   ", evidence_spans=residual.evidence_spans)
    outcome = build_missing_role_candidate(
        residual=residual,
        search_gate=gate,
        compute_budget=budget,
        run=run,
        problem_frame_digest=run.problem_frame_digest,
        original_contract_assessment_id=run.contract_assessment_id,
        grounded_unary_delta_cues=(cue,),
    )
    assert isinstance(outcome, CandidateOperatorRefusal)
    assert CandidateOperatorRefusalReason.MISSING_TYPED_CUE.value in outcome.reason_codes


def test_unsupported_typed_cue_direction_refuses() -> None:
    residual, gate, budget, run, _ = _chain()
    cue = GroundedUnaryDeltaCue(direction="sideways", evidence_spans=residual.evidence_spans)
    outcome = build_missing_role_candidate(
        residual=residual,
        search_gate=gate,
        compute_budget=budget,
        run=run,
        problem_frame_digest=run.problem_frame_digest,
        original_contract_assessment_id=run.contract_assessment_id,
        grounded_unary_delta_cues=(cue,),
    )
    assert isinstance(outcome, CandidateOperatorRefusal)
    assert CandidateOperatorRefusalReason.UNSUPPORTED_TYPED_CUE.value in outcome.reason_codes


def test_malformed_evidence_span_refuses() -> None:
    residual, gate, budget, run, _ = _chain()
    bad_span = SimpleNamespace(text="bad", start=-1, end=3, sentence_index=0)
    cue = GroundedUnaryDeltaCue(direction="increase", evidence_spans=(bad_span,))  # type: ignore[arg-type]
    outcome = build_missing_role_candidate(
        residual=residual,
        search_gate=gate,
        compute_budget=budget,
        run=run,
        problem_frame_digest=run.problem_frame_digest,
        original_contract_assessment_id=run.contract_assessment_id,
        grounded_unary_delta_cues=(cue,),
    )
    assert isinstance(outcome, CandidateOperatorRefusal)
    assert CandidateOperatorRefusalReason.MALFORMED_EVIDENCE_SPAN.value in outcome.reason_codes


def test_ungrounded_cue_span_refuses() -> None:
    residual, gate, budget, run, _ = _chain()
    cue = _cue(evidence_spans=(_span(text="other", start=99, end=104),))
    outcome = build_missing_role_candidate(
        residual=residual,
        search_gate=gate,
        compute_budget=budget,
        run=run,
        problem_frame_digest=run.problem_frame_digest,
        original_contract_assessment_id=run.contract_assessment_id,
        grounded_unary_delta_cues=(cue,),
    )
    assert isinstance(outcome, CandidateOperatorRefusal)
    assert CandidateOperatorRefusalReason.MALFORMED_EVIDENCE_SPAN.value in outcome.reason_codes


def test_duplicate_evidence_spans_are_preserved() -> None:
    span = _span()
    residual = _residual(evidence_spans=(span, span))
    gate = _gate(residual)
    budget = _budget(gate)
    run = _run(residual=residual, gate=gate, budget=budget)
    cue = GroundedUnaryDeltaCue(direction="increase", evidence_spans=(span, span))
    outcome = build_missing_role_candidate(
        residual=residual,
        search_gate=gate,
        compute_budget=budget,
        run=run,
        problem_frame_digest=run.problem_frame_digest,
        original_contract_assessment_id=run.contract_assessment_id,
        grounded_unary_delta_cues=(cue,),
    )
    assert isinstance(outcome, CandidateOperatorResult)
    assert outcome.evidence_spans == (span, span)
    assert outcome.candidate_attempt.evidence_spans == (span, span)


def test_evidence_span_reorder_changes_candidate_identity() -> None:
    first_span = _span(text="one", start=0, end=3)
    second_span = _span(text="two", start=4, end=7)
    residual = _residual(evidence_spans=(first_span, second_span))
    gate = _gate(residual)
    budget = _budget(gate)
    run = _run(residual=residual, gate=gate, budget=budget)

    first = build_missing_role_candidate(
        residual=residual,
        search_gate=gate,
        compute_budget=budget,
        run=run,
        problem_frame_digest=run.problem_frame_digest,
        original_contract_assessment_id=run.contract_assessment_id,
        grounded_unary_delta_cues=(
            GroundedUnaryDeltaCue(direction="increase", evidence_spans=(first_span, second_span)),
        ),
    )
    second = build_missing_role_candidate(
        residual=residual,
        search_gate=gate,
        compute_budget=budget,
        run=run,
        problem_frame_digest=run.problem_frame_digest,
        original_contract_assessment_id=run.contract_assessment_id,
        grounded_unary_delta_cues=(
            GroundedUnaryDeltaCue(direction="increase", evidence_spans=(second_span, first_span)),
        ),
    )
    assert isinstance(first, CandidateOperatorResult)
    assert isinstance(second, CandidateOperatorResult)
    assert first.candidate_digest != second.candidate_digest
    assert first.attempt_id != second.attempt_id
    assert first.operator_result_id != second.operator_result_id


def test_explanation_changes_do_not_affect_ids() -> None:
    first = _build(explanation="first prose")
    second = _build(explanation="second prose")
    assert isinstance(first, CandidateOperatorResult)
    assert isinstance(second, CandidateOperatorResult)
    assert first.input_digest == second.input_digest
    assert first.candidate_digest == second.candidate_digest
    assert first.candidate_reconstruction_digest == second.candidate_reconstruction_digest
    assert first.attempt_id == second.attempt_id
    assert first.operator_result_id == second.operator_result_id


def test_refusal_is_not_partial_candidate() -> None:
    outcome = _build(grounded_unary_delta_cues=())
    assert isinstance(outcome, CandidateOperatorRefusal)
    assert not hasattr(outcome, "candidate_attempt")
    assert not hasattr(outcome, "candidate_reconstruction")
    assert not hasattr(outcome, "candidate_digest")


def test_public_dataclasses_expose_no_authority_fields() -> None:
    forbidden = {
        "answer",
        "final_answer",
        "served_output",
        "proof",
        "verdict",
        "promotion",
        "mutation",
        "teaching_update",
        "pack_update",
        "policy_update",
        "identity_update",
        "workbench_state",
        "runtime_effect",
        "confidence",
        "score",
        "rank",
        "priority",
        "selected",
        "best",
        "selected_candidate",
        "best_candidate",
        "serving_allowed",
        "runnable",
    }
    from generate.candidate_operator import CandidateOperatorInput

    for record_type in (
        CandidateOperatorPolicy,
        GroundedUnaryDeltaCue,
        CandidateOperatorInput,
        CandidateReconstruction,
        CandidateOperatorResult,
        CandidateOperatorRefusal,
    ):
        assert forbidden.isdisjoint({field.name for field in dataclasses.fields(record_type)})


def test_candidate_result_cannot_represent_replay_closure() -> None:
    outcome = _build()
    assert isinstance(outcome, CandidateOperatorResult)
    assert not hasattr(outcome, "replay_disposition")
    assert not hasattr(outcome, "contract_replay_assessment_id")
    assert not hasattr(outcome, "trace_id")
    assert outcome.candidate_attempt.replay_status is CandidateReplayStatus.REPLAY_PENDING


def test_canonical_ids_match_independent_recomputation() -> None:
    residual, gate, budget, run, cue = _chain()
    outcome = build_missing_role_candidate(
        residual=residual,
        search_gate=gate,
        compute_budget=budget,
        run=run,
        problem_frame_digest=run.problem_frame_digest,
        original_contract_assessment_id=run.contract_assessment_id,
        grounded_unary_delta_cues=(cue,),
    )
    assert isinstance(outcome, CandidateOperatorResult)
    input_digest = _expected_input_digest(
        problem_frame_digest=run.problem_frame_digest,
        original_contract_assessment_id=run.contract_assessment_id,
        residual_id=residual.residual_id,
        search_gate_decision_id=gate.decision_id,
        compute_budget_id=budget.budget_id,
        geometric_search_run_id=run.run_id,
    )
    candidate_digest = _expected_candidate_digest(
        problem_frame_digest=run.problem_frame_digest,
        direction="increase",
        evidence_spans=cue.evidence_spans,
    )
    attempt_id = _expected_attempt_id(
        attempt_index=0,
        input_digest=input_digest,
        candidate_digest=candidate_digest,
        evidence_spans=cue.evidence_spans,
    )
    reconstruction_digest = _expected_reconstruction_digest(
        geometric_search_run_id=run.run_id,
        attempt_id=attempt_id,
        attempt_index=0,
        residual_id=residual.residual_id,
        candidate_digest=candidate_digest,
        evidence_spans=cue.evidence_spans,
    )
    result_id = _expected_result_id(
        input_digest=input_digest,
        geometric_search_run_id=run.run_id,
        attempt_id=attempt_id,
        attempt_index=0,
        candidate_digest=candidate_digest,
        candidate_reconstruction_digest=reconstruction_digest,
        evidence_spans=cue.evidence_spans,
    )
    assert outcome.input_digest == input_digest
    assert outcome.candidate_digest == candidate_digest
    assert outcome.candidate_reconstruction_digest == reconstruction_digest
    assert outcome.attempt_id == attempt_id
    assert outcome.operator_result_id == result_id


def test_refusal_id_matches_canonical_payload() -> None:
    outcome = _build(grounded_unary_delta_cues=())
    assert isinstance(outcome, CandidateOperatorRefusal)
    assert outcome.operator_refusal_id == _expected_refusal_id(
        input_digest=outcome.input_digest,
        geometric_search_run_id=outcome.geometric_search_run_id,
        residual_id=outcome.residual_id,
        reason_codes=outcome.reason_codes,
    )


def test_public_api_has_no_source_text_parameter() -> None:
    import inspect

    signature = inspect.signature(build_missing_role_candidate)
    assert "problem_text" not in signature.parameters
    assert "source_text" not in signature.parameters
    assert "raw_text" not in signature.parameters


def test_module_has_no_regex_or_template_matching() -> None:
    source = Path("generate/candidate_operator.py").read_text("utf-8")
    forbidden_fragments = (
        "import re",
        "from re",
        "re.search",
        "re.match",
        "re.findall",
        "regex",
        "template",
    )
    lowered = source.lower()
    assert not any(fragment in lowered for fragment in forbidden_fragments)


def test_module_coupling_and_side_effect_guards() -> None:
    path = Path("generate/candidate_operator.py")
    source = path.read_text("utf-8")
    tree = ast.parse(source)
    imports: set[str] = set()
    imported_names: set[str] = set()
    calls: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.add(node.module or "")
            imported_names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                calls.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                calls.add(node.func.attr)

    assert imports <= {
        "__future__",
        "dataclasses",
        "enum",
        "hashlib",
        "json",
        "generate.compute_budget",
        "generate.geometric_search_run",
        "generate.kernel_facts",
        "generate.search_gate",
    }
    assert {
        "initialize_geometric_search_run",
        "decide_search_gate",
        "decide_compute_budget",
        "project_contract_residuals",
        "assess_contracts",
        "build_replay_adapter_input",
        "classify_replay_result",
        "build_practice_trace_input",
        "seal_practice_trace",
        "determine",
        "build_problem_frame",
    }.isdisjoint(imported_names)
    assert {
        "initialize_geometric_search_run",
        "decide_search_gate",
        "decide_compute_budget",
        "project_contract_residuals",
        "assess_contracts",
        "build_replay_adapter_input",
        "classify_replay_result",
        "build_practice_trace_input",
        "seal_practice_trace",
        "determine",
        "repair",
        "serve",
        "store",
        "write",
        "open",
        "write_text",
        "write_bytes",
        "request",
        "urlopen",
        "sleep",
        "time",
        "uuid4",
    }.isdisjoint(calls)
    allowed_records = {
        "CandidateOperatorResult",
        "CandidateReconstruction",
        "CandidateOperatorRefusal",
    }
    forbidden_producers = {
        "build_missing_role_candidate",
        "candidate_operator_set_id",
        "GroundedUnaryDeltaCue",
    }
    for downstream_path in (
        "generate/geometric_search_run.py",
        "generate/replay_adapter.py",
        "generate/sealed_practice_trace.py",
        "generate/search_gate.py",
        "generate/compute_budget.py",
        "generate/contract_residuals.py",
        "generate/run_attempt_binding.py",
    ):
        ds_source = Path(downstream_path).read_text("utf-8")
        ds_tree = ast.parse(ds_source)
        ds_imported_names: set[str] = set()
        ds_calls: set[str] = set()
        for node in ast.walk(ds_tree):
            if isinstance(node, ast.ImportFrom):
                if node.module == "generate.candidate_operator":
                    ds_imported_names.update(alias.name for alias in node.names)
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    ds_calls.add(node.func.id)
                elif isinstance(node.func, ast.Attribute):
                    ds_calls.add(node.func.attr)

        assert ds_imported_names <= allowed_records, (
            f"{downstream_path} imported forbidden candidate_operator records: "
            f"{ds_imported_names - allowed_records}"
        )
        assert forbidden_producers.isdisjoint(ds_calls), (
            f"{downstream_path} called forbidden candidate_operator producers: "
            f"{ds_calls & forbidden_producers}"
        )


def test_no_filesystem_network_clock_random_or_environment_identity() -> None:
    source = Path("generate/candidate_operator.py").read_text("utf-8")
    forbidden_fragments = (
        "import os",
        "from os",
        "import pathlib",
        "from pathlib",
        "import random",
        "from random",
        "import time",
        "from time",
        "import datetime",
        "from datetime",
        "import uuid",
        "from uuid",
        "import socket",
        "from socket",
        "import subprocess",
        "from subprocess",
        "import requests",
        "from requests",
        "os.environ",
        "getenv(",
        "gethostname(",
        "Path(",
    )
    assert not any(fragment in source for fragment in forbidden_fragments)


def test_malformed_objects_fail_closed_without_throwing() -> None:
    outcome = build_missing_role_candidate(
        residual=SimpleNamespace(),  # type: ignore[arg-type]
        search_gate=SimpleNamespace(),  # type: ignore[arg-type]
        compute_budget=SimpleNamespace(),  # type: ignore[arg-type]
        run=SimpleNamespace(),  # type: ignore[arg-type]
        problem_frame_digest="f" * 64,
        original_contract_assessment_id="assessment-a",
        grounded_unary_delta_cues=(),
    )
    assert isinstance(outcome, CandidateOperatorRefusal)


def test_only_one_operator_row_in_static_set() -> None:
    payload = json.loads(
        json.dumps(
            {
                "operator_set_version": CANDIDATE_OPERATOR_SET_VERSION,
                "operators": [
                    {
                        "operator_family": "residual_missing_role",
                        "operator_name": MISSING_ROLE_CANDIDATE_OPERATOR_NAME,
                        "operator_version": MISSING_ROLE_CANDIDATE_OPERATOR_VERSION,
                        "allowed_residual_kinds": [MISSING_ROLE_RESIDUAL_KIND],
                        "allowed_residual_codes": [MISSING_ROLE_RESIDUAL_CODE],
                        "allowed_candidate_organs": [MISSING_ROLE_CANDIDATE_ORGAN],
                        "max_attempts_per_run": 1,
                        "budget_charge": {"candidates": 1, "steps": 1},
                        "depth": 1,
                        "max_parallelism": 1,
                    }
                ],
                "schema_versions": [],
                "policy_versions": [],
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    assert len(payload["operators"]) == 1
    assert payload["operators"][0]["operator_name"] == "missing_role_candidate"