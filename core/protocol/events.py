from __future__ import annotations

from typing import Any

from .envelope import CtpEnvelope
from .types import CtpActor, CtpEpistemic, CtpInvariant, CtpPayload, CtpProof, CtpStateRef

_DEFAULT_ACTOR = CtpActor(kind="core_runtime", id="core.protocol", authority="system")


def _env(
    *,
    message_type: str,
    kind: str,
    payload_schema: str,
    payload_body: dict[str, Any],
    actor: CtpActor = _DEFAULT_ACTOR,
    causation_id: str = "",
    correlation_id: str = "",
    sequence: int = 0,
    state: CtpStateRef | None = None,
    epistemic: CtpEpistemic | None = None,
    proof: CtpProof | None = None,
) -> CtpEnvelope:
    event = CtpEnvelope(
        ctp_version="0.1",
        message_type=message_type,
        kind=kind,
        actor=actor,
        causation_id=causation_id,
        correlation_id=correlation_id,
        sequence=sequence,
        state=state or CtpStateRef(),
        epistemic=epistemic,
        proof=proof or CtpProof(),
        payload=CtpPayload(
            encoding="json.v1",
            schema=payload_schema,
            body=payload_body,
        ),
    ).with_computed_message_id()
    event.validate()
    return event


def turn_requested(input_text: str, *, correlation_id: str, sequence: int = 0) -> CtpEnvelope:
    return _env(
        message_type="core.turn.requested.v1",
        kind="command",
        payload_schema="core.turn.requested.payload.v1",
        payload_body={"input_text": input_text},
        correlation_id=correlation_id,
        sequence=sequence,
    )


def turn_completed(
    *,
    surface: str,
    trace_hash: str,
    epistemic: CtpEpistemic,
    causation_id: str,
    correlation_id: str,
    sequence: int,
    state: CtpStateRef | None = None,
    proof: CtpProof | None = None,
) -> CtpEnvelope:
    p = proof or CtpProof()
    p = CtpProof(
        trace_hash=trace_hash,
        replay_digest=p.replay_digest,
        admissibility_trace_hash=p.admissibility_trace_hash,
        operator_invocation=p.operator_invocation,
        versor_condition=p.versor_condition,
        refusal_reason=p.refusal_reason,
        invariants=p.invariants,
    )
    return _env(
        message_type="core.turn.completed.v1",
        kind="event",
        payload_schema="core.turn.completed.payload.v1",
        payload_body={"surface": surface},
        causation_id=causation_id,
        correlation_id=correlation_id,
        sequence=sequence,
        state=state,
        epistemic=epistemic,
        proof=p,
    )


def turn_refused(
    *,
    refusal_reason: str,
    trace_hash: str,
    epistemic: CtpEpistemic,
    causation_id: str,
    correlation_id: str,
    sequence: int,
) -> CtpEnvelope:
    return _env(
        message_type="core.turn.refused.v1",
        kind="event",
        payload_schema="core.turn.refused.payload.v1",
        payload_body={"refusal_reason": refusal_reason},
        causation_id=causation_id,
        correlation_id=correlation_id,
        sequence=sequence,
        epistemic=epistemic,
        proof=CtpProof(trace_hash=trace_hash, refusal_reason=refusal_reason),
    )


def evidence_observed(source: str, ref: str, *, correlation_id: str, sequence: int) -> CtpEnvelope:
    return _env(
        message_type="core.evidence.observed.v1",
        kind="observation",
        payload_schema="core.evidence.observed.payload.v1",
        payload_body={"source": source, "ref": ref},
        correlation_id=correlation_id,
        sequence=sequence,
    )


def tool_invocation_requested(tool_name: str, args_hash: str, *, correlation_id: str, sequence: int) -> CtpEnvelope:
    return _env(
        message_type="core.tool.invocation.requested.v1",
        kind="command",
        payload_schema="core.tool.invocation.requested.payload.v1",
        payload_body={"tool_name": tool_name, "args_hash": args_hash},
        correlation_id=correlation_id,
        sequence=sequence,
    )


def tool_invocation_completed(tool_name: str, result_hash: str, *, causation_id: str, correlation_id: str, sequence: int) -> CtpEnvelope:
    return _env(
        message_type="core.tool.invocation.completed.v1",
        kind="event",
        payload_schema="core.tool.invocation.completed.payload.v1",
        payload_body={"tool_name": tool_name, "result_hash": result_hash},
        causation_id=causation_id,
        correlation_id=correlation_id,
        sequence=sequence,
    )


def learning_proposal_created(proposal_id: str, *, correlation_id: str, sequence: int) -> CtpEnvelope:
    return _env(
        message_type="core.learning.proposal.created.v1",
        kind="proposal",
        payload_schema="core.learning.proposal.created.payload.v1",
        payload_body={"proposal_id": proposal_id},
        correlation_id=correlation_id,
        sequence=sequence,
    )


def verdict_assigned(subject_message_id: str, verdict: str, *, correlation_id: str, sequence: int) -> CtpEnvelope:
    return _env(
        message_type="core.verdict.assigned.v1",
        kind="verdict",
        payload_schema="core.verdict.assigned.payload.v1",
        payload_body={"subject_message_id": subject_message_id, "verdict": verdict},
        correlation_id=correlation_id,
        sequence=sequence,
    )


def invariant_checked(invariant: CtpInvariant, *, correlation_id: str, sequence: int) -> CtpEnvelope:
    return _env(
        message_type="core.proof.invariant.checked.v1",
        kind="proof",
        payload_schema="core.proof.invariant.checked.payload.v1",
        payload_body={"invariant": invariant},
        correlation_id=correlation_id,
        sequence=sequence,
    )
