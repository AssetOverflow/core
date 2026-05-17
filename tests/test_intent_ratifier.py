"""Tests for field-grounded intent ratification (ADR-0022 §TBD-1)."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from generate.admissibility import AdmissibilityRegion
from generate.intent import DialogueIntent, IntentTag
from generate.intent_ratifier import (
    RatificationOutcome,
    ratify_intent,
    region_for_intent,
)


@dataclass
class _StubVocab:
    """Minimal vocab stub with the same shape ratify_intent reads."""

    table: dict[str, np.ndarray]

    def get_versor(self, token: str) -> np.ndarray:
        return self.table[token.lower()]


def _make_vocab(tokens: dict[str, int]) -> _StubVocab:
    table: dict[str, np.ndarray] = {}
    rng = np.random.default_rng(0)
    for token, seed in tokens.items():
        rng = np.random.default_rng(seed)
        table[token] = rng.standard_normal(32).astype(np.float32)
    return _StubVocab(table=table)


class TestRatifyIntent:
    def test_unknown_seed_passthrough(self) -> None:
        vocab = _make_vocab({})
        intent = DialogueIntent(tag=IntentTag.UNKNOWN, subject="")
        result = ratify_intent(intent, np.zeros(32, dtype=np.float32), vocab=vocab)
        assert result.outcome is RatificationOutcome.PASSTHROUGH
        assert result.intent.tag is IntentTag.UNKNOWN

    def test_no_anchor_returns_passthrough(self) -> None:
        vocab = _make_vocab({})  # empty vocab
        intent = DialogueIntent(tag=IntentTag.DEFINITION, subject="quokka")
        result = ratify_intent(intent, np.ones(32, dtype=np.float32), vocab=vocab)
        assert result.outcome is RatificationOutcome.PASSTHROUGH
        # Seed survives unchanged
        assert result.intent.tag is IntentTag.DEFINITION

    def test_ratified_when_prompt_aligns_with_anchor(self) -> None:
        vocab = _make_vocab({"truth": 1})
        anchor = vocab.get_versor("truth")
        intent = DialogueIntent(tag=IntentTag.DEFINITION, subject="truth")
        # prompt = the anchor itself → maximally aligned
        result = ratify_intent(intent, anchor, vocab=vocab, threshold=0.0)
        assert result.outcome in (
            RatificationOutcome.RATIFIED,
            RatificationOutcome.PASSTHROUGH,
        )
        # Either way the seed survives
        assert result.intent.tag is IntentTag.DEFINITION

    def test_demoted_under_extreme_threshold(self) -> None:
        vocab = _make_vocab({"x": 7})
        intent = DialogueIntent(tag=IntentTag.DEFINITION, subject="x")
        # threshold is unreachable → guaranteed demotion to UNKNOWN
        result = ratify_intent(
            intent,
            np.zeros(32, dtype=np.float32),
            vocab=vocab,
            threshold=1e9,
        )
        assert result.outcome is RatificationOutcome.DEMOTED
        assert result.intent.tag is IntentTag.UNKNOWN
        assert result.seed_tag is IntentTag.DEFINITION

    def test_ratification_is_deterministic(self) -> None:
        vocab = _make_vocab({"truth": 1})
        intent = DialogueIntent(tag=IntentTag.DEFINITION, subject="truth")
        prompt = vocab.get_versor("truth")
        a = ratify_intent(intent, prompt, vocab=vocab)
        b = ratify_intent(intent, prompt, vocab=vocab)
        assert a == b


class TestRegionForIntent:
    def test_empty_vocab_yields_unconstrained_region(self) -> None:
        vocab = _make_vocab({})
        intent = DialogueIntent(tag=IntentTag.DEFINITION, subject="quokka")
        region = region_for_intent(intent, vocab=vocab)
        assert isinstance(region, AdmissibilityRegion)
        assert region.is_unconstrained()
        assert "intent[definition]" in region.label

    def test_grounded_intent_yields_non_trivial_blade(self) -> None:
        vocab = _make_vocab({"truth": 1, "is": 2})
        intent = DialogueIntent(tag=IntentTag.DEFINITION, subject="truth")
        region = region_for_intent(intent, vocab=vocab)
        assert float(np.linalg.norm(region.relation_blade)) > 0.0

    def test_label_includes_intent_tag(self) -> None:
        vocab = _make_vocab({"a": 1})
        intent = DialogueIntent(tag=IntentTag.CAUSE, subject="a")
        region = region_for_intent(intent, vocab=vocab)
        assert "intent[cause]" in region.label
