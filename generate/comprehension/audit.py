"""Brief 11 / PR 11A — reader closure audit helpers.

Provides:

* :class:`AuditRow` — typed record for a recognized-but-skipped statement.
* :func:`audit_problem` — runs the Phase 2 reader over a single raw problem
  string and returns (result, audit_rows).  ``result`` is either a
  ``MathProblemGraph`` (success), a ``ReaderRefusal`` (first refusal), or
  ``None`` (regex fallback — reader was not attempted for this case).
* :func:`assert_graph_complete` — raises ``AssertionError`` with a descriptive
  message if any structural requirement of a ``MathProblemGraph`` is unmet.
  Intended for use inside tests and measurement scripts.

These helpers are *pure audit instruments* — they do not mutate any pack,
teaching store, or runtime state.  They operate solely on the reader path
defined by ADR-0164.3 and ADR-0164.4.

ADR-0166 invariant: these helpers produce diagnostic output only.  No
capability claim is made by their existence.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from generate.math_problem_graph import MathProblemGraph

from generate.comprehension.lifecycle import (
    apply_word,
    begin_sentence,
    end_sentence,
    finalize,
)
from generate.comprehension.state import ProblemReadingState, ReaderRefusal


# ---------------------------------------------------------------------------
# Audit row
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AuditRow:
    """One recognized-but-skipped or refused statement.

    Columns match the Brief 11 audit row shape::

        case_id | sentence_index | recognized_terms | skipped_frame
                | missing_operator | refusal_reason
    """

    case_id: str
    """Caller-supplied identifier (e.g. GSM8K row index as string)."""

    sentence_index: int
    """0-based sentence index at which the refusal occurred."""

    token_index: int
    """0-based token index within the sentence (from ReaderRefusal)."""

    token_text: str
    """Surface form of the token that triggered the refusal."""

    recognized_terms: tuple[str, ...]
    """Words successfully classified before the refusal in this sentence."""

    skipped_frame: str | None
    """Frame kind that was open when the refusal occurred, or None."""

    missing_operator: str | None
    """Derived missing-operator label (see :func:`_infer_missing_operator`)."""

    refusal_reason: str
    """ReaderRefusal.reason string verbatim."""

    refusal_detail: str
    """ReaderRefusal.detail string verbatim."""

    def as_tsv_row(self) -> str:
        """Single tab-separated line for the audit artifact."""
        terms = ", ".join(self.recognized_terms) if self.recognized_terms else "(none)"
        return "\t".join(
            [
                self.case_id,
                str(self.sentence_index),
                terms,
                self.skipped_frame or "(pre-frame)",
                self.missing_operator or "(unknown)",
                self.refusal_reason,
            ]
        )

    @staticmethod
    def tsv_header() -> str:
        return "\t".join(
            [
                "case_id",
                "sentence_index",
                "recognized_terms",
                "skipped_frame",
                "missing_operator",
                "refusal_reason",
            ]
        )


# ---------------------------------------------------------------------------
# Missing-operator inference
# ---------------------------------------------------------------------------

# Map refusal_reason + detail patterns → missing operator label.
# Ordered: first match wins.
_OPERATOR_INFERENCE_RULES: list[tuple[str, re.Pattern[str], str]] = [
    # Multi-quantity ops
    (
        "incomplete_operation",
        re.compile(r"multi-quantity", re.IGNORECASE),
        "multi_quantity_composition",
    ),
    # No-quantity operation frame
    (
        "incomplete_operation",
        re.compile(r"no quantity", re.IGNORECASE),
        "quantity_extraction",
    ),
    # Subject-dropped (no entity in operation/initial_state frame)
    (
        "incomplete_operation",
        re.compile(r"no subject entity", re.IGNORECASE),
        "subject_entity_recovery",
    ),
    # Unattached quantity
    (
        "unattached_quantity",
        re.compile(r"."),
        "unit_binding",
    ),
    # Compound numeric ("hundred", "million" etc.)
    (
        "unknown_word",
        re.compile(r"hundred|thousand|million|billion", re.IGNORECASE),
        "compound_numeric_literal",
    ),
    # Temporal compound ("one-hour", "two-day")
    (
        "unknown_word",
        re.compile(r"one-|two-|three-|four-|five-|six-|seven-|eight-|nine-|ten-", re.IGNORECASE),
        "compound_time_literal",
    ),
    # Generic unknown word (lexicon gap)
    (
        "unknown_word",
        re.compile(r"."),
        "lexicon_entry",
    ),
    # Fraction / percentage
    (
        "unexpected_category",
        re.compile(r"fraction|percentage", re.IGNORECASE),
        "fraction_percentage_literal",
    ),
    # Multi-subject sentence
    (
        "unexpected_category",
        re.compile(r"multi-subject|second entity", re.IGNORECASE),
        "multi_subject_sentence",
    ),
    # Unresolved pronoun
    (
        "unresolved_pronoun",
        re.compile(r"."),
        "pronoun_resolution",
    ),
    # Ambiguous pronoun
    (
        "ambiguous_pronoun_referent",
        re.compile(r"."),
        "pronoun_disambiguation",
    ),
    # No question target
    (
        "no_question_target",
        re.compile(r"."),
        "question_target_slot",
    ),
    # Graph construction failure
    (
        "graph_construction_failure",
        re.compile(r"."),
        "graph_construction",
    ),
    # Brief 11B: pre-frame statement_terminator — sentence ended without
    # opening any frame. May be context filler or a verb the reader cannot
    # admit yet. Distinct from multi_subject because no second entity.
    (
        "unexpected_category",
        re.compile(r"'statement_terminator'.*pre-frame", re.IGNORECASE),
        "pre_frame_filler_sentence",
    ),
    # Brief 11B: pre-frame "?" reached in a descriptive_frame — question
    # target slot was missed before the terminator arrived.
    (
        "unexpected_category",
        re.compile(r"'question_terminator'.*descriptive_frame", re.IGNORECASE),
        "descriptive_frame_question",
    ),
    # Brief 11B: question_frame opened but a required slot (e.g. unit_class)
    # never arrived. Labelled separately from generic incomplete_operation.
    (
        "incomplete_operation",
        re.compile(r"question_frame missing required slot", re.IGNORECASE),
        "question_frame_slot",
    ),
]


def _infer_missing_operator(reason: str, detail: str) -> str | None:
    """Infer the missing-operator label from a ReaderRefusal."""
    for target_reason, pattern, label in _OPERATOR_INFERENCE_RULES:
        if reason == target_reason and pattern.search(detail):
            return label
    return None


# ---------------------------------------------------------------------------
# Sentence splitter (minimal — matches the adapter's split logic)
# ---------------------------------------------------------------------------

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


def _split_sentences(text: str) -> list[str]:
    """Split problem text into sentences. Mirrors adapter behaviour."""
    return [s.strip() for s in _SENTENCE_SPLIT_RE.split(text.strip()) if s.strip()]


def _tokenise(sentence: str) -> list[str]:
    """Minimal whitespace tokeniser that preserves punctuation tokens."""
    tokens: list[str] = []
    for raw in sentence.split():
        # Strip leading/trailing punctuation but keep internal (e.g. "$3.50")
        stripped_left = raw.lstrip()
        # Separate trailing punctuation
        if stripped_left and stripped_left[-1] in ".!?,":
            body = stripped_left[:-1]
            tail = stripped_left[-1]
            if body:
                tokens.append(body)
            tokens.append(tail)
        else:
            if stripped_left:
                tokens.append(stripped_left)
    return tokens


# ---------------------------------------------------------------------------
# Core audit function
# ---------------------------------------------------------------------------


AuditResult = "MathProblemGraph | ReaderRefusal | None"


def audit_problem(
    problem_text: str,
    *,
    case_id: str = "unknown",
) -> tuple["AuditResult", list[AuditRow]]:
    """Run the Phase 2 reader over *problem_text* and return audit data.

    Returns
    -------
    result :
        ``MathProblemGraph`` on full admission,
        ``ReaderRefusal`` on the first refusal,
        ``None`` if the text produced no sentences.
    audit_rows :
        One :class:`AuditRow` per refusal encountered (at most one per sentence
        in the current single-refusal-stops-processing model).  On success,
        ``audit_rows`` is empty.
    """
    sentences = _split_sentences(problem_text)
    if not sentences:
        return None, []

    problem_state = ProblemReadingState(
        entity_registry=(),
        accumulated_initial_state=(),
        accumulated_operations=(),
        unknown_target_slot=None,
        pronoun_resolution_history=(),
        sentence_index=0,
        source_text_offset=0,
    )
    audit_rows: list[AuditRow] = []

    for sentence in sentences:
        tokens = _tokenise(sentence)
        sentence_state = begin_sentence(problem_state, source_text_offset=0)
        recognized: list[str] = []

        for word in tokens:
            result = apply_word(sentence_state, problem_state, word)
            if isinstance(result, ReaderRefusal):
                row = AuditRow(
                    case_id=case_id,
                    sentence_index=result.sentence_index,
                    token_index=result.token_index,
                    token_text=result.token_text,
                    recognized_terms=tuple(recognized),
                    skipped_frame=sentence_state.frame,
                    missing_operator=_infer_missing_operator(
                        result.reason, result.detail
                    ),
                    refusal_reason=result.reason,
                    refusal_detail=result.detail,
                )
                audit_rows.append(row)
                return result, audit_rows
            sentence_state = result
            recognized.append(word)

        end_result = end_sentence(sentence_state, problem_state)
        if isinstance(end_result, ReaderRefusal):
            row = AuditRow(
                case_id=case_id,
                sentence_index=end_result.sentence_index,
                token_index=end_result.token_index,
                token_text=end_result.token_text,
                recognized_terms=tuple(recognized),
                skipped_frame=sentence_state.frame,
                missing_operator=_infer_missing_operator(
                    end_result.reason, end_result.detail
                ),
                refusal_reason=end_result.reason,
                refusal_detail=end_result.detail,
            )
            audit_rows.append(row)
            return end_result, audit_rows
        problem_state = end_result

    graph_result = finalize(problem_state)
    if isinstance(graph_result, ReaderRefusal):
        row = AuditRow(
            case_id=case_id,
            sentence_index=graph_result.sentence_index,
            token_index=graph_result.token_index,
            token_text=graph_result.token_text,
            recognized_terms=(),
            skipped_frame=None,
            missing_operator=_infer_missing_operator(
                graph_result.reason, graph_result.detail
            ),
            refusal_reason=graph_result.reason,
            refusal_detail=graph_result.detail,
        )
        audit_rows.append(row)
        return graph_result, audit_rows

    return graph_result, audit_rows


# ---------------------------------------------------------------------------
# Graph completeness assertion
# ---------------------------------------------------------------------------


def assert_graph_complete(graph: "MathProblemGraph") -> None:
    """Assert structural completeness of a :class:`MathProblemGraph`.

    Checks (per Brief 11 Gate 3):

    1. At least one entity.
    2. At least one initial possession OR at least one operation.
    3. Every initial possession has a non-empty entity and a non-None quantity
       with a non-empty unit.
    4. Every operation has actor, kind, operand (with unit); transfer ops have
       a non-None target.
    5. Unknown has a non-empty entity (or None) and a non-empty unit.
    6. No entity name is empty or whitespace-only.

    Raises ``AssertionError`` with a descriptive message on the first failure.
    Does not return a value — callers should wrap in ``pytest.raises`` or a
    plain ``try/except`` depending on usage context.
    """
    # 1. Entities.
    assert graph.entities, "graph.entities is empty"
    for i, name in enumerate(graph.entities):
        assert name and name.strip(), f"graph.entities[{i}] is blank"

    # 2. At least some math content.
    assert graph.initial_state or graph.operations, (
        "graph has no initial_state and no operations"
    )

    # 3. Initial possessions.
    for i, ip in enumerate(graph.initial_state):
        assert ip.entity, f"initial_state[{i}].entity is blank"
        assert ip.quantity is not None, f"initial_state[{i}].quantity is None"
        assert ip.quantity.unit, f"initial_state[{i}].quantity.unit is blank"

    # 4. Operations.
    for i, op in enumerate(graph.operations):
        assert op.actor, f"operations[{i}].actor is blank"
        assert op.kind, f"operations[{i}].kind is blank"
        assert op.operand is not None, f"operations[{i}].operand is None"
        assert op.operand.unit, f"operations[{i}].operand.unit is blank"
        if op.kind == "transfer":
            assert op.target is not None, (
                f"operations[{i}] is a transfer but target is None"
            )

    # 5. Unknown.
    assert graph.unknown is not None, "graph.unknown is None"
    assert graph.unknown.unit, "graph.unknown.unit is blank"


__all__ = [
    "AuditRow",
    "assert_graph_complete",
    "audit_problem",
]
