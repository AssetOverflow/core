from __future__ import annotations

import ast
import dataclasses
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from generate.compute_budget import ComputeBudgetDecision, ComputeBudgetStatus
from generate.geometric_search_run import (
    GEOMETRIC_SEARCH_RUN_POLICY_VERSION,
    GEOMETRIC_SEARCH_RUN_SCHEMA_VERSION,
    BudgetCharge,
    BudgetConsumed,
    CandidateAttempt,
    CandidateReplayStatus,
    GeometricSearchRun,
    SearchRunDisposition,
    initialize_geometric_search_run,
)
from generate.kernel_facts import SourceSpan
from generate.replay_adapter import (
    CONTRACT_PROOF_REPLAY_POLICY_VERSION,
    REPLAY_ADAPTER_POLICY_VERSION,
    VACUOUS_PROOF_DECLARATION,
    ProofReplayRef,
    ReplayAdapterInput,
    ReplayAdapterRefusal,
    ReplayAdapterResult,
    ReplayDisposition,
    ReplayRefusalReason,
    build_replay_adapter_input,
    classify_replay_result,
)
from generate.search_gate import SearchGateDecision, SearchGateStatus

DEFAULT_CANDIDATE_ORGAN = "unary_delta_transition"
DEFAULT_CONTRACT_TARGET = "problem_frame_contracts.unary_delta"


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


def _proof_ref_payload(ref: ProofReplayRef) -> dict[str, object]:
    return {
        "proof_obligation_id": ref.proof_obligation_id,
        "proof_obligation_version": ref.proof_obligation_version,
        "proof_replay_id": ref.proof_replay_id,
        "closed": ref.closed,
        "reason_code": ref.reason_code,
    }


def _gate(
    *,
    input_digest: str = "a" * 64,
    residual_ids: tuple[str, ...] = ("residual-a",),
) -> SearchGateDecision:
    payload = {
        "policy_version": "search_gate.v1",
        "input_digest": input_digest,
        "residual_ids": list(residual_ids),
        "candidate_organ": "unary_delta_transition",
        "status": SearchGateStatus.ELIGIBLE.value,
        "reason_code": "eligible_missing_role",
        "evidence_spans": [],
    }
    return SearchGateDecision(
        decision_id=_digest(payload),
        policy_version="search_gate.v1",
        input_digest=input_digest,
        residual_ids=residual_ids,
        candidate_organ="unary_delta_transition",
        status=SearchGateStatus.ELIGIBLE,
        reason_code="eligible_missing_role",
        evidence_spans=(),
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
        "evidence_spans": [],
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
        evidence_spans=(),
        explanation="budget prose",
    )


def _attempt(
    *,
    attempt_id: str = "attempt-a",
    attempt_index: int = 0,
    input_digest: str = "d" * 64,
    candidate_digest: str = "b" * 64,
    evidence_spans: tuple[SourceSpan, ...] = (SourceSpan("x", 0, 1, 0),),
) -> CandidateAttempt:
    return CandidateAttempt(
        attempt_id=attempt_id,
        attempt_index=attempt_index,
        parent_attempt_id=None,
        operator_id="operator-a",
        operator_version="operator.v1",
        input_digest=input_digest,
        candidate_digest=candidate_digest,
        budget_charge=BudgetCharge(candidates=1, steps=1),
        depth=1,
        step_index=0,
        replay_status=CandidateReplayStatus.REPLAY_PENDING,
        replay_blockers=("replay_not_authorized",),
        evidence_spans=evidence_spans,
        explanation="attempt prose",
    )


def _run_with_attempt(
    attempt: CandidateAttempt | None = None,
    *,
    input_digest: str = "d" * 64,
) -> GeometricSearchRun:
    gate = _gate()
    budget = _budget(gate)
    base = initialize_geometric_search_run(
        problem_frame_digest="f" * 64,
        contract_assessment_id="assessment-a",
        residual_ids=gate.residual_ids,
        gate_decision=gate,
        compute_budget=budget,
        operator_set_id="operator-set-empty",
        operator_set_version="operators.v1",
    )
    assert isinstance(base, GeometricSearchRun)
    selected = attempt or _attempt(input_digest=input_digest)
    consumed = BudgetConsumed(
        candidates_considered=1,
        max_candidates=5,
        depth_reached=1,
        max_depth=2,
        steps_used=1,
        max_steps=10,
        parallelism_used=1,
        max_parallelism=1,
        exhausted=False,
    )
    run_payload = {
        "run_id": "",
        "run_policy_version": base.run_policy_version,
        "schema_version": base.schema_version,
        "problem_frame_digest": base.problem_frame_digest,
        "contract_assessment_id": base.contract_assessment_id,
        "residual_ids": list(base.residual_ids),
        "gate_decision_id": base.gate_decision_id,
        "budget_id": base.budget_id,
        "operator_set_id": base.operator_set_id,
        "operator_set_version": base.operator_set_version,
        "input_digest": input_digest,
        "candidate_attempts": [
            {
                "attempt_id": selected.attempt_id,
                "attempt_index": selected.attempt_index,
                "parent_attempt_id": selected.parent_attempt_id,
                "operator_id": selected.operator_id,
                "operator_version": selected.operator_version,
                "input_digest": selected.input_digest,
                "candidate_digest": selected.candidate_digest,
                "budget_charge": {
                    "candidates": selected.budget_charge.candidates,
                    "steps": selected.budget_charge.steps,
                },
                "depth": selected.depth,
                "step_index": selected.step_index,
                "replay_status": selected.replay_status.value,
                "replay_blockers": list(selected.replay_blockers),
                "evidence_spans": [
                    _span_payload(span) for span in selected.evidence_spans
                ],
            }
        ],
        "budget_consumed": {
            "candidates_considered": consumed.candidates_considered,
            "max_candidates": consumed.max_candidates,
            "depth_reached": consumed.depth_reached,
            "max_depth": consumed.max_depth,
            "steps_used": consumed.steps_used,
            "max_steps": consumed.max_steps,
            "parallelism_used": consumed.parallelism_used,
            "max_parallelism": consumed.max_parallelism,
            "exhausted": consumed.exhausted,
        },
        "run_disposition": SearchRunDisposition.CANDIDATE_REPLAY_PENDING.value,
        "exhaustion_code": None,
    }
    return GeometricSearchRun(
        run_id=_digest(run_payload),
        run_policy_version=base.run_policy_version,
        schema_version=base.schema_version,
        problem_frame_digest=base.problem_frame_digest,
        contract_assessment_id=base.contract_assessment_id,
        residual_ids=base.residual_ids,
        gate_decision_id=base.gate_decision_id,
        budget_id=base.budget_id,
        operator_set_id=base.operator_set_id,
        operator_set_version=base.operator_set_version,
        input_digest=input_digest,
        candidate_attempts=(selected,),
        budget_consumed=consumed,
        run_disposition=SearchRunDisposition.CANDIDATE_REPLAY_PENDING,
        exhaustion_code=None,
        explanation="diagnostic run with one attempt",
    )


def _build_input(
    *,
    run: GeometricSearchRun | None = None,
    attempt: CandidateAttempt | None = None,
    candidate_digest: str = "b" * 64,
    reconstruction_digest: str = "c" * 64,
    **changes: object,
) -> ReplayAdapterInput | ReplayAdapterRefusal:
    selected_run = run or _run_with_attempt()
    selected_attempt = attempt or selected_run.candidate_attempts[0]
    values: dict[str, object] = {
        "run": selected_run,
        "attempt": selected_attempt,
        "candidate_digest": candidate_digest,
        "candidate_reconstruction_digest": reconstruction_digest,
        "problem_frame_digest": selected_run.problem_frame_digest,
        "original_contract_assessment_id": selected_run.contract_assessment_id,
        "candidate_organ": DEFAULT_CANDIDATE_ORGAN,
    }
    values.update(changes)
    return build_replay_adapter_input(**values)  # type: ignore[arg-type]


def _expected_input_digest(
    *,
    run: GeometricSearchRun,
    attempt: CandidateAttempt,
    candidate_digest: str,
    candidate_reconstruction_digest: str,
    problem_frame_digest: str,
    original_contract_assessment_id: str,
    candidate_organ: str = DEFAULT_CANDIDATE_ORGAN,
    contract_replay_target: str = DEFAULT_CONTRACT_TARGET,
    proof_obligation_refs: tuple[str, ...] = (),
    schema_versions: tuple[tuple[str, str], ...] = (),
) -> str:
    return _digest(
        {
            "replay_policy_version": CONTRACT_PROOF_REPLAY_POLICY_VERSION,
            "run_id": run.run_id,
            "run_policy_version": run.run_policy_version,
            "attempt_id": attempt.attempt_id,
            "attempt_index": attempt.attempt_index,
            "candidate_digest": candidate_digest,
            "candidate_reconstruction_digest": candidate_reconstruction_digest,
            "problem_frame_digest": problem_frame_digest,
            "original_contract_assessment_id": original_contract_assessment_id,
            "candidate_organ": candidate_organ,
            "residual_ids": list(run.residual_ids),
            "gate_decision_id": run.gate_decision_id,
            "budget_id": run.budget_id,
            "operator_set_id": run.operator_set_id,
            "operator_set_version": run.operator_set_version,
            "contract_replay_target": contract_replay_target,
            "proof_obligation_refs": list(proof_obligation_refs),
            "schema_versions": [[name, version] for name, version in schema_versions],
        }
    )


def _expected_result_id(
    *,
    replay_input: ReplayAdapterInput,
    contract_replay_assessment_id: str,
    proof_replay_refs: tuple[ProofReplayRef, ...],
    replay_disposition: ReplayDisposition,
    reason_codes: tuple[str, ...],
    evidence_spans: tuple[SourceSpan, ...],
) -> str:
    return _digest(
        {
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
    )


def _expected_refusal_id(
    *,
    input_digest: str | None,
    run_id: str | None,
    attempt_id: str | None,
    candidate_digest: str | None,
    replay_refusal_reason: ReplayRefusalReason,
    reason_codes: tuple[str, ...],
) -> str:
    return _digest(
        {
            "replay_refusal_id": "",
            "replay_policy_version": REPLAY_ADAPTER_POLICY_VERSION,
            "input_digest": input_digest,
            "run_id": run_id,
            "attempt_id": attempt_id,
            "candidate_digest": candidate_digest,
            "replay_disposition": replay_refusal_reason.value,
            "reason_codes": list(reason_codes),
        }
    )


def test_public_api_exports_are_exact() -> None:
    import generate.replay_adapter as replay_adapter

    assert CONTRACT_PROOF_REPLAY_POLICY_VERSION == "contract_proof_replay.v1"
    assert REPLAY_ADAPTER_POLICY_VERSION == CONTRACT_PROOF_REPLAY_POLICY_VERSION
    assert tuple(replay_adapter.__all__) == (
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
    )


def test_input_construction_success_and_deterministic_digest() -> None:
    run = _run_with_attempt()
    attempt = run.candidate_attempts[0]
    outcome = _build_input(run=run, attempt=attempt)

    assert isinstance(outcome, ReplayAdapterInput)
    assert outcome.run_id == run.run_id
    assert outcome.attempt_id == attempt.attempt_id
    assert outcome.candidate_digest == attempt.candidate_digest
    assert outcome.candidate_reconstruction_digest == "c" * 64
    assert outcome.problem_frame_digest == run.problem_frame_digest
    assert outcome.original_contract_assessment_id == run.contract_assessment_id
    assert outcome.residual_ids == run.residual_ids
    assert outcome.gate_decision_id == run.gate_decision_id
    assert outcome.budget_id == run.budget_id
    assert outcome.operator_set_id == run.operator_set_id
    assert outcome.operator_set_version == run.operator_set_version
    assert outcome.candidate_organ == DEFAULT_CANDIDATE_ORGAN
    assert outcome.contract_replay_target == DEFAULT_CONTRACT_TARGET
    assert outcome.input_digest == _expected_input_digest(
        run=run,
        attempt=attempt,
        candidate_digest=attempt.candidate_digest,
        candidate_reconstruction_digest="c" * 64,
        problem_frame_digest=run.problem_frame_digest,
        original_contract_assessment_id=run.contract_assessment_id,
    )


def test_adapter_failure_is_distinct_from_contract_refused() -> None:
    refusal = _build_input(candidate_digest="z" * 64)
    assert isinstance(refusal, ReplayAdapterRefusal)
    assert refusal.replay_disposition is ReplayRefusalReason.CANDIDATE_IDENTITY_MISMATCH

    replay_input = _build_input()
    assert isinstance(replay_input, ReplayAdapterInput)
    result = classify_replay_result(
        replay_input,
        contract_replay_assessment_id="e" * 64,
        contract_closed=False,
    )
    assert isinstance(result, ReplayAdapterResult)
    assert result.replay_disposition is ReplayDisposition.CONTRACT_REFUSED
    assert type(refusal) is not type(result)


@pytest.mark.parametrize(
    ("factory", "expected_reason"),
    (
        (
            lambda: _build_input(
                attempt=_attempt(attempt_id="missing"),
            ),
            ReplayRefusalReason.CANDIDATE_IDENTITY_MISMATCH,
        ),
        (
            lambda: _build_input(
                attempt=_attempt(attempt_index=9),
            ),
            ReplayRefusalReason.CANDIDATE_IDENTITY_MISMATCH,
        ),
        (
            lambda: _build_input(candidate_digest=""),
            ReplayRefusalReason.INVALID_REPLAY_INPUT,
        ),
        (
            lambda: _build_input(candidate_reconstruction_digest=""),
            ReplayRefusalReason.INVALID_REPLAY_INPUT,
        ),
        (
            lambda: _build_input(problem_frame_digest=""),
            ReplayRefusalReason.INVALID_REPLAY_INPUT,
        ),
        (
            lambda: _build_input(original_contract_assessment_id=""),
            ReplayRefusalReason.INVALID_REPLAY_INPUT,
        ),
    ),
)
def test_identity_mismatches_fail_closed(
    factory: object, expected_reason: ReplayRefusalReason
) -> None:
    outcome = factory()  # type: ignore[operator]
    assert isinstance(outcome, ReplayAdapterRefusal)
    assert outcome.replay_disposition is expected_reason


def test_duplicate_attempt_ids_fail_closed() -> None:
    first = _attempt(attempt_id="dup", attempt_index=0)
    second = _attempt(attempt_id="dup", attempt_index=1)
    run = GeometricSearchRun(
        run_id="r" * 64,
        run_policy_version=GEOMETRIC_SEARCH_RUN_POLICY_VERSION,
        schema_version=GEOMETRIC_SEARCH_RUN_SCHEMA_VERSION,
        problem_frame_digest="f" * 64,
        contract_assessment_id="assessment-a",
        residual_ids=("residual-a",),
        gate_decision_id="g" * 64,
        budget_id="h" * 64,
        operator_set_id="operator-set-empty",
        operator_set_version="operators.v1",
        input_digest="d" * 64,
        candidate_attempts=(first, second),
        budget_consumed=BudgetConsumed(
            candidates_considered=2,
            max_candidates=5,
            depth_reached=1,
            max_depth=2,
            steps_used=2,
            max_steps=10,
            parallelism_used=1,
            max_parallelism=1,
            exhausted=False,
        ),
        run_disposition=SearchRunDisposition.CANDIDATE_REPLAY_PENDING,
        exhaustion_code=None,
        explanation="duplicate attempt ids",
    )
    outcome = _build_input(run=run, attempt=first)
    assert isinstance(outcome, ReplayAdapterRefusal)
    assert "ambiguous_or_missing_attempt_id" in outcome.reason_codes


def test_unsupported_replay_policy_fails_closed() -> None:
    run = _run_with_attempt()
    attempt = run.candidate_attempts[0]
    outcome = build_replay_adapter_input(
        run=run,
        attempt=attempt,
        candidate_digest=attempt.candidate_digest,
        candidate_reconstruction_digest="c" * 64,
        problem_frame_digest=run.problem_frame_digest,
        original_contract_assessment_id=run.contract_assessment_id,
        candidate_organ=DEFAULT_CANDIDATE_ORGAN,
        replay_policy_version="replay_adapter.future",
    )
    assert isinstance(outcome, ReplayAdapterRefusal)
    assert outcome.replay_disposition is ReplayRefusalReason.UNSUPPORTED_REPLAY_POLICY


def test_contract_replay_unavailable_fails_closed() -> None:
    replay_input = _build_input()
    assert isinstance(replay_input, ReplayAdapterInput)

    for kwargs in (
        {"contract_replay_assessment_id": None, "contract_closed": True},
        {"contract_replay_assessment_id": "e" * 64, "contract_closed": None},
    ):
        outcome = classify_replay_result(replay_input, **kwargs)  # type: ignore[arg-type]
        assert isinstance(outcome, ReplayAdapterRefusal)
        assert outcome.replay_disposition is ReplayRefusalReason.CONTRACT_REPLAY_UNAVAILABLE


def test_contract_refused_skips_proof_when_obligations_present() -> None:
    run = _run_with_attempt()
    attempt = run.candidate_attempts[0]
    replay_input = build_replay_adapter_input(
        run=run,
        attempt=attempt,
        candidate_digest=attempt.candidate_digest,
        candidate_reconstruction_digest="c" * 64,
        problem_frame_digest=run.problem_frame_digest,
        original_contract_assessment_id=run.contract_assessment_id,
        candidate_organ=DEFAULT_CANDIDATE_ORGAN,
        proof_obligation_refs=("obligation-z", "obligation-a"),
    )
    assert isinstance(replay_input, ReplayAdapterInput)
    result = classify_replay_result(
        replay_input,
        contract_replay_assessment_id="e" * 64,
        contract_closed=False,
    )
    assert isinstance(result, ReplayAdapterResult)
    assert result.replay_disposition is ReplayDisposition.CONTRACT_REFUSED
    assert result.proof_replay_refs == ()


def test_contract_refused_replay_emits_result_not_refusal() -> None:
    replay_input = _build_input()
    assert isinstance(replay_input, ReplayAdapterInput)
    result = classify_replay_result(
        replay_input,
        contract_replay_assessment_id="e" * 64,
        contract_closed=False,
        reason_codes=("missing_binding",),
    )
    assert isinstance(result, ReplayAdapterResult)
    assert result.replay_disposition is ReplayDisposition.CONTRACT_REFUSED
    assert result.proof_replay_refs == ()


def test_contract_closed_proof_refused_cases() -> None:
    run = _run_with_attempt()
    attempt = run.candidate_attempts[0]
    replay_input = build_replay_adapter_input(
        run=run,
        attempt=attempt,
        candidate_digest=attempt.candidate_digest,
        candidate_reconstruction_digest="c" * 64,
        problem_frame_digest=run.problem_frame_digest,
        original_contract_assessment_id=run.contract_assessment_id,
        candidate_organ=DEFAULT_CANDIDATE_ORGAN,
        proof_obligation_refs=("obligation-a",),
    )
    assert isinstance(replay_input, ReplayAdapterInput)

    missing_proof = classify_replay_result(
        replay_input,
        contract_replay_assessment_id="e" * 64,
        contract_closed=True,
    )
    assert isinstance(missing_proof, ReplayAdapterResult)
    assert (
        missing_proof.replay_disposition
        is ReplayDisposition.CONTRACT_CLOSED_BUT_PROOF_REFUSED
    )

    open_proof = classify_replay_result(
        replay_input,
        contract_replay_assessment_id="e" * 64,
        contract_closed=True,
        proof_replay_refs=(
            ProofReplayRef(
                proof_obligation_id="obligation-a",
                proof_obligation_version="proof.v1",
                proof_replay_id="p" * 64,
                closed=False,
                reason_code="proof_refused",
            ),
        ),
    )
    assert isinstance(open_proof, ReplayAdapterResult)
    assert (
        open_proof.replay_disposition
        is ReplayDisposition.CONTRACT_CLOSED_BUT_PROOF_REFUSED
    )


def test_contract_closed_without_obligations_fails_without_declaration() -> None:
    replay_input = _build_input()
    assert isinstance(replay_input, ReplayAdapterInput)
    outcome = classify_replay_result(
        replay_input,
        contract_replay_assessment_id="e" * 64,
        contract_closed=True,
    )
    assert isinstance(outcome, ReplayAdapterRefusal)
    assert outcome.replay_disposition is ReplayRefusalReason.PROOF_REPLAY_UNAVAILABLE


def test_contract_and_proof_closed_with_vacuous_proof_declaration() -> None:
    replay_input = _build_input(
        schema_versions=(VACUOUS_PROOF_DECLARATION,),
    )
    assert isinstance(replay_input, ReplayAdapterInput)
    result = classify_replay_result(
        replay_input,
        contract_replay_assessment_id="e" * 64,
        contract_closed=True,
    )
    assert isinstance(result, ReplayAdapterResult)
    assert result.replay_disposition is ReplayDisposition.CONTRACT_AND_PROOF_CLOSED
    assert result.proof_obligation_refs == ()


def test_contract_and_proof_closed_with_all_obligations_closed() -> None:
    run = _run_with_attempt()
    attempt = run.candidate_attempts[0]
    replay_input = build_replay_adapter_input(
        run=run,
        attempt=attempt,
        candidate_digest=attempt.candidate_digest,
        candidate_reconstruction_digest="c" * 64,
        problem_frame_digest=run.problem_frame_digest,
        original_contract_assessment_id=run.contract_assessment_id,
        candidate_organ=DEFAULT_CANDIDATE_ORGAN,
        proof_obligation_refs=("obligation-a", "obligation-b"),
    )
    assert isinstance(replay_input, ReplayAdapterInput)
    refs = (
        ProofReplayRef("obligation-a", "proof.v1", "p1" * 32, True, "closed"),
        ProofReplayRef("obligation-b", "proof.v1", "p2" * 32, True, "closed"),
    )
    result = classify_replay_result(
        replay_input,
        contract_replay_assessment_id="e" * 64,
        contract_closed=True,
        proof_replay_refs=refs,
    )
    assert isinstance(result, ReplayAdapterResult)
    assert result.replay_disposition is ReplayDisposition.CONTRACT_AND_PROOF_CLOSED
    assert result.proof_replay_refs == refs


def test_multiple_candidates_are_not_selected() -> None:
    first_input = _build_input(schema_versions=(VACUOUS_PROOF_DECLARATION,))
    second_run = _run_with_attempt(
        _attempt(candidate_digest="9" * 64),
        input_digest="d" * 64,
    )
    second_attempt = second_run.candidate_attempts[0]
    second_input = _build_input(
        run=second_run,
        attempt=second_attempt,
        candidate_digest=second_attempt.candidate_digest,
        schema_versions=(VACUOUS_PROOF_DECLARATION,),
    )
    assert isinstance(first_input, ReplayAdapterInput)
    assert isinstance(second_input, ReplayAdapterInput)

    first_result = classify_replay_result(
        first_input,
        contract_replay_assessment_id="e" * 64,
        contract_closed=True,
    )
    second_result = classify_replay_result(
        second_input,
        contract_replay_assessment_id="f" * 64,
        contract_closed=True,
    )
    assert isinstance(first_result, ReplayAdapterResult)
    assert isinstance(second_result, ReplayAdapterResult)
    assert first_result.replay_result_id != second_result.replay_result_id
    forbidden = {"rank", "score", "priority", "selected", "best", "answer"}
    for record in (first_result, second_result):
        assert forbidden.isdisjoint({field.name for field in dataclasses.fields(record)})


def test_deterministic_ids_and_explanation_exclusion() -> None:
    replay_input = _build_input()
    assert isinstance(replay_input, ReplayAdapterInput)
    spans = (SourceSpan("a", 0, 1, 0), SourceSpan("a", 0, 1, 0))

    first = classify_replay_result(
        replay_input,
        contract_replay_assessment_id="e" * 64,
        contract_closed=False,
        evidence_spans=spans,
        explanation="first prose",
    )
    second = classify_replay_result(
        replay_input,
        contract_replay_assessment_id="e" * 64,
        contract_closed=False,
        evidence_spans=spans,
        explanation="second prose",
    )
    assert isinstance(first, ReplayAdapterResult)
    assert isinstance(second, ReplayAdapterResult)
    assert first.replay_result_id == second.replay_result_id
    assert first.replay_result_id == _expected_result_id(
        replay_input=replay_input,
        contract_replay_assessment_id="e" * 64,
        proof_replay_refs=(),
        replay_disposition=ReplayDisposition.CONTRACT_REFUSED,
        reason_codes=(),
        evidence_spans=spans,
    )

    changed_assessment = classify_replay_result(
        replay_input,
        contract_replay_assessment_id="f" * 64,
        contract_closed=False,
        evidence_spans=spans,
    )
    assert isinstance(changed_assessment, ReplayAdapterResult)
    assert changed_assessment.replay_result_id != first.replay_result_id

    closed_input = _build_input(schema_versions=(VACUOUS_PROOF_DECLARATION,))
    assert isinstance(closed_input, ReplayAdapterInput)
    changed_disposition = classify_replay_result(
        closed_input,
        contract_replay_assessment_id="e" * 64,
        contract_closed=True,
        evidence_spans=spans,
    )
    assert isinstance(changed_disposition, ReplayAdapterResult)
    assert changed_disposition.replay_result_id != first.replay_result_id

    changed_run = _run_with_attempt(
        _attempt(candidate_digest="1" * 64),
        input_digest="d" * 64,
    )
    changed_attempt = changed_run.candidate_attempts[0]
    changed_input = _build_input(
        run=changed_run,
        attempt=changed_attempt,
        candidate_digest=changed_attempt.candidate_digest,
    )
    assert isinstance(changed_input, ReplayAdapterInput)
    assert changed_input.input_digest != replay_input.input_digest


def test_evidence_spans_preserve_order_and_duplicates() -> None:
    replay_input = _build_input()
    assert isinstance(replay_input, ReplayAdapterInput)
    ordered = (
        SourceSpan("first", 0, 5, 0),
        SourceSpan("second", 6, 11, 1),
        SourceSpan("first", 0, 5, 0),
    )
    result = classify_replay_result(
        replay_input,
        contract_replay_assessment_id="e" * 64,
        contract_closed=False,
        evidence_spans=ordered,
    )
    assert isinstance(result, ReplayAdapterResult)
    assert result.evidence_spans == ordered

    reordered = (
        SourceSpan("second", 6, 11, 1),
        SourceSpan("first", 0, 5, 0),
        SourceSpan("first", 0, 5, 0),
    )
    reordered_result = classify_replay_result(
        replay_input,
        contract_replay_assessment_id="e" * 64,
        contract_closed=False,
        evidence_spans=reordered,
    )
    assert isinstance(reordered_result, ReplayAdapterResult)
    assert reordered_result.replay_result_id != result.replay_result_id


def test_malformed_evidence_spans_fail_closed() -> None:
    replay_input = _build_input()
    assert isinstance(replay_input, ReplayAdapterInput)
    bad_span = SimpleNamespace(text="bad", start=3, end=1, sentence_index=0)
    outcome = classify_replay_result(
        replay_input,
        contract_replay_assessment_id="e" * 64,
        contract_closed=False,
        evidence_spans=(bad_span,),  # type: ignore[arg-type]
    )
    assert isinstance(outcome, ReplayAdapterRefusal)
    assert outcome.replay_disposition is ReplayRefusalReason.INVALID_REPLAY_INPUT


def test_proof_replay_refs_preserve_order_and_validate() -> None:
    run = _run_with_attempt()
    attempt = run.candidate_attempts[0]
    replay_input = build_replay_adapter_input(
        run=run,
        attempt=attempt,
        candidate_digest=attempt.candidate_digest,
        candidate_reconstruction_digest="c" * 64,
        problem_frame_digest=run.problem_frame_digest,
        original_contract_assessment_id=run.contract_assessment_id,
        candidate_organ=DEFAULT_CANDIDATE_ORGAN,
        proof_obligation_refs=("obligation-a", "obligation-b"),
    )
    assert isinstance(replay_input, ReplayAdapterInput)
    refs = (
        ProofReplayRef("obligation-a", "proof.v1", "p1" * 32, True, "closed"),
        ProofReplayRef("obligation-b", "proof.v1", "p2" * 32, True, "closed"),
    )
    result = classify_replay_result(
        replay_input,
        contract_replay_assessment_id="e" * 64,
        contract_closed=True,
        proof_replay_refs=refs,
    )
    assert isinstance(result, ReplayAdapterResult)
    assert result.proof_replay_refs == refs

    malformed = classify_replay_result(
        replay_input,
        contract_replay_assessment_id="e" * 64,
        contract_closed=True,
        proof_replay_refs=(
            ProofReplayRef("", "proof.v1", "p1" * 32, True, "closed"),
        ),
    )
    assert isinstance(malformed, ReplayAdapterRefusal)


def test_unsupported_proof_obligation_fails_closed() -> None:
    run = _run_with_attempt()
    attempt = run.candidate_attempts[0]
    replay_input = build_replay_adapter_input(
        run=run,
        attempt=attempt,
        candidate_digest=attempt.candidate_digest,
        candidate_reconstruction_digest="c" * 64,
        problem_frame_digest=run.problem_frame_digest,
        original_contract_assessment_id=run.contract_assessment_id,
        candidate_organ=DEFAULT_CANDIDATE_ORGAN,
        proof_obligation_refs=("obligation-a",),
    )
    assert isinstance(replay_input, ReplayAdapterInput)
    outcome = classify_replay_result(
        replay_input,
        contract_replay_assessment_id="e" * 64,
        contract_closed=True,
        proof_replay_refs=(
            ProofReplayRef("other", "proof.v1", "p1" * 32, True, "closed"),
        ),
    )
    assert isinstance(outcome, ReplayAdapterRefusal)
    assert outcome.replay_disposition is ReplayRefusalReason.UNSUPPORTED_PROOF_OBLIGATION


def test_public_dataclasses_expose_no_authority_fields() -> None:
    forbidden = {
        "answer",
        "final_answer",
        "served_output",
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
        "serving_allowed",
        "runnable",
        "tool_call",
    }
    for record_type in (
        ProofReplayRef,
        ReplayAdapterInput,
        ReplayAdapterResult,
        ReplayAdapterRefusal,
    ):
        assert forbidden.isdisjoint(
            {field.name for field in dataclasses.fields(record_type)}
        )


def test_module_coupling_and_side_effect_guards() -> None:
    path = Path("generate/replay_adapter.py")
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
        "generate.geometric_search_run",
        "generate.kernel_facts",
    }
    assert {
        "decide_search_gate",
        "decide_compute_budget",
        "initialize_geometric_search_run",
        "assess_contracts",
        "project_contract_residuals",
        "determine",
    }.isdisjoint(imported_names)
    assert {
        "decide_search_gate",
        "decide_compute_budget",
        "initialize_geometric_search_run",
        "assess_contracts",
        "project_contract_residuals",
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
    for upstream in (
        "generate/geometric_search_run.py",
        "generate/compute_budget.py",
        "generate/search_gate.py",
        "generate/contract_residuals.py",
    ):
        assert "replay_adapter" not in Path(upstream).read_text("utf-8")


def test_no_filesystem_network_clock_random_or_environment_identity() -> None:
    source = Path("generate/replay_adapter.py").read_text("utf-8")
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


def test_ordinary_malformed_objects_fail_closed_without_throwing() -> None:
    outcome = build_replay_adapter_input(
        run=SimpleNamespace(),  # type: ignore[arg-type]
        attempt=SimpleNamespace(),  # type: ignore[arg-type]
        candidate_digest="b" * 64,
        candidate_reconstruction_digest="c" * 64,
        problem_frame_digest="f" * 64,
        original_contract_assessment_id="assessment-a",
        candidate_organ=DEFAULT_CANDIDATE_ORGAN,
    )
    assert isinstance(outcome, ReplayAdapterRefusal)


def test_proof_obligation_refs_preserve_declared_order() -> None:
    run = _run_with_attempt()
    attempt = run.candidate_attempts[0]
    ordered = ("obligation-z", "obligation-a")
    replay_input = build_replay_adapter_input(
        run=run,
        attempt=attempt,
        candidate_digest=attempt.candidate_digest,
        candidate_reconstruction_digest="c" * 64,
        problem_frame_digest=run.problem_frame_digest,
        original_contract_assessment_id=run.contract_assessment_id,
        candidate_organ=DEFAULT_CANDIDATE_ORGAN,
        proof_obligation_refs=ordered,
    )
    assert isinstance(replay_input, ReplayAdapterInput)
    assert replay_input.proof_obligation_refs == ordered


def test_unsupported_candidate_organ_fails_closed() -> None:
    outcome = _build_input(candidate_organ="unknown_organ")
    assert isinstance(outcome, ReplayAdapterRefusal)
    assert "unsupported_candidate_organ" in outcome.reason_codes


def test_refusal_id_matches_canonical_payload() -> None:
    refusal = _build_input(candidate_digest="")
    assert isinstance(refusal, ReplayAdapterRefusal)
    assert refusal.replay_disposition is ReplayRefusalReason.INVALID_REPLAY_INPUT
    assert refusal.replay_refusal_id == _expected_refusal_id(
        input_digest=None,
        run_id=refusal.run_id,
        attempt_id=refusal.attempt_id,
        candidate_digest=None,
        replay_refusal_reason=refusal.replay_disposition,
        reason_codes=refusal.reason_codes,
    )