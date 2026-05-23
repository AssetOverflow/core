"""Phase SSBG-1 immutable semantic-symbolic binding graph model."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Literal


SemanticRole = Literal[
    "entity",
    "quantity",
    "rate",
    "duration",
    "count",
    "total",
    "difference",
    "ratio",
    "unknown",
]

_ALLOWED_ROLES: Final[frozenset[str]] = frozenset(
    {
        "entity",
        "quantity",
        "rate",
        "duration",
        "count",
        "total",
        "difference",
        "ratio",
        "unknown",
    }
)


class BindingGraphError(ValueError):
    """Raised when graph construction invariants are violated."""


@dataclass(frozen=True, slots=True)
class SourceSpanLink:
    span_id: str
    text: str
    start_offset: int | None = None
    end_offset: int | None = None

    def __post_init__(self) -> None:
        if not self.span_id:
            raise BindingGraphError("SourceSpanLink.span_id must be non-empty")
        if not self.text:
            raise BindingGraphError("SourceSpanLink.text must be non-empty")
        if self.start_offset is not None and self.start_offset < 0:
            raise BindingGraphError("start_offset must be >= 0")
        if self.end_offset is not None and self.end_offset < 0:
            raise BindingGraphError("end_offset must be >= 0")
        if (
            self.start_offset is not None
            and self.end_offset is not None
            and self.end_offset < self.start_offset
        ):
            raise BindingGraphError("end_offset must be >= start_offset")


@dataclass(frozen=True, slots=True)
class SymbolBinding:
    symbol_id: str
    name: str
    semantic_role: SemanticRole
    entity_id: str | None
    unit_id: str | None
    source_span_id: str | None
    introduced_by: str

    def __post_init__(self) -> None:
        if not self.symbol_id:
            raise BindingGraphError("symbol_id must be non-empty")
        if not self.name:
            raise BindingGraphError("name must be non-empty")
        if self.semantic_role not in _ALLOWED_ROLES:
            raise BindingGraphError(
                f"unsupported semantic_role {self.semantic_role!r}"
            )
        if not self.introduced_by:
            raise BindingGraphError("introduced_by must be non-empty")


@dataclass(frozen=True, slots=True)
class BoundFact:
    fact_id: str
    symbol_id: str
    value: str
    unit_id: str | None
    source_span_id: str

    def __post_init__(self) -> None:
        if not self.fact_id:
            raise BindingGraphError("fact_id must be non-empty")
        if not self.symbol_id:
            raise BindingGraphError("symbol_id must be non-empty")
        if not self.value:
            raise BindingGraphError("value must be non-empty")
        if not self.source_span_id:
            raise BindingGraphError("source_span_id must be non-empty")


@dataclass(frozen=True, slots=True)
class BoundEquation:
    equation_id: str
    lhs_symbol_id: str
    operator: str
    rhs_symbol_ids: tuple[str, ...]
    unit_proof: str | None
    depends_on: tuple[str, ...]
    source_span_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.equation_id:
            raise BindingGraphError("equation_id must be non-empty")
        if not self.lhs_symbol_id:
            raise BindingGraphError("lhs_symbol_id must be non-empty")
        if not self.operator:
            raise BindingGraphError("operator must be non-empty")
        if not self.rhs_symbol_ids:
            raise BindingGraphError("rhs_symbol_ids must be non-empty")
        if not self.source_span_ids:
            raise BindingGraphError("source_span_ids must be non-empty")


@dataclass(frozen=True, slots=True)
class BoundUnknown:
    unknown_id: str
    symbol_id: str
    question_span_id: str
    expected_unit_id: str | None

    def __post_init__(self) -> None:
        if not self.unknown_id:
            raise BindingGraphError("unknown_id must be non-empty")
        if not self.symbol_id:
            raise BindingGraphError("symbol_id must be non-empty")
        if not self.question_span_id:
            raise BindingGraphError("question_span_id must be non-empty")


@dataclass(frozen=True, slots=True)
class BoundConstraint:
    constraint_id: str
    kind: str
    symbol_ids: tuple[str, ...]
    description: str

    def __post_init__(self) -> None:
        if not self.constraint_id:
            raise BindingGraphError("constraint_id must be non-empty")
        if not self.kind:
            raise BindingGraphError("kind must be non-empty")
        if not self.description:
            raise BindingGraphError("description must be non-empty")


@dataclass(frozen=True, slots=True)
class SemanticSymbolicBindingGraph:
    graph_id: str
    symbols: tuple[SymbolBinding, ...]
    facts: tuple[BoundFact, ...]
    equations: tuple[BoundEquation, ...]
    unknowns: tuple[BoundUnknown, ...]
    constraints: tuple[BoundConstraint, ...]
    source_spans: tuple[SourceSpanLink, ...]

    def __post_init__(self) -> None:
        if not self.graph_id:
            raise BindingGraphError("graph_id must be non-empty")

        span_ids = _ensure_unique(
            [s.span_id for s in self.source_spans],
            "duplicate source span ids",
        )
        symbol_ids = _ensure_unique(
            [s.symbol_id for s in self.symbols],
            "duplicate symbol ids",
        )
        _ensure_unique([f.fact_id for f in self.facts], "duplicate fact ids")
        _ensure_unique(
            [e.equation_id for e in self.equations],
            "duplicate equation ids",
        )
        _ensure_unique(
            [u.unknown_id for u in self.unknowns],
            "duplicate unknown ids",
        )
        _ensure_unique(
            [c.constraint_id for c in self.constraints],
            "duplicate constraint ids",
        )

        for symbol in self.symbols:
            if (
                symbol.source_span_id is not None
                and symbol.source_span_id not in span_ids
            ):
                raise BindingGraphError(
                    f"symbol {symbol.symbol_id!r} references missing span "
                    f"{symbol.source_span_id!r}"
                )

        for fact in self.facts:
            if fact.symbol_id not in symbol_ids:
                raise BindingGraphError(
                    f"fact {fact.fact_id!r} references missing symbol "
                    f"{fact.symbol_id!r}"
                )
            if fact.source_span_id not in span_ids:
                raise BindingGraphError(
                    f"fact {fact.fact_id!r} references missing span "
                    f"{fact.source_span_id!r}"
                )

        for equation in self.equations:
            if equation.lhs_symbol_id not in symbol_ids:
                raise BindingGraphError(
                    f"equation {equation.equation_id!r} references missing lhs symbol"
                )
            for rhs_symbol_id in equation.rhs_symbol_ids:
                if rhs_symbol_id not in symbol_ids:
                    raise BindingGraphError(
                        f"equation {equation.equation_id!r} references missing rhs symbol "
                        f"{rhs_symbol_id!r}"
                    )
            for span_id in equation.source_span_ids:
                if span_id not in span_ids:
                    raise BindingGraphError(
                        f"equation {equation.equation_id!r} references missing span "
                        f"{span_id!r}"
                    )

        for unknown in self.unknowns:
            if unknown.symbol_id not in symbol_ids:
                raise BindingGraphError(
                    f"unknown {unknown.unknown_id!r} references missing symbol "
                    f"{unknown.symbol_id!r}"
                )
            if unknown.question_span_id not in span_ids:
                raise BindingGraphError(
                    f"unknown {unknown.unknown_id!r} references missing span "
                    f"{unknown.question_span_id!r}"
                )

        for constraint in self.constraints:
            for symbol_id in constraint.symbol_ids:
                if symbol_id not in symbol_ids:
                    raise BindingGraphError(
                        f"constraint {constraint.constraint_id!r} references missing symbol "
                        f"{symbol_id!r}"
                    )


def _ensure_unique(values: list[str], error: str) -> frozenset[str]:
    duplicates = sorted({v for v in values if values.count(v) > 1})
    if duplicates:
        raise BindingGraphError(f"{error}: {duplicates}")
    return frozenset(values)
