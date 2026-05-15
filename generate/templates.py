"""Deterministic surface templates for rhetorical moves.

Each template is a format string keyed by RhetoricalMove. Slots:
  {subject}   — primary subject from the articulation step
  {predicate} — semantic predicate (e.g. "is_defined_as", "contrasts_with")
  {obj}       — object slot from the graph node (may be "<pending>")

Templates are intentionally simple. The goal is structural correctness,
not fluency — fluency comes in a later phase when the generation stream
consumes these as constraints rather than final output.
"""

from __future__ import annotations

from generate.graph_planner import RhetoricalMove


_PREDICATE_DISPLAY: dict[str, str] = {
    "is_defined_as": "is defined as",
    "is_caused_by": "is caused by",
    "has_steps": "has the following steps",
    "contrasts_with": "contrasts with",
    "corrects": "corrects",
    "recalls": "recalls",
    "is_verified_as": "is verified as",
    "addresses": "addresses",
    "defines": "defines",
    "means": "means",
    "grounds": "grounds",
    "supports": "supports",
    "causes": "causes",
    "reveals": "reveals",
    "precedes": "precedes",
    "follows": "follows",
    "belongs_to": "belongs to",
    "answers": "answers",
}


def _humanize_predicate(predicate: str) -> str:
    return _PREDICATE_DISPLAY.get(predicate, predicate.replace("_", " "))


_MOVE_TEMPLATES: dict[RhetoricalMove, str] = {
    RhetoricalMove.ASSERT: "{subject} {predicate_h} {obj}",
    RhetoricalMove.ELABORATE: "furthermore, {subject} {predicate_h} {obj}",
    RhetoricalMove.CONTRAST: "in contrast, {subject} {predicate_h} {obj}",
    RhetoricalMove.SEQUENCE: "next, {subject} {predicate_h} {obj}",
    RhetoricalMove.CORRECT: "correction: {subject} {predicate_h} {obj}",
}


def render_step(
    move: RhetoricalMove,
    subject: str,
    predicate: str,
    obj: str,
) -> str:
    """Render a single articulation step into a surface fragment."""
    template = _MOVE_TEMPLATES[move]
    predicate_h = _humanize_predicate(predicate)
    obj_display = obj if obj != "<pending>" else "..."
    return template.format(
        subject=subject,
        predicate_h=predicate_h,
        obj=obj_display,
    )
