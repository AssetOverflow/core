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
from generate.math_roundtrip import WORD_NUMBERS

# Number (int or decimal) immediately followed by a unit word. Lexeme-level.
_QTY_RE: Final[re.Pattern[str]] = re.compile(
    r"(?<![\w.])(\d+(?:\.\d+)?)\s+([a-zA-Z]+)"
)

# Word-number immediately followed by a unit word. Reuses the round-trip table
# instead of defining a second number vocabulary. The hyphenated form is limited
# to tens-one compounds such as ``twenty-four``.
_WORD_NUMBER_ALT: Final[str] = "|".join(
    re.escape(word)
    for word in sorted(WORD_NUMBERS, key=len, reverse=True)
    if word not in {"half", "third", "quarter"}
)
_WORD_QTY_RE: Final[re.Pattern[str]] = re.compile(
    rf"(?i)\b({_WORD_NUMBER_ALT})(?:-({_WORD_NUMBER_ALT}))?\s+([a-zA-Z]+)\b"
)


def _resolve_word_number(first: str, second: str | None = None) -> float | None:
    """Resolve a conservative word-number token from ``WORD_NUMBERS``."""
    first_value = WORD_NUMBERS.get(first.lower())
    if first_value is None:
        return None
    if second is None:
        return float(first_value)

    second_value = WORD_NUMBERS.get(second.lower())
    if second_value is None:
        return None
    # Conservative hyphen compounds only: twenty-four, ninety-nine, etc.
    if first_value < 20 or first_value >= 100 or not 0 < second_value < 10:
        return None
    return float(first_value + second_value)


def _digit_quantity(value_token: str, unit: str) -> Quantity | None:
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

    for match in _QTY_RE.finditer(problem_text):
        quantity = _digit_quantity(match.group(1), match.group(2))
        if quantity is not None:
            found.append((match.start(1), quantity))

    for match in _WORD_QTY_RE.finditer(problem_text):
        value = _resolve_word_number(match.group(1), match.group(2))
        if value is None:
            continue
        source_token = match.group(1) if match.group(2) is None else match.group(0).rsplit(maxsplit=1)[0]
        found.append(
            (
                match.start(1),
                Quantity(value=value, unit=match.group(3).lower(), source_token=source_token),
            )
        )

    found.sort(key=lambda item: item[0])
    return tuple(quantity for _, quantity in found)
