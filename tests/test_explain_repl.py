"""Tests for W-013: explain_last_turn() wired into core chat REPL."""

from __future__ import annotations

from core.cognition.explain import explain_from_intent
from generate.intent import DialogueIntent, IntentTag


# ---------------------------------------------------------------------------
# explain_from_intent — unit tests (mirrors explain() dispatch)
# ---------------------------------------------------------------------------


def _intent(tag: IntentTag, subject: str = "truth") -> DialogueIntent:
    return DialogueIntent(tag=tag, subject=subject)


def test_explain_from_intent_none_returns_empty() -> None:
    assert explain_from_intent(None) == ""


def test_explain_from_intent_definition() -> None:
    result = explain_from_intent(_intent(IntentTag.DEFINITION, "wisdom"))
    assert result == "What is wisdom?"


def test_explain_from_intent_cause() -> None:
    result = explain_from_intent(_intent(IntentTag.CAUSE, "light reveals"))
    assert result == "Why light reveals?"


def test_explain_from_intent_procedure() -> None:
    result = explain_from_intent(_intent(IntentTag.PROCEDURE, "ground a claim"))
    assert result == "How do I ground a claim?"


def test_explain_from_intent_comparison() -> None:
    result = explain_from_intent(
        DialogueIntent(
            tag=IntentTag.COMPARISON,
            subject="knowledge",
            secondary_subject="wisdom",
        )
    )
    assert result == "Compare knowledge and wisdom."


def test_explain_from_intent_verification() -> None:
    result = explain_from_intent(_intent(IntentTag.VERIFICATION, "truth is coherent"))
    assert result == "Is truth is coherent?"


def test_explain_from_intent_recall() -> None:
    result = explain_from_intent(_intent(IntentTag.RECALL, "truth"))
    assert result == "Remember truth."


def test_explain_from_intent_correction_uses_correction_text() -> None:
    result = explain_from_intent(
        _intent(IntentTag.CORRECTION, "truth"),
        correction_text="Actually truth is coherent.",
    )
    assert result == "Actually truth is coherent."


def test_explain_from_intent_correction_falls_back_to_subject() -> None:
    result = explain_from_intent(_intent(IntentTag.CORRECTION, "truth"), correction_text="")
    assert "truth" in result


# ---------------------------------------------------------------------------
# ChatRuntime.explain_last_turn — integration test
# ---------------------------------------------------------------------------


def test_explain_last_turn_no_prior_turn_returns_empty() -> None:
    from chat.runtime import ChatRuntime
    runtime = ChatRuntime()
    assert runtime.explain_last_turn() == ""


def test_explain_last_turn_after_definition_turn() -> None:
    from chat.runtime import ChatRuntime
    runtime = ChatRuntime()
    runtime.chat("What is truth?")
    result = runtime.explain_last_turn()
    # Should produce a definition form ("What is <subject>?")
    assert result.startswith("What is ")
