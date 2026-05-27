"""ADR-0164 Phase 1 — bridge from regex-parser candidates to reader state.

Converts CandidateInitial / SentenceChoice tuples produced by the existing
regex parser into a ProblemReadingState that the comprehension reader can
consume for question-sentence processing.

This module is the only place where the Phase 1 coexistence wiring knows
about both worlds simultaneously.  It is intentionally a stopgap: Phase 3
(per ADR-0164 §Phasing Phase 3) removes the regex question parser entirely,
at which point this adapter either shrinks to a pure statement-candidate
helper or is deleted.

All public functions are pure and deterministic (same inputs → same outputs,
no I/O, no global state mutation).
"""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, Final, Union

from generate.comprehension.lifecycle import (
    _classify,
    _get_lexicon,
    apply_word,
    begin_sentence,
    end_sentence,
)
from generate.comprehension.state import (
    EntityRef,
    PartialInitialPossession,
    PartialOperation,
    ProblemReadingState,
    QuestionTargetSlot,
    QuantityRef,
    ReaderRefusal,
    SentenceReadingState,
)

if TYPE_CHECKING:
    from generate.math_candidate_parser import CandidateInitial
    from generate.math_roundtrip import CandidateOperation

# Union type for statement-sentence choices (mirrors math_candidate_graph).
SentenceChoice = Union["CandidateInitial", "CandidateOperation"]

# ---------------------------------------------------------------------------
# Gender inference via lexicon
# ---------------------------------------------------------------------------

_FEMALE_CATEGORIES: Final[frozenset[str]] = frozenset({"proper_noun_entity_female"})
_MALE_CATEGORIES: Final[frozenset[str]] = frozenset({"proper_noun_entity_male"})

_UNIT_CLASS_CATEGORIES: Final[dict[str, str]] = {
    "count_unit_noun": "count",
    "currency_unit_noun": "currency",
    "time_unit_noun": "time",
}


def _infer_gender(entity_name: str) -> str:
    """Return 'female', 'male', or 'unknown' for a proper-noun entity.

    Consults the en_core_math_v1 lexicon (via the lifecycle's cached loader)
    per ADR-0164.2 gender-inference policy.  Defaults to 'unknown' when the
    name is absent from the lexicon.
    """
    lex = _get_lexicon()
    key = entity_name.lower()
    entry = lex.get(key)
    if entry is None:
        return "unknown"
    if entry.category in _FEMALE_CATEGORIES:
        return "female"
    if entry.category in _MALE_CATEGORIES:
        return "male"
    return "unknown"


# ---------------------------------------------------------------------------
# Build ProblemReadingState from regex-parser output
# ---------------------------------------------------------------------------

def build_problem_state_from_candidates(
    statement_choices: list[SentenceChoice],
    statement_sentence_count: int,
) -> ProblemReadingState:
    """Convert regex-parser output into a ProblemReadingState for reader consumption.

    Args:
        statement_choices: Admissible CandidateInitial / CandidateOperation
            tuples produced by the existing regex parser, in source-text order.
        statement_sentence_count: Number of statement sentences already
            processed (sets ``ProblemReadingState.sentence_index``).

    Returns:
        A ProblemReadingState with entity_registry, accumulated_initial_state,
        and accumulated_operations populated from the candidates.
        unknown_target_slot is None (the question hasn't been processed yet).

    This function is the glue layer for Phase 1 coexistence.  It does NOT
    attempt to reproduce the reader's full incremental behaviour for statement
    sentences — that is Phase 2 scope.  It produces only what the reader's
    pronoun-resolution step needs: an ordered entity registry.
    """
    from generate.math_candidate_parser import CandidateInitial as _CI
    from generate.math_roundtrip import CandidateOperation as _CO

    entity_registry: list[EntityRef] = []
    seen_names: set[str] = set()
    accumulated_initials: list[PartialInitialPossession] = []
    accumulated_ops: list[PartialOperation] = []

    char_offset = 0
    for choice in statement_choices:
        if isinstance(choice, _CI):
            entity_name = choice.initial.entity
            if entity_name not in seen_names:
                gender = _infer_gender(entity_name)
                entity_registry.append(
                    EntityRef(
                        canonical_name=entity_name,
                        gender=gender,
                        first_mention_position=len(seen_names),
                    )
                )
                seen_names.add(entity_name)
            # Convert InitialPossession to PartialInitialPossession
            from decimal import Decimal
            qty_val = choice.initial.quantity.value
            qty = QuantityRef(
                value=Decimal(str(qty_val)),
                unit=choice.initial.quantity.unit,
                unit_class=None,
                owner_entity=entity_name,
                mention_position=len(accumulated_initials),
            )
            accumulated_initials.append(
                PartialInitialPossession(entity=entity_name, quantity=qty)
            )
        elif isinstance(choice, _CO):
            actor = choice.op.actor
            if actor not in seen_names:
                gender = _infer_gender(actor)
                entity_registry.append(
                    EntityRef(
                        canonical_name=actor,
                        gender=gender,
                        first_mention_position=len(seen_names),
                    )
                )
                seen_names.add(actor)
            if choice.op.target is not None and choice.op.target not in seen_names:
                tgt = choice.op.target
                gender_t = _infer_gender(tgt)
                entity_registry.append(
                    EntityRef(
                        canonical_name=tgt,
                        gender=gender_t,
                        first_mention_position=len(seen_names),
                    )
                )
                seen_names.add(tgt)
            # Operand — may be Quantity or Comparison; only carry scalar Quantity
            from generate.math_problem_graph import Quantity
            operand_ref: QuantityRef | None = None
            if hasattr(choice.op, "operand") and isinstance(choice.op.operand, Quantity):
                from decimal import Decimal
                operand_ref = QuantityRef(
                    value=Decimal(str(choice.op.operand.value)),
                    unit=choice.op.operand.unit,
                    unit_class=None,
                    owner_entity=actor,
                    mention_position=len(accumulated_ops),
                )
            accumulated_ops.append(
                PartialOperation(
                    actor=actor,
                    kind=choice.op.kind,
                    operand=operand_ref,
                    target=choice.op.target,
                )
            )

    return ProblemReadingState(
        entity_registry=tuple(entity_registry),
        accumulated_initial_state=tuple(accumulated_initials),
        accumulated_operations=tuple(accumulated_ops),
        unknown_target_slot=None,
        pronoun_resolution_history=(),
        sentence_index=statement_sentence_count,
        source_text_offset=char_offset,
    )


# ---------------------------------------------------------------------------
# Tokenisation (matches the reader's apply_word loop convention)
# ---------------------------------------------------------------------------

_TOKEN_SPLIT_RE: Final[re.Pattern[str]] = re.compile(r"\s+")
_PUNCT_STRIP_RE: Final[re.Pattern[str]] = re.compile(r"^[\"'()\[\]{}<>]+|[\"'()\[\]{}<>]+$")


def _tokenise_sentence(sentence: str) -> list[str]:
    """Split a sentence into tokens, emitting punctuation as separate tokens.

    Trailing ``?`` and ``.`` become their own token (matched by primitive scanner
    as ``question_terminator`` / ``statement_terminator``).  Leading/trailing
    matched-pair punctuation is stripped per word.  Empty strings are dropped.
    """
    tokens: list[str] = []
    for raw in _TOKEN_SPLIT_RE.split(sentence.strip()):
        if not raw:
            continue
        # Separate a trailing '?' or '.' from the word body.
        if len(raw) > 1 and raw[-1] in "?.!":
            body = raw[:-1]
            tail = raw[-1]
        else:
            body = raw
            tail = None
        body = _PUNCT_STRIP_RE.sub("", body)
        if body:
            tokens.append(body)
        if tail:
            tokens.append(tail)
    return tokens


# ---------------------------------------------------------------------------
# Unit extraction from question sentence
# ---------------------------------------------------------------------------

def _extract_unit_from_question(question_sentence: str, unit_class: str) -> str | None:
    """Scan question tokens for a unit-noun surface word matching ``unit_class``.

    After the reader produces a QuestionTargetSlot with unit_class set, this
    helper re-tokenises the question to find the specific unit word.  This lets
    the projected Unknown carry the actual unit string (e.g. 'apples') rather
    than the abstract class ('count'), maximising match probability against
    statement candidates' unit strings.

    Returns the canonicalised unit string, or None when no unit noun is found
    with the expected class.
    """
    from generate.math_candidate_parser import _canonicalize_unit  # type: ignore[attr-defined]
    target_categories = {
        "count": frozenset({"count_unit_noun"}),
        "currency": frozenset({"currency_unit_noun"}),
        "time": frozenset({"time_unit_noun"}),
    }.get(unit_class, frozenset())
    if not target_categories:
        return None
    for tok in _tokenise_sentence(question_sentence):
        cat, _surface = _classify(tok)
        if cat in target_categories:
            return _canonicalize_unit(tok)
    return None


# ---------------------------------------------------------------------------
# Run the reader over a question sentence
# ---------------------------------------------------------------------------

def invoke_reader_for_question(
    question_sentence: str,
    problem_state: ProblemReadingState,
) -> tuple[QuestionTargetSlot, str] | ReaderRefusal:
    """Run the Phase-1 reader over one question sentence.

    Returns:
        On success: ``(QuestionTargetSlot, canonical_unit)`` where
        ``canonical_unit`` is the actual unit string extracted from the
        question tokens (may differ from ``slot.unit_class``).
        On refusal: ``ReaderRefusal``.

    The caller is responsible for wrapping the result in a CandidateUnknown
    and for emitting the trace event.
    """
    tokens = _tokenise_sentence(question_sentence)
    sentence_state: SentenceReadingState = begin_sentence(
        problem_state, source_text_offset=problem_state.source_text_offset
    )
    for tok in tokens:
        result = apply_word(sentence_state, problem_state, tok)
        if isinstance(result, ReaderRefusal):
            return result
        sentence_state = result

    end_result = end_sentence(sentence_state, problem_state)
    if isinstance(end_result, ReaderRefusal):
        return end_result

    # end_sentence succeeded — extract QuestionTargetSlot from the new
    # problem_state (it was just committed as unknown_target_slot).
    slot = end_result.unknown_target_slot
    if slot is None:
        return ReaderRefusal(
            reason="no_question_target",
            detail="end_sentence succeeded but no unknown_target_slot set",
            sentence_index=problem_state.sentence_index,
            token_index=len(tokens),
            token_text="",
        )

    # Extract the canonical unit string from the question surface.
    unit_class = slot.unit_class or "unknown"
    canonical_unit = _extract_unit_from_question(question_sentence, unit_class)
    if canonical_unit is None:
        # Fall back to unit_class as the unit string per ADR-0164 Brief-9 spec.
        canonical_unit = unit_class

    return slot, canonical_unit


# ---------------------------------------------------------------------------
# Project QuestionTargetSlot → CandidateUnknown
# ---------------------------------------------------------------------------

def project_to_candidate_unknown(
    slot: QuestionTargetSlot,
    canonical_unit: str,
    question_sentence: str,
    problem_state: ProblemReadingState,
) -> "CandidateUnknown | None":  # type: ignore[name-defined]
    """Convert a QuestionTargetSlot into a CandidateUnknown for the candidate graph.

    Returns None if the projection would produce an invalid Unknown (e.g., the
    entity is set but not in the problem_state entity registry, which would
    cause _build_graph to reject it).

    Modifier flags (aggregate, comparative, residual) from the reader's
    lookback are not threaded into Unknown (Unknown has only entity + unit
    fields per ADR-0115).  Deferral documented here; a follow-up ADR will
    extend BoundUnknown resolution to consume these flags via side-channel.
    """
    from generate.math_candidate_parser import CandidateUnknown, _canonicalize_unit
    from generate.math_problem_graph import Unknown

    entity: str | None = slot.entity
    # Validate entity against the registry when set.
    if entity is not None:
        known = {e.canonical_name for e in problem_state.entity_registry}
        if entity not in known:
            return None

    matched_unit_token = canonical_unit
    matched_entity_token = entity

    try:
        unknown = Unknown(entity=entity, unit=canonical_unit)
    except Exception:
        return None

    try:
        return CandidateUnknown(
            unknown=unknown,
            source_span=question_sentence,
            matched_unit_token=matched_unit_token,
            matched_entity_token=matched_entity_token,
        )
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Trace-event construction
# ---------------------------------------------------------------------------

def make_admit_trace_event(
    slot: QuestionTargetSlot,
    canonical_unit: str,
) -> str:
    """Build a JSON-encoded admit trace event for the reader."""
    return json.dumps(
        {
            "layer": "comprehension_reader",
            "phase": 1,
            "outcome": "admit",
            "entity": slot.entity,
            "unit": canonical_unit,
            "question_form": slot.kind,
        },
        sort_keys=True,
        separators=(",", ":"),
    )


def make_fallthrough_trace_event(refusal: ReaderRefusal) -> str:
    """Build a JSON-encoded fallthrough trace event for the reader."""
    return json.dumps(
        {
            "layer": "comprehension_reader",
            "phase": 1,
            "outcome": "fallthrough_to_regex",
            "refusal_reason": refusal.reason,
            "refusal_token": refusal.token_text,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
