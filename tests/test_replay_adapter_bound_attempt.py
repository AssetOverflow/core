from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from types import SimpleNamespace

from generate.candidate_operator import (
    GroundedUnaryDeltaCue,
    build_missing_role_candidate,
    candidate_operator_set_id,
    GroundedQuantityEntityCue,
    build_quantity_entity_binding_candidate,
    QUANTITY_ENTITY_BINDING_CANDIDATE_ORGAN,
)
from generate.compute_budget import ComputeBudgetDecision, ComputeBudgetStatus
from generate.contract_residuals import ContractResidual, ResidualKind, ResidualSourceAxis
from generate.geometric_search_run import GeometricSearchRun, initialize_geometric_search_run
from generate.kernel_facts import SourceSpan
from generate.replay_adapter import (
    CONTRACT_PROOF_REPLAY_POLICY_VERSION,
    ReplayAdapterInput,
    ReplayAdapterRefusal,
    ReplayRefusalReason,
    build_replay_adapter_input_from_binding,
    VACUOUS_PROOF_DECLARATION,
    classify_replay_result,
    ReplayAdapterResult,
    ReplayDisposition,
)
from generate.run_attempt_binding import (
    CandidateAttemptRunBinding,
    bind_candidate_attempt_to_run,
)
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


def _residual() -> ContractResidual:
    spans = (SourceSpan(text="gained", start=10, end=16, sentence_index=0),)
    residual_id = _digest(
        {
            "candidate_organ": "unary_delta_transition",
            "residual_kind": ResidualKind.MISSING_ROLE.value,
            "residual_code": "direction_unbound",
            "evidence_spans": [_span_payload(span) for span in spans],
        }
    )
    return ContractResidual(
        residual_id=residual_id,
        candidate_organ="unary_delta_transition",
        family_id="state_change.unary_delta",
        residual_kind=ResidualKind.MISSING_ROLE,
        residual_code="direction_unbound",
        source_axis=ResidualSourceAxis.ROLE,
        evidence_spans=spans,
        explanation="residual prose",
    )


def _gate(residual: ContractResidual) -> SearchGateDecision:
    payload = {
        "policy_version": "search_gate.v1",
        "input_digest": "a" * 64,
        "residual_ids": [residual.residual_id],
        "candidate_organ": residual.candidate_organ,
        "status": SearchGateStatus.ELIGIBLE.value,
        "reason_code": "eligible_missing_role",
        "evidence_spans": [_span_payload(span) for span in residual.evidence_spans],
    }
    return SearchGateDecision(
        decision_id=_digest(payload),
        policy_version="search_gate.v1",
        input_digest="a" * 64,
        residual_ids=(residual.residual_id,),
        candidate_organ=residual.candidate_organ,
        status=SearchGateStatus.ELIGIBLE,
        reason_code="eligible_missing_role",
        evidence_spans=residual.evidence_spans,
        explanation="gate prose",
    )


def _budget(gate: SearchGateDecision) -> ComputeBudgetDecision:
    payload = {
        "policy_version": "compute_budget.v1",
        "gate_decision_id": gate.decision_id,
        "gate_policy_version": gate.policy_version,
        "gate_input_digest": gate.input_digest,
        "status": ComputeBudgetStatus.BUDGET_ALLOWED.value,
        "reason_code": "budget_allowed_missing_role",
        "max_candidates": 5,
        "max_depth": 2,
        "max_steps": 10,
        "max_parallelism": 1,
        "evidence_spans": [_span_payload(span) for span in gate.evidence_spans],
    }
    return ComputeBudgetDecision(
        budget_id=_digest(payload),
        policy_version="compute_budget.v1",
        gate_decision_id=gate.decision_id,
        gate_policy_version=gate.policy_version,
        gate_input_digest=gate.input_digest,
        status=ComputeBudgetStatus.BUDGET_ALLOWED,
        reason_code="budget_allowed_missing_role",
        max_candidates=5,
        max_depth=2,
        max_steps=10,
        max_wallclock_ms=None,
        max_parallelism=1,
        evidence_spans=gate.evidence_spans,
        explanation="budget prose",
    )


def _chain() -> tuple[GeometricSearchRun, object, CandidateAttemptRunBinding]:
    residual = _residual()
    gate = _gate(residual)
    budget = _budget(gate)
    run = initialize_geometric_search_run(
        problem_frame_digest="f" * 64,
        contract_assessment_id="assessment-a",
        residual_ids=(residual.residual_id,),
        gate_decision=gate,
        compute_budget=budget,
        operator_set_id=candidate_operator_set_id(),
        operator_set_version="candidate_operators.v2",
    )
    assert isinstance(run, GeometricSearchRun)
    result = build_missing_role_candidate(
        residual=residual,
        search_gate=gate,
        compute_budget=budget,
        run=run,
        problem_frame_digest=run.problem_frame_digest,
        original_contract_assessment_id=run.contract_assessment_id,
        grounded_unary_delta_cues=(
            GroundedUnaryDeltaCue(
                direction="increase",
                evidence_spans=residual.evidence_spans,
            ),
        ),
    )
    assert hasattr(result, "candidate_attempt")
    binding = bind_candidate_attempt_to_run(
        original_run=run,
        candidate_operator_result=result,
    )
    assert isinstance(binding, CandidateAttemptRunBinding)
    return run, result, binding


def _bound_input(
    run: GeometricSearchRun,
    result: object,
    binding: CandidateAttemptRunBinding,
    **kwargs: object,
) -> ReplayAdapterInput | ReplayAdapterRefusal:
    return build_replay_adapter_input_from_binding(
        run=run,
        binding=binding,
        candidate_operator_result=result,  # type: ignore[arg-type]
        **kwargs,
    )


def _refused(
    expected_reason: ReplayRefusalReason,
    expected_code: str,
    *,
    run: GeometricSearchRun,
    result: object,
    binding: object,
    **kwargs: object,
) -> None:
    outcome = build_replay_adapter_input_from_binding(
        run=run,
        binding=binding,  # type: ignore[arg-type]
        candidate_operator_result=result,  # type: ignore[arg-type]
        **kwargs,
    )
    assert isinstance(outcome, ReplayAdapterRefusal)
    assert outcome.replay_disposition is expected_reason
    assert outcome.reason_codes == (expected_code,)


def test_valid_bound_attempt_builds_replay_input_without_mutating_run() -> None:
    run, result, binding = _chain()
    before = run.candidate_attempts
    outcome = _bound_input(run, result, binding)
    assert isinstance(outcome, ReplayAdapterInput)
    assert outcome.run_id == run.run_id
    assert outcome.run_policy_version == run.run_policy_version
    assert outcome.attempt_id == binding.candidate_attempt_id
    assert outcome.attempt_index == binding.attempt_index
    assert outcome.candidate_digest == binding.candidate_digest
    assert outcome.candidate_reconstruction_digest == binding.candidate_reconstruction_digest
    assert outcome.problem_frame_digest == run.problem_frame_digest
    assert outcome.original_contract_assessment_id == run.contract_assessment_id
    assert outcome.candidate_organ == result.candidate_organ
    assert outcome.residual_ids == run.residual_ids
    assert outcome.gate_decision_id == run.gate_decision_id
    assert outcome.budget_id == run.budget_id
    assert outcome.operator_set_id == run.operator_set_id
    assert outcome.operator_set_version == run.operator_set_version
    assert outcome.contract_replay_target == "problem_frame_contracts.unary_delta"
    assert run.candidate_attempts == before == ()


def test_bound_input_digest_is_deterministic_and_binding_explanation_free() -> None:
    run, result, binding = _chain()
    first = _bound_input(run, result, binding)
    changed_binding = replace(binding, explanation="different prose")
    second = _bound_input(run, result, changed_binding)
    assert isinstance(first, ReplayAdapterInput)
    assert isinstance(second, ReplayAdapterInput)
    assert first.input_digest == second.input_digest


def test_invalid_bound_input_types_refuse() -> None:
    run, result, binding = _chain()
    outcome = build_replay_adapter_input_from_binding(
        run=SimpleNamespace(),  # type: ignore[arg-type]
        binding=binding,
        candidate_operator_result=result,
    )
    assert isinstance(outcome, ReplayAdapterRefusal)
    assert outcome.reason_codes == ("invalid_run_type",)
    _refused(
        ReplayRefusalReason.INVALID_REPLAY_INPUT,
        "invalid_binding_type",
        run=run,
        result=result,
        binding=SimpleNamespace(),
    )
    _refused(
        ReplayRefusalReason.INVALID_REPLAY_INPUT,
        "invalid_operator_result_type",
        run=run,
        result=SimpleNamespace(),
        binding=binding,
    )


def test_binding_identity_mismatches_refuse() -> None:
    run, result, binding = _chain()
    _refused(
        ReplayRefusalReason.CANDIDATE_IDENTITY_MISMATCH,
        "binding_run_mismatch",
        run=run,
        result=result,
        binding=replace(binding, original_run_id="wrong"),
    )
    _refused(
        ReplayRefusalReason.CANDIDATE_IDENTITY_MISMATCH,
        "binding_result_mismatch",
        run=run,
        result=result,
        binding=replace(binding, operator_result_id="wrong"),
    )
    _refused(
        ReplayRefusalReason.CANDIDATE_IDENTITY_MISMATCH,
        "binding_not_structurally_bound",
        run=run,
        result=result,
        binding=replace(binding, run_attempt_membership="other"),
    )
    _refused(
        ReplayRefusalReason.CANDIDATE_IDENTITY_MISMATCH,
        "binding_not_successful",
        run=run,
        result=result,
        binding=replace(binding, reason_codes=("blocked",)),
    )


def test_result_and_attempt_mismatches_refuse() -> None:
    run, result, binding = _chain()
    _refused(
        ReplayRefusalReason.CANDIDATE_IDENTITY_MISMATCH,
        "result_run_mismatch",
        run=run,
        result=replace(result, geometric_search_run_id="wrong"),
        binding=binding,
    )
    _refused(
        ReplayRefusalReason.CANDIDATE_IDENTITY_MISMATCH,
        "binding_result_mismatch",
        run=run,
        result=replace(result, attempt_id="wrong"),
        binding=binding,
    )
    bad_attempt = replace(result.candidate_attempt, attempt_id="wrong")
    _refused(
        ReplayRefusalReason.CANDIDATE_IDENTITY_MISMATCH,
        "binding_attempt_mismatch",
        run=run,
        result=replace(result, candidate_attempt=bad_attempt),
        binding=binding,
    )
    bad_attempt = replace(result.candidate_attempt, input_digest="wrong")
    _refused(
        ReplayRefusalReason.CANDIDATE_IDENTITY_MISMATCH,
        "attempt_input_digest_mismatch",
        run=run,
        result=replace(result, candidate_attempt=bad_attempt),
        binding=binding,
    )


def test_reconstruction_mismatches_refuse() -> None:
    run, result, binding = _chain()
    bad = replace(result.candidate_reconstruction, candidate_reconstruction_digest="wrong")
    _refused(
        ReplayRefusalReason.CANDIDATE_IDENTITY_MISMATCH,
        "binding_reconstruction_mismatch",
        run=run,
        result=replace(result, candidate_reconstruction=bad),
        binding=binding,
    )
    bad = replace(result.candidate_reconstruction, problem_frame_digest="wrong")
    _refused(
        ReplayRefusalReason.CANDIDATE_IDENTITY_MISMATCH,
        "reconstruction_problem_frame_mismatch",
        run=run,
        result=replace(result, candidate_reconstruction=bad),
        binding=binding,
    )
    bad = replace(result.candidate_reconstruction, original_contract_assessment_id="wrong")
    _refused(
        ReplayRefusalReason.CANDIDATE_IDENTITY_MISMATCH,
        "reconstruction_assessment_mismatch",
        run=run,
        result=replace(result, candidate_reconstruction=bad),
        binding=binding,
    )
    bad = replace(result.candidate_reconstruction, source_residual_id="missing")
    _refused(
        ReplayRefusalReason.CANDIDATE_IDENTITY_MISMATCH,
        "reconstruction_residual_mismatch",
        run=run,
        result=replace(result, candidate_reconstruction=bad),
        binding=binding,
    )


def test_evidence_and_policy_refusals() -> None:
    run, result, binding = _chain()
    other_span = (SourceSpan(text="other", start=20, end=25, sentence_index=0),)
    _refused(
        ReplayRefusalReason.CANDIDATE_IDENTITY_MISMATCH,
        "binding_evidence_mismatch",
        run=run,
        result=result,
        binding=replace(binding, evidence_spans=other_span),
    )
    _refused(
        ReplayRefusalReason.INVALID_REPLAY_INPUT,
        "invalid_proof_obligation_refs",
        run=run,
        result=result,
        binding=binding,
        proof_obligation_refs=(object(),),
    )
    _refused(
        ReplayRefusalReason.UNSUPPORTED_SCHEMA_VERSION,
        "unsupported_schema_version",
        run=run,
        result=result,
        binding=binding,
        schema_versions=(("b", "1"), ("a", "1")),
    )
    _refused(
        ReplayRefusalReason.UNSUPPORTED_REPLAY_POLICY,
        "unsupported_replay_policy_version",
        run=run,
        result=result,
        binding=binding,
        replay_policy_version="contract_proof_replay.future",
    )


def test_unsupported_candidate_organ_refuses() -> None:
    run, result, binding = _chain()
    bad_result = replace(result, candidate_organ="unsupported_candidate_organ")
    _refused(
        ReplayRefusalReason.INVALID_REPLAY_INPUT,
        "unsupported_candidate_organ",
        run=run,
        result=bad_result,
        binding=binding,
    )


def test_contract_policy_constant_is_preserved() -> None:
    assert CONTRACT_PROOF_REPLAY_POLICY_VERSION == "contract_proof_replay.v1"


def _quantity_entity_chain() -> tuple[GeometricSearchRun, object, CandidateAttemptRunBinding]:
    span = SourceSpan(text="5 apples", start=10, end=18, sentence_index=0)
    # residual
    payload = {
        "candidate_organ": QUANTITY_ENTITY_BINDING_CANDIDATE_ORGAN,
        "residual_kind": ResidualKind.MISSING_RELATION.value,
        "residual_code": "local_binding_relation_unbound",
        "evidence_spans": [_span_payload(span)],
    }
    residual_id = _digest(payload)
    residual = ContractResidual(
        residual_id=residual_id,
        candidate_organ=QUANTITY_ENTITY_BINDING_CANDIDATE_ORGAN,
        family_id="state_change.quantity_entity",
        residual_kind=ResidualKind.MISSING_RELATION,
        residual_code="local_binding_relation_unbound",
        source_axis=ResidualSourceAxis.ROLE,
        evidence_spans=(span,),
        explanation="residual prose",
    )

    # gate
    gate_payload = {
        "policy_version": "search_gate.v1",
        "input_digest": "a" * 64,
        "residual_ids": [residual.residual_id],
        "candidate_organ": residual.candidate_organ,
        "status": SearchGateStatus.ELIGIBLE.value,
        "reason_code": "eligible_missing_relation",
        "evidence_spans": [_span_payload(span)],
    }
    gate = SearchGateDecision(
        decision_id=_digest(gate_payload),
        policy_version="search_gate.v1",
        input_digest="a" * 64,
        residual_ids=(residual.residual_id,),
        candidate_organ=residual.candidate_organ,
        status=SearchGateStatus.ELIGIBLE,
        reason_code="eligible_missing_relation",
        evidence_spans=(span,),
        explanation="gate prose",
    )

    # budget
    budget_payload = {
        "policy_version": "compute_budget.v1",
        "gate_decision_id": gate.decision_id,
        "gate_policy_version": gate.policy_version,
        "gate_input_digest": gate.input_digest,
        "status": ComputeBudgetStatus.BUDGET_ALLOWED.value,
        "reason_code": "budget_allowed_missing_relation",
        "max_candidates": 5,
        "max_depth": 2,
        "max_steps": 10,
        "max_parallelism": 1,
        "evidence_spans": [_span_payload(span)],
    }
    budget = ComputeBudgetDecision(
        budget_id=_digest(budget_payload),
        policy_version="compute_budget.v1",
        gate_decision_id=gate.decision_id,
        gate_policy_version=gate.policy_version,
        gate_input_digest=gate.input_digest,
        status=ComputeBudgetStatus.BUDGET_ALLOWED,
        reason_code="budget_allowed_missing_relation",
        max_candidates=5,
        max_depth=2,
        max_steps=10,
        max_wallclock_ms=None,
        max_parallelism=1,
        evidence_spans=(span,),
        explanation="budget prose",
    )

    # run
    run = initialize_geometric_search_run(
        problem_frame_digest="f" * 64,
        contract_assessment_id="assessment-a",
        residual_ids=(residual.residual_id,),
        gate_decision=gate,
        compute_budget=budget,
        operator_set_id=candidate_operator_set_id(),
        operator_set_version="candidate_operators.v2",
    )
    assert isinstance(run, GeometricSearchRun)

    # cue
    cue = GroundedQuantityEntityCue(
        quantity_mention_id="q1",
        entity_mention_id="e1",
        quantity_kind="count",
        evidence_spans=(span,),
        unit_mention_id=None,
    )

    # result
    result = build_quantity_entity_binding_candidate(
        residual=residual,
        search_gate=gate,
        compute_budget=budget,
        run=run,
        problem_frame_digest=run.problem_frame_digest,
        original_contract_assessment_id=run.contract_assessment_id,
        grounded_quantity_entity_cues=(cue,),
    )
    assert hasattr(result, "candidate_attempt")

    # binding
    binding = bind_candidate_attempt_to_run(
        original_run=run,
        candidate_operator_result=result,
    )
    assert isinstance(binding, CandidateAttemptRunBinding)

    return run, result, binding


def test_quantity_entity_binding_path_success() -> None:
    run, result, binding = _quantity_entity_chain()
    replay_input = _bound_input(run, result, binding)

    assert isinstance(replay_input, ReplayAdapterInput)
    assert replay_input.candidate_organ == "quantity_entity_binding"
    assert replay_input.contract_replay_target == "problem_frame_contracts.quantity_entity"
    assert replay_input.operator_set_version == "candidate_operators.v2"
    assert replay_input.run_id == run.run_id
    assert replay_input.attempt_id == binding.candidate_attempt_id
    assert replay_input.candidate_digest == binding.candidate_digest
    assert run.candidate_attempts == ()


def test_quantity_entity_replay_classification_unavailable() -> None:
    run, result, binding = _quantity_entity_chain()
    replay_input = _bound_input(run, result, binding)
    assert isinstance(replay_input, ReplayAdapterInput)

    outcome = classify_replay_result(
        replay_input,
        contract_replay_assessment_id=None,
        contract_closed=None,
    )
    assert isinstance(outcome, ReplayAdapterRefusal)
    assert outcome.replay_disposition is ReplayRefusalReason.CONTRACT_REPLAY_UNAVAILABLE
    assert outcome.reason_codes == ("contract_replay_unavailable",)


def test_quantity_entity_replay_classification_refused() -> None:
    run, result, binding = _quantity_entity_chain()
    replay_input = _bound_input(run, result, binding)
    assert isinstance(replay_input, ReplayAdapterInput)

    outcome = classify_replay_result(
        replay_input,
        contract_replay_assessment_id="contract-replay-quantity-entity-1",
        contract_closed=False,
    )
    assert isinstance(outcome, ReplayAdapterResult)
    assert outcome.replay_disposition is ReplayDisposition.CONTRACT_REFUSED


def test_quantity_entity_replay_classification_closed() -> None:
    run, result, binding = _quantity_entity_chain()
    replay_input = _bound_input(
        run,
        result,
        binding,
        schema_versions=(VACUOUS_PROOF_DECLARATION,),
    )
    assert isinstance(replay_input, ReplayAdapterInput)

    outcome = classify_replay_result(
        replay_input,
        contract_replay_assessment_id="contract-replay-quantity-entity-closed",
        contract_closed=True,
    )
    assert isinstance(outcome, ReplayAdapterResult)
    assert outcome.replay_disposition is ReplayDisposition.CONTRACT_AND_PROOF_CLOSED
    assert outcome.proof_replay_refs == ()


def test_quantity_entity_replay_classification_proof_unavailable() -> None:
    run, result, binding = _quantity_entity_chain()
    # Build without VACUOUS_PROOF_DECLARATION
    replay_input = _bound_input(
        run,
        result,
        binding,
        schema_versions=(("some_other_schema", "v1"),),
    )
    assert isinstance(replay_input, ReplayAdapterInput)

    outcome = classify_replay_result(
        replay_input,
        contract_replay_assessment_id="contract-replay-quantity-entity-1",
        contract_closed=True,
    )
    assert isinstance(outcome, ReplayAdapterRefusal)
    assert outcome.replay_disposition is ReplayRefusalReason.PROOF_REPLAY_UNAVAILABLE
    assert outcome.reason_codes == ("proof_replay_unavailable",)


def test_quantity_entity_unsupported_organ_refuses() -> None:
    run, result, binding = _quantity_entity_chain()
    bad_result = replace(result, candidate_organ="unsupported_quantity_entity_variant")
    _refused(
        ReplayRefusalReason.INVALID_REPLAY_INPUT,
        "unsupported_candidate_organ",
        run=run,
        result=bad_result,
        binding=binding,
    )
