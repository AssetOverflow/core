"""Loader API for the ``en_numerics_v1`` ratified semantic pack.

Sub-phase ADR-0128.2. Lives in a sibling module to ``loader.py`` to
avoid a merge conflict with the concurrent ADR-0127 ``en_units_v1``
loader work; the two modules will be folded together in a follow-up
PR once both packs ratify.

The public API exposes typed dataclasses for each entry kind plus
lookup / compositional helpers:

    lookup_cardinal(token)            -> CardinalEntry | None
    lookup_ordinal(token)             -> OrdinalEntry | None
    lookup_fraction(token)            -> FractionEntry | None
    lookup_quantifier(token)          -> QuantifierEntry | None
    lookup_multiplier(token)          -> MultiplierEntry | None
    lookup_comparison_anchor(token)   -> ComparisonAnchorEntry | None
    match_number_format(token)        -> ParsedNumber | None
    parse_compound_cardinal(text)     -> int | None

Lookups are case-insensitive on surface and stable across calls.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from fractions import Fraction
from functools import lru_cache
from pathlib import Path
from typing import Mapping, Optional, Tuple

PACK_ID = "en_numerics_v1"
PACK_ROOT = Path(__file__).resolve().parent / "data" / PACK_ID

# Closed set of quantifier semantic types (ADR-0128 ratification invariant).
QUANTIFIER_SEMANTIC_TYPES: frozenset[str] = frozenset({
    "total", "empty", "partial", "paired", "distributive", "indefinite",
})


# ---------------------------------------------------------------------------
# Entry dataclasses (frozen — immutable per CLAUDE.md immutability rule).
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class CardinalEntry:
    entry_id: str
    surface: str
    numeric_value: int
    morphology: str


@dataclass(frozen=True)
class OrdinalEntry:
    entry_id: str
    surface: str
    position: int
    morphology: str


@dataclass(frozen=True)
class FractionEntry:
    entry_id: str
    surface: str
    numerator: int
    denominator: int
    decimal_value: float
    morphology: str
    symbol: Optional[str] = None
    spelled_form: Optional[str] = None


@dataclass(frozen=True)
class MultiplierEntry:
    entry_id: str
    surface: str
    factor: float
    morphology: str


@dataclass(frozen=True)
class QuantifierEntry:
    entry_id: str
    surface: str
    semantic_type: str
    morphology: str
    determinate_value: Optional[int] = None

    @property
    def is_indefinite(self) -> bool:
        return self.semantic_type == "indefinite"


@dataclass(frozen=True)
class ComparisonAnchorEntry:
    entry_id: str
    surface: str
    anchor_class: str  # "additive" | "multiplicative"
    morphology: str


@dataclass(frozen=True)
class NumberFormatEntry:
    entry_id: str
    format_id: str
    regex: str
    parser_function: str
    output_type: str


@dataclass(frozen=True)
class ParsedNumber:
    """Result of ``match_number_format`` — carries the parsed value plus
    the format rule that matched."""
    format_id: str
    raw: str
    value: object  # int | float | Fraction
    output_type: str


# ---------------------------------------------------------------------------
# Index — built once and cached for the process lifetime. Pack data is
# immutable on disk; returning the cached mapping is safe.
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class _PackIndex:
    cardinals: Mapping[str, CardinalEntry]
    ordinals: Mapping[str, OrdinalEntry]
    fractions: Mapping[str, FractionEntry]
    multipliers: Mapping[str, MultiplierEntry]
    quantifiers: Mapping[str, QuantifierEntry]
    comparison_anchors: Mapping[str, Tuple[ComparisonAnchorEntry, ...]]
    number_formats: Tuple[NumberFormatEntry, ...]
    fraction_symbols: Mapping[str, FractionEntry]
    fraction_spelled: Mapping[str, FractionEntry]


def _read_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)


@lru_cache(maxsize=1)
def _index() -> _PackIndex:
    lexicon = list(_read_jsonl(PACK_ROOT / "lexicon.jsonl"))

    cardinals: dict[str, CardinalEntry] = {}
    ordinals: dict[str, OrdinalEntry] = {}
    fractions: dict[str, FractionEntry] = {}
    multipliers: dict[str, MultiplierEntry] = {}
    quantifiers: dict[str, QuantifierEntry] = {}
    comparison_buckets: dict[str, list[ComparisonAnchorEntry]] = {}
    number_formats: list[NumberFormatEntry] = []
    fraction_symbols: dict[str, FractionEntry] = {}
    fraction_spelled: dict[str, FractionEntry] = {}

    for row in lexicon:
        eid = row["entry_id"]
        surface = row["surface"].lower()
        if eid.startswith("en-num-card-"):
            cardinals[surface] = CardinalEntry(
                entry_id=eid, surface=row["surface"],
                numeric_value=int(row["numeric_value"]),
                morphology=row["morphology"],
            )
        elif eid.startswith("en-num-ord-"):
            ordinals[surface] = OrdinalEntry(
                entry_id=eid, surface=row["surface"],
                position=int(row["position"]),
                morphology=row["morphology"],
            )
        elif eid.startswith("en-num-frac-"):
            fe = FractionEntry(
                entry_id=eid, surface=row["surface"],
                numerator=int(row["numerator"]),
                denominator=int(row["denominator"]),
                decimal_value=float(row["decimal_value"]),
                morphology=row["morphology"],
                symbol=row.get("symbol"),
                spelled_form=row.get("spelled_form"),
            )
            fractions[surface] = fe
            if fe.symbol:
                fraction_symbols[fe.symbol] = fe
            if fe.morphology == "fraction-symbol":
                fraction_symbols.setdefault(fe.surface, fe)
                if fe.spelled_form:
                    fraction_spelled[fe.spelled_form.lower()] = fe
        elif eid.startswith("en-num-mult-"):
            # ``half`` exists both as fraction and multiplier; both rows are
            # accepted — disambiguation is by caller intent (which lookup).
            multipliers[surface] = MultiplierEntry(
                entry_id=eid, surface=row["surface"],
                factor=float(row["factor"]),
                morphology=row["morphology"],
            )
        elif eid.startswith("en-num-quant-"):
            quantifiers[surface] = QuantifierEntry(
                entry_id=eid, surface=row["surface"],
                semantic_type=row["semantic_type"],
                morphology=row["morphology"],
                determinate_value=row.get("determinate_value"),
            )
        elif eid.startswith("en-num-compare-"):
            anchor = ComparisonAnchorEntry(
                entry_id=eid, surface=row["surface"],
                anchor_class=row["anchor_class"],
                morphology=row["morphology"],
            )
            comparison_buckets.setdefault(surface, []).append(anchor)
        elif eid.startswith("en-num-format-"):
            number_formats.append(NumberFormatEntry(
                entry_id=eid,
                format_id=row["format_id"],
                regex=row["regex"],
                parser_function=row["parser_function"],
                output_type=row["output_type"],
            ))

    return _PackIndex(
        cardinals=cardinals,
        ordinals=ordinals,
        fractions=fractions,
        multipliers=multipliers,
        quantifiers=quantifiers,
        comparison_anchors={k: tuple(v) for k, v in comparison_buckets.items()},
        number_formats=tuple(number_formats),
        fraction_symbols=fraction_symbols,
        fraction_spelled=fraction_spelled,
    )


# ---------------------------------------------------------------------------
# Public lookups
# ---------------------------------------------------------------------------
def lookup_cardinal(token: str) -> Optional[CardinalEntry]:
    return _index().cardinals.get(token.lower())


def lookup_ordinal(token: str) -> Optional[OrdinalEntry]:
    return _index().ordinals.get(token.lower())


def lookup_fraction(token: str) -> Optional[FractionEntry]:
    if not token:
        return None
    idx = _index()
    # Symbol lookup (single grapheme like '½') — case-preserving.
    if token in idx.fraction_symbols:
        return idx.fraction_symbols[token]
    lower = token.lower()
    # Article-bound forms: "a half", "a quarter" → same entry as bare form.
    stripped = re.sub(r"^(a|an|the)\s+", "", lower)
    if stripped in idx.fractions:
        return idx.fractions[stripped]
    if stripped in idx.fraction_spelled:
        return idx.fraction_spelled[stripped]
    # Compound form: "two-thirds", "three quarters", "five eighths"
    compound = _parse_compound_fraction(stripped, idx)
    if compound is not None:
        return compound
    return None


def lookup_quantifier(token: str) -> Optional[QuantifierEntry]:
    return _index().quantifiers.get(token.lower())


def lookup_multiplier(token: str) -> Optional[MultiplierEntry]:
    return _index().multipliers.get(token.lower())


def lookup_comparison_anchor(token: str) -> Optional[ComparisonAnchorEntry]:
    """Returns the first matching anchor entry. A surface may carry both
    additive and multiplicative classes only via separate entries; use
    :func:`lookup_comparison_anchors` to retrieve them all."""
    bucket = _index().comparison_anchors.get(token.lower())
    if not bucket:
        return None
    return bucket[0]


def lookup_comparison_anchors(token: str) -> Tuple[ComparisonAnchorEntry, ...]:
    return _index().comparison_anchors.get(token.lower(), ())


def number_format_entries() -> Tuple[NumberFormatEntry, ...]:
    return _index().number_formats


# ---------------------------------------------------------------------------
# Format matching
# ---------------------------------------------------------------------------
def _parse_thousand_separated(raw: str) -> int:
    return int(raw.replace(",", ""))


def _parse_decimal(raw: str) -> float:
    return float(raw)


def _parse_slash_fraction(raw: str) -> Fraction:
    return Fraction(raw)


def _parse_mixed_number(raw: str) -> Fraction:
    sign = 1
    body = raw
    if body.startswith("-"):
        sign = -1
        body = body[1:]
    whole_str, frac_str = body.split(" ", 1)
    whole = int(whole_str)
    frac = Fraction(frac_str)
    return sign * (whole + frac)


def _parse_percentage(raw: str) -> float:
    return float(raw[:-1]) / 100.0


def _parse_signed_integer(raw: str) -> int:
    return int(raw)


_FORMAT_PARSERS = {
    "parse_thousand_separated": _parse_thousand_separated,
    "parse_decimal": _parse_decimal,
    "parse_slash_fraction": _parse_slash_fraction,
    "parse_mixed_number": _parse_mixed_number,
    "parse_percentage": _parse_percentage,
    "parse_signed_integer": _parse_signed_integer,
}


def match_number_format(token: str) -> Optional[ParsedNumber]:
    """Return the parsed numeric value if ``token`` matches exactly one
    ratified format rule. Returns ``None`` if no rule matches OR if more
    than one rule matches (ambiguity is refused per ``wrong == 0``)."""
    if not isinstance(token, str) or not token:
        return None
    idx = _index()
    matches: list[NumberFormatEntry] = []
    for fmt in idx.number_formats:
        if re.fullmatch(fmt.regex, token):
            matches.append(fmt)
    if len(matches) != 1:
        return None
    fmt = matches[0]
    parser = _FORMAT_PARSERS[fmt.parser_function]
    try:
        value = parser(token)
    except (ValueError, ZeroDivisionError):
        return None
    return ParsedNumber(
        format_id=fmt.format_id, raw=token, value=value,
        output_type=fmt.output_type,
    )


# ---------------------------------------------------------------------------
# Compound parsing
# ---------------------------------------------------------------------------
_PLURAL_TO_SINGULAR = {
    "halves": "half", "thirds": "third", "quarters": "quarter",
    "fourths": "quarter",  # American "fourths" → same numeric form
    "fifths": "fifth", "sixths": "sixth", "sevenths": "seventh",
    "eighths": "eighth", "ninths": "ninth", "tenths": "tenth",
    "sixteenths": "sixteenth",
}


def _parse_compound_fraction(text: str, idx: _PackIndex) -> Optional[FractionEntry]:
    """Resolve compounds like ``two-thirds`` / ``three quarters``.

    Accepts a hyphen or a single space between the cardinal and the
    pluralised denominator word. Plural is required ("two thirds" not
    "two third") except for ``half`` where both forms exist in the wild
    — we accept "two halves" / "one half" / "a half"."""
    if "-" in text:
        parts = text.split("-", 1)
    elif " " in text:
        parts = text.split(" ", 1)
    else:
        return None
    if len(parts) != 2:
        return None
    num_word, den_word = parts
    cardinal = idx.cardinals.get(num_word)
    if cardinal is None:
        return None
    denom_singular = _PLURAL_TO_SINGULAR.get(den_word)
    if denom_singular is None:
        # Allow already-singular for "one half" / "one third" patterns.
        if den_word in idx.fractions:
            denom_singular = den_word
        else:
            return None
    base = idx.fractions.get(denom_singular)
    if base is None:
        return None
    num = cardinal.numeric_value
    den = base.denominator
    if den == 0:
        return None
    return FractionEntry(
        entry_id=f"{base.entry_id}+compound:{num}",
        surface=text,
        numerator=num,
        denominator=den,
        decimal_value=num / den,
        morphology="fraction-compound",
        symbol=None,
        spelled_form=None,
    )


def parse_compound_cardinal(text: str) -> Optional[int]:
    """Resolve compound English cardinals.

    Handles:
      * single-word forms ("seventeen")
      * hyphenated tens-unit ("twenty-one", "ninety-nine")
      * magnitude composition ("two hundred", "three hundred and fifty",
        "two thousand five hundred and seventeen")
    """
    if not text:
        return None
    text = text.strip().lower()
    if not text:
        return None
    idx = _index()
    if text in idx.cardinals:
        return idx.cardinals[text].numeric_value
    # Strip "and" connectors; normalise hyphens to spaces.
    normalised = text.replace("-", " ")
    tokens = [t for t in normalised.split() if t and t != "and"]
    if not tokens:
        return None

    total = 0
    current = 0
    for tok in tokens:
        if tok in idx.cardinals:
            val = idx.cardinals[tok].numeric_value
            if val == 100:
                current = max(current, 1) * 100
            elif val >= 1000:
                current = max(current, 1) * val
                total += current
                current = 0
            else:
                current += val
        else:
            return None
    return total + current
