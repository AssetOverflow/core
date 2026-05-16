"""Unit tests for core.cognition.explain (Gap 3 / introspection)."""
from __future__ import annotations

from dataclasses import dataclass

from core.cognition import explain
from generate.intent import DialogueIntent, IntentTag


@dataclass
class _StubResult:
    intent: DialogueIntent | None
    teaching_candidate: object | None = None


@dataclass
class _StubCandidate:
    correction_text: str


class TestExplainDispatch:
    def test_none_intent_returns_empty(self):
        assert explain(_StubResult(intent=None)) == ""

    def test_unknown_intent_returns_empty(self):
        intent = DialogueIntent(tag=IntentTag.UNKNOWN, subject="x")
        assert explain(_StubResult(intent=intent)) == ""

    def test_definition_returns_canonical_what_is(self):
        intent = DialogueIntent(tag=IntentTag.DEFINITION, subject="wisdom")
        assert explain(_StubResult(intent=intent)) == "What is wisdom?"

    def test_transitive_precedes(self):
        intent = DialogueIntent(
            tag=IntentTag.TRANSITIVE_QUERY,
            subject="wisdom",
            relation="precedes",
        )
        assert explain(_StubResult(intent=intent)) == "What does wisdom precede?"

    def test_transitive_belongs_to_uses_where(self):
        intent = DialogueIntent(
            tag=IntentTag.TRANSITIVE_QUERY,
            subject="question",
            relation="belongs_to",
        )
        assert explain(_StubResult(intent=intent)) == "Where does question belong?"

    def test_transitive_grounds(self):
        intent = DialogueIntent(
            tag=IntentTag.TRANSITIVE_QUERY,
            subject="truth",
            relation="grounds",
        )
        assert explain(_StubResult(intent=intent)) == "What does truth ground?"

    def test_cause(self):
        intent = DialogueIntent(tag=IntentTag.CAUSE, subject="does it rain")
        assert explain(_StubResult(intent=intent)) == "Why does it rain?"

    def test_comparison(self):
        intent = DialogueIntent(
            tag=IntentTag.COMPARISON,
            subject="wisdom",
            secondary_subject="knowledge",
        )
        assert explain(_StubResult(intent=intent)) == "Compare wisdom and knowledge."

    def test_correction_uses_correction_text(self):
        intent = DialogueIntent(
            tag=IntentTag.CORRECTION,
            subject="wisdom is judgment.",
        )
        result = _StubResult(
            intent=intent,
            teaching_candidate=_StubCandidate("Actually wisdom is judgment."),
        )
        assert explain(result) == "Actually wisdom is judgment."

    def test_correction_without_candidate_falls_back(self):
        intent = DialogueIntent(
            tag=IntentTag.CORRECTION,
            subject="x is y",
        )
        assert explain(_StubResult(intent=intent)) == "Actually x is y"

    def test_verification(self):
        intent = DialogueIntent(tag=IntentTag.VERIFICATION, subject="wisdom truth")
        assert explain(_StubResult(intent=intent)) == "Is wisdom truth?"

    def test_recall(self):
        intent = DialogueIntent(tag=IntentTag.RECALL, subject="the prior fact")
        assert explain(_StubResult(intent=intent)) == "Remember the prior fact."

    def test_determinism(self):
        intent = DialogueIntent(tag=IntentTag.DEFINITION, subject="wisdom")
        r = _StubResult(intent=intent)
        assert explain(r) == explain(r)


class TestExplainRoundTrip:
    """Round-trip: explain output re-classifies under the same intent."""

    def test_definition_round_trip_intent(self):
        from generate.intent import classify_intent

        intent = DialogueIntent(tag=IntentTag.DEFINITION, subject="wisdom")
        account = explain(_StubResult(intent=intent))
        re_intent = classify_intent(account)
        assert re_intent.tag is IntentTag.DEFINITION
        assert re_intent.subject == "wisdom"

    def test_transitive_round_trip_intent(self):
        from generate.intent import classify_intent

        intent = DialogueIntent(
            tag=IntentTag.TRANSITIVE_QUERY,
            subject="creation",
            relation="precedes",
        )
        account = explain(_StubResult(intent=intent))
        re_intent = classify_intent(account)
        assert re_intent.tag is IntentTag.TRANSITIVE_QUERY
        assert re_intent.subject == "creation"
        assert re_intent.relation == "precedes"

    def test_belongs_to_round_trip_intent(self):
        from generate.intent import classify_intent

        intent = DialogueIntent(
            tag=IntentTag.TRANSITIVE_QUERY,
            subject="question",
            relation="belongs_to",
        )
        account = explain(_StubResult(intent=intent))
        re_intent = classify_intent(account)
        assert re_intent.tag is IntentTag.TRANSITIVE_QUERY
        assert re_intent.relation == "belongs_to"
