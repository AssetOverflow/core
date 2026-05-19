"""Tests for the expository-DEFINITION classifier rules.

Pins:
* ``Explain X`` / ``Explain X.``                  → DEFINITION (subject=X)
* ``Write a paragraph about X``                   → DEFINITION (subject=X)
* ``Compose/draft a short paragraph about X``     → DEFINITION (subject=X)
* ``Paragraph about X``                           → DEFINITION (subject=X)

Orthogonality preservation:
* ``Tell me about X`` stays NARRATIVE.
* ``Describe X`` stays NARRATIVE.
* ``ResponseMode`` classification for the same prompts stays
  EXPLAIN / PARAGRAPH (independent axis).
"""

from __future__ import annotations

import pytest

from generate.intent import (
    DialogueIntent,
    IntentTag,
    ResponseMode,
    classify_intent,
    classify_response_mode,
)


class TestExplainDefinition:
    @pytest.mark.parametrize(
        "prompt,subject",
        [
            ("Explain truth.", "truth"),
            ("Explain truth", "truth"),
            ("explain memory", "memory"),
            ("Explain the parent.", "parent"),
            ("Explain a parent.", "parent"),
        ],
    )
    def test_explain_classifies_to_definition(
        self, prompt: str, subject: str
    ) -> None:
        result = classify_intent(prompt)
        assert result.tag is IntentTag.DEFINITION
        assert result.subject == subject

    def test_explain_response_mode_stays_explain(self) -> None:
        assert classify_response_mode("Explain truth.") is ResponseMode.EXPLAIN


class TestParagraphRequestDefinition:
    @pytest.mark.parametrize(
        "prompt,subject",
        [
            ("Write a paragraph about truth.", "truth"),
            ("Write a short paragraph about truth.", "truth"),
            ("Write a brief paragraph about memory.", "memory"),
            ("Compose a paragraph about light.", "light"),
            ("Draft a paragraph on knowledge.", "knowledge"),
            ("Paragraph about wisdom.", "wisdom"),
            ("Paragraph on understanding", "understanding"),
        ],
    )
    def test_paragraph_request_classifies_to_definition(
        self, prompt: str, subject: str
    ) -> None:
        result = classify_intent(prompt)
        assert result.tag is IntentTag.DEFINITION
        assert result.subject == subject

    def test_paragraph_request_response_mode_stays_paragraph(self) -> None:
        assert (
            classify_response_mode("Write a paragraph about truth.")
            is ResponseMode.PARAGRAPH
        )
        assert (
            classify_response_mode("Compose a paragraph about light.")
            is ResponseMode.PARAGRAPH
        )


class TestNarrativeRulesUntouched:
    @pytest.mark.parametrize(
        "prompt,subject",
        [
            ("Tell me about truth.", "truth"),
            ("Describe wisdom.", "wisdom"),
            ("Describe memory", "memory"),
        ],
    )
    def test_narrative_rules_still_win(
        self, prompt: str, subject: str
    ) -> None:
        result = classify_intent(prompt)
        assert result == DialogueIntent(
            tag=IntentTag.NARRATIVE, subject=subject
        )


class TestExampleRulesUntouched:
    def test_example_still_routes_correctly(self) -> None:
        result = classify_intent("Give me an example of truth.")
        assert result.tag is IntentTag.EXAMPLE
        assert result.subject == "truth"


class TestExistingDefinitionRulesUntouched:
    @pytest.mark.parametrize(
        "prompt,subject",
        [
            ("What is truth?", "truth"),
            ("Define memory.", "memory"),
        ],
    )
    def test_existing_definition_rules_unchanged(
        self, prompt: str, subject: str
    ) -> None:
        result = classify_intent(prompt)
        assert result.tag is IntentTag.DEFINITION
        assert result.subject == subject
