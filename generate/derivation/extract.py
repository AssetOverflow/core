"""ADR-0175 Phase 3b — lexeme-level quantity extraction.

Pulls ``(value, unit, source_token)`` triples from a problem using a single
orthographic pattern: a number immediately followed by a unit word. Per
ADR-0165 this is a *lexeme* pattern ("what this piece looks like: a number, a
unit word") — not a grammar template ("how words combine to mean X"). The
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


def extract_quantities(problem_text: str) -> tuple[Quantity, ...]:
    """Extract ``(value, unit, source_token)`` quantities in left-to-right order.

    Deterministic. ``source_token`` is the surface number string (used by the
    self-verification gate to prove the value is grounded in the text). Units
    are lowercased; the value's surface token is preserved verbatim.
    """
    out: list[Quantity] = []
    for match in _QTY_RE.finditer(problem_text):
        value_token = match.group(1)
        unit = match.group(2).lower()
        try:
            value = float(value_token)
        except ValueError:  # pragma: no cover - regex guarantees numeric
            continue
        out.append(Quantity(value=value, unit=unit, source_token=value_token))
    return tuple(out)
