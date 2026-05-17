"""ArticulationRealizerV2 — deterministic template-based realization.

Converts an ArticulationTarget (ordered rhetorical steps from the graph
planner) into a RealizedPlan: an ordered sequence of surface fragments
joined into a single deterministic surface string.

Design constraints:
  - No LLM fallback
  - No broad grammar engine
  - Deterministic: same ArticulationTarget → same RealizedPlan, always
  - Composable: does not replace the existing realize() path yet
"""

from __future__ import annotations

from dataclasses import dataclass

from generate.graph_planner import (
    ArticulationStep,
    ArticulationTarget,
    PropositionGraph,
    RhetoricalMove,
)
from generate.intent import IntentTag
from generate.semantic_templates import render_semantic
from generate.templates import render_step


@dataclass(frozen=True, slots=True)
class RealizedFragment:
    node_id: str
    move: RhetoricalMove
    surface: str

    def as_dict(self) -> dict[str, str]:
        return {
            "node_id": self.node_id,
            "move": self.move.value,
            "surface": self.surface,
        }


def _capitalize_sentence(s: str) -> str:
    """Capitalize the first alphabetic character of a sentence.

    Skips leading whitespace/punctuation so fragments that start with
    discourse markers ("next, knowledge…") still emit a capital first
    letter ("Next, knowledge…") at the sentence boundary.  Leaves the
    rest of the string untouched — proper nouns and embedded all-caps
    tokens are preserved.
    """
    if not s:
        return s
    for i, ch in enumerate(s):
        if ch.isalpha():
            return s[:i] + ch.upper() + s[i + 1:]
    return s


def _join_as_paragraph(fragments: list["RealizedFragment"]) -> str:
    """Join fragments into a paragraph with sentence-initial capitalization.

    Each fragment becomes one sentence; sentence-initial letters are
    capitalized; the paragraph ends with a single terminal period.
    """
    if not fragments:
        return ""
    pieces: list[str] = []
    for f in fragments:
        s = f.surface.strip()
        if not s:
            continue
        s = _capitalize_sentence(s)
        pieces.append(s)
    joined = ". ".join(pieces)
    if joined and not joined.endswith("."):
        joined += "."
    return joined


@dataclass(frozen=True, slots=True)
class RealizedPlan:
    fragments: tuple[RealizedFragment, ...]
    surface: str

    def as_dict(self) -> dict[str, object]:
        return {
            "fragments": tuple(f.as_dict() for f in self.fragments),
            "surface": self.surface,
        }


def realize_semantic(
    target: ArticulationTarget,
    graph: PropositionGraph | None = None,
) -> RealizedPlan:
    """Realize using intent-aware semantic templates.

    Uses the source intent to select a template that produces structurally
    better surfaces (e.g. "X is defined as Y" for definition intents)
    rather than the generic rhetorical-move templates.

    Returns an empty RealizedPlan for empty/None targets so the caller
    can fall back to the older articulation path.
    """
    if target is None or not target.steps:
        return RealizedPlan(fragments=(), surface="")

    intent = target.source_intent
    fragments: list[RealizedFragment] = []

    if intent is IntentTag.COMPARISON and len(target.steps) >= 2:
        step_a = target.steps[0]
        step_b = target.steps[1]
        obj_a = _resolve_obj(step_a, graph)
        secondary = step_b.subject if step_b.subject != step_a.subject else obj_a
        surface = render_semantic(
            intent=intent,
            subject=step_a.subject,
            predicate=step_a.predicate,
            obj=obj_a,
            secondary=secondary,
        )
        fragments.append(RealizedFragment(
            node_id=step_a.node_id,
            move=RhetoricalMove.CONTRAST,
            surface=surface,
        ))
    else:
        for step in target.steps:
            obj = _resolve_obj(step, graph)
            surface = render_semantic(
                intent=intent,
                subject=step.subject,
                predicate=step.predicate,
                obj=obj,
            )
            move = step.move
            if move is RhetoricalMove.ASSERT and intent is IntentTag.CORRECTION:
                move = RhetoricalMove.CORRECT
            fragments.append(RealizedFragment(
                node_id=step.node_id,
                move=move,
                surface=surface,
            ))

    joined = _join_as_paragraph(fragments)
    return RealizedPlan(fragments=tuple(fragments), surface=joined)


def _resolve_obj(step: ArticulationStep, graph: PropositionGraph | None) -> str:
    """Look up the object slot from the graph node matching this step."""
    if graph is None:
        return "..."
    for node in graph.nodes:
        if node.node_id == step.node_id:
            return node.obj
    return "..."


def realize_target(
    target: ArticulationTarget,
    graph: PropositionGraph | None = None,
) -> RealizedPlan:
    """Realize an ArticulationTarget into a deterministic surface plan.

    Handles compound constructions (conjunction, disjunction, complement,
    relative clause) by detecting graph edges and joining surfaces with
    appropriate connectors rather than sentence-level punctuation.

    Returns an empty-but-valid RealizedPlan for empty/None targets.
    """
    from generate.graph_planner import Relation

    if target is None or not target.steps:
        return RealizedPlan(fragments=(), surface="")

    edge_map: dict[str, tuple[str, Relation]] = {}
    if graph is not None:
        for edge in graph.edges:
            edge_map[edge.source] = (edge.target, edge.relation)

    step_by_id = {step.node_id: step for step in target.steps}
    visited: set[str] = set()
    fragments: list[RealizedFragment] = []

    for step in target.steps:
        if step.node_id in visited:
            continue
        visited.add(step.node_id)

        obj = _resolve_obj(step, graph)
        move = step.move
        if move is RhetoricalMove.ASSERT and target.source_intent is IntentTag.CORRECTION:
            move = RhetoricalMove.CORRECT

        surface = render_step(
            move=move,
            subject=step.subject,
            predicate=step.predicate,
            obj=obj,
            negated=step.negated,
            quantifier=step.quantifier,
            tense=step.tense,
            aspect=step.aspect,
        )

        if step.node_id in edge_map:
            target_id, relation = edge_map[step.node_id]
            target_step = step_by_id.get(target_id)
            if target_step is not None and target_id not in visited:
                match relation:
                    case Relation.CONJUNCTION | Relation.DISJUNCTION | Relation.COMPLEMENT | Relation.RELATIVE:
                        visited.add(target_id)
                        target_obj = _resolve_obj(target_step, graph)
                        target_surface = render_step(
                            move=RhetoricalMove.ASSERT,
                            subject=target_step.subject,
                            predicate=target_step.predicate,
                            obj=target_obj,
                            negated=target_step.negated,
                            quantifier=target_step.quantifier,
                            tense=target_step.tense,
                            aspect=target_step.aspect,
                        )
                        match relation:
                            case Relation.CONJUNCTION:
                                surface = f"{surface} and {target_surface}"
                            case Relation.DISJUNCTION:
                                surface = f"{surface} or {target_surface}"
                            case Relation.COMPLEMENT:
                                surface = f"{step.subject} {step.predicate} that {target_surface}"
                            case Relation.RELATIVE:
                                surface = f"{step.subject}, which {target_step.predicate} {target_obj}, {step.predicate} {obj}"
                    case _:
                        pass

        fragments.append(
            RealizedFragment(
                node_id=step.node_id,
                move=move,
                surface=surface,
            )
        )

    joined = _join_as_paragraph(fragments)
    return RealizedPlan(fragments=tuple(fragments), surface=joined)


