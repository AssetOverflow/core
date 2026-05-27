from __future__ import annotations

from decimal import Decimal

import pytest

from generate.comprehension.state import (
    # inner level (renamed from ComprehensionState)
    SentenceReadingState,
    # outer level (new)
    ProblemReadingState,
    # shared leaf types
    EntityRef,
    ExpectationFrame,
    PartialOp,
    QuantityRef,
    QuestionTargetSlot,
    # new inner-level leaf types
    AppliedCategory,
    FramePayload,
    VerbReference,
    # new outer-level leaf types
    PartialInitialPossession,
    PartialOperation,
    PronounResolution,
    # refusal
    ReaderRefusal,
    READER_REFUSAL_REASONS,
    # error
    ComprehensionStateError,
    # canonical-bytes function
    to_canonical_bytes,
    # backward-compat alias (must still resolve)
    ComprehensionState,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_entity(name: str = "tina", gender: str = "female", pos: int = 0) -> EntityRef:
    return EntityRef(canonical_name=name, gender=gender, first_mention_position=pos)


def _make_qty(
    val: str = "12.00",
    unit: str = "dollars",
    unit_class: str = "currency",
    pos: int = 1,
) -> QuantityRef:
    return QuantityRef(
        value=Decimal(val),
        unit=unit,
        unit_class=unit_class,
        owner_entity=None,
        mention_position=pos,
    )



def _make_empty_problem_state() -> ProblemReadingState:
    return ProblemReadingState(
        entity_registry=(),
        accumulated_initial_state=(),
        accumulated_operations=(),
        unknown_target_slot=None,
        pronoun_resolution_history=(),
        sentence_index=0,
        source_text_offset=0,
    )


# ===========================================================================
# EXISTING TESTS — now exercising SentenceReadingState (pure rename from #321)
# ===========================================================================

def test_canonical_bytes_are_deterministic_for_equal_states() -> None:
    first = SentenceReadingState(
        entities=(
            EntityRef(
                canonical_name="tina",
                gender="female",
                first_mention_position=0,
            ),
        ),
        quantities=(
            QuantityRef(
                value=Decimal("12.00"),
                unit="dollars",
                unit_class="currency",
                owner_entity="tina",
                mention_position=1,
            ),
        ),
        operations=(
            PartialOp(
                operator_kind="accumulation_verb",
                subject_entity="tina",
                object_entity=None,
                quantity_index=0,
                position=2,
            ),
        ),
        question_target=QuestionTargetSlot(
            kind="continuous_quantity",
            entity="tina",
            unit_class="currency",
            position=3,
        ),
        expectation=ExpectationFrame(
            allowed_categories=("residual_modifier", "state_continuation_verb"),
            reason="question frame remains open",
        ),
    )
    second = SentenceReadingState(
        entities=(
            EntityRef(
                canonical_name="tina",
                gender="female",
                first_mention_position=0,
            ),
        ),
        quantities=(
            QuantityRef(
                value=Decimal("12.0"),
                unit="dollars",
                unit_class="currency",
                owner_entity="tina",
                mention_position=1,
            ),
        ),
        operations=(
            PartialOp(
                operator_kind="accumulation_verb",
                subject_entity="tina",
                object_entity=None,
                quantity_index=0,
                position=2,
            ),
        ),
        question_target=QuestionTargetSlot(
            kind="continuous_quantity",
            entity="tina",
            unit_class="currency",
            position=3,
        ),
        expectation=ExpectationFrame(
            allowed_categories=("residual_modifier", "state_continuation_verb"),
            reason="question frame remains open",
        ),
    )

    assert first.canonical_bytes() == second.canonical_bytes()
    assert first.canonical_hash() == second.canonical_hash()
    assert (
        first.canonical_bytes()
        == b'{"entities":[{"canonical_name":"tina","first_mention_position":0,"gender":"female"}],"expectation":{"allowed_categories":["residual_modifier","state_continuation_verb"],"reason":"question frame remains open"},"operations":[{"object_entity":null,"operator_kind":"accumulation_verb","position":2,"quantity_index":0,"subject_entity":"tina"}],"quantities":[{"mention_position":1,"owner_entity":"tina","unit":"dollars","unit_class":"currency","value":"12"}],"question_target":{"entity":"tina","kind":"continuous_quantity","position":3,"unit_class":"currency"}}'
    )


def test_optional_fields_serialize_as_null() -> None:
    state = SentenceReadingState(
        entities=(),
        quantities=(),
        operations=(),
        question_target=None,
        expectation=None,
    )

    assert (
        state.canonical_bytes()
        == b'{"entities":[],"expectation":null,"operations":[],"quantities":[],"question_target":null}'
    )


def test_entity_ref_refuses_invalid_gender() -> None:
    with pytest.raises(ComprehensionStateError, match="EntityRef.gender"):
        EntityRef(
            canonical_name="tina",
            gender="plural",  # type: ignore[arg-type]
            first_mention_position=0,
        )


def test_quantity_ref_refuses_non_decimal_and_missing_unit_shape() -> None:
    with pytest.raises(ComprehensionStateError, match="QuantityRef.value"):
        QuantityRef(
            value="12.0",  # type: ignore[arg-type]
            unit="dollars",
            unit_class="currency",
            owner_entity="tina",
            mention_position=1,
        )
    with pytest.raises(
        ComprehensionStateError,
        match="QuantityRef.unit and QuantityRef.unit_class cannot both be None",
    ):
        QuantityRef(
            value=Decimal("12"),
            unit=None,
            unit_class=None,
            owner_entity=None,
            mention_position=1,
        )


def test_expectation_frame_refuses_empty_or_unknown_categories() -> None:
    with pytest.raises(
        ComprehensionStateError,
        match="ExpectationFrame.allowed_categories must not be empty",
    ):
        ExpectationFrame(allowed_categories=(), reason="x")
    with pytest.raises(ComprehensionStateError, match="allowed_categories"):
        ExpectationFrame(
            allowed_categories=("unsupported",),
            reason="x",
        )


def test_comprehension_state_refuses_non_tuple_and_wrong_member_types() -> None:
    with pytest.raises(ComprehensionStateError, match="entities must be tuple"):
        SentenceReadingState(
            entities=[],  # type: ignore[arg-type]
            quantities=(),
            operations=(),
        )
    with pytest.raises(ComprehensionStateError, match="quantities\\[0\\]"):
        SentenceReadingState(
            entities=(),
            quantities=("bad",),  # type: ignore[arg-type]
            operations=(),
        )


# ===========================================================================
# NEW TESTS — backward-compat alias
# ===========================================================================

def test_comprehension_state_alias_resolves_to_sentence_reading_state() -> None:
    """ComprehensionState must still resolve so callers from #321 need not change."""
    assert ComprehensionState is SentenceReadingState


# ===========================================================================
# NEW TESTS — SentenceReadingState new fields
# ===========================================================================

def test_sentence_reading_state_new_fields_default_to_safe_values() -> None:
    state = SentenceReadingState(entities=(), quantities=(), operations=())
    assert state.frame is None
    assert state.pending_quantities == ()
    assert state.pending_entity_ref is None
    assert state.pending_verb is None
    assert state.token_index == 0
    assert state.lookback == ()
    assert state.partial_frame_payload is None


def test_sentence_reading_state_accepts_new_fields() -> None:
    verb_ref = VerbReference(surface="makes", kind="rate_emit", position=1)
    applied = AppliedCategory(category="accumulation_verb", position=1)
    payload = FramePayload(frame_kind="operation_frame")
    entity = _make_entity()
    qty = _make_qty()

    state = SentenceReadingState(
        entities=(entity,),
        quantities=(qty,),
        operations=(),
        frame="operation_frame",
        pending_quantities=(qty,),
        pending_entity_ref=entity,
        pending_verb=verb_ref,
        token_index=3,
        lookback=(applied,),
        partial_frame_payload=payload,
    )

    assert state.frame == "operation_frame"
    assert state.pending_verb is verb_ref
    assert state.token_index == 3
    assert len(state.lookback) == 1
    assert state.partial_frame_payload is payload


def test_sentence_reading_state_refuses_invalid_frame() -> None:
    with pytest.raises(ComprehensionStateError, match="frame"):
        SentenceReadingState(
            entities=(), quantities=(), operations=(),
            frame="nonsense_frame",  # type: ignore[arg-type]
        )


def test_sentence_reading_state_refuses_lookback_overflow() -> None:
    cats = tuple(AppliedCategory(category="accumulation_verb", position=i) for i in range(9))
    with pytest.raises(ComprehensionStateError, match="lookback.*≤8"):
        SentenceReadingState(entities=(), quantities=(), operations=(), lookback=cats)


def test_verb_reference_construction_and_validation() -> None:
    vr = VerbReference(surface="earns", kind="accumulation_verb", position=2)
    assert vr.surface == "earns"
    assert vr.kind == "accumulation_verb"
    assert vr.as_canonical() == {"kind": "accumulation_verb", "position": 2, "surface": "earns"}

    with pytest.raises(ComprehensionStateError):
        VerbReference(surface="", kind="x", position=0)
    with pytest.raises(ComprehensionStateError):
        VerbReference(surface="x", kind="x", position=-1)


def test_applied_category_construction() -> None:
    ac = AppliedCategory(category="depletion_verb", position=5)
    assert ac.category == "depletion_verb"
    assert ac.as_canonical() == {"category": "depletion_verb", "position": 5}


def test_frame_payload_construction_and_validation() -> None:
    for kind in ("initial_state_frame", "operation_frame", "question_frame", "descriptive_frame"):
        fp = FramePayload(frame_kind=kind)
        assert fp.frame_kind == kind

    with pytest.raises(ComprehensionStateError, match="frame_kind"):
        FramePayload(frame_kind="bad_frame")


# ===========================================================================
# NEW TESTS — PartialInitialPossession and PartialOperation
# ===========================================================================

def test_partial_initial_possession_fully_nullable() -> None:
    pip = PartialInitialPossession(entity=None, quantity=None)
    assert pip.entity is None
    assert pip.quantity is None
    assert pip.as_canonical() == {}


def test_partial_initial_possession_with_values() -> None:
    qty = _make_qty()
    pip = PartialInitialPossession(entity="tina", quantity=qty)
    canon = pip.as_canonical()
    assert canon["entity"] == "tina"
    assert "quantity" in canon


def test_partial_initial_possession_refuses_empty_entity() -> None:
    with pytest.raises(ComprehensionStateError):
        PartialInitialPossession(entity="", quantity=None)


def test_partial_operation_fully_nullable() -> None:
    po = PartialOperation(actor=None, kind=None, operand=None, target=None)
    assert po.as_canonical() == {}


def test_partial_operation_with_values() -> None:
    qty = _make_qty()
    po = PartialOperation(actor="tina", kind="accumulation", operand=qty, target=None)
    canon = po.as_canonical()
    assert canon["actor"] == "tina"
    assert canon["kind"] == "accumulation"
    assert "operand" in canon
    assert "target" not in canon  # None → omitted


def test_pronoun_resolution_construction() -> None:
    pr = PronounResolution(pronoun="she", resolved_to="Tina", at_sentence=1, at_position=0)
    assert pr.resolved_to == "Tina"
    canon = pr.as_canonical()
    assert canon == {
        "at_position": 0,
        "at_sentence": 1,
        "pronoun": "she",
        "resolved_to": "Tina",
    }


def test_pronoun_resolution_refuses_empty_fields() -> None:
    with pytest.raises(ComprehensionStateError, match="PronounResolution.pronoun"):
        PronounResolution(pronoun="", resolved_to="Tina", at_sentence=0, at_position=0)
    with pytest.raises(ComprehensionStateError, match="PronounResolution.resolved_to"):
        PronounResolution(pronoun="she", resolved_to="", at_sentence=0, at_position=0)


# ===========================================================================
# NEW TESTS — ProblemReadingState construction
# ===========================================================================

def test_problem_reading_state_empty_construction() -> None:
    ps = _make_empty_problem_state()
    assert ps.entity_registry == ()
    assert ps.accumulated_initial_state == ()
    assert ps.accumulated_operations == ()
    assert ps.unknown_target_slot is None
    assert ps.pronoun_resolution_history == ()
    assert ps.sentence_index == 0
    assert ps.source_text_offset == 0


def test_problem_reading_state_with_entities_and_operations() -> None:
    entity = _make_entity()
    qty = _make_qty()
    pip = PartialInitialPossession(entity="tina", quantity=qty)
    po = PartialOperation(actor="tina", kind="accumulation", operand=qty, target=None)
    pr = PronounResolution(pronoun="she", resolved_to="tina", at_sentence=1, at_position=0)
    qt = QuestionTargetSlot(kind="continuous_quantity", entity="tina", unit_class="currency", position=0)

    ps = ProblemReadingState(
        entity_registry=(entity,),
        accumulated_initial_state=(pip,),
        accumulated_operations=(po,),
        unknown_target_slot=qt,
        pronoun_resolution_history=(pr,),
        sentence_index=2,
        source_text_offset=47,
    )

    assert len(ps.entity_registry) == 1
    assert ps.sentence_index == 2
    assert ps.source_text_offset == 47
    assert ps.unknown_target_slot is qt


def test_problem_reading_state_refuses_wrong_member_types() -> None:
    with pytest.raises(ComprehensionStateError, match="entity_registry"):
        ProblemReadingState(
            entity_registry="bad",  # type: ignore[arg-type]
            accumulated_initial_state=(),
            accumulated_operations=(),
            unknown_target_slot=None,
            pronoun_resolution_history=(),
            sentence_index=0,
            source_text_offset=0,
        )
    with pytest.raises(ComprehensionStateError, match="entity_registry\\[0\\]"):
        ProblemReadingState(
            entity_registry=("bad",),  # type: ignore[arg-type]
            accumulated_initial_state=(),
            accumulated_operations=(),
            unknown_target_slot=None,
            pronoun_resolution_history=(),
            sentence_index=0,
            source_text_offset=0,
        )
    with pytest.raises(ComprehensionStateError, match="sentence_index"):
        ProblemReadingState(
            entity_registry=(),
            accumulated_initial_state=(),
            accumulated_operations=(),
            unknown_target_slot=None,
            pronoun_resolution_history=(),
            sentence_index=-1,
            source_text_offset=0,
        )


# ===========================================================================
# NEW TESTS — ProblemReadingState canonical-bytes determinism gate
# ===========================================================================

def test_problem_reading_state_canonical_bytes_determinism() -> None:
    """Two equal ProblemReadingState instances must produce byte-equal output."""
    entity = _make_entity()
    pip = PartialInitialPossession(entity="tina", quantity=None)

    ps1 = ProblemReadingState(
        entity_registry=(entity,),
        accumulated_initial_state=(pip,),
        accumulated_operations=(),
        unknown_target_slot=None,
        pronoun_resolution_history=(),
        sentence_index=1,
        source_text_offset=33,
    )
    ps2 = ProblemReadingState(
        entity_registry=(entity,),
        accumulated_initial_state=(pip,),
        accumulated_operations=(),
        unknown_target_slot=None,
        pronoun_resolution_history=(),
        sentence_index=1,
        source_text_offset=33,
    )

    assert ps1.canonical_bytes() == ps2.canonical_bytes()
    assert ps1.canonical_hash() == ps2.canonical_hash()
    assert to_canonical_bytes(ps1) == to_canonical_bytes(ps2)


def test_problem_reading_state_canonical_bytes_sensitivity() -> None:
    """Single-field differences must produce different canonical bytes."""
    base = _make_empty_problem_state()

    # sentence_index differs
    incremented = ProblemReadingState(
        entity_registry=(),
        accumulated_initial_state=(),
        accumulated_operations=(),
        unknown_target_slot=None,
        pronoun_resolution_history=(),
        sentence_index=1,
        source_text_offset=0,
    )
    assert base.canonical_bytes() != incremented.canonical_bytes()

    # source_text_offset differs
    offset = ProblemReadingState(
        entity_registry=(),
        accumulated_initial_state=(),
        accumulated_operations=(),
        unknown_target_slot=None,
        pronoun_resolution_history=(),
        sentence_index=0,
        source_text_offset=10,
    )
    assert base.canonical_bytes() != offset.canonical_bytes()

    # entity_registry populated
    with_entity = ProblemReadingState(
        entity_registry=(_make_entity(),),
        accumulated_initial_state=(),
        accumulated_operations=(),
        unknown_target_slot=None,
        pronoun_resolution_history=(),
        sentence_index=0,
        source_text_offset=0,
    )
    assert base.canonical_bytes() != with_entity.canonical_bytes()


def test_problem_reading_state_none_fields_omitted_from_canonical() -> None:
    """Per ADR-0164.3 §Canonical-bytes: None → omitted, not serialised as null."""
    ps = _make_empty_problem_state()
    raw = to_canonical_bytes(ps)
    assert b"null" not in raw, (
        "None fields must be OMITTED from canonical bytes, not serialised as null"
    )


# ===========================================================================
# NEW TESTS — to_canonical_bytes handles SentenceReadingState too
# ===========================================================================

def test_to_canonical_bytes_sentence_state_none_omitted() -> None:
    state = SentenceReadingState(entities=(), quantities=(), operations=())
    raw = to_canonical_bytes(state)
    assert b"null" not in raw
    # token_index=0 is a non-None int — must be present
    assert b'"token_index"' in raw


def test_to_canonical_bytes_sentence_state_determinism() -> None:
    s1 = SentenceReadingState(
        entities=(_make_entity(),),
        quantities=(),
        operations=(),
        token_index=2,
    )
    s2 = SentenceReadingState(
        entities=(_make_entity(),),
        quantities=(),
        operations=(),
        token_index=2,
    )
    assert to_canonical_bytes(s1) == to_canonical_bytes(s2)


def test_to_canonical_bytes_sentence_state_sensitivity() -> None:
    base = SentenceReadingState(entities=(), quantities=(), operations=(), token_index=0)
    diff = SentenceReadingState(entities=(), quantities=(), operations=(), token_index=1)
    assert to_canonical_bytes(base) != to_canonical_bytes(diff)


# ===========================================================================
# NEW TESTS — ReaderRefusal construction and canonical bytes
# ===========================================================================

def test_reader_refusal_reasons_has_11_entries() -> None:
    assert len(READER_REFUSAL_REASONS) == 11


@pytest.mark.parametrize("reason", sorted(READER_REFUSAL_REASONS))
def test_every_refusal_reason_is_constructible(reason: str) -> None:
    rf = ReaderRefusal(
        reason=reason,
        detail=f"test refusal for {reason}",
        sentence_index=0,
        token_index=0,
        token_text="",
    )
    assert rf.reason == reason


def test_reader_refusal_refuses_unknown_reason() -> None:
    with pytest.raises(ComprehensionStateError, match="READER_REFUSAL_REASONS"):
        ReaderRefusal(
            reason="made_up_reason",
            detail="detail",
            sentence_index=0,
            token_index=0,
            token_text="",
        )


def test_reader_refusal_refuses_empty_detail() -> None:
    with pytest.raises(ComprehensionStateError, match="ReaderRefusal.detail"):
        ReaderRefusal(
            reason="unknown_word",
            detail="",
            sentence_index=0,
            token_index=0,
            token_text="if",
        )


def test_reader_refusal_canonical_bytes_round_trip() -> None:
    rf = ReaderRefusal(
        reason="unexpected_category",
        detail="conditional_open at sentence_index=1, position=0",
        sentence_index=1,
        token_index=0,
        token_text="If",
    )
    b1 = rf.canonical_bytes()
    b2 = to_canonical_bytes(rf)
    assert b1 == b2

    # same values → byte-equal
    rf2 = ReaderRefusal(
        reason="unexpected_category",
        detail="conditional_open at sentence_index=1, position=0",
        sentence_index=1,
        token_index=0,
        token_text="If",
    )
    assert rf.canonical_bytes() == rf2.canonical_bytes()
    assert rf.canonical_hash() == rf2.canonical_hash()


def test_reader_refusal_empty_token_text_allowed() -> None:
    """Sentence-level and problem-level refusals have no single token."""
    rf = ReaderRefusal(
        reason="unfinished_frame",
        detail="frame never decided",
        sentence_index=2,
        token_index=0,
        token_text="",
    )
    assert rf.token_text == ""


def test_reader_refusal_canonical_bytes_sensitivity() -> None:
    rf1 = ReaderRefusal(
        reason="unknown_word",
        detail="detail",
        sentence_index=0,
        token_index=0,
        token_text="foo",
    )
    rf2 = ReaderRefusal(
        reason="unknown_word",
        detail="detail",
        sentence_index=0,
        token_index=1,
        token_text="foo",
    )
    assert rf1.canonical_bytes() != rf2.canonical_bytes()
