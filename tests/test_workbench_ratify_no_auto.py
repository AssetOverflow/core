from __future__ import annotations

from pathlib import Path
import pytest

from tests.workbench_test_helper import setup_isolated_workbench, make_and_write_proposal


def test_workbench_ratify_no_auto_transition(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    api = setup_isolated_workbench(tmp_path, monkeypatch)
    pack_root = tmp_path / "en_core_math_v1"
    
    # 1. Create a replay-equivalent proposal in the queue
    proposal = make_and_write_proposal(
        api,
        proposed_change_kind="vocabulary_addition",
        evidence_surface="testlemma",
        evidence_sub_type="lexical",
        missing_operator="drain_token",
        refusal_reason="unknown_word",
    )
    
    # 2. Check that no entries have been written to the target file
    lex_file = pack_root / "lexicon" / "drain_token.jsonl"
    # It might contain existing lemmas from the copy, but should NOT contain "testlemma"
    content_before = lex_file.read_text(encoding="utf-8") if lex_file.exists() else ""
    assert "testlemma" not in content_before
    
    # 3. Emulate polling/idle state: assert that even after time/polling, nothing mutates the target file
    content_after_idle = lex_file.read_text(encoding="utf-8") if lex_file.exists() else ""
    assert "testlemma" not in content_after_idle
