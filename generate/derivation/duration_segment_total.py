"""Gate A2g — duration segment total (comparative middle leg + fixed legs).

Experience Flywheel Sprint 6 selected this family after scout showed
``lift_refused_to_correct == 0`` (prior lifts already served) and the
``multiplicative_aggregate`` cluster lacked end-to-end sealed signal.  The
composition-validation corpus pins train_sample **0015** as R5
(``cv-0022``): fixed leg + comparative middle leg referencing the first
fixed leg + optional trailing fixed leg, question asks total time.

This is a first-principles organ — not broad DCS injection, not
``resolve_pooled``.  Promotion requires:

- question binds ``total`` + ``time``;
- exactly one comparative scalar (``twice``, ``double``, ``thrice``, …);
- two or three grounded duration quantities in the body;
- comparative cue appears between the first and last duration anchors;
- hazard refusal (fractions, percent, money, profit, remaining, per-day tariffs).

Deterministic; sealed module (no ``chat/`` import).
"""

from __future__ import annotations

import re
from typing import Final

from generate.derivation.clauses import segment_clauses
from generate.derivation.comparatives import comparative_step, extract_comparative_scalars
from generate.derivation.extract import extract_quantities
from generate.derivation.model import GroundedDerivation, Quantity, Step
from generate.derivation.target import _question_clause
from generate.derivation.verify import Resolution, select_self_verified
from generate.math_roundtrip import _tokens

_FRACTION_RE: Final[re.Pattern[str]] = re.compile(r"\d+/\d+")
_DURATION_UNITS: Final[frozenset[str]] = frozenset(
    {"hour", "hours", "minute", "minutes", "min", "mins"}
)
_TEXT_BLOCKERS: Final[frozenset[str]] = frozenset(
    {
        "each",
        "insurance",
        "money",
        "overtime",
        "percent",
        "percentage",
        "profit",
        "rest",
        "salary",
        "wage",
    }
)
_REMAINING_DISTANCE_RE: Final[re.Pattern[str]] = re.compile(
    r"\bremaining\s+distance\b", re.IGNORECASE
)
_QUESTION_BLOCKERS: Final[frozenset[str]] = frozenset(
    {"longer", "more", "less", "per", "profit", "remaining"}
)


def _asks_total_time(question_clause: str) -> bool:
    tokens = _tokens(question_clause)
    return "total" in tokens and "time" in tokens


def _has_hazard_surface(problem_text: str, question_clause: str) -> bool:
    if _FRACTION_RE.search(problem_text):
        return True
    text_tokens = _tokens(problem_text)
    question_tokens = _tokens(question_clause)
    if "%" in problem_text or "percent" in text_tokens or "percentage" in text_tokens:
        return True
    if text_tokens & _TEXT_BLOCKERS:
        return True
    if "remaining" in text_tokens and not _REMAINING_DISTANCE_RE.search(problem_text):
        return True
    if question_tokens & _QUESTION_BLOCKERS:
        return True
    return False


def _duration_quantities(clause: str) -> tuple[Quantity, ...]:
    return tuple(
        q
        for q in extract_quantities(clause)
        if q.unit in _DURATION_UNITS or q.unit.rstrip("s") in {"hour", "minute", "min"}
    )


def _pick_add_cue(problem_text: str, *, prefer: tuple[str, ...]) -> str | None:
    tokens = _tokens(problem_text)
    for cue in prefer:
        if cue in tokens:
            return cue
    return None


def build_duration_segment_total(problem_text: str) -> GroundedDerivation | None:
    """Construct the ungated duration-segment-total chain, or ``None``.

    Shape (0015-class):
      leg1 + (leg1 × comparative_scalar) + leg3?

    Fold:
      start leg1 → × comparative → + leg1 → + leg3?
    """
    question_clause = _question_clause(problem_text)
    if not _asks_total_time(question_clause):
        return None
    if _has_hazard_surface(problem_text, question_clause):
        return None

    comparatives = extract_comparative_scalars(problem_text)
    if len(comparatives) != 1:
        return None
    comparative = comparatives[0]
    if comparative.scalar <= 0:
        return None

    body_clauses = [
        clause
        for clause in segment_clauses(problem_text)
        if clause != question_clause and comparative.cue in _tokens(clause)
    ]
    if len(body_clauses) != 1:
        return None

    durations = _duration_quantities(body_clauses[0])
    if len(durations) != 2:
        return None

    leg1, leg3 = durations

    add_back_cue = _pick_add_cue(problem_text, prefer=("subway", "bus", "ride", "and"))
    if add_back_cue is None:
        return None
    tail_cue = _pick_add_cue(problem_text, prefer=("then", "and"))
    if tail_cue is None:
        return None

    steps: list[Step] = [
        comparative_step(comparative),
        Step(
            op="add",
            operand=Quantity(value=leg1.value, unit=leg1.unit, source_token=leg1.source_token),
            cue=add_back_cue,
        ),
        Step(
            op="add",
            operand=Quantity(value=leg3.value, unit=leg3.unit, source_token=leg3.source_token),
            cue=tail_cue,
        ),
    ]

    return GroundedDerivation(start=leg1, steps=tuple(steps))


def compose_duration_segment_total(problem_text: str) -> Resolution | None:
    """Gate the typed duration chain through self-verification."""
    derivation = build_duration_segment_total(problem_text)
    if derivation is None:
        return None
    return select_self_verified([derivation], problem_text, target_units=())


def resolve_promotable_duration_segment_total(problem_text: str) -> Resolution | None:
    """Serving promotion bridge (Gate A2g)."""
    return compose_duration_segment_total(problem_text)