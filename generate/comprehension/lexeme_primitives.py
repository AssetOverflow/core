"""ADR-0164.1 — Lexeme primitive registry.

Nine seed primitives for the incremental comprehension reader's step-1
lexical scan (ADR-0164 §Decision §3, ADR-0165 §Legitimate uses).

Public API:
  PRIMITIVE_REGISTRY  — immutable sorted tuple[LexemePrimitive, ...]
  scan(token)         — first-hit match in priority order; None on miss
"""

from __future__ import annotations

import re
import types
from dataclasses import dataclass
from typing import Mapping

# ---------------------------------------------------------------------------
# Core types
# ---------------------------------------------------------------------------

_ORDINAL_RANKS: dict[str, str] = {
    "first": "1",
    "second": "2",
    "third": "3",
    "fourth": "4",
    "fifth": "5",
    "sixth": "6",
    "seventh": "7",
    "eighth": "8",
    "ninth": "9",
    "tenth": "10",
}


@dataclass(frozen=True, slots=True)
class LexemePrimitive:
    name: str
    pattern: re.Pattern[str]
    emits: str
    extracts: tuple[str, ...]
    priority: int
    provenance: str


@dataclass(frozen=True, slots=True)
class LexemeMatch:
    primitive_name: str
    emit_category: str
    extracted_values: Mapping[str, str]
    source_text: str
    source_span: tuple[int, int]


# ---------------------------------------------------------------------------
# Per-primitive constant fields (not captured by regex groups)
# ---------------------------------------------------------------------------

_PRIMITIVE_CONSTANTS: dict[str, dict[str, str]] = {
    "decimal-currency-literal": {"unit_class": "currency"},
    "currency-literal": {"unit_class": "currency"},
    "percentage-literal": {"unit_class": "ratio"},
    "fraction-literal": {"unit_class": "fraction"},
    "time-amount-literal": {"unit_class": "time"},
    "numeric-literal": {"unit_class": "pending"},
    "ordinal-literal": {},
    "mass-noun-token": {"unit_class": "currency-mass"},
}


def _make_registry() -> tuple[LexemePrimitive, ...]:
    entries: list[LexemePrimitive] = [
        LexemePrimitive(
            name="decimal-currency-literal",
            pattern=re.compile(r"\$(?P<whole>\d+)\.(?P<cents>\d{2})\b"),
            emits="QUANTITY",
            extracts=("whole", "cents"),
            priority=10,
            provenance="ADR-0164.1",
        ),
        LexemePrimitive(
            name="currency-literal",
            pattern=re.compile(r"\$(?P<value>\d+(?:\.\d+)?)\b"),
            emits="QUANTITY",
            extracts=("value",),
            priority=20,
            provenance="ADR-0164.1",
        ),
        LexemePrimitive(
            name="percentage-literal",
            pattern=re.compile(r"(?P<value>\d+(?:\.\d+)?)[ ]?%"),
            emits="QUANTITY",
            extracts=("value",),
            priority=30,
            provenance="ADR-0164.1",
        ),
        LexemePrimitive(
            name="fraction-literal",
            pattern=re.compile(r"(?P<numerator>\d+)[ ]?/[ ]?(?P<denominator>\d+)\b"),
            emits="QUANTITY",
            extracts=("numerator", "denominator"),
            priority=40,
            provenance="ADR-0164.1",
        ),
        LexemePrimitive(
            name="time-amount-literal",
            pattern=re.compile(
                r"(?P<value>\d+)[- ]?"
                r"(?P<unit>hour|minute|day|week|month|year|second)s?\b",
                re.IGNORECASE,
            ),
            emits="QUANTITY",
            extracts=("value", "unit"),
            priority=50,
            provenance="ADR-0164.1",
        ),
        LexemePrimitive(
            name="ordinal-literal",
            pattern=re.compile(
                r"(?P<rank>first|second|third|fourth|fifth|"
                r"sixth|seventh|eighth|ninth|tenth)\b",
                re.IGNORECASE,
            ),
            emits="ORDINAL",
            extracts=("rank",),
            priority=60,
            provenance="ADR-0164.1",
        ),
        LexemePrimitive(
            name="mass-noun-token",
            pattern=re.compile(
                r"(?P<lemma>money|profit|interest|income|savings|cost|amount|total)\b",
                re.IGNORECASE,
            ),
            emits="UNIT_CATEGORY_TOKEN",
            extracts=("lemma",),
            priority=70,
            provenance="ADR-0164.1",
        ),
        LexemePrimitive(
            name="numeric-literal",
            pattern=re.compile(r"(?P<value>\d+(?:\.\d+)?)\b"),
            emits="QUANTITY",
            extracts=("value",),
            priority=100,
            provenance="ADR-0164.1",
        ),
        # ADR-0165 code-review test:
        # 1) Matches one capitalized token shape (name-like orthographic material).
        # 2) The class is closed by token-local capitalization/punctuation rules.
        # 3) Novel sentence phrasings still admit because matching is token-local.
        LexemePrimitive(
            name="proper_noun_token",
            pattern=re.compile(r"^[A-Z][A-Za-z'’\-]*[a-z][A-Za-z'’\-]*$"),
            emits="proper_noun_token",
            extracts=("surface",),
            priority=90,
            provenance="adr_0164_1_amendment_brief_8_2",
        ),
    ]
    return tuple(sorted(entries, key=lambda p: (p.priority, p.name)))


PRIMITIVE_REGISTRY: tuple[LexemePrimitive, ...] = _make_registry()


# ---------------------------------------------------------------------------
# scan — hot path: priority-ordered first-hit match
# ---------------------------------------------------------------------------

def scan(token: str) -> LexemeMatch | None:
    """Return the first matching LexemePrimitive result, or None.

    Runs primitives in priority order (lower first). First non-empty match
    wins. Does not advance past end-of-token; uses fullmatch semantics on
    the trimmed token so cross-token patterns cannot fire.

    Pure / deterministic / no I/O.
    """
    if not token:
        return None

    for primitive in PRIMITIVE_REGISTRY:
        m = primitive.pattern.search(token)
        if m is None:
            continue

        start, end = m.span()
        groups = m.groupdict()

        # For ordinal-literal, replace the word with its integer rank.
        if primitive.name == "ordinal-literal" and "rank" in groups:
            groups["rank"] = _ORDINAL_RANKS.get(groups["rank"].lower(), groups["rank"])

        # Merge captured groups with per-primitive constants, sort keys.
        merged = {**groups, **_PRIMITIVE_CONSTANTS.get(primitive.name, {})}
        ev: Mapping[str, str] = types.MappingProxyType(
            {k: merged[k] for k in sorted(merged)}
        )

        return LexemeMatch(
            primitive_name=primitive.name,
            emit_category=primitive.emits,
            extracted_values=ev,
            source_text=token[start:end],
            source_span=(start, end),
        )

    return None
