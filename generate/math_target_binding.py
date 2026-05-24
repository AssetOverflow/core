"""ADR-G5 — deterministic question target-binding extraction.

This module is intentionally substrate-level: it derives a
:class:`TargetBinding` from an already-admitted ``CandidateUnknown`` and
branch-local entity list. It does not guess entities and it does not alter
solver semantics.
"""

from __future__ import annotations

import re
from typing import Final

from generate.math_candidate_parser import CandidateUnknown
from generate.math_problem_graph import TargetBinding

_AGGREGATE_SUM_RE: Final[re.Pattern[str]] = re.compile(
    r"\b(?:in\s+total|altogether|combined|together|total)\b",
    flags=re.IGNORECASE,
)


def aggregate_kind_for_question(source_span: str) -> str:
    """Return the closed-set aggregation kind signaled by a question.

    G.5 starts with the only safe widening: aggregate sum. Non-aggregate
    questions remain ``single``. Difference / multiplicative-total are
    reserved for later phases and are not inferred here.
    """
    if _AGGREGATE_SUM_RE.search(source_span):
        return "sum"
    return "single"


def target_binding_from_question(
    question: CandidateUnknown,
    *,
    branch_entities: tuple[str, ...],
) -> TargetBinding | None:
    """Build a TargetBinding for ``question`` when the scope is explicit.

    Rules:

    - entity question + no aggregate marker -> single(entity)
    - entity question + aggregate marker -> single(entity), because the
      entity text explicitly bounds the scope; the aggregate marker is
      arithmetically inert for one entity
    - total-across question + aggregate marker -> sum(all branch entities)
    - total-across question without aggregate marker -> None; the legacy
      ``Unknown(entity=None)`` path already represents total-across, and
      no new target-binding evidence is added

    Returns None rather than guessing when the entity universe is empty.
    """
    if not branch_entities:
        return None

    kind = aggregate_kind_for_question(question.source_span)
    unit = question.unknown.unit

    if question.unknown.entity is not None:
        return TargetBinding(
            entity_scope=(question.unknown.entity,),
            unit=unit,
            aggregation_kind="single",
            provenance_edges=("question.entity",),
        )

    if kind == "sum":
        return TargetBinding(
            entity_scope=branch_entities,
            unit=unit,
            aggregation_kind="sum",
            provenance_edges=("question.aggregate", "question.total_across"),
        )

    return None
