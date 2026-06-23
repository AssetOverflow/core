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
    BudgetCharge,
    BudgetConsumed,
    CandidateAttempt,
    CandidateReplayStatus,
    GeometricSearchRun,
    SearchRunDisposition,
    SearchRunRefusal,
    initialize_geometric_search_run,
)
from generate.kernel_facts import SourceSpan
from generate.replay_adapter import (
    VACUOUS_PROOF_DECLARATION,
    ReplayAdapterInput,
    ReplayAdapterRefusal,
    ReplayAdapterResult,
    ReplayDisposition,
    build_replay_adapter_input,
    classify_replay_result,
)
from generate.search_gate import SearchGateDecision, SearchGateStatus
from generate.sealed_practice_trace import (
    SEALED_PRACTICE_TRACE_POLICY_VERSION,
    PracticeDisposition,
    PracticeTraceInput,
    PracticeTraceRefusal,
    SealedPracticeTrace,
    build_practice_trace_input,
    seal_practice_trace,
)

DEFAULT_CANDIDATE_ORGAN = "unary_delta_transition"


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


def _gate(
    *,
    input_digest: str = "a" * 64,
    residual_ids: tuple[str, ...] = ("residual-a",),
    status: SearchGateStatus = SearchGateStatus.ELIGIBLE,
    reason_code: str = "eligible_missing_role",
) -> SearchGateDecision:
    payload = {
        "policy_version": "search_gate.v1",
        "input_digest": input_digest,
        "residual_ids": list(residual_ids),
        "candidate_organ": "unary_delta_transition",
        "status": status.value,
        "reason_code": reason_code,
        "evidence_spans": [],
    }
    return SearchGateDecision(
        decision_id=_digest(payload),
        policy_version="search_gate.v1",
        input_digest=input_digest,
        residual_ids=residual_ids,
        candidate_organ="unary_delta_transition",
        status=status,
        reason_code=reason_code,
        evidence_spans=(),
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
        "evidence_spans": [],
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


def _empty_run() -> GeometricSearchRun:
    gate = _gate()
    budget = _budget(gate)
    outcome = initialize_geometric_search_run(
        problem_frame_digest="f" * 64,
        contract_assessment_id="assessment-a",
        residual_ids=gate.residual_ids,
        gate_decision=gate,
        compute_budget=budget,
        operator_set_id="operator-set-empty",
        operator_set_version="operators.v1",
    )
    assert isinstance(outcome, GeometricSearchRun)
    return outcome


def _run_with_attempt(
    attempt: CandidateAttempt | None = None,
    *,
    input_digest: str = "d" * 64,
) -> GeometricSearchRun:
    base = _empty_run()
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


def _gate_blocked_refusal() -> SearchRunRefusal:
    gate = _gate(status=SearchGateStatus.BLOCKED, reason_code="blocked_reason")
    budget = _budget(
        gate,
        status=ComputeBudgetStatus.BUDGET_BLOCKED,
        reason_code="budget_blocked_gate_not_eligible",
        max_candidates=0,
        max_depth=0,
        max_steps=0,
        max_parallelism=0,
    )
    outcome = initialize_geometric_search_run(
        problem_frame_digest="f" * 64,
        contract_assessment_id="assessment-a",
        residual_ids=gate.residual_ids,
        gate_decision=gate,
        compute_budget=budget,
        operator_set_id="operator-set-empty",
        operator_set_version="operators.v1",
    )
    assert isinstance(outcome, SearchRunRefusal)
    return outcome


def _replay_result(
    run: GeometricSearchRun,
    *,
    disposition: ReplayDisposition = ReplayDisposition.CONTRACT_REFUSED,
    schema_versions: tuple[tuple[str, str], ...] = (),
    proof_obligation_refs: tuple[str, ...] = (),
) -> ReplayAdapterResult:
    attempt = run.candidate_attempts[0]
    if disposition is ReplayDisposition.CONTRACT_AND_PROOF_CLOSED:
        schema_versions = schema_versions or (VACUOUS_PROOF_DECLARATION,)
    if disposition is ReplayDisposition.CONTRACT_CLOSED_BUT_PROOF_REFUSED:
        proof_obligation_refs = proof_obligation_refs or ("obligation-a",)
    replay_input = build_replay_adapter_input(
        run=run,
        attempt=attempt,
        candidate_digest=attempt.candidate_digest,
        candidate_reconstruction_digest="c" * 64,
        problem_frame_digest=run.problem_frame_digest,
        original_contract_assessment_id=run.contract_assessment_id,
        candidate_organ=DEFAULT_CANDIDATE_ORGAN,
        schema_versions=schema_versions,
        proof_obligation_refs=proof_obligation_refs,
    )
    assert isinstance(replay_input, ReplayAdapterInput)
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


def _replay_refusal(run: GeometricSearchRun) -> ReplayAdapterRefusal:
    attempt = run.candidate_attempts[0]
    replay_input = build_replay_adapter_input(
        run=run,
        attempt=attempt,
        candidate_digest=attempt.candidate_digest,
        candidate_reconstruction_digest="c" * 64,
        problem_frame_digest=run.problem_frame_digest,
        original_contract_assessment_id=run.contract_assessment_id,
        candidate_organ=DEFAULT_CANDIDATE_ORGAN,
    )
    assert isinstance(replay_input, ReplayAdapterInput)
    outcome = classify_replay_result(
        replay_input,
        contract_replay_assessment_id=None,
        contract_closed=True,
    )
    assert isinstance(outcome, ReplayAdapterRefusal)
    return outcome


def _build_trace_input(
    run: GeometricSearchRun | SearchRunRefusal,
    *,
    replay_results: tuple[ReplayAdapterResult, ...] = (),
    replay_refusals: tuple[ReplayAdapterRefusal, ...] = (),
    **changes: object,
) -> PracticeTraceInput | PracticeTraceRefusal:
    if isinstance(run, GeometricSearchRun):
        values: dict[str, object] = {
            "problem_frame_digest": run.problem_frame_digest,
            "original_contract_assessment_id": run.contract_assessment_id,
            "residual_ids": run.residual_ids,
            "search_gate_decision_id": run.gate_decision_id,
            "compute_budget_id": run.budget_id,
            "run": run,
            "replay_results": replay_results,
            "replay_refusals": replay_refusals,
        }
    else:
        values = {
            "problem_frame_digest": "f" * 64,
            "original_contract_assessment_id": "assessment-a",
            "residual_ids": ("residual-a",),
            "search_gate_decision_id": run.gate_decision_id or "g" * 64,
            "compute_budget_id": run.budget_id or "h" * 64,
            "run": run,
            "replay_results": replay_results,
            "replay_refusals": replay_refusals,
        }
    values.update(changes)
    return build_practice_trace_input(**values)  # type: ignore[arg-type]


def _expected_input_digest(
    *,
    problem_frame_digest: str,
    original_contract_assessment_id: str,
    residual_ids: tuple[str, ...],
    search_gate_decision_id: str,
    compute_budget_id: str,
    geometric_search_run_id: str,
    candidate_attempt_ids: tuple[str, ...],
    replay_result_ids: tuple[str, ...],
    replay_refusal_ids: tuple[str, ...],
    schema_versions: tuple[tuple[str, str], ...] = (),
    policy_versions: tuple[tuple[str, str], ...] = (),
) -> str:
    return _digest(
        {
            "trace_policy_version": SEALED_PRACTICE_TRACE_POLICY_VERSION,
            "problem_frame_digest": problem_frame_digest,
            "original_contract_assessment_id": original_contract_assessment_id,
            "residual_ids": list(residual_ids),
            "search_gate_decision_id": search_gate_decision_id,
            "compute_budget_id": compute_budget_id,
            "geometric_search_run_id": geometric_search_run_id,
            "candidate_attempt_ids": list(candidate_attempt_ids),
            "candidate_attempt_binding_ids": [],
            "replay_result_ids": list(replay_result_ids),
            "replay_refusal_ids": list(replay_refusal_ids),
            "schema_versions": [[name, version] for name, version in schema_versions],
            "policy_versions": [[name, version] for name, version in policy_versions],
        }
    )


def _expected_trace_id(
    *,
    trace_input: PracticeTraceInput,
    practice_disposition: PracticeDisposition,
    evidence_spans: tuple[SourceSpan, ...],
) -> str:
    identity_chain = (
        trace_input.problem_frame_digest,
        trace_input.original_contract_assessment_id,
        *trace_input.residual_ids,
        trace_input.search_gate_decision_id,
        trace_input.compute_budget_id,
        trace_input.geometric_search_run_id,
        *trace_input.candidate_attempt_ids,
        *trace_input.candidate_attempt_binding_ids,
        *trace_input.replay_result_ids,
        *trace_input.replay_refusal_ids,
    )
    return _digest(
        {
            "trace_id": "",
            "trace_policy_version": trace_input.trace_policy_version,
            "input_digest": trace_input.input_digest,
            "problem_frame_digest": trace_input.problem_frame_digest,
            "original_contract_assessment_id": trace_input.original_contract_assessment_id,
            "residual_ids": list(trace_input.residual_ids),
            "search_gate_decision_id": trace_input.search_gate_decision_id,
            "compute_budget_id": trace_input.compute_budget_id,
            "geometric_search_run_id": trace_input.geometric_search_run_id,
            "candidate_attempt_ids": list(trace_input.candidate_attempt_ids),
            "candidate_attempt_binding_ids": list(trace_input.candidate_attempt_binding_ids),
            "replay_result_ids": list(trace_input.replay_result_ids),
            "replay_refusal_ids": list(trace_input.replay_refusal_ids),
            "upstream_identity_chain": list(identity_chain),
            "practice_disposition": practice_disposition.value,
            "trace_records": list(identity_chain),
            "evidence_spans": [_span_payload(span) for span in evidence_spans],
            "created_by_policy": SEALED_PRACTICE_TRACE_POLICY_VERSION,
        }
    )


def _expected_refusal_id(
    *,
    input_digest: str | None,
    disposition: PracticeDisposition,
    reason_codes: tuple[str, ...],
) -> str:
    return _digest(
        {
            "trace_refusal_id": "",
            "trace_policy_version": SEALED_PRACTICE_TRACE_POLICY_VERSION,
            "input_digest": input_digest,
            "practice_disposition": disposition.value,
            "reason_codes": list(reason_codes),
        }
    )


def test_public_api_exports_are_exact() -> None:
    import generate.sealed_practice_trace as sealed_trace

    expected = (
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
    )
    assert SEALED_PRACTICE_TRACE_POLICY_VERSION == "sealed_practice_trace.v1"
    assert tuple(sealed_trace.__all__) == expected
    namespace = {}
    exec("from generate.sealed_practice_trace import *", namespace)
    assert tuple(sorted(name for name in namespace if not name.startswith("_"))) == tuple(
        sorted(expected)
    )


def test_valid_full_practice_chain_seals_deterministic_trace() -> None:
    run = _run_with_attempt()
    replay = _replay_result(
        run,
        disposition=ReplayDisposition.CONTRACT_AND_PROOF_CLOSED,
    )
    trace_input = _build_trace_input(run, replay_results=(replay,))
    assert isinstance(trace_input, PracticeTraceInput)

    first = seal_practice_trace(
        trace_input,
        run=run,
        replay_results=(replay,),
        evidence_spans=(SourceSpan("alpha", 0, 5, 0),),
    )
    second = seal_practice_trace(
        trace_input,
        run=run,
        replay_results=(replay,),
        evidence_spans=(SourceSpan("alpha", 0, 5, 0),),
    )
    assert isinstance(first, SealedPracticeTrace)
    assert isinstance(second, SealedPracticeTrace)
    assert first.trace_id == second.trace_id
    assert first.practice_disposition is PracticeDisposition.SEALED_CANDIDATE_REPLAY_CLOSED
    assert first.trace_id == _expected_trace_id(
        trace_input=trace_input,
        practice_disposition=PracticeDisposition.SEALED_CANDIDATE_REPLAY_CLOSED,
        evidence_spans=(SourceSpan("alpha", 0, 5, 0),),
    )


def test_original_refusal_episode_seals_as_sealed_original_refusal() -> None:
    refusal = _gate_blocked_refusal()
    trace_input = _build_trace_input(refusal)
    assert isinstance(trace_input, PracticeTraceInput)
    sealed = seal_practice_trace(trace_input, run=refusal)
    assert isinstance(sealed, SealedPracticeTrace)
    assert sealed.practice_disposition is PracticeDisposition.SEALED_ORIGINAL_REFUSAL


def test_invalid_input_run_refusal_seals_as_sealed_original_refusal() -> None:
    gate = _gate()
    budget = dataclasses.replace(_budget(gate), gate_decision_id="0" * 64)
    outcome = initialize_geometric_search_run(
        problem_frame_digest="f" * 64,
        contract_assessment_id="assessment-a",
        residual_ids=gate.residual_ids,
        gate_decision=gate,
        compute_budget=budget,
        operator_set_id="operator-set-empty",
        operator_set_version="operators.v1",
    )
    assert isinstance(outcome, SearchRunRefusal)
    assert outcome.run_disposition is SearchRunDisposition.INVALID_INPUT
    trace_input = _build_trace_input(outcome)
    assert isinstance(trace_input, PracticeTraceInput)
    sealed = seal_practice_trace(trace_input, run=outcome)
    assert isinstance(sealed, SealedPracticeTrace)
    assert sealed.practice_disposition is PracticeDisposition.SEALED_ORIGINAL_REFUSAL


def test_empty_successful_run_seals_as_sealed_exhausted_no_candidate() -> None:
    run = _empty_run()
    trace_input = _build_trace_input(run)
    assert isinstance(trace_input, PracticeTraceInput)
    sealed = seal_practice_trace(trace_input, run=run)
    assert isinstance(sealed, SealedPracticeTrace)
    assert sealed.practice_disposition is PracticeDisposition.SEALED_EXHAUSTED_NO_CANDIDATE


def test_all_candidate_contract_refusals_seal_as_sealed_all_candidates_refused() -> None:
    run = _run_with_attempt()
    replay = _replay_result(run, disposition=ReplayDisposition.CONTRACT_REFUSED)
    trace_input = _build_trace_input(run, replay_results=(replay,))
    assert isinstance(trace_input, PracticeTraceInput)
    sealed = seal_practice_trace(trace_input, run=run, replay_results=(replay,))
    assert isinstance(sealed, SealedPracticeTrace)
    assert sealed.practice_disposition is PracticeDisposition.SEALED_ALL_CANDIDATES_REFUSED


def test_replay_refusals_only_seal_as_sealed_replay_unavailable() -> None:
    run = _run_with_attempt()
    refusal = _replay_refusal(run)
    trace_input = _build_trace_input(run, replay_refusals=(refusal,))
    assert isinstance(trace_input, PracticeTraceInput)
    sealed = seal_practice_trace(trace_input, run=run, replay_refusals=(refusal,))
    assert isinstance(sealed, SealedPracticeTrace)
    assert sealed.practice_disposition is PracticeDisposition.SEALED_REPLAY_UNAVAILABLE


def test_contract_closed_proof_refused_seals_correctly() -> None:
    run = _run_with_attempt()
    replay = _replay_result(
        run,
        disposition=ReplayDisposition.CONTRACT_CLOSED_BUT_PROOF_REFUSED,
        schema_versions=(),
    )
    replay_input = build_replay_adapter_input(
        run=run,
        attempt=run.candidate_attempts[0],
        candidate_digest=run.candidate_attempts[0].candidate_digest,
        candidate_reconstruction_digest="c" * 64,
        problem_frame_digest=run.problem_frame_digest,
        original_contract_assessment_id=run.contract_assessment_id,
        candidate_organ=DEFAULT_CANDIDATE_ORGAN,
        proof_obligation_refs=("obligation-a",),
    )
    assert isinstance(replay_input, ReplayAdapterInput)
    replay = classify_replay_result(
        replay_input,
        contract_replay_assessment_id="e" * 64,
        contract_closed=True,
    )
    assert isinstance(replay, ReplayAdapterResult)
    trace_input = _build_trace_input(run, replay_results=(replay,))
    assert isinstance(trace_input, PracticeTraceInput)
    sealed = seal_practice_trace(trace_input, run=run, replay_results=(replay,))
    assert isinstance(sealed, SealedPracticeTrace)
    assert (
        sealed.practice_disposition
        is PracticeDisposition.SEALED_CONTRACT_CLOSED_PROOF_REFUSED
    )


def test_contract_and_proof_closed_seals_without_answer_fields() -> None:
    run = _run_with_attempt()
    replay = _replay_result(
        run,
        disposition=ReplayDisposition.CONTRACT_AND_PROOF_CLOSED,
    )
    trace_input = _build_trace_input(run, replay_results=(replay,))
    assert isinstance(trace_input, PracticeTraceInput)
    sealed = seal_practice_trace(trace_input, run=run, replay_results=(replay,))
    assert isinstance(sealed, SealedPracticeTrace)
    assert sealed.practice_disposition is PracticeDisposition.SEALED_CANDIDATE_REPLAY_CLOSED
    forbidden = {
        "answer",
        "final_answer",
        "served_output",
        "promotion",
        "selected_candidate",
        "best_candidate",
        "confidence",
        "score",
        "rank",
    }
    assert forbidden.isdisjoint({field.name for field in dataclasses.fields(sealed)})


def test_missing_upstream_ids_return_practice_trace_refusal() -> None:
    run = _run_with_attempt()
    outcome = build_practice_trace_input(
        problem_frame_digest="",
        original_contract_assessment_id=run.contract_assessment_id,
        residual_ids=run.residual_ids,
        search_gate_decision_id=run.gate_decision_id,
        compute_budget_id=run.budget_id,
        run=run,
    )
    assert isinstance(outcome, PracticeTraceRefusal)
    assert outcome.practice_disposition is PracticeDisposition.TRACE_INVALID_INPUT


def test_unsupported_trace_policy_returns_trace_policy_unsupported() -> None:
    run = _empty_run()
    outcome = build_practice_trace_input(
        problem_frame_digest=run.problem_frame_digest,
        original_contract_assessment_id=run.contract_assessment_id,
        residual_ids=run.residual_ids,
        search_gate_decision_id=run.gate_decision_id,
        compute_budget_id=run.budget_id,
        run=run,
        trace_policy_version="sealed_practice_trace.future",
    )
    assert isinstance(outcome, PracticeTraceRefusal)
    assert outcome.practice_disposition is PracticeDisposition.TRACE_POLICY_UNSUPPORTED


@pytest.mark.parametrize(
    "versions",
    (
        (("schema-b", "1"), ("schema-a", "1")),
        (("schema-a", "1"), ("schema-a", "2")),
    ),
)
def test_schema_policy_versions_must_be_unique_and_sorted(
    versions: tuple[tuple[str, str], ...],
) -> None:
    run = _empty_run()
    outcome = build_practice_trace_input(
        problem_frame_digest=run.problem_frame_digest,
        original_contract_assessment_id=run.contract_assessment_id,
        residual_ids=run.residual_ids,
        search_gate_decision_id=run.gate_decision_id,
        compute_budget_id=run.budget_id,
        run=run,
        schema_versions=versions,
    )
    assert isinstance(outcome, PracticeTraceRefusal)
    assert outcome.practice_disposition is PracticeDisposition.TRACE_INVALID_INPUT


def test_gate_budget_run_replay_identity_mismatch_returns_refusal() -> None:
    run = _run_with_attempt()
    outcome = build_practice_trace_input(
        problem_frame_digest=run.problem_frame_digest,
        original_contract_assessment_id=run.contract_assessment_id,
        residual_ids=run.residual_ids,
        search_gate_decision_id="0" * 64,
        compute_budget_id=run.budget_id,
        run=run,
    )
    assert isinstance(outcome, PracticeTraceRefusal)
    assert outcome.practice_disposition is PracticeDisposition.TRACE_IDENTITY_MISMATCH


def test_orphan_replay_result_fails_closed() -> None:
    run = _run_with_attempt()
    replay = _replay_result(run, disposition=ReplayDisposition.CONTRACT_REFUSED)
    orphan = dataclasses.replace(replay, run_id="0" * 64)
    outcome = build_practice_trace_input(
        problem_frame_digest=run.problem_frame_digest,
        original_contract_assessment_id=run.contract_assessment_id,
        residual_ids=run.residual_ids,
        search_gate_decision_id=run.gate_decision_id,
        compute_budget_id=run.budget_id,
        run=run,
        replay_results=(orphan,),
    )
    assert isinstance(outcome, PracticeTraceRefusal)
    assert outcome.practice_disposition is PracticeDisposition.TRACE_IDENTITY_MISMATCH


def test_replay_result_vs_replay_refusal_distinction_is_preserved() -> None:
    run = _run_with_attempt()
    result = _replay_result(run, disposition=ReplayDisposition.CONTRACT_REFUSED)
    refusal = _replay_refusal(run)
    assert type(result) is not type(refusal)
    trace_input = _build_trace_input(run, replay_results=(result,))
    assert isinstance(trace_input, PracticeTraceInput)
    assert result.replay_result_id in trace_input.replay_result_ids
    assert refusal.replay_refusal_id not in trace_input.replay_result_ids


def test_candidate_disagreement_is_preserved_without_selection_api() -> None:
    first_attempt = _attempt(attempt_id="attempt-a", candidate_digest="1" * 64)
    second_attempt = _attempt(
        attempt_id="attempt-b",
        attempt_index=1,
        candidate_digest="2" * 64,
    )
    base = _empty_run()
    consumed = BudgetConsumed(
        candidates_considered=2,
        max_candidates=5,
        depth_reached=1,
        max_depth=2,
        steps_used=2,
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
        "input_digest": "d" * 64,
        "candidate_attempts": [
            {
                "attempt_id": first_attempt.attempt_id,
                "attempt_index": first_attempt.attempt_index,
                "parent_attempt_id": first_attempt.parent_attempt_id,
                "operator_id": first_attempt.operator_id,
                "operator_version": first_attempt.operator_version,
                "input_digest": first_attempt.input_digest,
                "candidate_digest": first_attempt.candidate_digest,
                "budget_charge": {
                    "candidates": first_attempt.budget_charge.candidates,
                    "steps": first_attempt.budget_charge.steps,
                },
                "depth": first_attempt.depth,
                "step_index": first_attempt.step_index,
                "replay_status": first_attempt.replay_status.value,
                "replay_blockers": list(first_attempt.replay_blockers),
                "evidence_spans": [
                    _span_payload(span) for span in first_attempt.evidence_spans
                ],
            },
            {
                "attempt_id": second_attempt.attempt_id,
                "attempt_index": second_attempt.attempt_index,
                "parent_attempt_id": second_attempt.parent_attempt_id,
                "operator_id": second_attempt.operator_id,
                "operator_version": second_attempt.operator_version,
                "input_digest": second_attempt.input_digest,
                "candidate_digest": second_attempt.candidate_digest,
                "budget_charge": {
                    "candidates": second_attempt.budget_charge.candidates,
                    "steps": second_attempt.budget_charge.steps,
                },
                "depth": second_attempt.depth,
                "step_index": second_attempt.step_index,
                "replay_status": second_attempt.replay_status.value,
                "replay_blockers": list(second_attempt.replay_blockers),
                "evidence_spans": [
                    _span_payload(span) for span in second_attempt.evidence_spans
                ],
            },
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
    run = GeometricSearchRun(
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
        input_digest="d" * 64,
        candidate_attempts=(first_attempt, second_attempt),
        budget_consumed=consumed,
        run_disposition=SearchRunDisposition.CANDIDATE_REPLAY_PENDING,
        exhaustion_code=None,
        explanation="two attempts",
    )

    first_replay_input = build_replay_adapter_input(
        run=run,
        attempt=first_attempt,
        candidate_digest=first_attempt.candidate_digest,
        candidate_reconstruction_digest="c" * 64,
        problem_frame_digest=run.problem_frame_digest,
        original_contract_assessment_id=run.contract_assessment_id,
        candidate_organ=DEFAULT_CANDIDATE_ORGAN,
        schema_versions=(VACUOUS_PROOF_DECLARATION,),
    )
    second_replay_input = build_replay_adapter_input(
        run=run,
        attempt=second_attempt,
        candidate_digest=second_attempt.candidate_digest,
        candidate_reconstruction_digest="d" * 64,
        problem_frame_digest=run.problem_frame_digest,
        original_contract_assessment_id=run.contract_assessment_id,
        candidate_organ=DEFAULT_CANDIDATE_ORGAN,
        schema_versions=(VACUOUS_PROOF_DECLARATION,),
    )
    assert isinstance(first_replay_input, ReplayAdapterInput)
    assert isinstance(second_replay_input, ReplayAdapterInput)
    first_result = classify_replay_result(
        first_replay_input,
        contract_replay_assessment_id="e" * 64,
        contract_closed=True,
    )
    second_result = classify_replay_result(
        second_replay_input,
        contract_replay_assessment_id="f" * 64,
        contract_closed=True,
    )
    assert isinstance(first_result, ReplayAdapterResult)
    assert isinstance(second_result, ReplayAdapterResult)
    assert first_result.replay_result_id != second_result.replay_result_id

    trace_input = _build_trace_input(
        run,
        replay_results=(first_result, second_result),
    )
    assert isinstance(trace_input, PracticeTraceInput)
    sealed = seal_practice_trace(
        trace_input,
        run=run,
        replay_results=(first_result, second_result),
    )
    assert isinstance(sealed, SealedPracticeTrace)
    assert sealed.practice_disposition is PracticeDisposition.SEALED_CANDIDATE_REPLAY_CLOSED
    assert sealed.replay_result_ids == (
        first_result.replay_result_id,
        second_result.replay_result_id,
    )
    assert not hasattr(sealed, "selected_candidate")
    assert not hasattr(sealed, "best_candidate")


def test_duplicate_evidence_spans_are_preserved() -> None:
    run = _empty_run()
    trace_input = _build_trace_input(run)
    assert isinstance(trace_input, PracticeTraceInput)
    span = SourceSpan("dup", 1, 4, 0)
    sealed = seal_practice_trace(
        trace_input,
        run=run,
        evidence_spans=(span, span),
    )
    assert isinstance(sealed, SealedPracticeTrace)
    assert sealed.evidence_spans == (span, span)


def test_evidence_span_reorder_changes_trace_identity() -> None:
    run = _empty_run()
    trace_input = _build_trace_input(run)
    assert isinstance(trace_input, PracticeTraceInput)
    first_span = SourceSpan("one", 0, 3, 0)
    second_span = SourceSpan("two", 4, 7, 1)
    first = seal_practice_trace(
        trace_input,
        run=run,
        evidence_spans=(first_span, second_span),
    )
    second = seal_practice_trace(
        trace_input,
        run=run,
        evidence_spans=(second_span, first_span),
    )
    assert isinstance(first, SealedPracticeTrace)
    assert isinstance(second, SealedPracticeTrace)
    assert first.trace_id != second.trace_id


def test_trace_ids_are_canonical_and_exclude_prose() -> None:
    run = _empty_run()
    trace_input = _build_trace_input(run)
    assert isinstance(trace_input, PracticeTraceInput)
    assert trace_input.input_digest == _expected_input_digest(
        problem_frame_digest=run.problem_frame_digest,
        original_contract_assessment_id=run.contract_assessment_id,
        residual_ids=run.residual_ids,
        search_gate_decision_id=run.gate_decision_id,
        compute_budget_id=run.budget_id,
        geometric_search_run_id=run.run_id,
        candidate_attempt_ids=(),
        replay_result_ids=(),
        replay_refusal_ids=(),
    )
    sealed = seal_practice_trace(trace_input, run=run, explanation="localized prose")
    assert isinstance(sealed, SealedPracticeTrace)
    changed = dataclasses.replace(sealed, explanation="different prose")
    assert changed.trace_id == sealed.trace_id


def test_explanation_changes_do_not_affect_ids() -> None:
    run = _empty_run()
    trace_input = _build_trace_input(run)
    assert isinstance(trace_input, PracticeTraceInput)
    first = seal_practice_trace(trace_input, run=run, explanation="first prose")
    second = seal_practice_trace(trace_input, run=run, explanation="second prose")
    assert isinstance(first, SealedPracticeTrace)
    assert isinstance(second, SealedPracticeTrace)
    assert first.trace_id == second.trace_id


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
        PracticeTraceInput,
        SealedPracticeTrace,
        PracticeTraceRefusal,
    ):
        assert forbidden.isdisjoint(
            {field.name for field in dataclasses.fields(record_type)}
        )


def test_module_coupling_and_side_effect_guards() -> None:
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

    assert imports <= {
        "__future__",
        "dataclasses",
        "enum",
        "hashlib",
        "json",
        "generate.geometric_search_run",
        "generate.kernel_facts",
        "generate.replay_adapter",
    }
    assert {
        "decide_search_gate",
        "decide_compute_budget",
        "initialize_geometric_search_run",
        "assess_contracts",
        "project_contract_residuals",
        "determine",
        "build_replay_adapter_input",
        "build_replay_adapter_input_from_binding",
        "classify_replay_result",
        "build_missing_role_candidate",
        "bind_candidate_attempt_to_run",
    }.isdisjoint(imported_names)
    assert {
        "decide_search_gate",
        "decide_compute_budget",
        "initialize_geometric_search_run",
        "assess_contracts",
        "project_contract_residuals",
        "determine",
        "build_missing_role_candidate",
        "bind_candidate_attempt_to_run",
        "build_replay_adapter_input_from_binding",
        "classify_replay_result",
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
        "generate/replay_adapter.py",
        "generate/compute_budget.py",
        "generate/search_gate.py",
        "generate/contract_residuals.py",
    ):
        assert "sealed_practice_trace" not in Path(upstream).read_text("utf-8")


def test_no_filesystem_network_clock_random_or_environment_identity() -> None:
    source = Path("generate/sealed_practice_trace.py").read_text("utf-8")
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


def test_candidates_without_replay_records_fail_closed() -> None:
    run = _run_with_attempt()
    trace_input = _build_trace_input(run)
    assert isinstance(trace_input, PracticeTraceInput)
    sealed = seal_practice_trace(trace_input, run=run)
    assert isinstance(sealed, PracticeTraceRefusal)
    assert sealed.practice_disposition is PracticeDisposition.TRACE_UPSTREAM_INCOMPLETE


def test_replay_records_with_run_refusal_fail_closed_at_build() -> None:
    refusal = _gate_blocked_refusal()
    run = _run_with_attempt()
    replay = _replay_result(run, disposition=ReplayDisposition.CONTRACT_REFUSED)
    outcome = build_practice_trace_input(
        problem_frame_digest="f" * 64,
        original_contract_assessment_id="assessment-a",
        residual_ids=("residual-a",),
        search_gate_decision_id=refusal.gate_decision_id or "g" * 64,
        compute_budget_id=refusal.budget_id or "h" * 64,
        run=refusal,
        replay_results=(replay,),
    )
    assert isinstance(outcome, PracticeTraceRefusal)
    assert outcome.practice_disposition is PracticeDisposition.TRACE_INVALID_INPUT


def test_refusal_id_matches_canonical_payload() -> None:
    outcome = build_practice_trace_input(
        problem_frame_digest="",
        original_contract_assessment_id="assessment-a",
        residual_ids=("residual-a",),
        search_gate_decision_id="g" * 64,
        compute_budget_id="h" * 64,
        run=_empty_run(),
    )
    assert isinstance(outcome, PracticeTraceRefusal)
    assert outcome.trace_refusal_id == _expected_refusal_id(
        input_digest=None,
        disposition=outcome.practice_disposition,
        reason_codes=outcome.reason_codes,
    )


def test_ordinary_malformed_objects_fail_closed_without_throwing() -> None:
    outcome = build_practice_trace_input(
        problem_frame_digest="f" * 64,
        original_contract_assessment_id="assessment-a",
        residual_ids=("residual-a",),
        search_gate_decision_id="g" * 64,
        compute_budget_id="h" * 64,
        run=SimpleNamespace(),  # type: ignore[arg-type]
    )
    assert isinstance(outcome, PracticeTraceRefusal)