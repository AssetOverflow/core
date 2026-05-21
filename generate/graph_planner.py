"""Graph planner — converts a PropositionGraph into an ArticulationTarget.

The planner walks the graph in topological order and emits an ordered
sequence of articulation steps that the downstream generation pipeline
can execute. Each step carries the proposition node ID, the rhetorical
move, and any constraints inherited from intent classification.
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from enum import Enum, unique

from generate.intent import DialogueIntent, IntentTag


@unique
class Relation(Enum):
    ELABORATION = "elaboration"
    CAUSE = "cause"
    CONTRAST = "contrast"
    SEQUENCE = "sequence"
    CORRECTION = "correction"
    CONJUNCTION = "conjunction"
    DISJUNCTION = "disjunction"
    COMPLEMENT = "complement"
    RELATIVE = "relative"


@unique
class RhetoricalMove(Enum):
    ASSERT = "assert"
    ELABORATE = "elaborate"
    CONTRAST = "contrast"
    SEQUENCE = "sequence"
    CORRECT = "correct"


@dataclass(frozen=True, slots=True)
class GraphEdge:
    source: str
    target: str
    relation: Relation

    def as_dict(self) -> dict[str, str]:
        return {
            "source": self.source,
            "target": self.target,
            "relation": self.relation.value,
        }


@dataclass(frozen=True, slots=True)
class GraphNode:
    node_id: str
    subject: str
    predicate: str
    obj: str
    source_intent: IntentTag

    def as_dict(self) -> dict[str, str]:
        return {
            "node_id": self.node_id,
            "subject": self.subject,
            "predicate": self.predicate,
            "object": self.obj,
            "source_intent": self.source_intent.value,
        }


@dataclass(frozen=True, slots=True)
class PropositionGraph:
    nodes: tuple[GraphNode, ...] = ()
    edges: tuple[GraphEdge, ...] = ()

    def add_node(self, node: GraphNode) -> PropositionGraph:
        return PropositionGraph(nodes=(*self.nodes, node), edges=self.edges)

    def add_edge(self, edge: GraphEdge) -> PropositionGraph:
        return PropositionGraph(nodes=self.nodes, edges=(*self.edges, edge))

    def roots(self) -> tuple[str, ...]:
        targets = frozenset(e.target for e in self.edges)
        return tuple(n.node_id for n in self.nodes if n.node_id not in targets)

    def topo_order(self) -> tuple[str, ...]:
        """Kahn's topological sort over the graph's edges.

        Comb pass 2026-05-21 — pre-fix this implementation had two
        compounding inefficiencies:

          * ``queue.pop(0)`` on a list is O(N) per pop ⇒ O(N²) total
          * The inner ``for e in self.edges`` rescanned every edge on
            every iteration ⇒ O(N × E) overall

        Properly implemented Kahn's is O(N + E) and produces the same
        deterministic order for the same input (queue seeded with
        sorted zero-in-degree nodes; ties on later iterations break
        by insertion order, identical to the pre-fix list).

        Today's graphs are 1–2 nodes so cost is invisible — but
        ADR-0089 Phase C2 (compound-intent multi-node dispatch) and
        ADR-0088 Phase B (grounded realizer) both make multi-node
        graphs realistic on the hot path.  Fix lands before the
        usage scales.
        """
        # Build out-edge adjacency once: O(E).
        out_edges: dict[str, list[str]] = defaultdict(list)
        in_degree: dict[str, int] = {n.node_id: 0 for n in self.nodes}
        for e in self.edges:
            out_edges[e.source].append(e.target)
            in_degree[e.target] = in_degree.get(e.target, 0) + 1
        # Seed with sorted zero-in-degree nodes (deterministic).
        queue: deque[str] = deque(
            sorted(nid for nid, deg in in_degree.items() if deg == 0)
        )
        order: list[str] = []
        while queue:
            nid = queue.popleft()  # O(1) on a deque
            order.append(nid)
            # Decrement in-degree of direct successors only: O(deg(nid))
            # amortised to O(E) total across the loop.
            for target in out_edges[nid]:
                in_degree[target] -= 1
                if in_degree[target] == 0:
                    queue.append(target)
        return tuple(order)

    def as_dict(self) -> dict[str, object]:
        return {
            "nodes": tuple(n.as_dict() for n in self.nodes),
            "edges": tuple(e.as_dict() for e in self.edges),
        }

    def to_json(self) -> str:
        import json
        return json.dumps(self.as_dict(), sort_keys=True)


@dataclass(frozen=True, slots=True)
class ArticulationStep:
    node_id: str
    move: RhetoricalMove
    predicate: str
    subject: str
    negated: bool = False
    quantifier: str | None = None
    tense: str | None = None
    aspect: str | None = None

    def as_dict(self) -> dict[str, str]:
        return {
            "node_id": self.node_id,
            "move": self.move.value,
            "predicate": self.predicate,
            "subject": self.subject,
        }


@dataclass(frozen=True, slots=True)
class ArticulationTarget:
    steps: tuple[ArticulationStep, ...]
    source_intent: IntentTag

    def as_dict(self) -> dict[str, object]:
        return {
            "steps": tuple(s.as_dict() for s in self.steps),
            "source_intent": self.source_intent.value,
        }


_RELATION_TO_MOVE: dict[Relation, RhetoricalMove] = {
    Relation.ELABORATION: RhetoricalMove.ELABORATE,
    Relation.CAUSE: RhetoricalMove.ELABORATE,
    Relation.CONTRAST: RhetoricalMove.CONTRAST,
    Relation.SEQUENCE: RhetoricalMove.SEQUENCE,
    Relation.CORRECTION: RhetoricalMove.CORRECT,
}


_INTENT_PREDICATES: dict[IntentTag, str] = {
    IntentTag.DEFINITION: "is_defined_as",
    IntentTag.CAUSE: "is_caused_by",
    IntentTag.PROCEDURE: "has_steps",
    IntentTag.COMPARISON: "contrasts_with",
    IntentTag.CORRECTION: "corrects",
    IntentTag.RECALL: "recalls",
    IntentTag.VERIFICATION: "is_verified_as",
}


def graph_from_intent(
    intent: DialogueIntent,
    *,
    prior_node_id: str | None = None,
) -> PropositionGraph:
    """Build a minimal proposition graph from a classified intent."""
    predicate = _INTENT_PREDICATES.get(intent.tag, "addresses")
    graph = PropositionGraph()

    if intent.tag is IntentTag.COMPARISON:
        left = GraphNode(
            node_id="p0",
            subject=intent.subject,
            predicate=predicate,
            obj=intent.secondary_subject or "<pending>",
            source_intent=intent.tag,
        )
        right = GraphNode(
            node_id="p1",
            subject=intent.secondary_subject or "<pending>",
            predicate=predicate,
            obj=intent.subject,
            source_intent=intent.tag,
        )
        edge = GraphEdge(source="p0", target="p1", relation=Relation.CONTRAST)
        return graph.add_node(left).add_node(right).add_edge(edge)

    if intent.tag is IntentTag.CORRECTION:
        root = GraphNode(
            node_id="p0",
            subject=intent.subject,
            predicate=predicate,
            obj=prior_node_id or "<prior>",
            source_intent=intent.tag,
        )
        graph = graph.add_node(root)
        if prior_node_id is not None:
            graph = graph.add_edge(
                GraphEdge(source="p0", target=prior_node_id, relation=Relation.CORRECTION)
            )
        return graph

    root = GraphNode(
        node_id="p0",
        subject=intent.subject,
        predicate=predicate,
        obj="<pending>",
        source_intent=intent.tag,
    )
    return graph.add_node(root)


def ground_graph(
    graph: PropositionGraph,
    recalled_words: tuple[str, ...],
) -> PropositionGraph:
    """Fill <pending> obj slots with recalled words from vault recall.

    Each node whose obj is '<pending>' gets the next available recalled
    word. If there are more nodes than words, remaining slots stay as
    '<pending>'. Comparison nodes get paired words when available.
    """
    words = list(recalled_words)
    new_nodes: list[GraphNode] = []
    for node in graph.nodes:
        if node.obj == "<pending>" and words:
            obj = words.pop(0)
            new_nodes.append(GraphNode(
                node_id=node.node_id,
                subject=node.subject,
                predicate=node.predicate,
                obj=obj,
                source_intent=node.source_intent,
            ))
        else:
            new_nodes.append(node)
    return PropositionGraph(nodes=tuple(new_nodes), edges=graph.edges)


def plan_articulation(graph: PropositionGraph) -> ArticulationTarget:
    """Walk *graph* in topological order and emit an articulation target."""
    node_map = {n.node_id: n for n in graph.nodes}
    incoming: dict[str, Relation | None] = {n.node_id: None for n in graph.nodes}
    for edge in graph.edges:
        if edge.target in incoming:
            incoming[edge.target] = edge.relation

    source_intent = IntentTag.UNKNOWN
    if graph.nodes:
        source_intent = graph.nodes[0].source_intent

    steps: list[ArticulationStep] = []
    for node_id in graph.topo_order():
        node = node_map.get(node_id)
        if node is None:
            continue
        relation = incoming.get(node_id)
        move = _RELATION_TO_MOVE.get(relation, RhetoricalMove.ASSERT) if relation is not None else RhetoricalMove.ASSERT
        steps.append(
            ArticulationStep(
                node_id=node_id,
                move=move,
                predicate=node.predicate,
                subject=node.subject,
            )
        )

    return ArticulationTarget(steps=tuple(steps), source_intent=source_intent)
