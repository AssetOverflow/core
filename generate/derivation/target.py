"""ADR-0176 MS-1 — question-targeting.

Turns the question sentence into a :class:`Target` — what the problem is asking
for. The target is the multi-step search's pruning signal and stopping criterion
(MS-3): a chain is a candidate answer only when it matches the target.

Lexeme-level only (ADR-0165 — no question-shape grammar regex, which 0165
forbids; the existing question parser does shape-matching but returns nothing on
these GSM8K questions). The three robust signals:

- **quantities** — numbers stated *in the question* (e.g. 0033's "when she is 25"),
  via the same lexeme extractor the body uses. These participate in the derivation.
- **aggregation** — presence of an aggregation lexeme ("total", "altogether",
  "combined", "in all") — a soft hint that the final step is a sum.
- **units** — the asked unit(s), resolved by **intersection with the body's known
  units** (a precise lexeme match where the question names a body unit, e.g.
  "jumping jacks"). Superordinate units the question may use instead (weight↔pounds,
  money↔dollars) are NOT resolved here — that needs a curated superordinate-units
  pack (a future irreducible-world-fact pack, like comparatives); until then the
  unit signal is precise-but-incomplete, and the search falls back to completeness.

Refuse-preferring: an empty target unit is not an error — the search simply has a
weaker prune and leans on completeness, or refuses.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from generate.derivation.extract import extract_quantities
from generate.derivation.model import Quantity
from generate.math_roundtrip import _tokens

# Aggregation-hint lexemes (soft signal that the final op is a sum). Single-word
# entries match by word token; multi-word entries match by substring.
_AGG_WORDS: Final[tuple[str, ...]] = ("total", "altogether", "combined", "sum")
_AGG_PHRASES: Final[tuple[str, ...]] = ("in all", "in total")


@dataclass(frozen=True, slots=True)
class Target:
    """What the question asks for (ADR-0176 MS-1)."""

    quantities: tuple[Quantity, ...]  # numbers stated in the question
    aggregation: str | None  # aggregation-hint lexeme/phrase, or None
    units: tuple[str, ...]  # asked units = body units named in the question


def extract_target(question_text: str, *, known_units: tuple[str, ...] = ()) -> Target:
    """Build the :class:`Target` for ``question_text``.

    ``known_units`` are the units extracted from the problem body; the asked
    unit(s) are the subset of them that appear as tokens in the question. Pass
    ``()`` (default) when body units are unavailable -> ``units`` is empty and the
    search leans on completeness. Deterministic.
    """
    quantities: tuple[Quantity, ...] = extract_quantities(question_text)

    lowered = question_text.lower()
    tokens = _tokens(question_text)
    aggregation: str | None = None
    for word in _AGG_WORDS:
        if word in tokens:
            aggregation = word
            break
    if aggregation is None:
        for phrase in _AGG_PHRASES:
            if phrase in lowered:
                aggregation = phrase
                break

    # Asked units = body units named in the question (precise lexeme match).
    units = tuple(
        u for u in dict.fromkeys(known_units) if u and u.lower() in tokens
    )

    return Target(quantities=quantities, aggregation=aggregation, units=units)
