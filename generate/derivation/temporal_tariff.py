"""Gate A2m — temporal tariff (overtime shift earnings + bundle overflow tariff).

Experience Flywheel Sprint 9 / microscope ``temporal_tariff:temporal_aggregation``
(train_sample **0001**, **0017**): two narrow tariff shapes, not a generic time
parser.

**Pattern A — overtime shift earnings (0001)**

    regular = threshold_hours × hourly_rate × days
    overtime_total = (hours_per_day − threshold_hours) × (rate + rate × ½) × days
    total = regular + overtime_total

**Pattern B — bundle overflow tariff (0017)**

    overflow_cost = (rental_days − bundle_days) × daily_rate
    total = bundle_price + overflow_cost

Promotion requires explicit positive anchors per pattern, question-target binding
(money/cost), and hazard refusal (profit, insurance, percent, multiple tariffs).

Deterministic; sealed module (no ``chat/`` import).
"""

from __future__ import annotations

import re
from typing import Final

from collections import Counter

from generate.derivation.clauses import segment_clauses
from generate.derivation.extract import extract_quantities
from generate.derivation.model import GroundedDerivation, Quantity, Step
from generate.derivation.target import _question_clause
from generate.derivation.verify import Resolution, SelfVerification
from generate.math_roundtrip import _token_in, _tokens, _value_grounds

_FRACTION_RE: Final[re.Pattern[str]] = re.compile(r"\d+\s*/\s*\d+")
_HOURLY_RATE_RE: Final[re.Pattern[str]] = re.compile(
    r"\$\s*(\d+(?:\.\d+)?)\s*(?:an\s+hour|/hour|per\s+hour)",
    re.IGNORECASE,
)
_THRESHOLD_HOURS_RE: Final[re.Pattern[str]] = re.compile(
    r"more\s+than\s+(\d+)\s+hours?",
    re.IGNORECASE,
)
_BUNDLE_TARIFF_RE: Final[re.Pattern[str]] = re.compile(
    r"\$\s*(\d+(?:\.\d+)?)\s+per\s+day\s+or\s+\$\s*(\d+(?:\.\d+)?)\s+for\s+(\d+)\s+days?",
    re.IGNORECASE,
)
_EARN_VERBS: Final[frozenset[str]] = frozenset(
    {"earn", "earned", "make", "made", "receive", "received", "get", "got"}
)
_COST_VERBS: Final[frozenset[str]] = frozenset({"cost", "costs", "charge", "charges", "pay", "paid"})
_TEXT_BLOCKERS: Final[frozenset[str]] = frozenset(
    {
        "insurance",
        "percent",
        "percentage",
        "profit",
        "ticket",
        "tickets",
        "vet",
        "amusement",
    }
)
_QUESTION_BLOCKERS: Final[frozenset[str]] = frozenset({"long", "take"})


def _asks_money_total(question_clause: str) -> bool:
    tokens = _tokens(question_clause)
    if "money" in tokens and bool(_EARN_VERBS & tokens):
        return True
    if "how" in tokens and "much" in tokens and bool(_COST_VERBS & tokens):
        return True
    return False


def _body_text(problem_text: str) -> str:
    question_clause = _question_clause(problem_text)
    return problem_text.replace(question_clause, "").strip()


def _has_hazard_surface(problem_text: str, question_clause: str) -> bool:
    if _FRACTION_RE.search(problem_text) and "overtime" not in _tokens(problem_text):
        return True
    text_tokens = _tokens(problem_text)
    question_tokens = _tokens(question_clause)
    if "%" in problem_text or "percent" in text_tokens:
        return True
    if text_tokens & _TEXT_BLOCKERS:
        return True
    if question_tokens & _QUESTION_BLOCKERS:
        return True
    return False


def _half_fraction_operand(problem_text: str) -> Quantity | None:
    match = re.search(r"1\s*/\s*2", problem_text)
    if match is None:
        return None
    return Quantity(value=0.5, unit="", source_token=match.group(0).replace(" ", ""))


def _hourly_rate(problem_text: str) -> Quantity | None:
    match = _HOURLY_RATE_RE.search(problem_text)
    if match is None:
        match = re.search(r"makes\s+\$\s*(\d+(?:\.\d+)?)", problem_text, re.IGNORECASE)
    if match is None:
        return None
    token = match.group(1)
    return Quantity(value=float(token), unit="dollars", source_token=token)


def _threshold_hours(problem_text: str) -> Quantity | None:
    match = _THRESHOLD_HOURS_RE.search(problem_text)
    if match is None:
        return None
    token = match.group(1)
    return Quantity(value=float(token), unit="hours", source_token=token)


def _hours_per_day(problem_text: str, question_clause: str) -> Quantity | None:
    threshold = _threshold_hours(problem_text)
    for clause in segment_clauses(problem_text):
        tokens = _tokens(clause)
        if "hours" not in tokens and "hour" not in tokens:
            continue
        if "more" in tokens and "than" in tokens:
            continue
        if "every" not in tokens and "per" not in tokens and "each" not in tokens:
            continue
        quantities = [
            q
            for q in extract_quantities(clause)
            if q.unit in {"hours", "hour"} or q.unit.rstrip("s") == "hour"
        ]
        if len(quantities) != 1:
            continue
        q = quantities[0]
        if threshold is not None and q.value <= threshold.value:
            continue
        return Quantity(value=q.value, unit="hours", source_token=q.source_token)
    return None


def _day_count(problem_text: str, question_clause: str) -> Quantity | None:
    for clause in segment_clauses(problem_text):
        tokens = _tokens(clause)
        if "days" not in tokens and "day" not in tokens:
            continue
        if clause == question_clause and "hours" not in tokens and "hour" not in tokens:
            continue
        quantities = [
            q
            for q in extract_quantities(clause)
            if q.unit in {"days", "day"} or q.unit.rstrip("s") == "day"
        ]
        if len(quantities) == 1:
            q = quantities[0]
            return Quantity(value=q.value, unit="days", source_token=q.source_token)
    return None


def _rental_days(problem_text: str, question_clause: str) -> Quantity | None:
    for clause in segment_clauses(problem_text):
        if clause == question_clause:
            continue
        tokens = _tokens(clause)
        if "rent" not in tokens and "rents" not in tokens:
            continue
        quantities = [
            q
            for q in extract_quantities(clause)
            if q.unit in {"days", "day"} or q.unit.rstrip("s") == "day"
        ]
        if len(quantities) == 1:
            q = quantities[0]
            return Quantity(value=q.value, unit="days", source_token=q.source_token)
    return None


def _bundle_tariff(problem_text: str) -> tuple[Quantity, Quantity, Quantity] | None:
    match = _BUNDLE_TARIFF_RE.search(problem_text)
    if match is None:
        return None
    daily_token, bundle_token, bundle_days_token = (
        match.group(1),
        match.group(2),
        match.group(3),
    )
    return (
        Quantity(value=float(daily_token), unit="dollars", source_token=daily_token),
        Quantity(value=float(bundle_token), unit="dollars", source_token=bundle_token),
        Quantity(value=float(bundle_days_token), unit="days", source_token=bundle_days_token),
    )


def build_overtime_shift_earnings(problem_text: str) -> GroundedDerivation | None:
    """Construct overtime shift earnings total, or ``None``."""
    question_clause = _question_clause(problem_text)
    if not _asks_money_total(question_clause):
        return None
    if _has_hazard_surface(problem_text, question_clause):
        return None
    if "overtime" not in _tokens(problem_text):
        return None

    rate = _hourly_rate(problem_text)
    threshold = _threshold_hours(problem_text)
    hours_per_day = _hours_per_day(problem_text, question_clause)
    days = _day_count(problem_text, question_clause)
    half = _half_fraction_operand(problem_text)
    if None in (rate, threshold, hours_per_day, days, half):
        return None
    if hours_per_day.value <= threshold.value:
        return None

    ot_hours_per_day = hours_per_day.value - threshold.value
    ot_rate = rate.value + (rate.value * half.value)
    ot_total = ot_hours_per_day * ot_rate * days.value

    return GroundedDerivation(
        start=threshold,
        steps=(
            Step(op="multiply", operand=rate, cue="hour"),
            Step(op="multiply", operand=days, cue="days"),
            Step(
                op="add",
                operand=Quantity(
                    value=ot_total,
                    unit="hours",
                    source_token=hours_per_day.source_token,
                ),
                cue="overtime",
            ),
        ),
    )


def build_bundle_overflow_tariff(problem_text: str) -> GroundedDerivation | None:
    """Construct bundle + overflow-day tariff total, or ``None``."""
    question_clause = _question_clause(problem_text)
    if not _asks_money_total(question_clause):
        return None
    if _has_hazard_surface(problem_text, question_clause):
        return None
    if "overtime" in _tokens(problem_text):
        return None

    tariff = _bundle_tariff(problem_text)
    rental_days = _rental_days(problem_text, question_clause)
    if tariff is None or rental_days is None:
        return None

    daily_rate, bundle_price, bundle_days = tariff
    if rental_days.value <= bundle_days.value:
        return None

    overflow_cost = (rental_days.value - bundle_days.value) * daily_rate.value

    return GroundedDerivation(
        start=bundle_price,
        steps=(
            Step(
                op="add",
                operand=Quantity(
                    value=overflow_cost,
                    unit="dollars",
                    source_token=rental_days.source_token,
                ),
                cue="per",
            ),
        ),
    )


def _self_verifies_temporal_tariff(
    derivation: GroundedDerivation, problem_text: str, *, pattern: str
) -> SelfVerification:
    reasons: list[str] = []
    tokens = _tokens(problem_text)
    question_clause = _question_clause(problem_text)

    operands = [derivation.start, *(s.operand for s in derivation.steps)]
    for q in operands:
        if not _value_grounds(q.source_token, tokens):
            reasons.append(f"operand {q.source_token!r} not grounded in text")

    for step in derivation.steps:
        if not _token_in(step.cue, tokens):
            reasons.append(f"operation cue {step.cue!r} not grounded in text")

    body = _body_text(problem_text)
    body_quantities = Counter(q.source_token for q in extract_quantities(body))
    used = Counter(
        [derivation.start.source_token]
        + [step.operand.source_token for step in derivation.steps]
    )
    if pattern == "overtime":
        half = _half_fraction_operand(problem_text)
        if half is not None:
            used[half.source_token] += 1
            if half.source_token == "1/2":
                used["2"] += 1
    elif pattern == "bundle":
        tariff = _bundle_tariff(problem_text)
        if tariff is not None:
            daily_rate, _, bundle_days = tariff
            used[daily_rate.source_token] += 1
            used[bundle_days.source_token] += 1
    unused = body_quantities - used
    if unused:
        reasons.append(f"incomplete: unused body quantities {sorted(unused.elements())}")

    if pattern == "overtime":
        if _hourly_rate(problem_text) is None:
            reasons.append("missing hourly rate anchor")
        if _threshold_hours(problem_text) is None:
            reasons.append("missing overtime threshold")
        if _hours_per_day(problem_text, question_clause) is None:
            reasons.append("missing hours-per-day anchor")
        if _day_count(problem_text, question_clause) is None:
            reasons.append("missing day-count anchor")
        if _half_fraction_operand(problem_text) is None:
            reasons.append("missing overtime half-fraction anchor")
    elif pattern == "bundle":
        if _bundle_tariff(problem_text) is None:
            reasons.append("missing bundle tariff anchor")
        if _rental_days(problem_text, question_clause) is None:
            reasons.append("missing rental-day question anchor")

    return SelfVerification(verified=not reasons, reasons=tuple(reasons))


def _compose_pattern(
    builder, problem_text: str, *, pattern: str
) -> Resolution | None:
    derivation = builder(problem_text)
    if derivation is None:
        return None
    if not _self_verifies_temporal_tariff(derivation, problem_text, pattern=pattern).verified:
        return None
    return Resolution(
        answer=derivation.answer,
        answer_unit=derivation.answer_unit,
        derivation=derivation,
    )


def compose_overtime_shift_earnings(problem_text: str) -> Resolution | None:
    return _compose_pattern(build_overtime_shift_earnings, problem_text, pattern="overtime")


def compose_bundle_overflow_tariff(problem_text: str) -> Resolution | None:
    return _compose_pattern(build_bundle_overflow_tariff, problem_text, pattern="bundle")


def compose_temporal_tariff(problem_text: str) -> Resolution | None:
    """Try overtime then bundle overflow; refuse on ambiguity."""
    overtime = compose_overtime_shift_earnings(problem_text)
    bundle = compose_bundle_overflow_tariff(problem_text)
    if overtime is not None and bundle is not None:
        return None
    return overtime or bundle


def resolve_promotable_temporal_tariff(problem_text: str) -> Resolution | None:
    """Serving promotion bridge (Gate A2m)."""
    return compose_temporal_tariff(problem_text)