from __future__ import annotations

import json
from pathlib import Path
import pytest

from tests.workbench_test_helper import setup_isolated_workbench, make_and_write_proposal


def test_workbench_ratify_category_allowlist_enforcement(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    api = setup_isolated_workbench(tmp_path, monkeypatch)
    pack_root = tmp_path / "en_core_math_v1"
    
    # 1. Test missing category
    proposal_lex = make_and_write_proposal(
        api,
        proposed_change_kind="vocabulary_addition",
        evidence_surface="testlemma",
        evidence_sub_type="lexical",
    )
    
    # Sending POST with empty body should be dry-run (returns 200, applied=False)
    response_dry = api.handle("POST", f"/math-proposals/{proposal_lex.proposal_id}/ratify", b"")
    assert response_dry.status == 200
    assert response_dry.payload["data"]["applied"] is False

    # Sending invalid/empty category in body should raise 400
    body_empty = json.dumps({"category": ""}).encode("utf-8")
    response_empty = api.handle("POST", f"/math-proposals/{proposal_lex.proposal_id}/ratify", body_empty)
    assert response_empty.status == 400
    assert response_empty.payload["ok"] is False

    bad_file = pack_root / "lexicon" / "accumulation_verb.jsonl"
    before_content = bad_file.read_bytes() if bad_file.exists() else b""

    # 2. Test off-allowlist category
    body_bad = json.dumps({"category": "accumulation_verb"}).encode("utf-8")  # Lexical safe list is only drain_token
    response_bad = api.handle("POST", f"/math-proposals/{proposal_lex.proposal_id}/ratify", body_bad)
    
    assert response_bad.status == 400
    assert response_bad.payload["ok"] is False
    assert "drain-class" in response_bad.payload["error"]["message"] or "restricted" in response_bad.payload["error"]["message"]
    
    # Verify nothing was written to accumulation_verb.jsonl
    after_content = bad_file.read_bytes() if bad_file.exists() else b""
    assert before_content == after_content
