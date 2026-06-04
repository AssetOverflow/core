from __future__ import annotations

import json
from pathlib import Path
import pytest

from chat.telemetry import JsonlBufferSink
from tests.workbench_test_helper import setup_isolated_workbench, make_and_write_proposal


def test_workbench_operator_telemetry_emission_and_redaction(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    api = setup_isolated_workbench(tmp_path, monkeypatch)
    sink = JsonlBufferSink()
    api.attach_telemetry_sink(sink)

    # Generate proposal
    proposal = make_and_write_proposal(
        api,
        proposed_change_kind="vocabulary_addition",
        evidence_surface="testlemma",
        evidence_sub_type="lexical",
        missing_operator="drain_token",
        refusal_reason="unknown_word",
    )
    
    # 1. Test operator_ratify success
    body = json.dumps({"category": "drain_token"}).encode("utf-8")
    response_ratify = api.handle("POST", f"/math-proposals/{proposal.proposal_id}/ratify", body)
    assert response_ratify.status == 200
    
    assert len(sink.lines) == 1
    event = json.loads(sink.lines[-1])
    assert event["event"] == "operator_ratify"
    assert event["proposal_id"] == proposal.proposal_id
    assert event["handler"] == "LexicalClaim"
    assert event["outcome"] == "applied"
    assert event["ratifier_kind"] == "workbench"
    # Ensure no evidence surface is leaked
    assert "testlemma" not in sink.lines[-1]
    
    # 2. Test operator_ratify failure (rejected_precondition)
    # Re-ratifying will fail (AlreadyRatified)
    api.handle("POST", f"/math-proposals/{proposal.proposal_id}/ratify", body)
    assert len(sink.lines) == 2
    event_fail = json.loads(sink.lines[-1])
    assert event_fail["event"] == "operator_ratify"
    assert event_fail["outcome"] == "rejected_precondition"
    assert "testlemma" not in sink.lines[-1]

    # 3. Test operator_reject
    body_reject = json.dumps({"note": "Spam proposal"}).encode("utf-8")
    response_reject = api.handle("POST", f"/math-proposals/{proposal.proposal_id}/reject", body_reject)
    assert response_reject.status == 200
    
    assert len(sink.lines) == 3
    event_reject = json.loads(sink.lines[-1])
    assert event_reject["event"] == "operator_reject"
    assert event_reject["note"] == "Spam proposal"
    assert event_reject["handler"] == "LexicalClaim"
    assert "testlemma" not in sink.lines[-1]

    # 4. Test operator_defer
    response_defer = api.handle("POST", f"/math-proposals/{proposal.proposal_id}/defer", b"")
    assert response_defer.status == 200
    
    assert len(sink.lines) == 4
    event_defer = json.loads(sink.lines[-1])
    assert event_defer["event"] == "operator_defer"
    assert event_defer["handler"] == "LexicalClaim"
    assert "testlemma" not in sink.lines[-1]
