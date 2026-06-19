"""Ambiguity hazard registry — centralises known ambiguous base-level surfaces.

Tranche 1 — broad base-layer foundations.

The registry is a static, deterministic mapping built at module load.
It annotates risks and context requirements on surfaces that are
ambiguous without additional problem context.

The registry does NOT solve, filter, or make admission decisions.
It provides hazard annotations that downstream substrate consumers
(scalar facade, process frames, ProblemFrame builder) can consult.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Mapping


# ---------------------------------------------------------------------------
# Hazard categories — closed set per Tranche 1 brief.
# ---------------------------------------------------------------------------
HAZARD_CATEGORIES: frozenset[str] = frozenset({
    "unbound_base_quantity",
    "half_duration",
    "quarter_coin",
    "quarter_calendar_period",
    "quarter_school_term",
    "third_ordinal",
    "ordinal_context",
    "currency_context",
    "temporal_context",
    "percent_change_vs_percent_of",
    "multiplicative_vs_occurrence_times",
    "comparative_direction_ambiguity",
    "indefinite_quantity",
    "remainder_context_required",
    "total_question_target_required",
    "blocked_provenance_gap",
})


# ---------------------------------------------------------------------------
# Hazard record — frozen and immutable.
# ---------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class AmbiguityHazard:
    """A registered ambiguity hazard for a base-level surface.

    ``context_required`` lists the context signals needed to resolve
    the ambiguity (e.g., ``("numeric_base_quantity",)`` for ``half``).
    ``disambiguation_notes`` provides human-readable guidance.
    """
    hazard_id: str
    surface: str
    category: str
    description: str
    context_required: tuple[str, ...]
    disambiguation_notes: str

    def __post_init__(self) -> None:
        if self.category not in HAZARD_CATEGORIES:
            raise ValueError(
                f"AmbiguityHazard.category must be one of the registered "
                f"categories, got {self.category!r}"
            )


# ---------------------------------------------------------------------------
# Registry data — static, exhaustive for Tranche 1 required surfaces.
# ---------------------------------------------------------------------------
def _build_registry() -> tuple[AmbiguityHazard, ...]:
    """Build the complete hazard registry.

    Each entry is a unique (surface, category) pair.  A single surface
    may carry multiple hazards (e.g., ``quarter`` has three).
    """
    entries: list[AmbiguityHazard] = []
    _id = 0

    def _add(
        surface: str,
        category: str,
        description: str,
        context_required: tuple[str, ...],
        disambiguation_notes: str,
    ) -> None:
        nonlocal _id
        _id += 1
        entries.append(AmbiguityHazard(
            hazard_id=f"haz-{_id:04d}",
            surface=surface,
            category=category,
            description=description,
            context_required=context_required,
            disambiguation_notes=disambiguation_notes,
        ))

    # --- half ---
    _add(
        "half", "unbound_base_quantity",
        "'half' requires a base quantity to halve",
        ("numeric_base_quantity",),
        "Resolve by identifying what is being halved (e.g., 'half of 10 apples')",
    )
    _add(
        "half", "half_duration",
        "'half' may refer to a temporal duration (e.g., 'half an hour')",
        ("temporal_context",),
        "Check if 'half' modifies a time unit",
    )

    # --- quarter ---
    _add(
        "quarter", "unbound_base_quantity",
        "'quarter' as 1/4 requires a base quantity",
        ("numeric_base_quantity",),
        "Resolve by identifying what is being quartered",
    )
    _add(
        "quarter", "quarter_coin",
        "'quarter' may refer to a US coin worth $0.25",
        ("currency_context",),
        "Check if context involves money, coins, or currency",
    )
    _add(
        "quarter", "quarter_calendar_period",
        "'quarter' may refer to a 3-month calendar period",
        ("temporal_context",),
        "Check if context involves calendar, fiscal, or business periods",
    )
    _add(
        "quarter", "quarter_school_term",
        "'quarter' may refer to an academic term",
        ("academic_context",),
        "Check if context involves school, classes, or academic terms",
    )

    # --- third ---
    _add(
        "third", "unbound_base_quantity",
        "'third' as 1/3 requires a base quantity",
        ("numeric_base_quantity",),
        "Resolve by identifying what is being divided into thirds",
    )
    _add(
        "third", "third_ordinal",
        "'third' may be an ordinal (position 3), not a fraction",
        ("ordinal_context",),
        "Check if 'third' refers to position/rank vs. fraction 1/3",
    )

    # --- percent ---
    _add(
        "percent", "percent_change_vs_percent_of",
        "'percent' is ambiguous between percent-of and percent-change",
        ("percent_base_quantity", "change_direction"),
        "Determine if percent is applied to a base (percent-of) "
        "or describes a change (percent-change)",
    )

    # --- percentage points ---
    _add(
        "percentage points", "percent_change_vs_percent_of",
        "'percentage points' is distinct from percent but easily confused",
        ("percent_base_quantity",),
        "Percentage points are additive differences between percentages, "
        "not multiplicative",
    )

    # --- times ---
    _add(
        "times", "multiplicative_vs_occurrence_times",
        "'times' may be a multiplier (3 times as many) or an occurrence "
        "count (3 times a day)",
        ("multiplicative_context", "occurrence_context"),
        "Check if 'times' multiplies a quantity or counts occurrences",
    )

    # --- more than ---
    _add(
        "more than", "comparative_direction_ambiguity",
        "'more than' requires clear reference and target quantities",
        ("reference_quantity", "comparison_direction"),
        "Identify which quantity is the reference and which is the target",
    )

    # --- less than ---
    _add(
        "less than", "comparative_direction_ambiguity",
        "'less than' requires clear reference and target quantities",
        ("reference_quantity", "comparison_direction"),
        "Identify which quantity is the reference and which is the target",
    )

    # --- of ---
    _add(
        "of", "unbound_base_quantity",
        "'of' in 'X of Y' requires identifying the base quantity Y",
        ("base_quantity_referent",),
        "Determine if 'of' is partitive (half of), possessive, or descriptive",
    )

    # --- per ---
    _add(
        "per", "unbound_base_quantity",
        "'per' introduces a rate denominator; base must be grounded",
        ("rate_numerator", "rate_denominator"),
        "Both sides of the rate must be dimensionally grounded",
    )

    # --- each ---
    _add(
        "each", "unbound_base_quantity",
        "'each' is distributive — requires knowing the set being distributed over",
        ("distribution_set",),
        "Identify the set and the per-item quantity",
    )

    # --- some ---
    _add(
        "some", "indefinite_quantity",
        "'some' is an indefinite quantifier — cannot yield a determinate value",
        (),
        "Refuse: 'some' does not resolve to a number. "
        "Preserves wrong == 0.",
    )

    # --- remaining ---
    _add(
        "remaining", "remainder_context_required",
        "'remaining' requires knowing total and consumed quantities",
        ("total_quantity", "consumed_quantity"),
        "Identify what was the total and what was consumed/used",
    )

    # --- left ---
    _add(
        "left", "remainder_context_required",
        "'left' as remainder requires total and consumed quantities",
        ("total_quantity", "consumed_quantity"),
        "Identify what was the total and what was consumed/used; "
        "'left' may also be directional (spatial)",
    )

    # --- total ---
    _add(
        "total", "total_question_target_required",
        "'total' may be the question target or an intermediate sum",
        ("aggregation_scope",),
        "Determine if 'total' is the final answer target or an intermediate value",
    )

    # --- altogether ---
    _add(
        "altogether", "total_question_target_required",
        "'altogether' signals a summation question but scope must be identified",
        ("aggregation_scope",),
        "Determine what quantities are being summed",
    )

    return tuple(entries)


# ---------------------------------------------------------------------------
# Index — built once, cached for process lifetime.
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class _HazardIndex:
    """Internal index for fast lookup by surface."""
    by_surface: Mapping[str, tuple[AmbiguityHazard, ...]]
    all_hazards: tuple[AmbiguityHazard, ...]
    all_surfaces: tuple[str, ...]


@lru_cache(maxsize=1)
def _index() -> _HazardIndex:
    registry = _build_registry()
    by_surface: dict[str, list[AmbiguityHazard]] = {}
    for h in registry:
        by_surface.setdefault(h.surface.lower(), []).append(h)
    # Deterministic ordering: sort surfaces, sort hazards within each surface by hazard_id.
    sorted_surfaces = tuple(sorted(by_surface.keys()))
    frozen_by_surface = {
        k: tuple(sorted(v, key=lambda h: h.hazard_id))
        for k, v in by_surface.items()
    }
    return _HazardIndex(
        by_surface=frozen_by_surface,
        all_hazards=registry,
        all_surfaces=sorted_surfaces,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def lookup_hazards(surface: str) -> tuple[AmbiguityHazard, ...]:
    """Return all hazards registered for the given surface (case-insensitive).

    Returns an empty tuple if the surface has no registered hazards.
    """
    return _index().by_surface.get(surface.lower(), ())


def all_hazard_categories() -> frozenset[str]:
    """Return the closed set of hazard category strings."""
    return HAZARD_CATEGORIES


def all_registered_surfaces() -> tuple[str, ...]:
    """Return all surfaces with registered hazards, sorted deterministically."""
    return _index().all_surfaces


def is_hazardous(surface: str) -> bool:
    """Return True if the surface has any registered hazards."""
    return surface.lower() in _index().by_surface
