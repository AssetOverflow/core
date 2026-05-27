"""ADR-0164 / ADR-0164.3 — incremental comprehension reader lifecycle.

Phase 1 scope: ``question_frame`` only.
Phase 2 scope: ``initial_state_frame``, ``operation_frame``,
``descriptive_frame``, plus ``finalize()`` projection to
:class:`~generate.math_problem_graph.MathProblemGraph`.

The four public functions are pure and deterministic:

* :func:`begin_sentence` opens a fresh sentence-local state.
* :func:`apply_word` advances one token; returns a new state or a typed
  :class:`ReaderRefusal`.
* :func:`end_sentence` projects the closed sentence into a new
  :class:`ProblemReadingState` (or refuses).
* :func:`finalize` projects the finished :class:`ProblemReadingState`
  into a :class:`~generate.math_problem_graph.MathProblemGraph` (or refuses).

ADR-0164 §Decision §3 specifies the four-step token loop:

1. Lexeme primitive scan.
2. Lexicon lookup.
3. Expectation check.
4. Update emit.
"""

from __future__ import annotations

from decimal import Decimal
from functools import cache
from typing import Callable, Final, Literal

from generate.comprehension.lexeme_primitives import LexemeMatch, scan
from generate.comprehension.lexicon import Lexicon, LexiconEntry, load_lexicon, lookup
from generate.comprehension.state import (
    _LOOKBACK_MAX,
    AppliedCategory,
    EntityRef,
    FramePayload,
    PartialInitialPossession,
    PartialOperation,
    ProblemReadingState,
    QuantityRef,
    QuestionTargetSlot,
    ReaderRefusal,
    SentenceReadingState,
    VerbReference,
)

# ---------------------------------------------------------------------------
# Cached lexicon.
# ---------------------------------------------------------------------------


@cache
def _get_lexicon() -> Lexicon:
    return load_lexicon()


# ---------------------------------------------------------------------------
# Category groupings and mapping tables.
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

# Verb categories that determine the statement frame at pre-frame position.
_VERB_TO_FRAME: Final[dict[str, str]] = {
    "possession_verb": "initial_state_frame",
    "accumulation_verb": "operation_frame",
    "depletion_verb": "operation_frame",
    "transfer_verb": "operation_frame",
    "capacity_verb": "operation_frame",
    "copula_verb": "descriptive_frame",
}

# Verb category → Operation.kind for operation_frame.
# possession_verb is excluded — it produces an InitialPossession, not an Operation.
_VERB_CATEGORY_TO_OP_KIND: Final[dict[str, str]] = {
    "accumulation_verb": "add",
    "depletion_verb": "subtract",
    "transfer_verb": "transfer",
    "capacity_verb": "add",
}

# Map qualifier category → QuestionTargetSlot.kind.
_KIND_BY_QUALIFIER: Final[dict[str, str]] = {
    "question_continuous_qty": "continuous_quantity",
    "question_discrete_qty": "discrete_quantity",
    "question_comparative": "difference",
    "aggregate_modifier": "aggregate",
}

# Map unit category → unit_class string.
_UNIT_CLASS_BY_CATEGORY: Final[dict[str, str]] = {
    "count_unit_noun": "count",
    "currency_unit_noun": "currency",
    "time_unit_noun": "time",
}

# Map primitive_name → semantic category used internally.
_PRIMITIVE_CATEGORY_MAP: Final[dict[str, str]] = {
    "decimal-currency-literal": "currency_quantity",
    "currency-literal": "currency_quantity",
    "numeric-literal": "count_quantity",
    "time-amount-literal": "time_quantity",
    "ordinal-literal": "ordinal_token",
    "fraction-literal": "fraction_token",
    "percentage-literal": "percentage_token",
    "mass-noun-token": "mass_noun_token",
}

# Internal category produced by "UNIT_CATEGORY_TOKEN" emit (mass-noun-token).
_UNIT_CATEGORY_TOKEN: Final[str] = "UNIT_CATEGORY_TOKEN"

# Sentinel category recorded in the lookback once any frame closes.
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

# Categories that are always silently drained in any statement frame.
_STATEMENT_DRAIN_CATEGORIES: Final[frozenset[str]] = frozenset(
    {
        "drain_token",
        "modal_aux",
        "residual_modifier",
        "aggregate_modifier",
        "ordinal_token",
        "mass_noun_token",
        _UNIT_CATEGORY_TOKEN,
        "punctuation_comma",
    }
)


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
    no compatible entity in the registry.
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
    unit: str | None = None,
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
    new_unit = unit if unit is not None else (
        existing.unit if existing is not None else None
    )
    new_position = position if position is not None else (
        existing.position if existing is not None else 0
    )
    return QuestionTargetSlot(
        kind=new_kind,
        entity=new_entity,
        unit_class=new_unit_class,
        unit=new_unit,
        position=new_position,
    )


def _close_frame(
    sentence_state: SentenceReadingState,
    category: str,
) -> SentenceReadingState:
    """Push category to lookback then append _FRAME_CLOSED_MARKER."""
    intermediate = _advance(sentence_state, category=category)
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


# ---------------------------------------------------------------------------
# Lifecycle API.
# ---------------------------------------------------------------------------


def begin_sentence(
    problem_state: ProblemReadingState,
    source_text_offset: int,
) -> SentenceReadingState:
    """Open a fresh sentence-local state.

    Per ADR-0164.3 §Lifecycle API. ``sentence_index`` is *not* incremented
    here — ``end_sentence`` owns the increment.
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

    See module docstring for the four-step contract. Phase 2 extends
    Phase 1 to handle statement-frame openers at position 0.
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
    category, _surface, dec_val = _classify(word, token_index=position)

    # Once the frame is closed, every token drains.
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

    # Pure-drain categories at any position and in any frame.
    if category in {"drain_token", "punctuation_comma"}:
        return _advance(sentence_state, category=category)

    # Fraction/percentage tokens: refuse at any position in any open frame.
    # These require Phase 2.1+ handling (embedded-quantifier aggregates).
    if category in {"fraction_token", "percentage_token"}:
        return ReaderRefusal(
            reason="unexpected_category",
            detail=(
                f"fraction/percentage literal at position {position} is "
                "out-of-scope (embedded-quantifier aggregate; deferred to Phase 2.1)"
            ),
            sentence_index=sentence_idx,
            token_index=position,
            token_text=word,
        )

    # -----------------------------------------------------------------------
    # Pre-frame dispatch (frame is None).
    # -----------------------------------------------------------------------
    if sentence_state.frame is None:
        return _apply_preframe(
            sentence_state=sentence_state,
            problem_state=problem_state,
            category=category,
            word=word,
            dec_val=dec_val,
        )

    # -----------------------------------------------------------------------
    # In-frame dispatch.
    # -----------------------------------------------------------------------
    if sentence_state.frame == "question_frame":
        handler = _QUESTION_FRAME_RULES.get(category, _rule_default_refuse)
        return handler(
            sentence_state=sentence_state,
            problem_state=problem_state,
            category=category,
            word=word,
            dec_val=dec_val,
        )

    if sentence_state.frame == "initial_state_frame":
        handler = _INITIAL_STATE_FRAME_RULES.get(category, _rule_statement_refuse)
        return handler(
            sentence_state=sentence_state,
            problem_state=problem_state,
            category=category,
            word=word,
            dec_val=dec_val,
        )

    if sentence_state.frame == "operation_frame":
        handler = _OPERATION_FRAME_RULES.get(category, _rule_statement_refuse)
        return handler(
            sentence_state=sentence_state,
            problem_state=problem_state,
            category=category,
            word=word,
            dec_val=dec_val,
        )

    if sentence_state.frame == "descriptive_frame":
        handler = _DESCRIPTIVE_FRAME_RULES.get(category, _rule_descriptive_drain_or_refuse)
        return handler(
            sentence_state=sentence_state,
            problem_state=problem_state,
            category=category,
            word=word,
            dec_val=dec_val,
        )

    return ReaderRefusal(
        reason="unexpected_category",
        detail=f"unknown frame kind {sentence_state.frame!r}",
        sentence_index=sentence_idx,
        token_index=position,
        token_text=word,
    )


def end_sentence(
    sentence_state: SentenceReadingState,
    problem_state: ProblemReadingState,
) -> ProblemReadingState | ReaderRefusal:
    """Close the sentence and fold it into a new ``ProblemReadingState``.

    Validation order per ADR-0164.3 §Lifecycle API.
    """
    sentence_idx = problem_state.sentence_index
    last_position = max(sentence_state.token_index - 1, 0)

    if sentence_state.frame is None:
        if sentence_state.token_index == 0:
            return ReaderRefusal(
                reason="unfinished_frame",
                detail="sentence ended without a frame being decided",
                sentence_index=sentence_idx,
                token_index=last_position,
                token_text="",
            )
        return _end_descriptive_frame(sentence_state, problem_state)

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

    # question_frame — same logic as Phase 1.
    if sentence_state.frame == "question_frame":
        return _end_question_frame(sentence_state, problem_state, sentence_idx, last_position)

    # initial_state_frame — commit PartialInitialPossession.
    if sentence_state.frame == "initial_state_frame":
        return _end_initial_state_frame(sentence_state, problem_state, sentence_idx, last_position)

    # operation_frame — commit PartialOperation.
    if sentence_state.frame == "operation_frame":
        return _end_operation_frame(sentence_state, problem_state, sentence_idx, last_position)

    # descriptive_frame — no math state, just advance.
    if sentence_state.frame == "descriptive_frame":
        return _end_descriptive_frame(sentence_state, problem_state)

    return ReaderRefusal(
        reason="unfinished_frame",
        detail=f"unrecognised frame kind {sentence_state.frame!r}",
        sentence_index=sentence_idx,
        token_index=last_position,
        token_text="",
    )


def finalize(
    problem_state: ProblemReadingState,
) -> "MathProblemGraph | ReaderRefusal":
    """Project a finished ProblemReadingState into a MathProblemGraph.

    Called after the last sentence's end_sentence succeeds.
    Returns a :class:`ReaderRefusal` if any structural requirement is unmet.
    """
    from generate.math_problem_graph import (
        InitialPossession,
        MathGraphError,
        MathProblemGraph,
        Operation,
        Quantity,
        Unknown,
    )

    # 1. Require a question target.
    if problem_state.unknown_target_slot is None:
        return ReaderRefusal(
            reason="no_question_target",
            detail="ProblemReadingState has no unknown_target_slot after finalize",
            sentence_index=problem_state.sentence_index,
            token_index=0,
            token_text="",
        )

    target = problem_state.unknown_target_slot

    # 2. Build entity list from registry.
    entities = tuple(e.canonical_name for e in problem_state.entity_registry)
    if not entities:
        return ReaderRefusal(
            reason="dangling_entity",
            detail="entity_registry is empty; no entities to build graph",
            sentence_index=problem_state.sentence_index,
            token_index=0,
            token_text="",
        )

    # 3. Project accumulated_initial_state → InitialPossession.
    initial_possessions: list[InitialPossession] = []
    for pip in problem_state.accumulated_initial_state:
        if pip.entity is None or pip.quantity is None:
            return ReaderRefusal(
                reason="graph_construction_failure",
                detail="PartialInitialPossession missing entity or quantity at finalize",
                sentence_index=problem_state.sentence_index,
                token_index=0,
                token_text="",
            )
        qty = pip.quantity
        if qty.unit is None:
            return ReaderRefusal(
                reason="graph_construction_failure",
                detail="PartialInitialPossession.quantity has no unit at finalize",
                sentence_index=problem_state.sentence_index,
                token_index=0,
                token_text="",
            )
        try:
            ip = InitialPossession(
                entity=pip.entity,
                quantity=Quantity(value=float(qty.value), unit=qty.unit),
            )
        except MathGraphError as exc:
            return ReaderRefusal(
                reason="graph_construction_failure",
                detail=f"InitialPossession construction failed: {exc}",
                sentence_index=problem_state.sentence_index,
                token_index=0,
                token_text="",
            )
        initial_possessions.append(ip)

    # 4. Project accumulated_operations → Operation.
    operations: list[Operation] = []
    for pop in problem_state.accumulated_operations:
        if pop.actor is None or pop.kind is None or pop.operand is None:
            return ReaderRefusal(
                reason="graph_construction_failure",
                detail="PartialOperation missing actor/kind/operand at finalize",
                sentence_index=problem_state.sentence_index,
                token_index=0,
                token_text="",
            )
        qty = pop.operand
        if qty.unit is None:
            return ReaderRefusal(
                reason="graph_construction_failure",
                detail="PartialOperation.operand has no unit at finalize",
                sentence_index=problem_state.sentence_index,
                token_index=0,
                token_text="",
            )
        op_kind = _VERB_CATEGORY_TO_OP_KIND.get(pop.kind)
        if op_kind is None:
            return ReaderRefusal(
                reason="graph_construction_failure",
                detail=f"unknown verb kind {pop.kind!r} in PartialOperation at finalize",
                sentence_index=problem_state.sentence_index,
                token_index=0,
                token_text="",
            )
        try:
            op = Operation(
                actor=pop.actor,
                kind=op_kind,
                operand=Quantity(value=float(qty.value), unit=qty.unit),
                target=pop.target,
            )
        except MathGraphError as exc:
            return ReaderRefusal(
                reason="graph_construction_failure",
                detail=f"Operation construction failed: {exc}",
                sentence_index=problem_state.sentence_index,
                token_index=0,
                token_text="",
            )
        operations.append(op)

    # 5. Build Unknown from QuestionTargetSlot.
    # unit is the question's unit noun lemma (set by _rule_unit_noun_question).
    # Fall back to unit_class if unit was not captured (for currency/time).
    unknown_unit = target.unit
    if unknown_unit is None:
        # Derive a best-effort unit from unit_class — this allows currency/time
        # questions without an explicit unit noun to still resolve.
        unknown_unit = _UNIT_CLASS_TO_DEFAULT_UNIT.get(target.unit_class or "")
    if not unknown_unit:
        return ReaderRefusal(
            reason="graph_construction_failure",
            detail="QuestionTargetSlot has no unit and no unit_class to derive from",
            sentence_index=problem_state.sentence_index,
            token_index=0,
            token_text="",
        )

    try:
        unknown = Unknown(entity=target.entity, unit=unknown_unit)
    except MathGraphError as exc:
        return ReaderRefusal(
            reason="graph_construction_failure",
            detail=f"Unknown construction failed: {exc}",
            sentence_index=problem_state.sentence_index,
            token_index=0,
            token_text="",
        )

    # 6. Build MathProblemGraph.
    try:
        graph = MathProblemGraph(
            entities=entities,
            initial_state=tuple(initial_possessions),
            operations=tuple(operations),
            unknown=unknown,
        )
    except MathGraphError as exc:
        return ReaderRefusal(
            reason="graph_construction_failure",
            detail=f"MathProblemGraph construction failed: {exc}",
            sentence_index=problem_state.sentence_index,
            token_index=0,
            token_text="",
        )
    return graph


# Default unit strings for unit_class values when the question sentence
# contains no unit noun (e.g. "How much will it cost him?" → unit_class="currency").
_UNIT_CLASS_TO_DEFAULT_UNIT: Final[dict[str, str]] = {
    "currency": "dollars",
    "time": "hours",
}


# ---------------------------------------------------------------------------
# Step 1 + 2 — classification.
# ---------------------------------------------------------------------------


def _classify(word: str, *, token_index: int) -> tuple[str | None, str, Decimal | None]:
    """Return (category, surface, decimal_value). Category is None on miss.

    Dispatch order:
    - At token_index == 0 (sentence-initial, ADR-0164.1 amendment via
      Brief 8.2): lookup-first, skipping proper_noun_gender_* entries
      (those are enrichment, not admission). On miss, primitive scan
      catches the universal proper_noun_token primitive.
    - At token_index > 0: lookup-first (Phase 2 ordering — lexicon
      verbs/units take precedence over primitive coverage); on miss,
      possessive strip retry; then primitive scan for numerics, currency
      amounts, fractions, and capitalized names.

    Numeric primitives extract a Decimal value; non-numeric primitives
    return Decimal=None.
    """
    # Punctuation terminators — reader-internal dispatch.
    if word == "?":
        return "question_terminator", word, None
    if word in (".", "!"):
        return "statement_terminator", word, None
    if word == ",":
        return "punctuation_comma", word, None

    lex = _get_lexicon()

    def _emit_primitive() -> tuple[str | None, str, Decimal | None]:
        primitive: LexemeMatch | None = scan(word)
        if primitive is None:
            return None, word, None
        if primitive.emit_category == _UNIT_CATEGORY_TOKEN:
            # Lexicon override for mass-noun tokens with operational meaning.
            entry = lookup(lex, word)
            if entry is not None:
                return entry.category, entry.lemma, None
            return "mass_noun_token", primitive.source_text, None
        cat = _PRIMITIVE_CATEGORY_MAP.get(primitive.primitive_name, primitive.emit_category)
        dec_val: Decimal | None = None
        ev = primitive.extracted_values
        if "value" in ev:
            try:
                dec_val = Decimal(ev["value"])
            except Exception:
                pass
        elif "whole" in ev:
            # decimal-currency-literal splits into "whole" + "cents"
            whole = ev.get("whole", "0")
            cents = ev.get("cents", "0").zfill(2)
            try:
                dec_val = Decimal(f"{whole}.{cents}")
            except Exception:
                pass
        return cat, primitive.source_text, dec_val

    if token_index == 0:
        # Sentence-initial: lookup-first, skip gender-enrichment categories
        # (per Brief 8.2 — gender is enrichment, not admission).
        entry: LexiconEntry | None = lookup(lex, word)
        if entry is not None and entry.category not in {
            "proper_noun_gender_female",
            "proper_noun_gender_male",
        }:
            return entry.category, entry.lemma, None
        # On lookup miss OR gender-only hit: primitive scan picks up the name.
        return _emit_primitive()

    # Mid-sentence: lookup-first (Phase 2 ordering), but skip
    # proper_noun_gender_* entries (gender is enrichment everywhere,
    # per Brief 8.2 — let the primitive emit proper_noun_token so the
    # dispatch table sees one consistent category for names).
    entry = lookup(lex, word)
    if entry is not None and entry.category not in {
        "proper_noun_gender_female",
        "proper_noun_gender_male",
    }:
        return entry.category, entry.lemma, None

    # Possessive strip retry.
    if word.endswith("'s") and len(word) > 2:
        entry = lookup(lex, word[:-2])
        if entry is not None and entry.category not in {
            "proper_noun_gender_female",
            "proper_noun_gender_male",
        }:
            return entry.category, entry.lemma, None

    # Primitive scan for numerics, currency, names, etc.
    return _emit_primitive()


def gender_of_proper_noun(
    surface: str,
    lexicon: Lexicon,
) -> Literal["female", "male", "neuter", "unknown"]:
    """Pure enrichment lookup. Unknown names still admit.

    Per ADR-0164.2 §EntityRegistry: gender is a ratifiable annotation
    on EntityRef, NOT an admission criterion. Names outside the
    gender-coded lexicon lists return "unknown" and admit cleanly.
    Pronoun resolution (ADR-0164.2 §Refusal rules) handles unknown
    gender via single-salient fallback or refuses with
    ambiguous_pronoun_referent.
    """
    entry = lookup(lexicon, surface.lower())
    if entry is None:
        return "unknown"
    if entry.category == "proper_noun_gender_female":
        return "female"
    if entry.category == "proper_noun_gender_male":
        return "male"
    return "unknown"


# ---------------------------------------------------------------------------
# _advance helper.
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


# ---------------------------------------------------------------------------
# Pre-frame handlers (frame is None at the time of the call).
# ---------------------------------------------------------------------------


def _apply_preframe(
    *,
    sentence_state: SentenceReadingState,
    problem_state: ProblemReadingState,
    category: str,
    word: str,
    dec_val: Decimal | None,
) -> SentenceReadingState | ReaderRefusal:
    """Dispatch token when frame has not yet been determined."""
    position = sentence_state.token_index
    sentence_idx = problem_state.sentence_index

    if category in _QUESTION_OPENERS:
        return _rule_question_open(
            sentence_state=sentence_state,
            problem_state=problem_state,
            category=category,
            word=word,
            dec_val=dec_val,
        )

    if category == "proper_noun_token":
        return _rule_preframe_entity(
            sentence_state=sentence_state,
            problem_state=problem_state,
            category=category,
            word=word,
            dec_val=dec_val,
        )

    if category == "entity_pronoun":
        return _rule_preframe_pronoun(
            sentence_state=sentence_state,
            problem_state=problem_state,
            category=category,
            word=word,
            dec_val=dec_val,
        )

    if category in _VERB_TO_FRAME:
        if sentence_state.pending_entity_ref is None:
            # Subject-dropped: treat as descriptive frame and drain the verb.
            return _advance(
                sentence_state,
                category=category,
                frame="descriptive_frame",
            )
        return _rule_preframe_verb(
            sentence_state=sentence_state,
            problem_state=problem_state,
            category=category,
            word=word,
            dec_val=dec_val,
        )

    if category in _STATEMENT_DRAIN_CATEGORIES:
        return _advance(sentence_state, category=category)

    # Categories that can safely drain when no frame is set yet.
    _PREFRAME_DRAIN: frozenset[str] = frozenset({
        "count_unit_noun", "currency_unit_noun", "time_unit_noun",
        "count_quantity", "currency_quantity", "time_quantity",
        "question_continuous_qty", "question_discrete_qty",
        "question_comparative",
        "copula_verb",
    })
    if category in _PREFRAME_DRAIN:
        return _advance(sentence_state, category=category)

    return ReaderRefusal(
        reason="unexpected_category",
        detail=(
            f"category {category!r} (word={word!r}) at pre-frame position "
            f"{position} not handled; may be Phase-3 scope"
        ),
        sentence_index=sentence_idx,
        token_index=position,
        token_text=word,
    )


def _rule_preframe_entity(
    *,
    sentence_state: SentenceReadingState,
    problem_state: ProblemReadingState,
    category: str,
    word: str,
    dec_val: Decimal | None,  # noqa: ARG001
) -> SentenceReadingState | ReaderRefusal:
    """Proper noun at pre-frame position — records subject entity, leaves frame=None."""
    if sentence_state.pending_entity_ref is not None:
        return ReaderRefusal(
            reason="unexpected_category",
            detail=(
                f"second entity {word!r} at pre-frame position "
                f"{sentence_state.token_index}; multi-subject sentences are "
                "Phase-2.1 scope"
            ),
            sentence_index=problem_state.sentence_index,
            token_index=sentence_state.token_index,
            token_text=word,
        )
    canonical = word.lower()
    gender = gender_of_proper_noun(word, _get_lexicon())
    entity_ref = EntityRef(
        canonical_name=canonical,
        gender=gender,
        first_mention_position=sentence_state.token_index,
    )
    return _advance(
        sentence_state,
        category=category,
        pending_entity_ref=entity_ref,
    )


def _rule_preframe_pronoun(
    *,
    sentence_state: SentenceReadingState,
    problem_state: ProblemReadingState,
    category: str,  # noqa: ARG001
    word: str,
    dec_val: Decimal | None,  # noqa: ARG001
) -> SentenceReadingState | ReaderRefusal:
    """Pronoun at pre-frame position — resolves to registry entity, leaves frame=None."""
    if sentence_state.pending_entity_ref is not None:
        # Possessive adjective after entity (e.g., "Aaron and his brother") — drain.
        return _advance(sentence_state, category="drain_token")
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
                f"pronoun {word!r} matches >1 entity: " + ", ".join(candidates)
            ),
            sentence_index=problem_state.sentence_index,
            token_index=sentence_state.token_index,
            token_text=word,
        )
    resolved_name = candidates[0]
    pronoun_lower = word.lower()
    gender = _PRONOUN_GENDER.get(pronoun_lower, "unknown")
    # Create an EntityRef referencing the already-registered entity (not new).
    entity_ref = EntityRef(
        canonical_name=resolved_name,
        gender=gender,
        first_mention_position=sentence_state.token_index,
    )
    return _advance(
        sentence_state,
        category="entity_pronoun",
        pending_entity_ref=entity_ref,
    )


def _rule_preframe_verb(
    *,
    sentence_state: SentenceReadingState,
    problem_state: ProblemReadingState,  # noqa: ARG001
    category: str,
    word: str,
    dec_val: Decimal | None,  # noqa: ARG001
) -> SentenceReadingState | ReaderRefusal:
    """Frame-determining verb — sets frame based on verb category."""
    frame = _VERB_TO_FRAME[category]
    verb_ref = VerbReference(
        surface=word.lower(),
        kind=category,
        position=sentence_state.token_index,
    )
    return _advance(
        sentence_state,
        category=category,
        frame=frame,
        pending_verb=verb_ref,
        partial_frame_payload=FramePayload(frame_kind=frame),
    )


# ---------------------------------------------------------------------------
# Question-frame handlers.
# ---------------------------------------------------------------------------


def _rule_question_open(
    *,
    sentence_state: SentenceReadingState,
    problem_state: ProblemReadingState,
    category: str,
    word: str,
    dec_val: Decimal | None,  # noqa: ARG001
) -> SentenceReadingState | ReaderRefusal:
    """Opening word ('How', 'What') begins a question_frame."""
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
    dec_val: Decimal | None,  # noqa: ARG001
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


def _rule_unit_noun_question(
    *,
    sentence_state: SentenceReadingState,
    problem_state: ProblemReadingState,
    category: str,
    word: str,
    dec_val: Decimal | None,  # noqa: ARG001
) -> SentenceReadingState | ReaderRefusal:
    """Rule: count/currency/time unit noun in question_frame sets unit_class + unit."""
    if sentence_state.frame != "question_frame":
        return ReaderRefusal(
            reason="unexpected_category",
            detail=f"{category} outside question_frame",
            sentence_index=problem_state.sentence_index,
            token_index=sentence_state.token_index,
            token_text=word,
        )
    unit_class = _UNIT_CLASS_BY_CATEGORY[category]
    # Capture the lemma as the unit string for finalize().
    lex = _get_lexicon()
    entry = lookup(lex, word)
    unit_lemma = entry.lemma if entry is not None else word.lower()
    new_target = _update_question_target(
        sentence_state, unit_class=unit_class, unit=unit_lemma
    )
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
    dec_val: Decimal | None,  # noqa: ARG001
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
    dec_val: Decimal | None,  # noqa: ARG001
) -> SentenceReadingState | ReaderRefusal:
    """Rule: resolve pronoun against registry (question_frame only)."""
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


def _rule_proper_noun_question(
    *,
    sentence_state: SentenceReadingState,
    problem_state: ProblemReadingState,
    category: str,
    word: str,
    dec_val: Decimal | None,  # noqa: ARG001
) -> SentenceReadingState | ReaderRefusal:
    if sentence_state.frame != "question_frame":
        return ReaderRefusal(
            reason="unexpected_category",
            detail="proper_noun outside question_frame",
            sentence_index=problem_state.sentence_index,
            token_index=sentence_state.token_index,
            token_text=word,
        )
    canonical = word
    gender = gender_of_proper_noun(word, _get_lexicon())
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
    dec_val: Decimal | None,  # noqa: ARG001
) -> SentenceReadingState | ReaderRefusal:
    """Rule: 'left'/'remaining'/'after' — drain outside question_frame."""
    if sentence_state.frame != "question_frame":
        return _advance(sentence_state, category="drain_token")
    return _advance(sentence_state, category=category)


def _rule_frame_closer_question(
    *,
    sentence_state: SentenceReadingState,
    problem_state: ProblemReadingState,
    category: str,
    word: str,
    dec_val: Decimal | None,  # noqa: ARG001
) -> SentenceReadingState | ReaderRefusal:
    """Rule: verb or '?' closes the question_frame."""
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
    intermediate = _advance(sentence_state, category=category, pending_verb=pending_verb)
    return _close_frame_from_intermediate(intermediate)


def _close_frame_from_intermediate(
    intermediate: SentenceReadingState,
) -> SentenceReadingState:
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
    dec_val: Decimal | None,  # noqa: ARG001
) -> ReaderRefusal:
    return ReaderRefusal(
        reason="unexpected_category",
        detail=f"category {category!r} not handled by question_frame rules",
        sentence_index=problem_state.sentence_index,
        token_index=sentence_state.token_index,
        token_text=word,
    )


# ---------------------------------------------------------------------------
# Statement-frame handlers (shared across initial_state + operation frames).
# ---------------------------------------------------------------------------


def _rule_statement_drain(
    *,
    sentence_state: SentenceReadingState,
    problem_state: ProblemReadingState,  # noqa: ARG001
    category: str,
    word: str,  # noqa: ARG001
    dec_val: Decimal | None,  # noqa: ARG001
) -> SentenceReadingState:
    """Drain token in a statement frame — advance without semantic effect."""
    return _advance(sentence_state, category="drain_token")


def _rule_statement_quantity(
    *,
    sentence_state: SentenceReadingState,
    problem_state: ProblemReadingState,
    category: str,
    word: str,
    dec_val: Decimal | None,
) -> SentenceReadingState | ReaderRefusal:
    """Numeric literal in a statement frame — creates a pending QuantityRef."""
    if dec_val is None:
        return ReaderRefusal(
            reason="unexpected_category",
            detail=f"quantity token {word!r} has no parseable decimal value",
            sentence_index=problem_state.sentence_index,
            token_index=sentence_state.token_index,
            token_text=word,
        )
    actor = sentence_state.pending_entity_ref
    owner = actor.canonical_name if actor is not None else None
    # currency_quantity gets a default unit "dollars" (refined if unit noun follows).
    # count_quantity and time_quantity get unit_class="pending" until unit noun arrives.
    if category == "currency_quantity":
        pending = QuantityRef(
            value=dec_val,
            unit="dollars",
            unit_class="currency",
            owner_entity=owner,
            mention_position=sentence_state.token_index,
        )
    else:
        pending = QuantityRef(
            value=dec_val,
            unit=None,
            unit_class="pending",
            owner_entity=owner,
            mention_position=sentence_state.token_index,
        )
    new_pending = sentence_state.pending_quantities + (pending,)
    return _advance(
        sentence_state,
        category=category,
        pending_quantities=new_pending,
    )


def _rule_unit_noun_statement(
    *,
    sentence_state: SentenceReadingState,
    problem_state: ProblemReadingState,  # noqa: ARG001
    category: str,
    word: str,
    dec_val: Decimal | None,  # noqa: ARG001
) -> SentenceReadingState | ReaderRefusal:
    """Unit noun in a statement frame — completes the most-recent pending quantity.

    If no pending quantity exists, the unit noun is a bare descriptor and is
    drained (e.g. "Sandra had some bags" — 'bags' has no quantity).
    """
    if not sentence_state.pending_quantities:
        return _advance(sentence_state, category="drain_token")

    unit_class = _UNIT_CLASS_BY_CATEGORY[category]
    lex = _get_lexicon()
    entry = lookup(lex, word)
    unit_lemma = entry.lemma if entry is not None else word.lower()

    pending = sentence_state.pending_quantities[-1]
    complete = QuantityRef(
        value=pending.value,
        unit=unit_lemma,
        unit_class=unit_class,
        owner_entity=pending.owner_entity,
        mention_position=pending.mention_position,
    )
    new_pending = sentence_state.pending_quantities[:-1]
    new_quantities = sentence_state.quantities + (complete,)
    return _advance(
        sentence_state,
        category=category,
        pending_quantities=new_pending,
        quantities=new_quantities,
    )


def _rule_statement_closer(
    *,
    sentence_state: SentenceReadingState,
    problem_state: ProblemReadingState,  # noqa: ARG001
    category: str,
    word: str,  # noqa: ARG001
    dec_val: Decimal | None,  # noqa: ARG001
) -> SentenceReadingState:
    """Statement terminator — closes the statement frame."""
    return _close_frame(sentence_state, category)


def _rule_statement_refuse(
    *,
    sentence_state: SentenceReadingState,
    problem_state: ProblemReadingState,
    category: str,
    word: str,
    dec_val: Decimal | None,  # noqa: ARG001
) -> ReaderRefusal:
    return ReaderRefusal(
        reason="unexpected_category",
        detail=(
            f"category {category!r} (word={word!r}) not handled in "
            f"{sentence_state.frame!r}"
        ),
        sentence_index=problem_state.sentence_index,
        token_index=sentence_state.token_index,
        token_text=word,
    )


# ---------------------------------------------------------------------------
# Operation-frame specific handlers.
# ---------------------------------------------------------------------------


def _rule_op_proper_noun(
    *,
    sentence_state: SentenceReadingState,
    problem_state: ProblemReadingState,  # noqa: ARG001
    category: str,
    word: str,
    dec_val: Decimal | None,  # noqa: ARG001
) -> SentenceReadingState:
    """Proper noun mid-operation frame — potential transfer target.

    Stored in ``entities`` so end_sentence can extract it as the transfer
    target when verb kind is transfer_verb.
    """
    canonical = word.lower()
    gender = gender_of_proper_noun(word, _get_lexicon())
    entity_ref = EntityRef(
        canonical_name=canonical,
        gender=gender,
        first_mention_position=sentence_state.token_index,
    )
    new_entities = sentence_state.entities + (entity_ref,)
    return _advance(
        sentence_state,
        category=category,
        entities=new_entities,
    )


def _rule_op_pronoun(
    *,
    sentence_state: SentenceReadingState,
    problem_state: ProblemReadingState,
    category: str,  # noqa: ARG001
    word: str,
    dec_val: Decimal | None,  # noqa: ARG001
) -> SentenceReadingState | ReaderRefusal:
    """Pronoun mid-operation frame — potential transfer target (resolved)."""
    candidates = _resolve_pronoun(word, problem_state.entity_registry)
    if candidates is None or len(candidates) == 0:
        return ReaderRefusal(
            reason="unresolved_pronoun",
            detail=(
                f"pronoun {word!r} in operation_frame has no compatible entity"
            ),
            sentence_index=problem_state.sentence_index,
            token_index=sentence_state.token_index,
            token_text=word,
        )
    if len(candidates) > 1:
        return ReaderRefusal(
            reason="ambiguous_pronoun_referent",
            detail=(
                f"pronoun {word!r} in operation_frame matches >1 entity: "
                + ", ".join(candidates)
            ),
            sentence_index=problem_state.sentence_index,
            token_index=sentence_state.token_index,
            token_text=word,
        )
    resolved_name = candidates[0]
    pronoun_lower = word.lower()
    gender = _PRONOUN_GENDER.get(pronoun_lower, "unknown")
    entity_ref = EntityRef(
        canonical_name=resolved_name,
        gender=gender,
        first_mention_position=sentence_state.token_index,
    )
    new_entities = sentence_state.entities + (entity_ref,)
    return _advance(
        sentence_state,
        category="entity_pronoun",
        entities=new_entities,
    )


# ---------------------------------------------------------------------------
# Descriptive-frame handler.
# ---------------------------------------------------------------------------


def _rule_descriptive_drain_or_refuse(
    *,
    sentence_state: SentenceReadingState,
    problem_state: ProblemReadingState,
    category: str,
    word: str,
    dec_val: Decimal | None,  # noqa: ARG001
) -> SentenceReadingState | ReaderRefusal:
    """In descriptive_frame, known semantic categories drain; unknowns refuse."""
    _DESCRIPTIVE_DRAIN_CATEGORIES: frozenset[str] = frozenset(
        {
            "count_unit_noun",
            "currency_unit_noun",
            "time_unit_noun",
            "proper_noun_token",
            "entity_pronoun",
            "count_quantity",
            "currency_quantity",
            "time_quantity",
            "ordinal_token",
            "mass_noun_token",
            "accumulation_verb",
            "depletion_verb",
            "transfer_verb",
            "capacity_verb",
            "possession_verb",
        }
    )
    if category in _DESCRIPTIVE_DRAIN_CATEGORIES:
        return _advance(sentence_state, category="drain_token")
    return ReaderRefusal(
        reason="unexpected_category",
        detail=f"category {category!r} (word={word!r}) not drainable in descriptive_frame",
        sentence_index=problem_state.sentence_index,
        token_index=sentence_state.token_index,
        token_text=word,
    )


# ---------------------------------------------------------------------------
# end_sentence helpers.
# ---------------------------------------------------------------------------


def _carry_entity(
    sentence_state: SentenceReadingState,
    problem_state: ProblemReadingState,
) -> tuple[tuple[EntityRef, ...], ProblemReadingState]:
    """Return (registry, updated-problem-state) after carrying sentence entity."""
    new_registry = problem_state.entity_registry
    if sentence_state.pending_entity_ref is not None:
        existing_names = {e.canonical_name for e in new_registry}
        candidate = sentence_state.pending_entity_ref
        if candidate.canonical_name not in existing_names:
            new_registry = new_registry + (candidate,)
    return new_registry, problem_state


def _end_question_frame(
    sentence_state: SentenceReadingState,
    problem_state: ProblemReadingState,
    sentence_idx: int,
    last_position: int,
) -> ProblemReadingState | ReaderRefusal:
    target = sentence_state.question_target
    if target is None:
        return ReaderRefusal(
            reason="incomplete_operation",
            detail="question_frame closed with no QuestionTargetSlot",
            sentence_index=sentence_idx,
            token_index=last_position,
            token_text="",
        )
    if target.unit_class is None:
        return ReaderRefusal(
            reason="incomplete_operation",
            detail="question_frame missing required slot(s): unit_class",
            sentence_index=sentence_idx,
            token_index=last_position,
            token_text="",
        )
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
    new_registry, _ = _carry_entity(sentence_state, problem_state)
    return ProblemReadingState(
        entity_registry=new_registry,
        accumulated_initial_state=problem_state.accumulated_initial_state,
        accumulated_operations=problem_state.accumulated_operations,
        unknown_target_slot=target,
        pronoun_resolution_history=problem_state.pronoun_resolution_history,
        sentence_index=problem_state.sentence_index + 1,
        source_text_offset=problem_state.source_text_offset
        + max(sentence_state.token_index, 1),
    )


def _end_initial_state_frame(
    sentence_state: SentenceReadingState,
    problem_state: ProblemReadingState,
    sentence_idx: int,
    last_position: int,
) -> ProblemReadingState | ReaderRefusal:
    if not sentence_state.quantities:
        return ReaderRefusal(
            reason="incomplete_operation",
            detail="initial_state_frame closed with no quantity",
            sentence_index=sentence_idx,
            token_index=last_position,
            token_text="",
        )
    if len(sentence_state.quantities) > 1:
        return ReaderRefusal(
            reason="incomplete_operation",
            detail=(
                f"initial_state_frame has {len(sentence_state.quantities)} "
                "quantities; multi-quantity initial state is Phase-2.1 scope"
            ),
            sentence_index=sentence_idx,
            token_index=last_position,
            token_text="",
        )
    actor = sentence_state.pending_entity_ref
    if actor is None:
        return ReaderRefusal(
            reason="incomplete_operation",
            detail="initial_state_frame has no subject entity",
            sentence_index=sentence_idx,
            token_index=last_position,
            token_text="",
        )
    qty = sentence_state.quantities[0]
    pip = PartialInitialPossession(entity=actor.canonical_name, quantity=qty)
    new_initial_state = problem_state.accumulated_initial_state + (pip,)
    new_registry, _ = _carry_entity(sentence_state, problem_state)
    return ProblemReadingState(
        entity_registry=new_registry,
        accumulated_initial_state=new_initial_state,
        accumulated_operations=problem_state.accumulated_operations,
        unknown_target_slot=problem_state.unknown_target_slot,
        pronoun_resolution_history=problem_state.pronoun_resolution_history,
        sentence_index=problem_state.sentence_index + 1,
        source_text_offset=problem_state.source_text_offset
        + max(sentence_state.token_index, 1),
    )


def _end_operation_frame(
    sentence_state: SentenceReadingState,
    problem_state: ProblemReadingState,
    sentence_idx: int,
    last_position: int,
) -> ProblemReadingState | ReaderRefusal:
    if not sentence_state.quantities:
        return ReaderRefusal(
            reason="incomplete_operation",
            detail="operation_frame closed with no quantity",
            sentence_index=sentence_idx,
            token_index=last_position,
            token_text="",
        )
    if len(sentence_state.quantities) > 1:
        return ReaderRefusal(
            reason="incomplete_operation",
            detail=(
                f"operation_frame has {len(sentence_state.quantities)} "
                "quantities; multi-quantity operations are Phase-2.1 scope"
            ),
            sentence_index=sentence_idx,
            token_index=last_position,
            token_text="",
        )
    actor = sentence_state.pending_entity_ref
    if actor is None:
        return ReaderRefusal(
            reason="incomplete_operation",
            detail="operation_frame has no subject entity",
            sentence_index=sentence_idx,
            token_index=last_position,
            token_text="",
        )
    verb = sentence_state.pending_verb
    if verb is None:
        return ReaderRefusal(
            reason="incomplete_operation",
            detail="operation_frame has no pending_verb",
            sentence_index=sentence_idx,
            token_index=last_position,
            token_text="",
        )
    qty = sentence_state.quantities[0]
    # Transfer target: the first entity in sentence_state.entities that is NOT
    # the actor (added by _rule_op_proper_noun / _rule_op_pronoun).
    transfer_target: str | None = None
    if verb.kind == "transfer_verb":
        for ent in sentence_state.entities:
            if ent.canonical_name != actor.canonical_name:
                transfer_target = ent.canonical_name
                break
    pop = PartialOperation(
        actor=actor.canonical_name,
        kind=verb.kind,
        operand=qty,
        target=transfer_target,
    )
    new_operations = problem_state.accumulated_operations + (pop,)
    # Also carry over any newly-introduced entities from this operation frame.
    new_registry = problem_state.entity_registry
    for ent in (sentence_state.pending_entity_ref,) + sentence_state.entities:
        if ent is not None:
            existing_names = {e.canonical_name for e in new_registry}
            if ent.canonical_name not in existing_names:
                new_registry = new_registry + (ent,)
    return ProblemReadingState(
        entity_registry=new_registry,
        accumulated_initial_state=problem_state.accumulated_initial_state,
        accumulated_operations=new_operations,
        unknown_target_slot=problem_state.unknown_target_slot,
        pronoun_resolution_history=problem_state.pronoun_resolution_history,
        sentence_index=problem_state.sentence_index + 1,
        source_text_offset=problem_state.source_text_offset
        + max(sentence_state.token_index, 1),
    )


def _end_descriptive_frame(
    sentence_state: SentenceReadingState,
    problem_state: ProblemReadingState,
) -> ProblemReadingState:
    new_registry, _ = _carry_entity(sentence_state, problem_state)
    return ProblemReadingState(
        entity_registry=new_registry,
        accumulated_initial_state=problem_state.accumulated_initial_state,
        accumulated_operations=problem_state.accumulated_operations,
        unknown_target_slot=problem_state.unknown_target_slot,
        pronoun_resolution_history=problem_state.pronoun_resolution_history,
        sentence_index=problem_state.sentence_index + 1,
        source_text_offset=problem_state.source_text_offset
        + max(sentence_state.token_index, 1),
    )


# ---------------------------------------------------------------------------
# Rule tables.
# ---------------------------------------------------------------------------

_Handler = Callable[..., "SentenceReadingState | ReaderRefusal"]

# question_frame — Phase 1, unchanged in semantics.
_QUESTION_FRAME_RULES: Final[dict[str, _Handler]] = {
    "question_open": _rule_question_open,
    "question_continuous_qty": _rule_qty_qualifier,
    "question_discrete_qty": _rule_qty_qualifier,
    "question_comparative": _rule_qty_qualifier,
    "aggregate_modifier": _rule_qty_qualifier,
    "count_unit_noun": _rule_unit_noun_question,
    "currency_unit_noun": _rule_unit_noun_question,
    "time_unit_noun": _rule_unit_noun_question,
    "modal_aux": _rule_modal_aux,
    "entity_pronoun": _rule_entity_pronoun,
    "proper_noun_token": _rule_proper_noun_question,
    # Residual marker
    "residual_modifier": _rule_residual_modifier,
    "accumulation_verb": _rule_frame_closer_question,
    "depletion_verb": _rule_frame_closer_question,
    "transfer_verb": _rule_frame_closer_question,
    "capacity_verb": _rule_frame_closer_question,
    "possession_verb": _rule_frame_closer_question,
    "copula_verb": _rule_frame_closer_question,
    "question_terminator": _rule_frame_closer_question,
    # Quantity tokens that appear in a post-close portion of a question sentence
    # drain safely (frame is already closed before they're reached in practice).
    "count_quantity": _rule_statement_drain,
    "currency_quantity": _rule_statement_drain,
    "time_quantity": _rule_statement_drain,
    "ordinal_token": _rule_statement_drain,
    "mass_noun_token": _rule_statement_drain,
}

# initial_state_frame — entity had/has/owned N unit.
_INITIAL_STATE_FRAME_RULES: Final[dict[str, _Handler]] = {
    "count_quantity": _rule_statement_quantity,
    "currency_quantity": _rule_statement_quantity,
    "time_quantity": _rule_statement_quantity,
    "count_unit_noun": _rule_unit_noun_statement,
    "currency_unit_noun": _rule_unit_noun_statement,
    "time_unit_noun": _rule_unit_noun_statement,
    "modal_aux": _rule_statement_drain,
    "residual_modifier": _rule_statement_drain,
    "aggregate_modifier": _rule_statement_drain,
    "ordinal_token": _rule_statement_drain,
    "mass_noun_token": _rule_statement_drain,
    "question_comparative": _rule_statement_drain,
    "proper_noun_token": _rule_statement_drain,
    "entity_pronoun": _rule_statement_drain,
    "accumulation_verb": _rule_statement_drain,
    "depletion_verb": _rule_statement_drain,
    "transfer_verb": _rule_statement_drain,
    "capacity_verb": _rule_statement_drain,
    "copula_verb": _rule_statement_drain,
    "possession_verb": _rule_statement_drain,
    "question_open": _rule_statement_drain,
    "question_continuous_qty": _rule_statement_drain,
    "question_discrete_qty": _rule_statement_drain,
    "statement_terminator": _rule_statement_closer,
    "question_terminator": _rule_statement_closer,
}

# operation_frame — entity verb N unit [to entity2].
_OPERATION_FRAME_RULES: Final[dict[str, _Handler]] = {
    "count_quantity": _rule_statement_quantity,
    "currency_quantity": _rule_statement_quantity,
    "time_quantity": _rule_statement_quantity,
    "count_unit_noun": _rule_unit_noun_statement,
    "currency_unit_noun": _rule_unit_noun_statement,
    "time_unit_noun": _rule_unit_noun_statement,
    "modal_aux": _rule_statement_drain,
    "residual_modifier": _rule_statement_drain,
    "aggregate_modifier": _rule_statement_drain,
    "ordinal_token": _rule_statement_drain,
    "mass_noun_token": _rule_statement_drain,
    "question_comparative": _rule_statement_drain,
    "proper_noun_token": _rule_op_proper_noun,
    "entity_pronoun": _rule_op_pronoun,
    "accumulation_verb": _rule_statement_drain,
    "depletion_verb": _rule_statement_drain,
    "transfer_verb": _rule_statement_drain,
    "capacity_verb": _rule_statement_drain,
    "copula_verb": _rule_statement_drain,
    "possession_verb": _rule_statement_drain,
    "question_open": _rule_statement_drain,
    "question_continuous_qty": _rule_statement_drain,
    "question_discrete_qty": _rule_statement_drain,
    "statement_terminator": _rule_statement_closer,
    "question_terminator": _rule_statement_closer,
}

# descriptive_frame — drains known categories; closes on terminator.
_DESCRIPTIVE_FRAME_RULES: Final[dict[str, _Handler]] = {
    "statement_terminator": _rule_statement_closer,
    "modal_aux": _rule_statement_drain,
    "residual_modifier": _rule_statement_drain,
    "aggregate_modifier": _rule_statement_drain,
    "ordinal_token": _rule_statement_drain,
    "mass_noun_token": _rule_statement_drain,
    "question_comparative": _rule_statement_drain,
    "count_unit_noun": _rule_statement_drain,
    "currency_unit_noun": _rule_statement_drain,
    "time_unit_noun": _rule_statement_drain,
    "proper_noun_token": _rule_statement_drain,
    "entity_pronoun": _rule_statement_drain,
    "count_quantity": _rule_statement_drain,
    "currency_quantity": _rule_statement_drain,
    "time_quantity": _rule_statement_drain,
    "accumulation_verb": _rule_statement_drain,
    "depletion_verb": _rule_statement_drain,
    "transfer_verb": _rule_statement_drain,
    "capacity_verb": _rule_statement_drain,
    "possession_verb": _rule_statement_drain,
    "copula_verb": _rule_statement_drain,
    "question_open": _rule_statement_drain,
    "question_continuous_qty": _rule_statement_drain,
    "question_discrete_qty": _rule_statement_drain,
}


__all__ = [
    "apply_word",
    "begin_sentence",
    "end_sentence",
    "finalize",
]
