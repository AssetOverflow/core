"""Typed expression IR for the arithmetic reader (PR-4).

The READER's source of meaning for an equation's right-hand side. The binding-graph
deliberately keeps ``BoundEquation.rhs_canonical`` a *string* (a decoupling layer that
does not import the symbolic substrate); this IR lives ABOVE that boundary in the reader,
serializes DOWN to the canonical string (``to_canonical_string``), and is read directly by
the projection (``to_relation``) so meaning is never recovered by re-parsing the string.

``to_canonical_string`` is byte-identical to the strings the reader emitted before PR-4
("ref + delta", "ref - delta", "a + b") — so the binding-graph and every downstream hash
are unchanged. Deterministic; no clock, no randomness.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Union


@dataclass(frozen=True, slots=True)
class Literal:
    """A grounded integer operand (a value sourced from the text)."""

    value: int


@dataclass(frozen=True, slots=True)
class Symbol:
    """A reference to another bound symbol."""

    symbol_id: str


@dataclass(frozen=True, slots=True)
class Add:
    left: "Expr"
    right: "Expr"


@dataclass(frozen=True, slots=True)
class Sub:
    left: "Expr"
    right: "Expr"


@dataclass(frozen=True, slots=True)
class Mul:
    """A scalar multiple of a symbol — the multiplicative comparative ("twice/N times
    as many"). ``left`` is the referenced symbol, ``right`` a dimensionless literal
    factor; the product keeps the symbol's unit (``count × scalar = count``).

    Scalar-only contract (the wrong=0 boundary). The *only* admitted shape is
    ``Mul(Symbol, Literal)`` — a unit-bearing symbol times a dimensionless integer.
    ``right`` being a :class:`Literal` (an ``int`` with no unit field) is what makes the
    factor dimensionless *by construction*: a unit-bearing literal multiplication is not
    representable, not merely unchecked. ``Mul(Symbol, Symbol)`` (a ``count × count``
    product) and any compound factor are deliberately NOT projected — see
    :func:`to_relation`, which refuses them. This refusal lives at the projection
    boundary, NOT in the dimensional admissibility checker: ``check_admissibility``'s
    ``multiply`` dispatch products operand units generally (``foot × pound → length·mass``,
    no refusal), so it would happily admit a ``count × count`` product as ``count²``. The
    scalar-only guarantee is therefore enforced HERE, by what we project, not there."""

    left: "Expr"
    right: "Expr"


@dataclass(frozen=True, slots=True)
class Div:
    """Exact integer division of a symbol by a dimensionless literal divisor — the
    fractional comparative ("half/a third as many"). ``left`` is the referenced symbol,
    ``right`` a dimensionless literal divisor; the quotient keeps the symbol's unit
    (``count / scalar = count``).

    "half as many" is modelled as ``Div(Symbol, Literal(2))``, NOT ``Mul`` by a rational:
    the system is integer-exact end to end (``oracle_answer -> int``) and :class:`Literal`
    is a dimensionless *integer* (the contract PR-6a proved load-bearing), so a fractional
    factor is not representable. Division by an integer divisor keeps everything integral.

    Divisor-only contract (the wrong=0 boundary). The only admitted shape is
    ``Div(Symbol, Literal)`` — see :func:`to_relation`, which refuses every other shape.
    Exactness is enforced downstream: the answer oracle admits the quotient ONLY when
    ``base % divisor == 0`` (an odd base over 2 refuses, never floors to a wrong integer)."""

    left: "Expr"
    right: "Expr"


@dataclass(frozen=True, slots=True)
class SumOf:
    """An aggregate over ≥2 symbols (the part-whole total)."""

    parts: tuple[Symbol, ...]


Expr = Union[Literal, Symbol, Add, Sub, Mul, Div, SumOf]


def to_canonical_string(expr: Expr) -> str:
    """Serialize to the canonical rhs string — byte-identical to the pre-IR format."""
    match expr:
        case Literal(value):
            return str(value)
        case Symbol(symbol_id):
            return symbol_id
        case Add(left, right):
            return f"{to_canonical_string(left)} + {to_canonical_string(right)}"
        case Sub(left, right):
            return f"{to_canonical_string(left)} - {to_canonical_string(right)}"
        case Mul(left, right):
            return f"{to_canonical_string(left)} * {to_canonical_string(right)}"
        case Div(left, right):
            return f"{to_canonical_string(left)} / {to_canonical_string(right)}"
        case SumOf(parts):
            return " + ".join(to_canonical_string(p) for p in parts)
    raise TypeError(f"not an Expr: {expr!r}")  # pragma: no cover - exhaustive above


def dependencies(expr: Expr) -> frozenset[str]:
    """The symbols the expression reads (the equation's dependency set)."""
    match expr:
        case Literal(_):
            return frozenset()
        case Symbol(symbol_id):
            return frozenset({symbol_id})
        case Add(left, right) | Sub(left, right) | Mul(left, right) | Div(left, right):
            return dependencies(left) | dependencies(right)
        case SumOf(parts):
            out: frozenset[str] = frozenset()
            for p in parts:
                out |= dependencies(p)
            return out
    raise TypeError(f"not an Expr: {expr!r}")  # pragma: no cover


def operation_kind(expr: Expr) -> str:
    """The binding-graph ``operation_kind`` an expression lowers to."""
    match expr:
        case Add(_, _) | SumOf(_):
            return "add"
        case Sub(_, _):
            return "subtract"
        case Mul(_, _):
            return "multiply"
        case Div(_, _):
            return "divide"
        case _:
            raise TypeError(f"expression has no operation_kind: {expr!r}")


def to_relation(lhs: str, expr: Expr) -> dict[str, Any] | None:
    """Project to a relational_metric relation, read from STRUCTURE (no string parse).

    ``None`` for a shape the projection does not handle — the caller refuses rather than
    emit a guessed relation (wrong=0 boundary). Each ``case`` is intentionally a *narrow*
    structural pattern, not a kind tag: ``Mul(Symbol, Literal)`` is the only multiplicative
    shape projected and ``Div(Symbol, Literal)`` the only divisive one (the scalar/divisor
    contracts — a ``count × count`` ``Mul(Symbol, Symbol)``, a compound factor, or a
    symbol-over-symbol ``Div`` falls through to ``None``). The dimensional checker would not
    catch such a masquerade (it products/quotients units happily), so this boundary is
    load-bearing.
    """
    match expr:
        case Add(Symbol(ref), Literal(delta)):
            return {"kind": "more_than", "entity": lhs, "ref": ref, "delta": delta}
        case Sub(Symbol(ref), Literal(delta)):
            return {"kind": "fewer_than", "entity": lhs, "ref": ref, "delta": delta}
        case Mul(Symbol(ref), Literal(factor)):
            return {"kind": "times_as_many", "entity": lhs, "ref": ref, "factor": factor}
        case Div(Symbol(ref), Literal(divisor)):
            return {"kind": "divide_by", "entity": lhs, "ref": ref, "divisor": divisor}
        case SumOf(parts):
            return {"kind": "sum_of", "entity": lhs, "parts": [p.symbol_id for p in parts]}
        case _:
            return None


__all__ = [
    "Add",
    "Div",
    "Expr",
    "Literal",
    "Mul",
    "Sub",
    "SumOf",
    "Symbol",
    "dependencies",
    "operation_kind",
    "to_canonical_string",
    "to_relation",
]
