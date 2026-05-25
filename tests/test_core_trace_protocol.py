from __future__ import annotations

import math

import pytest

from core.protocol import (
    CtpEpistemic,
    CtpInvariant,
    CtpPayload,
    JsonlEventReader,
    JsonlEventSink,
    ReplayViolation,
    canonical_bytes,
    canonical_hash,
    evidence_observed,
    invariant_checked,
    turn_completed,
    turn_requested,
    verify_chain,
)
from core.protocol.canonical import CanonicalizationError
from core.protocol.envelope import CtpEnvelope
from core.protocol.types import CtpActor, CtpProof


def test_canonical_hash_is_order_insensitive_and_rejects_nan():
    a = {"b": 2, "a": [1, -0.0]}
    b = {"a": [1, 0.0], "b": 2}
    assert canonical_bytes(a) == canonical_bytes(b)
    assert canonical_hash(a) == canonical_hash(b)
    with pytest.raises(CanonicalizationError):
        canonical_bytes({"bad": math.nan})
    with pytest.raises(CanonicalizationError):
        canonical_bytes({"bad": math.inf})


def test_message_id_is_content_addressed_and_payload_changes_change_it():
    first = turn_requested("What is alpha?", correlation_id="turn-1", sequence=0)
    same = turn_requested("What is alpha?", correlation_id="turn-1", sequence=0)
    changed = turn_requested("What is beta?", correlation_id="turn-1", sequence=0)
    assert first.message_id == same.message_id
    assert first.message_id != changed.message_id


def test_completed_turn_requires_epistemic_and_trace_hash():
    bad = CtpEnvelope(
        ctp_version="0.1",
        message_type="core.turn.completed.v1",
        kind="event",
        actor=CtpActor(kind="test", id="test"),
        payload=CtpPayload(encoding="json.v1", schema="x", body={}),
    )
    with pytest.raises(ValueError, match="requires epistemic"):
        bad.validate()

    epistemic = CtpEpistemic(
        state="GROUNDED",
        grounding_source="pack",
        normative_clearance="CLEARED",
    )
    bad_trace = CtpEnvelope(
        ctp_version="0.1",
        message_type="core.turn.completed.v1",
        kind="event",
        actor=CtpActor(kind="test", id="test"),
        payload=CtpPayload(encoding="json.v1", schema="x", body={}),
        epistemic=epistemic,
    )
    with pytest.raises(ValueError, match="requires proof.trace_hash"):
        bad_trace.validate()


def test_jsonl_round_trip_and_replay_chain(tmp_path):
    start = turn_requested("What does alpha cause?", correlation_id="turn-2", sequence=0)
    epistemic = CtpEpistemic(
        state="GROUNDED",
        grounding_source="pack",
        normative_clearance="CLEARED",
    )
    done = turn_completed(
        surface="alpha causes beta.",
        trace_hash="sha256:trace",
        epistemic=epistemic,
        causation_id=start.message_id,
        correlation_id="turn-2",
        sequence=1,
        proof=CtpProof(
            replay_digest="sha256:replay",
            versor_condition=0.0,
            invariants=(CtpInvariant(name="versor_condition", status="passed", value=0.0, threshold=1e-6),),
        ),
    )
    path = tmp_path / "events.jsonl"
    sink = JsonlEventSink(path)
    sink.append(start)
    sink.append(done)

    loaded = list(JsonlEventReader(path))
    assert [e.message_id for e in loaded] == [start.message_id, done.message_id]
    verify_chain(loaded)


def test_replay_chain_detects_causation_break():
    first = evidence_observed("fixture", "1", correlation_id="turn-3", sequence=0)
    second = invariant_checked(
        CtpInvariant(name="x", status="passed"),
        correlation_id="turn-3",
        sequence=1,
    )
    broken = second.with_computed_message_id()
    broken = CtpEnvelope(
        ctp_version=broken.ctp_version,
        message_type=broken.message_type,
        kind=broken.kind,
        actor=broken.actor,
        payload=broken.payload,
        causation_id="sha256:not-the-first-id",
        correlation_id=broken.correlation_id,
        sequence=broken.sequence,
        state=broken.state,
        epistemic=broken.epistemic,
        proof=broken.proof,
    ).with_computed_message_id()
    with pytest.raises(ReplayViolation, match="causation break"):
        verify_chain([first, broken])
