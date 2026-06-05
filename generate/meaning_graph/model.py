"""Frozen data model for the MeaningGraph — the general-meaning interlingua.

This module is the typed boundary between comprehended natural language and the
domain reasoners. Like ``generate.binding_graph.model`` it holds *only data* —
no parser, no solver, no algebra — and every dataclass is ``frozen=True,
slots=True`` with immutable ``tuple`` collections.

Refusal-first: invalid construction raises ``MeaningGraphError`` rather than
silently coercing. Neutral by design: imports nothing from ``algebra`` /
``field`` / ``numpy`` / the engine, so the structure is a fair meeting point for
two independent decodings (INV-26-style neutrality).

Distinct from the binding-graph in two deliberate ways:

  - it carries GENERAL meaning (entities + n-ary named relations), not
    quantities/equations;
  - it imposes **no acyclicity** constraint. A cycle in general relations
    ("A loves B, B loves A") is well-formed, not the circular *reasoning* the
    binding-graph's equation DAG forbids.
"""

from __future__ import annotations

from dataclasses import dataclass, field


class MeaningGraphError(ValueError):
    """Raised on invalid MeaningGraph construction; never silently coerces."""


def _require_non_empty_str(value: object, field_name: str) -> None:
    if not isinstance(value, str) or value == "":
        raise MeaningGraphError(f"{field_name} must be a non-empty str; got {value!r}")


def _require_identifier(value: object, field_name: str) -> None:
    _require_non_empty_str(value, field_name)
    assert isinstance(value, str)
    if not value.isidentifier():
        raise MeaningGraphError(
            f"{field_name} must be a Python identifier; got {value!r}"
        )


# --------------------------------------------------------------------------- #
# MeaningSpan — provenance
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class MeaningSpan:
    """An immutable pointer back to a ``[start, end)`` slice of the NL source.

    ``text`` is retained verbatim so downstream tooling can audit the span
    without re-reading the source document.
    """

    source_id: str
    start: int
    end: int
    text: str

    def __post_init__(self) -> None:
        _require_non_empty_str(self.source_id, "MeaningSpan.source_id")
        if not isinstance(self.start, int) or isinstance(self.start, bool):
            raise MeaningGraphError(f"MeaningSpan.start must be int; got {self.start!r}")
        if not isinstance(self.end, int) or isinstance(self.end, bool):
            raise MeaningGraphError(f"MeaningSpan.end must be int; got {self.end!r}")
        if self.start < 0:
            raise MeaningGraphError(f"MeaningSpan.start must be >= 0; got {self.start}")
        if self.end <= self.start:
            raise MeaningGraphError(
                f"MeaningSpan.end must be > start; got start={self.start}, end={self.end}"
            )
        _require_non_empty_str(self.text, "MeaningSpan.text")

    def to_canonical_string(self) -> str:
        return f"{self.source_id}[{self.start}:{self.end}]"


# --------------------------------------------------------------------------- #
# Entity
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class Entity:
    """A referent lifted from language: a stable id + surface name + provenance.

    ``entity_id`` is a Python identifier so relations can key it safely.
    ``kind`` is an optional, open free-text class hint (e.g. "person",
    "number"); it carries NO closed vocabulary yet (defer-substrate-vocab —
    a closed taxonomy is a deliberate later extension driven by a real use case).
    """

    entity_id: str
    name: str
    span: MeaningSpan
    kind: str | None = None

    def __post_init__(self) -> None:
        _require_identifier(self.entity_id, "Entity.entity_id")
        _require_non_empty_str(self.name, "Entity.name")
        if not isinstance(self.span, MeaningSpan):
            raise MeaningGraphError(
                f"Entity.span must be a MeaningSpan; got {type(self.span).__name__}"
            )
        if self.kind is not None and (not isinstance(self.kind, str) or self.kind == ""):
            raise MeaningGraphError(
                f"Entity.kind must be None or a non-empty str; got {self.kind!r}"
            )


# --------------------------------------------------------------------------- #
# Relation
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class Relation:
    """An n-ary named predicate over entity ids, with provenance and polarity.

    ``predicate`` is a free-text relation name (e.g. ``"mother_of"``); like
    ``Entity.kind`` it carries no closed vocabulary yet. ``arguments`` is the
    *ordered* tuple of entity ids the predicate relates (arity >= 1). ``negated``
    captures polarity ("A is NOT the mother of B") as first-class structure.
    """

    predicate: str
    arguments: tuple[str, ...]
    span: MeaningSpan
    negated: bool = False

    def __post_init__(self) -> None:
        _require_non_empty_str(self.predicate, "Relation.predicate")
        if not isinstance(self.arguments, tuple):
            raise MeaningGraphError(
                f"Relation.arguments must be a tuple; got {type(self.arguments).__name__}"
            )
        if len(self.arguments) == 0:
            raise MeaningGraphError("Relation.arguments must be non-empty (arity >= 1)")
        for arg in self.arguments:
            _require_identifier(arg, "Relation.arguments entry")
        if not isinstance(self.span, MeaningSpan):
            raise MeaningGraphError(
                f"Relation.span must be a MeaningSpan; got {type(self.span).__name__}"
            )
        if not isinstance(self.negated, bool):
            raise MeaningGraphError(
                f"Relation.negated must be a bool; got {self.negated!r}"
            )

    @property
    def arity(self) -> int:
        return len(self.arguments)


# --------------------------------------------------------------------------- #
# MeaningGraph
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class MeaningGraph:
    """Top-level immutable container of comprehended meaning.

    Cross-collection invariants enforced at construction:

      - ``entities`` carries unique ``entity_id`` values;
      - every ``Relation`` argument references a known entity.

    No acyclicity constraint (see module docstring). Collections are emitted in
    *given* order; the graph is identity-preserving by design.
    """

    entities: tuple[Entity, ...] = field(default_factory=tuple)
    relations: tuple[Relation, ...] = field(default_factory=tuple)
    provenance: tuple[MeaningSpan, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        for name, value, item_type in (
            ("entities", self.entities, Entity),
            ("relations", self.relations, Relation),
            ("provenance", self.provenance, MeaningSpan),
        ):
            if not isinstance(value, tuple):
                raise MeaningGraphError(
                    f"MeaningGraph.{name} must be a tuple; got {type(value).__name__}"
                )
            for item in value:
                if not isinstance(item, item_type):
                    raise MeaningGraphError(
                        f"MeaningGraph.{name} entries must be {item_type.__name__}; "
                        f"got {type(item).__name__}"
                    )

        known_ids: set[str] = set()
        for ent in self.entities:
            if ent.entity_id in known_ids:
                raise MeaningGraphError(
                    f"Duplicate Entity.entity_id: {ent.entity_id!r}"
                )
            known_ids.add(ent.entity_id)

        for rel in self.relations:
            for arg in rel.arguments:
                if arg not in known_ids:
                    raise MeaningGraphError(
                        f"Relation {rel.predicate!r} references unknown entity_id {arg!r}"
                    )

    def to_canonical_string(self) -> str:
        """Deterministic string serialization for stable hashing / replay."""
        lines: list[str] = []
        for ent in self.entities:
            lines.append(
                f"E {ent.entity_id} {ent.name} kind={ent.kind} "
                f"span={ent.span.to_canonical_string()}"
            )
        for rel in self.relations:
            args = ",".join(rel.arguments)
            polarity = "not " if rel.negated else ""
            lines.append(
                f"R {polarity}{rel.predicate}({args}) "
                f"span={rel.span.to_canonical_string()}"
            )
        for span in self.provenance:
            lines.append(f"P {span.to_canonical_string()} text={span.text}")
        return "\n".join(lines)
