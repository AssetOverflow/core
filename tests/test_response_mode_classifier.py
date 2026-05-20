"""Tests for the ``ResponseMode`` classifier and its placement.

These tests pin two things:

* :class:`ResponseMode` lives in ``generate/intent.py`` and is
  re-exported by ``generate/discourse_planner.py`` (one-way dependency:
  the planner imports from intent, never the reverse).
* :func:`classify_response_mode` is deterministic, pure, and additive —
  it does not alter ``DialogueIntent`` or any branch of
  :func:`classify_intent`, so cognition-eval byte-identity is preserved
  (verified separately by running the eval; see commit message).

The classifier is sibling to ``classify_intent``: callers compose the
two outputs rather than threading mode through the intent classifier's
return value.  This keeps the change risk-free for the broad swath of
codepaths that already destructure ``DialogueIntent``.
"""

from __future__ import annotations

import inspect

import pytest

from generate.discourse_planner import ResponseMode as PlannerResponseMode
from generate.intent import (
    DialogueIntent,
    IntentTag,
    ResponseMode,
    classify_intent,
    classify_response_mode,
)


# ---------------------------------------------------------------------------
# Placement / re-export
# ---------------------------------------------------------------------------


class TestResponseModePlacement:
    def test_response_mode_is_canonical_in_intent_module(self) -> None:
        assert ResponseMode.__module__ == "generate.intent"

    def test_planner_reexports_same_class_object(self) -> None:
        assert PlannerResponseMode is ResponseMode

    def test_enum_membership_matches_contract(self) -> None:
        assert {m.value for m in ResponseMode} == {
            "brief",
            "explain",
            "walkthrough",
            "paragraph",
            "example",
        }


# ---------------------------------------------------------------------------
# Classifier behavior
# ---------------------------------------------------------------------------


class TestClassifyResponseMode:
    @pytest.mark.parametrize(
        "prompt,expected",
        [
            # PARAGRAPH
            ("Write a paragraph about truth", ResponseMode.PARAGRAPH),
            ("write a short paragraph on memory", ResponseMode.PARAGRAPH),
            ("Compose a brief paragraph about light.", ResponseMode.PARAGRAPH),
            ("Draft a paragraph about evidence", ResponseMode.PARAGRAPH),
            ("Paragraph about knowledge", ResponseMode.PARAGRAPH),
            ("Explain truth in a paragraph", ResponseMode.PARAGRAPH),
            # WALKTHROUGH
            ("Walk me through how truth grounds knowledge", ResponseMode.WALKTHROUGH),
            ("walk through the proof", ResponseMode.WALKTHROUGH),
            ("Explain it step by step", ResponseMode.WALKTHROUGH),
            ("Show the step-by-step derivation", ResponseMode.WALKTHROUGH),
            # EXAMPLE
            ("Give me an example of memory", ResponseMode.EXAMPLE),
            ("Show an instance of correction", ResponseMode.EXAMPLE),
            ("Example of evidence", ResponseMode.EXAMPLE),
            # EXPLAIN
            ("Explain truth", ResponseMode.EXPLAIN),
            ("Tell me about parent", ResponseMode.EXPLAIN),
            ("Tell me more about light", ResponseMode.EXPLAIN),
            ("Describe knowledge", ResponseMode.EXPLAIN),
            ("What do you know about memory", ResponseMode.EXPLAIN),
            ("What can you say about evidence", ResponseMode.EXPLAIN),
            # BRIEF (default)
            ("What is truth?", ResponseMode.BRIEF),
            ("Define memory", ResponseMode.BRIEF),
            ("Why does light reveal truth?", ResponseMode.BRIEF),
            ("Does memory require recall?", ResponseMode.BRIEF),
            ("", ResponseMode.BRIEF),
            ("   ", ResponseMode.BRIEF),
        ],
    )
    def test_classification(self, prompt: str, expected: ResponseMode) -> None:
        assert classify_response_mode(prompt) == expected

    def test_paragraph_takes_priority_over_explain(self) -> None:
        # "Explain truth in a paragraph" should classify as PARAGRAPH,
        # not EXPLAIN — the paragraph marker is more specific.
        assert (
            classify_response_mode("Explain truth in a paragraph")
            is ResponseMode.PARAGRAPH
        )

    def test_walkthrough_takes_priority_over_explain(self) -> None:
        # "Explain it step by step" should be WALKTHROUGH, not EXPLAIN.
        assert (
            classify_response_mode("Explain it step by step")
            is ResponseMode.WALKTHROUGH
        )

    def test_is_deterministic_across_calls(self) -> None:
        prompt = "Tell me about truth"
        results = {classify_response_mode(prompt) for _ in range(16)}
        assert results == {ResponseMode.EXPLAIN}

    def test_is_pure_no_external_state(self) -> None:
        src = inspect.getsource(classify_response_mode)
        assert "time." not in src
        assert "datetime" not in src
        assert "os.environ" not in src
        assert "open(" not in src
        assert "random" not in src


# ---------------------------------------------------------------------------
# Additive invariant: classify_intent unchanged
# ---------------------------------------------------------------------------


class TestClassifyIntentUnchanged:
    """Spot-check that classify_intent still returns the same shapes
    on representative prompts.  Full coverage lives in
    test_intent_classification_extensions.py /
    test_intent_subject_extraction.py / test_narrative_example_intents.py;
    here we only verify the additive landing didn't accidentally
    perturb any branch.
    """

    def test_definition_intact(self) -> None:
        result = classify_intent("What is truth?")
        assert result == DialogueIntent(tag=IntentTag.DEFINITION, subject="truth")

    def test_narrative_intact(self) -> None:
        result = classify_intent("Tell me about light")
        assert result == DialogueIntent(tag=IntentTag.NARRATIVE, subject="light")

    def test_example_intact(self) -> None:
        result = classify_intent("Give me an example of memory")
        assert result == DialogueIntent(tag=IntentTag.EXAMPLE, subject="memory")

    def test_cause_intact(self) -> None:
        result = classify_intent("Why does light reveal truth?")
        assert result.tag is IntentTag.CAUSE
        assert result.subject == "light"

    def test_verification_intact(self) -> None:
        result = classify_intent("Does memory require recall?")
        assert result.tag is IntentTag.VERIFICATION
        # subject extraction strips aux verbs ("does") per ADR-0049.
        assert result.subject == "memory"

    def test_dialogue_intent_field_set_unchanged(self) -> None:
        # ResponseMode must NOT have been added as a DialogueIntent
        # field.  Equality on the canonical intent shape must hold.
        fields = {f for f in DialogueIntent.__dataclass_fields__}
        assert fields == {
            "tag", "subject", "secondary_subject", "object",
            "relation", "negated", "frame",
        }


# ---------------------------------------------------------------------------
# Orthogonality: (intent, mode) compose, neither shadows the other
# ---------------------------------------------------------------------------


class TestIntentModeOrthogonality:
    def test_definition_plus_paragraph(self) -> None:
        prompt = "Write a paragraph about truth"
        # The semantic intent and presentation mode are still distinct:
        # the intent anchors the subject as a definition, while
        # ResponseMode carries the paragraph shape.
        intent = classify_intent(prompt)
        mode = classify_response_mode(prompt)
        assert intent.tag is IntentTag.DEFINITION
        assert intent.subject == "truth"
        assert mode is ResponseMode.PARAGRAPH

    def test_narrative_plus_explain(self) -> None:
        prompt = "Tell me about truth"
        intent = classify_intent(prompt)
        mode = classify_response_mode(prompt)
        assert intent.tag is IntentTag.NARRATIVE
        assert mode is ResponseMode.EXPLAIN

    def test_example_intent_matches_example_mode(self) -> None:
        prompt = "Give me an example of memory"
        intent = classify_intent(prompt)
        mode = classify_response_mode(prompt)
        assert intent.tag is IntentTag.EXAMPLE
        assert mode is ResponseMode.EXAMPLE
