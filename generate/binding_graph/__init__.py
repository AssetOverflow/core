"""ADR-0132/0133 — Semantic-Symbolic Binding Graph.

Phase 1 (ADR-0132): pure data layer (frozen dataclasses, deterministic
allocator, refusal-first construction; no I/O, no parser, no algebra,
no ``Polynomial`` coupling — symbolic expressions held as canonical
strings only).

Phase 2 (ADR-0133): pure-function adapter
:func:`bind_math_problem_graph` translating
:class:`generate.math_problem_graph.MathProblemGraph` (ADR-0115) into a
:class:`SemanticSymbolicBindingGraph`. Still no runtime wiring.

Phases 3-5 (unit-aware equation binding / question-target binding /
bounded-grammar integration) are deferred to follow-up PRs.
"""

from __future__ import annotations

from .adapter import (
    INTRODUCED_BY,
    REFUSED_UNIT_PROOF,
    SYNTHETIC_SOURCE_ID,
    AdapterError,
    bind_math_problem_graph,
)
from .admissibility import (
    ADMISSIBILITY_REASONS,
    AdmissibilityError,
    UnitProof,
    check_admissibility,
)
from .allocation import allocate_symbols
from .model import (
    ADMISSIBILITY_STATUSES,
    SEMANTIC_ROLES,
    BindingGraphError,
    BoundConstraint,
    BoundEquation,
    BoundFact,
    BoundUnknown,
    SemanticSymbolicBindingGraph,
    SourceSpanLink,
    SymbolBinding,
)
from .units import (
    BASE_DIMENSIONS,
    DIMENSIONLESS,
    UnitAlgebraError,
    UnitVector,
    parse_unit,
    unit_inverse,
    unit_product,
    unit_quotient,
    units_equal,
)

__all__ = (
    "ADMISSIBILITY_REASONS",
    "ADMISSIBILITY_STATUSES",
    "BASE_DIMENSIONS",
    "DIMENSIONLESS",
    "INTRODUCED_BY",
    "REFUSED_UNIT_PROOF",
    "SEMANTIC_ROLES",
    "SYNTHETIC_SOURCE_ID",
    "AdapterError",
    "AdmissibilityError",
    "BindingGraphError",
    "BoundConstraint",
    "BoundEquation",
    "BoundFact",
    "BoundUnknown",
    "SemanticSymbolicBindingGraph",
    "SourceSpanLink",
    "SymbolBinding",
    "UnitAlgebraError",
    "UnitProof",
    "UnitVector",
    "allocate_symbols",
    "bind_math_problem_graph",
    "check_admissibility",
    "parse_unit",
    "unit_inverse",
    "unit_product",
    "unit_quotient",
    "units_equal",
)
