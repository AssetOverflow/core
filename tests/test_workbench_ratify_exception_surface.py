from __future__ import annotations

import json
from pathlib import Path
import pytest

from tests.workbench_test_helper import setup_isolated_workbench, make_and_write_proposal


def test_workbench_ratify_exception_surface_verbatim(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    api = setup_isolated_workbench(tmp_path, monkeypatch)
    
    # 1. Trigger WrongClaimSubType: Lexical proposal but frame sub_type
    proposal_lex = make_and_write_proposal(
        api,
        proposed_change_kind="vocabulary_addition",
        evidence_surface="testlemma",
        evidence_sub_type="frame",  # wrong sub_type for LexicalClaim
        missing_operator="drain_token",
        refusal_reason="unknown_word",
    )
    body = json.dumps({"category": "drain_token"}).encode("utf-8")
    response_sub = api.handle("POST", f"/math-proposals/{proposal_lex.proposal_id}/ratify", body)
    
    assert response_sub.status == 400
    assert response_sub.payload["ok"] is False
    # Verbatim error message from WrongClaimSubType
    assert "Lexical ratification requires sub_type='lexical'" in response_sub.payload["error"]["message"]

    # 2. Trigger WrongCompositionCategory
    proposal_comp = make_and_write_proposal(
        api,
        proposed_change_kind="composition_reclassification",
        evidence_surface="each",
        evidence_sub_type="composition",
        missing_operator="quantity_extraction",
        refusal_reason="incomplete_operation",
    )
    body_bad_comp = json.dumps({"category": "distributive_composition", "polarity": "affirms"}).encode("utf-8")
    response_comp = api.handle("POST", f"/math-proposals/{proposal_comp.proposal_id}/ratify", body_bad_comp)
    
    assert response_comp.status == 400
    assert response_comp.payload["ok"] is False
    assert "CompositionClaim ratification is allowlist-only" in response_comp.payload["error"]["message"]
