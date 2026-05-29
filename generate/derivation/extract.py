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

# Number with no following unit, at the end of a sentence/text. Emits an empty
# unit so the quantity remains available to downstream gates without inventing a
# unit lexeme.
_FINAL_NUMBER_RE: Final[re.Pattern[str]] = re.compile(
    r"(?<![\w.])(\d+(?:\.\d+)?)(?=\s*(?:[.?!]|$))"
)


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
    occupied_spans: list[tuple[int, int]] = []

    for match in _QTY_RE.finditer(problem_text):
        quantity = _quantity(match.group(1), match.group(2))
        if quantity is not None:
            occupied_spans.append(match.span(1))
            found.append((match.start(1), quantity))

    for match in _FINAL_NUMBER_RE.finditer(problem_text):
        if any(start <= match.start(1) < end for start, end in occupied_spans):
            continue
        quantity = _quantity(match.group(1), "")
        if quantity is not None:
            found.append((match.start(1), quantity))

    found.sort(key=lambda item: item[0])
    return tuple(quantity for _, quantity in found)
