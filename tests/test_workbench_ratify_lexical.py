from __future__ import annotations

import json
import getpass
from pathlib import Path
import pytest

from teaching.math_lexical_ratification import apply_lexical_claim
from tests.workbench_test_helper import setup_isolated_workbench, make_and_write_proposal


def test_workbench_ratify_lexical_byte_equivalence(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    api = setup_isolated_workbench(tmp_path, monkeypatch)
    pack_root = tmp_path / "en_core_math_v1"
    target_file = pack_root / "lexicon" / "drain_token.jsonl"
    
    # Write a clean target file
    target_file.write_text("", encoding="utf-8")
    
    # Generate proposal
    proposal = make_and_write_proposal(
        api,
        proposed_change_kind="vocabulary_addition",
        evidence_surface="testlemma",
        evidence_sub_type="lexical",
        missing_operator="drain_token",
        refusal_reason="unknown_word",
    )
    
    # 1. UI Ratify
    body = json.dumps({"category": "drain_token"}).encode("utf-8")
    response = api.handle("POST", f"/math-proposals/{proposal.proposal_id}/ratify", body)
    
    assert response.status == 200
    assert response.payload["ok"] is True
    assert response.payload["data"]["applied"] is True
    
    ui_lines = target_file.read_bytes().splitlines()
    assert len(ui_lines) == 1
    
    # Clear target file
    target_file.write_text("", encoding="utf-8")
    
    # 2. CLI Ratify
    claim = proposal.evidence_pointers[0]
    apply_lexical_claim(
        claim=claim,
        category="drain_token",
        reviewer=getpass.getuser(),
        pack_root=pack_root,
        ratifier_kind="cli",
    )
    
    cli_lines = target_file.read_bytes().splitlines()
    assert len(cli_lines) == 1
    
    # 3. Assert byte equivalence except for ratifier_kind
    ui_line = ui_lines[0].decode("utf-8")
    cli_line = cli_lines[0].decode("utf-8")
    
    # Replacing ratifier_kind="workbench" with "cli" in the UI-serialized line should make it identical to the CLI-serialized line.
    assert ui_line.replace('"ratifier_kind": "workbench"', '"ratifier_kind": "cli"').replace('"ratifier_kind":"workbench"', '"ratifier_kind":"cli"') == cli_line

