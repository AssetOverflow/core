"""ADR-0135 — Question-target binding refinement.

Pure-function resolvers that take a :class:`MathProblemGraph` and produce
the two new fields ``BoundUnknown`` requires under ADR-0135:

  - :func:`resolve_state_index` — picks the temporal index at which the
    unknown's symbol is observed. Current rule: ``"terminal"`` when at
    least one :class:`Operation` exists in the graph, ``"initial"`` when
    not. The :class:`Operation` (state-index) variant is part of the
    closed vocabulary but not produced by this resolver yet — it exists
    so future intermediate-state queries have a typed home.

  - :func:`infer_question_form` — closed dispatch over the operations
    whose actor / target / reference touches the unknown's entity. The
    precedence rule (documented in ADR-0135) is deterministic; ambiguous
    or unmappable shapes refuse with :class:`QuestionTargetError`.

  - :func:`bound_unknown_from_math_problem_graph` — the public entry
    point the adapter uses. Refusal-first, deterministic, pure.

No I/O. No solver. No mutation. The resolver only determines *which*
symbol the question targets and *what* form the answer takes.
"""

from __future__ import annotations

import re
from typing import Final, Literal

from generate.math_problem_graph import (
    Comparison,
    MathProblemGraph,
    Operation as MathOperation,
    Rate,
)

from .model import (
    BoundUnknown,
    Operation,
    SourceSpanLink,
    StateIndex,
)


# ---------------------------------------------------------------------------
# Public error
# ---------------------------------------------------------------------------


class QuestionTargetError(ValueError):
    """Raised when the question-target resolver cannot bind deterministically.

    Sibling of :class:`generate.binding_graph.AdapterError` and
    :class:`generate.binding_graph.AdmissibilityError`. Always carries a
    typed ``reason`` token from :data:`QUESTION_TARGET_REASONS`. The
    resolver never silently picks a default form.
    """

    def __init__(self, reason: str, *, detail: str = "") -> None:
        if reason not in QUESTION_TARGET_REASONS:
            raise ValueError(
                f"QuestionTargetError.reason must be one of "
                f"{sorted(QUESTION_TARGET_REASONS)}; got {reason!r}"
            )
        self.reason: Final[str] = reason
        self.detail: Final[str] = detail
        message = f"{reason}: {detail}" if detail else reason
        super().__init__(message)


QUESTION_TARGET_REASONS: Final[frozenset[str]] = frozenset(
    {
        "not_a_math_problem_graph",
        "unknown_entity_not_in_entities",
        "unmappable_question_form",
        "apply_rate_unit_mismatch",
    }
)


# ---------------------------------------------------------------------------
# Helpers — naming locked to ``generate.binding_graph.adapter`` conventions.
# ---------------------------------------------------------------------------

_SLUG_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def _slug(text: str) -> str:
    return _SLUG_NON_ALNUM.sub("_", text.strip().lower()).strip("_")


def _unknown_symbol_id(entity: str | None, unit: str) -> str:
    scope = _slug(entity) if entity is not None else "total"
    if scope == "":
        scope = "total"
    unit_slug = _slug(unit) or "x"
    return f"unknown_{scope}_{unit_slug}"


def _unknown_span(entity: str | None, unit: str) -> SourceSpanLink:
    text = f"{entity}|{unit}" if entity is not None else f"total|{unit}"
    return SourceSpanLink(
        source_id="math_problem_graph", start=0, end=len(text), text=text
    )


def _operation_touches_unknown(
    op: MathOperation, unk_entity: str | None
) -> bool:
    """An operation touches the unknown if its actor / target /
    comparison reference matches the unknown's entity. When the unknown
    has no entity (``entity is None``, the "total across all entities"
    case), every operation is considered to touch it.
    """
    if unk_entity is None:
        return True
    if op.actor == unk_entity:
        return True
    if op.target is not None and op.target == unk_entity:
        return True
    if isinstance(op.operand, Comparison):
        if op.operand.reference_actor == unk_entity:
            return True
    return False


# ---------------------------------------------------------------------------
# Public resolvers
# ---------------------------------------------------------------------------


def resolve_state_index(g: object) -> StateIndex:
    """Pick the temporal index at which the unknown is observed.

    Closed rule: ``"terminal"`` when the graph has at least one
    operation, ``"initial"`` when not. The :class:`Operation` variant of
    :data:`StateIndex` is part of the public vocabulary so future
    intermediate-state queries have a typed home, but this resolver
    never returns it today.
    """
    if not isinstance(g, MathProblemGraph):
        raise QuestionTargetError(
            "not_a_math_problem_graph",
            detail=f"got {type(g).__name__}",
        )
    if g.operations:
        return "terminal"
    return "initial"


_COUNT_KINDS: Final[frozenset[str]] = frozenset(
    {"add", "subtract", "transfer", "multiply", "divide"}
)


def infer_question_form(
    g: object,
) -> Literal["count", "rate", "total", "difference", "ratio", "identity"]:
    """Closed-vocab dispatch on operation kinds touching the unknown.

    Precedence (deterministic; documented in ADR-0135). Evaluate in
    order, return on first match:

      1. No operations touch the unknown's entity → ``"identity"``.
      2. Any ``compare_multiplicative`` touches → ``"ratio"``.
      3. Any ``compare_additive`` touches → ``"difference"``.
      4. Any ``apply_rate`` touches → ``"total"`` when the unknown's
         unit matches the rate's ``numerator_unit``; ``"rate"`` when it
         matches the ``denominator_unit``. Otherwise refuse
         (``apply_rate_unit_mismatch``).
      5. Every touching operation is in ``{add, subtract, transfer,
         multiply, divide}`` → ``"count"``.
      6. Anything else → refuse (``unmappable_question_form``).

    The precedence order resolves ambiguity: a graph mixing
    ``compare_additive`` with ``add`` returns ``"difference"`` because
    the comparison establishes the question's shape regardless of any
    downstream arithmetic. This is a closed rule, not a heuristic.
    """
    if not isinstance(g, MathProblemGraph):
        raise QuestionTargetError(
            "not_a_math_problem_graph",
            detail=f"got {type(g).__name__}",
        )

    unk_entity = g.unknown.entity
    if unk_entity is not None and unk_entity not in g.entities:
        # MathProblemGraph already enforces this invariant, but defensive
        # restatement keeps the resolver self-contained.
        raise QuestionTargetError(
            "unknown_entity_not_in_entities",
            detail=f"entity={unk_entity!r}",
        )

    touching: tuple[MathOperation, ...] = tuple(
        op for op in g.operations if _operation_touches_unknown(op, unk_entity)
    )

    if not touching:
        return "identity"

    kinds = {op.kind for op in touching}

    if "compare_multiplicative" in kinds:
        return "ratio"
    if "compare_additive" in kinds:
        return "difference"

    if "apply_rate" in kinds:
        unk_unit = g.unknown.unit
        for op in touching:
            if op.kind == "apply_rate" and isinstance(op.operand, Rate):
                if unk_unit == op.operand.numerator_unit:
                    return "total"
                if unk_unit == op.operand.denominator_unit:
                    return "rate"
        raise QuestionTargetError(
            "apply_rate_unit_mismatch",
            detail=(
                f"unknown.unit={unk_unit!r} matches neither numerator nor "
                f"denominator of any touching apply_rate"
            ),
        )

    if kinds.issubset(_COUNT_KINDS):
        return "count"

    raise QuestionTargetError(
        "unmappable_question_form",
        detail=f"touching kinds={sorted(kinds)!r}",
    )


def bound_unknown_from_math_problem_graph(g: object) -> BoundUnknown:
    """Build the refined :class:`BoundUnknown` for ``g``.

    The adapter (ADR-0133) calls this in place of its old ad-hoc
    ``Unknown → BoundUnknown`` mapping. Determinism: identical ``g``
    yields a byte-equal :class:`BoundUnknown`. Refusal-first: any
    :class:`QuestionTargetError` from the sub-resolvers propagates.

    The synthesized ``symbol_id`` / ``question_span`` mirror the
    adapter's pre-ADR-0135 convention exactly, so the symbol map in the
    surrounding binding graph remains the same shape.
    """
    if not isinstance(g, MathProblemGraph):
        raise QuestionTargetError(
            "not_a_math_problem_graph",
            detail=f"got {type(g).__name__}",
        )
    unk = g.unknown
    state_index = resolve_state_index(g)
    question_form = infer_question_form(g)
    sid = _unknown_symbol_id(unk.entity, unk.unit)
    span = _unknown_span(unk.entity, unk.unit)
    return BoundUnknown(
        symbol_id=sid,
        question_span=span,
        state_index=state_index,
        question_form=question_form,
        expected_unit=unk.unit,
    )


# Re-export ``Operation`` so callers do not need to thread the model
# import separately just to construct the state-index variant.
__all__ = (
    "QUESTION_TARGET_REASONS",
    "Operation",
    "QuestionTargetError",
    "bound_unknown_from_math_problem_graph",
    "infer_question_form",
    "resolve_state_index",
)
