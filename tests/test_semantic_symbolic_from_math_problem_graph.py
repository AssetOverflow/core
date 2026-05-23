from __future__ import annotations

from generate.math_problem_graph import (
    InitialPossession,
    MathProblemGraph,
    Operation,
    Quantity,
    Rate,
    Unknown,
)
from semantic_symbolic.from_math_problem_graph import (
    binding_graph_from_math_problem_graph,
)
from semantic_symbolic.serialization import graph_hash


def _tina_rate_graph() -> MathProblemGraph:
    return MathProblemGraph(
        entities=("Tina",),
        initial_state=(),
        operations=(
            Operation(
                actor="Tina",
                kind="apply_rate",
                operand=Rate(
                    value=18,
                    numerator_unit="dollars",
                    denominator_unit="hour",
                ),
            ),
        ),
        unknown=Unknown(entity="Tina", unit="dollars"),
    )


def _sam_apples_graph() -> MathProblemGraph:
    return MathProblemGraph(
        entities=("Sam",),
        initial_state=(
            InitialPossession(
                entity="Sam",
                quantity=Quantity(value=5, unit="apples"),
            ),
        ),
        operations=(
            Operation(
                actor="Sam",
                kind="add",
                operand=Quantity(value=3, unit="apples"),
            ),
        ),
        unknown=Unknown(entity="Sam", unit="apples"),
    )


def test_adapter_preserves_unknown_context() -> None:
    graph = binding_graph_from_math_problem_graph(_sam_apples_graph())

    assert graph.unknowns[0].expected_unit_id == "apples"
    assert graph.unknowns[0].symbol_id == "sym_unknown_sam_apples"
    unknown_symbol = next(s for s in graph.symbols if s.symbol_id == graph.unknowns[0].symbol_id)
    assert unknown_symbol.entity_id == "entity_sam"
    assert unknown_symbol.unit_id == "apples"


def test_adapter_preserves_initial_fact_context() -> None:
    graph = binding_graph_from_math_problem_graph(_sam_apples_graph())

    fact = graph.facts[0]
    symbol = next(s for s in graph.symbols if s.symbol_id == fact.symbol_id)
    assert fact.value == "5"
    assert fact.unit_id == "apples"
    assert symbol.entity_id == "entity_sam"
    assert symbol.semantic_role == "quantity"


def test_adapter_creates_operation_equation() -> None:
    graph = binding_graph_from_math_problem_graph(_sam_apples_graph())

    assert len(graph.equations) == 1
    eq = graph.equations[0]
    assert eq.operator == "add"
    assert eq.lhs_symbol_id.startswith("sym_op_001_sam_apples")
    assert len(eq.rhs_symbol_ids) == 2
    assert eq.unit_proof == "operand unit apples preserved"


def test_adapter_preserves_rate_context() -> None:
    graph = binding_graph_from_math_problem_graph(_tina_rate_graph())

    rate_symbols = [s for s in graph.symbols if s.semantic_role == "rate"]
    assert len(rate_symbols) == 1
    assert rate_symbols[0].entity_id == "entity_tina"
    assert rate_symbols[0].unit_id == "dollars_per_hour"
    assert graph.equations[0].operator == "apply_rate"
    assert graph.equations[0].unit_proof == "dollars/hour applied"


def test_adapter_hash_is_deterministic() -> None:
    first = binding_graph_from_math_problem_graph(_sam_apples_graph())
    second = binding_graph_from_math_problem_graph(_sam_apples_graph())

    assert graph_hash(first) == graph_hash(second)


def test_adapter_graph_id_can_be_overridden() -> None:
    graph = binding_graph_from_math_problem_graph(
        _sam_apples_graph(),
        graph_id="explicit_graph_id",
    )

    assert graph.graph_id == "explicit_graph_id"
