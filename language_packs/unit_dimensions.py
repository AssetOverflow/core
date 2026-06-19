"""Unit and dimension facade — exact unit/dimension facts from ADR-0127.

Tranche 1 — broad base-layer foundations.

Facade over ``loader.py`` (en_units_v1) exposing dimension compatibility
checks, exact conversions, and provenance-tagged unit facts.

Non-goals:
  - Fuzzy month/year conversions
  - Unsupported world conversions
  - Unit guessing
  - Solving a problem by unit conversion alone
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction

from language_packs.loader import (
    lookup_dimension,
    lookup_unit,
    get_conversion_graph,
)

# ---------------------------------------------------------------------------
# Rate dimension component mappings.
# ---------------------------------------------------------------------------
_RATE_COMPONENTS: dict[str, tuple[str, str]] = {
    "wage": ("money", "time"),
    "speed": ("length", "time"),
    "unit_price": ("money", "count"),
    "frequency": ("count", "time"),
    "density": ("mass", "volume"),
    "items_per_container": ("count", "container"),
}


# ---------------------------------------------------------------------------
# Dataclasses — frozen, slots=True.
# ---------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class DimensionFact:
    """A classified dimension fact for a unit token."""
    surface: str
    dimension: str
    singular: str
    plural: str
    is_derived: bool
    provenance_kind: str  # always "kernel_unit"


@dataclass(frozen=True, slots=True)
class ConversionFact:
    """An exact conversion fact between two compatible units."""
    from_unit: str
    to_unit: str
    ratio: Fraction
    dimension: str
    provenance_kind: str  # always "kernel_unit"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def classify_dimension(token: str) -> DimensionFact | None:
    """Classify a token's dimension via the en_units_v1 pack.

    Looks up the token as a unit and maps it to a DimensionFact.
    Returns None if unsupported or not found in the pack.
    """
    if not token:
        return None

    unit = lookup_unit(token)
    if unit is None:
        return None

    dim = lookup_dimension(unit.dimension)
    if dim is None:
        return None

    return DimensionFact(
        surface=token,
        dimension=unit.dimension,
        singular=unit.singular,
        plural=unit.plural,
        is_derived=dim.is_derived,
        provenance_kind="kernel_unit",
    )


def are_dimensions_compatible(dim_a: str, dim_b: str) -> bool:
    """Return True if two dimensions are compatible (same base dimension)."""
    dim_a_clean = dim_a.strip().lower()
    dim_b_clean = dim_b.strip().lower()

    if dim_a_clean == dim_b_clean:
        return True

    # Check if both are rate dimensions with compatible components.
    if dim_a_clean in _RATE_COMPONENTS and dim_b_clean in _RATE_COMPONENTS:
        num_a, den_a = _RATE_COMPONENTS[dim_a_clean]
        num_b, den_b = _RATE_COMPONENTS[dim_b_clean]
        return (
            are_dimensions_compatible(num_a, num_b)
            and are_dimensions_compatible(den_a, den_b)
        )

    return False


def exact_conversion(from_unit: str, to_unit: str) -> ConversionFact | None:
    """Return an exact conversion between two units if one exists in the pack.

    Does not perform multi-hop conversions (returns None if no direct edge exists).
    Ratios are converted to exact Fraction values.
    """
    if not from_unit or not to_unit:
        return None

    u_from = lookup_unit(from_unit)
    u_to = lookup_unit(to_unit)

    if u_from is None or u_to is None:
        return None

    if u_from.dimension != u_to.dimension:
        return None

    graph = get_conversion_graph(u_from.dimension)
    if not graph or not graph.edges:
        return None

    from_singular = u_from.singular.lower()
    to_singular = u_to.singular.lower()

    # Look for direct edge in the conversion graph.
    for edge in graph.edges:
        if edge.from_unit.lower() == from_singular and edge.to_unit.lower() == to_singular:
            exact_ratio = Fraction(edge.ratio).limit_denominator(1000000)
            return ConversionFact(
                from_unit=u_from.singular,
                to_unit=u_to.singular,
                ratio=exact_ratio,
                dimension=u_from.dimension,
                provenance_kind="kernel_unit",
            )

    return None


def classify_rate_dimension(numerator_dim: str, denominator_dim: str) -> str | None:
    """Classify a rate dimension from its components."""
    num = numerator_dim.strip().lower()
    den = denominator_dim.strip().lower()

    for rate_dim, (n, d) in _RATE_COMPONENTS.items():
        if n == num and d == den:
            return rate_dim

    return None


def supported_dimension_families() -> tuple[str, ...]:
    """Return all supported dimension family names, sorted."""
    return ("count", "length", "money", "time")
