"""Single-rate prose reader (R3d): explicit rate prose -> RateProblem.

Reads ONLY explicit single-rate problems and refuses everything else — combined/multi-rate,
clock-time/temporal, unit-mismatched durations, and underdetermined (missing-piece) prose. The
compound-unit consistency check (R3a) is the wrong=0 gate: a duration whose unit is not the rate's
denominator (``60 miles per hour for 30 minutes``) REFUSES rather than silently converting.

Recognized clauses (structural, not fixed strings):
  - rate value     : ``<N> <plural> per <singular>``        -> rate value + RateUnit(num, denom)
  - duration/time  : ``(for|in) <N> <unit>``                -> time value + unit
  - quantity       : a standalone ``<N> <unit>`` (outside the rate/duration spans)
  - query          : ``how many <unit>`` (role by unit match) | ``speed in <X> per <Y>`` (-> rate)

Refusals: ``combined_rates`` (≥2 rate clauses), ``temporal_state`` (clock markers),
``rate_unit_mismatch`` (duration/quantity unit ≠ rate unit), ``missing_rate`` / ``missing_time`` /
``missing_quantity`` (underdetermined). Off-serving; deterministic.
"""

from __future__ import annotations

import re

from generate.meaning_graph.reader import Refusal
from generate.rate_comprehension.conversion import is_convertible
from generate.rate_comprehension.model import RateProblem
from generate.rate_comprehension.units import RateUnit

_RATE_VALUE = re.compile(r"\b(\d+)\s+([a-z]+)\s+per\s+([a-z]+)\b")
_RATE_QUERY = re.compile(r"\bspeed in ([a-z]+) per ([a-z]+)\b")
_DURATION = re.compile(r"\b(?:for|in)\s+(\d+)\s+([a-z]+)\b")
_HOW_MANY = re.compile(r"\bhow many ([a-z]+)\b")
_DIGIT_NOUN = re.compile(r"\b(\d+)\s+([a-z]+)\b")
_TEMPORAL = re.compile(r"\b\d+\s*(?:am|pm)\b|\barrived\b|\bleft at\b|\bo'?clock\b")


def _singular(noun: str) -> str:
    if noun.endswith("es") and noun[:-2].endswith(("x", "s", "z", "ch", "sh")):
        return noun[:-2]
    if noun.endswith("s") and len(noun) > 1:
        return noun[:-1]
    return noun


def read_rate_problem(text: str) -> RateProblem | Refusal:
    """Comprehend explicit single-rate prose into a typed RateProblem, or refuse."""
    if not text or not text.strip():
        return Refusal("empty")
    t = text.lower()

    if _TEMPORAL.search(t):
        return Refusal("temporal_state", "elapsed clock time is not an explicit duration")
    rate_clauses = _RATE_VALUE.findall(t)
    if len(rate_clauses) >= 2:
        return Refusal("combined_rates", "more than one rate is multi-rate (R3.2)")

    # rate value clause (≤1)
    rate_value: int | None = None
    num_unit = denom_unit = None
    rate_match = _RATE_VALUE.search(t)
    if rate_match:
        rate_value = int(rate_match.group(1))
        num_unit, denom_unit = _singular(rate_match.group(2)), _singular(rate_match.group(3))

    # duration / time clause
    dur = _DURATION.search(t)
    time_value = int(dur.group(1)) if dur else None
    time_unit = _singular(dur.group(2)) if dur else None

    # standalone quantity: a digit-noun outside the rate-clause and duration spans
    spans = [m.span() for m in (rate_match, dur) if m is not None]
    quantity_value = quantity_unit = None
    for m in _DIGIT_NOUN.finditer(t):
        if any(s <= m.start() < e for s, e in spans):
            continue
        quantity_value, quantity_unit = int(m.group(1)), _singular(m.group(2))
        break

    # query role + rate unit
    rate_query = _RATE_QUERY.search(t)
    how_many = _HOW_MANY.search(t)
    if rate_query:
        query = "rate"
        rate_unit = RateUnit(_singular(rate_query.group(1)), _singular(rate_query.group(2)))
    elif how_many:
        asked = _singular(how_many.group(1))
        if rate_value is None:
            # No rate clause. This is a rate-underdetermined problem ONLY if rate-like structure
            # (a duration) is present; otherwise it simply is not a rate problem and must refuse as
            # not-my-domain (so R3 never claims a substantive boundary on R1/R2 text).
            if dur is not None:
                return Refusal("missing_rate", "a duration but no rate clause")
            return Refusal("not_rate_shaped", "no rate structure")
        rate_unit = RateUnit(num_unit, denom_unit)
        if asked == num_unit:
            query = "quantity"
        elif asked == denom_unit:
            query = "time"
        else:
            return Refusal("query_target_unrecognized", asked)
    else:
        return Refusal("no_query")

    # compound-unit consistency (the wrong=0 gate). R3.2: a duration whose unit CONVERTS to the
    # rate denominator (minute↔hour) is accepted — the reader keeps the original time_unit and the
    # SOLVER converts exactly. A non-convertible duration (e.g. gallons) still refuses.
    if time_value is not None and not is_convertible(time_unit, rate_unit.denominator):
        return Refusal("rate_unit_mismatch", f"duration {time_unit!r} does not convert to {rate_unit.denominator!r}")
    if quantity_value is not None and quantity_unit != rate_unit.numerator:
        return Refusal("rate_unit_mismatch", f"quantity {quantity_unit!r} ≠ rate numerator {rate_unit.numerator!r}")

    # assemble by query (refusing an underdetermined setup); time_unit is the duration's ORIGINAL
    # unit (the solver converts), or the rate denominator when the time is the unknown.
    if query == "quantity":
        if rate_value is None:
            return Refusal("missing_rate")
        if time_value is None:
            return Refusal("missing_time")
        return RateProblem(rate_unit, rate_value, time_value, None, "quantity", time_unit=time_unit)
    if query == "rate":
        if quantity_value is None:
            return Refusal("missing_quantity")
        if time_value is None:
            return Refusal("missing_time")
        return RateProblem(rate_unit, None, time_value, quantity_value, "rate", time_unit=time_unit)
    # query == "time"
    if rate_value is None:
        return Refusal("missing_rate")
    if quantity_value is None:
        return Refusal("missing_quantity")
    return RateProblem(rate_unit, rate_value, None, quantity_value, "time", time_unit=rate_unit.denominator)


__all__ = ["read_rate_problem"]
