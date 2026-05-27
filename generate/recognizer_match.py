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

    # Narrowness #1 + #5 — shape + counted-noun lemma.
    extract_re = _extract_discrete_count_re_for(observed_nouns)
    m = extract_re.match(statement.strip())
    if m is None:
        return None

    subject = m.group("subject")
    if subject.lower() in _REFUSED_SUBJECT_TOKENS:
        return None

    verb = m.group("verb").lower()
    if verb not in _POSSESSION_VERBS:
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

    return {
        "kind": "discrete_count",
        "subject_role": subject,
        "count_token": count_token,
        "count_kind": count_kind,
        "counted_noun": canon,
    }


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
