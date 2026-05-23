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
    PHASE_2_ADMISSIBILITY,
    PHASE_2_UNIT_PROOF,
    SYNTHETIC_SOURCE_ID,
    AdapterError,
    bind_math_problem_graph,
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

__all__ = (
    "ADMISSIBILITY_STATUSES",
    "INTRODUCED_BY",
    "PHASE_2_ADMISSIBILITY",
    "PHASE_2_UNIT_PROOF",
    "SEMANTIC_ROLES",
    "SYNTHETIC_SOURCE_ID",
    "AdapterError",
    "BindingGraphError",
    "BoundConstraint",
    "BoundEquation",
    "BoundFact",
    "BoundUnknown",
    "SemanticSymbolicBindingGraph",
    "SourceSpanLink",
    "SymbolBinding",
    "allocate_symbols",
    "bind_math_problem_graph",
)
