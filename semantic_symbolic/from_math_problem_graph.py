"""Adapter from existing MathProblemGraph into SemanticSymbolicBindingGraph.

Phase SSBG-2: representation adapter only. This module does not change
parsing, solving, verification, or runtime behavior. It proves the new
binding graph can faithfully represent the current bounded math graph.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any

from generate.math_problem_graph import (
    Comparison,
    MathProblemGraph,
    Operation,
    Quantity,
    Rate,
)
from semantic_symbolic.bindings import (
    BoundEquation,
    BoundFact,
    BoundUnknown,
    SemanticSymbolicBindingGraph,
    SourceSpanLink,
    SymbolBinding,
)


def binding_graph_from_math_problem_graph(
    graph: MathProblemGraph,
    *,
    graph_id: str | None = None,
) -> SemanticSymbolicBindingGraph:
    """Convert a MathProblemGraph into a semantic-symbolic binding graph."""
    gid = graph_id or _graph_id(graph)
    source_spans = _source_spans(graph)
    symbols: list[SymbolBinding] = []
    facts: list[BoundFact] = []
    equations: list[BoundEquation] = []

    symbol_ids: set[str] = set()

    def add_symbol(
        *,
        symbol_id: str,
        name: str,
        role: str,
        entity_id: str | None,
        unit_id: str | None,
        source_span_id: str | None,
        introduced_by: str,
    ) -> str:
        if symbol_id in symbol_ids:
            return symbol_id
        symbol_ids.add(symbol_id)
        symbols.append(
            SymbolBinding(
                symbol_id=symbol_id,
                name=name,
                semantic_role=role,  # type: ignore[arg-type]
                entity_id=entity_id,
                unit_id=unit_id,
                source_span_id=source_span_id,
                introduced_by=introduced_by,
            )
        )
        return symbol_id

    for idx, initial in enumerate(graph.initial_state, start=1):
        span_id = f"span_initial_{idx:03d}"
        entity_slug = _slug(initial.entity)
        unit_slug = _unit_id(initial.quantity.unit)
        symbol_id = f"sym_quantity_{entity_slug}_{unit_slug}_initial"
        add_symbol(
            symbol_id=symbol_id,
            name=f"quantity_{entity_slug}_{unit_slug}_initial",
            role="quantity",
            entity_id=_entity_id(initial.entity),
            unit_id=unit_slug,
            source_span_id=span_id,
            introduced_by="MathProblemGraph.initial_state",
        )
        facts.append(
            BoundFact(
                fact_id=f"fact_initial_{idx:03d}",
                symbol_id=symbol_id,
                value=str(initial.quantity.value),
                unit_id=unit_slug,
                source_span_id=span_id,
            )
        )

    for idx, op in enumerate(graph.operations, start=1):
        span_id = f"span_operation_{idx:03d}"
        equation = _operation_to_equation(
            op,
            idx=idx,
            span_id=span_id,
            add_symbol=add_symbol,
        )
        equations.append(equation)

    unknown_span_id = "span_unknown_001"
    unknown_symbol_id = _unknown_symbol_id(graph)
    add_symbol(
        symbol_id=unknown_symbol_id,
        name=unknown_symbol_id.removeprefix("sym_"),
        role="unknown",
        entity_id=_entity_id(graph.unknown.entity) if graph.unknown.entity else None,
        unit_id=_unit_id(graph.unknown.unit),
        source_span_id=unknown_span_id,
        introduced_by="MathProblemGraph.unknown",
    )

    return SemanticSymbolicBindingGraph(
        graph_id=gid,
        symbols=tuple(symbols),
        facts=tuple(facts),
        equations=tuple(equations),
        unknowns=(
            BoundUnknown(
                unknown_id="unknown_001",
                symbol_id=unknown_symbol_id,
                question_span_id=unknown_span_id,
                expected_unit_id=_unit_id(graph.unknown.unit),
            ),
        ),
        constraints=(),
        source_spans=source_spans,
    )


def _operation_to_equation(
    op: Operation,
    *,
    idx: int,
    span_id: str,
    add_symbol: Any,
) -> BoundEquation:
    actor_slug = _slug(op.actor)
    lhs_unit = _operation_output_unit(op)
    lhs_symbol_id = f"sym_op_{idx:03d}_{actor_slug}_{_unit_id(lhs_unit)}"
    add_symbol(
        symbol_id=lhs_symbol_id,
        name=lhs_symbol_id.removeprefix("sym_"),
        role="quantity",
        entity_id=_entity_id(op.actor),
        unit_id=_unit_id(lhs_unit),
        source_span_id=span_id,
        introduced_by=f"MathProblemGraph.operation.{idx:03d}",
    )

    rhs_symbol_ids: list[str] = []
    actor_state = f"sym_state_{actor_slug}_{_unit_id(lhs_unit)}_before_op_{idx:03d}"
    add_symbol(
        symbol_id=actor_state,
        name=actor_state.removeprefix("sym_"),
        role="quantity",
        entity_id=_entity_id(op.actor),
        unit_id=_unit_id(lhs_unit),
        source_span_id=span_id,
        introduced_by=f"MathProblemGraph.operation.{idx:03d}.actor_state",
    )
    rhs_symbol_ids.append(actor_state)

    operand_symbol = _operand_symbol(op, idx, span_id, add_symbol)
    rhs_symbol_ids.append(operand_symbol)

    if op.target is not None:
        target_symbol = f"sym_target_{_slug(op.target)}_{_unit_id(lhs_unit)}_op_{idx:03d}"
        add_symbol(
            symbol_id=target_symbol,
            name=target_symbol.removeprefix("sym_"),
            role="quantity",
            entity_id=_entity_id(op.target),
            unit_id=_unit_id(lhs_unit),
            source_span_id=span_id,
            introduced_by=f"MathProblemGraph.operation.{idx:03d}.target",
        )
        rhs_symbol_ids.append(target_symbol)

    return BoundEquation(
        equation_id=f"eq_operation_{idx:03d}",
        lhs_symbol_id=lhs_symbol_id,
        operator=op.kind,
        rhs_symbol_ids=tuple(rhs_symbol_ids),
        unit_proof=_unit_proof(op),
        depends_on=(),
        source_span_ids=(span_id,),
    )


def _operand_symbol(op: Operation, idx: int, span_id: str, add_symbol: Any) -> str:
    operand = op.operand
    if isinstance(operand, Quantity):
        unit_id = _unit_id(operand.unit)
        symbol_id = f"sym_operand_{idx:03d}_{unit_id}"
        add_symbol(
            symbol_id=symbol_id,
            name=symbol_id.removeprefix("sym_"),
            role="quantity",
            entity_id=None,
            unit_id=unit_id,
            source_span_id=span_id,
            introduced_by=f"MathProblemGraph.operation.{idx:03d}.operand",
        )
        return symbol_id
    if isinstance(operand, Rate):
        unit_id = f"{_unit_id(operand.numerator_unit)}_per_{_unit_id(operand.denominator_unit)}"
        symbol_id = f"sym_rate_operand_{idx:03d}_{unit_id}"
        add_symbol(
            symbol_id=symbol_id,
            name=symbol_id.removeprefix("sym_"),
            role="rate",
            entity_id=_entity_id(op.actor),
            unit_id=unit_id,
            source_span_id=span_id,
            introduced_by=f"MathProblemGraph.operation.{idx:03d}.rate",
        )
        return symbol_id
    if isinstance(operand, Comparison):
        role = "difference" if operand.delta is not None else "ratio"
        symbol_id = f"sym_comparison_operand_{idx:03d}_{_slug(operand.direction)}"
        unit_id = _unit_id(operand.delta.unit) if operand.delta is not None else None
        add_symbol(
            symbol_id=symbol_id,
            name=symbol_id.removeprefix("sym_"),
            role=role,
            entity_id=_entity_id(operand.reference_actor),
            unit_id=unit_id,
            source_span_id=span_id,
            introduced_by=f"MathProblemGraph.operation.{idx:03d}.comparison",
        )
        return symbol_id
    raise TypeError(f"unsupported operand type {type(operand).__name__}")


def _source_spans(graph: MathProblemGraph) -> tuple[SourceSpanLink, ...]:
    spans: list[SourceSpanLink] = []
    for idx, initial in enumerate(graph.initial_state, start=1):
        spans.append(
            SourceSpanLink(
                span_id=f"span_initial_{idx:03d}",
                text=(
                    f"initial_state[{idx}]: {initial.entity} has "
                    f"{initial.quantity.value} {initial.quantity.unit}"
                ),
            )
        )
    for idx, op in enumerate(graph.operations, start=1):
        spans.append(
            SourceSpanLink(
                span_id=f"span_operation_{idx:03d}",
                text=f"operation[{idx}]: {op.as_json()}",
            )
        )
    spans.append(
        SourceSpanLink(
            span_id="span_unknown_001",
            text=f"unknown: {graph.unknown.as_json()}",
        )
    )
    return tuple(spans)


def _graph_id(graph: MathProblemGraph) -> str:
    digest = hashlib.sha256(graph.canonical_bytes()).hexdigest()[:16]
    return f"math_problem_graph_binding_{digest}"


def _unknown_symbol_id(graph: MathProblemGraph) -> str:
    entity = _slug(graph.unknown.entity or "total")
    return f"sym_unknown_{entity}_{_unit_id(graph.unknown.unit)}"


def _operation_output_unit(op: Operation) -> str:
    if isinstance(op.operand, Quantity):
        return op.operand.unit
    if isinstance(op.operand, Rate):
        return op.operand.numerator_unit
    if isinstance(op.operand, Comparison):
        if op.operand.delta is not None:
            return op.operand.delta.unit
        return "dimensionless"
    return "unknown"


def _unit_proof(op: Operation) -> str | None:
    if isinstance(op.operand, Rate):
        return f"{op.operand.numerator_unit}/{op.operand.denominator_unit} applied"
    if isinstance(op.operand, Quantity):
        return f"operand unit {op.operand.unit} preserved"
    if isinstance(op.operand, Comparison):
        return f"comparison direction {op.operand.direction} preserves referenced unit"
    return None


def _entity_id(entity: str) -> str:
    return f"entity_{_slug(entity)}"


def _unit_id(unit: str) -> str:
    return _slug(unit)


def _slug(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    value = value.strip("_")
    return value or "unnamed"
