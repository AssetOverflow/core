"""ADR-0055 Phase A — typed provenance parser for reviewed teaching entries.

Today's corpus provenance is a free-text string like
``"adr-0052:reviewed:2026-05-17"``.  This module parses that shape
into a typed ``Provenance`` without rewriting the JSONL on disk.
Existing entries keep their raw string; the parser is lenient — if
the string does not match the expected shape, the typed fields fall
back to ``None`` / ``"unknown"`` and the raw is preserved.

Future entries written by ``TeachingChainProposal`` (Phase C) should
emit the canonical shape directly.

Source enum follows ADR-0055 §A3:

  - ``"hand_authored"``    — written by an operator in an ADR PR
  - ``"discovery_promoted"`` — accepted ``TeachingChainProposal`` (Phase C+)
  - ``"imported"``         — bulk-imported from an external reviewed source

Anything else maps to ``"unknown"``.  The legacy ``"reviewed"`` token
seen in existing entries is treated as ``"hand_authored"`` so today's
corpus reports the right enum without a file rewrite.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


_KNOWN_SOURCES: frozenset[str] = frozenset({
    "hand_authored",
    "discovery_promoted",
    "imported",
})

# Legacy free-text tokens that have appeared in the corpus prior to
# Phase A.  Each maps to its canonical typed enum value.
_LEGACY_SOURCE_ALIASES: dict[str, str] = {
    "reviewed": "hand_authored",
}


@dataclass(frozen=True, slots=True)
class Provenance:
    adr_id: str | None
    source: str
    review_date: str | None
    raw: str


def _coerce_source(token: str) -> str:
    token = token.strip().lower()
    if token in _KNOWN_SOURCES:
        return token
    if token in _LEGACY_SOURCE_ALIASES:
        return _LEGACY_SOURCE_ALIASES[token]
    return "unknown"


def parse_provenance(value: Any) -> Provenance:
    """Parse a free-text provenance string into the typed shape.

    Recognised shape:  ``"<adr_id>:<source>:<review_date>"``
    where each segment is non-empty.  Extra trailing segments are
    folded into ``review_date`` so ``"adr-0052:reviewed:2026-05-17"``
    parses cleanly even if a future writer adds a fourth field by
    accident (defensive — the parser does not crash on drift).

    Non-string or empty input produces a ``Provenance`` with all
    typed fields ``None`` / ``"unknown"`` and ``raw=""``.
    """
    if not isinstance(value, str):
        return Provenance(adr_id=None, source="unknown", review_date=None, raw="")
    raw = value.strip()
    if not raw:
        return Provenance(adr_id=None, source="unknown", review_date=None, raw="")
    parts = raw.split(":")
    if len(parts) < 3:
        return Provenance(adr_id=None, source="unknown", review_date=None, raw=raw)
    adr_id = parts[0].strip() or None
    source = _coerce_source(parts[1])
    review_date_token = ":".join(parts[2:]).strip() or None
    return Provenance(
        adr_id=adr_id,
        source=source,
        review_date=review_date_token,
        raw=raw,
    )
