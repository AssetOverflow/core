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
# "$2 per cup" / "$45/hour" / "$20 for one kg".
# Captures symbol, amount, and the rate connector (the word that will
# become matched_verb for apply_rate) + per_unit.
# The connector is localized to the rate surface span so that
# _locate_rate_verb no longer does a dangerous whole-sentence scan
# that could pick an unrelated "a" from earlier text.
_CURRENCY_AMOUNT_RE: Final[re.Pattern[str]] = re.compile(
    r"""(?ix)
    ([\$£€¥])                       # 1: currency symbol
    \s*
    (\d+(?:\.\d+)?|\d+/\d+)         # 2: amount
    \s*
    (?:
        (an?)\s+([a-z]+)              # 3: a/an connector, 4: unit   ("$X an hour")
      | (per)\s+([a-z]+)              # 5: per, 6: unit
      | /\s*([a-z]+)                  # 7: unit (slash shorthand)
      | for\s+(one|each|every|a)\s+([a-z]+)  # 8: the quant, 9: unit
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

    ME-1 (ADR-0169 composition consumption) — when
    ``spec["anchor_kind"] == "currency_per_unit_composition"`` this
    matcher dispatches to :func:`_try_extract_currency_per_unit_composition_anchor`
    which publishes ``composition_shape`` + a pre-composed
    :class:`CandidateInitial` in ``parsed_anchors`` so the consumption
    path in :func:`generate.recognizer_anchor_inject.inject_from_match`
    can admit the statement under an operator-ratified
    ``multiplicative_composition`` entry.
    """
    anchor_kind = spec.get("anchor_kind")
    if anchor_kind == "currency_per_unit_composition":
        return _try_extract_currency_per_unit_composition_anchor(statement, spec)
    if anchor_kind != "currency_per_unit_rate":
        return None
    observed_symbols = set(spec.get("observed_currency_symbols") or ())
    observed_per_units = set(spec.get("observed_per_units") or ())
    if not observed_symbols or not observed_per_units:
        return None

    anchors: list[Mapping[str, Any]] = []
    for m in _CURRENCY_AMOUNT_RE.finditer(statement):
        symbol = m.group(1)
        amount_token = m.group(2)

        # Determine the rate connector (the token that will serve as
        # matched_verb) and the per_unit *from the matched rate span only*.
        # This prevents the whole-sentence scan hazard in the injector.
        connector = None
        per_unit = None
        if m.group(3):  # a/an case
            connector = m.group(3)
            per_unit = m.group(4)
        elif m.group(5):  # per
            connector = m.group(5)
            per_unit = m.group(6)
        elif m.group(7):  # slash
            connector = "per"  # canonicalize / as per for apply_rate verb
            per_unit = m.group(7)
        elif m.group(8):
            q = m.group(8).lower()
            per_unit = m.group(9)
            if q in ("each", "every", "a", "one"):
                connector = q
            else:
                connector = None

        if not per_unit:
            continue
        per_unit_lc = per_unit.lower()
        if symbol not in observed_symbols:
            continue
        if per_unit_lc not in observed_per_units:
            continue
        if "/" in amount_token:
            amount_kind = "word"
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
            "rate_anchor_token": connector.lower() if connector else None,
        })

    if not anchors:
        return None
    cmin = int(spec.get("anchor_count_min", 1))
    cmax = int(spec.get("anchor_count_max", 1))
    if not (cmin <= len(anchors) <= cmax):
        return None
    return (tuple(anchors), "rate")


# ---------------------------------------------------------------------------
# ME-1 — currency-per-unit COMPOSITION extension (ADR-0169 consumption).
#
# Lights up the dormant consumption path shipped by CW-2: when a
# statement carries a count-of-items + per-item cost shape with a
# same-sentence proper-noun subject, this helper publishes a
# pre-composed CandidateInitial in ``parsed_anchors`` along with the
# ``composition_shape`` key the composition_registry gates on.
#
# Subject-binding discipline: Option A from
# docs/handoff/MATCHER-EXTENSION-DISPATCH-PACK.md — refuse the
# composition emission when no same-sentence proper-noun subject is
# present. Option B (placeholder subject) is forbidden by the brief;
# Option C (cross-sentence lookup) ships in ME-2.
# ---------------------------------------------------------------------------

_CURRENCY_SYMBOL_TO_UNIT: Final[dict[str, str]] = {
    "$": "dollars",
    "£": "pounds",
    "€": "euros",
    "¥": "yen",
}

_PER_ITEM_TOKENS: Final[frozenset[str]] = frozenset({"each", "apiece"})

_COMPOSITION_VERBS: Final[frozenset[str]] = frozenset({"buys", "bought"})

_COMPOSITION_SHAPE_MULTIPLICATIVE: Final[str] = "bound(count) × bound(unit_cost)"


# Shape: `<Subject> <buy-verb> <count> <noun-phrase>(?: at| for) <$amount>(?: each|apiece)`
# Example: "Maria bought 3 vet appointments at $400 each."
_COMPOSITION_SUBJECT_BUY_RE: Final[re.Pattern[str]] = re.compile(
    r"""(?x)
    ^\s*
    (?P<subject>[A-Z][a-zA-Z]+)            # same-sentence proper-noun subject
    \s+
    (?P<verb>buys|bought)
    \s+
    (?P<count>\d+(?:\.\d+)?)               # outer count token (integer/decimal)
    \s+
    (?P<noun>[a-z][a-z\s]+?)               # counted noun phrase (lowercase words)
    \s+
    (?:at|for)\s+
    (?P<symbol>[\$£€¥])
    (?P<amount>\d+(?:\.\d+)?)              # unit cost
    \s+
    (?P<per_unit>each|apiece)
    \b
    """,
)


def _try_extract_currency_per_unit_composition_anchor(
    statement: str, spec: Mapping[str, Any]
) -> tuple[tuple[Mapping[str, Any], ...], Literal["rate"]] | None:
    """Extract a pre-composed CandidateInitial anchor or refuse.

    Narrowness layers (all must hold; any failure returns ``None``):

    1. ``spec["anchor_kind"] == "currency_per_unit_composition"`` (caller-checked)
    2. ``spec["observed_currency_symbols"]`` and
       ``spec["observed_per_units"]`` are non-empty (the same narrowness
       as the rate matcher; protects against unseen currency / per-unit)
    3. Exactly one match of :data:`_COMPOSITION_SUBJECT_BUY_RE` in the
       statement (multi-match refuses to avoid ambiguity)
    4. Currency symbol in ``observed_currency_symbols``
    5. Per-unit token in ``observed_per_units``
    6. Outer count is a positive integer or float (``> 0``)
    7. Unit cost is a positive integer or float (``> 0``)
    8. The composed value (``count × unit_cost``) is finite and positive
    9. The subject is not in the existing refused-subject set
       (mirrors ``_REFUSED_SUBJECT_TOKENS`` for parity with the
       discrete-count extractor)

    On success the anchor carries:

    - ``composition_shape``: the canonical pattern string ratified
      operators bind under ``multiplicative_composition``
    - ``composed_initial``: a fully-constructed CandidateInitial
    - audit fields: ``currency_symbol``, ``amount``, ``per_unit``,
      ``outer_count``, ``subject``, ``verb``
    """
    observed_symbols = set(spec.get("observed_currency_symbols") or ())
    observed_per_units = set(spec.get("observed_per_units") or ())
    if not observed_symbols or not observed_per_units:
        return None

    matches = list(_COMPOSITION_SUBJECT_BUY_RE.finditer(statement))
    if len(matches) != 1:
        # Refusal-preferring: zero matches (no shape) or multi-match
        # (ambiguity) both refuse the composition emission.
        return None

    m = matches[0]
    subject = m.group("subject")
    if subject.lower() in _REFUSED_SUBJECT_TOKENS:
        return None
    verb = m.group("verb").lower()
    if verb not in _COMPOSITION_VERBS:
        return None

    symbol = m.group("symbol")
    if symbol not in observed_symbols:
        return None

    per_unit_lc = m.group("per_unit").lower()
    if per_unit_lc not in observed_per_units:
        return None
    if per_unit_lc not in _PER_ITEM_TOKENS:
        # Defense in depth: only per-item quantifiers compose
        # multiplicatively in the v1 scope. ``per hour`` is rate, not
        # composition.
        return None

    count_token = m.group("count")
    amount_token = m.group("amount")
    try:
        outer_count: float = float(count_token)
        unit_cost: float = float(amount_token)
    except ValueError:
        return None
    if outer_count <= 0 or unit_cost <= 0:
        return None

    composed_value_f = outer_count * unit_cost
    if composed_value_f != composed_value_f:  # NaN guard
        return None
    composed_value: int | float
    if composed_value_f.is_integer() and "." not in count_token and "." not in amount_token:
        composed_value = int(composed_value_f)
    else:
        composed_value = composed_value_f

    unit = _CURRENCY_SYMBOL_TO_UNIT.get(symbol)
    if unit is None:
        return None  # Defense in depth — observed set should already filter

    # Lazy import: CandidateInitial / InitialPossession / Quantity live
    # in modules that don't depend on recognizer_match — import here to
    # avoid coupling at module load time.
    from generate.math_candidate_parser import CandidateInitial
    from generate.math_problem_graph import InitialPossession, Quantity

    composed_initial = CandidateInitial(
        initial=InitialPossession(
            entity=subject,
            quantity=Quantity(value=composed_value, unit=unit),
        ),
        source_span=m.group(0),
        matched_anchor=verb,
        matched_value_token=str(composed_value),
        matched_unit_token=unit,
        matched_entity_token=subject,
        composition_evidence={
            "composition_shape": _COMPOSITION_SHAPE_MULTIPLICATIVE,
            "input_tokens": f"{count_token}|{amount_token}",
            "currency_symbol": symbol,
            "entity_source": "same_sentence",
        },
    )

    anchor: Mapping[str, Any] = {
        "kind": "currency_per_unit_composition",
        "composition_shape": _COMPOSITION_SHAPE_MULTIPLICATIVE,
        "composed_initial": composed_initial,
        "currency_symbol": symbol,
        "amount": amount_token,
        "per_unit": per_unit_lc,
        "outer_count": count_token,
        "subject": subject,
        "verb": verb,
    }
    return ((anchor,), "rate")


# ---------------------------------------------------------------------------
# ME-2 — cross-sentence subject binding (admits case 0019).
#
# Case 0019: "John adopts a dog from a shelter. The dog ends up having
# health problems and this requires 3 vet appointments, which cost
# $400 each."
#
# The composition sentence has no same-sentence proper-noun subject —
# "John" lives in sentence 0. ME-1 (Option A) refuses; ME-2 admits
# when the caller supplies a ``prior_subject`` resolved from the
# upstream sentence trace.
#
# Discipline:
# - The cross-sentence regex requires NO subject prefix; instead it
#   keys on a discourse-anaphoric introduction like "which cost $X each"
#   or "and this requires N noun" + "$X each" in the same sentence.
# - Caller is responsible for providing a confidence-pinned prior
#   subject (most-recent proper-noun subject from prior sentences).
# - The matcher refuses if prior_subject is None / empty / refused.
# ---------------------------------------------------------------------------

# Shape: `... which cost(s)? $<amount> each` plus a preceding count token.
# Constructed so the count + noun are pulled from the same statement, but
# the subject is supplied externally.
_CROSS_SENTENCE_COMPOSITION_RE: Final[re.Pattern[str]] = re.compile(
    r"""(?ix)
    \b
    (?:requires|require|needs|need|costs|cost)
    \s+
    (?P<count>\d+(?:\.\d+)?)               # outer count token
    \s+
    (?P<noun>[a-z][a-z\s]+?)               # counted noun phrase
    ,?\s+
    (?:which\s+)?
    (?:cost|costs|costing)
    \s+
    (?P<symbol>[\$£€¥])
    (?P<amount>\d+(?:\.\d+)?)
    \s+
    (?P<per_unit>each|apiece)
    \b
    """,
)


def try_extract_cross_sentence_composition_anchor(
    statement: str,
    spec: Mapping[str, Any],
    prior_subject: str | None,
) -> tuple[tuple[Mapping[str, Any], ...], Literal["rate"]] | None:
    """Cross-sentence composition extraction.

    Like :func:`_try_extract_currency_per_unit_composition_anchor` but
    sources the subject from ``prior_subject`` instead of a
    same-sentence head proper-noun.

    Refuses when:

    - ``prior_subject`` is None / empty / in :data:`_REFUSED_SUBJECT_TOKENS`
    - the cross-sentence regex matches zero or multiple times
    - currency / per-unit / count narrowness fail (mirrors ME-1)

    The same composition_shape + composed_initial payload as ME-1 is
    published. The consumer (composition_registry) gates admission.
    """
    if spec.get("anchor_kind") != "currency_per_unit_composition":
        return None
    if not prior_subject or not isinstance(prior_subject, str):
        return None
    if prior_subject.lower() in _REFUSED_SUBJECT_TOKENS:
        return None

    observed_symbols = set(spec.get("observed_currency_symbols") or ())
    observed_per_units = set(spec.get("observed_per_units") or ())
    if not observed_symbols or not observed_per_units:
        return None

    matches = list(_CROSS_SENTENCE_COMPOSITION_RE.finditer(statement))
    if len(matches) != 1:
        return None

    m = matches[0]
    symbol = m.group("symbol")
    if symbol not in observed_symbols:
        return None
    per_unit_lc = m.group("per_unit").lower()
    if per_unit_lc not in observed_per_units:
        return None
    if per_unit_lc not in _PER_ITEM_TOKENS:
        return None

    count_token = m.group("count")
    amount_token = m.group("amount")
    try:
        outer_count: float = float(count_token)
        unit_cost: float = float(amount_token)
    except ValueError:
        return None
    if outer_count <= 0 or unit_cost <= 0:
        return None

    composed_value_f = outer_count * unit_cost
    if composed_value_f != composed_value_f:  # NaN guard
        return None
    composed_value: int | float
    if (
        composed_value_f.is_integer()
        and "." not in count_token
        and "." not in amount_token
    ):
        composed_value = int(composed_value_f)
    else:
        composed_value = composed_value_f

    unit = _CURRENCY_SYMBOL_TO_UNIT.get(symbol)
    if unit is None:
        return None

    from generate.math_candidate_parser import CandidateInitial
    from generate.math_problem_graph import InitialPossession, Quantity

    # Validate prior_subject can satisfy CandidateInitial.entity.
    entity = prior_subject.strip()
    if not entity:
        return None

    composed_initial = CandidateInitial(
        initial=InitialPossession(
            entity=entity,
            quantity=Quantity(value=composed_value, unit=unit),
        ),
        source_span=m.group(0),
        matched_anchor="bought",  # canonical buy-anchor for the whitelist
        matched_value_token=str(composed_value),
        matched_unit_token=unit,
        matched_entity_token=entity,
        composition_evidence={
            "composition_shape": _COMPOSITION_SHAPE_MULTIPLICATIVE,
            "input_tokens": f"{count_token}|{amount_token}",
            "currency_symbol": symbol,
            "entity_source": "prior_sentence",
        },
    )

    anchor: Mapping[str, Any] = {
        "kind": "currency_per_unit_composition_cross_sentence",
        "composition_shape": _COMPOSITION_SHAPE_MULTIPLICATIVE,
        "composed_initial": composed_initial,
        "currency_symbol": symbol,
        "amount": amount_token,
        "per_unit": per_unit_lc,
        "outer_count": count_token,
        "subject": entity,
        "subject_source": "prior_sentence",
    }
    return ((anchor,), "rate")


# Refused subjects mirrors the constant defined later in this module
# (used by both the same-sentence and cross-sentence extractors).


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
    # RAT-1 — standalone per-item quantifiers. "$400 each" is per-unit
    # framing semantically equivalent to "$400 per item". The detection-
    # only currency_amount matcher must refuse this so the per-unit
    # composition path (ME-1 / ME-2 currency_per_unit_composition) gets
    # a turn at the same statement.
    " each ", " each.", " apiece ", " apiece.",
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
    """ADR-0163.D.2 — extraction match for "X has N Y" shape.

    Detection conditions (same as round-2 detection-only matcher):
      - statement carries ≥1 quantity marker (digit or number word)
      - statement does NOT carry a currency symbol (else currency_amount)
      - statement does NOT carry per-unit framing (else rate_with_currency)
      - statement does NOT carry temporal-quantifier framing
        (else temporal_aggregation)
      - spec's anchor_kind is "discrete_count"

    Extraction (D.2 v1) populates a SINGLE anchor when ALL of the
    following narrowness rules hold; otherwise returns
    ``(empty parsed_anchors, "count")`` (detection-only fallback, same
    skip-only safety as round 2).  Narrowness layers (refusal-preferring,
    wrong=0 doctrine):

      1. Statement matches the canonical possession form
         ``<ProperNoun> <poss-verb> <count> <counted_noun>...``.
         Subject must be a single capitalized proper noun (no
         conjunctions, no leading pronoun).  Possession verb must come
         from the v1 closed whitelist (has/have/had); broader verbs
         (owns/holds/contains) defer to a coordinated CandidateInitial
         change in a follow-up PR.
      2. Statement carries exactly ONE numeric token (digit or word
         numeral) — a second count indicates multi-anchor content the
         v1 schema cannot honor; refuse extraction.
      3. Statement contains no clause-splitting connectives (``but``,
         ``then``, ``however``, ``before``, ``after``, ``and``,
         ``or``) — these indicate trailing operations or enumerations
         that would invalidate a single InitialPossession.
      4. count_kind ∈ spec.observed_count_kinds.
      5. counted_noun ∈ spec.observed_counted_nouns (case-insensitive,
         matched against the closed lemma list from Phase B/C).

    The matcher returns ``(populated parsed_anchors, "count")`` on
    extraction success, ``(tuple(), "count")`` on detection-only
    fallback (skip-only safe), or ``None`` on detection failure.
    Phase D.2's per-category injector consumes the populated anchors;
    the empty-tuple fallback continues the round-2 skip-only behavior.
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

    anchor = _try_extract_discrete_count_anchor(statement, padded, spec)
    if anchor is not None:
        return ((anchor,), "count")
    # ADR-0174 Phase 3b — when single-anchor extraction fails (typically
    # because of clause_split layer refusal), try the compound-clause
    # extractor.  Pure conjunctive lists of discrete counts ("Malcolm has
    # 240 followers on Instagram and 500 followers on Facebook") emit
    # multiple anchors sharing the head's subject + verb. Refusal-
    # preferring: if any tail clause fails to ground a count+noun pair
    # from the closed observed_counted_nouns set, the whole compound
    # refuses.
    compound = _try_extract_compound_discrete_count_anchors(statement, padded, spec)
    if compound is not None:
        return (compound, "count")
    return (tuple(), "count")


# ---------------------------------------------------------------------------
# ADR-0163.D.2 — discrete_count_statement value extraction (v1).
# ---------------------------------------------------------------------------

# Closed possession-verb whitelist.  These verbs assert a static
# possession state (no goal, no acquisition event, no transfer).  Verbs
# like 'collected', 'wants', 'lost', 'bought', etc. are deliberately
# omitted — they encode operations, not initial state, and admitting
# them as InitialPossession would over-extract.
#
# v1 intentionally restricts the surface to has/have/had so the
# extracted matched_anchor token is always accepted by the downstream
# CandidateInitial post-init whitelist.  Widening to owns/holds/contains
# requires a coordinated CandidateInitial change and lands in a follow-up
# PR after the framework's empirical lift is operator-reviewed.
_POSSESSION_VERBS: Final[frozenset[str]] = frozenset({
    "has", "have", "had",
})

# ADR-0170 W2 — acquisition verbs: surface verbs that grammatically place
# the actor as the *gainer* of the operand quantity, NOT as having the
# operand as an initial state.  Per ADR-0131.G.1 these verbs route to
# CandidateOperation(add), not CandidateInitial — emitting them as
# initials would create branch disagreement with the regex parser's
# ADD_VERBS path.
#
# Each member is also a member of generate.math_roundtrip.ADD_VERBS so
# the downstream CandidateOperation post-init whitelist accepts the
# matched_verb token.
#
# DELIBERATELY EXCLUDED:
# - "gained / gains / gain": delta-of-attribute (weight, age) — admitting
#   as add-operation risks wrong>0 on questions that ask total state
# - "donated / donates / donate": SUBTRACT verb (actor gives away)
# - "saved / saves / save": ambiguous (saved time vs saved up money)
#
# Widening this set is operator-reviewable per the wrong=0 hazard
# documented in feedback-wrong-zero-hazard-case-0050.
_ACQUISITION_VERBS: Final[frozenset[str]] = frozenset({
    "collected", "collects", "collect",
    "received", "receives", "receive",
    "bought", "buys", "buy",
    "got", "gets", "get",
})

# Pronoun subjects refused at extraction (ambiguous referent).  The
# extractor requires a concrete proper-noun subject the source span can
# ground.
_REFUSED_SUBJECT_TOKENS: Final[frozenset[str]] = frozenset({
    "he", "she", "they", "it", "we", "you", "i",
    "him", "her", "them", "us",
})

# Clause-splitting / enumeration markers.  Their presence indicates a
# second clause that may carry operations or additional anchors, so
# v1 refuses extraction (skip-only fallback preserves wrong=0).
_CLAUSE_SPLIT_TOKENS: Final[tuple[str, ...]] = (
    " but ", " then ", " however ", " before ", " after ",
    " and ", " or ", " while ", " until ", " unless ",
    ", and ", ", but ", ", or ", ", then ",
)

# Hyphenated compound cardinal: 'twenty-five', 'ninety-nine'.  These
# are word-form counts.  The narrowness rule below classifies any
# non-digit token in the count slot as count_kind='word'.
_HYPHEN_CARDINAL_RE: Final[re.Pattern[str]] = re.compile(r"^[a-z]+-[a-z]+$")


def _extract_discrete_count_re_for(counted_nouns: list[str]) -> re.Pattern[str]:
    """Build the extraction regex for a closed counted-noun set.

    The counted-noun alternation is constructed from the spec's
    ``observed_counted_nouns``; multi-word nouns (e.g., ``Pokemon cards``)
    are honored verbatim.  Longest-first to prevent the alternation
    swallowing a prefix.
    """
    # Sort longest-first so 'Pokemon cards' wins over 'cards'.
    options = sorted({n for n in counted_nouns if n}, key=len, reverse=True)
    noun_alt = "|".join(re.escape(n) for n in options)
    return re.compile(
        r"^\s*"
        r"(?P<subject>(?-i:[A-Z][a-z]+))"     # case-sensitive proper noun
        r"\s+(?P<verb>[A-Za-z]+)"             # any word; verified against whitelist
        r"\s+(?P<count>\d+|[A-Za-z\-]+)"      # integer or word/hyphenated cardinal
        r"\s+(?P<noun>" + noun_alt + r")"
        r"(?:\b.*)?$",                        # optional trailing content
        flags=re.IGNORECASE,
    )


# ADR-0192 — words that terminate (cannot be part of) an open counted-noun
# phrase: prepositions, conjunctions, determiners, and comparative markers.
# Bounding the phrase against these is what stops the open noun from
# swallowing a trailing prepositional phrase ("mango trees on his farm" →
# "mango trees", not "mango trees on his farm").
_OPEN_NOUN_STOP: Final[str] = (
    "on|in|at|to|for|with|of|from|by|per|into|onto|over|under|"
    "and|or|but|than|as|that|which|who|whose|whom|while|when|because|"
    "the|a|an|his|her|its|their|our|your|my|each|every|"
    "more|fewer|less|most|fewest|other|another"
)


def _extract_discrete_count_re_open(counted_nouns: list[str]) -> re.Pattern[str]:
    """ADR-0192 — open-vocabulary variant of the single-anchor extractor.

    Strictly additive: the counted-noun slot matches either a ratified
    ``observed_counted_nouns`` entry (closed branch — preserves casing
    canonicalization and capitalized compounds like ``Pokemon cards``) OR
    an OPEN lowercase noun phrase: 1–3 consecutive lowercase word tokens,
    none a boundary/stop word.  The ``(?-i:...)`` makes the open branch
    lowercase-only so it never captures a following proper noun, and the
    stop-word lookahead bounds the phrase so it never swallows a trailing
    prepositional phrase.  Every other narrowness layer (proper-noun
    subject, verb whitelist, single numeric token, no clause-split) is
    unchanged; wrong=0 is held downstream by the ADR-0191 completeness
    guard + round-trip + branch-disagreement.
    """
    options = sorted({n for n in counted_nouns if n}, key=len, reverse=True)
    closed_alt = "|".join(re.escape(n) for n in options)
    open_tok = rf"(?-i:(?!(?:{_OPEN_NOUN_STOP})\b)[a-z]+)"
    open_noun = rf"{open_tok}(?:\s+{open_tok}){{0,2}}"
    noun_group = (
        rf"(?P<noun>{closed_alt}|{open_noun})" if closed_alt
        else rf"(?P<noun>{open_noun})"
    )
    return re.compile(
        r"^\s*"
        r"(?P<subject>(?-i:[A-Z][a-z]+))"
        r"\s+(?P<verb>[A-Za-z]+)"
        r"\s+(?P<count>\d+|[A-Za-z\-]+)"
        r"\s+" + noun_group +
        r"(?:\b.*)?$",
        flags=re.IGNORECASE,
    )


_DIGIT_RUN_RE: Final[re.Pattern[str]] = re.compile(r"\d+(?:\.\d+)?")


def _count_quantity_tokens(statement: str, padded_lower: str) -> int:
    """Total numeric tokens (digit runs + number words) in *statement*.

    Used for the "exactly one count" narrowness rule.  Hyphenated
    cardinals count as one token; a multi-digit integer (``400``) counts
    as one token, not as multiple single-digit hits.
    """
    digit_hits = len(_DIGIT_RUN_RE.findall(statement))
    word_hits = 0
    for raw in padded_lower.split():
        tok = raw.strip(".,;:!?\"'()[]{}").lower()
        if tok in _NUMBER_WORDS:
            word_hits += 1
        elif _HYPHEN_CARDINAL_RE.match(tok):
            # Hyphenated cardinal only counts when at least one half is
            # a known number word.
            left, _, right = tok.partition("-")
            if left in _NUMBER_WORDS or right in _NUMBER_WORDS:
                word_hits += 1
    return digit_hits + word_hits


def _try_extract_discrete_count_anchor(
    statement: str,
    padded_lower: str,
    spec: Mapping[str, Any],
) -> Mapping[str, Any] | None:
    """Refusal-preferring single-anchor extraction (D.2 v1).

    Returns ``None`` when any narrowness layer fails — the caller then
    falls back to skip-only detection.  The returned anchor is the
    discrete_count_statement schema dict: ``kind``, ``subject_role``,
    ``count_token``, ``count_kind``, ``counted_noun``.
    """
    raw_kinds = spec.get("observed_count_kinds") or ()
    raw_nouns = spec.get("observed_counted_nouns") or ()
    observed_kinds: list[str] = [str(k) for k in raw_kinds]
    observed_nouns: list[str] = [str(n) for n in raw_nouns]
    if not observed_kinds or not observed_nouns:
        return None

    # Narrowness #3 — clause-split / enumeration markers.
    for token in _CLAUSE_SPLIT_TOKENS:
        if token in padded_lower:
            return None

    # Narrowness #2 — exactly one numeric token.
    if _count_quantity_tokens(statement, padded_lower) != 1:
        return None

    # Narrowness #1 — shape. ADR-0192: the counted-noun slot is open
    # (adjective* + multi-word head) rather than gated on the closed
    # observed_counted_nouns set; the other narrowness layers above plus
    # the downstream ADR-0191 completeness guard / round-trip / branch
    # disagreement hold wrong=0 without the curated noun list.
    extract_re = _extract_discrete_count_re_open(observed_nouns)
    m = extract_re.match(statement.strip())
    if m is None:
        return None

    subject = m.group("subject")
    # ADR-0174 Phase 3 — pronoun-subject statements are no longer
    # rejected outright.  Instead they emit a HELD anchor (with the
    # pronoun in subject_role and ``requires_pronoun_resolution=True``)
    # so the downstream candidate-graph layer can stash them in
    # ``ProblemReadingState.open_hypotheses`` and run the lookback
    # reevaluate pass against the discourse subject map.  When no
    # antecedent resolves, the held hypothesis is dropped (refusal-
    # preferring discipline preserves wrong=0).
    requires_pronoun_resolution = subject.lower() in _REFUSED_SUBJECT_TOKENS

    verb = m.group("verb").lower()
    if verb in _POSSESSION_VERBS:
        anchor_kind = "possession"
    elif verb in _ACQUISITION_VERBS:
        anchor_kind = "acquisition"
    else:
        return None

    count_token = m.group("count")
    if count_token.isdigit():
        count_kind = "integer"
    else:
        # Word-form cardinal — must be a known number word (single or
        # hyphenated compound).  Anything else is unrecognized and the
        # extractor refuses.
        lc = count_token.lower()
        if lc in _NUMBER_WORDS:
            count_kind = "word"
        elif _HYPHEN_CARDINAL_RE.match(lc):
            left, _, right = lc.partition("-")
            if left in _NUMBER_WORDS or right in _NUMBER_WORDS:
                count_kind = "word"
            else:
                return None
        else:
            return None

    # Narrowness #4 — count_kind in observed set.
    if count_kind not in observed_kinds:
        return None

    counted_noun = m.group("noun")
    # Canonicalize counted_noun to the spec's observed casing where
    # available; fall back to literal surface.
    canon = counted_noun
    counted_noun_lc = counted_noun.lower()
    for observed_n in observed_nouns:
        if observed_n.lower() == counted_noun_lc:
            canon = observed_n
            break

    anchor: dict[str, Any] = {
        "kind": "discrete_count",
        "subject_role": subject,
        "count_token": count_token,
        "count_kind": count_kind,
        "counted_noun": canon,
        # ADR-0170 W2 — anchor_kind discriminates the downstream
        # injector path: "possession" → CandidateInitial (existing);
        # "acquisition" → CandidateOperation(add) (new).
        "anchor_kind": anchor_kind,
        "verb_token": verb,
    }
    if requires_pronoun_resolution:
        # ADR-0174 Phase 3 marker — the downstream injector reads this
        # and emits a held CandidateOperation/CandidateInitial whose
        # Hypothesis carries unresolved=("actor_pronoun",).
        anchor["requires_pronoun_resolution"] = True
    return anchor


# ---------------------------------------------------------------------------
# ADR-0174 Phase 3b — compound-clause held hypotheses
# ---------------------------------------------------------------------------

# Markers that defeat compound extraction.  Each indicates a clause
# whose semantics are NOT a pure count of items (multiplicative
# comparison, percent, fraction). Refusal-preferring: if any of these
# appears in the sentence we refuse the compound extraction; the case
# routes to a future phase that handles those shapes.
_COMPOUND_REFUSE_SUBSTRINGS: Final[tuple[str, ...]] = (
    " times ", " times.", " times,",
    " as long", " as many", " as much", " as old",
    " greater than", " less than", " more than", " fewer than",
    " half as ", " twice as ", " thrice ",
    "%", " percent",
    " half of ", " quarter of ", " third of ",
)

# Fraction literal pattern (matched against raw statement, not padded).
_COMPOUND_FRACTION_RE: Final[re.Pattern[str]] = re.compile(r"\b\d+/\d+\b")


def _try_extract_compound_discrete_count_anchors(
    statement: str,
    padded_lower: str,
    spec: Mapping[str, Any],
) -> tuple[Mapping[str, Any], ...] | None:
    """ADR-0174 Phase 3b — emit N anchors for compound-clause sentences.

    Handles ``<Subject> <verb> <count_1> <unit_1>[, <count_2> <unit_2>,
    ..., and <count_k> <unit_k>]`` shapes — pure conjunctive lists of
    discrete counts sharing one subject + one verb. Each anchor
    inherits ``subject_role``, ``verb_token``, ``anchor_kind``, and
    ``requires_pronoun_resolution`` from the head clause.

    Refusal-preferring (wrong=0 doctrine):
      - Returns ``None`` when no conjunctive separator is present
        (sentence is single-anchor or not a list).
      - Returns ``None`` when any multiplicative / percent / fraction
        marker appears (out-of-scope shapes — refuse rather than mis-
        attribute the math).
      - Returns ``None`` when the head clause doesn't match the
        canonical discrete-count regex (no shared subject + verb to
        propagate; refuse rather than guess).
      - Returns ``None`` when the head verb isn't in the closed
        whitelist (verb expansion is separate work).
      - Returns ``None`` when any tail clause fails to ground a
        ``<count> <observed_counted_noun>`` pair (all-or-nothing per
        sentence; admitting partial state would create an incomplete
        graph).
      - Returns ``None`` if only one anchor extracts (the existing
        single-anchor extractor handles that path).

    Cap: bounded by ``HYPOTHESIS_CAP=8``. Sentences exceeding the cap
    refuse rather than truncate (cap is structural, not heuristic).
    """
    # Spec validation
    raw_kinds = spec.get("observed_count_kinds") or ()
    raw_nouns = spec.get("observed_counted_nouns") or ()
    observed_kinds: list[str] = [str(k) for k in raw_kinds]
    observed_nouns: list[str] = [str(n) for n in raw_nouns]
    if not observed_kinds or not observed_nouns:
        return None

    # Must have a conjunctive separator — otherwise this isn't compound
    has_conjunctive = any(
        tok in padded_lower
        for tok in (", and ", " and ", ", ")
    )
    if not has_conjunctive:
        return None

    # Refuse on multiplicative / percent / fraction markers
    s_lc = " " + statement.lower() + " "
    for marker in _COMPOUND_REFUSE_SUBSTRINGS:
        if marker in s_lc:
            return None
    if _COMPOUND_FRACTION_RE.search(statement):
        return None

    # Head match via existing regex — captures subject + verb +
    # first(count, noun). The regex's trailing-content allowance
    # absorbs the rest of the sentence; we re-parse the tail below.
    extract_re = _extract_discrete_count_re_for(observed_nouns)
    head_m = extract_re.match(statement.strip())
    if head_m is None:
        return None  # head doesn't match canonical shape

    subject = head_m.group("subject")
    requires_pronoun_resolution = subject.lower() in _REFUSED_SUBJECT_TOKENS
    verb = head_m.group("verb").lower()
    if verb in _POSSESSION_VERBS:
        anchor_kind: Literal["possession", "acquisition"] = "possession"
    elif verb in _ACQUISITION_VERBS:
        anchor_kind = "acquisition"
    else:
        return None  # head verb not in whitelist — refuse compound

    def _resolve_count_kind(count_token: str) -> str | None:
        if count_token.isdigit():
            return "integer"
        lc = count_token.lower()
        if lc in _NUMBER_WORDS:
            return "word"
        if _HYPHEN_CARDINAL_RE.match(lc):
            left, _, right = lc.partition("-")
            if left in _NUMBER_WORDS or right in _NUMBER_WORDS:
                return "word"
        return None

    def _build_anchor(count_token: str, noun_surface: str) -> Mapping[str, Any] | None:
        count_kind = _resolve_count_kind(count_token)
        if count_kind is None:
            return None
        if count_kind not in observed_kinds:
            return None
        # Canonicalise noun casing to the spec's observed form.
        canon = noun_surface
        nl = noun_surface.lower()
        for observed_n in observed_nouns:
            if observed_n.lower() == nl:
                canon = observed_n
                break
        anchor: dict[str, Any] = {
            "kind": "discrete_count",
            "subject_role": subject,
            "count_token": count_token,
            "count_kind": count_kind,
            "counted_noun": canon,
            "anchor_kind": anchor_kind,
            "verb_token": verb,
        }
        if requires_pronoun_resolution:
            anchor["requires_pronoun_resolution"] = True
        return anchor

    # First anchor — from the head match
    first_anchor = _build_anchor(head_m.group("count"), head_m.group("noun"))
    if first_anchor is None:
        return None
    anchors: list[Mapping[str, Any]] = [first_anchor]

    # Tail: search for additional <count> <observed_noun> pairs in the
    # statement string AFTER the head's noun match. Each tail anchor
    # must independently ground; any failure refuses the whole compound.
    head_end = head_m.end("noun")
    tail = statement.strip()[head_end:].rstrip(".!?")
    noun_alt = "|".join(
        re.escape(n) for n in sorted(observed_nouns, key=len, reverse=True)
    )
    tail_pattern = re.compile(
        r"\b(?P<count>\d+|[A-Za-z\-]+)\s+(?P<noun>" + noun_alt + r")",
        flags=re.IGNORECASE,
    )
    for tm in tail_pattern.finditer(tail):
        tail_anchor = _build_anchor(tm.group("count"), tm.group("noun"))
        if tail_anchor is None:
            return None  # all-or-nothing; preserves wrong=0
        anchors.append(tail_anchor)

    # Wrong=0 hazard defense — all-or-nothing across UNACCOUNTED counts.
    # Without this check, a tail clause like "1 bogusnoun" (where
    # 'bogusnoun' is not in observed_counted_nouns) would silently fail
    # to produce an anchor while leaving the digit '1' unaccounted —
    # admitting partial state. The check: every digit run in the tail
    # must be accounted for by an extracted anchor's count_token. Any
    # unaccounted digit means a clause we didn't ground; refuse the
    # whole compound. Surfaced by 2026-05-28 Phase 3b implementation
    # lookback review.
    tail_digit_count = len(_DIGIT_RUN_RE.findall(tail))
    extracted_tail_count = len(anchors) - 1  # minus the head's anchor
    if tail_digit_count != extracted_tail_count:
        return None

    # Not compound — single-anchor extractor handles this
    if len(anchors) < 2:
        return None

    # HYPOTHESIS_CAP enforcement — refusal-preferring rather than truncate
    from generate.comprehension.state import HYPOTHESIS_CAP
    if len(anchors) > HYPOTHESIS_CAP:
        return None

    return tuple(anchors)


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

    ME-3 (ADR-0169 additive composition) — when
    ``spec["anchor_kind"] == "additive_quantity_composition"`` this
    matcher dispatches to :func:`_try_extract_additive_composition_anchor`
    which publishes ``composition_shape`` + a pre-composed
    :class:`CandidateInitial` in ``parsed_anchors`` for two same-unit
    quantities connected by ``and``. The graph_intent is widened from
    ``"aggregate"`` to also include ``"additive"`` so the dispatcher in
    :func:`match` can recognize composition emissions.
    """
    anchor_kind = spec.get("anchor_kind")
    if anchor_kind == "additive_quantity_composition":
        # ME-3 dispatch — same Literal narrowing keeps the return type
        # consistent ('aggregate' is reused).
        return _try_extract_additive_composition_anchor(statement, spec)
    if anchor_kind == "subtractive_quantity_composition":
        # ME-4 dispatch — subtractive shape returns ("amount" intent).
        sub_result = _try_extract_subtractive_composition_anchor(statement, spec)
        if sub_result is None:
            return None
        anchors, _ = sub_result
        return (anchors, "aggregate")
    if anchor_kind != "multiplicative_aggregate":
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

    # WAVE-A — value-extracting variant. When the spec opts in via
    # ``extract_values: True`` (a separate signal from anchor_kind so
    # existing detection-only specs are unaffected), try to extract
    # the M (outer count) and N (inner count) values from the canonical
    # "<Subject> <verb> <M> <outer-noun>, each <verb> <N> <unit>" shape.
    # On extraction success, emit a pre-composed CandidateInitial with
    # composition_evidence (mirrors the ME-1..ME-4 pattern). The detection-
    # only behaviour is preserved when extract_values is absent or False.
    if spec.get("extract_values"):
        emit = _try_extract_each_weighing_anchor(statement, spec)
        if emit is not None:
            return emit
    return (tuple(), "aggregate")


# ---------------------------------------------------------------------------
# WAVE-A — multiplicative aggregation injector with value extraction.
#
# Targets the canonical "<Subject> <bake-verb> <M> <outer-noun>, each
# <weigh-verb>ing <N> <unit>" shape (case 0047 in the train_sample
# audit). Emits a pre-composed CandidateInitial(value=M*N, unit=unit,
# entity=Subject) with composition_evidence so the wave-A admission
# fires through the same _composed_initial_admissible gate as ME-1..ME-4.
# ---------------------------------------------------------------------------

_MULT_AGG_EACH_WEIGHING_RE: Final[re.Pattern[str]] = re.compile(
    r"""(?ix)
    ^\s*
    (?P<subject>[A-Z][a-zA-Z]+)
    \s+
    (?P<outer_verb>bakes|baked|made|makes|fills|filled|has|had|owns|holds|held|contains|brings|brought|carries|carried|buys|bought)
    \s+
    (?P<count_a>\d+(?:\.\d+)?)
    \s+
    (?P<outer_noun>[a-z][a-zA-Z\-]+(?:\s+[a-z][a-zA-Z\-]+)?)
    \s*,?\s+
    (?:each\s+(?:weighing|holding|containing|costing)|where\s+each\s+(?:bag|basket|box|crate|carton|container|one|item)\s+holds)
    \s+
    (?P<count_b>\d+(?:\.\d+)?)
    \s+
    (?P<unit>[a-z]+)
    \b
    """,
)

_MULT_AGG_SHAPE: Final[str] = "bound(outer_count) × bound(per_outer_count)"


def _try_extract_each_weighing_anchor(
    statement: str, spec: Mapping[str, Any]
) -> tuple[tuple[Mapping[str, Any], ...], Literal["aggregate"]] | None:
    """Extract a pre-composed CandidateInitial for the "each weighing" shape.

    Narrowness:
    - Exactly one match of :data:`_MULT_AGG_EACH_WEIGHING_RE`
    - Subject is a proper noun not in pronoun/determiner sets
    - Outer count + inner count are both positive numerics
    - Inner unit is in ``spec["observed_units"]`` (or its singular form)
    - Outer verb in the canonical whitelist (mapped via matched_anchor)

    Refuses on any failure; refusal-preferring.
    """
    observed_units = set(spec.get("observed_units") or ())
    if not observed_units:
        return None

    matches = list(_MULT_AGG_EACH_WEIGHING_RE.finditer(statement))
    if len(matches) != 1:
        return None

    m = matches[0]
    subject = m.group("subject")
    if subject.lower() in _REFUSED_SUBJECT_TOKENS:
        return None
    if subject.lower() in _COMMON_DETERMINERS_AT_HEAD:
        return None

    count_a_token = m.group("count_a")
    count_b_token = m.group("count_b")
    try:
        count_a = float(count_a_token)
        count_b = float(count_b_token)
    except ValueError:
        return None
    if count_a <= 0 or count_b <= 0:
        return None

    unit = m.group("unit").lower()
    if unit not in observed_units and unit.rstrip("s") not in observed_units:
        return None

    composed_value_f = count_a * count_b
    composed_value: int | float
    if (
        composed_value_f.is_integer()
        and "." not in count_a_token
        and "." not in count_b_token
    ):
        composed_value = int(composed_value_f)
    else:
        composed_value = composed_value_f

    from generate.math_candidate_parser import CandidateInitial
    from generate.math_problem_graph import InitialPossession, Quantity

    # matched_anchor must be in CandidateInitial post-init whitelist.
    outer_verb = m.group("outer_verb").lower()
    matched_anchor = outer_verb if outer_verb in {
        "has", "had", "made", "makes", "buys", "bought", "paid", "earned", "saved", "got", "received"
    } else "had"

    composed_initial = CandidateInitial(
        initial=InitialPossession(
            entity=subject,
            quantity=Quantity(value=composed_value, unit=unit),
        ),
        source_span=m.group(0),
        matched_anchor=matched_anchor,
        matched_value_token=str(composed_value),
        matched_unit_token=unit,
        matched_entity_token=subject,
        composition_evidence={
            "composition_shape": _MULT_AGG_SHAPE,
            "input_tokens": f"{count_a_token}|{count_b_token}",
            "entity_source": "same_sentence",
        },
        # ADR-0191 completeness provenance.  This is an aggregating initial:
        # its derived value (count_a × count_b) collapses TWO source tokens
        # into one quantity.  Without recording them, the completeness guard
        # (generate/math_completeness.py) sees required={count_a, count_b}
        # but consumed={composed_value} and refuses every WAVE-A reading as
        # "incomplete" — a silent regression of the WAVE-A capability that
        # predates the guard.  Expose both consumed tokens so the guard can
        # confirm no source quantity was dropped.  wrong==0 is preserved:
        # these tokens genuinely ARE the multiplicands of the emitted value.
        consumed_value_tokens=(count_a_token, count_b_token),
    )

    anchor: Mapping[str, Any] = {
        "kind": "multiplicative_aggregate_each_weighing",
        "composition_shape": _MULT_AGG_SHAPE,
        "composed_initial": composed_initial,
        "count_a": count_a_token,
        "count_b": count_b_token,
        "unit": unit,
        "subject": subject,
        "outer_verb": outer_verb,
    }
    return ((anchor,), "aggregate")


# ---------------------------------------------------------------------------
# ME-3 — additive composition matcher.
#
# Admits "<count_a> <unit> and <count_b> <unit>" shape (same unit) and
# emits a pre-composed CandidateInitial whose value is the sum.
#
# Subject-binding discipline:
# - SAME-SENTENCE proper-noun subject preferred (Option A from ME-1).
# - When absent, the caller MAY supply ``prior_subject`` via the match()
#   dispatcher (ME-2 path); the ME-3 helper does NOT itself consult
#   ``prior_subject`` — that path is reserved for the cross-sentence
#   composition extension (a future ME-3b if needed). v1 ME-3 narrowness
#   matches the dispatch pack: refuse on subject-absent.
# - Pronoun subject refused (mirrors existing _REFUSED_SUBJECT_TOKENS).
# ---------------------------------------------------------------------------

_ADDITIVE_TWO_QUANTITY_RE: Final[re.Pattern[str]] = re.compile(
    r"""(?ix)
    ^\s*
    (?P<subject>[A-Z][a-zA-Z]+)
    \s+
    (?P<verb>lost|gained|earned|saved|made|paid|spent|bought|sold|added|removed|received)
    \s+
    (?P<count_a>\d+(?:\.\d+)?)
    \s+
    (?P<unit_a>[a-z]+)
    (?:\s+[a-z]+\s+[a-z]+)?           # optional time/location phrase like "in March"
    \s+and\s+
    (?P<count_b>\d+(?:\.\d+)?)
    \s+
    (?P<unit_b>[a-z]+)
    (?:\s+[a-z]+\s+[a-z]+)?           # optional second time/location phrase
    \b
    """,
)

_ADDITIVE_COMPOSITION_SHAPE: Final[str] = "bound(qty_a) + bound(qty_b)"


def _try_extract_additive_composition_anchor(
    statement: str, spec: Mapping[str, Any]
) -> tuple[tuple[Mapping[str, Any], ...], Literal["aggregate"]] | None:
    """Extract a pre-composed CandidateInitial for additive composition.

    Narrowness layers (all required):

    1. ``spec["anchor_kind"] == "additive_quantity_composition"`` (caller)
    2. ``spec["observed_units"]`` is non-empty
    3. Exactly one match of :data:`_ADDITIVE_TWO_QUANTITY_RE`
    4. ``unit_a == unit_b`` (same-unit composition only; cross-unit
       addition is ill-defined without a conversion table — refuse)
    5. Both unit tokens in ``observed_units``
    6. Both counts are positive
    7. Subject is a proper noun not in :data:`_REFUSED_SUBJECT_TOKENS`
    8. Verb in :data:`_ADDITIVE_COMPOSITION_VERBS`

    Refuses on any failure; refusal-preferring discipline.
    """
    if spec.get("anchor_kind") != "additive_quantity_composition":
        return None
    observed_units = set(spec.get("observed_units") or ())
    if not observed_units:
        return None

    matches = list(_ADDITIVE_TWO_QUANTITY_RE.finditer(statement))
    if len(matches) != 1:
        return None

    m = matches[0]
    subject = m.group("subject")
    if subject.lower() in _REFUSED_SUBJECT_TOKENS:
        return None
    if subject.lower() in _COMMON_DETERMINERS_AT_HEAD:
        return None

    verb = m.group("verb").lower()
    if verb not in _ADDITIVE_COMPOSITION_VERBS:
        return None

    unit_a = m.group("unit_a").lower()
    unit_b = m.group("unit_b").lower()
    # Strip trailing 's' for plural normalization on the comparison
    # (apples vs apple). Refuse on stem mismatch.
    if unit_a.rstrip("s") != unit_b.rstrip("s"):
        return None
    canonical_unit = unit_a
    if canonical_unit not in observed_units and canonical_unit.rstrip("s") not in observed_units:
        return None

    count_a_token = m.group("count_a")
    count_b_token = m.group("count_b")
    try:
        count_a = float(count_a_token)
        count_b = float(count_b_token)
    except ValueError:
        return None
    if count_a <= 0 or count_b <= 0:
        return None

    composed_value_f = count_a + count_b
    if composed_value_f != composed_value_f:  # NaN guard
        return None
    composed_value: int | float
    if (
        composed_value_f.is_integer()
        and "." not in count_a_token
        and "." not in count_b_token
    ):
        composed_value = int(composed_value_f)
    else:
        composed_value = composed_value_f

    from generate.math_candidate_parser import CandidateInitial
    from generate.math_problem_graph import InitialPossession, Quantity

    # Verb whitelist maps to a CandidateInitial.matched_anchor value
    # the post-init guard accepts (existing whitelist includes
    # has/have/had/saved/earned/got/received/bought/made/paid).
    matched_anchor = verb if verb in {
        "saved", "earned", "got", "received", "bought", "made", "paid"
    } else "had"

    composed_initial = CandidateInitial(
        initial=InitialPossession(
            entity=subject,
            quantity=Quantity(value=composed_value, unit=canonical_unit),
        ),
        source_span=m.group(0),
        matched_anchor=matched_anchor,
        matched_value_token=str(composed_value),
        matched_unit_token=canonical_unit,
        matched_entity_token=subject,
        composition_evidence={
            "composition_shape": _ADDITIVE_COMPOSITION_SHAPE,
            "input_tokens": f"{count_a_token}|{count_b_token}",
            "entity_source": "same_sentence",
        },
    )

    anchor: Mapping[str, Any] = {
        "kind": "additive_quantity_composition",
        "composition_shape": _ADDITIVE_COMPOSITION_SHAPE,
        "composed_initial": composed_initial,
        "count_a": count_a_token,
        "count_b": count_b_token,
        "unit": canonical_unit,
        "subject": subject,
        "verb": verb,
    }
    return ((anchor,), "aggregate")


_ADDITIVE_COMPOSITION_VERBS: Final[frozenset[str]] = frozenset({
    "lost", "gained", "earned", "saved", "made", "paid", "spent",
    "bought", "sold", "added", "removed", "received",
})


# ---------------------------------------------------------------------------
# ME-4 — subtractive composition matcher.
#
# Admits "<Subject> <init-verb> <N> <unit>(,| then|; etc.) <sub-verb>
# <M> <unit>" (same unit; positive initial verb followed by removal
# verb) and emits a pre-composed CandidateInitial(N - M, unit).
#
# Refusal-preferring discipline: count_b >= count_a → refuse
# (non-negative remainder; subtractive composition that goes below
# zero is a wrong>0 hazard).
# ---------------------------------------------------------------------------

_SUBTRACTIVE_TWO_QUANTITY_RE: Final[re.Pattern[str]] = re.compile(
    r"""(?ix)
    ^\s*
    (?P<subject>[A-Z][a-zA-Z]+)
    \s+
    (?P<verb_a>had|has|got|owns|owned|earned|saved|made|received|bought)
    \s+
    (?P<count_a>\d+(?:\.\d+)?)
    \s+
    (?P<unit_a>[a-z]+)
    \s*
    (?:,|\sthen\s|;|\s+and\s+then\s+|\s+then\s+|\s+and\s+)
    \s*
    (?:then\s+)?
    (?P<verb_b>lost|spent|gave|donated|paid|removed|sold|used|consumed)
    (?:\s+away)?
    \s+
    (?P<count_b>\d+(?:\.\d+)?)
    \s+
    (?P<unit_b>[a-z]+)
    \b
    """,
)

_SUBTRACTIVE_COMPOSITION_SHAPE: Final[str] = "bound(initial) − bound(removed)"


_SUBTRACTIVE_INITIAL_VERBS: Final[frozenset[str]] = frozenset({
    "had", "has", "got", "owns", "owned", "earned", "saved",
    "made", "received", "bought",
})

_SUBTRACTIVE_REMOVAL_VERBS: Final[frozenset[str]] = frozenset({
    "lost", "spent", "gave", "donated", "paid", "removed",
    "sold", "used", "consumed",
})


def _try_extract_subtractive_composition_anchor(
    statement: str, spec: Mapping[str, Any]
) -> tuple[tuple[Mapping[str, Any], ...], Literal["amount"]] | None:
    """Extract a pre-composed CandidateInitial for subtractive composition.

    See module docstring above for narrowness layers. ``count_b >=
    count_a`` refuses (non-negative remainder discipline; wrong>0
    hazard).
    """
    if spec.get("anchor_kind") != "subtractive_quantity_composition":
        return None
    observed_units = set(spec.get("observed_units") or ())
    if not observed_units:
        return None

    matches = list(_SUBTRACTIVE_TWO_QUANTITY_RE.finditer(statement))
    if len(matches) != 1:
        return None

    m = matches[0]
    subject = m.group("subject")
    if subject.lower() in _REFUSED_SUBJECT_TOKENS:
        return None
    if subject.lower() in _COMMON_DETERMINERS_AT_HEAD:
        return None

    verb_a = m.group("verb_a").lower()
    verb_b = m.group("verb_b").lower()
    if verb_a not in _SUBTRACTIVE_INITIAL_VERBS:
        return None
    if verb_b not in _SUBTRACTIVE_REMOVAL_VERBS:
        return None

    unit_a = m.group("unit_a").lower()
    unit_b = m.group("unit_b").lower()
    if unit_a.rstrip("s") != unit_b.rstrip("s"):
        return None
    canonical_unit = unit_a
    if (
        canonical_unit not in observed_units
        and canonical_unit.rstrip("s") not in observed_units
    ):
        return None

    count_a_token = m.group("count_a")
    count_b_token = m.group("count_b")
    try:
        count_a = float(count_a_token)
        count_b = float(count_b_token)
    except ValueError:
        return None
    if count_a <= 0 or count_b <= 0:
        return None
    if count_b >= count_a:
        return None  # Non-negative remainder; wrong>0 hazard.

    composed_value_f = count_a - count_b
    composed_value: int | float
    if (
        composed_value_f.is_integer()
        and "." not in count_a_token
        and "." not in count_b_token
    ):
        composed_value = int(composed_value_f)
    else:
        composed_value = composed_value_f

    from generate.math_candidate_parser import CandidateInitial
    from generate.math_problem_graph import InitialPossession, Quantity

    matched_anchor = verb_a if verb_a in {
        "has", "had", "saved", "earned", "got", "received", "bought", "made", "paid",
    } else "had"

    composed_initial = CandidateInitial(
        initial=InitialPossession(
            entity=subject,
            quantity=Quantity(value=composed_value, unit=canonical_unit),
        ),
        source_span=m.group(0),
        matched_anchor=matched_anchor,
        matched_value_token=str(composed_value),
        matched_unit_token=canonical_unit,
        matched_entity_token=subject,
        composition_evidence={
            "composition_shape": _SUBTRACTIVE_COMPOSITION_SHAPE,
            "input_tokens": f"{count_a_token}|{count_b_token}",
            "entity_source": "same_sentence",
        },
    )

    anchor: Mapping[str, Any] = {
        "kind": "subtractive_quantity_composition",
        "composition_shape": _SUBTRACTIVE_COMPOSITION_SHAPE,
        "composed_initial": composed_initial,
        "count_a": count_a_token,
        "count_b": count_b_token,
        "unit": canonical_unit,
        "subject": subject,
        "initial_verb": verb_a,
        "removal_verb": verb_b,
    }
    return ((anchor,), "amount")


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
    *,
    prior_subject: str | None = None,
) -> RecognizerMatch | None:
    """First-match-wins over *registry*.

    Pure: same ``(statement, registry, prior_subject)`` → same result,
    byte-identical. Order is registry order (the projection step in
    :mod:`generate.recognizer_registry` sorts by ``(review_date,
    proposal_id)``).

    ME-2 (cross-sentence subject binding) — when the per-category
    matcher returns ``None`` for a ``RATE_WITH_CURRENCY`` recognizer
    AND ``prior_subject`` is supplied, this dispatcher additionally
    tries
    :func:`try_extract_cross_sentence_composition_anchor`. Admitting
    the case 0019 sentence shape requires both:

    - a ratified recognizer carrying
      ``anchor_kind = "currency_per_unit_composition"``
    - a non-empty ``prior_subject`` resolved from upstream sentences

    Refusal-preferring discipline is preserved: ``prior_subject=None``
    + same-sentence Option A regex miss → returns ``None``.
    """
    if not isinstance(statement, str) or not statement.strip():
        return None
    for recognizer in registry:
        matcher = _MATCHERS.get(recognizer.shape_category)
        if matcher is None:
            continue
        result = matcher(statement, recognizer.canonical_pattern)
        if result is None:
            if (
                recognizer.shape_category is ShapeCategory.RATE_WITH_CURRENCY
                and recognizer.canonical_pattern.get("anchor_kind")
                == "currency_per_unit_composition"
                and prior_subject is not None
            ):
                cross_result = try_extract_cross_sentence_composition_anchor(
                    statement, recognizer.canonical_pattern, prior_subject
                )
                if cross_result is None:
                    continue
                parsed_anchors, graph_intent = cross_result
                return RecognizerMatch(
                    recognizer=recognizer,
                    category=recognizer.shape_category,
                    outcome="admissible",
                    graph_intent=graph_intent,
                    parsed_anchors=parsed_anchors,
                )
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


# ---------------------------------------------------------------------------
# Cross-sentence subject resolution helper (ME-2).
# ---------------------------------------------------------------------------

_PROPER_NOUN_SUBJECT_RE: Final[re.Pattern[str]] = re.compile(
    r"^\s*([A-Z][a-zA-Z]+)\b"
)


_COMMON_DETERMINERS_AT_HEAD: Final[frozenset[str]] = frozenset(
    {
        # Articles + demonstratives
        "the", "a", "an", "this", "that", "these", "those",
        # Possessives
        "his", "her", "their", "its", "my", "your", "our",
        # Sentence-initial connectors / prepositions that get capitalized
        "after", "before", "when", "while", "if", "then", "so", "but",
        "and", "or", "during", "since", "until", "though", "although",
        "however", "moreover", "additionally", "first", "next", "later",
        "finally", "now", "soon", "today", "tomorrow", "yesterday",
        "every", "all", "some", "many", "each", "another", "other",
        "in", "on", "at", "by", "for", "from", "with", "without",
        "how", "why", "what", "where", "who", "when",
    }
)


def extract_proper_noun_subject(statement: str) -> str | None:
    """Return the head proper-noun subject of *statement*, or None.

    Used by callers (e.g. ``generate.math_candidate_graph``) to track a
    running ``prior_subject`` across sentences for cross-sentence
    composition binding (ME-2).

    Heuristic narrowness:

    - The head token must match ``[A-Z][a-zA-Z]+``.
    - The lowercased head must NOT be in :data:`_REFUSED_SUBJECT_TOKENS`
      (existing pronoun set) or
      :data:`_COMMON_DETERMINERS_AT_HEAD` (articles + demonstratives +
      possessives that get capitalized at sentence start but are not
      proper nouns).

    Refuses on any ambiguity. The caller is expected to update the
    running ``prior_subject`` only when this returns a non-None value.
    """
    if not isinstance(statement, str):
        return None
    m = _PROPER_NOUN_SUBJECT_RE.match(statement)
    if m is None:
        return None
    cand = m.group(1)
    lc = cand.lower()
    if lc in _REFUSED_SUBJECT_TOKENS:
        return None
    if lc in _COMMON_DETERMINERS_AT_HEAD:
        return None
    return cand


__all__ = [
    "RecognizerMatch",
    "match",
    "extract_proper_noun_subject",
    "try_extract_cross_sentence_composition_anchor",
]
