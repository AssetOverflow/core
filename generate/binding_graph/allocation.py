"""ADR-0132 — Deterministic symbol allocator (Phase 1).

Given a sorted iterable of natural-language noun-phrases plus a single
source span anchoring them, return a stable ``tuple[SymbolBinding, ...]``
in the same order. Identical input → identical output, byte-for-byte.

This is the smallest useful allocator: pure transformation, no parsing,
no entity resolution. Phases 2+ will layer entity/unit inference on top.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from .model import BindingGraphError, SEMANTIC_ROLES, SourceSpanLink, SymbolBinding

_SLUG_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def _slugify(phrase: str) -> str:
    """Lowercase ASCII slug. Non-alphanumeric runs collapse to ``_``."""
    lowered = phrase.strip().lower()
    slug = _SLUG_NON_ALNUM.sub("_", lowered).strip("_")
    return slug


def allocate_symbols(
    noun_phrases: Iterable[str],
    *,
    source_span: SourceSpanLink,
    introduced_by: str,
    semantic_role: str = "quantity",
    prefix: str = "sym",
) -> tuple[SymbolBinding, ...]:
    """Allocate a deterministic ``tuple[SymbolBinding, ...]``.

    ``noun_phrases`` is consumed in given order. Caller is responsible
    for sorting if order-stability across input shapes is required —
    this function preserves the order it is handed.

    Symbol ids follow ``{prefix}_{slug}_{index:03d}``. The numeric
    suffix disambiguates duplicate slugs (e.g. two empty phrases would
    refuse — see below — but two phrases that slugify the same are
    legal and disambiguated by position).

    Refuses on:
      - empty iterable,
      - any phrase that slugifies to the empty string,
      - duplicate symbol_id collisions (cannot occur given the indexed
        suffix; defensive check retained).
    """
    if semantic_role not in SEMANTIC_ROLES:
        raise BindingGraphError(
            f"allocate_symbols.semantic_role must be one of "
            f"{sorted(SEMANTIC_ROLES)}; got {semantic_role!r}"
        )
    if not isinstance(introduced_by, str) or introduced_by == "":
        raise BindingGraphError(
            "allocate_symbols.introduced_by must be a non-empty str"
        )
    if not isinstance(prefix, str) or not prefix.isidentifier():
        raise BindingGraphError(
            f"allocate_symbols.prefix must be a Python identifier; "
            f"got {prefix!r}"
        )
    if not isinstance(source_span, SourceSpanLink):
        raise BindingGraphError(
            "allocate_symbols.source_span must be a SourceSpanLink"
        )

    phrases = tuple(noun_phrases)
    if not phrases:
        raise BindingGraphError(
            "allocate_symbols requires at least one noun-phrase"
        )

    bindings: list[SymbolBinding] = []
    seen_ids: set[str] = set()
    for index, phrase in enumerate(phrases):
        if not isinstance(phrase, str) or phrase.strip() == "":
            raise BindingGraphError(
                f"allocate_symbols phrase at index {index} must be a "
                f"non-empty str; got {phrase!r}"
            )
        slug = _slugify(phrase)
        if slug == "":
            raise BindingGraphError(
                f"allocate_symbols phrase at index {index} slugifies to "
                f"empty; got {phrase!r}"
            )
        symbol_id = f"{prefix}_{slug}_{index:03d}"
        if symbol_id in seen_ids:
            raise BindingGraphError(
                f"allocate_symbols produced duplicate symbol_id "
                f"{symbol_id!r} (this should not happen)"
            )
        seen_ids.add(symbol_id)
        bindings.append(
            SymbolBinding(
                symbol_id=symbol_id,
                name=phrase.strip(),
                semantic_role=semantic_role,
                source_span=source_span,
                introduced_by=introduced_by,
            )
        )
    return tuple(bindings)
