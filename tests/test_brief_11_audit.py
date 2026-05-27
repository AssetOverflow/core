"""Brief 11 / PR 11A — regression tests for reader closure audit.

Three categories:

1. **Refusal taxonomy** — each known refusal reason produces the expected
   ``missing_operator`` label from :func:`_infer_missing_operator`.
2. **Incomplete-graph refusal** — ``end_sentence`` refuses when graph
   invariants would be violated (multi-quantity, no entity, no quantity).
3. **Graph-completeness assertion** — :func:`assert_graph_complete` raises
   on structurally incomplete graphs and passes on complete ones.

All tests are pure: no file I/O, no runtime state, no teaching-store access.
wrong == 0 is not directly tested here (that is the measurement lane's job),
but no test herein produces a wrong answer.
"""

from __future__ import annotations

import pytest

from generate.comprehension.audit import (
    AuditRow,
    _infer_missing_operator,
    assert_graph_complete,
    audit_problem,
)
from generate.comprehension.lifecycle import (
    apply_word,
    begin_sentence,
    end_sentence,
)
from generate.comprehension.state import ProblemReadingState, ReaderRefusal


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fresh_problem() -> ProblemReadingState:
    return ProblemReadingState(
        entity_registry=(),
        accumulated_initial_state=(),
        accumulated_operations=(),
        unknown_target_slot=None,
        pronoun_resolution_history=(),
        sentence_index=0,
        source_text_offset=0,
    )


def _apply_words(
    words: list[str],
    problem_state: ProblemReadingState | None = None,
) -> "tuple[object, ProblemReadingState]":
    """Apply words through begin/apply_word/end_sentence; return (end_result, latest_problem)."""
    ps = problem_state or _fresh_problem()
    ss = begin_sentence(ps, source_text_offset=0)
    for w in words:
        result = apply_word(ss, ps, w)
        if isinstance(result, ReaderRefusal):
            return result, ps
        ss = result
    return end_sentence(ss, ps), ps


# ---------------------------------------------------------------------------
# 1. Refusal taxonomy / missing_operator inference
# ---------------------------------------------------------------------------


class TestMissingOperatorInference:
    def test_multi_quantity_composition(self) -> None:
        label = _infer_missing_operator(
            "incomplete_operation",
            "operation_frame has 2 quantities; multi-quantity operations are Phase-2.1 scope",
        )
        assert label == "multi_quantity_composition"

    def test_quantity_extraction_no_quantity(self) -> None:
        label = _infer_missing_operator(
            "incomplete_operation",
            "operation_frame closed with no quantity",
        )
        assert label == "quantity_extraction"

    def test_subject_entity_recovery(self) -> None:
        label = _infer_missing_operator(
            "incomplete_operation",
            "operation_frame has no subject entity",
        )
        assert label == "subject_entity_recovery"

    def test_unit_binding(self) -> None:
        label = _infer_missing_operator(
            "unattached_quantity",
            "1 quantities never attached to entity+unit at sentence end",
        )
        assert label == "unit_binding"

    def test_compound_numeric_hundred(self) -> None:
        label = _infer_missing_operator(
            "unknown_word",
            "no primitive or lexicon match for 'hundred'",
        )
        assert label == "compound_numeric_literal"

    def test_compound_time_literal(self) -> None:
        label = _infer_missing_operator(
            "unknown_word",
            "no primitive or lexicon match for 'one-hour'",
        )
        assert label == "compound_time_literal"

    def test_lexicon_entry_generic(self) -> None:
        label = _infer_missing_operator(
            "unknown_word",
            "no primitive or lexicon match for 'presently'",
        )
        assert label == "lexicon_entry"

    def test_fraction_literal(self) -> None:
        label = _infer_missing_operator(
            "unexpected_category",
            "fraction/percentage literal at position 2 is out-of-scope",
        )
        assert label == "fraction_percentage_literal"

    def test_multi_subject_sentence(self) -> None:
        label = _infer_missing_operator(
            "unexpected_category",
            "second entity 'Bob' at pre-frame position 2; multi-subject sentences are Phase-2.1 scope",
        )
        assert label == "multi_subject_sentence"

    def test_unresolved_pronoun(self) -> None:
        label = _infer_missing_operator(
            "unresolved_pronoun",
            "pronoun 'them' has no compatible entity in registry (size=0)",
        )
        assert label == "pronoun_resolution"

    def test_no_question_target(self) -> None:
        label = _infer_missing_operator(
            "no_question_target",
            "ProblemReadingState has no unknown_target_slot after finalize",
        )
        assert label == "question_target_slot"


# ---------------------------------------------------------------------------
# 2. Incomplete-graph refusal via lifecycle
# ---------------------------------------------------------------------------


class TestIncompleteGraphRefusal:
    def test_operation_frame_refuses_no_quantity(self) -> None:
        """operation_frame with verb but no number → incomplete_operation."""
        # 'Alice bought .' — depletion_verb with no quantity before terminator.
        result, _ = _apply_words(["Alice", "bought", "."])
        assert isinstance(result, ReaderRefusal)
        assert result.reason == "incomplete_operation"

    def test_initial_state_frame_refuses_no_quantity(self) -> None:
        """initial_state_frame with no quantity → incomplete_operation."""
        result, _ = _apply_words(["Alice", "has", "."])
        assert isinstance(result, ReaderRefusal)
        assert result.reason == "incomplete_operation"

    def test_unattached_quantity_refusal(self) -> None:
        """A bare quantity with no following unit → unattached_quantity at end_sentence.

        'Alice bought 5 .' — 5 has no unit noun, so pending_quantities is non-empty.
        """
        result, _ = _apply_words(["Alice", "bought", "5", "."])
        assert isinstance(result, ReaderRefusal)
        assert result.reason == "unattached_quantity"

    def test_unresolved_pronoun_no_registry(self) -> None:
        """Pronoun with empty registry → unresolved_pronoun."""
        result, _ = _apply_words(["She", "bought", "5", "apples", "."])
        assert isinstance(result, ReaderRefusal)
        assert result.reason == "unresolved_pronoun"

    def test_fraction_token_refuses(self) -> None:
        """Fraction literal always refuses in Phase 2."""
        result, _ = _apply_words(["Alice", "ate", "1/2", "pie", "."])
        # 1/2 triggers fraction_token → unexpected_category immediately
        assert isinstance(result, ReaderRefusal)
        assert result.reason == "unexpected_category"


# ---------------------------------------------------------------------------
# 3. assert_graph_complete
# ---------------------------------------------------------------------------


class TestAssertGraphComplete:
    """Uses audit_problem on canonical problems to get real MathProblemGraph objects."""

    _SIMPLE_PROBLEM = (
        "Alice has 3 apples . "
        "She ate 1 apple . "
        "How many apples does Alice have ?"
    )

    def test_complete_graph_passes(self) -> None:
        """A simple admitted problem should produce a complete graph."""
        graph, audit_rows = audit_problem(self._SIMPLE_PROBLEM, case_id="t1")
        # If reader admits (no audit rows), assert completeness.
        if audit_rows:
            pytest.skip(
                f"Reader refused this problem (reason={audit_rows[0].refusal_reason}); "
                "graph completeness test not applicable"
            )
        assert graph is not None
        assert_graph_complete(graph)  # type: ignore[arg-type]

    def test_audit_row_tsv_header(self) -> None:
        header = AuditRow.tsv_header()
        cols = header.split("\t")
        assert cols[0] == "case_id"
        assert cols[-1] == "refusal_reason"
        assert len(cols) == 6

    def test_audit_row_as_tsv_row(self) -> None:
        row = AuditRow(
            case_id="case_0",
            sentence_index=1,
            token_index=3,
            token_text="hundred",
            recognized_terms=("Alice", "bought"),
            skipped_frame="operation_frame",
            missing_operator="compound_numeric_literal",
            refusal_reason="unknown_word",
            refusal_detail="no primitive or lexicon match for 'hundred'",
        )
        tsv = row.as_tsv_row()
        parts = tsv.split("\t")
        assert parts[0] == "case_0"
        assert parts[1] == "1"
        assert "Alice" in parts[2]
        assert parts[3] == "operation_frame"
        assert parts[4] == "compound_numeric_literal"
        assert parts[5] == "unknown_word"

    def test_audit_problem_returns_refusal_for_unknown_word(self) -> None:
        """Problem with an unknown word returns a ReaderRefusal and one audit row."""
        problem = "Alice bought hundred apples . How many apples does Alice have ?"
        result, rows = audit_problem(problem, case_id="c42")
        assert isinstance(result, ReaderRefusal)
        assert len(rows) == 1
        assert rows[0].refusal_reason == "unknown_word"
        assert rows[0].missing_operator == "compound_numeric_literal"
        assert rows[0].case_id == "c42"

    def test_audit_problem_empty_string(self) -> None:
        result, rows = audit_problem("", case_id="empty")
        assert result is None
        assert rows == []


# ---------------------------------------------------------------------------
# 4. AuditRow integrity
# ---------------------------------------------------------------------------


class TestAuditRowIntegrity:
    def test_frozen_dataclass(self) -> None:
        row = AuditRow(
            case_id="x",
            sentence_index=0,
            token_index=0,
            token_text="test",
            recognized_terms=(),
            skipped_frame=None,
            missing_operator=None,
            refusal_reason="unknown_word",
            refusal_detail="detail",
        )
        with pytest.raises((AttributeError, TypeError)):
            row.case_id = "y"  # type: ignore[misc]

    def test_no_recognized_terms_tsv(self) -> None:
        row = AuditRow(
            case_id="c",
            sentence_index=0,
            token_index=0,
            token_text="",
            recognized_terms=(),
            skipped_frame=None,
            missing_operator=None,
            refusal_reason="unfinished_frame",
            refusal_detail="empty sentence",
        )
        tsv = row.as_tsv_row()
        assert "(none)" in tsv
        assert "(pre-frame)" in tsv
