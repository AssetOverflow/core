from __future__ import annotations

import dataclasses
import hashlib
import json
from dataclasses import replace
from types import SimpleNamespace

from generate.candidate_operator import (
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
from generate.run_attempt_binding import (
    CANDIDATE_ATTEMPT_RUN_BINDING_POLICY_VERSION,
    CandidateAttemptRunBinding,
    CandidateAttemptRunBindingInput,
    CandidateAttemptRunBindingOutcome,
    CandidateAttemptRunBindingRefusal,
    RunAttemptBindingRefusalReason,
    bind_candidate_attempt_to_run,
)
from generate.search_gate import SearchGateDecision, SearchGateStatus


def _digest(payload: dict[str, object]) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _span_payload(span: SourceSpan) -> dict[str, object]:
    return {"text": span.text, "start": span.start, "end": span.end, "sentence_index": span.sentence_index}


def _span(text: str = "gained", start: int = 10, end: int = 15) -> SourceSpan:
    return SourceSpan(text=text, start=start, end=end, sentence_index=0)


def _residual(evidence_spans: tuple[SourceSpan, ...] | None = None) -> ContractResidual:
    spans = evidence_spans if evidence_spans is not None else (_span(),)
    residual_id = _digest({
        "candidate_organ": "unary_delta_transition",
        "residual_kind": ResidualKind.MISSING_ROLE.value,
        "residual_code": "direction_unbound",
        "evidence_spans": [_span_payload(span) for span in spans],
    })
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


def _budget(gate: SearchGateDecision, *, max_candidates: int = 5, max_depth: int = 2, max_steps: int = 10) -> ComputeBudgetDecision:
    payload = {
        "policy_version": "compute_budget.v1",
        "gate_decision_id": gate.decision_id,
        "gate_policy_version": gate.policy_version,
        "gate_input_digest": gate.input_digest,
        "status": ComputeBudgetStatus.BUDGET_ALLOWED.value,
        "reason_code": "budget_allowed_missing_role",
        "max_candidates": max_candidates,
        "max_depth": max_depth,
        "max_steps": max_steps,
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
        max_candidates=max_candidates,
        max_depth=max_depth,
        max_steps=max_steps,
        max_wallclock_ms=None,
        max_parallelism=1,
        evidence_spans=gate.evidence_spans,
        explanation="budget prose",
    )


def _chain() -> tuple[ContractResidual, GeometricSearchRun, object]:
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
        operator_set_version="candidate_operators.v1",
    )
    assert isinstance(run, GeometricSearchRun)
    result = build_missing_role_candidate(
        residual=residual,
        search_gate=gate,
        compute_budget=budget,
        run=run,
        problem_frame_digest=run.problem_frame_digest,
        original_contract_assessment_id=run.contract_assessment_id,
        grounded_unary_delta_cues=(GroundedUnaryDeltaCue(direction="increase", evidence_spans=residual.evidence_spans),),
    )
    assert hasattr(result, "candidate_attempt")
    return residual, run, result


def _refused(reason: RunAttemptBindingRefusalReason, *, run: GeometricSearchRun, result: object) -> None:
    outcome = bind_candidate_attempt_to_run(original_run=run, candidate_operator_result=result)  # type: ignore[arg-type]
    assert isinstance(outcome, CandidateAttemptRunBindingRefusal)
    assert outcome.reason_codes == (reason.value,)


def test_public_api_exports_are_exact() -> None:
    import generate.run_attempt_binding as module
    assert tuple(module.__all__) == (
        "CANDIDATE_ATTEMPT_RUN_BINDING_POLICY_VERSION",
        "RunAttemptBindingRefusalReason",
        "CandidateAttemptRunBindingInput",
        "CandidateAttemptRunBinding",
        "CandidateAttemptRunBindingRefusal",
        "CandidateAttemptRunBindingOutcome",
        "bind_candidate_attempt_to_run",
    )
    assert CANDIDATE_ATTEMPT_RUN_BINDING_POLICY_VERSION == "candidate_attempt_run_binding.v1"
    assert CandidateAttemptRunBindingOutcome is not None


def test_valid_result_binds_without_mutating_run() -> None:
    _, run, result = _chain()
    before = run.candidate_attempts
    outcome = bind_candidate_attempt_to_run(original_run=run, candidate_operator_result=result)
    assert isinstance(outcome, CandidateAttemptRunBinding)
    assert outcome.run_attempt_membership == "structurally_bound"
    assert outcome.reason_codes == ()
    assert run.candidate_attempts == before == ()


def test_explanation_does_not_affect_ids() -> None:
    _, run, result = _chain()
    first = bind_candidate_attempt_to_run(original_run=run, candidate_operator_result=result, explanation="first")
    second = bind_candidate_attempt_to_run(original_run=run, candidate_operator_result=result, explanation="second")
    assert isinstance(first, CandidateAttemptRunBinding)
    assert isinstance(second, CandidateAttemptRunBinding)
    assert first.input_digest == second.input_digest
    assert first.candidate_attempt_ref == second.candidate_attempt_ref
    assert first.binding_id == second.binding_id


def test_invalid_inputs_refuse() -> None:
    _, run, result = _chain()
    outcome = bind_candidate_attempt_to_run(original_run=SimpleNamespace(), candidate_operator_result=result)  # type: ignore[arg-type]
    assert isinstance(outcome, CandidateAttemptRunBindingRefusal)
    assert outcome.reason_codes == (RunAttemptBindingRefusalReason.INVALID_BINDING_INPUT.value,)
    outcome = bind_candidate_attempt_to_run(original_run=run, candidate_operator_result=SimpleNamespace())  # type: ignore[arg-type]
    assert isinstance(outcome, CandidateAttemptRunBindingRefusal)
    assert outcome.reason_codes == (RunAttemptBindingRefusalReason.INVALID_BINDING_INPUT.value,)


def test_run_and_attempt_identity_refusals() -> None:
    _, run, result = _chain()
    _refused(RunAttemptBindingRefusalReason.RUN_RESULT_MISMATCH, run=run, result=replace(result, geometric_search_run_id="wrong"))
    _refused(RunAttemptBindingRefusalReason.ATTEMPT_RESULT_MISMATCH, run=run, result=replace(result, attempt_id="wrong"))
    bad_attempt = replace(result.candidate_attempt, candidate_digest="bad")
    _refused(RunAttemptBindingRefusalReason.ATTEMPT_RESULT_MISMATCH, run=run, result=replace(result, candidate_attempt=bad_attempt))
    bad_attempt = replace(result.candidate_attempt, input_digest="bad")
    _refused(RunAttemptBindingRefusalReason.ATTEMPT_RESULT_MISMATCH, run=run, result=replace(result, candidate_attempt=bad_attempt))


def test_reconstruction_identity_refusals() -> None:
    _, run, result = _chain()
    bad = replace(result.candidate_reconstruction, candidate_digest="bad")
    _refused(RunAttemptBindingRefusalReason.RECONSTRUCTION_RESULT_MISMATCH, run=run, result=replace(result, candidate_reconstruction=bad))
    bad = replace(result.candidate_reconstruction, candidate_reconstruction_digest="bad")
    _refused(RunAttemptBindingRefusalReason.RECONSTRUCTION_RESULT_MISMATCH, run=run, result=replace(result, candidate_reconstruction=bad))


def test_replay_state_refusals() -> None:
    _, run, result = _chain()
    bad_attempt = replace(result.candidate_attempt, replay_status=CandidateReplayStatus.REPLAY_CLOSED)
    _refused(RunAttemptBindingRefusalReason.REPLAY_STATUS_NOT_PENDING, run=run, result=replace(result, candidate_attempt=bad_attempt))
    bad_attempt = replace(result.candidate_attempt, replay_blockers=("blocked",))
    _refused(RunAttemptBindingRefusalReason.REPLAY_BLOCKERS_PRESENT, run=run, result=replace(result, candidate_attempt=bad_attempt))


def test_run_identity_and_operator_set_refusals() -> None:
    _, run, result = _chain()
    bad = replace(result.candidate_reconstruction, source_residual_id="missing")
    _refused(RunAttemptBindingRefusalReason.RUN_IDENTITY_MISMATCH, run=run, result=replace(result, candidate_reconstruction=bad))
    bad = replace(result.candidate_reconstruction, problem_frame_digest="bad")
    _refused(RunAttemptBindingRefusalReason.RUN_IDENTITY_MISMATCH, run=run, result=replace(result, candidate_reconstruction=bad))
    bad = replace(result.candidate_reconstruction, original_contract_assessment_id="bad")
    _refused(RunAttemptBindingRefusalReason.RUN_IDENTITY_MISMATCH, run=run, result=replace(result, candidate_reconstruction=bad))
    bad = replace(result.candidate_reconstruction, operator_provenance=(("operator_set_id", "wrong"), ("operator_set_version", run.operator_set_version)))
    _refused(RunAttemptBindingRefusalReason.OPERATOR_SET_MISMATCH, run=run, result=replace(result, candidate_reconstruction=bad))


def test_evidence_span_refusals() -> None:
    _, run, result = _chain()
    span = SourceSpan(text="other", start=20, end=25, sentence_index=0)
    _refused(RunAttemptBindingRefusalReason.MALFORMED_EVIDENCE_SPAN, run=run, result=replace(result, evidence_spans=(span,)))
    bad_attempt = replace(result.candidate_attempt, evidence_spans=(object(),))
    _refused(RunAttemptBindingRefusalReason.MALFORMED_EVIDENCE_SPAN, run=run, result=replace(result, candidate_attempt=bad_attempt))


def test_duplicate_membership_refusals() -> None:
    _, run, result = _chain()
    existing = replace(result.candidate_attempt, attempt_id="other", candidate_digest="other")
    _refused(RunAttemptBindingRefusalReason.DUPLICATE_ATTEMPT_INDEX, run=replace(run, candidate_attempts=(existing,)), result=result)
    existing = replace(result.candidate_attempt, attempt_index=99, candidate_digest="other")
    _refused(RunAttemptBindingRefusalReason.DUPLICATE_ATTEMPT_ID, run=replace(run, candidate_attempts=(existing,)), result=result)
    existing = replace(result.candidate_attempt, attempt_index=99, attempt_id="other")
    _refused(RunAttemptBindingRefusalReason.DUPLICATE_CANDIDATE_DIGEST, run=replace(run, candidate_attempts=(existing,)), result=result)


def test_budget_refusals() -> None:
    _, run, result = _chain()
    bad_attempt = replace(result.candidate_attempt, budget_charge=BudgetCharge(candidates=999, steps=1))
    _refused(RunAttemptBindingRefusalReason.BUDGET_CHARGE_EXCEEDS_REMAINING, run=run, result=replace(result, candidate_attempt=bad_attempt))
    bad_attempt = replace(result.candidate_attempt, budget_charge=BudgetCharge(candidates=1, steps=999))
    _refused(RunAttemptBindingRefusalReason.BUDGET_CHARGE_EXCEEDS_REMAINING, run=run, result=replace(result, candidate_attempt=bad_attempt))
    bad_attempt = replace(result.candidate_attempt, depth=999)
    _refused(RunAttemptBindingRefusalReason.BUDGET_CHARGE_EXCEEDS_REMAINING, run=run, result=replace(result, candidate_attempt=bad_attempt))


def test_schema_policy_version_pairs_validate() -> None:
    _, run, result = _chain()
    outcome = bind_candidate_attempt_to_run(original_run=run, candidate_operator_result=result, schema_versions=(("b", "1"), ("a", "1")))
    assert isinstance(outcome, CandidateAttemptRunBindingRefusal)
    assert outcome.reason_codes == (RunAttemptBindingRefusalReason.UNSUPPORTED_SCHEMA_VERSION.value,)
    outcome = bind_candidate_attempt_to_run(original_run=run, candidate_operator_result=result, policy_versions=(("a", "1"), ("a", "2")))
    assert isinstance(outcome, CandidateAttemptRunBindingRefusal)
    assert outcome.reason_codes == (RunAttemptBindingRefusalReason.UNSUPPORTED_SCHEMA_VERSION.value,)


def test_evidence_order_and_duplicates_are_preserved() -> None:
    _, run, result = _chain()
    first = SourceSpan(text="one", start=0, end=3, sentence_index=0)
    second = SourceSpan(text="two", start=4, end=7, sentence_index=0)
    spans = (first, first, second)
    attempt = replace(result.candidate_attempt, evidence_spans=spans)
    reconstruction = replace(result.candidate_reconstruction, evidence_spans=spans)
    updated = replace(result, candidate_attempt=attempt, candidate_reconstruction=reconstruction, evidence_spans=spans)
    outcome = bind_candidate_attempt_to_run(original_run=run, candidate_operator_result=updated)
    assert isinstance(outcome, CandidateAttemptRunBinding)
    assert outcome.evidence_spans == spans
    reordered = (second, first, first)
    attempt = replace(result.candidate_attempt, evidence_spans=reordered)
    reconstruction = replace(result.candidate_reconstruction, evidence_spans=reordered)
    updated_reordered = replace(result, candidate_attempt=attempt, candidate_reconstruction=reconstruction, evidence_spans=reordered)
    other = bind_candidate_attempt_to_run(original_run=run, candidate_operator_result=updated_reordered)
    assert isinstance(other, CandidateAttemptRunBinding)
    assert outcome.binding_id != other.binding_id


def test_binding_dataclasses_have_no_forbidden_authority_fields() -> None:
    forbidden = {
        "answer", "final_answer", "served_output", "proof", "verdict", "promotion",
        "mutation", "teaching_update", "pack_update", "policy_update", "identity_update",
        "workbench_state", "runtime_effect", "confidence", "score", "rank", "priority",
        "selected", "selected_candidate", "best", "best_candidate", "serving_allowed", "runnable",
    }
    for record_type in (CandidateAttemptRunBindingInput, CandidateAttemptRunBinding, CandidateAttemptRunBindingRefusal):
        assert forbidden.isdisjoint({field.name for field in dataclasses.fields(record_type)})


def test_refusal_is_not_partial_binding() -> None:
    _, run, result = _chain()
    outcome = bind_candidate_attempt_to_run(original_run=run, candidate_operator_result=replace(result, geometric_search_run_id="wrong"))
    assert isinstance(outcome, CandidateAttemptRunBindingRefusal)
    assert not hasattr(outcome, "binding_id")
    assert not hasattr(outcome, "candidate_attempt_ref")
