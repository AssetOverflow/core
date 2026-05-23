"""ADR-0134 — Pure unit algebra for binding-graph admissibility.

Closed dimensional vocabulary sourced from ``language_packs/data/en_units_v1``
(ADR-0127). Every unit id used in admissibility checking must canonicalize to a
lemma in that pack — otherwise :func:`parse_unit` refuses with
:class:`UnitAlgebraError` (``unknown_unit``). The module performs **no I/O at
call time**: the pack lexicon is read once at first :func:`parse_unit` /
:func:`_known` call and memoized into an immutable mapping.

Refusal-first: no coercion, no invention of new units. Composite unit strings
of the form ``"<num>_per_<denom>"`` are admitted iff both components resolve
to known pack lemmas; this lets rate operands compose deterministically
without expanding the pack vocabulary.

Algebra is the trivial integer-vector algebra over the closed base
``BASE_DIMENSIONS``. All primitives are pure, total on
:class:`UnitVector`, and commute / associate trivially.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Final


# ---------------------------------------------------------------------------
# Base dimensions
# ---------------------------------------------------------------------------

#: Closed base-dimension axis. Order is load-bearing: the exponent tuple of
#: every :class:`UnitVector` indexes into this in lockstep. Adding a new base
#: dimension is an ADR-level decision (extend deliberately; never silently).
BASE_DIMENSIONS: Final[tuple[str, ...]] = (
    "length",
    "time",
    "mass",
    "money",
    "count",
    "temperature",
)

_N_DIMS: Final[int] = len(BASE_DIMENSIONS)
_ZERO_VEC: Final[tuple[int, ...]] = (0,) * _N_DIMS


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class UnitAlgebraError(ValueError):
    """Raised when a unit id cannot be resolved to the closed vocabulary."""


# ---------------------------------------------------------------------------
# UnitVector
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class UnitVector:
    """An immutable exponent vector over :data:`BASE_DIMENSIONS`.

    ``exponents[i]`` is the exponent on ``BASE_DIMENSIONS[i]``. The all-zero
    vector is the dimensionless unit. Algebra is trivially commutative on
    :func:`unit_product` because integer addition commutes.
    """

    exponents: tuple[int, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.exponents, tuple):
            raise UnitAlgebraError(
                f"UnitVector.exponents must be a tuple; "
                f"got {type(self.exponents).__name__}"
            )
        if len(self.exponents) != _N_DIMS:
            raise UnitAlgebraError(
                f"UnitVector.exponents must have length {_N_DIMS}; "
                f"got {len(self.exponents)}"
            )
        for e in self.exponents:
            if not isinstance(e, int) or isinstance(e, bool):
                raise UnitAlgebraError(
                    f"UnitVector.exponents entries must be int; got {e!r}"
                )

    def to_canonical_string(self) -> str:
        """Deterministic human-readable form (e.g. ``money/time``).

        Empty (all-zero) → ``"dimensionless"``. Pure-numerator → no slash.
        Mixed → ``"<num>/<denom>"`` with multiple factors joined by ``*``.
        """
        nums: list[str] = []
        dens: list[str] = []
        for dim, e in zip(BASE_DIMENSIONS, self.exponents, strict=True):
            if e > 0:
                nums.append(dim if e == 1 else f"{dim}^{e}")
            elif e < 0:
                dens.append(dim if e == -1 else f"{dim}^{-e}")
        if not nums and not dens:
            return "dimensionless"
        num_part = "*".join(nums) if nums else "1"
        if not dens:
            return num_part
        return f"{num_part}/{'*'.join(dens)}"


#: Module-level singleton; reuse instead of reconstructing.
DIMENSIONLESS: Final[UnitVector] = UnitVector(exponents=_ZERO_VEC)


def _vec(**kwargs: int) -> UnitVector:
    """Construct a :class:`UnitVector` by base-dimension keyword."""
    v: list[int] = [0] * _N_DIMS
    for k, val in kwargs.items():
        v[BASE_DIMENSIONS.index(k)] = val
    return UnitVector(exponents=tuple(v))


# ---------------------------------------------------------------------------
# Domain → dimension vector (pack-driven)
# ---------------------------------------------------------------------------

# Each non-``units.dimension`` / non-``units.rate`` semantic-domain in
# ``en_units_v1`` corresponds to a single dimensional family. ``units.rate``
# entries are *connector words* ("per", "each") — not units — and are dropped.
# ``units.dimension`` entries are abstract dimension headers — also dropped.
_DOMAIN_VECTOR: Final[dict[str, UnitVector]] = {
    "units.length": _vec(length=1),
    "units.time": _vec(time=1),
    "units.mass": _vec(mass=1),
    "units.money": _vec(money=1),
    "units.count": _vec(count=1),
    "units.temperature": _vec(temperature=1),
    "units.area": _vec(length=2),
    "units.volume": _vec(length=3),
    "units.speed": _vec(length=1, time=-1),
    "units.frequency": _vec(time=-1),
    "units.density": _vec(mass=1, length=-3),
    "units.unit_price": _vec(money=1, count=-1),
    "units.wage": _vec(money=1, time=-1),
    "units.container": _vec(count=1),
    "units.symbol": DIMENSIONLESS,
}

_NON_UNIT_DOMAINS: Final[frozenset[str]] = frozenset(
    {"units.dimension", "units.rate"}
)


# ---------------------------------------------------------------------------
# Pack loader (lazy, memoized, frozen at first call)
# ---------------------------------------------------------------------------

_UNITS_PACK_LEXICON: Final[Path] = (
    Path(__file__).resolve().parents[2]
    / "language_packs"
    / "data"
    / "en_units_v1"
    / "lexicon.jsonl"
)


_KNOWN_UNITS: dict[str, UnitVector] | None = None


def _load_pack() -> dict[str, UnitVector]:
    """Parse ``en_units_v1/lexicon.jsonl`` once into the closed-vocab table.

    Only the lemma and its primary ``semantic_domain`` are consulted. Unknown
    domains are skipped (not refused — this is loader robustness, not user
    input). The resulting mapping is frozen by convention via the
    :func:`_known` memoization.
    """
    table: dict[str, UnitVector] = {}
    with _UNITS_PACK_LEXICON.open("r", encoding="utf-8") as fp:
        for line in fp:
            stripped = line.strip()
            if not stripped:
                continue
            row = json.loads(stripped)
            lemma = row.get("lemma")
            domains = row.get("semantic_domains") or ()
            if not lemma or not domains:
                continue
            primary = domains[0]
            if primary in _NON_UNIT_DOMAINS:
                continue
            vec = _DOMAIN_VECTOR.get(primary)
            if vec is None:
                continue
            # First-wins so deterministic reloads do not flip the mapping.
            table.setdefault(lemma, vec)
    return table


def _known() -> dict[str, UnitVector]:
    """Return the memoized closed-vocab table.

    The mapping is built lazily and never mutated thereafter — callers
    receive the same object each call but treat it as read-only.
    """
    global _KNOWN_UNITS
    if _KNOWN_UNITS is None:
        _KNOWN_UNITS = _load_pack()
    return _KNOWN_UNITS


# ---------------------------------------------------------------------------
# parse_unit + composite resolver
# ---------------------------------------------------------------------------


def _depluralize(unit_id: str) -> str | None:
    """Conservative English plural strip; returns canonical lemma or ``None``.

    Tries (in order): exact lookup, ``-ies → -y``, ``-es`` strip, ``-s`` strip.
    Returns the first candidate found in the pack table.
    """
    table = _known()
    if unit_id in table:
        return unit_id
    candidates: list[str] = []
    if unit_id.endswith("ies") and len(unit_id) > 3:
        candidates.append(unit_id[:-3] + "y")
    if unit_id.endswith("es") and len(unit_id) > 2:
        candidates.append(unit_id[:-2])
    if unit_id.endswith("s") and len(unit_id) > 1:
        candidates.append(unit_id[:-1])
    for cand in candidates:
        if cand in table:
            return cand
    return None


def parse_unit(canonical_id: str) -> UnitVector:
    """Resolve a unit id to its :class:`UnitVector` via the closed vocabulary.

    Resolution order:
      1. exact pack lemma;
      2. conservative depluralization (``apples → apple`` etc.);
      3. composite ``"<num>_per_<denom>"`` recursively resolved as
         ``unit_quotient(parse_unit(num), parse_unit(denom))``.

    Refuses (raises :class:`UnitAlgebraError`) on any other input. The refusal
    is the wrong-answer firewall — the binding graph never silently invents
    or coerces a unit.
    """
    if not isinstance(canonical_id, str) or canonical_id == "":
        raise UnitAlgebraError(
            f"parse_unit requires a non-empty str; got {canonical_id!r}"
        )
    table = _known()
    canon = _depluralize(canonical_id)
    if canon is not None:
        return table[canon]
    # Composite fallback: ``X_per_Y``.
    if "_per_" in canonical_id:
        # Rightmost split keeps complex numerators (``foot_per_second_squared``
        # would parse as ``foot_per_second`` / ``squared`` — refuse loudly if
        # either side is not in the closed vocab, which is the correct outcome).
        num_part, _, denom_part = canonical_id.partition("_per_")
        # parse_unit may raise; let it propagate as the typed refusal.
        num_vec = parse_unit(num_part)
        denom_vec = parse_unit(denom_part)
        return unit_quotient(num_vec, denom_vec)
    raise UnitAlgebraError(
        f"unknown_unit: {canonical_id!r} is not in en_units_v1"
    )


# ---------------------------------------------------------------------------
# Algebra primitives
# ---------------------------------------------------------------------------


def unit_product(a: UnitVector, b: UnitVector) -> UnitVector:
    """Component-wise sum of exponents. Commutative; byte-equal on swap."""
    return UnitVector(
        exponents=tuple(
            x + y for x, y in zip(a.exponents, b.exponents, strict=True)
        )
    )


def unit_quotient(a: UnitVector, b: UnitVector) -> UnitVector:
    """Component-wise subtraction. Non-commutative by construction."""
    return UnitVector(
        exponents=tuple(
            x - y for x, y in zip(a.exponents, b.exponents, strict=True)
        )
    )


def unit_inverse(a: UnitVector) -> UnitVector:
    """Component-wise negation. ``unit_inverse(unit_inverse(v)) == v``."""
    return UnitVector(exponents=tuple(-x for x in a.exponents))


def units_equal(a: UnitVector, b: UnitVector) -> bool:
    """Strict equality on the exponent vector. No tolerance, no coercion."""
    return a.exponents == b.exponents


__all__ = (
    "BASE_DIMENSIONS",
    "DIMENSIONLESS",
    "UnitAlgebraError",
    "UnitVector",
    "parse_unit",
    "unit_inverse",
    "unit_product",
    "unit_quotient",
    "units_equal",
)
