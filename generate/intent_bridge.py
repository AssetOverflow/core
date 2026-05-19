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

Phase 1 instrumentation (observation-only)
  ``articulate_with_intent()`` emits one ``BridgeTraceRecord`` per call
  through the module-level ``_TRACE_SINK`` when a sink has been attached via
  ``attach_bridge_trace_sink()``.  When no sink is attached the emission
  path is a pure no-op (single ``is None`` guard, no allocation).  This
  instruments the four dimensions named in the mastery plan's Phase 1.3:
    - recalled_words population at the call site
    - pre- and post-grounding obj slot content
    - bridge_useful flag
    - fallback_surface (what the runtime would use if bridge returns "")
  Zero behavior change on all existing paths.
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


# ---------------------------------------------------------------------------
# Phase 1 — module-level trace sink (opt-in, observation-only)
# ---------------------------------------------------------------------------

_TRACE_SINK = None  # type: object | None
_TRACE_INCLUDE_CONTENT: bool = False


def attach_bridge_trace_sink(
    sink,
    *,
    include_content: bool = False,
) -> None:
    """Attach a :class:`generate.bridge_trace.BridgeTraceSink`.

    After each call to ``articulate_with_intent()`` the runtime emits
    one JSONL-formatted ``BridgeTraceRecord`` to *sink*.  Passing
    ``None`` detaches.

    ``include_content`` opts surface text, recalled words, and slot
    values into the emitted record.  Default ``False`` preserves
    redact-by-default (CLAUDE.md trust boundary): aggregation
    pipelines get counts and flags without raw text.
    """
    global _TRACE_SINK, _TRACE_INCLUDE_CONTENT
    _TRACE_SINK = sink
    _TRACE_INCLUDE_CONTENT = bool(include_content)


def detach_bridge_trace_sink() -> None:
    """Detach any attached trace sink (convenience alias for attach(None))."""
    global _TRACE_SINK, _TRACE_INCLUDE_CONTENT
    _TRACE_SINK = None
    _TRACE_INCLUDE_CONTENT = False


def _emit_trace(
    *,
    intent_tag: str,
    intent_subject: str,
    plan: ArticulationPlan,
    recalled_words: tuple[str, ...],
    pre_ground_obj: str,
    post_ground_obj: str,
    bridge_surface: str,
    bridge_useful: bool,
) -> None:
    """Emit one BridgeTraceRecord to the attached sink (no-op when None).

    Called from within ``articulate_with_intent()`` after the bridge
    has resolved.  All arguments are plain Python types — no numpy,
    no I/O dependencies at the construction site.
    """
    if _TRACE_SINK is None:
        return
    from generate.bridge_trace import BridgeTraceRecord, format_bridge_trace_jsonl

    record = BridgeTraceRecord(
        intent_tag=intent_tag,
        intent_subject=intent_subject,
        plan_subject=plan.subject or "",
        plan_predicate=plan.predicate or "",
        plan_object=plan.object or "",
        recalled_words_len=len(recalled_words),
        recalled_words_sample=recalled_words[:5] if _TRACE_INCLUDE_CONTENT else (),
        pre_ground_obj=pre_ground_obj,
        post_ground_obj=post_ground_obj,
        bridge_surface=bridge_surface if _TRACE_INCLUDE_CONTENT else "",
        bridge_useful=bridge_useful,
        fallback_surface=plan.surface if _TRACE_INCLUDE_CONTENT else "",
    )
    line = format_bridge_trace_jsonl(
        record,
        include_content=_TRACE_INCLUDE_CONTENT,
    )
    _TRACE_SINK.emit(line)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


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

    Phase 1: emits one BridgeTraceRecord to the module-level sink (if
    attached) after resolution — observation-only, no effect on return value.
    """
    intent = classify_intent_from_input(text)
    intent_tag_name = intent.tag.name if intent.tag is not None else "UNKNOWN"
    intent_subject = intent.subject or ""

    graph = _build_graph_from_intent(intent, plan)

    # Record pre-grounding obj for the Phase 1 trace.
    pre_ground_obj = graph.nodes[0].obj if graph.nodes else _PENDING

    if recalled_words:
        graph = ground_graph(graph, recalled_words)

    # Record post-grounding obj for the Phase 1 trace.
    post_ground_obj = graph.nodes[0].obj if graph.nodes else _PENDING

    articulation_target = plan_articulation(graph)
    realized: RealizedPlan = realize_semantic(articulation_target, graph)

    if not realized.surface or not realized.fragments:
        _emit_trace(
            intent_tag=intent_tag_name,
            intent_subject=intent_subject,
            plan=plan,
            recalled_words=recalled_words,
            pre_ground_obj=pre_ground_obj,
            post_ground_obj=post_ground_obj,
            bridge_surface="",
            bridge_useful=False,
        )
        return ""

    surface = realized.surface
    useful = _is_useful_surface(surface)

    _emit_trace(
        intent_tag=intent_tag_name,
        intent_subject=intent_subject,
        plan=plan,
        recalled_words=recalled_words,
        pre_ground_obj=pre_ground_obj,
        post_ground_obj=post_ground_obj,
        bridge_surface=surface,
        bridge_useful=useful,
    )

    if not useful:
        return ""

    return surface
