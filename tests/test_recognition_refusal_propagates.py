"""W-011 — recognition refusal propagates to CognitiveTurnResult.refusal_reason.

Pin: when a DerivedRecognizer is attached and recognition refuses the input,
CognitiveTurnResult.refusal_reason is populated with the RECOGNITION_REFUSED
code.  Happy-path (admitted) turns keep refusal_reason empty.
"""

from __future__ import annotations

import pytest

from chat.runtime import ChatRuntime
from core.cognition.pipeline import CognitiveTurnPipeline
from generate.exhaustion import RefusalReason
from recognition.anti_unifier import DerivedRecognizer, derive_recognizer
from recognition.outcome import (
    EvidenceSpan,
    FeatureBundle,
    NegativeEvidence,
)


def _span(tokens: tuple[str, ...], s: int, e: int) -> EvidenceSpan:
    return EvidenceSpan(start=s, end=e, text=" ".join(tokens[s:e]))


def _make_teaching_examples() -> list[tuple[tuple[str, ...], FeatureBundle]]:
    rows = [
        ("John", "has", "5", "apples"),
        ("Mary", "has", "3", "books"),
    ]
    examples = []
    for tokens in rows:
        has_idx = tokens.index("has")
        bundle = FeatureBundle.from_mapping({
            "agent": (tokens[0], _span(tokens, 0, 1)),
            "count": (int(tokens[has_idx + 1]), _span(tokens, has_idx + 1, has_idx + 2)),
            "relation": ("has", _span(tokens, has_idx, has_idx + 1)),
            "unit": (tokens[has_idx + 2], _span(tokens, has_idx + 2, has_idx + 3)),
            "polarity": ("+", NegativeEvidence(0, len(tokens), "no negator")),
        })
        examples.append((tokens, bundle))
    return examples


@pytest.fixture(scope="module")
def recognizer() -> DerivedRecognizer:
    return derive_recognizer(_make_teaching_examples())


class TestRecognitionRefusalPropagates:
    """W-011: recognition refusal materializes in CognitiveTurnResult."""

    def test_refused_turn_has_recognition_refusal_reason(
        self, recognizer: DerivedRecognizer
    ) -> None:
        runtime = ChatRuntime()
        pipeline = CognitiveTurnPipeline(runtime, recognizer=recognizer)
        result = pipeline.run("something completely unrelated to the pattern")
        assert result.refusal_reason == RefusalReason.RECOGNITION_REFUSED.value

    def test_admitted_turn_has_empty_refusal_reason(
        self, recognizer: DerivedRecognizer
    ) -> None:
        runtime = ChatRuntime()
        pipeline = CognitiveTurnPipeline(runtime, recognizer=recognizer)
        result = pipeline.run("John has 5 apples")
        assert result.refusal_reason == ""

    def test_recognition_refusal_wins_over_generation_refusal(
        self, recognizer: DerivedRecognizer
    ) -> None:
        runtime = ChatRuntime()
        pipeline = CognitiveTurnPipeline(runtime, recognizer=recognizer)
        result = pipeline.run("xyz totally unknown input")
        assert result.refusal_reason == RefusalReason.RECOGNITION_REFUSED.value
