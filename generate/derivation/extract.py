"""ADR-0175 Phase 3b — lexeme-level quantity extraction.

Pulls ``(value, unit, source_token)`` triples from a problem using conservative
orthographic patterns. Per ADR-0165 these are *lexeme* patterns ("what this
piece looks like") — not grammar templates ("how words combine to mean X"). The
*combining* is the search's job (search.py) gated by self-verification.
"""

from __future__ import annotations

import re
from typing import Final

from generate.derivation.model import Quantity

# Number (int or decimal) immediately followed by a unit word. Lexeme-level.
_QTY_RE: Final[re.Pattern[str]] = re.compile(
    r"(?<![\w.])(\d+(?:\.\d+)?)\s+([a-zA-Z]+)"
)

# Same-unit numeric list with the unit stated once at the end, e.g.
# ``20, 36, 40 and 50 push-ups``.  This is still orthographic: a run of number
# tokens separated by comma/and delimiters, followed by one unit token.  It does
# not infer semantic grouping; downstream verification decides whether the
# resulting quantities can compose.
_LIST_WITH_TRAILING_UNIT_RE: Final[re.Pattern[str]] = re.compile(
    r"(?<![\w.])"
    r"((?:\d+(?:\.\d+)?\s*(?:,\s*|\s+and\s+)){1,}\d+(?:\.\d+)?)"
    r"\s+([a-zA-Z]+(?:-[a-zA-Z]+)*)"
)
_NUMBER_RE: Final[re.Pattern[str]] = re.compile(r"\d+(?:\.\d+)?")


def _quantity(value_token: str, unit: str) -> Quantity | None:
    """Build a quantity from an already-matched numeric token."""
    try:
        value = float(value_token)
    except ValueError:  # pragma: no cover - regex guarantees numeric
        return None
    return Quantity(value=value, unit=unit.lower(), source_token=value_token)


def extract_quantities(problem_text: str) -> tuple[Quantity, ...]:
    """Extract ``(value, unit, source_token)`` quantities in left-to-right order.

    Deterministic. ``source_token`` is the surface number string (used by the
    self-verification gate to prove the value is grounded in the text). Units
    are lowercased; the value's surface token is preserved verbatim.
    """
    found: list[tuple[int, Quantity]] = []
    inherited_spans: list[tuple[int, int]] = []

    for match in _LIST_WITH_TRAILING_UNIT_RE.finditer(problem_text):
        unit = match.group(2).lower()
        inherited_spans.append(match.span())
        for num in _NUMBER_RE.finditer(match.group(1)):
            quantity = _quantity(num.group(0), unit)
            if quantity is not None:
                found.append((match.start(1) + num.start(), quantity))

    for match in _QTY_RE.finditer(problem_text):
        if any(start <= match.start() < end for start, end in inherited_spans):
            continue
        quantity = _quantity(match.group(1), match.group(2))
        if quantity is not None:
            found.append((match.start(1), quantity))

    found.sort(key=lambda item: item[0])
    return tuple(quantity for _, quantity in found)
