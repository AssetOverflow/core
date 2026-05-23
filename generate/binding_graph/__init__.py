"""ADR-0132 — Semantic-Symbolic Binding Graph, Phase 1 (data model only).

This package introduces the typed compiler boundary between natural-language
semantic parsing and symbolic/equational solving proposed in
``docs/implementation/semantic-symbolic-binding-graph-proposal.md``.

Phase 1 is intentionally a pure data layer:

  - frozen dataclasses with immutable collections,
  - deterministic symbol allocation,
  - refusal-first construction (typed ``BindingGraphError``),
  - no I/O, no parser calls, no algebra calls, no numpy,
  - no coupling to ``generate.math_symbolic_normalizer.Polynomial``;
    symbolic expressions are referenced by canonical string form only.

Phases 2-5 (adapter, unit-aware binding, question target binding, bounded
grammar integration) are deferred to follow-up PRs.
"""

from __future__ import annotations

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
    "SEMANTIC_ROLES",
    "BindingGraphError",
    "BoundConstraint",
    "BoundEquation",
    "BoundFact",
    "BoundUnknown",
    "SemanticSymbolicBindingGraph",
    "SourceSpanLink",
    "SymbolBinding",
    "allocate_symbols",
)
