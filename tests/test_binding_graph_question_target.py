"""ADR-0135 — Tests for the question-target resolver.

Covers:
  - ``resolve_state_index`` boundary cases (0 / 1 / many operations);
  - ``infer_question_form`` for every operation-kind family;
  - precedence rule on mixed-kind graphs;
  - refusal-first ``QuestionTargetError`` paths;
  - ``bound_unknown_from_math_problem_graph`` deterministic shape;
  - typed ``Operation`` (state-index variant) construction guards.

Pure unit lane — adapter integration lives in
``test_binding_graph_adapter_question_target.py``.
"""

from __future__ import annotations

import pytest

from generate.binding_graph import (
    BindingGraphError,
    BoundUnknown,
    Operation as StateIndexOperation,
    QUESTION_FORMS,
    QUESTION_TARGET_REASONS,
    QuestionTargetError,
    STATE_INDEX_LABELS,
    bound_unknown_from_math_problem_graph,
    infer_question_form,
    resolve_state_index,
)
from generate.math_problem_graph import (
    Comparison,
    InitialPossession,
    MathProblemGraph,
    Operation,
    Quantity,
    Rate,
    Unknown,
)


# ---------------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------------


def _graph(
    *,
    entities: tuple[str, ...] = ("Tina",),
    initial_state: tuple[InitialPossession, ...] = (
        InitialPossession(entity="Tina", quantity=Quantity(5, "apples")),
    ),
    operations: tuple[Operation, ...] = (),
    unknown: Unknown = Unknown(entity="Tina", unit="apples"),
) -> MathProblemGraph:
    return MathProblemGraph(
        entities=entities,
        initial_state=initial_state,
        operations=operations,
        unknown=unknown,
    )


def _add(actor: str, n: int, unit: str = "apples") -> Operation:
    return Operation(actor=actor, kind="add", operand=Quantity(n, unit))


def _sub(actor: str, n: int, unit: str = "apples") -> Operation:
    return Operation(actor=actor, kind="subtract", operand=Quantity(n, unit))


def _transfer(actor: str, target: str, n: int, unit: str = "apples") -> Operation:
    return Operation(
        actor=actor, kind="transfer", operand=Quantity(n, unit), target=target
    )


def _mul(actor: str, n: int, unit: str = "apples") -> Operation:
    return Operation(actor=actor, kind="multiply", operand=Quantity(n, unit))


def _div(actor: str, n: int, unit: str = "apples") -> Operation:
    return Operation(actor=actor, kind="divide", operand=Quantity(n, unit))


def _rate_op(
    actor: str, value: float, num: str, denom: str
) -> Operation:
    return Operation(
        actor=actor,
        kind="apply_rate",
        operand=Rate(value=value, numerator_unit=num, denominator_unit=denom),
    )


def _cmp_add(
    actor: str, ref: str, delta: int, unit: str = "apples", direction: str = "more"
) -> Operation:
    return Operation(
        actor=actor,
        kind="compare_additive",
        operand=Comparison(
            reference_actor=ref,
            delta=Quantity(delta, unit),
            factor=None,
            direction=direction,  # type: ignore[arg-type]
        ),
    )


def _cmp_mul(
    actor: str, ref: str, factor: float, direction: str = "times"
) -> Operation:
    return Operation(
        actor=actor,
        kind="compare_multiplicative",
        operand=Comparison(
            reference_actor=ref,
            delta=None,
            factor=factor,
            direction=direction,  # type: ignore[arg-type]
        ),
    )


# ---------------------------------------------------------------------------
# StateIndex / Operation dataclass guards
# ---------------------------------------------------------------------------


def test_operation_state_index_construction() -> None:
    op = StateIndexOperation(operation_index=3)
    assert op.operation_index == 3


def test_operation_state_index_refuses_negative() -> None:
    with pytest.raises(BindingGraphError):
        StateIndexOperation(operation_index=-1)


def test_operation_state_index_refuses_bool() -> None:
    with pytest.raises(BindingGraphError):
        StateIndexOperation(operation_index=True)  # type: ignore[arg-type]


def test_operation_state_index_refuses_string() -> None:
    with pytest.raises(BindingGraphError):
        StateIndexOperation(operation_index="3")  # type: ignore[arg-type]


def test_state_index_labels_locked() -> None:
    assert STATE_INDEX_LABELS == frozenset({"initial", "terminal"})


def test_question_forms_locked() -> None:
    assert QUESTION_FORMS == frozenset(
        {"count", "rate", "total", "difference", "ratio", "identity"}
    )


# ---------------------------------------------------------------------------
# resolve_state_index
# ---------------------------------------------------------------------------


def test_resolve_state_index_no_operations_is_initial() -> None:
    g = _graph(operations=())
    assert resolve_state_index(g) == "initial"


def test_resolve_state_index_one_operation_is_terminal() -> None:
    g = _graph(operations=(_add("Tina", 2),))
    assert resolve_state_index(g) == "terminal"


def test_resolve_state_index_many_operations_is_terminal() -> None:
    g = _graph(
        operations=tuple(_add("Tina", n) for n in (1, 2, 3, 4, 5)),
    )
    assert resolve_state_index(g) == "terminal"


def test_resolve_state_index_refuses_non_graph() -> None:
    with pytest.raises(QuestionTargetError) as exc:
        resolve_state_index({"entities": ["Tina"]})
    assert exc.value.reason == "not_a_math_problem_graph"


def test_resolve_state_index_deterministic() -> None:
    g = _graph(operations=(_add("Tina", 2), _sub("Tina", 1)))
    assert resolve_state_index(g) == resolve_state_index(g)


# ---------------------------------------------------------------------------
# infer_question_form — single-kind families
# ---------------------------------------------------------------------------


def test_infer_count_pure_add() -> None:
    g = _graph(operations=(_add("Tina", 2), _add("Tina", 3)))
    assert infer_question_form(g) == "count"


def test_infer_count_pure_subtract() -> None:
    g = _graph(operations=(_sub("Tina", 2),))
    assert infer_question_form(g) == "count"


def test_infer_count_pure_transfer() -> None:
    g = _graph(
        entities=("Tina", "Sam"),
        initial_state=(
            InitialPossession(entity="Tina", quantity=Quantity(5, "apples")),
            InitialPossession(entity="Sam", quantity=Quantity(3, "apples")),
        ),
        operations=(_transfer("Tina", "Sam", 2),),
    )
    assert infer_question_form(g) == "count"


def test_infer_count_multiply() -> None:
    g = _graph(operations=(_mul("Tina", 3),))
    assert infer_question_form(g) == "count"


def test_infer_count_divide() -> None:
    g = _graph(operations=(_div("Tina", 5),))
    assert infer_question_form(g) == "count"


def test_infer_count_mixed_arithmetic() -> None:
    g = _graph(
        operations=(_add("Tina", 4), _sub("Tina", 1), _mul("Tina", 2)),
    )
    assert infer_question_form(g) == "count"


def test_infer_difference_compare_additive() -> None:
    g = _graph(
        entities=("Tina", "Sam"),
        initial_state=(
            InitialPossession(entity="Tina", quantity=Quantity(5, "apples")),
            InitialPossession(entity="Sam", quantity=Quantity(3, "apples")),
        ),
        operations=(_cmp_add("Tina", "Sam", 2),),
    )
    assert infer_question_form(g) == "difference"


def test_infer_ratio_compare_multiplicative() -> None:
    g = _graph(
        entities=("Tina", "Sam"),
        initial_state=(
            InitialPossession(entity="Tina", quantity=Quantity(5, "apples")),
            InitialPossession(entity="Sam", quantity=Quantity(3, "apples")),
        ),
        operations=(_cmp_mul("Tina", "Sam", 2.0),),
    )
    assert infer_question_form(g) == "ratio"


def test_infer_total_apply_rate_unknown_is_numerator() -> None:
    # "How many dollars does Tina earn?" — apply_rate consumes hours,
    # produces dollars. Unknown.unit == numerator_unit ⇒ total.
    g = _graph(
        initial_state=(
            InitialPossession(entity="Tina", quantity=Quantity(8, "hours")),
        ),
        operations=(_rate_op("Tina", 12.5, num="dollars", denom="hours"),),
        unknown=Unknown(entity="Tina", unit="dollars"),
    )
    assert infer_question_form(g) == "total"


def test_infer_rate_apply_rate_unknown_is_denominator() -> None:
    # Unknown.unit == denominator_unit ⇒ rate.
    g = _graph(
        initial_state=(
            InitialPossession(entity="Tina", quantity=Quantity(8, "hours")),
        ),
        operations=(_rate_op("Tina", 12.5, num="dollars", denom="hours"),),
        unknown=Unknown(entity="Tina", unit="hours"),
    )
    assert infer_question_form(g) == "rate"


def test_infer_identity_no_operations() -> None:
    g = _graph(operations=())
    assert infer_question_form(g) == "identity"


def test_infer_identity_when_no_operation_touches_unknown_entity() -> None:
    # Tina is in entities (has initial possession) but the only operation
    # belongs to Sam → no touching op → identity.
    g = _graph(
        entities=("Tina", "Sam"),
        initial_state=(
            InitialPossession(entity="Tina", quantity=Quantity(5, "apples")),
            InitialPossession(entity="Sam", quantity=Quantity(3, "apples")),
        ),
        operations=(_add("Sam", 2),),
        unknown=Unknown(entity="Tina", unit="apples"),
    )
    assert infer_question_form(g) == "identity"


# ---------------------------------------------------------------------------
# infer_question_form — precedence on mixed kinds
# ---------------------------------------------------------------------------


def test_precedence_compare_multiplicative_beats_additive() -> None:
    g = _graph(
        entities=("Tina", "Sam"),
        initial_state=(
            InitialPossession(entity="Tina", quantity=Quantity(5, "apples")),
            InitialPossession(entity="Sam", quantity=Quantity(3, "apples")),
        ),
        operations=(
            _cmp_add("Tina", "Sam", 2),
            _cmp_mul("Tina", "Sam", 2.0),
        ),
    )
    assert infer_question_form(g) == "ratio"


def test_precedence_compare_additive_beats_count() -> None:
    g = _graph(
        entities=("Tina", "Sam"),
        initial_state=(
            InitialPossession(entity="Tina", quantity=Quantity(5, "apples")),
            InitialPossession(entity="Sam", quantity=Quantity(3, "apples")),
        ),
        operations=(
            _add("Tina", 4),
            _cmp_add("Tina", "Sam", 2),
        ),
    )
    assert infer_question_form(g) == "difference"


def test_precedence_compare_beats_apply_rate() -> None:
    g = _graph(
        entities=("Tina", "Sam"),
        initial_state=(
            InitialPossession(entity="Tina", quantity=Quantity(8, "hours")),
            InitialPossession(entity="Sam", quantity=Quantity(4, "hours")),
        ),
        operations=(
            _rate_op("Tina", 12.5, "dollars", "hours"),
            _cmp_add("Tina", "Sam", 2, unit="hours"),
        ),
        unknown=Unknown(entity="Tina", unit="hours"),
    )
    assert infer_question_form(g) == "difference"


def test_precedence_apply_rate_beats_count() -> None:
    g = _graph(
        initial_state=(
            InitialPossession(entity="Tina", quantity=Quantity(8, "hours")),
        ),
        operations=(
            _add("Tina", 1, unit="hours"),
            _rate_op("Tina", 12.5, "dollars", "hours"),
        ),
        unknown=Unknown(entity="Tina", unit="dollars"),
    )
    assert infer_question_form(g) == "total"


# ---------------------------------------------------------------------------
# infer_question_form — refusals
# ---------------------------------------------------------------------------


def test_apply_rate_unit_mismatch_refuses() -> None:
    # Unknown unit matches neither numerator nor denominator of any
    # touching apply_rate → typed refusal.
    g = _graph(
        initial_state=(
            InitialPossession(entity="Tina", quantity=Quantity(8, "hours")),
        ),
        operations=(_rate_op("Tina", 12.5, num="dollars", denom="hours"),),
        unknown=Unknown(entity="Tina", unit="apples"),
    )
    with pytest.raises(QuestionTargetError) as exc:
        infer_question_form(g)
    assert exc.value.reason == "apply_rate_unit_mismatch"


def test_infer_refuses_non_graph_input() -> None:
    with pytest.raises(QuestionTargetError) as exc:
        infer_question_form(object())
    assert exc.value.reason == "not_a_math_problem_graph"


def test_question_target_reasons_locked() -> None:
    assert QUESTION_TARGET_REASONS == frozenset(
        {
            "not_a_math_problem_graph",
            "unknown_entity_not_in_entities",
            "unmappable_question_form",
            "apply_rate_unit_mismatch",
        }
    )


def test_question_target_error_refuses_unknown_reason() -> None:
    with pytest.raises(ValueError):
        QuestionTargetError("nonexistent_reason")


def test_question_target_error_carries_typed_reason() -> None:
    exc = QuestionTargetError("unmappable_question_form", detail="weird shape")
    assert exc.reason == "unmappable_question_form"
    assert "weird shape" in str(exc)


# ---------------------------------------------------------------------------
# bound_unknown_from_math_problem_graph
# ---------------------------------------------------------------------------


def test_bound_unknown_terminal_count() -> None:
    g = _graph(operations=(_add("Tina", 2),))
    bu = bound_unknown_from_math_problem_graph(g)
    assert isinstance(bu, BoundUnknown)
    assert bu.symbol_id == "unknown_tina_apples"
    assert bu.state_index == "terminal"
    assert bu.question_form == "count"
    assert bu.expected_unit == "apples"


def test_bound_unknown_initial_identity_no_ops() -> None:
    g = _graph(operations=())
    bu = bound_unknown_from_math_problem_graph(g)
    assert bu.state_index == "initial"
    assert bu.question_form == "identity"


def test_bound_unknown_total_unknown_entity_none() -> None:
    g = _graph(
        entities=("Tina", "Sam"),
        initial_state=(
            InitialPossession(entity="Tina", quantity=Quantity(5, "apples")),
            InitialPossession(entity="Sam", quantity=Quantity(3, "apples")),
        ),
        operations=(_add("Tina", 2), _sub("Sam", 1)),
        unknown=Unknown(entity=None, unit="apples"),
    )
    bu = bound_unknown_from_math_problem_graph(g)
    assert bu.symbol_id == "unknown_total_apples"
    assert bu.state_index == "terminal"
    assert bu.question_form == "count"


def test_bound_unknown_deterministic_byte_equal() -> None:
    g = _graph(operations=(_add("Tina", 2),))
    a = bound_unknown_from_math_problem_graph(g)
    b = bound_unknown_from_math_problem_graph(g)
    assert a == b


def test_bound_unknown_refuses_non_graph_input() -> None:
    with pytest.raises(QuestionTargetError):
        bound_unknown_from_math_problem_graph(123)


# ---------------------------------------------------------------------------
# Defensive: input is read-only
# ---------------------------------------------------------------------------


def test_resolver_does_not_mutate_input() -> None:
    g = _graph(operations=(_add("Tina", 2),))
    before = g.canonical_bytes()
    _ = bound_unknown_from_math_problem_graph(g)
    after = g.canonical_bytes()
    assert before == after


# ---------------------------------------------------------------------------
# Parametric coverage of every operation kind in every question_form bucket
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "kind_op",
    [
        _add("Tina", 2),
        _sub("Tina", 1),
        _mul("Tina", 2),
        _div("Tina", 2),
    ],
)
def test_count_kinds_single_op_terminal_count(kind_op: Operation) -> None:
    g = _graph(operations=(kind_op,))
    bu = bound_unknown_from_math_problem_graph(g)
    assert bu.question_form == "count"
    assert bu.state_index == "terminal"


def test_transfer_count_form_for_actor() -> None:
    g = _graph(
        entities=("Tina", "Sam"),
        initial_state=(
            InitialPossession(entity="Tina", quantity=Quantity(5, "apples")),
            InitialPossession(entity="Sam", quantity=Quantity(3, "apples")),
        ),
        operations=(_transfer("Tina", "Sam", 1),),
        unknown=Unknown(entity="Tina", unit="apples"),
    )
    bu = bound_unknown_from_math_problem_graph(g)
    assert bu.question_form == "count"


def test_transfer_count_form_for_target() -> None:
    g = _graph(
        entities=("Tina", "Sam"),
        initial_state=(
            InitialPossession(entity="Tina", quantity=Quantity(5, "apples")),
            InitialPossession(entity="Sam", quantity=Quantity(3, "apples")),
        ),
        operations=(_transfer("Tina", "Sam", 1),),
        unknown=Unknown(entity="Sam", unit="apples"),
    )
    bu = bound_unknown_from_math_problem_graph(g)
    assert bu.question_form == "count"


# ---------------------------------------------------------------------------
# Unknown-entity boundary: comparison reference_actor counts as "touching"
# ---------------------------------------------------------------------------


def test_comparison_reference_actor_is_touching() -> None:
    # Unknown.entity == reference_actor (Sam). The compare_additive op
    # touches via the reference_actor edge → difference.
    g = _graph(
        entities=("Tina", "Sam"),
        initial_state=(
            InitialPossession(entity="Tina", quantity=Quantity(5, "apples")),
            InitialPossession(entity="Sam", quantity=Quantity(3, "apples")),
        ),
        operations=(_cmp_add("Tina", "Sam", 2),),
        unknown=Unknown(entity="Sam", unit="apples"),
    )
    bu = bound_unknown_from_math_problem_graph(g)
    assert bu.question_form == "difference"
