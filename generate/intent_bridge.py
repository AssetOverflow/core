"""generate/intent_bridge.py — connects intent classification to the realizer.

Bridges the gap between chat/runtime.py's articulation path (which resolves
Proposition slot-versors into raw word tokens) and the intent-aware realizer
pipeline (realize_semantic / realize_target in realizer.py, which are fully
implemented but were never called from the chat hot path).

Design constraints:
  - Deterministic: same input text + same field state → same surface
  - No LLM fallback
  - Falls back cleanly to the existing ArticulationPlan when the realizer
    cannot produce a non-empty surface (OOV-heavy input, UNKNOWN intent
    with no grounded obj slots)
  - Does not alter the ArticulationPlan dataclass or ChatResponse structure;
    only the .surface field is replaced when the bridge succeeds
"""

from __future__ import annotations

from generate.articulation import ArticulationPlan
from generate.graph_planner import (
    GraphEdge,
    GraphNode,
    PropositionGraph,
    Relation,
    ground_graph,
    plan_articulation,
)
from generate.intent import DialogueIntent, IntentTag, classify_intent
from generate.realizer import RealizedPlan, realize_semantic

_PENDING = "<pending>"
_PRIOR = "<prior>"
_EMPTY_INDICATORS = frozenset({_PENDING, _PRIOR, "...", ""})


def classify_intent_from_input(text: str) -> DialogueIntent:
    """Run the rule-based intent classifier against raw input text."""
    return classify_intent(text)


def build_graph_from_input(text: str, plan: ArticulationPlan) -> PropositionGraph:
    """Public helper: classify intent and build the pre-generation PropositionGraph.

    Returns the same graph that ``articulate_with_intent`` builds internally,
    but without grounding ``<pending>`` slots — the result is suitable for
    forward-constraint construction via ``build_graph_constraint`` BEFORE
    ``generate()`` runs (ADR-0046, ADR-0047).

    Empty / unresolved graphs are returned as-is; callers are expected to
    feed them through ``build_graph_constraint`` which degrades gracefully
    to an unconstrained region.
    """
    intent = classify_intent_from_input(text)
    return _build_graph_from_intent(intent, plan)


def _build_graph_from_intent(intent: DialogueIntent, plan: ArticulationPlan) -> PropositionGraph:
    """Build a minimal PropositionGraph from a classified intent and an ArticulationPlan.

    Uses the resolved slot words from ArticulationPlan (subject, predicate, object)
    as the concrete node content, with the intent tag selecting the predicate.
    """
    from generate.graph_planner import _INTENT_PREDICATES  # noqa: PLC0415

    predicate = _INTENT_PREDICATES.get(intent.tag, "addresses")
    subject = intent.subject or plan.subject or ""
    obj = plan.object or plan.predicate or _PENDING

    graph = PropositionGraph()

    if intent.tag is IntentTag.COMPARISON:
        secondary = intent.secondary_subject or plan.object or plan.predicate or obj
        left = GraphNode(
            node_id="p0",
            subject=subject,
            predicate=predicate,
            obj=secondary,
            source_intent=intent.tag,
        )
        right = GraphNode(
            node_id="p1",
            subject=secondary,
            predicate=predicate,
            obj=subject,
            source_intent=intent.tag,
        )
        edge = GraphEdge(source="p0", target="p1", relation=Relation.CONTRAST)
        return graph.add_node(left).add_node(right).add_edge(edge)

    root = GraphNode(
        node_id="p0",
        subject=subject,
        predicate=predicate,
        obj=obj,
        source_intent=intent.tag,
    )
    return graph.add_node(root)


def _is_useful_surface(surface: str) -> bool:
    """Return True when the realized surface is non-empty and fully grounded."""
    if not surface or not surface.strip():
        return False
    for indicator in _EMPTY_INDICATORS:
        if indicator and indicator in surface:
            return False
    return True


def articulate_with_intent(
    text: str,
    plan: ArticulationPlan,
    recalled_words: tuple[str, ...] = (),
) -> str:
    """Return an intent-aware surface string for *plan*, or "" if none can be produced.

    Steps:
      1. Classify intent from raw input *text*
      2. Build a PropositionGraph from the intent + ArticulationPlan slot words
      3. Ground <pending> obj slots with *recalled_words* from generation result
      4. Plan articulation (topological walk)
      5. Realize via realize_semantic() for intent-specific templates
      6. Return the surface, or "" if the result is empty / ungrounded

    The caller (chat/runtime.py) should fall back to the existing
    ArticulationPlan.surface when this returns "".
    """
    intent = classify_intent_from_input(text)

    graph = _build_graph_from_intent(intent, plan)
    if recalled_words:
        graph = ground_graph(graph, recalled_words)

    articulation_target = plan_articulation(graph)
    realized: RealizedPlan = realize_semantic(articulation_target, graph)

    if not realized.surface or not realized.fragments:
        return ""

    surface = realized.surface
    if not _is_useful_surface(surface):
        return ""

    return surface
