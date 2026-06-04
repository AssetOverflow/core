from __future__ import annotations

import json
from pathlib import Path
import pytest

from tests.workbench_test_helper import setup_isolated_workbench, make_and_write_proposal


def test_workbench_ratify_partition_enforcement(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    api = setup_isolated_workbench(tmp_path, monkeypatch)
    
    # Create a proposal with domain="math" initially (so build_proposal succeeds)
    proposal = make_and_write_proposal(
        api,
        domain="math",
        proposed_change_kind="vocabulary_addition",
        evidence_surface="testlemma",
        evidence_sub_type="lexical",
        missing_operator="drain_token",
        refusal_reason="unknown_word",
    )
    
    # Overwrite the domain key directly on disk to "cognition" to test partition isolation
    import workbench.readers as readers
    path = readers.MATH_PROPOSALS_JSONL
    lines = path.read_text(encoding="utf-8").splitlines()
    modified_lines = []
    for line in lines:
        if line.strip():
            record = json.loads(line)
            if record["proposal_id"] == proposal.proposal_id:
                record["domain"] = "cognition"
            modified_lines.append(json.dumps(record, ensure_ascii=False, separators=(",", ":")))
    path.write_text("\n".join(modified_lines) + "\n", encoding="utf-8")

    
    # Try to ratify it via the math API
    body = json.dumps({"category": "drain_token"}).encode("utf-8")
    response = api.handle("POST", f"/math-proposals/{proposal.proposal_id}/ratify", body)
    
    # Should be rejected with 400 Bad Request
    assert response.status == 400
    assert response.payload["ok"] is False
    assert "partition" in response.payload["error"]["message"].lower()
