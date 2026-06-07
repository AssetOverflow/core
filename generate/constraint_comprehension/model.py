"""Problem model for the R2 finite-integer constraint organ.

The structural layer above ``generate.constraint_comprehension.expr``: the unknowns, the
raw per-category attribute coefficients (provenance), the assembled linear system, and the
query. This is the R2 twin of the binding-graph model — a typed :class:`ConstraintProblem`
the setup oracle grades and the solver consumes.

Pure data — no behavior. Deterministic.

Deviation from the design sketch: the query is a minimal dedicated :class:`ConstraintQuery`
(symbol + unit), NOT the binding-graph ``BoundUnknown`` — R2 has no state-index /
question-form axis, and forcing R1's unknown type onto it would be a degenerate fit.
Multiple-choice options and the provided answer key are NOT part of the problem IR; they are
answer-choice concerns graded separately (C4).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from generate.constraint_comprehension.expr import LinearConstraint

#: A finite-integer domain for an unknown. Count categories are nonnegative integers; the
#: broader signed-integer domain is reserved for future signed-quantity problems (so the
#: distinction is explicit, not a silent assumption that every unknown is a count).
Domain = Literal["nonnegative_integer", "integer"]


@dataclass(frozen=True, slots=True)
class Unknown:
    """One unknown category — ``large_bus``, ``chicken``, ``adult_ticket``.

    ``symbol`` is the canonical identifier used in ``LinearExpr.terms``; ``entity`` is the
    surface category noun (provenance); ``unit`` is the category's own count unit (``bus``,
    ``animal``); ``domain`` constrains the solution set (a count -> ``nonnegative_integer``).
    """

    symbol: str
    entity: str
    unit: str
    domain: Domain


@dataclass(frozen=True, slots=True)
class AttributeFact:
    """A per-category attribute coefficient read from the prose: ``large bus holds 50
    students`` -> ``AttributeFact("large_bus", "student", 50)``.

    This is the RAW reading (provenance); the weighted-total constraint
    ``50*large_bus + 30*small_bus = 260`` is assembled FROM these. ``value`` is the integer
    coefficient — positivity and cross-category distinctness are the reader's/oracle's gate
    (C3/C6), not enforced in this pure-data layer.
    """

    category: str
    measured_unit: str
    value: int


@dataclass(frozen=True, slots=True)
class ConstraintQuery:
    """The asked unknown: which category's count is the answer, and in what unit."""

    symbol: str
    unit: str


@dataclass(frozen=True, slots=True)
class ConstraintProblem:
    """A complete finite-integer constraint setup: the unknowns, the raw attribute
    coefficients, the assembled linear system, and the query.

    The setup oracle (C2) grades unknowns / units / domains / constraints / query
    canonically; the solver (C3) consumes ``unknowns`` + ``constraints``. ``facts`` is
    provenance — the coefficients the constraints were built from.
    """

    unknowns: tuple[Unknown, ...]
    facts: tuple[AttributeFact, ...]
    constraints: tuple[LinearConstraint, ...]
    query: ConstraintQuery


__all__ = [
    "AttributeFact",
    "ConstraintProblem",
    "ConstraintQuery",
    "Domain",
    "Unknown",
]
