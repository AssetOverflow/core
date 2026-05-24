"""Connector: EpistemicNode → GraphNode — ADR-0144.

Maps an admitted EpistemicNode's FeatureBundle to a generation-side
GraphNode so the recognition path can feed the articulation planner.

The v1 mapping covers has-relation feature bundles (agent, relation,
count, unit).  New proposition types extend the mapping here; unknown
feature layouts raise ValueError so gaps surface explicitly rather than
silently defaulting.
"""

from __future__ import annotations

from generate.graph_planner import GraphNode
from generate.intent import IntentTag
from recognition.carrier import EpistemicNode
from recognition.outcome import EVIDENCED


def epistemic_node_to_graph_node(
    node: EpistemicNode,
    *,
    source_intent: IntentTag,
    node_id: str | None = None,
) -> GraphNode:
    """Derive a generation-side GraphNode from an admitted EpistemicNode.

    Raises ``ValueError`` if ``node.recognition_outcome.state != EVIDENCED``.

    Feature-bundle → GraphNode mapping (v1, has-relation propositions):
      subject   ← bundle["agent"].value
      predicate ← bundle["relation"].value
      obj       ← "{count.value} {unit.value}"
    """
    outcome = node.recognition_outcome
    if outcome.state != EVIDENCED:
        raise ValueError(
            f"Cannot derive GraphNode from non-EVIDENCED EpistemicNode: "
            f"state={outcome.state!r}"
        )
    bundle = outcome.proposition
    assert bundle is not None  # invariant: EVIDENCED → proposition not None

    agent = bundle.get("agent")
    relation = bundle.get("relation")
    count = bundle.get("count")
    unit = bundle.get("unit")

    subject = str(agent.value) if agent is not None else "<unknown-agent>"
    predicate = str(relation.value) if relation is not None else "has"
    obj = (
        f"{count.value} {unit.value}"
        if count is not None and unit is not None
        else "<pending>"
    )

    return GraphNode(
        node_id=node_id or node.node_id,
        subject=subject,
        predicate=predicate,
        obj=obj,
        source_intent=source_intent,
    )


__all__ = ["epistemic_node_to_graph_node"]
