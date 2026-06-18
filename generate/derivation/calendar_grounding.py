"""Calendar grounding policy for cluster-contract piecewise daily-hour organs.

Sprint 11 ClusterContract: ``civil_month_day_count_table`` supplies month
day-count **only** when a named month appears in problem text.  Table values are
deterministic, tiny, and provenance-labeled ``calendar_table`` — not problem-text
operands and not serving-memory mutation.

Allowed:
- explicit civil month name in text (January–December)
- table lookup from fixed non-leap civil-year counts
- month day-count used solely as whole-month span for end-of-month totals

Refused:
- February (leap ambiguity without explicit year/rule)
- vague spans (``about a month``, ``several weeks``)
- date-range / inclusive-exclusive date math
- multiple named months in one problem
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final

from generate.math_roundtrip import _token_in, _tokens

PROVENANCE_CALENDAR_TABLE: Final[str] = "calendar_table"

# Fixed non-leap civil-year month lengths (deterministic, no runtime mutation).
CIVIL_MONTH_DAY_COUNT: Final[dict[str, int]] = {
    "january": 31,
    "february": 28,
    "march": 31,
    "april": 30,
    "may": 31,
    "june": 30,
    "july": 31,
    "august": 31,
    "september": 30,
    "october": 31,
    "november": 30,
    "december": 31,
}

# February is table-known but serving-blocked without leap-year policy.
BLOCKED_SERVING_MONTHS: Final[frozenset[str]] = frozenset({"february"})

_MONTH_NAME_RE: Final[re.Pattern[str]] = re.compile(
    r"\b(" + "|".join(sorted(CIVIL_MONTH_DAY_COUNT, key=len, reverse=True)) + r")\b",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class MonthGrounding:
    """A named month grounded via the civil table."""

    month_name: str
    day_count: int
    provenance: str = PROVENANCE_CALENDAR_TABLE

    @property
    def source_token(self) -> str:
        return f"{self.provenance}:{self.month_name}"


def extract_named_months(problem_text: str) -> tuple[str, ...]:
    """Return lowercased month names in narrative order."""
    return tuple(match.group(1).lower() for match in _MONTH_NAME_RE.finditer(problem_text))


def resolve_month_grounding(problem_text: str) -> MonthGrounding | None:
    """Resolve exactly one serving-eligible named month, or refuse."""
    months = extract_named_months(problem_text)
    if len(months) != 1:
        return None
    month = months[0]
    if month in BLOCKED_SERVING_MONTHS:
        return None
    day_count = CIVIL_MONTH_DAY_COUNT.get(month)
    if day_count is None:
        return None
    tokens = _tokens(problem_text)
    if not _token_in(month, tokens):
        return None
    return MonthGrounding(month_name=month, day_count=day_count)


def allows_halfway_split(day_count: int) -> bool:
    """Halfway-through-month splits require an even day-count month."""
    return day_count > 0 and day_count % 2 == 0


def calendar_operand_grounds(source_token: str, tokens: frozenset[str]) -> bool:
    """True when a calendar_table operand's month name appears in the text."""
    if not source_token.startswith(f"{PROVENANCE_CALENDAR_TABLE}:"):
        return False
    month = source_token.split(":", 1)[1]
    return _token_in(month, tokens)