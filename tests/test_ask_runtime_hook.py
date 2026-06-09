"""Tests for the default-dark ASK runtime fallback hook."""

from unittest.mock import Mock

from chat.runtime import _maybe_apply_served_ask
from core.config import RuntimeConfig
from generate.contemplation.pass_manager import ContemplationResult
from generate.contemplation.findings import Terminal


def test_runtime_hook_gate_disabled_returns_fallback():
    """Gate disabled: runtime helper returns original fallback surface and does not call provider."""
    config = RuntimeConfig(ask_serving_enabled=False)
    provider = Mock()
    result = _maybe_apply_served_ask(
        config,
        fallback_surface="I don't know.",
        provider=provider,
    )
    assert result == "I don't know."
    provider.assert_not_called()


def test_runtime_hook_gate_enabled_valid_artifact(tmp_path):
    """Gate enabled + valid question artifact: runtime helper returns artifact question text."""
    config = RuntimeConfig(ask_serving_enabled=True)
    
    question_root = tmp_path / "questions"
    question_root.mkdir()
    qfile = question_root / "q.json"
    qfile.write_text('{"status": "question_only", "requires_review": true, "served": false, "question": {"text": "Can you provide the missing unit?", "slot_name": "unit"}}')
    
    candidate = ContemplationResult(
        terminal=Terminal.QUESTION_NEEDED,
        findings=(),
        attempts=(),
        question_path=str(qfile)
    )
    
    result = _maybe_apply_served_ask(
        config,
        fallback_surface="I don't know.",
        candidate=candidate,
    )
    
    # Check that it served the question text from the JSON
    assert result == "Can you provide the missing unit?"


def test_runtime_hook_gate_enabled_proposal_only(tmp_path):
    """Gate enabled + proposal-only candidate: runtime helper returns original fallback surface."""
    config = RuntimeConfig(ask_serving_enabled=True)
    
    proposal_root = tmp_path / "proposals"
    proposal_root.mkdir()
    pfile = proposal_root / "prop.json"
    pfile.write_text('{}')
    
    candidate = ContemplationResult(
        terminal=Terminal.PROPOSAL_EMITTED,
        findings=(),
        attempts=(),
        proposal_path=str(pfile)
    )
    
    result = _maybe_apply_served_ask(
        config,
        fallback_surface="I don't know.",
        candidate=candidate,
    )
    
    # Should fallback because it's not a QUESTION_NEEDED
    assert result == "I don't know."


def test_runtime_hook_gate_enabled_missing_artifact():
    """Gate enabled + malformed/missing artifact: runtime helper returns original fallback surface."""
    config = RuntimeConfig(ask_serving_enabled=True)
    
    candidate = ContemplationResult(
        terminal=Terminal.QUESTION_NEEDED,
        findings=(),
        attempts=(),
        question_path="nonexistent.json"
    )
    
    result = _maybe_apply_served_ask(
        config,
        fallback_surface="I don't know.",
        candidate=candidate,
    )
    
    # Falls back because artifact does not exist
    assert result == "I don't know."
