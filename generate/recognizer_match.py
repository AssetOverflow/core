"""ADR-0163 Phase D — per-category recognizer match.

Pure, rules-only matching of a natural-language statement against the
ratified recognizer registry.  Returns at most one
:class:`RecognizerMatch` per call (first-match-wins over the registry
order).

Doctrine
- No LLM call, no embedding, no learned classifier.  The matcher is
  the same discipline as Phase A's categorizer + Phase C's
  synthesizer.  A module-import test (mirroring Phase A/C) enforces
  this.
- Per ADR-0163 §Phase C The Synthesis Rule property (b), the
  recognizer is the *narrowest* commitment that subsumes the seeds.
  This module honors that narrowness verbatim: an out-of-corpus
  currency symbol, window unit, or per-unit value does NOT match.
  Widening happens in operator review (Phase B round 2 → Phase C
  synthesis → Phase D wiring picks up the wider spec automatically),
  never here.
- ``parsed_anchors`` carry the actual numeric tokens extracted from
  the statement (NOT from the spec).  The extraction is rules-only
  and deterministic.  For
  ``descriptive_setup_no_quantity``, ``parsed_anchors`` is the empty
  tuple by design — the recognizer admits the statement as setup
  context, contributing no math state.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Final, Literal, Mapping

from evals.refusal_taxonomy.shape_categories import ShapeCategory
from generate.recognizer_registry import RatifiedRecognizer


# Word numerals 1..20 plus the higher cardinals and a small set of
# multipliers ("dozen").  Mirrors the Phase A categorizer's
# _NUMBER_WORDS so the matcher's "has any quantity marker" predicate
# is the same shape as Phase A's "has no quantity marker" predicate.
_NUMBER_WORDS: Final[frozenset[str]] = frozenset({
    "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
    "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen",
    "seventeen", "eighteen", "nineteen", "twenty", "thirty", "forty", "fifty",
    "sixty", "seventy", "eighty", "ninety",
    "hundred", "thousand", "million", "billion",
    "dozen", "dozens",
})

_DIGIT_RE: Final[re.Pattern[str]] = re.compile(r"\d")
_INDEFINITE_TOKENS: Final[tuple[str, ...]] = (
    " some ", " several ", " a few ", " many ", " any ",
)


# Currency-per-unit "amount" regex.  Matches "$18.00 an hour" /
# "$2 per cup" / "$45/hour" / "$20 for one kg".  The captured
# groups are (symbol, amount, _spacer, per_unit).
_CURRENCY_AMOUNT_RE: Final[re.Pattern[str]] = re.compile(
    r"""(?ix)
    ([\$£€¥])                       # currency symbol
    \s*
    (\d+(?:\.\d+)?|\d+/\d+)         # amount (integer, decimal, or fraction)
    \s*
    (?:
        an?\s+([a-z]+)              # "$X an hour" / "$X a day"
      | per\s+([a-z]+)              # "$X per hour"
      | /\s*([a-z]+)                # "$X/hour"
      | for\s+(?:one|each|every|a)\s+([a-z]+)
                                    # "$X for one cup" / "for each X"
    )
    """,
)

# Temporal-aggregation event_count_per_window patterns.
#
# Matches:
#   "10 oysters in 5 minutes"          -> count=10, window="minute", q="per"
#   "10 videos each day"               -> count=10, window="day",    q="each"
#   "20 jumping jacks on Monday"       -> day-of-week single hit
#   "uploads 90 minutes daily"         -> count=90, window="day",    q="per"
#
# Three regexes cover the high-signal canonical surfaces.  Each match
# yields (count_token, window_unit, window_quantifier).
_TEMPORAL_PATTERNS: Final[tuple[tuple[re.Pattern[str], str], ...]] = (
    # "<count> ... each|every|per <unit>"
    (
        re.compile(
            r"""(?ix)
            \b(\d+(?:\.\d+)?)\b              # count_token
            [^.,;]*?                         # arbitrary intervening words
            \b(each|every|per)\s+
            (day|week|month|year|hour|minute|second)s?\b
            """
        ),
        "explicit_quantifier",
    ),
    # "<count> ... in <N> <unit>"  → "per <unit>" canonical
    (
        re.compile(
            r"""(?ix)
            \b(\d+(?:\.\d+)?)\b              # count_token
            [^.,;]*?                         # arbitrary intervening words
            \bin\s+\d+(?:\.\d+)?\s+
            (day|week|month|year|hour|minute|second)s?\b
            """
        ),
        "in_window",
    ),
    # "<count> ... <unit>ly"  (adverbial: daily, weekly, monthly...)
    (
        re.compile(
            r"""(?ix)
            \b(\d+(?:\.\d+)?)\b              # count_token
            [^.,;]*?                         # arbitrary intervening words
            \b(daily|weekly|monthly|yearly|hourly)\b
            """
        ),
        "adverbial",
    ),
)

# Day-of-week enumeration: at least two distinct day names with at
# least one numeric count.  Matches "20 ... Monday, 36 ... Tuesday".
_DAY_NAMES: Final[tuple[str, ...]] = (
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
)
_DAY_HIT_RE: Final[re.Pattern[str]] = re.compile(
    r"""(?ix)
    \b(\d+(?:\.\d+)?)\b\s*               # count_token
    [^.,;]*?                             # arbitrary intervening words
    \b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b
    """
)


@dataclass(frozen=True, slots=True)
class RecognizerMatch:
    """One ratified-recognizer hit against a natural-language statement.

    ``parsed_anchors`` carry the numeric content extracted from
    the statement.  For ``descriptive_setup_no_quantity``, the tuple
    is empty by design — the recognizer admits the statement as
    setup context, contributing no math state.
    """

    recognizer: RatifiedRecognizer
    category: ShapeCategory
    outcome: Literal["admissible", "inadmissible_by_design"]
    graph_intent: Literal["setup", "aggregate", "rate", "count", "amount"]
    parsed_anchors: tuple[Mapping[str, Any], ...]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _padded_lower(statement: str) -> str:
    return " " + statement.lower().replace("\n", " ") + " "


def _has_number_word(padded_lower: str) -> bool:
    for raw_token in padded_lower.split():
        token = raw_token.strip(".,;:!?\"'()[]{}").lower()
        if token in _NUMBER_WORDS:
            return True
    return False


def _has_any_quantity_marker(statement: str, padded_lower: str) -> bool:
    if _DIGIT_RE.search(statement):
        return True
    if _has_number_word(padded_lower):
        return True
    for needle in _INDEFINITE_TOKENS:
        if needle in padded_lower:
            return True
    return False


# ---------------------------------------------------------------------------
# Per-category matchers
# ---------------------------------------------------------------------------


def _match_descriptive_setup_no_quantity(
    statement: str, spec: Mapping[str, Any]
) -> tuple[tuple[Mapping[str, Any], ...], Literal["setup"]] | None:
    """Match a statement that carries no extractable quantity.

    Mirrors Phase A's ``_is_descriptive_setup_no_quantity`` predicate —
    a statement with NO digit, NO number word, AND NO indefinite
    quantifier is the canonical setup-context shape.

    Returns ``(empty parsed_anchors, "setup")`` on a hit; ``None``
    otherwise.  The spec's ``quantity_anchor_count`` MUST equal 0 —
    every Phase C synthesis for this category pins that, but we read
    the spec rather than hard-code.
    """
    if spec.get("quantity_anchor_count") != 0:
        return None
    padded = _padded_lower(statement)
    if _has_any_quantity_marker(statement, padded):
        return None
    return (tuple(), "setup")


def _match_temporal_aggregation(
    statement: str, spec: Mapping[str, Any]
) -> tuple[tuple[Mapping[str, Any], ...], Literal["aggregate"]] | None:
    """Match the event_count_per_window shape against *statement*.

    Narrowness: every extracted anchor's ``window_unit`` and
    ``window_quantifier`` MUST appear in the spec's observed sets.
    A statement carrying an unseen window unit / quantifier returns
    ``None``.
    """
    if spec.get("anchor_kind") != "event_count_per_window":
        return None
    observed_units = set(spec.get("observed_window_units") or ())
    observed_quantifiers = set(spec.get("observed_window_quantifiers") or ())
    if not observed_units or not observed_quantifiers:
        return None

    anchors: list[Mapping[str, Any]] = []
    padded = " " + statement.lower() + " "

    # Pass 1 — day-of-week enumeration.  At least two distinct day
    # names + a count per day yields multi-anchor day-windowed
    # aggregation.
    if "day" in observed_units and ("each" in observed_quantifiers or "every" in observed_quantifiers):
        day_hits: list[tuple[str, str]] = []
        for m in _DAY_HIT_RE.finditer(statement):
            day_hits.append((m.group(1), m.group(2).lower()))
        # Require ≥ 2 distinct day names — same threshold Phase A uses.
        distinct_days = {d for _, d in day_hits}
        if len(distinct_days) >= 2:
            quant = "each" if "each" in observed_quantifiers else "every"
            for count_token, _day in day_hits:
                anchors.append({
                    "kind": "event_count_per_window",
                    "count_token": count_token,
                    "window_unit": "day",
                    "window_quantifier": quant,
                })
            if anchors:
                return (tuple(anchors), "aggregate")

    # Pass 2 — explicit-quantifier and adverbial framings.
    for pat, kind in _TEMPORAL_PATTERNS:
        for m in pat.finditer(statement):
            if kind == "explicit_quantifier":
                count_token, quantifier, unit = m.group(1), m.group(2).lower(), m.group(3).lower()
            elif kind == "in_window":
                count_token, quantifier, unit = m.group(1), "per", m.group(2).lower()
            else:  # adverbial
                count_token = m.group(1)
                adverb = m.group(2).lower()
                # Map adverb → unit.
                unit_map = {
                    "daily": "day", "weekly": "week", "monthly": "month",
                    "yearly": "year", "hourly": "hour",
                }
                unit = unit_map[adverb]
                quantifier = "per"
            if unit not in observed_units:
                continue
            if quantifier not in observed_quantifiers:
                continue
            anchors.append({
                "kind": "event_count_per_window",
                "count_token": count_token,
                "window_unit": unit,
                "window_quantifier": quantifier,
            })

    if not anchors:
        return None

    # Spec narrowness: anchor_count must fall within the observed range.
    cmin = int(spec.get("anchor_count_min", 1))
    cmax = int(spec.get("anchor_count_max", 1))
    if not (cmin <= len(anchors) <= cmax):
        return None
    return (tuple(anchors), "aggregate")


def _match_rate_with_currency(
    statement: str, spec: Mapping[str, Any]
) -> tuple[tuple[Mapping[str, Any], ...], Literal["rate"]] | None:
    """Match the currency_per_unit_rate shape against *statement*.

    Narrowness: every extracted anchor's ``currency_symbol`` and
    ``per_unit`` MUST be in the spec's observed sets.  A statement
    carrying an unseen currency or per-unit value returns ``None``.
    """
    if spec.get("anchor_kind") != "currency_per_unit_rate":
        return None
    observed_symbols = set(spec.get("observed_currency_symbols") or ())
    observed_per_units = set(spec.get("observed_per_units") or ())
    if not observed_symbols or not observed_per_units:
        return None

    anchors: list[Mapping[str, Any]] = []
    for m in _CURRENCY_AMOUNT_RE.finditer(statement):
        symbol = m.group(1)
        amount_token = m.group(2)
        # Per-unit is whichever group captured.
        per_unit = next(
            (g for g in m.groups()[2:] if g),
            None,
        )
        if not per_unit:
            continue
        per_unit_lc = per_unit.lower()
        if symbol not in observed_symbols:
            continue
        if per_unit_lc not in observed_per_units:
            continue
        if "/" in amount_token:
            amount_kind = "word"  # fractional surface; Phase B labels as 'word'
        elif "." in amount_token:
            amount_kind = "decimal"
        else:
            amount_kind = "integer"
        anchors.append({
            "kind": "currency_per_unit_rate",
            "currency_symbol": symbol,
            "amount": amount_token,
            "amount_kind": amount_kind,
            "per_unit": per_unit_lc,
        })

    if not anchors:
        return None
    cmin = int(spec.get("anchor_count_min", 1))
    cmax = int(spec.get("anchor_count_max", 1))
    if not (cmin <= len(anchors) <= cmax):
        return None
    return (tuple(anchors), "rate")


# ---------------------------------------------------------------------------
# ADR-0163.B.2 round-2 matchers.  Detection-only (return empty
# parsed_anchors) — consistent with Phase D's skip-only wiring.  Real
# value extraction lands when Phase D.2 plumbs parsed_anchors into the
# solver.  Narrowness is enforced via shape predicates (no currency on a
# discrete-count match; no "per X" on a currency_amount match; etc.).
# ---------------------------------------------------------------------------

_PER_UNIT_TOKENS: Final[tuple[str, ...]] = (
    " per ", "/", " an hour", " a hour", " a day", " a week", " a month",
    " a year", " for one ", " for each ", " for every ",
)

_TEMPORAL_QUANTIFIER_TOKENS: Final[tuple[str, ...]] = (
    " per ", " each ", " every ", " daily", " weekly", " monthly",
    " yearly", " hourly",
)

_MULTIPLICATIVE_CONNECTIVES: Final[tuple[str, ...]] = (
    " with ", " each ", " in each ", " per each ",
)


def _has_per_unit_framing(padded_lower: str) -> bool:
    return any(tok in padded_lower for tok in _PER_UNIT_TOKENS)


def _has_temporal_quantifier(padded_lower: str) -> bool:
    return any(tok in padded_lower for tok in _TEMPORAL_QUANTIFIER_TOKENS)


def _has_currency_symbol(statement: str) -> bool:
    return any(c in statement for c in "$£€¥")


def _match_discrete_count_statement(
    statement: str, spec: Mapping[str, Any]
) -> tuple[tuple[Mapping[str, Any], ...], Literal["count"]] | None:
    """Detection-only match for "X has N Y" shape.

    Conditions:
      - statement carries ≥1 quantity marker (digit or number word)
      - statement does NOT carry a currency symbol (else currency_amount)
      - statement does NOT carry per-unit framing (else rate_with_currency)
      - statement does NOT carry temporal-quantifier framing
        (else temporal_aggregation)
      - spec's anchor_kind is "discrete_count"

    Returns ``(empty parsed_anchors, "count")`` on a hit; real value
    extraction is Phase D.2 follow-up.
    """
    if spec.get("anchor_kind") != "discrete_count":
        return None
    padded = _padded_lower(statement)
    if not _has_any_quantity_marker(statement, padded):
        return None
    if _has_currency_symbol(statement):
        return None
    if _has_per_unit_framing(padded):
        return None
    if _has_temporal_quantifier(padded):
        return None
    return (tuple(), "count")


def _match_multiplicative_aggregation(
    statement: str, spec: Mapping[str, Any]
) -> tuple[tuple[Mapping[str, Any], ...], Literal["aggregate"]] | None:
    """Detection-only match for "M outer × N inner" shape.

    Conditions:
      - spec's anchor_kind is "multiplicative_aggregate"
      - statement carries a multiplicative connective
        ("with", "each holds", "in each", etc.)
      - statement carries ≥2 quantity markers (the outer + inner counts)
      - statement does NOT carry currency-per-unit framing

    Returns ``(empty parsed_anchors, "aggregate")`` on a hit.
    """
    if spec.get("anchor_kind") != "multiplicative_aggregate":
        return None
    padded = _padded_lower(statement)
    if not any(c in padded for c in _MULTIPLICATIVE_CONNECTIVES):
        return None
    # Count distinct quantity markers (digits + number words).  At least
    # two needed to admit a multiplicative shape.
    digit_hits = len(_DIGIT_RE.findall(statement))
    word_hits = sum(
        1 for token in padded.split()
        if token.strip(".,;:!?\"'()[]{}").lower() in _NUMBER_WORDS
    )
    if (digit_hits + word_hits) < 2:
        return None
    if _has_currency_symbol(statement) and _has_per_unit_framing(padded):
        return None
    return (tuple(), "aggregate")


def _match_currency_amount(
    statement: str, spec: Mapping[str, Any]
) -> tuple[tuple[Mapping[str, Any], ...], Literal["amount"]] | None:
    """Detection-only match for "X costs $Y" (NO per-unit framing).

    Discriminator vs rate_with_currency: this matcher REQUIRES a
    currency symbol AND requires that no per-unit framing is present.

    Narrowness: the currency symbol observed in the statement MUST
    appear in the spec's ``observed_currency_symbols`` set.

    Returns ``(empty parsed_anchors, "amount")`` on a hit.
    """
    if spec.get("anchor_kind") != "currency_amount":
        return None
    observed_symbols = set(spec.get("observed_currency_symbols") or ())
    if not observed_symbols:
        return None
    # Find at least one currency symbol present in the statement that is
    # also observed by the spec.
    found_observed = any(sym in statement for sym in observed_symbols)
    if not found_observed:
        return None
    padded = _padded_lower(statement)
    if _has_per_unit_framing(padded):
        return None
    return (tuple(), "amount")


_MATCHERS: Final[dict[ShapeCategory, Any]] = {
    ShapeCategory.DESCRIPTIVE_SETUP_NO_QUANTITY: _match_descriptive_setup_no_quantity,
    ShapeCategory.TEMPORAL_AGGREGATION: _match_temporal_aggregation,
    ShapeCategory.RATE_WITH_CURRENCY: _match_rate_with_currency,
    ShapeCategory.DISCRETE_COUNT_STATEMENT: _match_discrete_count_statement,
    ShapeCategory.MULTIPLICATIVE_AGGREGATION: _match_multiplicative_aggregation,
    ShapeCategory.CURRENCY_AMOUNT: _match_currency_amount,
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def match(
    statement: str,
    registry: tuple[RatifiedRecognizer, ...],
) -> RecognizerMatch | None:
    """First-match-wins over *registry*.

    Pure: same ``(statement, registry)`` → same result, byte-identical.
    Order is registry order (the projection step in
    :mod:`generate.recognizer_registry` sorts by ``(review_date,
    proposal_id)``).
    """
    if not isinstance(statement, str) or not statement.strip():
        return None
    for recognizer in registry:
        matcher = _MATCHERS.get(recognizer.shape_category)
        if matcher is None:
            continue
        result = matcher(statement, recognizer.canonical_pattern)
        if result is None:
            continue
        parsed_anchors, graph_intent = result
        outcome: Literal["admissible", "inadmissible_by_design"] = (
            "inadmissible_by_design"
            if recognizer.shape_category is ShapeCategory.DESCRIPTIVE_SETUP_NO_QUANTITY
            else "admissible"
        )
        return RecognizerMatch(
            recognizer=recognizer,
            category=recognizer.shape_category,
            outcome=outcome,
            graph_intent=graph_intent,
            parsed_anchors=parsed_anchors,
        )
    return None


__all__ = [
    "RecognizerMatch",
    "match",
]
