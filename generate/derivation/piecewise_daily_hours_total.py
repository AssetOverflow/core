"""Gate A2q — calendar-grounded piecewise daily hours total (ClusterContract organ).

Sprint 11: train_sample **0013** — daily event-hours rate, ``halfway through {month}``
first period, ``doubled`` rate on ``remaining days``, question asks end-of-month
total hours.  Month day-count is table-grounded (:mod:`calendar_grounding`) with
explicit ``calendar_table`` provenance.

Chain (0013-class):

    half_days = month_days / 2          # licensed by ``halfway``
    period1 = daily_hours × half_days
    period2 = (daily_hours × 2) × half_days   # ``doubled`` comparative
    total = period1 + period2

Narrow organ — not generic calendar/temporal parser, not broad
``multiplicative_aggregate``.  Promotion requires ClusterContract positive anchors,
explicit actor/target/unit binding, and hazard refusal.

Deterministic; sealed module (no ``chat/`` import).
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Final

from generate.derivation.calendar_grounding import (
    MonthGrounding,
    allows_halfway_split,
    calendar_operand_grounds,
    resolve_month_grounding,
)
from generate.derivation.extract import extract_quantities
from generate.derivation.model import GroundedDerivation, Quantity, Step
from generate.derivation.target import _question_clause
from generate.derivation.verify import Resolution, SelfVerification
from generate.math_roundtrip import _token_in, _tokens, _value_grounds

_FRACTION_RE: Final[re.Pattern[str]] = re.compile(r"\d+\s*/\s*\d+")
_DAILY_ONE_HOUR_RE: Final[re.Pattern[str]] = re.compile(
    r"(\d+)\s+one-hour\s+\w+",
    re.IGNORECASE,
)
_UPLOADER_RE: Final[re.Pattern[str]] = re.compile(
    r"^(\w+)\s*,",
    re.IGNORECASE,
)
_HALFWAY_MONTH_RE: Final[re.Pattern[str]] = re.compile(
    r"halfway\s+through\s+(\w+)",
    re.IGNORECASE,
)
_TEXT_BLOCKERS: Final[frozenset[str]] = frozenset(
    {
        "insurance",
        "overtime",
        "percent",
        "percentage",
        "profit",
        "rent",
        "rents",
        "rented",
        "salary",
        "ticket",
        "tickets",
        "week",
        "weeks",
    }
)
_QUESTION_BLOCKERS: Final[frozenset[str]] = frozenset(
    {"daily", "left", "per", "rate", "remaining"}
)
_VAGUE_MONTH_RE: Final[re.Pattern[str]] = re.compile(
    r"\b(?:about|several)\s+(?:a\s+)?month\b",
    re.IGNORECASE,
)
_OBLIGATION_UNITS: Final[frozenset[str]] = frozenset({"hours", "hour"})


def _asks_end_of_month_total_hours(question_clause: str) -> bool:
    tokens = _tokens(question_clause)
    asks_quantity = "how" in tokens or "what" in tokens or "what's" in tokens
    return (
        asks_quantity
        and "total" in tokens
        and "hours" in tokens
        and "month" in tokens
    )


def _has_hazard_surface(problem_text: str, question_clause: str) -> bool:
    if _FRACTION_RE.search(problem_text):
        return True
    if _VAGUE_MONTH_RE.search(problem_text):
        return True
    text_tokens = _tokens(problem_text)
    question_tokens = _tokens(question_clause)
    if "%" in problem_text or "percent" in text_tokens:
        return True
    if text_tokens & _TEXT_BLOCKERS:
        return True
    if question_tokens & _QUESTION_BLOCKERS:
        return True
    if "$" in problem_text:
        return True
    if "twice" in text_tokens and "doubled" not in text_tokens:
        return True
    return False


def _body_actor(problem_text: str) -> str | None:
    match = _UPLOADER_RE.search(problem_text)
    if match is None:
        return None
    return match.group(1).lower()


def _daily_hours_rate(problem_text: str) -> Quantity | None:
    """``N one-hour videos`` → ``N`` hours/day (one-hour detail is unit conversion)."""
    match = _DAILY_ONE_HOUR_RE.search(problem_text)
    if match is None:
        return None
    value = float(match.group(1))
    return Quantity(value=value, unit="hours", source_token=match.group(1))


def _halfway_month_matches(month: MonthGrounding, problem_text: str) -> bool:
    match = _HALFWAY_MONTH_RE.search(problem_text)
    if match is None:
        return False
    return match.group(1).lower() == month.month_name


def _has_doubled_remaining_pattern(problem_text: str) -> bool:
    tokens = _tokens(problem_text)
    return (
        "doubled" in tokens
        and "remaining" in tokens
        and "days" in tokens
    )


def _recompute_total(daily_hours: Quantity, month: MonthGrounding) -> float:
    half_days = month.day_count / 2
    period1 = daily_hours.value * half_days
    period2 = daily_hours.value * 2.0 * half_days
    return period1 + period2


def _piecewise_total(
    daily_hours: Quantity, month: MonthGrounding
) -> tuple[GroundedDerivation, float]:
    """Build an audit derivation and the explicit piecewise total."""
    half_days = month.day_count / 2
    total = _recompute_total(daily_hours, month)
    period2 = daily_hours.value * 2.0 * half_days

    derivation = GroundedDerivation(
        start=Quantity(
            value=daily_hours.value * half_days,
            unit="hours",
            source_token=daily_hours.source_token,
        ),
        steps=(
            Step(
                op="add",
                operand=Quantity(value=period2, unit="hours", source_token="doubled"),
                cue="doubled",
                comparative=True,
            ),
        ),
    )
    return derivation, total


def build_piecewise_daily_hours_total(problem_text: str) -> tuple[GroundedDerivation, float] | None:
    """Construct the ungated piecewise chain, or ``None``."""
    question_clause = _question_clause(problem_text)
    if not _asks_end_of_month_total_hours(question_clause):
        return None
    if _has_hazard_surface(problem_text, question_clause):
        return None

    month = resolve_month_grounding(problem_text)
    if month is None or not allows_halfway_split(month.day_count):
        return None
    if not _halfway_month_matches(month, problem_text):
        return None
    if not _has_doubled_remaining_pattern(problem_text):
        return None

    daily_hours = _daily_hours_rate(problem_text)
    if daily_hours is None:
        return None
    if _body_actor(problem_text) is None:
        return None

    return _piecewise_total(daily_hours, month)


def _obligation_quantities(problem_text: str) -> Counter[str]:
    return Counter(
        q.source_token
        for q in extract_quantities(problem_text)
        if q.unit in _OBLIGATION_UNITS or q.unit.rstrip("s") == "hour"
    )


def _operand_grounds(q: Quantity, tokens: frozenset[str]) -> bool:
    if calendar_operand_grounds(q.source_token, tokens):
        return True
    return _value_grounds(q.source_token, tokens)


def _self_verifies_piecewise(
    derivation: GroundedDerivation, problem_text: str, expected_total: float
) -> SelfVerification:
    tokens = _tokens(problem_text)
    reasons: list[str] = []

    for q in [derivation.start, *(s.operand for s in derivation.steps if not s.comparative)]:
        if not _operand_grounds(q, tokens):
            reasons.append(f"operand {q.source_token!r} not grounded in text")

    for step in derivation.steps:
        if not _token_in(step.cue, tokens):
            reasons.append(f"operation cue {step.cue!r} not grounded in text")

    if abs(derivation.answer - expected_total) > 1e-9:
        reasons.append("arithmetic mismatch on piecewise total")

    obligation = _obligation_quantities(problem_text)
    used = Counter([derivation.start.source_token])
    unused = obligation - used
    if unused:
        reasons.append(f"incomplete: unused hour quantities {sorted(unused.keys())}")

    month = resolve_month_grounding(problem_text)
    daily = _daily_hours_rate(problem_text)
    if month is None:
        reasons.append("missing calendar month grounding")
    elif not _halfway_month_matches(month, problem_text):
        reasons.append("halfway month does not match named month")
    elif daily is not None and abs(_recompute_total(daily, month) - expected_total) > 1e-9:
        reasons.append("piecewise formula mismatch")

    if not _has_doubled_remaining_pattern(problem_text):
        reasons.append("missing doubled remaining-days pattern")

    if daily is None:
        reasons.append("missing daily one-hour rate anchor")

    return SelfVerification(verified=not reasons, reasons=tuple(reasons))


def compose_piecewise_daily_hours_total(problem_text: str) -> Resolution | None:
    """Gate the typed piecewise chain through self-verification."""
    built = build_piecewise_daily_hours_total(problem_text)
    if built is None:
        return None
    derivation, total = built
    if not _self_verifies_piecewise(derivation, problem_text, total).verified:
        return None
    return Resolution(
        answer=total,
        answer_unit="hours",
        derivation=derivation,
    )


def resolve_promotable_piecewise_daily_hours_total(
    problem_text: str,
) -> Resolution | None:
    """Serving promotion bridge (Gate A2q, ClusterContract calendar_grounded_piecewise)."""
    return compose_piecewise_daily_hours_total(problem_text)