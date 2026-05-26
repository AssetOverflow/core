"""ADR-0163 Phase A — refusal-shape taxonomy.

Deterministic, rules-only categorizer that maps a refused GSM8K statement
to a single ``ShapeCategory``.

Doctrine (non-negotiable):
- No LLM call, no embedding, no learned classifier.  The categorizer is a
  pure function of its input string; the same input always returns the same
  output, and the function has no side effects, no I/O, no global state.
- No hidden normalization.  Comparisons are lower-cased and padded with
  spaces for word-boundary safety; the original statement is never mutated
  for downstream consumers.
- First-match-wins.  Priority order is fixed at module level; a statement
  belongs to exactly one category.
- UNCATEGORIZED is a first-class outcome.  It is honest measurement, not
  a failure.  Phase A's purpose is to surface the histogram, including the
  uncategorized tail; the operator selects what Phase B addresses.

Adding a new category requires ≥ 3 refused statements as evidence, cited
inline.  ADR-0163 §Risks enforces this.

Phase B round 2 extension
~~~~~~~~~~~~~~~~~~~~~~~~~
Three new categories surfaced from categorizing the post-#304 GSM8K
train_sample's still-refused 47 set: ``CURRENCY_AMOUNT``,
``MULTIPLICATIVE_AGGREGATION``, and ``DISCRETE_COUNT_STATEMENT``.  Each is
inserted into the dispatch order *after* the existing more-specific
categories so that statements matching both (e.g. currency + per-unit
rate framing) still resolve to the more-specific existing category.
"""

from __future__ import annotations

import re
from enum import Enum


class ShapeCategory(str, Enum):
    """Disjoint shape categories surfaced from the GSM8K train-sample report.

    The non-``UNCATEGORIZED`` values are the baseline set named in
    ADR-0163 §Phase A plus the round-2 extensions; every value listed
    here has a rule below, and if no rule fires ``UNCATEGORIZED`` is
    returned.
    """

    RATE_WITH_CURRENCY = "rate_with_currency"
    UNIT_PARTITION = "unit_partition"
    DESCRIPTIVE_SETUP_NO_QUANTITY = "descriptive_setup_no_quantity"
    INDEFINITE_QUANTITY = "indefinite_quantity"
    FRACTIONAL_RATE_OF_CHANGE = "fractional_rate_of_change"
    COMPARATIVE_WITH_UNIT = "comparative_with_unit"
    NESTED_QUESTION_TARGET = "nested_question_target"
    TEMPORAL_AGGREGATION = "temporal_aggregation"
    CONDITIONAL_QUANTITY = "conditional_quantity"
    CURRENCY_AMOUNT = "currency_amount"
    MULTIPLICATIVE_AGGREGATION = "multiplicative_aggregation"
    DISCRETE_COUNT_STATEMENT = "discrete_count_statement"
    UNCATEGORIZED = "uncategorized"


# ---------------------------------------------------------------------------
# Lexical primitives — small, named sets the rules below compose from.
# ---------------------------------------------------------------------------

_DIGIT_RE = re.compile(r"\d")

# Word-form numerals 1..20 plus tens, scale words, common fraction words, and
# "dozen".  Used only to decide "does the statement contain any quantity at
# all".  Detecting an exact value is out of scope here.
_NUMBER_WORDS: frozenset[str] = frozenset({
    "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
    "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen",
    "seventeen", "eighteen", "nineteen", "twenty", "thirty", "forty", "fifty",
    "sixty", "seventy", "eighty", "ninety",
    "hundred", "thousand", "million", "billion",
    "half", "halves", "third", "thirds", "quarter", "quarters",
    "fourth", "fourths", "fifth", "fifths", "sixth", "sixths",
    "dozen", "dozens",
})

# Subset of NUMBER_WORDS that are *integer* count words — used by the
# discrete-count and multiplicative rules so a bare fraction word
# ("half", "third") does not misroute to "discrete count of half things".
_COUNT_NUMBER_WORDS: frozenset[str] = _NUMBER_WORDS - {
    "half", "halves", "third", "thirds", "quarter", "quarters",
    "fourth", "fourths", "fifth", "fifths", "sixth", "sixths",
}
_COUNT_NUMBER_WORDS_RE_SRC = "|".join(sorted(_COUNT_NUMBER_WORDS))

# Indefinite quantifiers — "amount unspecified" signals.
_INDEFINITE_TOKENS: tuple[str, ...] = (
    " some ", " several ", " a few ", " many ", " any ",
)

# Change-of-state verbs that combine with a fraction/percent to mean
# "fractional rate of change".  Limited to high-signal lemmas.
_CHANGE_VERBS: tuple[str, ...] = (
    "decrease", "decreased", "decreases", "decreasing",
    "increase", "increased", "increases", "increasing",
    "lose", "loses", "lost", "losing",
    "gain", "gained", "gains", "gaining",
    "drop", "drops", "dropped", "dropping",
    "reduce", "reduced", "reduces", "reducing",
    "eat", "eats", "eaten", "ate", "eating",
    "shrink", "shrinks", "shrank", "shrunk", "shrinking",
    "grow", "grows", "grew", "grown", "growing",
)

# Fraction-or-percentage signal.  "%" symbol, ``digit/digit`` pattern, or
# fraction words.
_PERCENT_OR_FRACTION_RE = re.compile(r"%|\b\d+\s*/\s*\d+\b")
_FRACTION_WORDS: tuple[str, ...] = (
    " half ", " halves ", " quarter ", " quarters ",
    " third ", " thirds ", " fourth ", " fifth ",
)

# Comparative markers.  Each is a substring on the padded lower-case form.
_COMPARATIVE_TOKENS: tuple[str, ...] = (
    " more than ", " less than ",
    " twice as ", " twice the ",
    " as much as ", " as many as ", " as long as ",
    " times her ", " times his ", " times their ", " times the ",
)
# Pattern for "N times" where N is a digit — covers "7 times her age".
_DIGIT_TIMES_RE = re.compile(r"\b\d+(?:\.\d+)?\s+times\b")

# Currency + rate signal.  A "$" alone is not a rate; the statement must
# also carry a per-unit framing.
_CURRENCY_RE = re.compile(r"[\$£€¥]")
_RATE_PER_UNIT_TOKENS: tuple[str, ...] = (
    " per ", " an hour", " a hour", " a day", " a week", " a month", " a year",
    "/hour", "/day", "/week", "/month", "/year", "/kg", "/lb",
    " for one ", " for each ", " for a ", " for every ",
)

# Hyphenated unit partition — e.g. "25-foot sections".  Pattern stays small.
_HYPHENATED_UNIT_RE = re.compile(
    r"\b\d+(?:\.\d+)?-(?:foot|feet|inch|inches|mile|miles|meter|meters|"
    r"yard|yards|pound|pounds|ounce|ounces|hour|hours|minute|minutes|"
    r"second|seconds|gram|grams|kg|liter|liters|gallon|gallons)\b"
)
# Temporal aggregation cues.  Repeated/aggregated time, not incidental "old".
_TEMPORAL_TOKENS: tuple[str, ...] = (
    " each day", " each week", " each month", " each year", " each hour",
    " each minute", " each second",
    " every day", " every week", " every month", " every year",
    " every hour", " every minute", " every other ",
    " per day", " per week", " per month", " per year", " per hour",
    " per minute", " per second",
    " daily", " weekly", " monthly", " yearly", " hourly",
)
_TEMPORAL_WINDOW_RE = re.compile(
    r"\b(?:over|for|in|within)\s+\d+(?:\.\d+)?\s+"
    r"(?:second|seconds|minute|minutes|hour|hours|day|days|week|weeks|"
    r"month|months|year|years)\b"
)
_DAY_NAMES: tuple[str, ...] = (
    " monday", " tuesday", " wednesday", " thursday", " friday",
    " saturday", " sunday",
)

# Nested question + conditional: "If X, how many/much Y ...?".
_NESTED_QUESTION_RE = re.compile(
    r"^\s*if\b.+?\bhow\s+(?:many|much|long|far|old|tall)\b.*\?\s*$",
    re.IGNORECASE | re.DOTALL,
)
# Bare conditional — "If X, would/will Y" — without a how-target.
_CONDITIONAL_RE = re.compile(
    r"^\s*if\b.+?\b(?:would|will|could|then|gets?|has|have)\b",
    re.IGNORECASE | re.DOTALL,
)

# --- Round-2 extension primitives ------------------------------------------

# Container nouns whose presence with a count + ("of"|"with"|...) signals
# multiplicative aggregation ("N <container> of <thing>" or
# "N <container> with N <thing>").  Kept tight so a bare "house" or
# "room" doesn't promote unrelated counts.
_CONTAINER_NOUNS: tuple[str, ...] = (
    "bag", "bags", "basket", "baskets", "box", "boxes",
    "case", "cases", "crate", "crates", "carton", "cartons",
    "package", "packages", "bundle", "bundles", "set", "sets",
    "pack", "packs", "tray", "trays", "jar", "jars",
    "bottle", "bottles", "bin", "bins", "shelf", "shelves",
    "pallet", "pallets", "container", "containers",
)
_CONTAINER_NOUNS_RE_SRC = "|".join(_CONTAINER_NOUNS)

# "<integer-or-word> <container_noun> (with|of|holding|containing|having)"
# Allow up to two adjective words between the count and the container noun
# ("five full boxes of crayons" → "five full boxes of").
_MULTIPLICATIVE_CONTAINER_RE = re.compile(
    r"\b(?:\d+(?:,\d{3})*|" + _COUNT_NUMBER_WORDS_RE_SRC + r")\s+"
    r"(?:\w+\s+){0,2}"
    r"(?:" + _CONTAINER_NOUNS_RE_SRC + r")\s+"
    r"(?:of|with|holding|containing|having)\b",
    re.IGNORECASE,
)
# "each ... <integer-or-word>" within a ~4-word window.  Catches
# "each weighing 5 ounces", "each basket holds 50", "each contain six".
_MULTIPLICATIVE_EACH_RE = re.compile(
    r"\beach\s+(?:\w+\s+){0,4}(?:\d+|" + _COUNT_NUMBER_WORDS_RE_SRC + r")\b",
    re.IGNORECASE,
)

# Discrete-count noun pair: a digit (optionally comma-grouped) immediately
# followed by a counted noun, OR an integer number-word immediately
# followed by a counted noun.  The "immediately" matters: "10% simple"
# is *not* a digit+noun pair because "%" intervenes, so it stays
# UNCATEGORIZED (an honest residual).
_DISCRETE_COUNT_DIGIT_NOUN_RE = re.compile(
    r"\b\d+(?:,\d{3})*\s+[A-Za-z][A-Za-z\-]*\b"
)
_DISCRETE_COUNT_WORD_NOUN_RE = re.compile(
    r"\b(?:" + _COUNT_NUMBER_WORDS_RE_SRC + r")\s+[A-Za-z][A-Za-z\-]*\b",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Helpers — pure string predicates.
# ---------------------------------------------------------------------------


def _padded_lower(statement: str) -> str:
    """Return a lower-case form padded with spaces for substring word matching.

    Padding lets ``" some "`` reliably miss inside ``"somewhere"``.
    """

    return " " + statement.lower().replace("\n", " ") + " "


def _has_any_substring(haystack: str, needles: tuple[str, ...]) -> bool:
    return any(needle in haystack for needle in needles)


def _has_number_word(padded_lower: str) -> bool:
    # Walk word boundaries cheaply by splitting on whitespace and stripping
    # surrounding punctuation.  This stays string-only.
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
    if _has_any_substring(padded_lower, _INDEFINITE_TOKENS):
        return True
    return False


# ---------------------------------------------------------------------------
# Rule predicates — one per category.  Each is independent and pure.
# ---------------------------------------------------------------------------


def _is_nested_question_target(statement: str) -> bool:
    """Conditional question whose target is a ``how`` quantity.

    Baseline category — ADR-0163 §Phase A names this shape explicitly.
    The 50-case sample carries two instances (case 0009, case 0042); the
    rule is retained as a reserve for the public/holdout splits where the
    shape is expected to be more frequent.  Alternative chosen over
    splitting into separate "question" vs "conditional" categories: every
    observed nested-question case in the 50-sample is also conditional,
    so collapsing them is honest.
    """

    return _NESTED_QUESTION_RE.match(statement) is not None


def _is_conditional_quantity(statement: str) -> bool:
    """Conditional setup without a nested ``how``-target.

    Examples surfaced as candidates:
    - case 0009 (also matches nested) — handled by ordering
    - case 0042 (also matches nested) — handled by ordering
    - reserve slot: ADR-0163 §Phase A names this category explicitly with
      "if she had 2 more, she would have…" as the template.  No bare
      conditional appears in the 50-sample (every conditional was also
      a nested question), so this rule is conservative and may return
      ``False`` for the entire current corpus.  That is the honest
      outcome; the category is retained because the ADR commits to it.
    """

    return _CONDITIONAL_RE.match(statement) is not None


def _is_unit_partition(padded_lower: str) -> bool:
    """Partition into unit-bearing pieces.

    Baseline category — ADR-0163 §Phase A names this shape explicitly
    ("She splits it up into 25-foot sections").  The 50-case sample
    carries one instance (case 0002); the rule is retained as a reserve
    for the public/holdout splits where partition-into-unit-pieces is
    expected to be more frequent.  Alternative considered: also fold any
    "split/divide/cut ... into N pieces" without a unit.  Rejected —
    that shape is "enumeration", not "unit partition", and Phase B's
    exemplars should treat them separately.
    """

    if _HYPHENATED_UNIT_RE.search(padded_lower):
        return True
    return False


def _is_rate_with_currency(padded_lower: str) -> bool:
    """Currency + per-unit framing.

    Examples (≥ 3 cites):
    - case 0001 "Tina makes $18.00 an hour."
    - case 0011 "Alexa ... sells lemonade for $2 for one cup."
    - case 0022 "earning $20 per kg of fish."
    """

    if not _CURRENCY_RE.search(padded_lower):
        return False
    return _has_any_substring(padded_lower, _RATE_PER_UNIT_TOKENS)


def _is_currency_amount(padded_lower: str) -> bool:
    """Currency symbol without a per-unit framing — a bare amount.

    Dispatched AFTER ``_is_rate_with_currency`` so any "$N per X"
    statement is already claimed; what reaches this predicate is a
    currency mention without rate framing.

    Examples (≥ 3 cites, drawn from the post-#304 still-refused 47
    GSM8K train_sample set):
    - case 0019 "The dog ends up having health problems and this
      requires 3 vet appointments, which cost $400 each."
    - case 0026 "Aaron and his brother Carson each saved up $40
      to go to dinner."
    - case 0028 "It cost $100,000 to open initially."

    Alternative considered: only fire when a currency-bearing token is
    paired with a verb of payment ("cost", "paid", "owes").
    Rejected — the bare currency presence is the load-bearing signal,
    and the rate-with-currency rule already claims any per-unit form
    above this dispatch slot, so widening the verb whitelist would
    only add false negatives (e.g., "the donation jar collected
    $87.50 at the festival" should still admit).
    """

    return bool(_CURRENCY_RE.search(padded_lower))


def _is_comparative_with_unit(padded_lower: str) -> bool:
    """Comparative quantity phrases.

    Examples (≥ 3 cites):
    - case 0015 "rides for twice as much time as the subway ride"
    - case 0016 "2 more than 5 miles ... 3 less than 17 stop signs"
    - case 0033 "her grandfather is 7 times her age"
    """

    if _has_any_substring(padded_lower, _COMPARATIVE_TOKENS):
        return True
    if _DIGIT_TIMES_RE.search(padded_lower):
        return True
    return False


def _is_fractional_rate_of_change(padded_lower: str) -> bool:
    """Fraction or percentage paired with a change-of-state verb.

    Examples (≥ 3 cites):
    - case 0005 "decrease to 3/4 of its temperature"
    - case 0012 "his fish ate half of them"
    - case 0041 "guests eat all of 1 pan, and 75% of the 2nd pan"
    Alternative considered: include bare "10% simple interest" (case 0044).
    Rejected — there is no change verb, so the shape is a percentage-rate,
    not a percentage-change.  That case falls to UNCATEGORIZED honestly.
    """

    has_fraction = bool(_PERCENT_OR_FRACTION_RE.search(padded_lower)) or \
        _has_any_substring(padded_lower, _FRACTION_WORDS)
    if not has_fraction:
        return False
    return any(f" {verb} " in padded_lower for verb in _CHANGE_VERBS)


def _is_temporal_aggregation(padded_lower: str) -> bool:
    """Repeated / aggregated time framing with a quantity.

    Examples (≥ 3 cites):
    - case 0013 "uploads 10 one-hour videos ... each day"
    - case 0014 "Bob can shuck 10 oysters in 5 minutes"
    - case 0024 "20 jumping jacks on Monday, 36 on Tuesday ..."
    - case 0050 "every other day for 2 weeks"
    Alternative considered: split "in N minutes" (rate) from "each day"
    (aggregation).  Rejected for parsimony — both demand the same shape
    treatment from the candidate-graph (event repetition over a time axis).
    """

    if _has_any_substring(padded_lower, _TEMPORAL_TOKENS):
        return True
    if _TEMPORAL_WINDOW_RE.search(padded_lower):
        return True
    # Day-of-week enumeration: require at least two day names to avoid
    # incidental "on Monday" one-offs.
    day_hits = sum(1 for d in _DAY_NAMES if d in padded_lower)
    if day_hits >= 2:
        return True
    return False


def _is_indefinite_quantity(padded_lower: str) -> bool:
    """Indefinite quantifier present without a specific count.

    Examples (≥ 3 cites):
    - case 0004 "There are some kids in camp."
    - case 0040 "Over several years, Daniel has adopted any stray animals"
    - case 0043 "Sandra wants to buy some sweets."
    Alternative considered: route case 0040 to TEMPORAL_AGGREGATION because
    of "Over several years".  Rejected — the load-bearing shape problem is
    the unbounded quantifier ("any stray animals"), not the time window.
    Ordering reflects that.
    """

    return _has_any_substring(padded_lower, _INDEFINITE_TOKENS)


def _is_multiplicative_aggregation(padded_lower: str) -> bool:
    """N outer-units each carrying M inner-units — spatial / per-container.

    Two surface forms compose: (a) ``N <container> of/with/holding/...
    <something>`` and (b) ``each <verb> <count>`` within a short window.
    Either form is sufficient.

    Examples (≥ 3 cites, drawn from the post-#304 still-refused 47):
    - case 0025 "Lilibeth fills 6 baskets where each basket holds 50
      strawberries."
    - case 0045 "Each survey has 10 questions."
    - case 0047 "John bakes 12 coconut macaroons, each weighing 5 ounces."

    Discriminator vs ``TEMPORAL_AGGREGATION``: multiplicative is
    spatial/per-container ("baskets ... strawberries"); temporal is
    per-time-window ("per day", "every week").  Dispatch order places
    temporal first so an "each day" framing wins where both apply.
    Discriminator vs ``DISCRETE_COUNT_STATEMENT``: multiplicative carries
    an inner aggregate dimension (the count-of-counted-things), while
    discrete-count carries one count-noun pair; the inner aggregate is
    the more-specific reading.
    """

    if _MULTIPLICATIVE_EACH_RE.search(padded_lower):
        return True
    if _MULTIPLICATIVE_CONTAINER_RE.search(padded_lower):
        return True
    return False


def _is_discrete_count_statement(padded_lower: str) -> bool:
    """A subject paired with one or more bare count-noun anchors.

    The canonical surface is ``<subject> <verb> <count> <counted-noun>``;
    "Nicole collected 400 Pokemon cards" and "A school has 100 students"
    are central instances.  Lists of count-noun pairs ("2 horses, 5 dogs")
    are admitted by the same predicate because each pair matches.

    Examples (≥ 3 cites, drawn from the post-#304 still-refused 47):
    - case 0023 "Nicole collected 400 Pokemon cards."
    - case 0027 "Malcolm has 240 followers on Instagram and 500
      followers on Facebook."
    - case 0046 "A school has 100 students."

    Discriminator vs ``RATE_WITH_CURRENCY`` and ``CURRENCY_AMOUNT``:
    discrete-count statements carry no currency symbol; the currency
    rules above this dispatch slot already claim those.  Discriminator
    vs ``MULTIPLICATIVE_AGGREGATION``: discrete-count has no
    inner-aggregate dimension; multiplicative above this slot already
    claims "each ... N" and "N <container> of N" forms.  Anything left
    is a bare count-noun pair.
    """

    if _DISCRETE_COUNT_DIGIT_NOUN_RE.search(padded_lower):
        return True
    if _DISCRETE_COUNT_WORD_NOUN_RE.search(padded_lower):
        return True
    return False


def _is_descriptive_setup_no_quantity(statement: str, padded_lower: str) -> bool:
    """Pure context with no extractable measurement.

    Examples (≥ 3 cites):
    - case 0003 "The student council sells scented erasers in the morning ..."
    - case 0008 "Marnie makes bead bracelets."
    - case 0019 "John adopts a dog from a shelter."
    """

    return not _has_any_quantity_marker(statement, padded_lower)


# ---------------------------------------------------------------------------
# Dispatch — fixed priority order.
# ---------------------------------------------------------------------------


def categorize(statement: str) -> ShapeCategory:
    """Map a refused statement to exactly one ``ShapeCategory``.

    Deterministic and side-effect free.  Returns ``UNCATEGORIZED`` when no
    rule fires; UNCATEGORIZED is the honest outcome, not a failure.
    """

    if not isinstance(statement, str):
        raise TypeError("statement must be a string")

    padded_lower = _padded_lower(statement)

    if _is_nested_question_target(statement):
        return ShapeCategory.NESTED_QUESTION_TARGET
    if _is_unit_partition(padded_lower):
        return ShapeCategory.UNIT_PARTITION
    if _is_rate_with_currency(padded_lower):
        return ShapeCategory.RATE_WITH_CURRENCY
    if _is_currency_amount(padded_lower):
        return ShapeCategory.CURRENCY_AMOUNT
    if _is_comparative_with_unit(padded_lower):
        return ShapeCategory.COMPARATIVE_WITH_UNIT
    if _is_fractional_rate_of_change(padded_lower):
        return ShapeCategory.FRACTIONAL_RATE_OF_CHANGE
    if _is_indefinite_quantity(padded_lower):
        return ShapeCategory.INDEFINITE_QUANTITY
    if _is_temporal_aggregation(padded_lower):
        return ShapeCategory.TEMPORAL_AGGREGATION
    if _is_conditional_quantity(statement):
        return ShapeCategory.CONDITIONAL_QUANTITY
    if _is_multiplicative_aggregation(padded_lower):
        return ShapeCategory.MULTIPLICATIVE_AGGREGATION
    if _is_discrete_count_statement(padded_lower):
        return ShapeCategory.DISCRETE_COUNT_STATEMENT
    if _is_descriptive_setup_no_quantity(statement, padded_lower):
        return ShapeCategory.DESCRIPTIVE_SETUP_NO_QUANTITY
    return ShapeCategory.UNCATEGORIZED


# Ordered enum tuple — exposed for tests asserting exhaustive coverage and
# for runners that need a stable iteration order.
SHAPE_CATEGORY_ORDER: tuple[ShapeCategory, ...] = (
    ShapeCategory.NESTED_QUESTION_TARGET,
    ShapeCategory.UNIT_PARTITION,
    ShapeCategory.RATE_WITH_CURRENCY,
    ShapeCategory.CURRENCY_AMOUNT,
    ShapeCategory.COMPARATIVE_WITH_UNIT,
    ShapeCategory.FRACTIONAL_RATE_OF_CHANGE,
    ShapeCategory.INDEFINITE_QUANTITY,
    ShapeCategory.TEMPORAL_AGGREGATION,
    ShapeCategory.CONDITIONAL_QUANTITY,
    ShapeCategory.MULTIPLICATIVE_AGGREGATION,
    ShapeCategory.DISCRETE_COUNT_STATEMENT,
    ShapeCategory.DESCRIPTIVE_SETUP_NO_QUANTITY,
    ShapeCategory.UNCATEGORIZED,
)


__all__ = [
    "ShapeCategory",
    "SHAPE_CATEGORY_ORDER",
    "categorize",
]
