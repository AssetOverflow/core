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


@dataclass(frozen=True, slots=True)
class RealizedPlan:
    fragments: tuple[RealizedFragment, ...]
    surface: str

    def as_dict(self) -> dict[str, object]:
        return {
            "fragments": tuple(f.as_dict() for f in self.fragments),
            "surface": self.surface,
        }


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

    Each step is rendered through the template for its rhetorical move,
    then fragments are joined with sentence-level punctuation.

    Returns an empty-but-valid RealizedPlan for empty/None targets.
    """
    if target is None or not target.steps:
        return RealizedPlan(fragments=(), surface="")

    fragments: list[RealizedFragment] = []
    for step in target.steps:
        obj = _resolve_obj(step, graph)
        move = step.move
        if move is RhetoricalMove.ASSERT and target.source_intent is IntentTag.CORRECTION:
            move = RhetoricalMove.CORRECT
        surface = render_step(
            move=move,
            subject=step.subject,
            predicate=step.predicate,
            obj=obj,
        )
        fragments.append(
            RealizedFragment(
                node_id=step.node_id,
                move=move,
                surface=surface,
            )
        )

    joined = ". ".join(f.surface for f in fragments)
    if joined and not joined.endswith("."):
        joined += "."

    return RealizedPlan(fragments=tuple(fragments), surface=joined)
