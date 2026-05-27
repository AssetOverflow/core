"""ADR-0164 / ADR-0164.3 — incremental comprehension reader lifecycle.

Phase 1 scope: ``question_frame`` only. Statement-side frames
(``initial_state_frame``, ``operation_frame``, ``descriptive_frame``) are
Phase 2.

The three public functions are pure and deterministic:

* :func:`begin_sentence` opens a fresh sentence-local state.
* :func:`apply_word` advances one token; returns a new state or a typed
  :class:`ReaderRefusal`.
* :func:`end_sentence` projects the closed sentence into a new
  :class:`ProblemReadingState` (or refuses).

ADR-0164 §Decision §3 specifies the four-step token loop:

1. Lexeme primitive scan.
2. Lexicon lookup.
3. Expectation check.
4. Update emit.

Update rules live in :data:`_QUESTION_FRAME_RULES` as a single readable
table. The table's coverage is intentionally narrow — the five Brief-8
GSM8K target question sentences plus close variants. Adding a category is
either an entry in this table (mechanical) or a sub-ADR (semantic).
"""

from __future__ import annotations

from functools import cache
from typing import Callable, Final

from generate.comprehension._interface_stubs import (
    Lexicon,
    LexemeMatch,
    LexiconEntry,
    load_lexicon,
    lookup,
    scan_primitive,
)
from generate.comprehension.state import (
    _LOOKBACK_MAX,
    AppliedCategory,
    EntityRef,
    FramePayload,
    ProblemReadingState,
    QuestionTargetSlot,
    ReaderRefusal,
    SentenceReadingState,
    VerbReference,
)

# ---------------------------------------------------------------------------
# Cached lexicon — Brief 7's loader is the source of truth once it lands.
# ---------------------------------------------------------------------------


@cache
def _get_lexicon() -> Lexicon:
    return load_lexicon()


# ---------------------------------------------------------------------------
# Category groupings.
# ---------------------------------------------------------------------------

_QUESTION_OPENERS: Final[frozenset[str]] = frozenset({"question_open"})

_FRAME_CLOSING_VERBS: Final[frozenset[str]] = frozenset(
    {
        "accumulation_verb",
        "depletion_verb",
        "transfer_verb",
        "capacity_verb",
        "possession_verb",
        "copula_verb",
    }
)

# Map qualifier category → QuestionTargetSlot.kind.
_KIND_BY_QUALIFIER: Final[dict[str, str]] = {
    "question_continuous_qty": "continuous_quantity",
    "question_discrete_qty": "discrete_quantity",
    "question_comparative": "difference",
    "aggregate_modifier": "aggregate",
}

# Map unit category → unit_class string carried into QuestionTargetSlot.
_UNIT_CLASS_BY_CATEGORY: Final[dict[str, str]] = {
    "count_unit_noun": "count",
    "currency_unit_noun": "currency",
    "time_unit_noun": "time",
}

# Sentinel category recorded in the lookback once the question frame closes.
# After this marker lands, every further token drains into the lookback
# without further state mutation. The marker itself is filtered out of
# the lookback if it would exceed the bounded length.
_FRAME_CLOSED_MARKER: Final[str] = "_frame_closed"

_PRONOUN_GENDER: Final[dict[str, str]] = {
    "she": "female",
    "her": "female",
    "hers": "female",
    "he": "male",
    "him": "male",
    "his": "male",
    "it": "neuter",
    "they": "unknown",
    "them": "unknown",
    "their": "unknown",
}


# ---------------------------------------------------------------------------
# Internal helpers — all pure.
# ---------------------------------------------------------------------------


def _push_lookback(
    lookback: tuple[AppliedCategory, ...],
    category: str,
    position: int,
) -> tuple[AppliedCategory, ...]:
    """Append a new category to the bounded lookback window."""
    entry = AppliedCategory(category=category, position=position)
    combined = lookback + (entry,)
    if len(combined) > _LOOKBACK_MAX:
        combined = combined[-_LOOKBACK_MAX:]
    return combined


def _frame_closed(state: SentenceReadingState) -> bool:
    return any(ac.category == _FRAME_CLOSED_MARKER for ac in state.lookback)


def _resolve_pronoun(
    pronoun: str,
    registry: tuple[EntityRef, ...],
) -> tuple[str, ...] | None:
    """Return a tuple of canonical names compatible with the pronoun's gender.

    ``None`` means the pronoun's gender is not recognised. Empty tuple means
    no compatible entity in the registry. Multi-element means ambiguous;
    Phase 1 refuses on >1 candidates.

    The compatibility table is a Phase-1 subset of ADR-0164.2 §2.2:
    gender match by exact string; "unknown" gender entries are compatible
    with any pronoun gender (single-salient-entity case).
    """
    needed = _PRONOUN_GENDER.get(pronoun.lower())
    if needed is None:
        return None
    matches: list[str] = []
    for entity in registry:
        if entity.gender == needed or entity.gender == "unknown":
            matches.append(entity.canonical_name)
    return tuple(matches)


def _update_question_target(
    sentence_state: SentenceReadingState,
    *,
    kind: str | None = None,
    entity: str | None = None,
    unit_class: str | None = None,
    position: int | None = None,
) -> QuestionTargetSlot:
    """Build a new QuestionTargetSlot, falling back to existing values."""
    existing = sentence_state.question_target
    new_kind = kind if kind is not None else (
        existing.kind if existing is not None else "continuous_quantity"
    )
    new_entity = entity if entity is not None else (
        existing.entity if existing is not None else None
    )
    new_unit_class = unit_class if unit_class is not None else (
        existing.unit_class if existing is not None else None
    )
    new_position = position if position is not None else (
        existing.position if existing is not None else 0
    )
    return QuestionTargetSlot(
        kind=new_kind,
        entity=new_entity,
        unit_class=new_unit_class,
        position=new_position,
    )


# ---------------------------------------------------------------------------
# Lifecycle API.
# ---------------------------------------------------------------------------


def begin_sentence(
    problem_state: ProblemReadingState,
    source_text_offset: int,
) -> SentenceReadingState:
    """Open a fresh sentence-local state.

    Per ADR-0164.3 §Lifecycle API. ``sentence_index`` is *not* incremented
    here — ``end_sentence`` owns the increment. ``source_text_offset`` is
    accepted for parity with the spec; the sentence state itself doesn't
    carry it (it lives on ``ProblemReadingState`` and advances at
    ``end_sentence``).
    """
    if not isinstance(problem_state, ProblemReadingState):
        raise TypeError(
            "begin_sentence: problem_state must be ProblemReadingState; "
            f"got {type(problem_state).__name__}"
        )
    if not isinstance(source_text_offset, int) or source_text_offset < 0:
        raise ValueError(
            "begin_sentence: source_text_offset must be a non-negative int; "
            f"got {source_text_offset!r}"
        )
    return SentenceReadingState(
        entities=(),
        quantities=(),
        operations=(),
        question_target=None,
        expectation=None,
        frame=None,
        pending_quantities=(),
        pending_entity_ref=None,
        pending_verb=None,
        token_index=0,
        lookback=(),
        partial_frame_payload=None,
    )


def apply_word(
    sentence_state: SentenceReadingState,
    problem_state: ProblemReadingState,
    word: str,
) -> SentenceReadingState | ReaderRefusal:
    """Advance the reader by one token. Pure / deterministic.

    See module docstring for the four-step contract. The Phase-1 update
    rules apply only to the ``question_frame``; opening any other frame at
    position 0 refuses with ``unexpected_category`` carrying a Phase-2
    diagnostic.
    """
    if not isinstance(word, str) or word == "":
        return ReaderRefusal(
            reason="unknown_word",
            detail="apply_word called with empty/non-string word",
            sentence_index=problem_state.sentence_index,
            token_index=sentence_state.token_index,
            token_text="" if not isinstance(word, str) else word,
        )

    position = sentence_state.token_index
    sentence_idx = problem_state.sentence_index

    # Step 1 + 2 — primitive scan, then lexicon lookup.
    category, _surface = _classify(word)

    # Step 3 + 4 — expectation + update emit.
    # Once the frame is closed, every token drains: classified ones keep
    # their category in the lookback; unknowns drain as
    # ``unknown_remainder`` so downstream consumers can still see them.
    if _frame_closed(sentence_state):
        return _advance(
            sentence_state,
            category=category if category is not None else "unknown_remainder",
        )

    if category is None:
        return ReaderRefusal(
            reason="unknown_word",
            detail=f"no primitive or lexicon match for {word!r}",
            sentence_index=sentence_idx,
            token_index=position,
            token_text=word,
        )

    # Pure-drain categories at any stage (punctuation, articles, etc.).
    if category in {"drain_token", "punctuation_comma"}:
        return _advance(sentence_state, category=category)

    # Phase-1 scope check at position 0.
    if sentence_state.frame is None and category not in _QUESTION_OPENERS:
        return ReaderRefusal(
            reason="unexpected_category",
            detail=(
                f"non-question frame at position 0 is Phase-2 scope "
                f"(saw category={category!r}, word={word!r})"
            ),
            sentence_index=sentence_idx,
            token_index=position,
            token_text=word,
        )

    # Dispatch the rule table.
    handler = _QUESTION_FRAME_RULES.get(category, _rule_default_refuse)
    return handler(
        sentence_state=sentence_state,
        problem_state=problem_state,
        category=category,
        word=word,
    )


def end_sentence(
    sentence_state: SentenceReadingState,
    problem_state: ProblemReadingState,
) -> ProblemReadingState | ReaderRefusal:
    """Close the sentence and fold it into a new ``ProblemReadingState``.

    Validation order matches ADR-0164.3 §Lifecycle API:

    1. ``sentence_state.frame`` must be a legal frame kind.
    2. ``sentence_state.pending_quantities`` must be empty.
    3. If frame is ``question_frame``: target slot must have unit_class
       AND a non-default kind set; otherwise ``incomplete_operation``.
    4. Project payload → ``problem_state.unknown_target_slot`` (locked
       if already set, refusing).
    5. Append any sentence-introduced entities, fold pronoun resolutions
       into the history, increment ``sentence_index``, advance offset.
    """
    sentence_idx = problem_state.sentence_index
    last_position = max(sentence_state.token_index - 1, 0)

    if sentence_state.frame is None:
        return ReaderRefusal(
            reason="unfinished_frame",
            detail="sentence ended without a frame being decided",
            sentence_index=sentence_idx,
            token_index=last_position,
            token_text="",
        )

    if sentence_state.pending_quantities:
        return ReaderRefusal(
            reason="unattached_quantity",
            detail=(
                f"{len(sentence_state.pending_quantities)} quantities never "
                "attached to entity+unit at sentence end"
            ),
            sentence_index=sentence_idx,
            token_index=last_position,
            token_text="",
        )

    if sentence_state.frame == "question_frame":
        target = sentence_state.question_target
        if target is None:
            return ReaderRefusal(
                reason="incomplete_operation",
                detail="question_frame closed with no QuestionTargetSlot",
                sentence_index=sentence_idx,
                token_index=last_position,
                token_text="",
            )
        missing: list[str] = []
        if target.unit_class is None:
            missing.append("unit_class")
        # question_form is encoded in kind; "continuous_quantity" is the
        # default at first qualifier — accept any of the four valid kinds.
        if missing:
            return ReaderRefusal(
                reason="incomplete_operation",
                detail=(
                    "question_frame missing required slot(s): "
                    + ", ".join(missing)
                ),
                sentence_index=sentence_idx,
                token_index=last_position,
                token_text="",
            )

        # Commit unknown_target_slot. Lock-on-set: refuse if already set.
        if problem_state.unknown_target_slot is not None:
            return ReaderRefusal(
                reason="incomplete_operation",
                detail=(
                    "problem already has unknown_target_slot set; "
                    "second question sentence rejected"
                ),
                sentence_index=sentence_idx,
                token_index=last_position,
                token_text="",
            )
        new_unknown = target
    else:
        new_unknown = problem_state.unknown_target_slot

    # Carry the sentence-introduced entities into the registry. Phase 1
    # only introduces an entity via pending_entity_ref (subject/proper
    # noun); pronoun resolutions do NOT introduce new entries.
    new_registry = problem_state.entity_registry
    if sentence_state.pending_entity_ref is not None:
        existing_names = {e.canonical_name for e in new_registry}
        candidate = sentence_state.pending_entity_ref
        if candidate.canonical_name not in existing_names:
            new_registry = new_registry + (candidate,)

    # Pronoun resolutions recorded in lookback via "_pronoun_resolved:<name>"
    # sentinels are not persisted to history here (Phase 1 keeps the
    # discipline minimal). The history fold is a Phase-2 sub-ADR; this
    # PR preserves the history field untouched on success.
    return ProblemReadingState(
        entity_registry=new_registry,
        accumulated_initial_state=problem_state.accumulated_initial_state,
        accumulated_operations=problem_state.accumulated_operations,
        unknown_target_slot=new_unknown,
        pronoun_resolution_history=problem_state.pronoun_resolution_history,
        sentence_index=problem_state.sentence_index + 1,
        source_text_offset=problem_state.source_text_offset
        + max(sentence_state.token_index, 1),
    )


# ---------------------------------------------------------------------------
# Step 1 + 2 — classification.
# ---------------------------------------------------------------------------


def _classify(word: str) -> tuple[str | None, str]:
    """Return (category, surface). Category is None on miss."""
    # 1. Primitive scan first (orthographic shapes are unambiguous).
    primitive: LexemeMatch | None = scan_primitive(word)
    if primitive is not None:
        return primitive.emit_category, primitive.surface
    # 2. Lexicon lookup.
    lex = _get_lexicon()
    entry: LexiconEntry | None = lookup(lex, word)
    if entry is not None:
        return entry.category, entry.surface
    return None, word


# ---------------------------------------------------------------------------
# Update-rule handlers.
# Each handler signature: keyword-only sentence_state, problem_state,
# category, word. Returns a new SentenceReadingState or a ReaderRefusal.
# ---------------------------------------------------------------------------


def _advance(
    sentence_state: SentenceReadingState,
    *,
    category: str,
    **changes,
) -> SentenceReadingState:
    """Replace the sentence state with token_index+1 and lookback push."""
    position = sentence_state.token_index
    next_lookback = _push_lookback(
        sentence_state.lookback, category, position
    )
    base = {
        "entities": sentence_state.entities,
        "quantities": sentence_state.quantities,
        "operations": sentence_state.operations,
        "question_target": sentence_state.question_target,
        "expectation": sentence_state.expectation,
        "frame": sentence_state.frame,
        "pending_quantities": sentence_state.pending_quantities,
        "pending_entity_ref": sentence_state.pending_entity_ref,
        "pending_verb": sentence_state.pending_verb,
        "token_index": position + 1,
        "lookback": next_lookback,
        "partial_frame_payload": sentence_state.partial_frame_payload,
    }
    base.update(changes)
    return SentenceReadingState(**base)


def _rule_question_open(
    *,
    sentence_state: SentenceReadingState,
    problem_state: ProblemReadingState,
    category: str,
    word: str,
) -> SentenceReadingState | ReaderRefusal:
    """Rule: opening word ('How', 'What') begins a question_frame.

    Only legal at position 0 (or after a punctuation token; Phase 1
    restricts to position 0 since within-sentence multi-clause is
    Phase 2 scope).
    """
    if sentence_state.frame is not None:
        return ReaderRefusal(
            reason="unexpected_category",
            detail=f"question_open at non-opening position {sentence_state.token_index}",
            sentence_index=problem_state.sentence_index,
            token_index=sentence_state.token_index,
            token_text=word,
        )
    return _advance(
        sentence_state,
        category=category,
        frame="question_frame",
        partial_frame_payload=FramePayload(frame_kind="question_frame"),
    )


def _rule_qty_qualifier(
    *,
    sentence_state: SentenceReadingState,
    problem_state: ProblemReadingState,
    category: str,
    word: str,
) -> SentenceReadingState | ReaderRefusal:
    """Rule: 'many'/'much'/'more'/'less'/'longer'/'total'/'combined'."""
    if sentence_state.frame != "question_frame":
        return ReaderRefusal(
            reason="unexpected_category",
            detail=f"{category} outside question_frame",
            sentence_index=problem_state.sentence_index,
            token_index=sentence_state.token_index,
            token_text=word,
        )
    kind = _KIND_BY_QUALIFIER[category]
    new_target = _update_question_target(
        sentence_state, kind=kind, position=sentence_state.token_index
    )
    return _advance(
        sentence_state,
        category=category,
        question_target=new_target,
    )


def _rule_unit_noun(
    *,
    sentence_state: SentenceReadingState,
    problem_state: ProblemReadingState,
    category: str,
    word: str,
) -> SentenceReadingState | ReaderRefusal:
    """Rule: count/currency/time unit noun sets ``unit_class``."""
    if sentence_state.frame != "question_frame":
        return ReaderRefusal(
            reason="unexpected_category",
            detail=f"{category} outside question_frame",
            sentence_index=problem_state.sentence_index,
            token_index=sentence_state.token_index,
            token_text=word,
        )
    unit_class = _UNIT_CLASS_BY_CATEGORY[category]
    new_target = _update_question_target(sentence_state, unit_class=unit_class)
    return _advance(
        sentence_state,
        category=category,
        question_target=new_target,
    )


def _rule_modal_aux(
    *,
    sentence_state: SentenceReadingState,
    problem_state: ProblemReadingState,
    category: str,
    word: str,
) -> SentenceReadingState | ReaderRefusal:
    if sentence_state.frame != "question_frame":
        return ReaderRefusal(
            reason="unexpected_category",
            detail="modal_aux outside question_frame",
            sentence_index=problem_state.sentence_index,
            token_index=sentence_state.token_index,
            token_text=word,
        )
    return _advance(sentence_state, category=category)


def _rule_entity_pronoun(
    *,
    sentence_state: SentenceReadingState,
    problem_state: ProblemReadingState,
    category: str,
    word: str,
) -> SentenceReadingState | ReaderRefusal:
    """Rule: resolve against ``problem_state.entity_registry`` per ADR-0164.2."""
    if sentence_state.frame != "question_frame":
        return ReaderRefusal(
            reason="unexpected_category",
            detail="entity_pronoun outside question_frame",
            sentence_index=problem_state.sentence_index,
            token_index=sentence_state.token_index,
            token_text=word,
        )
    candidates = _resolve_pronoun(word, problem_state.entity_registry)
    if candidates is None or len(candidates) == 0:
        return ReaderRefusal(
            reason="unresolved_pronoun",
            detail=(
                f"pronoun {word!r} has no compatible entity in registry "
                f"(size={len(problem_state.entity_registry)})"
            ),
            sentence_index=problem_state.sentence_index,
            token_index=sentence_state.token_index,
            token_text=word,
        )
    if len(candidates) > 1:
        return ReaderRefusal(
            reason="ambiguous_pronoun_referent",
            detail=(
                f"pronoun {word!r} matches >1 entity: "
                + ", ".join(candidates)
            ),
            sentence_index=problem_state.sentence_index,
            token_index=sentence_state.token_index,
            token_text=word,
        )
    resolved = candidates[0]
    new_target = _update_question_target(sentence_state, entity=resolved)
    return _advance(
        sentence_state,
        category=category,
        question_target=new_target,
    )


def _rule_proper_noun(
    *,
    sentence_state: SentenceReadingState,
    problem_state: ProblemReadingState,
    category: str,
    word: str,
) -> SentenceReadingState | ReaderRefusal:
    if sentence_state.frame != "question_frame":
        return ReaderRefusal(
            reason="unexpected_category",
            detail="proper_noun outside question_frame",
            sentence_index=problem_state.sentence_index,
            token_index=sentence_state.token_index,
            token_text=word,
        )
    canonical = word.lower()
    gender = (
        "female"
        if category == "proper_noun_entity_female"
        else "male"
    )
    pending = EntityRef(
        canonical_name=canonical,
        gender=gender,
        first_mention_position=sentence_state.token_index,
    )
    new_target = _update_question_target(sentence_state, entity=canonical)
    return _advance(
        sentence_state,
        category=category,
        pending_entity_ref=pending,
        question_target=new_target,
    )


def _rule_residual_modifier(
    *,
    sentence_state: SentenceReadingState,
    problem_state: ProblemReadingState,  # noqa: ARG001
    category: str,
    word: str,  # noqa: ARG001
) -> SentenceReadingState | ReaderRefusal:
    """Rule: 'left'/'remaining'/'after' modify residual semantics.

    QuestionTargetSlot.kind has no 'residual' literal; Phase 1 keeps the
    current kind (typically continuous_quantity / difference) and records
    the residual marker in the lookback for downstream consumers.
    """
    if sentence_state.frame != "question_frame":
        # Outside the frame these are drain tokens.
        return _advance(sentence_state, category="drain_token")
    return _advance(sentence_state, category=category)


def _rule_frame_closer(
    *,
    sentence_state: SentenceReadingState,
    problem_state: ProblemReadingState,
    category: str,
    word: str,
) -> SentenceReadingState | ReaderRefusal:
    """Rule: verb or '?' closes the question frame."""
    if sentence_state.frame != "question_frame":
        return ReaderRefusal(
            reason="unexpected_category",
            detail=f"{category} outside question_frame at position 0 is Phase-2 scope",
            sentence_index=problem_state.sentence_index,
            token_index=sentence_state.token_index,
            token_text=word,
        )
    pending_verb = sentence_state.pending_verb
    if category in _FRAME_CLOSING_VERBS:
        pending_verb = VerbReference(
            surface=word.lower(), kind=category, position=sentence_state.token_index
        )
    # First push the category, then the close marker, so trace order is
    # preserved.
    intermediate = _advance(sentence_state, category=category, pending_verb=pending_verb)
    closed_lookback = _push_lookback(
        intermediate.lookback,
        _FRAME_CLOSED_MARKER,
        intermediate.token_index - 1,
    )
    return SentenceReadingState(
        entities=intermediate.entities,
        quantities=intermediate.quantities,
        operations=intermediate.operations,
        question_target=intermediate.question_target,
        expectation=intermediate.expectation,
        frame=intermediate.frame,
        pending_quantities=intermediate.pending_quantities,
        pending_entity_ref=intermediate.pending_entity_ref,
        pending_verb=intermediate.pending_verb,
        token_index=intermediate.token_index,
        lookback=closed_lookback,
        partial_frame_payload=intermediate.partial_frame_payload,
    )


def _rule_default_refuse(
    *,
    sentence_state: SentenceReadingState,
    problem_state: ProblemReadingState,
    category: str,
    word: str,
) -> ReaderRefusal:
    return ReaderRefusal(
        reason="unexpected_category",
        detail=f"category {category!r} not handled by Phase-1 question_frame rules",
        sentence_index=problem_state.sentence_index,
        token_index=sentence_state.token_index,
        token_text=word,
    )


# ---------------------------------------------------------------------------
# Phase-1 question_frame rule table.
# Each entry: category → handler. New categories belong here, not in a
# different module.
# ---------------------------------------------------------------------------

_Handler = Callable[..., "SentenceReadingState | ReaderRefusal"]

_QUESTION_FRAME_RULES: Final[dict[str, _Handler]] = {
    # Openers
    "question_open": _rule_question_open,
    # Quantifiers / comparatives / aggregate
    "question_continuous_qty": _rule_qty_qualifier,
    "question_discrete_qty": _rule_qty_qualifier,
    "question_comparative": _rule_qty_qualifier,
    "aggregate_modifier": _rule_qty_qualifier,
    # Unit nouns
    "count_unit_noun": _rule_unit_noun,
    "currency_unit_noun": _rule_unit_noun,
    "time_unit_noun": _rule_unit_noun,
    # Pivots
    "modal_aux": _rule_modal_aux,
    "entity_pronoun": _rule_entity_pronoun,
    "proper_noun_entity_female": _rule_proper_noun,
    "proper_noun_entity_male": _rule_proper_noun,
    # Residual marker
    "residual_modifier": _rule_residual_modifier,
    # Frame closers
    "accumulation_verb": _rule_frame_closer,
    "depletion_verb": _rule_frame_closer,
    "transfer_verb": _rule_frame_closer,
    "capacity_verb": _rule_frame_closer,
    "possession_verb": _rule_frame_closer,
    "copula_verb": _rule_frame_closer,
    "question_terminator": _rule_frame_closer,
}


__all__ = [
    "apply_word",
    "begin_sentence",
    "end_sentence",
]
