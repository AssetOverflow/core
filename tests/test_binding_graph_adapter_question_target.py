"""ADR-0135 — Adapter integration tests for question-target binding.

Covers:
  - the adapter consumes ``bound_unknown_from_math_problem_graph`` and
    emits a single :class:`BoundUnknown` per graph with populated
    ``state_index`` + ``question_form`` fields;
  - byte-equal hash-stability across runs survives the Phase-4 wiring
    (Phase 2 invariant — value may differ from Phase 3 main, by design);
  - every Phase-2 / Phase-3 round-trip case still produces a
    well-formed binding graph;
  - intentionally-ambiguous inputs surface ``QuestionTargetError``
    (resolver refusal) — not silent coercion;
  - cross-collection invariant guards against bogus ``Operation``
    state-index pointing past ``len(equations)``.
"""

from __future__ import annotations

import hashlib

import pytest

from generate.binding_graph import (
    BindingGraphError,
    BoundEquation,
    BoundFact,
    BoundUnknown,
    Operation as StateIndexOperation,
    QuestionTargetError,
    SemanticSymbolicBindingGraph,
    SourceSpanLink,
    SymbolBinding,
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


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _g(
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


def _rate_op(actor: str, value: float, num: str, denom: str) -> Operation:
    return Operation(
        actor=actor,
        kind="apply_rate",
        operand=Rate(value=value, numerator_unit=num, denominator_unit=denom),
    )


def _cmp_add(actor: str, ref: str, delta: int, unit: str = "apples") -> Operation:
    return Operation(
        actor=actor,
        kind="compare_additive",
        operand=Comparison(
            reference_actor=ref,
            delta=Quantity(delta, unit),
            factor=None,
            direction="more",
        ),
    )


def _cmp_mul(actor: str, ref: str, factor: float) -> Operation:
    return Operation(
        actor=actor,
        kind="compare_multiplicative",
        operand=Comparison(
            reference_actor=ref, delta=None, factor=factor, direction="times"
        ),
    )


# ---------------------------------------------------------------------------
# Smoke: every Phase-2 round-trip case still emits a well-formed graph
# ---------------------------------------------------------------------------


def test_adapter_emits_single_bound_unknown() -> None:
    bg = bind_math_problem_graph(_g(operations=(_add("Tina", 2),)))
    assert len(bg.unknowns) == 1


def test_adapter_bound_unknown_terminal_count() -> None:
    bg = bind_math_problem_graph(_g(operations=(_add("Tina", 2),)))
    bu = bg.unknowns[0]
    assert bu.state_index == "terminal"
    assert bu.question_form == "count"
    assert bu.expected_unit == "apples"


def test_adapter_bound_unknown_initial_identity() -> None:
    bg = bind_math_problem_graph(_g(operations=()))
    bu = bg.unknowns[0]
    assert bu.state_index == "initial"
    assert bu.question_form == "identity"


def test_adapter_bound_unknown_total_via_apply_rate() -> None:
    g = _g(
        initial_state=(
            InitialPossession(entity="Tina", quantity=Quantity(8, "hours")),
        ),
        operations=(_rate_op("Tina", 12.5, "dollars", "hours"),),
        unknown=Unknown(entity="Tina", unit="dollars"),
    )
    bg = bind_math_problem_graph(g)
    assert bg.unknowns[0].question_form == "total"


def test_adapter_bound_unknown_rate_via_apply_rate() -> None:
    g = _g(
        initial_state=(
            InitialPossession(entity="Tina", quantity=Quantity(8, "hours")),
        ),
        operations=(_rate_op("Tina", 12.5, "dollars", "hours"),),
        unknown=Unknown(entity="Tina", unit="hours"),
    )
    bg = bind_math_problem_graph(g)
    assert bg.unknowns[0].question_form == "rate"


def test_adapter_bound_unknown_difference() -> None:
    g = _g(
        entities=("Tina", "Sam"),
        initial_state=(
            InitialPossession(entity="Tina", quantity=Quantity(5, "apples")),
            InitialPossession(entity="Sam", quantity=Quantity(3, "apples")),
        ),
        operations=(_cmp_add("Tina", "Sam", 2),),
    )
    bg = bind_math_problem_graph(g)
    assert bg.unknowns[0].question_form == "difference"


def test_adapter_bound_unknown_ratio() -> None:
    g = _g(
        entities=("Tina", "Sam"),
        initial_state=(
            InitialPossession(entity="Tina", quantity=Quantity(5, "apples")),
            InitialPossession(entity="Sam", quantity=Quantity(3, "apples")),
        ),
        operations=(_cmp_mul("Tina", "Sam", 2.0),),
    )
    bg = bind_math_problem_graph(g)
    assert bg.unknowns[0].question_form == "ratio"


# ---------------------------------------------------------------------------
# Hash-stability: byte-equal across runs (Phase 2 invariant)
# ---------------------------------------------------------------------------


def _digest(bg: SemanticSymbolicBindingGraph) -> str:
    return hashlib.sha256(bg.to_canonical_string().encode("utf-8")).hexdigest()


def test_byte_equal_across_runs_count() -> None:
    g = _g(operations=(_add("Tina", 2), _add("Tina", 3)))
    a = bind_math_problem_graph(g)
    b = bind_math_problem_graph(g)
    assert a.to_canonical_string() == b.to_canonical_string()
    assert _digest(a) == _digest(b)


def test_byte_equal_across_runs_identity() -> None:
    g = _g(operations=())
    a = bind_math_problem_graph(g)
    b = bind_math_problem_graph(g)
    assert a.to_canonical_string() == b.to_canonical_string()


def test_byte_equal_across_runs_difference() -> None:
    g = _g(
        entities=("Tina", "Sam"),
        initial_state=(
            InitialPossession(entity="Tina", quantity=Quantity(5, "apples")),
            InitialPossession(entity="Sam", quantity=Quantity(3, "apples")),
        ),
        operations=(_cmp_add("Tina", "Sam", 2),),
    )
    assert bind_math_problem_graph(g).to_canonical_string() == bind_math_problem_graph(
        g
    ).to_canonical_string()


def test_canonical_string_mentions_state_and_form() -> None:
    bg = bind_math_problem_graph(_g(operations=(_add("Tina", 2),)))
    s = bg.to_canonical_string()
    assert "state=terminal" in s
    assert "form=count" in s


def test_canonical_string_identity_form() -> None:
    bg = bind_math_problem_graph(_g(operations=()))
    s = bg.to_canonical_string()
    assert "state=initial" in s
    assert "form=identity" in s


# ---------------------------------------------------------------------------
# Refusal-first propagation: resolver refusals surface to caller
# ---------------------------------------------------------------------------


def test_adapter_propagates_apply_rate_unit_mismatch() -> None:
    g = _g(
        initial_state=(
            InitialPossession(entity="Tina", quantity=Quantity(8, "hours")),
        ),
        operations=(_rate_op("Tina", 12.5, num="dollars", denom="hours"),),
        unknown=Unknown(entity="Tina", unit="apples"),
    )
    with pytest.raises(QuestionTargetError) as exc:
        bind_math_problem_graph(g)
    assert exc.value.reason == "apply_rate_unit_mismatch"


# ---------------------------------------------------------------------------
# Cross-collection guard: Operation(operation_index) out of bounds
# ---------------------------------------------------------------------------


def _span(text: str = "x") -> SourceSpanLink:
    return SourceSpanLink(source_id="t", start=0, end=len(text), text=text)


def test_graph_refuses_operation_state_index_out_of_bounds() -> None:
    # Construct a manual graph: 1 equation (so equation_count == 1), but
    # the BoundUnknown points to Operation(operation_index=5) → refuse.
    lhs = "op_000_result"
    sym_q = SymbolBinding(
        symbol_id="q_x_apples_t0",
        name="x@t0",
        semantic_role="quantity",
        source_span=_span(),
        introduced_by="test",
        entity="x",
        unit="apples",
    )
    sym_r = SymbolBinding(
        symbol_id=lhs,
        name="r",
        semantic_role="quantity",
        source_span=_span(),
        introduced_by="test",
        entity="x",
    )
    sym_u = SymbolBinding(
        symbol_id="unknown_x_apples",
        name="u",
        semantic_role="unknown",
        source_span=_span(),
        introduced_by="test",
        entity="x",
        unit="apples",
    )
    fact = BoundFact(
        symbol_id="q_x_apples_t0", value="5", source_span=_span(), unit="apples"
    )
    eq = BoundEquation(
        lhs_symbol_id=lhs,
        rhs_canonical="add(x, 2 apples)",
        dependencies=frozenset({"q_x_apples_t0"}),
        operation_kind="add",
        unit_proof="apples",
        admissibility_status="admitted",
        source_span=_span(),
    )
    bu = BoundUnknown(
        symbol_id="unknown_x_apples",
        question_span=_span(),
        state_index=StateIndexOperation(operation_index=5),
        question_form="count",
    )
    with pytest.raises(BindingGraphError):
        SemanticSymbolicBindingGraph(
            symbols=(sym_q, sym_r, sym_u),
            facts=(fact,),
            equations=(eq,),
            unknowns=(bu,),
        )


def test_graph_accepts_operation_state_index_within_bounds() -> None:
    # Same shape, but operation_index=0 is within bounds (equation_count==1).
    lhs = "op_000_result"
    sym_q = SymbolBinding(
        symbol_id="q_x_apples_t0",
        name="x@t0",
        semantic_role="quantity",
        source_span=_span(),
        introduced_by="test",
        entity="x",
        unit="apples",
    )
    sym_r = SymbolBinding(
        symbol_id=lhs,
        name="r",
        semantic_role="quantity",
        source_span=_span(),
        introduced_by="test",
        entity="x",
    )
    sym_u = SymbolBinding(
        symbol_id="unknown_x_apples",
        name="u",
        semantic_role="unknown",
        source_span=_span(),
        introduced_by="test",
        entity="x",
        unit="apples",
    )
    fact = BoundFact(
        symbol_id="q_x_apples_t0", value="5", source_span=_span(), unit="apples"
    )
    eq = BoundEquation(
        lhs_symbol_id=lhs,
        rhs_canonical="add(x, 2 apples)",
        dependencies=frozenset({"q_x_apples_t0"}),
        operation_kind="add",
        unit_proof="apples",
        admissibility_status="admitted",
        source_span=_span(),
    )
    bu = BoundUnknown(
        symbol_id="unknown_x_apples",
        question_span=_span(),
        state_index=StateIndexOperation(operation_index=0),
        question_form="count",
    )
    bg = SemanticSymbolicBindingGraph(
        symbols=(sym_q, sym_r, sym_u),
        facts=(fact,),
        equations=(eq,),
        unknowns=(bu,),
    )
    assert bg.unknowns[0].state_index == StateIndexOperation(operation_index=0)


# ---------------------------------------------------------------------------
# MathProblemGraph is read-only (frozen) — assert in test as brief requires
# ---------------------------------------------------------------------------


def test_adapter_does_not_mutate_input_graph() -> None:
    g = _g(operations=(_add("Tina", 2),))
    before = g.canonical_bytes()
    _ = bind_math_problem_graph(g)
    after = g.canonical_bytes()
    assert before == after


def test_math_problem_graph_is_frozen() -> None:
    g = _g()
    with pytest.raises((AttributeError, Exception)):
        g.unknown = Unknown(entity="Tina", unit="apples")  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Symbol binding for the unknown still emitted (Phase 2 invariant)
# ---------------------------------------------------------------------------


def test_unknown_symbol_binding_still_emitted() -> None:
    bg = bind_math_problem_graph(_g(operations=(_add("Tina", 2),)))
    unk_syms = [s for s in bg.symbols if s.semantic_role == "unknown"]
    assert len(unk_syms) == 1
    assert unk_syms[0].symbol_id == "unknown_tina_apples"
    assert unk_syms[0].entity == "Tina"
    assert unk_syms[0].unit == "apples"


def test_unknown_symbol_id_matches_bound_unknown() -> None:
    bg = bind_math_problem_graph(_g(operations=(_add("Tina", 2),)))
    unk_sym = next(s for s in bg.symbols if s.semantic_role == "unknown")
    assert unk_sym.symbol_id == bg.unknowns[0].symbol_id


# ---------------------------------------------------------------------------
# Parametric: question_form is one of the closed vocabulary on smoke graphs
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "ops, expected_form",
    [
        ((), "identity"),
        ((_add("Tina", 1),), "count"),
        (
            (
                Operation(actor="Tina", kind="subtract", operand=Quantity(1, "apples")),
            ),
            "count",
        ),
        (
            (
                Operation(actor="Tina", kind="multiply", operand=Quantity(3, "apples")),
            ),
            "count",
        ),
        (
            (
                Operation(actor="Tina", kind="divide", operand=Quantity(2, "apples")),
            ),
            "count",
        ),
    ],
)
def test_adapter_form_table(ops, expected_form) -> None:
    bg = bind_math_problem_graph(_g(operations=ops))
    assert bg.unknowns[0].question_form == expected_form


def test_adapter_bound_unknown_is_instance() -> None:
    bg = bind_math_problem_graph(_g(operations=(_add("Tina", 1),)))
    assert isinstance(bg.unknowns[0], BoundUnknown)
