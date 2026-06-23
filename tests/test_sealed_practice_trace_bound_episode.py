from __future__ import annotations

import ast
import dataclasses
import hashlib
import json
from dataclasses import replace
from pathlib import Path
from generate.candidate_operator import (
    CandidateOperatorResult,
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
    VACUOUS_PROOF_DECLARATION,
    ReplayAdapterInput,
    ReplayAdapterRefusal,
    ReplayAdapterResult,
    ReplayDisposition,
    build_replay_adapter_input_from_binding,
    classify_replay_result,
)
from generate.run_attempt_binding import (
    CandidateAttemptRunBinding,
    bind_candidate_attempt_to_run,
)
from generate.search_gate import SearchGateDecision, SearchGateStatus
from generate.sealed_practice_trace import (
    PracticeDisposition,
    PracticeTraceInput,
    PracticeTraceRefusal,
    SealedPracticeTrace,
    build_bound_practice_trace_input,
    seal_bound_practice_trace,
)


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


def _chain() -> tuple[
    GeometricSearchRun,
    CandidateOperatorResult,
    CandidateAttemptRunBinding,
]:
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
    assert isinstance(result, CandidateOperatorResult)
    binding = bind_candidate_attempt_to_run(
        original_run=run,
        candidate_operator_result=result,
    )
    assert isinstance(binding, CandidateAttemptRunBinding)
    return run, result, binding


def _bound_replay_input(
    run: GeometricSearchRun,
    result: CandidateOperatorResult,
    binding: CandidateAttemptRunBinding,
    **kwargs: object,
) -> ReplayAdapterInput | ReplayAdapterRefusal:
    outcome = build_replay_adapter_input_from_binding(
        run=run,
        binding=binding,
        candidate_operator_result=result,
        **kwargs,  # type: ignore[arg-type]
    )
    assert isinstance(outcome, ReplayAdapterInput)
    return outcome


def _bound_replay_result(
    run: GeometricSearchRun,
    result: CandidateOperatorResult,
    binding: CandidateAttemptRunBinding,
    *,
    disposition: ReplayDisposition = ReplayDisposition.CONTRACT_REFUSED,
    schema_versions: tuple[tuple[str, str], ...] = (),
    proof_obligation_refs: tuple[str, ...] = (),
) -> ReplayAdapterResult:
    if disposition is ReplayDisposition.CONTRACT_AND_PROOF_CLOSED:
        schema_versions = schema_versions or (VACUOUS_PROOF_DECLARATION,)
    if disposition is ReplayDisposition.CONTRACT_CLOSED_BUT_PROOF_REFUSED:
        proof_obligation_refs = proof_obligation_refs or ("obligation-a",)
    replay_input = _bound_replay_input(
        run,
        result,
        binding,
        schema_versions=schema_versions,
        proof_obligation_refs=proof_obligation_refs,
    )
    if disposition is ReplayDisposition.CONTRACT_REFUSED:
        outcome = classify_replay_result(
            replay_input,
            contract_replay_assessment_id="e" * 64,
            contract_closed=False,
        )
    else:
        outcome = classify_replay_result(
            replay_input,
            contract_replay_assessment_id="e" * 64,
            contract_closed=True,
        )
    assert isinstance(outcome, ReplayAdapterResult)
    assert outcome.replay_disposition is disposition
    return outcome


def _bound_replay_refusal(
    run: GeometricSearchRun,
    result: CandidateOperatorResult,
    binding: CandidateAttemptRunBinding,
) -> ReplayAdapterRefusal:
    replay_input = _bound_replay_input(run, result, binding)
    outcome = classify_replay_result(
        replay_input,
        contract_replay_assessment_id=None,
        contract_closed=True,
    )
    assert isinstance(outcome, ReplayAdapterRefusal)
    return outcome


def _build_bound_trace_input(
    run: GeometricSearchRun,
    result: CandidateOperatorResult,
    binding: CandidateAttemptRunBinding,
    *,
    replay_results: tuple[ReplayAdapterResult, ...] = (),
    replay_refusals: tuple[ReplayAdapterRefusal, ...] = (),
    **changes: object,
) -> PracticeTraceInput | PracticeTraceRefusal:
    values: dict[str, object] = {
        "problem_frame_digest": run.problem_frame_digest,
        "original_contract_assessment_id": run.contract_assessment_id,
        "residual_ids": run.residual_ids,
        "search_gate_decision_id": run.gate_decision_id,
        "compute_budget_id": run.budget_id,
        "run": run,
        "bindings": (binding,),
        "candidate_operator_results": (result,),
        "replay_results": replay_results,
        "replay_refusals": replay_refusals,
    }
    values.update(changes)
    return build_bound_practice_trace_input(**values)  # type: ignore[arg-type]


def _seal_bound(
    trace_input: PracticeTraceInput,
    run: GeometricSearchRun,
    result: CandidateOperatorResult,
    binding: CandidateAttemptRunBinding,
    *,
    replay_results: tuple[ReplayAdapterResult, ...] = (),
    replay_refusals: tuple[ReplayAdapterRefusal, ...] = (),
    evidence_spans: tuple[SourceSpan, ...] = (),
    explanation: str = "",
) -> SealedPracticeTrace | PracticeTraceRefusal:
    return seal_bound_practice_trace(
        trace_input,
        run=run,
        bindings=(binding,),
        candidate_operator_results=(result,),
        replay_results=replay_results,
        replay_refusals=replay_refusals,
        evidence_spans=evidence_spans,
        explanation=explanation,
    )


def test_bound_contract_refused_seals_all_candidates_refused() -> None:
    run, result, binding = _chain()
    replay = _bound_replay_result(run, result, binding)
    trace_input = _build_bound_trace_input(run, result, binding, replay_results=(replay,))
    assert isinstance(trace_input, PracticeTraceInput)
    sealed = _seal_bound(trace_input, run, result, binding, replay_results=(replay,))
    assert isinstance(sealed, SealedPracticeTrace)
    assert sealed.practice_disposition is PracticeDisposition.SEALED_ALL_CANDIDATES_REFUSED


def test_bound_vacuous_proof_closed_seals_candidate_replay_closed() -> None:
    run, result, binding = _chain()
    replay = _bound_replay_result(
        run,
        result,
        binding,
        disposition=ReplayDisposition.CONTRACT_AND_PROOF_CLOSED,
    )
    trace_input = _build_bound_trace_input(run, result, binding, replay_results=(replay,))
    assert isinstance(trace_input, PracticeTraceInput)
    sealed = _seal_bound(trace_input, run, result, binding, replay_results=(replay,))
    assert isinstance(sealed, SealedPracticeTrace)
    assert sealed.practice_disposition is PracticeDisposition.SEALED_CANDIDATE_REPLAY_CLOSED


def test_bound_contract_closed_proof_refused_seals_disposition() -> None:
    run, result, binding = _chain()
    replay = _bound_replay_result(
        run,
        result,
        binding,
        disposition=ReplayDisposition.CONTRACT_CLOSED_BUT_PROOF_REFUSED,
    )
    trace_input = _build_bound_trace_input(run, result, binding, replay_results=(replay,))
    assert isinstance(trace_input, PracticeTraceInput)
    sealed = _seal_bound(trace_input, run, result, binding, replay_results=(replay,))
    assert isinstance(sealed, SealedPracticeTrace)
    assert (
        sealed.practice_disposition
        is PracticeDisposition.SEALED_CONTRACT_CLOSED_PROOF_REFUSED
    )


def test_bound_replay_refusal_only_seals_replay_unavailable() -> None:
    run, result, binding = _chain()
    refusal = _bound_replay_refusal(run, result, binding)
    trace_input = _build_bound_trace_input(run, result, binding, replay_refusals=(refusal,))
    assert isinstance(trace_input, PracticeTraceInput)
    sealed = _seal_bound(trace_input, run, result, binding, replay_refusals=(refusal,))
    assert isinstance(sealed, SealedPracticeTrace)
    assert sealed.practice_disposition is PracticeDisposition.SEALED_REPLAY_UNAVAILABLE


def test_run_remains_unmutated_after_bound_sealing() -> None:
    run, result, binding = _chain()
    before = run.candidate_attempts
    replay = _bound_replay_result(run, result, binding)
    trace_input = _build_bound_trace_input(run, result, binding, replay_results=(replay,))
    assert isinstance(trace_input, PracticeTraceInput)
    sealed = _seal_bound(trace_input, run, result, binding, replay_results=(replay,))
    assert isinstance(sealed, SealedPracticeTrace)
    assert run.candidate_attempts == before == ()


def test_trace_includes_bound_identity_fields() -> None:
    run, result, binding = _chain()
    replay = _bound_replay_result(run, result, binding)
    trace_input = _build_bound_trace_input(run, result, binding, replay_results=(replay,))
    assert isinstance(trace_input, PracticeTraceInput)
    sealed = _seal_bound(trace_input, run, result, binding, replay_results=(replay,))
    assert isinstance(sealed, SealedPracticeTrace)
    assert sealed.candidate_attempt_ids == (binding.candidate_attempt_id,)
    assert sealed.candidate_attempt_binding_ids == (binding.binding_id,)
    assert sealed.replay_result_ids == (replay.replay_result_id,)
    assert sealed.replay_refusal_ids == ()


def test_bound_trace_id_is_deterministic() -> None:
    run, result, binding = _chain()
    replay = _bound_replay_result(run, result, binding)
    trace_input = _build_bound_trace_input(run, result, binding, replay_results=(replay,))
    assert isinstance(trace_input, PracticeTraceInput)
    first = _seal_bound(trace_input, run, result, binding, replay_results=(replay,))
    second = _seal_bound(trace_input, run, result, binding, replay_results=(replay,))
    assert isinstance(first, SealedPracticeTrace)
    assert isinstance(second, SealedPracticeTrace)
    assert first.trace_id == second.trace_id


def test_bound_explanation_changes_do_not_affect_trace_id() -> None:
    run, result, binding = _chain()
    replay = _bound_replay_result(run, result, binding)
    trace_input = _build_bound_trace_input(run, result, binding, replay_results=(replay,))
    assert isinstance(trace_input, PracticeTraceInput)
    first = _seal_bound(
        trace_input,
        run,
        result,
        binding,
        replay_results=(replay,),
        explanation="first prose",
    )
    second = _seal_bound(
        trace_input,
        run,
        result,
        binding,
        replay_results=(replay,),
        explanation="second prose",
    )
    assert isinstance(first, SealedPracticeTrace)
    assert isinstance(second, SealedPracticeTrace)
    assert first.trace_id == second.trace_id


def test_bound_duplicate_evidence_spans_are_preserved() -> None:
    run, result, binding = _chain()
    replay = _bound_replay_result(run, result, binding)
    trace_input = _build_bound_trace_input(run, result, binding, replay_results=(replay,))
    assert isinstance(trace_input, PracticeTraceInput)
    span = SourceSpan("dup", 1, 4, 0)
    sealed = _seal_bound(
        trace_input,
        run,
        result,
        binding,
        replay_results=(replay,),
        evidence_spans=(span, span),
    )
    assert isinstance(sealed, SealedPracticeTrace)
    assert sealed.evidence_spans == (span, span)


def test_binding_run_mismatch_refuses() -> None:
    run, result, binding = _chain()
    replay = _bound_replay_result(run, result, binding)
    bad_binding = replace(binding, original_run_id="wrong" * 8)
    outcome = _build_bound_trace_input(
        run,
        result,
        bad_binding,
        replay_results=(replay,),
    )
    assert isinstance(outcome, PracticeTraceRefusal)
    assert "binding_run_mismatch" in outcome.reason_codes


def test_binding_result_mismatch_refuses() -> None:
    run, result, binding = _chain()
    replay = _bound_replay_result(run, result, binding)
    bad_binding = replace(binding, operator_result_id="wrong" * 8)
    outcome = _build_bound_trace_input(
        run,
        result,
        bad_binding,
        replay_results=(replay,),
    )
    assert isinstance(outcome, PracticeTraceRefusal)
    assert "binding_result_mismatch" in outcome.reason_codes


def test_binding_attempt_mismatch_refuses() -> None:
    run, result, binding = _chain()
    replay = _bound_replay_result(run, result, binding)
    bad_binding = replace(binding, candidate_attempt_id="wrong" * 8)
    outcome = _build_bound_trace_input(
        run,
        result,
        bad_binding,
        replay_results=(replay,),
    )
    assert isinstance(outcome, PracticeTraceRefusal)
    assert "binding_attempt_mismatch" in outcome.reason_codes


def test_binding_reconstruction_mismatch_refuses() -> None:
    run, result, binding = _chain()
    replay = _bound_replay_result(run, result, binding)
    bad_binding = replace(binding, candidate_reconstruction_digest="wrong" * 8)
    outcome = _build_bound_trace_input(
        run,
        result,
        bad_binding,
        replay_results=(replay,),
    )
    assert isinstance(outcome, PracticeTraceRefusal)
    assert "binding_reconstruction_mismatch" in outcome.reason_codes


def test_binding_not_structurally_bound_refuses() -> None:
    run, result, binding = _chain()
    replay = _bound_replay_result(run, result, binding)
    bad_binding = replace(binding, run_attempt_membership="pending")
    outcome = _build_bound_trace_input(
        run,
        result,
        bad_binding,
        replay_results=(replay,),
    )
    assert isinstance(outcome, PracticeTraceRefusal)
    assert "binding_not_structurally_bound" in outcome.reason_codes


def test_binding_with_reason_codes_refuses() -> None:
    run, result, binding = _chain()
    replay = _bound_replay_result(run, result, binding)
    bad_binding = replace(binding, reason_codes=("leftover",))
    outcome = _build_bound_trace_input(
        run,
        result,
        bad_binding,
        replay_results=(replay,),
    )
    assert isinstance(outcome, PracticeTraceRefusal)
    assert "binding_not_successful" in outcome.reason_codes


def test_duplicate_binding_ids_refuse() -> None:
    run, result, binding = _chain()
    replay = _bound_replay_result(run, result, binding)
    outcome = build_bound_practice_trace_input(
        problem_frame_digest=run.problem_frame_digest,
        original_contract_assessment_id=run.contract_assessment_id,
        residual_ids=run.residual_ids,
        search_gate_decision_id=run.gate_decision_id,
        compute_budget_id=run.budget_id,
        run=run,
        bindings=(binding, binding),
        candidate_operator_results=(result, result),
        replay_results=(replay, replay),
    )
    assert isinstance(outcome, PracticeTraceRefusal)
    assert "duplicate_candidate_attempt_binding_id" in outcome.reason_codes


def test_duplicate_attempt_ids_refuse() -> None:
    run, result, binding = _chain()
    replay = _bound_replay_result(run, result, binding)
    second_binding = replace(binding, binding_id="b" * 64)
    outcome = build_bound_practice_trace_input(
        problem_frame_digest=run.problem_frame_digest,
        original_contract_assessment_id=run.contract_assessment_id,
        residual_ids=run.residual_ids,
        search_gate_decision_id=run.gate_decision_id,
        compute_budget_id=run.budget_id,
        run=run,
        bindings=(binding, second_binding),
        candidate_operator_results=(result, result),
        replay_results=(replay,),
    )
    assert isinstance(outcome, PracticeTraceRefusal)
    assert "duplicate_candidate_attempt_id" in outcome.reason_codes


def test_duplicate_candidate_digests_refuse() -> None:
    run, result, binding = _chain()
    replay = _bound_replay_result(run, result, binding)
    second_binding = replace(
        binding,
        binding_id="b" * 64,
        candidate_attempt_id="c" * 64,
    )
    outcome = build_bound_practice_trace_input(
        problem_frame_digest=run.problem_frame_digest,
        original_contract_assessment_id=run.contract_assessment_id,
        residual_ids=run.residual_ids,
        search_gate_decision_id=run.gate_decision_id,
        compute_budget_id=run.budget_id,
        run=run,
        bindings=(binding, second_binding),
        candidate_operator_results=(result, result),
        replay_results=(replay,),
    )
    assert isinstance(outcome, PracticeTraceRefusal)
    assert "duplicate_candidate_digest" in outcome.reason_codes


def test_replay_result_wrong_run_id_refuses() -> None:
    run, result, binding = _chain()
    replay = _bound_replay_result(run, result, binding)
    bad_replay = replace(replay, run_id="wrong" * 8)
    outcome = _build_bound_trace_input(run, result, binding, replay_results=(bad_replay,))
    assert isinstance(outcome, PracticeTraceRefusal)
    assert "replay_run_id_mismatch" in outcome.reason_codes


def test_replay_result_orphan_attempt_id_refuses() -> None:
    run, result, binding = _chain()
    replay = _bound_replay_result(run, result, binding)
    bad_replay = replace(replay, attempt_id="orphan" * 8)
    outcome = _build_bound_trace_input(run, result, binding, replay_results=(bad_replay,))
    assert isinstance(outcome, PracticeTraceRefusal)
    assert "replay_orphan_attempt_id" in outcome.reason_codes


def test_replay_result_wrong_candidate_digest_refuses() -> None:
    run, result, binding = _chain()
    replay = _bound_replay_result(run, result, binding)
    bad_replay = replace(replay, candidate_digest="wrong" * 8)
    outcome = _build_bound_trace_input(run, result, binding, replay_results=(bad_replay,))
    assert isinstance(outcome, PracticeTraceRefusal)
    assert "replay_candidate_digest_mismatch" in outcome.reason_codes


def test_replay_refusal_wrong_run_id_refuses() -> None:
    run, result, binding = _chain()
    refusal = _bound_replay_refusal(run, result, binding)
    bad_refusal = replace(refusal, run_id="wrong" * 8)
    outcome = _build_bound_trace_input(run, result, binding, replay_refusals=(bad_refusal,))
    assert isinstance(outcome, PracticeTraceRefusal)
    assert "replay_run_id_mismatch" in outcome.reason_codes


def test_replay_refusal_orphan_attempt_id_refuses() -> None:
    run, result, binding = _chain()
    refusal = _bound_replay_refusal(run, result, binding)
    bad_refusal = replace(refusal, attempt_id="orphan" * 8)
    outcome = _build_bound_trace_input(run, result, binding, replay_refusals=(bad_refusal,))
    assert isinstance(outcome, PracticeTraceRefusal)
    assert "replay_orphan_attempt_id" in outcome.reason_codes


def test_unsupported_trace_policy_refuses() -> None:
    run, result, binding = _chain()
    replay = _bound_replay_result(run, result, binding)
    outcome = _build_bound_trace_input(
        run,
        result,
        binding,
        replay_results=(replay,),
        trace_policy_version="unsupported.v9",
    )
    assert isinstance(outcome, PracticeTraceRefusal)
    assert outcome.practice_disposition is PracticeDisposition.TRACE_POLICY_UNSUPPORTED


def test_invalid_schema_versions_refuse() -> None:
    run, result, binding = _chain()
    replay = _bound_replay_result(run, result, binding)
    outcome = _build_bound_trace_input(
        run,
        result,
        binding,
        replay_results=(replay,),
        schema_versions=(("b", "1"), ("a", "1")),
    )
    assert isinstance(outcome, PracticeTraceRefusal)
    assert "invalid_schema_versions" in outcome.reason_codes


def test_build_bound_refuses_invalid_binding_type_without_exception() -> None:
    run, result, _binding = _chain()
    outcome = build_bound_practice_trace_input(
        problem_frame_digest=run.problem_frame_digest,
        original_contract_assessment_id=run.contract_assessment_id,
        residual_ids=run.residual_ids,
        search_gate_decision_id=run.gate_decision_id,
        compute_budget_id=run.budget_id,
        run=run,
        bindings=(object(),),
        candidate_operator_results=(result,),
    )
    assert isinstance(outcome, PracticeTraceRefusal)
    assert "invalid_binding_type" in outcome.reason_codes


def test_build_bound_refuses_invalid_operator_result_type_without_exception() -> None:
    run, _result, binding = _chain()
    outcome = build_bound_practice_trace_input(
        problem_frame_digest=run.problem_frame_digest,
        original_contract_assessment_id=run.contract_assessment_id,
        residual_ids=run.residual_ids,
        search_gate_decision_id=run.gate_decision_id,
        compute_budget_id=run.budget_id,
        run=run,
        bindings=(binding,),
        candidate_operator_results=(object(),),
    )
    assert isinstance(outcome, PracticeTraceRefusal)
    assert "invalid_candidate_operator_result_type" in outcome.reason_codes


def test_build_bound_refuses_non_tuple_bindings_without_exception() -> None:
    run, result, _binding = _chain()
    outcome = build_bound_practice_trace_input(
        problem_frame_digest=run.problem_frame_digest,
        original_contract_assessment_id=run.contract_assessment_id,
        residual_ids=run.residual_ids,
        search_gate_decision_id=run.gate_decision_id,
        compute_budget_id=run.budget_id,
        run=run,
        bindings=object(),  # type: ignore[arg-type]
        candidate_operator_results=(result,),
    )
    assert isinstance(outcome, PracticeTraceRefusal)
    assert "invalid_binding_type" in outcome.reason_codes


def test_seal_bound_refuses_binding_result_count_mismatch_without_exception() -> None:
    run, result, binding = _chain()
    replay = _bound_replay_result(run, result, binding)
    trace_input = _build_bound_trace_input(run, result, binding, replay_results=(replay,))
    assert isinstance(trace_input, PracticeTraceInput)
    outcome = seal_bound_practice_trace(
        trace_input,
        run=run,
        bindings=(binding,),
        candidate_operator_results=(),
        replay_results=(replay,),
    )
    assert isinstance(outcome, PracticeTraceRefusal)
    assert "binding_result_count_mismatch" in outcome.reason_codes


def test_seal_bound_refuses_invalid_binding_type_without_exception() -> None:
    run, result, binding = _chain()
    replay = _bound_replay_result(run, result, binding)
    trace_input = _build_bound_trace_input(run, result, binding, replay_results=(replay,))
    assert isinstance(trace_input, PracticeTraceInput)
    outcome = seal_bound_practice_trace(
        trace_input,
        run=run,
        bindings=(object(),),
        candidate_operator_results=(result,),
        replay_results=(replay,),
    )
    assert isinstance(outcome, PracticeTraceRefusal)
    assert "invalid_binding_type" in outcome.reason_codes


def test_bound_module_does_not_call_upstream_producers() -> None:
    # sealed_practice_trace consumes already-produced evidence.
    # It does not produce candidates, bind attempts, build replay input, classify replay,
    # or execute sealing side effects beyond constructing immutable records.
    path = Path("generate/sealed_practice_trace.py")
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

    # Allowed record imports and standard library / upstream modules
    assert imports <= {
        "__future__",
        "dataclasses",
        "enum",
        "hashlib",
        "json",
        "generate.geometric_search_run",
        "generate.kernel_facts",
        "generate.replay_adapter",
        "generate.candidate_operator",
        "generate.run_attempt_binding",
    }

    # Forbidden authority modules
    forbidden_module_families = (
        "runtime", "serving", "workbench", "teaching", "proposal", "pack", "policy", "identity"
    )
    for imp in imports:
        assert not any(imp.startswith(family) for family in forbidden_module_families), f"Imported forbidden module family: {imp}"

    # Forbidden imports/calls
    forbidden_imports = {
        "build_missing_role_candidate",
        "candidate_operator_set_id",
        "GroundedUnaryDeltaCue",
        "bind_candidate_attempt_to_run",
        "build_replay_adapter_input",
        "build_replay_adapter_input_from_binding",
        "classify_replay_result",
        "initialize_geometric_search_run",
    }
    assert forbidden_imports.isdisjoint(imported_names)
    assert forbidden_imports.isdisjoint(calls)

    # Allowed imported names from generate module family must be record types/enums only
    allowed_imported_names = {
        "CandidateOperatorResult",
        "CandidateAttemptRunBinding",
        "ReplayAdapterResult",
        "ReplayAdapterRefusal",
        "ReplayDisposition",
        "GeometricSearchRun",
        "SearchRunRefusal",
        "SearchRunDisposition",
        "SourceSpan",
        # standard library imports and dataclass/enum decorators/helpers
        "annotations",
        "hashlib",
        "json",
        "dataclass",
        "Enum",
        "unique",
    }
    # Check that any imported name starting with generate or from a generate module is allowed
    generate_imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("generate"):
            generate_imports.update(alias.name for alias in node.names)
    assert generate_imports <= allowed_imported_names, f"Imported names that are not allowed records: {generate_imports - allowed_imported_names}"


def test_bound_dataclasses_have_no_forbidden_authority_fields() -> None:
    from generate.sealed_practice_trace import PracticeTraceRefusal, SealedPracticeTrace

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
        "selected_candidate",
        "best",
        "best_candidate",
        "serving_allowed",
        "runnable",
    }
    for record_type in (PracticeTraceInput, SealedPracticeTrace, PracticeTraceRefusal):
        assert forbidden.isdisjoint(
            {field.name for field in dataclasses.fields(record_type)}
        )


def _quantity_entity_chain() -> tuple[
    GeometricSearchRun,
    CandidateOperatorResult,
    CandidateAttemptRunBinding,
]:
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
    assert isinstance(result, CandidateOperatorResult)

    # binding
    binding = bind_candidate_attempt_to_run(
        original_run=run,
        candidate_operator_result=result,
    )
    assert isinstance(binding, CandidateAttemptRunBinding)

    return run, result, binding


def test_quantity_entity_sealed_episode_success() -> None:
    run, result, binding = _quantity_entity_chain()

    # build_replay_adapter_input_from_binding with vacuous proof
    replay_input = build_replay_adapter_input_from_binding(
        run=run,
        binding=binding,
        candidate_operator_result=result,
        schema_versions=(VACUOUS_PROOF_DECLARATION,),
    )
    assert isinstance(replay_input, ReplayAdapterInput)

    # classify_replay_result
    replay_result = classify_replay_result(
        replay_input,
        contract_replay_assessment_id="contract-replay-quantity-entity-closed",
        contract_closed=True,
    )
    assert isinstance(replay_result, ReplayAdapterResult)

    # build_bound_practice_trace_input
    trace_input = _build_bound_trace_input(
        run,
        result,
        binding,
        replay_results=(replay_result,),
    )
    assert isinstance(trace_input, PracticeTraceInput)

    # seal_bound_practice_trace
    trace = _seal_bound(
        trace_input,
        run,
        result,
        binding,
        replay_results=(replay_result,),
    )
    assert isinstance(trace, SealedPracticeTrace)

    # Required assertions
    assert trace.candidate_attempt_ids == (binding.candidate_attempt_id,)
    assert trace.candidate_attempt_binding_ids == (binding.binding_id,)
    assert trace.replay_result_ids == (replay_result.replay_result_id,)
    assert trace.replay_refusal_ids == ()
    assert trace.practice_disposition == PracticeDisposition.SEALED_CANDIDATE_REPLAY_CLOSED
    assert run.candidate_attempts == ()

    # Assert trace remains diagnostic-only
    assert not hasattr(trace, "answer")
    assert not hasattr(trace, "final_answer")
    assert not hasattr(trace, "served_output")
    assert not hasattr(trace, "proof")
    assert not hasattr(trace, "verdict")
    assert not hasattr(trace, "score")
    assert not hasattr(trace, "rank")
    assert not hasattr(trace, "selected")
    assert not hasattr(trace, "best")
    assert not hasattr(trace, "serving_allowed")
    assert not hasattr(trace, "runnable")
    assert not hasattr(trace, "mutation")
    assert not hasattr(trace, "promotion")


