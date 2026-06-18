"""Gate A2i — round-trip drive + comparative activity duration total.

Experience Flywheel Sprint 7 selected this family from the
``joint_sealed_no_resolution`` cluster after decomposition of composition-
validation **cv-0006** (train_sample **0030**): one-way drive duration, round
trip via ``each way``, activity duration as a comparative scalar of total
driving time, question binds trip time.

    driving_total = one_way × 2
    activity = driving_total × comparative_scalar
    trip_total = driving_total + activity
      = one_way × 2 × (1 + comparative_scalar)

Fold (grounded operands only):

    start one_way → add one_way (second leg) → × comparative_scalar
    → +one_way → +one_way

This is distinct from Gate A2g ``duration_segment_total`` (fixed leg +
comparative middle + trailing leg).  Promotion requires:

- ``each`` and ``way`` in the body;
- exactly one duration quantity and one comparative scalar;
- comparative references driving time (``driving`` token present);
- question binds ``time`` and ``trip``;
- hazard refusal (fractions, percent, money, goal/residual giveaway shapes).

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
    {"hour", "hours", "hr", "hrs", "minute", "minutes", "min", "mins"}
)
_TEXT_BLOCKERS: Final[frozenset[str]] = frozenset(
    {
        "insurance",
        "money",
        "overtime",
        "percent",
        "percentage",
        "profit",
        "salary",
        "wage",
    }
)
_QUESTION_BLOCKERS: Final[frozenset[str]] = frozenset(
    {"longer", "less", "per", "profit", "remaining"}
)


def _asks_trip_time(question_clause: str) -> bool:
    tokens = _tokens(question_clause)
    return "time" in tokens and "trip" in tokens


def _has_hazard_surface(problem_text: str, question_clause: str) -> bool:
    if _FRACTION_RE.search(problem_text):
        return True
    text_tokens = _tokens(problem_text)
    question_tokens = _tokens(question_clause)
    if "%" in problem_text or "percent" in text_tokens or "percentage" in text_tokens:
        return True
    if text_tokens & _TEXT_BLOCKERS:
        return True
    if "give" in text_tokens and "away" in text_tokens:
        return True
    if question_tokens & _QUESTION_BLOCKERS:
        return True
    return False


def _duration_quantities(clause: str) -> tuple[Quantity, ...]:
    return tuple(
        q
        for q in extract_quantities(clause)
        if q.unit in _DURATION_UNITS
        or q.unit.rstrip("s") in {"hour", "hr", "minute", "min"}
    )


def _duration_family(unit: str) -> str | None:
    stem = unit.rstrip("s")
    if stem in {"hour", "hr"}:
        return "hour"
    if stem in {"minute", "min"}:
        return "minute"
    return None


def build_round_trip_trip_duration(problem_text: str) -> GroundedDerivation | None:
    """Construct the ungated round-trip trip-duration chain, or ``None``."""
    question_clause = _question_clause(problem_text)
    if not _asks_trip_time(question_clause):
        return None
    if _has_hazard_surface(problem_text, question_clause):
        return None

    text_tokens = _tokens(problem_text)
    if "each" not in text_tokens or "way" not in text_tokens:
        return None
    if "driving" not in text_tokens:
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
        if clause != question_clause
    ]
    durations = [
        q
        for clause in body_clauses
        for q in _duration_quantities(clause)
    ]
    if len(durations) != 1:
        return None

    one_way = durations[0]
    if _duration_family(one_way.unit) is None:
        return None

    leg = Quantity(
        value=one_way.value,
        unit=one_way.unit,
        source_token=one_way.source_token,
    )
    steps: list[Step] = [
        Step(op="add", operand=leg, cue="way"),
        comparative_step(comparative),
        Step(op="add", operand=leg, cue="drive"),
        Step(op="add", operand=leg, cue="each"),
    ]
    return GroundedDerivation(start=leg, steps=tuple(steps))


def compose_round_trip_trip_duration(problem_text: str) -> Resolution | None:
    """Gate the typed round-trip chain through self-verification."""
    derivation = build_round_trip_trip_duration(problem_text)
    if derivation is None:
        return None
    return select_self_verified([derivation], problem_text, target_units=())


def resolve_promotable_round_trip_trip_duration(problem_text: str) -> Resolution | None:
    """Serving promotion bridge (Gate A2i)."""
    return compose_round_trip_trip_duration(problem_text)