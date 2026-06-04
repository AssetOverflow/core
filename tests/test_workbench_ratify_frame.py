from __future__ import annotations

import json
import getpass
from pathlib import Path
import pytest

from teaching.math_frame_ratification import apply_frame_claim
from tests.workbench_test_helper import setup_isolated_workbench, make_and_write_proposal


def test_workbench_ratify_frame_byte_equivalence(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    api = setup_isolated_workbench(tmp_path, monkeypatch)
    pack_root = tmp_path / "en_core_math_v1"
    target_file = pack_root / "frames" / "transfer_frame.jsonl"
    
    # Write a clean target file
    target_file.write_text("", encoding="utf-8")
    
    # Generate proposal
    proposal = make_and_write_proposal(
        api,
        proposed_change_kind="frame_reclassification",
        evidence_surface="gives",
        evidence_sub_type="frame",
        missing_operator="transfer_frame",
        refusal_reason="unexpected_category",
    )
    
    # 1. UI Ratify
    body = json.dumps({"category": "transfer_frame", "polarity": "affirms"}).encode("utf-8")
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
    apply_frame_claim(
        claim=claim,
        frame_category="transfer_frame",
        polarity="affirms",
        reviewer=getpass.getuser(),
        pack_root=pack_root,
        ratifier_kind="cli",
    )
    
    cli_lines = target_file.read_bytes().splitlines()
    assert len(cli_lines) == 1
    
    # 3. Assert byte equivalence except for ratifier_kind
    ui_line = ui_lines[0].decode("utf-8")
    cli_line = cli_lines[0].decode("utf-8")
    
    assert ui_line.replace('"ratifier_kind": "workbench"', '"ratifier_kind": "cli"').replace('"ratifier_kind":"workbench"', '"ratifier_kind":"cli"') == cli_line

