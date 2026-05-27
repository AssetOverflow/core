"""Tests for the Phase-1 question-frame reader lifecycle (ADR-0164.3)."""

from __future__ import annotations

import pytest

from generate.comprehension.lifecycle import (
    apply_word,
    begin_sentence,
    end_sentence,
)
from generate.comprehension.state import (
    EntityRef,
    ProblemReadingState,
    ReaderRefusal,
    SentenceReadingState,
)


def _empty_problem(
    *,
    registry: tuple[EntityRef, ...] = (),
    sentence_index: int = 0,
) -> ProblemReadingState:
    return ProblemReadingState(
        entity_registry=registry,
        accumulated_initial_state=(),
        accumulated_operations=(),
        unknown_target_slot=None,
        pronoun_resolution_history=(),
        sentence_index=sentence_index,
        source_text_offset=0,
    )


def _read_sentence(
    words: list[str],
    problem_state: ProblemReadingState,
) -> SentenceReadingState | ReaderRefusal:
    """Drive a full sentence through apply_word. Returns final state or refusal."""
    state: SentenceReadingState | ReaderRefusal = begin_sentence(problem_state, 0)
    assert isinstance(state, SentenceReadingState)
    for word in words:
        result = apply_word(state, problem_state, word)
        if isinstance(result, ReaderRefusal):
            return result
        state = result
    return state


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


class TestDeterminism:
    def test_apply_word_byte_equal_outputs(self) -> None:
        ps = _empty_problem(registry=(EntityRef("monica", "female", 0),))
        s1 = begin_sentence(ps, 0)
        s2 = begin_sentence(ps, 0)
        r1 = apply_word(s1, ps, "How")
        r2 = apply_word(s2, ps, "How")
        assert isinstance(r1, SentenceReadingState)
        assert isinstance(r2, SentenceReadingState)
        assert r1.canonical_bytes() == r2.canonical_bytes()
        assert r1.canonical_hash() == r2.canonical_hash()

    def test_full_sentence_byte_equal(self) -> None:
        ps = _empty_problem(registry=(EntityRef("monica", "female", 0),))
        words = ["How", "much", "time", "did", "she", "spend", "?"]
        a = _read_sentence(words, ps)
        b = _read_sentence(words, ps)
        assert isinstance(a, SentenceReadingState)
        assert isinstance(b, SentenceReadingState)
        assert a.canonical_bytes() == b.canonical_bytes()


# ---------------------------------------------------------------------------
# Five GSM8K target question sentences
# ---------------------------------------------------------------------------


class TestGSM8KQuestions:
    def test_0007_how_many_more_boxes(self) -> None:
        ps = _empty_problem(
            registry=(EntityRef("francine_and_friend", "unknown", 0),)
        )
        words = [
            "How", "many", "more", "boxes", "do", "they", "need",
            "if", "Francine", "has", "a", "total", "of", "85", "crayons", "?",
        ]
        state = _read_sentence(words, ps)
        assert isinstance(state, SentenceReadingState), state
        end = end_sentence(state, ps)
        assert isinstance(end, ProblemReadingState), end
        target = end.unknown_target_slot
        assert target is not None
        assert target.entity == "francine_and_friend"
        assert target.unit_class == "count"
        assert target.kind == "difference"

    def test_0017_how_much_cost_him(self) -> None:
        ps = _empty_problem(
            registry=(
                EntityRef("eric", "male", 0),
                EntityRef("house", "neuter", 1),
            )
        )
        words = ["How", "much", "will", "it", "cost", "him", "?"]
        state = _read_sentence(words, ps)
        assert isinstance(state, SentenceReadingState), state
        end = end_sentence(state, ps)
        assert isinstance(end, ProblemReadingState), end
        target = end.unknown_target_slot
        assert target is not None
        assert target.entity == "eric"
        assert target.unit_class == "currency"
        assert target.kind == "continuous_quantity"

    def test_0027_how_many_followers_malcolm(self) -> None:
        ps = _empty_problem()
        words = [
            "How", "many", "followers", "does", "Malcolm", "have",
            "on", "all", "his", "social", "media", "?",
        ]
        state = _read_sentence(words, ps)
        assert isinstance(state, SentenceReadingState), state
        end = end_sentence(state, ps)
        assert isinstance(end, ProblemReadingState), end
        target = end.unknown_target_slot
        assert target is not None
        assert target.entity == "malcolm"
        assert target.unit_class == "count"
        assert target.kind == "discrete_quantity"
        # Proper-noun entity entered the registry.
        names = [e.canonical_name for e in end.entity_registry]
        assert "malcolm" in names

    def test_0036_how_much_time_studying(self) -> None:
        ps = _empty_problem(registry=(EntityRef("monica", "female", 0),))
        words = [
            "How", "much", "time", "did", "she", "spend", "studying",
            "in", "total", "during", "the", "five", "days", "?",
        ]
        state = _read_sentence(words, ps)
        assert isinstance(state, SentenceReadingState), state
        end = end_sentence(state, ps)
        assert isinstance(end, ProblemReadingState), end
        target = end.unknown_target_slot
        assert target is not None
        assert target.entity == "monica"
        assert target.unit_class == "time"
        assert target.kind == "continuous_quantity"

    def test_0043_how_much_money_left(self) -> None:
        ps = _empty_problem(registry=(EntityRef("sandra", "female", 0),))
        words = [
            "How", "much", "money", "will", "she", "be", "left",
            "with", "after", "the", "purchase", "?",
        ]
        state = _read_sentence(words, ps)
        assert isinstance(state, SentenceReadingState), state
        end = end_sentence(state, ps)
        assert isinstance(end, ProblemReadingState), end
        target = end.unknown_target_slot
        assert target is not None
        assert target.entity == "sandra"
        assert target.unit_class == "currency"
        assert target.kind == "continuous_quantity"


# ---------------------------------------------------------------------------
# Refusal modes
# ---------------------------------------------------------------------------


class TestRefusals:
    def test_unknown_word(self) -> None:
        ps = _empty_problem()
        s = begin_sentence(ps, 0)
        r = apply_word(s, ps, "@@@")
        assert isinstance(r, ReaderRefusal)
        assert r.reason == "unknown_word"
        assert r.token_text == "@@@"

    def test_unexpected_category_non_question_opener(self) -> None:
        """A statement-frame opener at position 0 is Phase-2 scope."""
        ps = _empty_problem(registry=(EntityRef("francine", "female", 0),))
        s = begin_sentence(ps, 0)
        # "francine" is a proper_noun_entity_female — would open a
        # statement frame. Phase 1 refuses.
        r = apply_word(s, ps, "Francine")
        assert isinstance(r, ReaderRefusal)
        assert r.reason == "unexpected_category"
        assert "Phase-2" in r.detail

    def test_unresolved_pronoun_empty_registry(self) -> None:
        """A pronoun with no compatible entity refuses cleanly."""
        ps = _empty_problem()  # empty registry
        s = begin_sentence(ps, 0)
        s = apply_word(s, ps, "How")
        assert isinstance(s, SentenceReadingState)
        s = apply_word(s, ps, "much")
        assert isinstance(s, SentenceReadingState)
        s = apply_word(s, ps, "money")
        assert isinstance(s, SentenceReadingState)
        s = apply_word(s, ps, "will")
        assert isinstance(s, SentenceReadingState)
        r = apply_word(s, ps, "she")
        assert isinstance(r, ReaderRefusal)
        assert r.reason == "unresolved_pronoun"
        assert r.token_text == "she"

    def test_unfinished_frame_on_end(self) -> None:
        ps = _empty_problem()
        s = begin_sentence(ps, 0)
        # No words applied → frame is still None.
        end = end_sentence(s, ps)
        assert isinstance(end, ReaderRefusal)
        assert end.reason == "unfinished_frame"

    def test_unattached_quantity_on_end(self) -> None:
        """A SentenceReadingState with frame set but pending_quantities
        non-empty refuses with unattached_quantity at end_sentence."""
        from decimal import Decimal

        from generate.comprehension.state import QuantityRef

        ps = _empty_problem()
        # Construct a hand-built state to isolate the rule.
        pending = QuantityRef(
            value=Decimal("18"),
            unit=None,
            unit_class="pending",
            owner_entity=None,
            mention_position=0,
        )
        state = SentenceReadingState(
            entities=(),
            quantities=(),
            operations=(),
            frame="question_frame",
            pending_quantities=(pending,),
            token_index=2,
        )
        end = end_sentence(state, ps)
        assert isinstance(end, ReaderRefusal)
        assert end.reason == "unattached_quantity"

    def test_incomplete_operation_no_unit(self) -> None:
        """question_frame closes with no unit_class on the target → refuse."""
        ps = _empty_problem(registry=(EntityRef("monica", "female", 0),))
        s = begin_sentence(ps, 0)
        # Only "How" then "?" — no unit was ever set.
        s = apply_word(s, ps, "How")
        assert isinstance(s, SentenceReadingState)
        s = apply_word(s, ps, "?")
        assert isinstance(s, SentenceReadingState)
        end = end_sentence(s, ps)
        assert isinstance(end, ReaderRefusal)
        assert end.reason == "incomplete_operation"


# ---------------------------------------------------------------------------
# Lifecycle invariants
# ---------------------------------------------------------------------------


class TestLifecycleInvariants:
    def test_problem_state_preserved_when_sentence_introduces_no_entity(self) -> None:
        """begin → apply_word(*) → end_sentence preserves the registry
        when the sentence only references existing entities."""
        registry = (EntityRef("monica", "female", 0),)
        ps = _empty_problem(registry=registry)
        words = ["How", "much", "time", "did", "she", "spend", "?"]
        state = _read_sentence(words, ps)
        assert isinstance(state, SentenceReadingState)
        end = end_sentence(state, ps)
        assert isinstance(end, ProblemReadingState)
        assert end.entity_registry == registry

    def test_sentence_index_advances(self) -> None:
        ps = _empty_problem(registry=(EntityRef("monica", "female", 0),))
        words = ["How", "much", "time", "did", "she", "spend", "?"]
        state = _read_sentence(words, ps)
        assert isinstance(state, SentenceReadingState)
        end = end_sentence(state, ps)
        assert isinstance(end, ProblemReadingState)
        assert end.sentence_index == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
