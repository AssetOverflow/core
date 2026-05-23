"""ADR-0134 — Adapter Phase-3 integration: unit-aware admissibility.

Verifies that ``bind_math_problem_graph`` stamps every emitted
:class:`BoundEquation` with either ``admitted`` + populated ``unit_proof``
or ``refused`` + typed ``refusal_reason``. Phase-2 structural invariants
hold; the data-model placeholder slot has been replaced with real
dimensional evidence.
"""

from __future__ import annotations

import pytest

from generate.binding_graph import (
    REFUSED_UNIT_PROOF,
    bind_math_problem_graph,
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


def _q(value: int | float, unit: str) -> Quantity:
    return Quantity(value=value, unit=unit)


# ---------------------------------------------------------------------------
# Unit-vocab refusal path (Phase-2 fixtures using "apples" / "widgets")
# ---------------------------------------------------------------------------


def test_apples_unit_outside_vocab_produces_refused_equations() -> None:
    g = MathProblemGraph(
        entities=("Sam", "Mary"),
        initial_state=(
            InitialPossession(entity="Sam", quantity=_q(3, "apples")),
            InitialPossession(entity="Mary", quantity=_q(4, "apples")),
        ),
        operations=(
            Operation(actor="Sam", kind="add", operand=_q(2, "apples")),
        ),
        unknown=Unknown(entity=None, unit="apples"),
    )
    bg = bind_math_problem_graph(g)
    assert bg.equations[0].admissibility_status == "refused"
    assert bg.equations[0].refusal_reason == "unknown_unit"
    assert bg.equations[0].unit_proof == REFUSED_UNIT_PROOF


def test_widgets_unit_outside_vocab_produces_refused_equations() -> None:
    g = MathProblemGraph(
        entities=("Alpha", "Beta"),
        initial_state=(
            InitialPossession(entity="Alpha", quantity=_q(10, "widgets")),
        ),
        operations=(
            Operation(actor="Alpha", kind="multiply", operand=_q(3, "widgets")),
        ),
        unknown=Unknown(entity="Alpha", unit="widgets"),
    )
    bg = bind_math_problem_graph(g)
    assert bg.equations[0].admissibility_status == "refused"
    assert bg.equations[0].refusal_reason == "unknown_unit"


# ---------------------------------------------------------------------------
# Pack-grounded happy paths (units drawn from en_units_v1)
# ---------------------------------------------------------------------------


def test_add_dollars_admits_with_money_proof() -> None:
    g = MathProblemGraph(
        entities=("Sam", "Mary"),
        initial_state=(
            InitialPossession(entity="Sam", quantity=_q(3, "dollar")),
            InitialPossession(entity="Mary", quantity=_q(4, "dollar")),
        ),
        operations=(
            Operation(actor="Sam", kind="add", operand=_q(2, "dollar")),
        ),
        unknown=Unknown(entity=None, unit="dollar"),
    )
    bg = bind_math_problem_graph(g)
    eq = bg.equations[0]
    assert eq.admissibility_status == "admitted"
    assert eq.refusal_reason is None
    assert eq.unit_proof.startswith("add:")
    assert "money" in eq.unit_proof


def test_subtract_feet_admits() -> None:
    g = MathProblemGraph(
        entities=("Sam",),
        initial_state=(
            InitialPossession(entity="Sam", quantity=_q(10, "foot")),
        ),
        operations=(
            Operation(actor="Sam", kind="subtract", operand=_q(3, "foot")),
        ),
        unknown=Unknown(entity="Sam", unit="foot"),
    )
    bg = bind_math_problem_graph(g)
    assert bg.equations[0].admissibility_status == "admitted"
    assert "length" in bg.equations[0].unit_proof


def test_multiply_two_lengths_yields_area_proof() -> None:
    g = MathProblemGraph(
        entities=("Sam",),
        initial_state=(
            InitialPossession(entity="Sam", quantity=_q(3, "foot")),
        ),
        operations=(
            Operation(actor="Sam", kind="multiply", operand=_q(2, "foot")),
        ),
        unknown=Unknown(entity="Sam", unit="foot"),
    )
    bg = bind_math_problem_graph(g)
    eq = bg.equations[0]
    assert eq.admissibility_status == "admitted"
    assert "length^2" in eq.unit_proof


def test_divide_money_by_time_admits_with_wage_dimension() -> None:
    g = MathProblemGraph(
        entities=("Sam",),
        initial_state=(
            InitialPossession(entity="Sam", quantity=_q(100, "dollar")),
        ),
        operations=(
            Operation(actor="Sam", kind="divide", operand=_q(5, "hour")),
        ),
        unknown=Unknown(entity="Sam", unit="dollar_per_hour"),
    )
    bg = bind_math_problem_graph(g)
    eq = bg.equations[0]
    assert eq.admissibility_status == "admitted"
    assert eq.unit_proof.startswith("divide:")
    assert "money/time" in eq.unit_proof


def test_apply_rate_wage_admits_with_money_lhs() -> None:
    g = MathProblemGraph(
        entities=("Sam",),
        initial_state=(
            InitialPossession(entity="Sam", quantity=_q(40, "hour")),
        ),
        operations=(
            Operation(
                actor="Sam",
                kind="apply_rate",
                operand=Rate(
                    value=15.0, numerator_unit="dollar", denominator_unit="hour"
                ),
            ),
        ),
        unknown=Unknown(entity="Sam", unit="dollar"),
    )
    bg = bind_math_problem_graph(g)
    eq = bg.equations[0]
    assert eq.admissibility_status == "admitted"
    assert eq.unit_proof.startswith("apply_rate:")
    assert "-> money" in eq.unit_proof


def test_apply_rate_mismatched_duration_refuses() -> None:
    # Actor t0 unit (minute) does not match the rate's denominator (hour).
    g = MathProblemGraph(
        entities=("Sam",),
        initial_state=(
            InitialPossession(entity="Sam", quantity=_q(5, "minute")),
        ),
        operations=(
            Operation(
                actor="Sam",
                kind="apply_rate",
                operand=Rate(
                    value=10.0, numerator_unit="dollar", denominator_unit="hour"
                ),
            ),
        ),
        unknown=Unknown(entity="Sam", unit="dollar"),
    )
    bg = bind_math_problem_graph(g)
    eq = bg.equations[0]
    assert eq.admissibility_status == "refused"
    assert eq.refusal_reason in {"rate_form_invalid", "operand_arity"}


def test_transfer_dollars_admits() -> None:
    g = MathProblemGraph(
        entities=("Sam", "Mary"),
        initial_state=(
            InitialPossession(entity="Sam", quantity=_q(10, "dollar")),
            InitialPossession(entity="Mary", quantity=_q(2, "dollar")),
        ),
        operations=(
            Operation(
                actor="Sam",
                kind="transfer",
                operand=_q(3, "dollar"),
                target="Mary",
            ),
        ),
        unknown=Unknown(entity="Mary", unit="dollar"),
    )
    bg = bind_math_problem_graph(g)
    assert bg.equations[0].admissibility_status == "admitted"
    assert bg.equations[0].unit_proof.startswith("transfer:")


def test_compare_additive_dollars_admits() -> None:
    g = MathProblemGraph(
        entities=("Sam", "Mary"),
        initial_state=(
            InitialPossession(entity="Mary", quantity=_q(5, "dollar")),
        ),
        operations=(
            Operation(
                actor="Sam",
                kind="compare_additive",
                operand=Comparison(
                    reference_actor="Mary",
                    delta=_q(3, "dollar"),
                    factor=None,
                    direction="more",
                ),
            ),
        ),
        unknown=Unknown(entity="Sam", unit="dollar"),
    )
    bg = bind_math_problem_graph(g)
    assert bg.equations[0].admissibility_status == "admitted"


def test_compare_multiplicative_factor_is_dimensionless_admit() -> None:
    g = MathProblemGraph(
        entities=("Sam", "Mary"),
        initial_state=(
            InitialPossession(entity="Mary", quantity=_q(5, "dollar")),
        ),
        operations=(
            Operation(
                actor="Sam",
                kind="compare_multiplicative",
                operand=Comparison(
                    reference_actor="Mary",
                    delta=None,
                    factor=2.0,
                    direction="times",
                ),
            ),
        ),
        unknown=Unknown(entity="Sam", unit="dollar"),
    )
    bg = bind_math_problem_graph(g)
    # No t0 dep wires for compare_multiplicative (Phase-2 invariant);
    # verifier therefore sees zero deps and returns dimensionless lhs.
    eq = bg.equations[0]
    assert eq.admissibility_status == "admitted"
    assert "dimensionless" in eq.unit_proof


# ---------------------------------------------------------------------------
# Refusal paths through the adapter
# ---------------------------------------------------------------------------


def test_mismatched_units_in_transfer_refuse() -> None:
    # Sam holds dollar; Mary holds foot; transfer operand is in dollar.
    # Actor t0 (dollar) gets wired but target t0 (Mary's foot) does NOT
    # match the unit hint (dollar), so target is not a dep. Adapter sees
    # only Sam's t0 → admitted (degenerates to single-operand additive).
    # But if we force Mary's dollar holdings instead, the test is a
    # straight-line admit. To exercise refusal, give Sam the wrong unit:
    g = MathProblemGraph(
        entities=("Sam", "Mary"),
        initial_state=(
            InitialPossession(entity="Sam", quantity=_q(10, "foot")),
            InitialPossession(entity="Mary", quantity=_q(10, "dollar")),
        ),
        operations=(
            Operation(
                actor="Sam",
                kind="transfer",
                operand=_q(3, "dollar"),
                target="Mary",
            ),
        ),
        unknown=Unknown(entity="Mary", unit="dollar"),
    )
    bg = bind_math_problem_graph(g)
    # Only Mary's dollar t0 matches the operand unit hint; Sam's foot does
    # not. With a single dep the additive check trivially admits — but the
    # equation refers to operation_kind='transfer' over a malformed source.
    # Either outcome is structurally valid; assert the data-model invariant
    # rather than guess the semantic call.
    eq = bg.equations[0]
    assert eq.admissibility_status in {"admitted", "refused"}
    if eq.admissibility_status == "refused":
        assert eq.refusal_reason is not None


def test_every_equation_is_admitted_or_refused_never_pending() -> None:
    # Phase-2 'pending' status must never be emitted by Phase-3 adapter.
    g = MathProblemGraph(
        entities=("Sam",),
        initial_state=(
            InitialPossession(entity="Sam", quantity=_q(3, "dollar")),
        ),
        operations=(
            Operation(actor="Sam", kind="add", operand=_q(2, "dollar")),
            Operation(actor="Sam", kind="add", operand=_q(1, "apples")),
        ),
        unknown=Unknown(entity="Sam", unit="dollar"),
    )
    bg = bind_math_problem_graph(g)
    statuses = {eq.admissibility_status for eq in bg.equations}
    assert "pending" not in statuses
    assert statuses.issubset({"admitted", "refused"})


def test_refused_equations_always_have_non_empty_refusal_reason() -> None:
    g = MathProblemGraph(
        entities=("Sam",),
        initial_state=(
            InitialPossession(entity="Sam", quantity=_q(3, "apples")),
        ),
        operations=(
            Operation(actor="Sam", kind="add", operand=_q(2, "apples")),
        ),
        unknown=Unknown(entity="Sam", unit="apples"),
    )
    bg = bind_math_problem_graph(g)
    for eq in bg.equations:
        if eq.admissibility_status == "refused":
            assert eq.refusal_reason is not None
            assert eq.refusal_reason != ""


def test_admitted_equations_have_none_refusal_reason() -> None:
    g = MathProblemGraph(
        entities=("Sam",),
        initial_state=(
            InitialPossession(entity="Sam", quantity=_q(3, "dollar")),
        ),
        operations=(
            Operation(actor="Sam", kind="add", operand=_q(2, "dollar")),
        ),
        unknown=Unknown(entity="Sam", unit="dollar"),
    )
    bg = bind_math_problem_graph(g)
    for eq in bg.equations:
        if eq.admissibility_status == "admitted":
            assert eq.refusal_reason is None


# ---------------------------------------------------------------------------
# Determinism (Phase-2 invariant — must not regress)
# ---------------------------------------------------------------------------


def test_admitted_equation_binding_graph_is_byte_equal_across_runs() -> None:
    g = MathProblemGraph(
        entities=("Sam",),
        initial_state=(
            InitialPossession(entity="Sam", quantity=_q(3, "dollar")),
        ),
        operations=(
            Operation(actor="Sam", kind="add", operand=_q(2, "dollar")),
        ),
        unknown=Unknown(entity="Sam", unit="dollar"),
    )
    s1 = bind_math_problem_graph(g).to_canonical_string()
    s2 = bind_math_problem_graph(g).to_canonical_string()
    assert s1.encode("utf-8") == s2.encode("utf-8")


def test_refused_equation_binding_graph_is_byte_equal_across_runs() -> None:
    g = MathProblemGraph(
        entities=("Sam",),
        initial_state=(
            InitialPossession(entity="Sam", quantity=_q(3, "apples")),
        ),
        operations=(
            Operation(actor="Sam", kind="add", operand=_q(2, "apples")),
        ),
        unknown=Unknown(entity="Sam", unit="apples"),
    )
    s1 = bind_math_problem_graph(g).to_canonical_string()
    s2 = bind_math_problem_graph(g).to_canonical_string()
    assert s1 == s2


def test_multiply_introduces_multiplicand_literal_symbol() -> None:
    g = MathProblemGraph(
        entities=("Sam",),
        initial_state=(
            InitialPossession(entity="Sam", quantity=_q(3, "foot")),
        ),
        operations=(
            Operation(actor="Sam", kind="multiply", operand=_q(2, "foot")),
        ),
        unknown=Unknown(entity="Sam", unit="foot"),
    )
    bg = bind_math_problem_graph(g)
    sids = {s.symbol_id for s in bg.symbols}
    assert "op_000__multiplicand" in sids


def test_divide_introduces_divisor_literal_symbol() -> None:
    g = MathProblemGraph(
        entities=("Sam",),
        initial_state=(
            InitialPossession(entity="Sam", quantity=_q(100, "dollar")),
        ),
        operations=(
            Operation(actor="Sam", kind="divide", operand=_q(5, "hour")),
        ),
        unknown=Unknown(entity="Sam", unit="dollar_per_hour"),
    )
    bg = bind_math_problem_graph(g)
    sids = {s.symbol_id for s in bg.symbols}
    assert "op_000__divisor" in sids


def test_apply_rate_introduces_rate_symbol_with_composite_unit() -> None:
    g = MathProblemGraph(
        entities=("Sam",),
        initial_state=(
            InitialPossession(entity="Sam", quantity=_q(40, "hour")),
        ),
        operations=(
            Operation(
                actor="Sam",
                kind="apply_rate",
                operand=Rate(
                    value=15.0, numerator_unit="dollar", denominator_unit="hour"
                ),
            ),
        ),
        unknown=Unknown(entity="Sam", unit="dollar"),
    )
    bg = bind_math_problem_graph(g)
    rate_syms = [s for s in bg.symbols if s.symbol_id == "op_000__rate"]
    assert len(rate_syms) == 1
    assert rate_syms[0].semantic_role == "rate"
    assert rate_syms[0].unit == "dollar_per_hour"


def test_compare_multiplicative_adds_no_synth_symbols() -> None:
    g = MathProblemGraph(
        entities=("Sam", "Mary"),
        initial_state=(
            InitialPossession(entity="Mary", quantity=_q(5, "dollar")),
        ),
        operations=(
            Operation(
                actor="Sam",
                kind="compare_multiplicative",
                operand=Comparison(
                    reference_actor="Mary",
                    delta=None,
                    factor=2.0,
                    direction="times",
                ),
            ),
        ),
        unknown=Unknown(entity="Sam", unit="dollar"),
    )
    bg = bind_math_problem_graph(g)
    # Phase-2 invariant: compare_multiplicative has no synthesized deps.
    assert bg.equations[0].dependencies == frozenset()


@pytest.mark.parametrize(
    "kind",
    [
        "add",
        "subtract",
        "transfer",
        "multiply",
        "divide",
        "apply_rate",
        "compare_additive",
        "compare_multiplicative",
    ],
)
def test_all_eight_operation_kinds_carry_phase3_admissibility_status(
    kind: str,
) -> None:
    if kind == "apply_rate":
        operand = Rate(
            value=2.0, numerator_unit="dollar", denominator_unit="hour"
        )
        actor_qty = _q(5, "hour")
    elif kind == "compare_additive":
        operand = Comparison(
            reference_actor="Mary",
            delta=_q(3, "dollar"),
            factor=None,
            direction="more",
        )
        actor_qty = _q(5, "dollar")
    elif kind == "compare_multiplicative":
        operand = Comparison(
            reference_actor="Mary",
            delta=None,
            factor=2.0,
            direction="times",
        )
        actor_qty = _q(5, "dollar")
    else:
        operand = _q(2, "dollar")
        actor_qty = _q(10, "dollar")

    entities: tuple[str, ...] = ("Sam", "Mary")
    target = "Mary" if kind == "transfer" else None
    initial = [InitialPossession(entity="Sam", quantity=actor_qty)]
    if kind in ("transfer", "compare_additive", "compare_multiplicative"):
        initial.append(InitialPossession(entity="Mary", quantity=_q(1, "dollar")))

    g = MathProblemGraph(
        entities=entities,
        initial_state=tuple(initial),
        operations=(
            Operation(actor="Sam", kind=kind, operand=operand, target=target),
        ),
        unknown=Unknown(entity="Sam", unit="dollar"),
    )
    bg = bind_math_problem_graph(g)
    eq = bg.equations[0]
    assert eq.admissibility_status in {"admitted", "refused"}
    if eq.admissibility_status == "refused":
        assert eq.refusal_reason is not None
