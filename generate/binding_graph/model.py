"""ADR-0132 — Frozen data model for the Semantic-Symbolic Binding Graph.

This module is the typed compiler boundary between natural language and
symbolic reasoning. It deliberately holds *only data* — no parser, no
solver, no algebra. Every dataclass is ``frozen=True, slots=True`` and
every collection field is an immutable ``tuple`` or ``frozenset``.

Refusal-first: invalid construction raises ``BindingGraphError`` rather
than silently coercing.

No coupling to ``Polynomial``: symbolic expressions are referenced by
their canonical *string* form (the byte-equality discriminator from
ADR-0131). This keeps the binding graph independent of the symbolic
substrate.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final, Literal, Union

from generate.binding_graph.acyclicity import CIRCULAR_DEPENDENCY, find_cycle

# ---------------------------------------------------------------------------
# Public errors
# ---------------------------------------------------------------------------


class BindingGraphError(ValueError):
    """Raised on invalid binding-graph construction.

    Sibling of ``generate.math_symbolic_normalizer.SymbolicError``;
    refusal-first by design, never silently coerces.
    """


# ---------------------------------------------------------------------------
# Closed vocabularies
# ---------------------------------------------------------------------------

# Allowed semantic roles. Closed set; extend deliberately in a future ADR.
SEMANTIC_ROLES: Final[frozenset[str]] = frozenset(
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

# Equation admissibility outcomes. ``"refused"`` requires ``refusal_reason``.
ADMISSIBILITY_STATUSES: Final[frozenset[str]] = frozenset(
    {"admitted", "pending", "refused"}
)

# ADR-0135 — closed ``BoundUnknown.question_form`` vocabulary. Never coerce
# silently to a default; refuse with ``QuestionTargetError`` on unmappable
# graph shapes. Extending this set is a future ADR (not a one-liner).
QUESTION_FORMS: Final[frozenset[str]] = frozenset(
    {"count", "rate", "total", "difference", "ratio", "identity"}
)

# ADR-0135 — closed ``BoundUnknown.state_index`` literal labels. The
# tagged-union ``StateIndex`` (below) is either one of these strings or
# an :class:`Operation` instance carrying a typed operation index.
STATE_INDEX_LABELS: Final[frozenset[str]] = frozenset({"initial", "terminal"})


@dataclass(frozen=True, slots=True)
class Operation:
    """ADR-0135 — state-index variant pointing at a specific operation.

    The ``operation_index`` is type-checked as ``int`` (not ``str``) so
    typos like ``Operation("3")`` refuse at construction. Cross-collection
    bounds (``operation_index < graph operation count``) are enforced by
    :class:`SemanticSymbolicBindingGraph.__post_init__`, not here — at
    standalone construction we only know the value must be non-negative.
    """

    operation_index: int

    def __post_init__(self) -> None:
        if not isinstance(self.operation_index, int) or isinstance(
            self.operation_index, bool
        ):
            raise BindingGraphError(
                f"Operation.operation_index must be int; "
                f"got {type(self.operation_index).__name__}"
            )
        if self.operation_index < 0:
            raise BindingGraphError(
                f"Operation.operation_index must be >= 0; "
                f"got {self.operation_index}"
            )


# Tagged union for the state at which a :class:`BoundUnknown`'s symbol
# is observed. ``"initial"`` / ``"terminal"`` collapse to the obvious
# endpoints; ``Operation`` references a specific intermediate step.
StateIndex = Union[Literal["initial", "terminal"], Operation]


def _require_non_empty_str(value: object, field_name: str) -> None:
    if not isinstance(value, str) or value == "":
        raise BindingGraphError(
            f"{field_name} must be a non-empty str; got {value!r}"
        )


def _require_optional_str(value: object, field_name: str) -> None:
    if value is not None and (not isinstance(value, str) or value == ""):
        raise BindingGraphError(
            f"{field_name} must be None or a non-empty str; got {value!r}"
        )


# ---------------------------------------------------------------------------
# SourceSpanLink
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SourceSpanLink:
    """An immutable pointer back to a slice of the original NL input.

    ``text`` is retained verbatim so downstream tooling can audit the
    span without re-reading the source document. ``[start, end)`` is a
    Python-style half-open interval over the source string.
    """

    source_id: str
    start: int
    end: int
    text: str

    def __post_init__(self) -> None:
        _require_non_empty_str(self.source_id, "SourceSpanLink.source_id")
        if not isinstance(self.start, int) or isinstance(self.start, bool):
            raise BindingGraphError(
                f"SourceSpanLink.start must be int; got {self.start!r}"
            )
        if not isinstance(self.end, int) or isinstance(self.end, bool):
            raise BindingGraphError(
                f"SourceSpanLink.end must be int; got {self.end!r}"
            )
        if self.start < 0:
            raise BindingGraphError(
                f"SourceSpanLink.start must be >= 0; got {self.start}"
            )
        if self.end <= self.start:
            raise BindingGraphError(
                f"SourceSpanLink.end must be > start; got start={self.start}, "
                f"end={self.end}"
            )
        if not isinstance(self.text, str) or self.text == "":
            raise BindingGraphError(
                f"SourceSpanLink.text must be a non-empty str; got {self.text!r}"
            )

    def to_canonical_string(self) -> str:
        """Stable serialization for hashing / replay."""
        return f"{self.source_id}[{self.start}:{self.end}]"


# ---------------------------------------------------------------------------
# SymbolBinding
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SymbolBinding:
    """A single bound symbol: identifier + semantic context + provenance."""

    symbol_id: str
    name: str
    semantic_role: str
    source_span: SourceSpanLink
    introduced_by: str
    entity: str | None = None
    unit: str | None = None

    def __post_init__(self) -> None:
        _require_non_empty_str(self.symbol_id, "SymbolBinding.symbol_id")
        if not self.symbol_id.isidentifier():
            raise BindingGraphError(
                f"SymbolBinding.symbol_id must be a Python identifier; "
                f"got {self.symbol_id!r}"
            )
        _require_non_empty_str(self.name, "SymbolBinding.name")
        if self.semantic_role not in SEMANTIC_ROLES:
            raise BindingGraphError(
                f"SymbolBinding.semantic_role must be one of "
                f"{sorted(SEMANTIC_ROLES)}; got {self.semantic_role!r}"
            )
        if not isinstance(self.source_span, SourceSpanLink):
            raise BindingGraphError(
                "SymbolBinding.source_span must be a SourceSpanLink; "
                f"got {type(self.source_span).__name__}"
            )
        _require_non_empty_str(self.introduced_by, "SymbolBinding.introduced_by")
        _require_optional_str(self.entity, "SymbolBinding.entity")
        _require_optional_str(self.unit, "SymbolBinding.unit")


# ---------------------------------------------------------------------------
# BoundFact
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class BoundFact:
    """A grounded fact: ``symbol_id = value [unit]`` lifted from language."""

    symbol_id: str
    value: str
    source_span: SourceSpanLink
    unit: str | None = None

    def __post_init__(self) -> None:
        _require_non_empty_str(self.symbol_id, "BoundFact.symbol_id")
        if not self.symbol_id.isidentifier():
            raise BindingGraphError(
                f"BoundFact.symbol_id must be a Python identifier; "
                f"got {self.symbol_id!r}"
            )
        _require_non_empty_str(self.value, "BoundFact.value")
        if not isinstance(self.source_span, SourceSpanLink):
            raise BindingGraphError(
                "BoundFact.source_span must be a SourceSpanLink"
            )
        _require_optional_str(self.unit, "BoundFact.unit")


# ---------------------------------------------------------------------------
# BoundEquation
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class BoundEquation:
    """A derived symbolic relation with provenance.

    ``lhs_symbol_id`` is the symbol being defined. ``rhs_canonical`` is
    the right-hand side as a canonical *string* — the binding graph
    deliberately does not import ``Polynomial`` (decoupling layer).

    ``dependencies`` is the (immutable) set of symbols the rhs reads.
    """

    lhs_symbol_id: str
    rhs_canonical: str
    dependencies: frozenset[str]
    operation_kind: str
    unit_proof: str
    admissibility_status: str
    source_span: SourceSpanLink
    refusal_reason: str | None = None

    def __post_init__(self) -> None:
        _require_non_empty_str(self.lhs_symbol_id, "BoundEquation.lhs_symbol_id")
        if not self.lhs_symbol_id.isidentifier():
            raise BindingGraphError(
                f"BoundEquation.lhs_symbol_id must be a Python identifier; "
                f"got {self.lhs_symbol_id!r}"
            )
        _require_non_empty_str(self.rhs_canonical, "BoundEquation.rhs_canonical")
        if not isinstance(self.dependencies, frozenset):
            raise BindingGraphError(
                "BoundEquation.dependencies must be a frozenset; "
                f"got {type(self.dependencies).__name__}"
            )
        for dep in self.dependencies:
            if not isinstance(dep, str) or not dep.isidentifier():
                raise BindingGraphError(
                    f"BoundEquation.dependencies entries must be identifier "
                    f"strs; got {dep!r}"
                )
        _require_non_empty_str(self.operation_kind, "BoundEquation.operation_kind")
        _require_non_empty_str(self.unit_proof, "BoundEquation.unit_proof")
        if self.admissibility_status not in ADMISSIBILITY_STATUSES:
            raise BindingGraphError(
                f"BoundEquation.admissibility_status must be one of "
                f"{sorted(ADMISSIBILITY_STATUSES)}; "
                f"got {self.admissibility_status!r}"
            )
        if not isinstance(self.source_span, SourceSpanLink):
            raise BindingGraphError(
                "BoundEquation.source_span must be a SourceSpanLink"
            )
        if self.admissibility_status == "refused":
            if not (
                isinstance(self.refusal_reason, str) and self.refusal_reason != ""
            ):
                raise BindingGraphError(
                    "BoundEquation.refusal_reason is required when "
                    "admissibility_status == 'refused'"
                )
        else:
            if self.refusal_reason is not None:
                raise BindingGraphError(
                    "BoundEquation.refusal_reason must be None unless "
                    "admissibility_status == 'refused'"
                )


# ---------------------------------------------------------------------------
# BoundUnknown
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class BoundUnknown:
    """The target of the question, bound to a known symbol.

    ADR-0135 widens the contract from "the symbol whose value the solver
    determines" to "the symbol at a specific temporal/state index with a
    specific question-form". The two new fields are *required* — no
    defaults — so every construction site declares its intent.
    """

    symbol_id: str
    question_span: SourceSpanLink
    state_index: "StateIndex"
    question_form: Literal[
        "count", "rate", "total", "difference", "ratio", "identity"
    ]
    expected_unit: str | None = None

    def __post_init__(self) -> None:
        _require_non_empty_str(self.symbol_id, "BoundUnknown.symbol_id")
        if not self.symbol_id.isidentifier():
            raise BindingGraphError(
                f"BoundUnknown.symbol_id must be a Python identifier; "
                f"got {self.symbol_id!r}"
            )
        if not isinstance(self.question_span, SourceSpanLink):
            raise BindingGraphError(
                "BoundUnknown.question_span must be a SourceSpanLink"
            )
        if isinstance(self.state_index, Operation):
            pass  # bounds re-checked by the graph; standalone is sign-only
        elif self.state_index not in STATE_INDEX_LABELS:
            raise BindingGraphError(
                f"BoundUnknown.state_index must be 'initial', 'terminal', or "
                f"an Operation instance; got {self.state_index!r}"
            )
        if self.question_form not in QUESTION_FORMS:
            raise BindingGraphError(
                f"BoundUnknown.question_form must be one of "
                f"{sorted(QUESTION_FORMS)}; got {self.question_form!r}"
            )
        _require_optional_str(self.expected_unit, "BoundUnknown.expected_unit")


# ---------------------------------------------------------------------------
# BoundConstraint
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class BoundConstraint:
    """A predicate restricting a symbol's admissible values.

    ``predicate`` is a canonical *string* (e.g. ``"x >= 0"``). Like
    ``BoundEquation.rhs_canonical``, this avoids importing the symbolic
    substrate.
    """

    symbol_id: str
    predicate: str
    source_span: SourceSpanLink

    def __post_init__(self) -> None:
        _require_non_empty_str(self.symbol_id, "BoundConstraint.symbol_id")
        if not self.symbol_id.isidentifier():
            raise BindingGraphError(
                f"BoundConstraint.symbol_id must be a Python identifier; "
                f"got {self.symbol_id!r}"
            )
        _require_non_empty_str(self.predicate, "BoundConstraint.predicate")
        if not isinstance(self.source_span, SourceSpanLink):
            raise BindingGraphError(
                "BoundConstraint.source_span must be a SourceSpanLink"
            )


# ---------------------------------------------------------------------------
# SemanticSymbolicBindingGraph
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SemanticSymbolicBindingGraph:
    """Top-level immutable container.

    All five sub-collections are tuples (deterministic order is the
    caller's responsibility — the model only enforces shape).
    Cross-collection invariants enforced at construction:

      - every ``BoundFact.symbol_id`` references a known ``SymbolBinding``;
      - every ``BoundEquation.lhs_symbol_id`` references a known symbol;
      - every ``BoundEquation`` dependency references a known symbol;
      - every ``BoundUnknown.symbol_id`` references a known symbol;
      - every ``BoundConstraint.symbol_id`` references a known symbol;
      - ``symbols`` carries unique ``symbol_id`` values.
    """

    symbols: tuple[SymbolBinding, ...] = field(default_factory=tuple)
    facts: tuple[BoundFact, ...] = field(default_factory=tuple)
    equations: tuple[BoundEquation, ...] = field(default_factory=tuple)
    unknowns: tuple[BoundUnknown, ...] = field(default_factory=tuple)
    constraints: tuple[BoundConstraint, ...] = field(default_factory=tuple)
    provenance: tuple[SourceSpanLink, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        for name, value, item_type in (
            ("symbols", self.symbols, SymbolBinding),
            ("facts", self.facts, BoundFact),
            ("equations", self.equations, BoundEquation),
            ("unknowns", self.unknowns, BoundUnknown),
            ("constraints", self.constraints, BoundConstraint),
            ("provenance", self.provenance, SourceSpanLink),
        ):
            if not isinstance(value, tuple):
                raise BindingGraphError(
                    f"SemanticSymbolicBindingGraph.{name} must be a tuple; "
                    f"got {type(value).__name__}"
                )
            for item in value:
                if not isinstance(item, item_type):
                    raise BindingGraphError(
                        f"SemanticSymbolicBindingGraph.{name} entries must be "
                        f"{item_type.__name__}; got {type(item).__name__}"
                    )

        known_ids: set[str] = set()
        for sym in self.symbols:
            if sym.symbol_id in known_ids:
                raise BindingGraphError(
                    f"Duplicate SymbolBinding.symbol_id: {sym.symbol_id!r}"
                )
            known_ids.add(sym.symbol_id)

        for fact in self.facts:
            if fact.symbol_id not in known_ids:
                raise BindingGraphError(
                    f"BoundFact references unknown symbol_id "
                    f"{fact.symbol_id!r}"
                )

        for eq in self.equations:
            if eq.lhs_symbol_id not in known_ids:
                raise BindingGraphError(
                    f"BoundEquation references unknown lhs_symbol_id "
                    f"{eq.lhs_symbol_id!r}"
                )
            for dep in eq.dependencies:
                if dep not in known_ids:
                    raise BindingGraphError(
                        f"BoundEquation references unknown dependency "
                        f"{dep!r} (lhs={eq.lhs_symbol_id!r})"
                    )

        # ADR-0203 — acyclicity invariant. Referential integrity (above) proves
        # every dependency names a known symbol; this proves the equation
        # dependency structure has no cycle. A cycle is circular reasoning
        # (conclude P because Q because P) — structurally well-formed, invalid.
        # The math adapter is acyclic by construction, so this refuses no
        # existing graph; it guards the structure before proof_chain (the first
        # consumer that could build a cycle) wires in. Multiple equations sharing
        # an lhs union their dependencies.
        adjacency: dict[str, set[str]] = {}
        for eq in self.equations:
            adjacency.setdefault(eq.lhs_symbol_id, set()).update(eq.dependencies)
        cycle = find_cycle({lhs: frozenset(deps) for lhs, deps in adjacency.items()})
        if cycle is not None:
            raise BindingGraphError(
                f"{CIRCULAR_DEPENDENCY}: equation dependency cycle "
                f"{' -> '.join(cycle)}"
            )

        equation_count = len(self.equations)
        for unk in self.unknowns:
            if unk.symbol_id not in known_ids:
                raise BindingGraphError(
                    f"BoundUnknown references unknown symbol_id "
                    f"{unk.symbol_id!r}"
                )
            if isinstance(unk.state_index, Operation):
                if unk.state_index.operation_index >= equation_count:
                    raise BindingGraphError(
                        f"BoundUnknown.state_index.operation_index "
                        f"{unk.state_index.operation_index} >= equation_count "
                        f"{equation_count}"
                    )

        for con in self.constraints:
            if con.symbol_id not in known_ids:
                raise BindingGraphError(
                    f"BoundConstraint references unknown symbol_id "
                    f"{con.symbol_id!r}"
                )

    def to_canonical_string(self) -> str:
        """Deterministic string serialization for stable hashing.

        Sub-collections are emitted in *given* (caller-supplied) order;
        the binding graph is identity-preserving by design.
        """
        lines: list[str] = []
        for sym in self.symbols:
            lines.append(
                f"S {sym.symbol_id} {sym.name} {sym.semantic_role} "
                f"entity={sym.entity} unit={sym.unit} "
                f"span={sym.source_span.to_canonical_string()} "
                f"by={sym.introduced_by}"
            )
        for fact in self.facts:
            lines.append(
                f"F {fact.symbol_id} = {fact.value} unit={fact.unit} "
                f"span={fact.source_span.to_canonical_string()}"
            )
        for eq in self.equations:
            deps = ",".join(sorted(eq.dependencies))
            lines.append(
                f"E {eq.lhs_symbol_id} := {eq.rhs_canonical} "
                f"op={eq.operation_kind} deps=[{deps}] "
                f"unit_proof={eq.unit_proof} "
                f"status={eq.admissibility_status} "
                f"refusal={eq.refusal_reason} "
                f"span={eq.source_span.to_canonical_string()}"
            )
        for unk in self.unknowns:
            if isinstance(unk.state_index, Operation):
                state_token = f"op({unk.state_index.operation_index})"
            else:
                state_token = unk.state_index
            lines.append(
                f"U {unk.symbol_id} expected_unit={unk.expected_unit} "
                f"state={state_token} form={unk.question_form} "
                f"qspan={unk.question_span.to_canonical_string()}"
            )
        for con in self.constraints:
            lines.append(
                f"C {con.symbol_id} pred={con.predicate} "
                f"span={con.source_span.to_canonical_string()}"
            )
        for span in self.provenance:
            lines.append(f"P {span.to_canonical_string()} text={span.text}")
        return "\n".join(lines)
