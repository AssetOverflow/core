"""Typed linear-constraint IR for the R2 finite-integer constraint organ.

The algebraic layer: a linear combination over unknown symbols (:class:`LinearExpr`) and a
single linear equation (:class:`LinearConstraint`). This is the R2 twin of
``generate.quantitative_expr`` — the reader's/gold's SOURCE OF MEANING for a constraint,
kept above the string-serialization boundary. Strings are serialization only: meaning lives
in these typed terms, never recovered by parsing an expression string.

Pure data — no behavior. Canonicalization (sorting terms, comparing constraints) lives in
the setup signature (C2); the solver (C3) reads these terms directly. Deterministic; no
clock, no randomness.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from generate.binding_graph.model import SourceSpanLink

#: v1 admits only equality constraints. Inequalities (``<=`` / ``>=``) are a deliberate
#: future extension — not representable here, so they cannot be silently half-supported.
Relation = Literal["eq"]


@dataclass(frozen=True, slots=True)
class LinearExpr:
    """A linear combination over unknown symbols: ``sum(coeff * symbol) + constant``.

    ``terms`` pairs each symbol with its INTEGER coefficient as ``(symbol, coefficient)`` —
    matching the gold serialization ``["large_bus", 1]`` (the design sketch's prose comment
    said "coefficient, symbol"; the concrete JSON artifact and the idiomatic ``{var: coeff}``
    form both put the symbol first, so the symbol-first pairing is the one pinned here). The
    canonical form sorts terms by symbol and merges duplicates; that canonicalization lives
    in the setup signature, so two equal combinations written in different orders compare
    equal there. No floats: every coefficient and the constant are integers (the domain is
    finite-integer by construction).
    """

    terms: tuple[tuple[str, int], ...]
    constant: int = 0


@dataclass(frozen=True, slots=True)
class LinearConstraint:
    """A single linear equation ``lhs <relation> rhs`` (v1: ``relation == "eq"``).

    ``source_span`` is provenance populated by the reader (C5+); it is ``None`` for
    gold-authored constraints (which have no input span). It never participates in canonical
    equality — two constraints are setup-equal iff their ``lhs`` / ``relation`` / ``rhs``
    match (the signature in C2 strips the span before comparing).
    """

    lhs: LinearExpr
    relation: Relation
    rhs: int
    source_span: SourceSpanLink | None = None


__all__ = ["LinearConstraint", "LinearExpr", "Relation"]
