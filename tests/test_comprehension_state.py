from __future__ import annotations

from decimal import Decimal

import pytest

from generate.comprehension.state import (
    ComprehensionState,
    ComprehensionStateError,
    EntityRef,
    ExpectationFrame,
    PartialOp,
    QuantityRef,
    QuestionTargetSlot,
)


def test_canonical_bytes_are_deterministic_for_equal_states() -> None:
    first = ComprehensionState(
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
    second = ComprehensionState(
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
    state = ComprehensionState(
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
        ComprehensionState(
            entities=[],  # type: ignore[arg-type]
            quantities=(),
            operations=(),
        )
    with pytest.raises(ComprehensionStateError, match="quantities\\[0\\]"):
        ComprehensionState(
            entities=(),
            quantities=("bad",),  # type: ignore[arg-type]
            operations=(),
        )
