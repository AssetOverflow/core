from __future__ import annotations

import json
from pathlib import Path
import pytest

from tests.workbench_test_helper import setup_isolated_workbench, make_and_write_proposal


def test_workbench_ratify_idempotent_raises_already_ratified(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    api = setup_isolated_workbench(tmp_path, monkeypatch)
    
    # Generate proposal
    proposal = make_and_write_proposal(
        api,
        proposed_change_kind="vocabulary_addition",
        evidence_surface="testlemma",
        evidence_sub_type="lexical",
        missing_operator="drain_token",
        refusal_reason="unknown_word",
    )
    body = json.dumps({"category": "drain_token"}).encode("utf-8")
    
    # First ratification succeeds
    response1 = api.handle("POST", f"/math-proposals/{proposal.proposal_id}/ratify", body)
    assert response1.status == 200
    assert response1.payload["data"]["applied"] is True
    
    # Second ratification fails with 409 Conflict (AlreadyRatified)
    response2 = api.handle("POST", f"/math-proposals/{proposal.proposal_id}/ratify", body)
    assert response2.status == 409
    assert response2.payload["ok"] is False
    assert "already ratified" in response2.payload["error"]["message"].lower()
