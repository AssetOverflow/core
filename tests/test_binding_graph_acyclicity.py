"""ADR-0203 — acyclicity guard for the binding-graph dependency structure.

Two layers, both exercised here:

1. The **pure checker** (`find_cycle`) in isolation against synthetic adjacency
   graphs — no binding-graph construction. Cyclic graphs return the cycle;
   acyclic graphs return None; fails-loud under mutation (the equivalent
   cyclic/acyclic assertions are mutually constraining, so a neutered detector
   fails the suite).
2. The **construction-boundary enforcement** in
   `SemanticSymbolicBindingGraph.__post_init__` — a cyclic equation set raises
   `BindingGraphError(circular_dependency …)`; an acyclic set (including the
   math-adapter shape: fresh result symbol per op, deps point backward)
   constructs fine — the math-lane regression proof.
"""

from __future__ import annotations

import pytest

from generate.binding_graph import (
    CIRCULAR_DEPENDENCY,
    BindingGraphError,
    BoundEquation,
    SemanticSymbolicBindingGraph,
    SourceSpanLink,
    SymbolBinding,
    find_cycle,
)


# ---------------------------------------------------------------------------
# Layer 1 — pure checker, isolated
# ---------------------------------------------------------------------------

ACYCLIC_GRAPHS = [
    {},                                                         # empty
    {"a": frozenset()},                                         # single, no edges
    {"a": frozenset({"b"}), "b": frozenset({"c"})},             # linear chain
    {"a": frozenset({"b", "c"}), "b": frozenset({"d"}),
     "c": frozenset({"d"}), "d": frozenset()},                  # diamond / shared dep
    {"a": frozenset({"b", "c", "d"})},                          # leaves not defined by any eq
]


@pytest.mark.parametrize("graph", ACYCLIC_GRAPHS)
def test_acyclic_graphs_return_none(graph) -> None:
    assert find_cycle(graph) is None


CYCLIC_GRAPHS = [
    {"a": frozenset({"a"})},                                    # self-loop
    {"a": frozenset({"b"}), "b": frozenset({"a"})},             # 2-cycle
    {"a": frozenset({"b"}), "b": frozenset({"c"}),
     "c": frozenset({"a"})},                                    # 3-cycle
    {"t": frozenset({"a"}), "a": frozenset({"b"}),
     "b": frozenset({"c"}), "c": frozenset({"b"})},             # cycle with a tail (t→a→b→c→b)
]


@pytest.mark.parametrize("graph", CYCLIC_GRAPHS)
def test_cyclic_graphs_are_detected(graph) -> None:
    cycle = find_cycle(graph)
    assert cycle is not None
    # A reported cycle closes on itself and every hop is a real edge.
    assert cycle[0] == cycle[-1]
    for src, dst in zip(cycle, cycle[1:]):
        assert dst in graph[src], f"{src}->{dst} is not an edge"


def test_self_loop_reported_as_length_one_cycle() -> None:
    assert find_cycle({"x": frozenset({"x"})}) == ("x", "x")


def test_reported_cycle_is_deterministic() -> None:
    graph = {"a": frozenset({"b"}), "b": frozenset({"c"}), "c": frozenset({"a"})}
    assert find_cycle(graph) == find_cycle(graph)


# ---------------------------------------------------------------------------
# Construction fixtures (mirror tests/test_binding_graph_model.py helpers)
# ---------------------------------------------------------------------------


def _span() -> SourceSpanLink:
    return SourceSpanLink(source_id="src", start=0, end=3, text="xyz")


def _sym(symbol_id: str) -> SymbolBinding:
    return SymbolBinding(
        symbol_id=symbol_id,
        name=symbol_id,
        semantic_role="quantity",
        source_span=_span(),
        introduced_by="test",
    )


def _eq(lhs: str, deps: set[str]) -> BoundEquation:
    return BoundEquation(
        lhs_symbol_id=lhs,
        rhs_canonical=f"{lhs} := f({sorted(deps)})",
        dependencies=frozenset(deps),
        operation_kind="add",
        unit_proof="pending",
        admissibility_status="pending",
        source_span=_span(),
    )


# ---------------------------------------------------------------------------
# Layer 2 — enforcement at the shared construction boundary
# ---------------------------------------------------------------------------


def test_acyclic_equation_set_constructs() -> None:
    # r1 := f(x);  r2 := f(r1, y)   — strict DAG, edges point backward.
    syms = tuple(_sym(s) for s in ("x", "y", "r1", "r2"))
    eqs = (_eq("r1", {"x"}), _eq("r2", {"r1", "y"}))
    graph = SemanticSymbolicBindingGraph(symbols=syms, equations=eqs)
    assert len(graph.equations) == 2


def test_adapter_shape_is_acyclic_by_construction() -> None:
    # Mirrors the math adapter: each op result depends only on prior symbols.
    syms = tuple(_sym(s) for s in ("q0", "q1", "op_0", "op_1"))
    eqs = (
        _eq("op_0", {"q0", "q1"}),     # op_0 := q0 + q1
        _eq("op_1", {"op_0", "q1"}),   # op_1 := op_0 + q1  (chains forward)
    )
    graph = SemanticSymbolicBindingGraph(symbols=syms, equations=eqs)
    assert len(graph.equations) == 2


def test_two_cycle_equation_set_refuses() -> None:
    syms = (_sym("x"), _sym("y"))
    eqs = (_eq("x", {"y"}), _eq("y", {"x"}))  # x↔y circular dependency
    with pytest.raises(BindingGraphError) as exc:
        SemanticSymbolicBindingGraph(symbols=syms, equations=eqs)
    assert CIRCULAR_DEPENDENCY in str(exc.value)


def test_self_dependent_equation_refuses() -> None:
    syms = (_sym("x"),)
    eqs = (_eq("x", {"x"}),)  # x defined in terms of itself
    with pytest.raises(BindingGraphError) as exc:
        SemanticSymbolicBindingGraph(symbols=syms, equations=eqs)
    assert CIRCULAR_DEPENDENCY in str(exc.value)


def test_longer_cycle_equation_set_refuses() -> None:
    syms = tuple(_sym(s) for s in ("a", "b", "c"))
    eqs = (_eq("a", {"b"}), _eq("b", {"c"}), _eq("c", {"a"}))
    with pytest.raises(BindingGraphError) as exc:
        SemanticSymbolicBindingGraph(symbols=syms, equations=eqs)
    assert CIRCULAR_DEPENDENCY in str(exc.value)


def test_referential_integrity_still_enforced_before_cycle_check() -> None:
    # An unknown dependency is still the referential-integrity refusal, not a
    # cycle — the existing ADR-0132 invariant is unchanged.
    syms = (_sym("x"),)
    eqs = (_eq("x", {"ghost"}),)
    with pytest.raises(BindingGraphError) as exc:
        SemanticSymbolicBindingGraph(symbols=syms, equations=eqs)
    assert "unknown dependency" in str(exc.value)
    assert CIRCULAR_DEPENDENCY not in str(exc.value)
