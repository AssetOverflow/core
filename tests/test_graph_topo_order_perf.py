"""``PropositionGraph.topo_order`` Kahn's correctness (comb pass 2026-05-21).

Pre-fix the implementation was O(N²) on the outer loop (``queue.pop(0)``
on a list) and O(N × E) overall because it rescanned all edges every
iteration.  These tests pin Kahn's correctness on multi-node graphs
since today's production graphs are too small (1–2 nodes) to exercise
the algorithm — ADR-0089 Phase C2 (compound-intent multi-node
dispatch) is the consumer this fix prepares for.
"""

from __future__ import annotations

from generate.graph_planner import (
    GraphEdge,
    GraphNode,
    PropositionGraph,
    Relation,
)
from generate.intent import IntentTag


def _node(node_id: str) -> GraphNode:
    return GraphNode(
        node_id=node_id,
        subject=node_id,
        predicate="is_defined_as",
        obj="<pending>",
        source_intent=IntentTag.DEFINITION,
    )


def test_topo_order_chain() -> None:
    """A → B → C → D linearly orders root → leaf."""
    g = PropositionGraph(
        nodes=(_node("A"), _node("B"), _node("C"), _node("D")),
        edges=(
            GraphEdge(source="A", target="B", relation=Relation.SEQUENCE),
            GraphEdge(source="B", target="C", relation=Relation.SEQUENCE),
            GraphEdge(source="C", target="D", relation=Relation.SEQUENCE),
        ),
    )
    assert g.topo_order() == ("A", "B", "C", "D")


def test_topo_order_diamond() -> None:
    """A → B, A → C, B → D, C → D — both middle nodes precede D."""
    g = PropositionGraph(
        nodes=(_node("A"), _node("B"), _node("C"), _node("D")),
        edges=(
            GraphEdge(source="A", target="B", relation=Relation.ELABORATION),
            GraphEdge(source="A", target="C", relation=Relation.ELABORATION),
            GraphEdge(source="B", target="D", relation=Relation.SEQUENCE),
            GraphEdge(source="C", target="D", relation=Relation.SEQUENCE),
        ),
    )
    order = g.topo_order()
    assert order[0] == "A"
    assert order[-1] == "D"
    assert set(order[1:3]) == {"B", "C"}


def test_topo_order_two_disjoint_roots_sorted() -> None:
    """Two zero-in-degree roots → emitted in sorted order (deterministic)."""
    g = PropositionGraph(
        nodes=(_node("Z"), _node("A"), _node("M")),
        edges=(),
    )
    # All three are roots; sort_order pins determinism.
    assert g.topo_order() == ("A", "M", "Z")


def test_topo_order_preserves_byte_identity_on_single_node() -> None:
    """The current production graph shape: one node, no edges.

    Pre-fix output ``("p0",)`` is the post-fix output too — pins the
    null-lift invariant on today's hot path.
    """
    g = PropositionGraph(nodes=(_node("p0"),), edges=())
    assert g.topo_order() == ("p0",)


def test_topo_order_handles_empty_graph() -> None:
    assert PropositionGraph().topo_order() == ()


def test_topo_order_complexity_grows_linearly() -> None:
    """Smoke test: a 100-node chain returns in linear time and order.

    Pre-fix this would have been O(N²) on the queue and O(N × E)
    overall.  We don't assert wall-clock; we assert the output is
    correct on a size that would have been visibly slow.
    """
    nodes = tuple(_node(f"n{i:03d}") for i in range(100))
    edges = tuple(
        GraphEdge(source=f"n{i:03d}", target=f"n{i+1:03d}", relation=Relation.SEQUENCE)
        for i in range(99)
    )
    g = PropositionGraph(nodes=nodes, edges=edges)
    order = g.topo_order()
    assert len(order) == 100
    assert order[0] == "n000"
    assert order[-1] == "n099"
    # Every position must match the natural chain order.
    for i, nid in enumerate(order):
        assert nid == f"n{i:03d}"
