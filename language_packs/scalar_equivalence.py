"""Scalar equivalence facade — canonical rational scalar facts from ADR-0128.

Tranche 1 — broad base-layer foundations.

Thin facade over ``numerics_loader.py`` exposing canonical ``Fraction``
values for scalar surfaces.  Respects ADR-0128 boundaries: if a surface
is refused by the underlying pack, this facade does not silently broaden it.

The facade MAY emit ``ScalarCandidate`` records.
It MAY NOT solve problems, bind base quantities, choose operations,
or infer final answers.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction

from language_packs.ambiguity_hazards import lookup_hazards
from language_packs.numerics_loader import (
    FractionEntry,
    MultiplierEntry,
    ParsedNumber,
    lookup_fraction,
    lookup_multiplier,
    match_number_format,
)


# ---------------------------------------------------------------------------
# Documented unsupported surfaces — Tranche 1 scope.
# ---------------------------------------------------------------------------
_UNSUPPORTED_SURFACES: tuple[str, ...] = (
    ".5",       # no leading digit — ambiguous tokenisation
    "1 / 2",   # spaces around slash — not a single token
)


# ---------------------------------------------------------------------------
# Source category constants — closed set per Tranche 1 spec.
# ---------------------------------------------------------------------------
SOURCE_FRACTION_WORD: str = "fraction_word"
SOURCE_FRACTION_SYMBOL: str = "fraction_symbol"
SOURCE_PERCENTAGE: str = "percentage"
SOURCE_DECIMAL: str = "decimal"
SOURCE_SLASH_FRACTION: str = "slash_fraction"
SOURCE_MULTIPLIER: str = "multiplier"

# Mapping from FractionEntry morphology to source category.
_MORPHOLOGY_TO_SOURCE: dict[str, str] = {
    "fraction": SOURCE_FRACTION_WORD,
    "fraction-symbol": SOURCE_FRACTION_SYMBOL,
    "fraction-compound": SOURCE_FRACTION_WORD,
}

# Mapping from number-format format_id to source category.
_FORMAT_ID_TO_SOURCE: dict[str, str] = {
    "decimal": SOURCE_DECIMAL,
    "slash_fraction": SOURCE_SLASH_FRACTION,
    "mixed_number": SOURCE_SLASH_FRACTION,
    "percentage": SOURCE_PERCENTAGE,
    "thousand_separated": SOURCE_DECIMAL,
    "signed_integer": SOURCE_DECIMAL,
}


# ---------------------------------------------------------------------------
# ScalarCandidate — frozen, immutable result record.
# ---------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class ScalarCandidate:
    """A canonicalised scalar value derived from a surface string.

    ``canonical`` is always an exact ``fractions.Fraction`` — never a float.
    ``source`` classifies how the value was resolved (see source constants).
    ``entry_id`` is the ``en_numerics_v1`` entry id when the value came from
    a pack-backed lookup, ``None`` for purely format-parsed values.
    ``hazards`` carries hazard IDs from the ambiguity registry.
    """
    surface: str
    canonical: Fraction
    source: str
    entry_id: str | None
    hazards: tuple[str, ...]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
def _collect_hazard_ids(surface: str) -> tuple[str, ...]:
    """Look up ambiguity hazards for *surface* and return their IDs."""
    hazards = lookup_hazards(surface)
    if not hazards:
        return ()
    return tuple(h.hazard_id for h in hazards)


def _fraction_entry_to_candidate(
    surface: str,
    entry: FractionEntry,
) -> ScalarCandidate:
    """Convert a ``FractionEntry`` to a ``ScalarCandidate``."""
    canonical = Fraction(entry.numerator, entry.denominator)
    if entry.morphology == "fraction-symbol" or surface in {"½", "¼", "¾", "⅓", "⅔"}:
        source = SOURCE_FRACTION_SYMBOL
    else:
        source = _MORPHOLOGY_TO_SOURCE.get(entry.morphology, SOURCE_FRACTION_WORD)
    return ScalarCandidate(
        surface=surface,
        canonical=canonical,
        source=source,
        entry_id=entry.entry_id,
        hazards=_collect_hazard_ids(surface),
    )


def _parsed_number_to_candidate(
    surface: str,
    parsed: ParsedNumber,
) -> ScalarCandidate | None:
    """Convert a ``ParsedNumber`` to a ``ScalarCandidate``.

    Ensures the canonical value is an exact ``Fraction``.
    """
    source = _FORMAT_ID_TO_SOURCE.get(parsed.format_id)
    if source is None:
        return None

    # Derive an exact Fraction from the raw string, avoiding float intermediaries.
    canonical: Fraction
    if parsed.format_id == "percentage":
        # Raw is like "50%" or "12.5%" — strip '%', convert to Fraction, divide by 100.
        number_str = parsed.raw.rstrip("%")
        canonical = Fraction(number_str) / 100
    elif parsed.format_id == "decimal":
        # Raw is like "0.5" or "-3.14" — Fraction(str) gives exact representation.
        canonical = Fraction(parsed.raw)
    elif parsed.format_id == "slash_fraction":
        # Raw is like "1/2" or "-3/4" — Fraction(str) handles this directly.
        canonical = Fraction(parsed.raw)
    elif parsed.format_id == "mixed_number":
        # Raw is like "1 1/2" — parsed.value is already a Fraction from the loader.
        if isinstance(parsed.value, Fraction):
            canonical = parsed.value
        else:
            # Fallback: parse manually.
            parts = parsed.raw.split(" ", 1)
            sign = 1
            body = parsed.raw
            if body.startswith("-"):
                sign = -1
                body = body[1:]
                parts = body.split(" ", 1)
            whole = int(parts[0])
            frac = Fraction(parts[1])
            canonical = Fraction(sign * (whole + frac))
    elif parsed.format_id == "thousand_separated":
        # Raw is like "1,000" — parsed.value is int.
        canonical = Fraction(int(str(parsed.value)))
    elif parsed.format_id == "signed_integer":
        # Raw is like "-42" or "7" — parsed.value is int.
        canonical = Fraction(int(str(parsed.value)))
    else:
        return None

    return ScalarCandidate(
        surface=surface,
        canonical=canonical,
        source=source,
        entry_id=None,
        hazards=_collect_hazard_ids(surface),
    )


def _multiplier_entry_to_candidate(
    surface: str,
    entry: MultiplierEntry,
) -> ScalarCandidate:
    """Convert a ``MultiplierEntry`` to a ``ScalarCandidate``.

    The multiplier factor is stored as float in the pack; we convert to
    an exact Fraction via the string representation for clean rationals.
    """
    canonical = Fraction(entry.factor).limit_denominator(10000)
    return ScalarCandidate(
        surface=surface,
        canonical=canonical,
        source=SOURCE_MULTIPLIER,
        entry_id=entry.entry_id,
        hazards=_collect_hazard_ids(surface),
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def canonicalize_scalar(surface: str) -> ScalarCandidate | None:
    """Attempt to canonicalize a surface string to an exact Fraction.

    Resolution order:

    1. Try ``lookup_fraction`` (handles word forms, symbols, compounds).
    2. Try ``match_number_format`` (handles ``1/2``, ``0.5``, ``50%``, etc.).
    3. Try ``lookup_multiplier`` (handles ``half`` as multiplier).

    Returns ``None`` if the surface is unsupported or refused by the
    underlying pack.
    """
    if not surface:
        return None

    # Explicitly refuse documented unsupported surfaces.
    if surface in _UNSUPPORTED_SURFACES:
        return None

    # 1. Fraction lookup — word forms, Unicode symbols, compounds.
    frac_entry: FractionEntry | None = lookup_fraction(surface)
    if frac_entry is not None:
        return _fraction_entry_to_candidate(surface, frac_entry)

    # 2. Number format matching — slash fractions, decimals, percentages, etc.
    parsed: ParsedNumber | None = match_number_format(surface)
    if parsed is not None:
        candidate = _parsed_number_to_candidate(surface, parsed)
        if candidate is not None:
            return candidate

    # 3. Multiplier lookup — 'half' as multiplier, 'double', 'triple'.
    mult_entry: MultiplierEntry | None = lookup_multiplier(surface)
    if mult_entry is not None:
        return _multiplier_entry_to_candidate(surface, mult_entry)

    return None


def is_supported_scalar(surface: str) -> bool:
    """Return ``True`` if the surface can be canonicalized."""
    return canonicalize_scalar(surface) is not None


def list_unsupported_surfaces() -> tuple[str, ...]:
    """Return documented unsupported scalar surfaces.

    These are surfaces that look numeric but are explicitly refused
    by the pack or this facade due to tokenisation or ambiguity issues.
    """
    return _UNSUPPORTED_SURFACES
