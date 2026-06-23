from __future__ import annotations

import hashlib
import json
from types import SimpleNamespace

from generate.candidate_operator import (
    CANDIDATE_OPERATOR_SET_VERSION,
    QUANTITY_ENTITY_BINDING_CANDIDATE_OPERATOR_NAME,
    QUANTITY_ENTITY_BINDING_CANDIDATE_OPERATOR_VERSION,
    QUANTITY_ENTITY_BINDING_CANDIDATE_ORGAN,
    QUANTITY_ENTITY_BINDING_RESIDUAL_CODE,
    CandidateOperatorRefusal,
    CandidateOperatorRefusalReason,
    CandidateOperatorResult,
    GroundedQuantityEntityCue,
    build_quantity_entity_binding_candidate,
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
from generate.run_attempt_binding import bind_candidate_attempt_to_run
from generate.replay_adapter import build_replay_adapter_input_from_binding, ReplayAdapterRefusal, ReplayAdapterInput


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


def _span(text: str = "5 apples", start: int = 10, end: int = 18) -> SourceSpan:
    return SourceSpan(text=text, start=start, end=end, sentence_index=0)


def _residual(
    *,
    residual_id: str | None = None,
    evidence_spans: tuple[SourceSpan, ...] | None = None,
    residual_kind: ResidualKind = ResidualKind.MISSING_RELATION,
    residual_code: str = QUANTITY_ENTITY_BINDING_RESIDUAL_CODE,
    candidate_organ: str = QUANTITY_ENTITY_BINDING_CANDIDATE_ORGAN,
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
        family_id="state_change.quantity_entity",
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
    reason_code: str = "eligible_missing_relation",
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
    reason_code: str = "budget_allowed_missing_relation",
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
    quantity_mention_id: str = "q1",
    entity_mention_id: str = "e1",
    quantity_kind: str = "count",
    evidence_spans: tuple[SourceSpan, ...] | None = None,
    unit_mention_id: str | None = None,
) -> GroundedQuantityEntityCue:
    return GroundedQuantityEntityCue(
        quantity_mention_id=quantity_mention_id,
        entity_mention_id=entity_mention_id,
        quantity_kind=quantity_kind,
        evidence_spans=evidence_spans if evidence_spans is not None else (_span(),),
        unit_mention_id=unit_mention_id,
    )


def _chain() -> tuple[
    ContractResidual,
    SearchGateDecision,
    ComputeBudgetDecision,
    GeometricSearchRun,
    GroundedQuantityEntityCue,
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
        "grounded_quantity_entity_cues": (cue,),
    }
    values.update(changes)
    return build_quantity_entity_binding_candidate(**values)  # type: ignore[arg-type]


def test_valid_chain_produces_candidate_operator_result() -> None:
    outcome = _build()
    assert isinstance(outcome, CandidateOperatorResult)
    assert outcome.operator_name == QUANTITY_ENTITY_BINDING_CANDIDATE_OPERATOR_NAME
    assert outcome.operator_version == QUANTITY_ENTITY_BINDING_CANDIDATE_OPERATOR_VERSION
    assert outcome.candidate_organ == QUANTITY_ENTITY_BINDING_CANDIDATE_ORGAN
    assert outcome.attempt_index == 0
    assert outcome.candidate_attempt.budget_charge == BudgetCharge(candidates=1, steps=1)
    assert outcome.candidate_attempt.depth == 1
    assert outcome.candidate_attempt.replay_status == CandidateReplayStatus.REPLAY_PENDING
    assert outcome.candidate_attempt.replay_blockers == ()
    assert outcome.reason_codes == ()


def test_candidate_payload_matches_schema() -> None:
    outcome = _build()
    assert isinstance(outcome, CandidateOperatorResult)
    payload_dict = dict(outcome.candidate_reconstruction.candidate_payload)
    assert payload_dict == {
        "binding_type": "quantity_entity",
        "candidate_organ": QUANTITY_ENTITY_BINDING_CANDIDATE_ORGAN,
        "entity_mention_id": "e1",
        "kind": "mention_binding",
        "quantity_kind": "count",
        "quantity_mention_id": "q1",
        "relation_type": "quantity_entity",
        "source": "GroundedQuantityEntityCue",
        "unit_mention_id": "",
    }


def test_deterministic_result_id() -> None:
    first = _build()
    second = _build()
    assert isinstance(first, CandidateOperatorResult)
    assert isinstance(second, CandidateOperatorResult)
    assert first.operator_result_id == second.operator_result_id


def test_deterministic_attempt_id() -> None:
    first = _build()
    second = _build()
    assert isinstance(first, CandidateOperatorResult)
    assert isinstance(second, CandidateOperatorResult)
    assert first.attempt_id == second.attempt_id


def test_deterministic_candidate_digest() -> None:
    first = _build()
    second = _build()
    assert isinstance(first, CandidateOperatorResult)
    assert isinstance(second, CandidateOperatorResult)
    assert first.candidate_digest == second.candidate_digest


def test_explanation_does_not_affect_canonical_ids() -> None:
    first = _build(explanation="hello")
    second = _build(explanation="world")
    assert isinstance(first, CandidateOperatorResult)
    assert isinstance(second, CandidateOperatorResult)
    assert first.operator_result_id == second.operator_result_id
    assert first.attempt_id == second.attempt_id
    assert first.candidate_digest == second.candidate_digest


def test_evidence_span_order_preserved() -> None:
    spans = (_span("A"), _span("B"), _span("C"))
    residual = _residual(evidence_spans=spans)
    gate = _gate(residual)
    budget = _budget(gate)
    run = _run(residual=residual, gate=gate, budget=budget)
    cue = _cue(evidence_spans=spans)
    outcome = _build(residual=residual, search_gate=gate, compute_budget=budget, run=run, grounded_quantity_entity_cues=(cue,))
    assert isinstance(outcome, CandidateOperatorResult)
    assert outcome.evidence_spans == spans
    assert outcome.candidate_attempt.evidence_spans == spans


def test_duplicate_evidence_spans_preserved() -> None:
    spans = (_span("A"), _span("A"))
    residual = _residual(evidence_spans=spans)
    gate = _gate(residual)
    budget = _budget(gate)
    run = _run(residual=residual, gate=gate, budget=budget)
    cue = _cue(evidence_spans=spans)
    outcome = _build(residual=residual, search_gate=gate, compute_budget=budget, run=run, grounded_quantity_entity_cues=(cue,))
    assert isinstance(outcome, CandidateOperatorResult)
    assert outcome.evidence_spans == spans


def test_run_candidate_attempts_unchanged() -> None:
    residual, gate, budget, run, cue = _chain()
    run_attempts_before = tuple(run.candidate_attempts)
    _build(residual=residual, search_gate=gate, compute_budget=budget, run=run, grounded_quantity_entity_cues=(cue,))
    assert run.candidate_attempts == run_attempts_before


def test_spine_compatibility() -> None:
    residual, gate, budget, run, cue = _chain()
    outcome = build_quantity_entity_binding_candidate(
        residual=residual,
        search_gate=gate,
        compute_budget=budget,
        run=run,
        problem_frame_digest=run.problem_frame_digest,
        original_contract_assessment_id=run.contract_assessment_id,
        grounded_quantity_entity_cues=(cue,),
    )
    assert isinstance(outcome, CandidateOperatorResult)
    bound_attempt = bind_candidate_attempt_to_run(original_run=run, candidate_operator_result=outcome)
    adapter_input = build_replay_adapter_input_from_binding(
        run=run,
        binding=bound_attempt,
        candidate_operator_result=outcome,
    )
    assert isinstance(adapter_input, ReplayAdapterInput)
    assert adapter_input.candidate_organ == "quantity_entity_binding"
    assert adapter_input.contract_replay_target == "problem_frame_contracts.quantity_entity"


# Refusal tests
def test_wrong_residual_kind() -> None:
    residual = _residual(residual_kind=ResidualKind.MISSING_ROLE)
    gate = _gate(residual, reason_code="eligible_missing_relation")
    budget = _budget(gate, reason_code="budget_allowed_missing_relation")
    run = _run(residual=residual, gate=gate, budget=budget)
    outcome = build_quantity_entity_binding_candidate(
        residual=residual,
        search_gate=gate,
        compute_budget=budget,
        run=run,
        problem_frame_digest=run.problem_frame_digest,
        original_contract_assessment_id=run.contract_assessment_id,
        grounded_quantity_entity_cues=(_cue(evidence_spans=residual.evidence_spans),),
    )
    assert isinstance(outcome, CandidateOperatorRefusal)
    assert CandidateOperatorRefusalReason.UNSUPPORTED_RESIDUAL_KIND.value in outcome.reason_codes


def test_wrong_residual_code() -> None:
    residual = _residual(residual_code="some_other_code")
    gate = _gate(residual)
    budget = _budget(gate)
    run = _run(residual=residual, gate=gate, budget=budget)
    outcome = build_quantity_entity_binding_candidate(
        residual=residual,
        search_gate=gate,
        compute_budget=budget,
        run=run,
        problem_frame_digest=run.problem_frame_digest,
        original_contract_assessment_id=run.contract_assessment_id,
        grounded_quantity_entity_cues=(_cue(evidence_spans=residual.evidence_spans),),
    )
    assert isinstance(outcome, CandidateOperatorRefusal)
    assert CandidateOperatorRefusalReason.UNSUPPORTED_RESIDUAL_CODE.value in outcome.reason_codes


def test_unsupported_candidate_organ() -> None:
    residual = _residual(candidate_organ="some_other_organ")
    gate = _gate(residual)
    budget = _budget(gate)
    run = _run(residual=residual, gate=gate, budget=budget)
    outcome = build_quantity_entity_binding_candidate(
        residual=residual,
        search_gate=gate,
        compute_budget=budget,
        run=run,
        problem_frame_digest=run.problem_frame_digest,
        original_contract_assessment_id=run.contract_assessment_id,
        grounded_quantity_entity_cues=(_cue(evidence_spans=residual.evidence_spans),),
    )
    assert isinstance(outcome, CandidateOperatorRefusal)
    assert CandidateOperatorRefusalReason.UNSUPPORTED_CANDIDATE_ORGAN.value in outcome.reason_codes


def test_missing_evidence_spans() -> None:
    cue = GroundedQuantityEntityCue(
        quantity_mention_id="q1",
        entity_mention_id="e1",
        quantity_kind="count",
        evidence_spans=(),
    )
    outcome = _build(grounded_quantity_entity_cues=(cue,))
    assert isinstance(outcome, CandidateOperatorRefusal)
    assert CandidateOperatorRefusalReason.MISSING_EVIDENCE_SPANS.value in outcome.reason_codes


def test_malformed_evidence_spans() -> None:
    bad_span = SimpleNamespace(text="bad", start=-1, end=3, sentence_index=0)
    cue = GroundedQuantityEntityCue(
        quantity_mention_id="q1",
        entity_mention_id="e1",
        quantity_kind="count",
        evidence_spans=(bad_span,),  # type: ignore[arg-type]
    )
    outcome = _build(grounded_quantity_entity_cues=(cue,))
    assert isinstance(outcome, CandidateOperatorRefusal)
    assert CandidateOperatorRefusalReason.MALFORMED_EVIDENCE_SPAN.value in outcome.reason_codes


def test_ungrounded_quantity_cue() -> None:
    outcome = _build(grounded_quantity_entity_cues=("not a cue",))
    assert isinstance(outcome, CandidateOperatorRefusal)
    assert CandidateOperatorRefusalReason.INVALID_QUANTITY_ENTITY_CUE_TYPE.value in outcome.reason_codes


def test_zero_cues() -> None:
    outcome = _build(grounded_quantity_entity_cues=())
    assert isinstance(outcome, CandidateOperatorRefusal)
    assert CandidateOperatorRefusalReason.MISSING_TYPED_CUE.value in outcome.reason_codes


def test_multiple_cues() -> None:
    cue1 = _cue()
    cue2 = _cue()
    outcome = _build(grounded_quantity_entity_cues=(cue1, cue2))
    assert isinstance(outcome, CandidateOperatorRefusal)
    assert CandidateOperatorRefusalReason.QUANTITY_ENTITY_CUE_COUNT_MISMATCH.value in outcome.reason_codes


def test_empty_quantity_mention_id() -> None:
    outcome = _build(grounded_quantity_entity_cues=(_cue(quantity_mention_id=""),))
    assert isinstance(outcome, CandidateOperatorRefusal)
    assert CandidateOperatorRefusalReason.EMPTY_QUANTITY_MENTION_ID.value in outcome.reason_codes


def test_empty_entity_mention_id() -> None:
    outcome = _build(grounded_quantity_entity_cues=(_cue(entity_mention_id=""),))
    assert isinstance(outcome, CandidateOperatorRefusal)
    assert CandidateOperatorRefusalReason.EMPTY_ENTITY_MENTION_ID.value in outcome.reason_codes


def test_empty_quantity_kind() -> None:
    outcome = _build(grounded_quantity_entity_cues=(_cue(quantity_kind=""),))
    assert isinstance(outcome, CandidateOperatorRefusal)
    assert CandidateOperatorRefusalReason.EMPTY_QUANTITY_KIND.value in outcome.reason_codes


def test_empty_unit_mention_id() -> None:
    outcome = _build(grounded_quantity_entity_cues=(_cue(unit_mention_id=""),))
    assert isinstance(outcome, CandidateOperatorRefusal)
    assert CandidateOperatorRefusalReason.EMPTY_UNIT_MENTION_ID.value in outcome.reason_codes


def test_state_change_surface_backdoor() -> None:
    residual = _residual(candidate_organ="unary_delta_transition")
    gate = _gate(residual)
    budget = _budget(gate)
    run = _run(residual=residual, gate=gate, budget=budget)
    outcome = build_quantity_entity_binding_candidate(
        residual=residual,
        search_gate=gate,
        compute_budget=budget,
        run=run,
        problem_frame_digest=run.problem_frame_digest,
        original_contract_assessment_id=run.contract_assessment_id,
        grounded_quantity_entity_cues=(_cue(evidence_spans=residual.evidence_spans),),
    )
    assert isinstance(outcome, CandidateOperatorRefusal)
    assert CandidateOperatorRefusalReason.UNSUPPORTED_CANDIDATE_ORGAN.value in outcome.reason_codes


def test_attempt_index_not_zero() -> None:
    outcome = _build(attempt_index=1)
    assert isinstance(outcome, CandidateOperatorRefusal)
    assert CandidateOperatorRefusalReason.ATTEMPT_INDEX_EXCEEDS_BUDGET.value in outcome.reason_codes


def test_residual_id_not_in_run() -> None:
    residual = _residual()
    gate = _gate(residual)
    budget = _budget(gate)
    run = _run(residual=residual, gate=gate, budget=budget)
    other_residual = _residual(residual_id="other", evidence_spans=residual.evidence_spans)
    outcome = build_quantity_entity_binding_candidate(
        residual=other_residual,
        search_gate=gate,
        compute_budget=budget,
        run=run,
        problem_frame_digest=run.problem_frame_digest,
        original_contract_assessment_id=run.contract_assessment_id,
        grounded_quantity_entity_cues=(_cue(evidence_spans=residual.evidence_spans),),
    )
    assert isinstance(outcome, CandidateOperatorRefusal)
    assert CandidateOperatorRefusalReason.INVALID_OPERATOR_INPUT.value in outcome.reason_codes


def test_problem_frame_mismatch() -> None:
    outcome = _build(problem_frame_digest="wrong" * 8)
    assert isinstance(outcome, CandidateOperatorRefusal)
    assert CandidateOperatorRefusalReason.INVALID_OPERATOR_INPUT.value in outcome.reason_codes


def test_contract_assessment_mismatch() -> None:
    outcome = _build(original_contract_assessment_id="wrong_assessment")
    assert isinstance(outcome, CandidateOperatorRefusal)
    assert CandidateOperatorRefusalReason.INVALID_OPERATOR_INPUT.value in outcome.reason_codes


def test_search_gate_not_eligible() -> None:
    residual, valid_gate, valid_budget, run, cue = _chain()
    gate = _gate(residual, status=SearchGateStatus.INELIGIBLE)
    outcome = build_quantity_entity_binding_candidate(
        residual=residual,
        search_gate=gate,
        compute_budget=valid_budget,
        run=run,
        problem_frame_digest=run.problem_frame_digest,
        original_contract_assessment_id=run.contract_assessment_id,
        grounded_quantity_entity_cues=(_cue(evidence_spans=residual.evidence_spans),),
    )
    assert isinstance(outcome, CandidateOperatorRefusal)
    assert CandidateOperatorRefusalReason.INELIGIBLE_SEARCH_GATE.value in outcome.reason_codes


def test_compute_budget_not_allowed() -> None:
    residual, gate, valid_budget, run, cue = _chain()
    budget = _budget(gate, status=ComputeBudgetStatus.BUDGET_BLOCKED)
    outcome = build_quantity_entity_binding_candidate(
        residual=residual,
        search_gate=gate,
        compute_budget=budget,
        run=run,
        problem_frame_digest=run.problem_frame_digest,
        original_contract_assessment_id=run.contract_assessment_id,
        grounded_quantity_entity_cues=(_cue(evidence_spans=residual.evidence_spans),),
    )
    assert isinstance(outcome, CandidateOperatorRefusal)
    assert CandidateOperatorRefusalReason.NON_ALLOWED_BUDGET.value in outcome.reason_codes
