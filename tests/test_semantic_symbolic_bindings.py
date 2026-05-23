from __future__ import annotations

import pytest

from semantic_symbolic.bindings import (
    BindingGraphError,
    BoundConstraint,
    BoundEquation,
    BoundFact,
    BoundUnknown,
    SemanticSymbolicBindingGraph,
    SourceSpanLink,
    SymbolBinding,
)
from semantic_symbolic.serialization import (
    canonical_json,
    graph_hash,
)


@pytest.fixture()
def tina_graph() -> SemanticSymbolicBindingGraph:
    return SemanticSymbolicBindingGraph(
        graph_id="graph_tina_wage_v1",
        source_spans=(
            SourceSpanLink(
                span_id="span_001",
                text="Tina makes $18 per hour.",
            ),
            SourceSpanLink(
                span_id="span_002",
                text="She works 7 hours.",
            ),
            SourceSpanLink(
                span_id="span_003",
                text="How much does she earn?",
            ),
        ),
        symbols=(
            SymbolBinding(
                symbol_id="sym_rate_tina_wage_001",
                name="rate_tina_wage",
                semantic_role="rate",
                entity_id="entity_tina",
                unit_id="dollars_per_hour",
                source_span_id="span_001",
                introduced_by="fixture",
            ),
            SymbolBinding(
                symbol_id="sym_duration_tina_work_001",
                name="duration_tina_work",
                semantic_role="duration",
                entity_id="entity_tina",
                unit_id="hours",
                source_span_id="span_002",
                introduced_by="fixture",
            ),
            SymbolBinding(
                symbol_id="sym_earnings_tina_work_001",
                name="earnings_tina_work",
                semantic_role="unknown",
                entity_id="entity_tina",
                unit_id="dollars",
                source_span_id="span_003",
                introduced_by="fixture",
            ),
        ),
        facts=(
            BoundFact(
                fact_id="fact_rate_tina_001",
                symbol_id="sym_rate_tina_wage_001",
                value="18",
                unit_id="dollars_per_hour",
                source_span_id="span_001",
            ),
            BoundFact(
                fact_id="fact_duration_tina_001",
                symbol_id="sym_duration_tina_work_001",
                value="7",
                unit_id="hours",
                source_span_id="span_002",
            ),
        ),
        equations=(
            BoundEquation(
                equation_id="eq_earnings_001",
                lhs_symbol_id="sym_earnings_tina_work_001",
                operator="multiply",
                rhs_symbol_ids=(
                    "sym_rate_tina_wage_001",
                    "sym_duration_tina_work_001",
                ),
                unit_proof="dollars/hour * hour = dollars",
                depends_on=(
                    "fact_rate_tina_001",
                    "fact_duration_tina_001",
                ),
                source_span_ids=("span_001", "span_002"),
            ),
        ),
        unknowns=(
            BoundUnknown(
                unknown_id="unknown_earnings_tina_001",
                symbol_id="sym_earnings_tina_work_001",
                question_span_id="span_003",
                expected_unit_id="dollars",
            ),
        ),
        constraints=(
            BoundConstraint(
                constraint_id="constraint_unit_001",
                kind="unit_consistency",
                symbol_ids=(
                    "sym_rate_tina_wage_001",
                    "sym_duration_tina_work_001",
                    "sym_earnings_tina_work_001",
                ),
                description="rate * duration produces dollars",
            ),
        ),
    )


def test_graph_constructs_successfully(
    tina_graph: SemanticSymbolicBindingGraph,
) -> None:
    assert tina_graph.graph_id == "graph_tina_wage_v1"
    assert len(tina_graph.symbols) == 3
    assert len(tina_graph.equations) == 1


def test_duplicate_symbol_ids_rejected() -> None:
    with pytest.raises(BindingGraphError, match="duplicate symbol ids"):
        SemanticSymbolicBindingGraph(
            graph_id="bad_graph",
            source_spans=(
                SourceSpanLink(span_id="span_001", text="x"),
            ),
            symbols=(
                SymbolBinding(
                    symbol_id="dup",
                    name="a",
                    semantic_role="quantity",
                    entity_id=None,
                    unit_id=None,
                    source_span_id="span_001",
                    introduced_by="test",
                ),
                SymbolBinding(
                    symbol_id="dup",
                    name="b",
                    semantic_role="quantity",
                    entity_id=None,
                    unit_id=None,
                    source_span_id="span_001",
                    introduced_by="test",
                ),
            ),
            facts=(),
            equations=(),
            unknowns=(),
            constraints=(),
            source_spans=(
                SourceSpanLink(span_id="span_001", text="duplicate"),
            ),
        )


def test_missing_symbol_reference_rejected() -> None:
    with pytest.raises(BindingGraphError, match="references missing symbol"):
        SemanticSymbolicBindingGraph(
            graph_id="bad_ref",
            source_spans=(
                SourceSpanLink(span_id="span_001", text="x"),
            ),
            symbols=(),
            facts=(
                BoundFact(
                    fact_id="fact_001",
                    symbol_id="missing",
                    value="5",
                    unit_id=None,
                    source_span_id="span_001",
                ),
            ),
            equations=(),
            unknowns=(),
            constraints=(),
            source_spans=(
                SourceSpanLink(span_id="span_001", text="missing"),
            ),
        )


def test_canonical_json_is_stable(
    tina_graph: SemanticSymbolicBindingGraph,
) -> None:
    first = canonical_json(tina_graph)
    second = canonical_json(tina_graph)
    assert first == second


def test_graph_hash_is_order_independent(
    tina_graph: SemanticSymbolicBindingGraph,
) -> None:
    reordered = SemanticSymbolicBindingGraph(
        graph_id=tina_graph.graph_id,
        source_spans=tuple(reversed(tina_graph.source_spans)),
        symbols=tuple(reversed(tina_graph.symbols)),
        facts=tuple(reversed(tina_graph.facts)),
        equations=tina_graph.equations,
        unknowns=tina_graph.unknowns,
        constraints=tina_graph.constraints,
    )
    assert graph_hash(tina_graph) == graph_hash(reordered)


def test_graph_hash_changes_when_unit_changes(
    tina_graph: SemanticSymbolicBindingGraph,
) -> None:
    modified = SemanticSymbolicBindingGraph(
        graph_id=tina_graph.graph_id,
        source_spans=tina_graph.source_spans,
        symbols=(
            SymbolBinding(
                symbol_id="sym_rate_tina_wage_001",
                name="rate_tina_wage",
                semantic_role="rate",
                entity_id="entity_tina",
                unit_id="euros_per_hour",
                source_span_id="span_001",
                introduced_by="fixture",
            ),
            *tina_graph.symbols[1:],
        ),
        facts=tina_graph.facts,
        equations=tina_graph.equations,
        unknowns=tina_graph.unknowns,
        constraints=tina_graph.constraints,
    )
    assert graph_hash(tina_graph) != graph_hash(modified)
