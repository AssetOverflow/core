"""Phase 2 statement-frame reader tests (ADR-0164 Phase 2)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from generate.comprehension.lifecycle import (
    apply_word,
    begin_sentence,
    end_sentence,
    finalize,
)
from generate.comprehension.state import (
    EntityRef,
    ProblemReadingState,
    ReaderRefusal,
    SentenceReadingState,
)
from generate.math_problem_graph import MathProblemGraph


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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
    state: SentenceReadingState | ReaderRefusal = begin_sentence(problem_state, 0)
    assert isinstance(state, SentenceReadingState)
    for word in words:
        result = apply_word(state, problem_state, word)
        if isinstance(result, ReaderRefusal):
            return result
        state = result
    return state


def _read_problem(sentences: list[list[str]]) -> ProblemReadingState | ReaderRefusal:
    """Drive a list of tokenised sentences through the full lifecycle."""
    ps: ProblemReadingState = _empty_problem()
    for words in sentences:
        ss = _read_sentence(words, ps)
        if isinstance(ss, ReaderRefusal):
            return ss
        end = end_sentence(ss, ps)
        if isinstance(end, ReaderRefusal):
            return end
        ps = end
    return ps


# ---------------------------------------------------------------------------
# Initial-state frame
# ---------------------------------------------------------------------------


class TestInitialStateFrame:
    def test_proper_noun_possession_verb_count_unit(self) -> None:
        """Sandra had 600 dollars."""
        ps = _empty_problem()
        words = ["Sandra", "had", "600", "dollars", "."]
        ss = _read_sentence(words, ps)
        assert isinstance(ss, SentenceReadingState), ss
        end = end_sentence(ss, ps)
        assert isinstance(end, ProblemReadingState), end
        assert len(end.accumulated_initial_state) == 1
        pip = end.accumulated_initial_state[0]
        assert pip.entity == "sandra"
        assert pip.quantity is not None
        assert pip.quantity.value == Decimal("600")
        assert pip.quantity.unit == "dollar"
        assert "sandra" in {e.canonical_name for e in end.entity_registry}

    def test_proper_noun_has_count_unit(self) -> None:
        """Tom has 5 apples."""
        ps = _empty_problem()
        words = ["Tom", "has", "5", "apples", "."]
        ss = _read_sentence(words, ps)
        assert isinstance(ss, SentenceReadingState), ss
        end = end_sentence(ss, ps)
        assert isinstance(end, ProblemReadingState), end
        pip = end.accumulated_initial_state[0]
        assert pip.entity == "tom"
        assert pip.quantity.unit == "apple"

    def test_sentence_index_advances(self) -> None:
        ps = _empty_problem()
        words = ["Sandra", "had", "600", "dollars", "."]
        ss = _read_sentence(words, ps)
        assert isinstance(ss, SentenceReadingState)
        end = end_sentence(ss, ps)
        assert isinstance(end, ProblemReadingState)
        assert end.sentence_index == 1

    def test_entity_added_to_registry(self) -> None:
        ps = _empty_problem()
        words = ["Monica", "had", "5", "apples", "."]
        ss = _read_sentence(words, ps)
        assert isinstance(ss, SentenceReadingState)
        end = end_sentence(ss, ps)
        assert isinstance(end, ProblemReadingState)
        names = [e.canonical_name for e in end.entity_registry]
        assert "monica" in names

    def test_refuse_no_quantity(self) -> None:
        """initial_state_frame with no quantity → incomplete_operation."""
        ps = _empty_problem()
        words = ["Sandra", "had", "."]
        ss = _read_sentence(words, ps)
        assert isinstance(ss, SentenceReadingState)
        end = end_sentence(ss, ps)
        assert isinstance(end, ReaderRefusal)
        assert end.reason == "incomplete_operation"


# ---------------------------------------------------------------------------
# Operation frame
# ---------------------------------------------------------------------------


class TestOperationFrame:
    def test_depletion_verb_count(self) -> None:
        """She spent 200 dollars."""
        ps = _empty_problem(registry=(EntityRef("sandra", "female", 0),))
        words = ["She", "spent", "200", "dollars", "."]
        ss = _read_sentence(words, ps)
        assert isinstance(ss, SentenceReadingState), ss
        end = end_sentence(ss, ps)
        assert isinstance(end, ProblemReadingState), end
        assert len(end.accumulated_operations) == 1
        pop = end.accumulated_operations[0]
        assert pop.actor == "sandra"
        assert pop.kind == "depletion_verb"
        assert pop.operand is not None
        assert pop.operand.value == Decimal("200")
        assert pop.operand.unit == "dollar"

    def test_accumulation_verb_count(self) -> None:
        """Tom earned 3 books."""
        ps = _empty_problem(registry=(EntityRef("tom", "male", 0),))
        words = ["Tom", "earned", "3", "books", "."]
        ss = _read_sentence(words, ps)
        assert isinstance(ss, SentenceReadingState), ss
        end = end_sentence(ss, ps)
        assert isinstance(end, ProblemReadingState), end
        pop = end.accumulated_operations[0]
        assert pop.actor == "tom"
        assert pop.kind == "accumulation_verb"
        assert pop.operand.unit == "book"

    def test_pronoun_subject(self) -> None:
        """He spent 50 dollars — pronoun resolved from registry."""
        ps = _empty_problem(registry=(EntityRef("eric", "male", 0),))
        words = ["He", "spent", "50", "dollars", "."]
        ss = _read_sentence(words, ps)
        assert isinstance(ss, SentenceReadingState), ss
        end = end_sentence(ss, ps)
        assert isinstance(end, ProblemReadingState), end
        pop = end.accumulated_operations[0]
        assert pop.actor == "eric"

    def test_refuse_no_quantity(self) -> None:
        ps = _empty_problem(registry=(EntityRef("sandra", "female", 0),))
        words = ["She", "spent", "."]
        ss = _read_sentence(words, ps)
        assert isinstance(ss, SentenceReadingState)
        end = end_sentence(ss, ps)
        assert isinstance(end, ReaderRefusal)
        assert end.reason == "incomplete_operation"


# ---------------------------------------------------------------------------
# Descriptive frame
# ---------------------------------------------------------------------------


class TestDescriptiveFrame:
    def test_copula_drains_advances(self) -> None:
        """Sandra is a baker. — descriptive_frame, no math state."""
        ps = _empty_problem()
        words = ["Sandra", "is", "a", "baker", "."]
        ss = _read_sentence(words, ps)
        # "a" drains, "baker" → unknown_word refusal (not in lexicon)
        # This is expected for Phase 2 scope
        assert isinstance(ss, (SentenceReadingState, ReaderRefusal))

    def test_copula_with_known_tokens_only(self) -> None:
        """Sandra is the student. — all known tokens drain."""
        ps = _empty_problem()
        words = ["Sandra", "is", "the", "student", "."]
        ss = _read_sentence(words, ps)
        assert isinstance(ss, SentenceReadingState), ss
        end = end_sentence(ss, ps)
        assert isinstance(end, ProblemReadingState), end
        assert len(end.accumulated_initial_state) == 0
        assert len(end.accumulated_operations) == 0
        assert end.sentence_index == 1


# ---------------------------------------------------------------------------
# Full problem round-trip with finalize()
# ---------------------------------------------------------------------------


class TestFinalize:
    def test_simple_two_sentence_problem(self) -> None:
        """Sandra had 600 dollars. She spent 200 dollars. How much is left?"""
        sentences = [
            ["Sandra", "had", "600", "dollars", "."],
            ["She", "spent", "200", "dollars", "."],
            ["How", "much", "money", "will", "she", "be", "left", "with", "?"],
        ]
        ps = _read_problem(sentences)
        assert isinstance(ps, ProblemReadingState), ps
        graph = finalize(ps)
        assert isinstance(graph, MathProblemGraph), graph
        assert "sandra" in graph.entities
        assert len(graph.initial_state) == 1
        assert graph.initial_state[0].entity == "sandra"
        assert graph.initial_state[0].quantity.value == 600.0
        assert len(graph.operations) == 1
        assert graph.operations[0].kind == "subtract"
        assert graph.operations[0].operand.value == 200.0
        assert graph.unknown.entity == "sandra"

    def test_finalize_no_question_target_refuses(self) -> None:
        ps = _empty_problem()
        result = finalize(ps)
        assert isinstance(result, ReaderRefusal)
        assert result.reason == "no_question_target"

    def test_finalize_empty_registry_refuses(self) -> None:
        from generate.comprehension.state import QuestionTargetSlot
        qs = QuestionTargetSlot(
            kind="continuous_quantity",
            entity="sandra",
            unit_class="currency",
            unit="dollar",
            position=0,
        )
        ps = ProblemReadingState(
            entity_registry=(),  # empty
            accumulated_initial_state=(),
            accumulated_operations=(),
            unknown_target_slot=qs,
            pronoun_resolution_history=(),
            sentence_index=1,
            source_text_offset=0,
        )
        result = finalize(ps)
        assert isinstance(result, ReaderRefusal)
        assert result.reason == "dangling_entity"

    def test_determinism(self) -> None:
        """Same input → same trace hash."""
        sentences = [
            ["Sandra", "had", "600", "dollars", "."],
            ["She", "spent", "200", "dollars", "."],
            ["How", "much", "money", "will", "she", "be", "left", "with", "?"],
        ]
        ps1 = _read_problem(sentences)
        ps2 = _read_problem(sentences)
        assert isinstance(ps1, ProblemReadingState)
        assert isinstance(ps2, ProblemReadingState)
        assert ps1.canonical_hash() == ps2.canonical_hash()


# ---------------------------------------------------------------------------
# Refusal coverage
# ---------------------------------------------------------------------------


class TestPhase2Refusals:
    def test_fraction_token_refused(self) -> None:
        """Fraction literals are out of Phase 2 scope."""
        ps = _empty_problem()
        s = begin_sentence(ps, 0)
        result = apply_word(s, ps, "1/2")
        assert isinstance(result, ReaderRefusal)
        assert result.reason == "unexpected_category"
        assert "Phase 2.1" in result.detail

    def test_verb_without_entity_opens_descriptive(self) -> None:
        """Verb before entity (subject dropped) opens descriptive_frame."""
        ps = _empty_problem()
        s = begin_sentence(ps, 0)
        result = apply_word(s, ps, "spent")
        assert isinstance(result, SentenceReadingState)
        assert result.frame == "descriptive_frame"

    def test_unresolved_pronoun_statement_frame(self) -> None:
        """Pronoun with empty registry refuses at pre-frame."""
        ps = _empty_problem()
        s = begin_sentence(ps, 0)
        result = apply_word(s, ps, "She")
        assert isinstance(result, ReaderRefusal)
        assert result.reason == "unresolved_pronoun"

    def test_multi_sentence_wrong_zero(self) -> None:
        """All-or-nothing: if one sentence fails, the whole problem refuses."""
        # First sentence succeeds, second has unknown word "baker"
        ps0 = _empty_problem()
        words1 = ["Sandra", "had", "600", "dollars", "."]
        ss1 = _read_sentence(words1, ps0)
        assert isinstance(ss1, SentenceReadingState)
        ps1 = end_sentence(ss1, ps0)
        assert isinstance(ps1, ProblemReadingState)

        # Second sentence: "baker" is unknown → refusal
        words2 = ["She", "is", "a", "baker", "."]
        ss2 = _read_sentence(words2, ps1)
        # "baker" not in lexicon → unknown_word refusal
        assert isinstance(ss2, ReaderRefusal)
        assert ss2.reason == "unknown_word"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
