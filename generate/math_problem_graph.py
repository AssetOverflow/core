"""ADR-0115 — Typed proposition graph for grade-school math word problems.

This module defines the structural target of the parser added under ADR-0115.
Parsing a natural-language problem produces a :class:`MathProblemGraph`; the
solver (ADR-0116) and verifier (ADR-0117) consume the same structure.

Determinism guarantees:

- Every dataclass is ``frozen=True, slots=True`` and hashes by value.
- :meth:`MathProblemGraph.canonical_bytes` is sorted-keys, compact-separators
  JSON — same graph object → byte-identical SHA-256.
- Field order on ``entities``, ``initial_state``, ``operations`` is
  **order-of-introduction** in the source text. Two graphs that disagree on
  introduction order are NOT equal; this matches CORE's general "preserve
  source-text ordering" doctrine.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Final, Mapping


# Operation kinds correspond to math-pack lemma vocabulary (en_mathematics_logic_v1).
# A future solver under ADR-0116 dispatches on this string.
VALID_OPERATION_KINDS: Final[frozenset[str]] = frozenset(
    {"add", "subtract", "transfer", "multiply", "divide", "apply_rate"}
)


class MathGraphError(ValueError):
    """Raised on schema violations in math-problem-graph construction."""


@dataclass(frozen=True, slots=True)
class Quantity:
    """A numeric value paired with a textual unit.

    The unit is the canonical noun (lowercase). Equality is exact:
    ``Quantity(5, 'apples')`` != ``Quantity(5, 'apple')``. Authors and
    parsers must canonicalize units before constructing.
    """

    value: int | float
    unit: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, (int, float)) or isinstance(self.value, bool):
            raise MathGraphError(
                f"Quantity.value must be int or float, got "
                f"{type(self.value).__name__}"
            )
        if not isinstance(self.unit, str) or not self.unit:
            raise MathGraphError(
                f"Quantity.unit must be a non-empty string, got {self.unit!r}"
            )

    def as_json(self) -> dict[str, Any]:
        return {"unit": self.unit, "value": self.value}


@dataclass(frozen=True, slots=True)
class Rate:
    """A per-unit rate connecting two units (ADR-0122).

    ``Rate(2.0, "dollars", "apple")`` means "2 dollars per apple". The
    rate consumes a quantity in ``denominator_unit`` and produces a
    quantity in ``numerator_unit`` via scalar multiplication. ``value``
    must be strictly positive — zero or negative rates are refused at
    construction (illegal states made hard to represent).
    """

    value: int | float
    numerator_unit: str
    denominator_unit: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, (int, float)) or isinstance(self.value, bool):
            raise MathGraphError(
                f"Rate.value must be int or float, got "
                f"{type(self.value).__name__}"
            )
        if self.value <= 0:
            raise MathGraphError(
                f"Rate.value must be strictly positive; got {self.value!r}"
            )
        if not isinstance(self.numerator_unit, str) or not self.numerator_unit:
            raise MathGraphError(
                f"Rate.numerator_unit must be a non-empty string, got "
                f"{self.numerator_unit!r}"
            )
        if not isinstance(self.denominator_unit, str) or not self.denominator_unit:
            raise MathGraphError(
                f"Rate.denominator_unit must be a non-empty string, got "
                f"{self.denominator_unit!r}"
            )
        if self.numerator_unit == self.denominator_unit:
            raise MathGraphError(
                f"Rate.numerator_unit and Rate.denominator_unit must differ; "
                f"got {self.numerator_unit!r} for both"
            )

    def as_json(self) -> dict[str, Any]:
        return {
            "denominator_unit": self.denominator_unit,
            "numerator_unit": self.numerator_unit,
            "value": self.value,
        }


@dataclass(frozen=True, slots=True)
class InitialPossession:
    """Some entity holds some quantity at the start of the problem."""

    entity: str
    quantity: Quantity

    def __post_init__(self) -> None:
        if not isinstance(self.entity, str) or not self.entity:
            raise MathGraphError(
                "InitialPossession.entity must be a non-empty string"
            )

    def as_json(self) -> dict[str, Any]:
        return {"entity": self.entity, "quantity": self.quantity.as_json()}


@dataclass(frozen=True, slots=True)
class Operation:
    """A state-mutating event applied in story order.

    ``transfer`` denotes ``actor → target`` movement of ``operand``. The
    solver (ADR-0116) decomposes ``transfer`` into ``subtract`` from actor
    plus ``add`` to target; the parser emits ``transfer`` to stay close to
    natural-language surface ("gives X to Y").

    For ``multiply`` / ``divide`` the ``operand`` is the scalar (e.g. a
    factor of 3). Unit handling for these kinds is delegated to the solver.
    """

    actor: str
    kind: str
    operand: Quantity | Rate
    target: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.actor, str) or not self.actor:
            raise MathGraphError("Operation.actor must be a non-empty string")
        if self.kind not in VALID_OPERATION_KINDS:
            raise MathGraphError(
                f"Operation.kind must be one of {sorted(VALID_OPERATION_KINDS)}, "
                f"got {self.kind!r}"
            )
        if self.kind == "apply_rate":
            if not isinstance(self.operand, Rate):
                raise MathGraphError(
                    "Operation.operand must be a Rate when kind='apply_rate'; "
                    f"got {type(self.operand).__name__}"
                )
        else:
            if not isinstance(self.operand, Quantity):
                raise MathGraphError(
                    "Operation.operand must be a Quantity when "
                    f"kind={self.kind!r}; got {type(self.operand).__name__}"
                )
        if self.kind == "transfer":
            if not self.target:
                raise MathGraphError(
                    "Operation.target required when kind='transfer'"
                )
            if self.target == self.actor:
                raise MathGraphError(
                    "Operation.target must differ from Operation.actor for "
                    "kind='transfer'"
                )
        elif self.target is not None:
            raise MathGraphError(
                f"Operation.target only valid for kind='transfer'; got "
                f"kind={self.kind!r}"
            )

    def as_json(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "actor": self.actor,
            "kind": self.kind,
            "operand": self.operand.as_json(),
        }
        if self.target is not None:
            d["target"] = self.target
        return d


@dataclass(frozen=True, slots=True)
class Unknown:
    """The quantity the question is asking for.

    ``entity=None`` means "total across every entity holding ``unit``"
    (e.g. "How many apples do they have in total?"). For a single-entity
    question ("How many apples does Sam have?") set ``entity='Sam'``.
    """

    entity: str | None
    unit: str

    def __post_init__(self) -> None:
        if not isinstance(self.unit, str) or not self.unit:
            raise MathGraphError("Unknown.unit must be a non-empty string")
        if self.entity is not None and (
            not isinstance(self.entity, str) or not self.entity
        ):
            raise MathGraphError(
                "Unknown.entity must be a non-empty string or None"
            )

    def as_json(self) -> dict[str, Any]:
        return {"entity": self.entity, "unit": self.unit}


@dataclass(frozen=True, slots=True)
class MathProblemGraph:
    """Typed graph produced by the ADR-0115 parser.

    Field order on tuples is **order of introduction in the source text**,
    not alphabetical. ``MathProblemGraph`` equality is element-wise tuple
    equality; reordering changes the graph identity.
    """

    entities: tuple[str, ...]
    initial_state: tuple[InitialPossession, ...]
    operations: tuple[Operation, ...]
    unknown: Unknown

    def __post_init__(self) -> None:
        if not self.entities:
            raise MathGraphError(
                "MathProblemGraph.entities must contain at least one entity"
            )
        seen: set[str] = set()
        for e in self.entities:
            if not isinstance(e, str) or not e:
                raise MathGraphError(
                    "MathProblemGraph.entities must be non-empty strings"
                )
            if e in seen:
                raise MathGraphError(
                    f"MathProblemGraph.entities contains duplicate {e!r}"
                )
            seen.add(e)
        entity_set = set(self.entities)
        for p in self.initial_state:
            if p.entity not in entity_set:
                raise MathGraphError(
                    f"initial_state references unknown entity {p.entity!r}"
                )
        for op in self.operations:
            if op.actor not in entity_set:
                raise MathGraphError(
                    f"operation references unknown actor {op.actor!r}"
                )
            if op.target is not None and op.target not in entity_set:
                raise MathGraphError(
                    f"operation references unknown target {op.target!r}"
                )
        if self.unknown.entity is not None and self.unknown.entity not in entity_set:
            raise MathGraphError(
                f"unknown references unknown entity {self.unknown.entity!r}"
            )

    def as_json(self) -> dict[str, Any]:
        return {
            "entities": list(self.entities),
            "initial_state": [p.as_json() for p in self.initial_state],
            "operations": [o.as_json() for o in self.operations],
            "unknown": self.unknown.as_json(),
        }

    def canonical_bytes(self) -> bytes:
        """Deterministic JSON for hashing/byte-equality comparison."""
        return json.dumps(
            self.as_json(), sort_keys=True, separators=(",", ":")
        ).encode("utf-8")


def graph_from_dict(d: Mapping[str, Any]) -> MathProblemGraph:
    """Deserialize a graph from its canonical JSON dict.

    The reverse of :meth:`MathProblemGraph.as_json`. Raises
    :class:`MathGraphError` on any schema violation surfaced by the
    dataclass constructors.
    """
    if not isinstance(d, Mapping):
        raise MathGraphError(f"graph payload must be a mapping; got {type(d).__name__}")
    for required in ("entities", "initial_state", "operations", "unknown"):
        if required not in d:
            raise MathGraphError(f"graph payload missing required field {required!r}")

    entities = tuple(d["entities"])
    initial_state = tuple(
        InitialPossession(
            entity=p["entity"],
            quantity=Quantity(value=p["quantity"]["value"], unit=p["quantity"]["unit"]),
        )
        for p in d["initial_state"]
    )
    operations = tuple(
        Operation(
            actor=o["actor"],
            kind=o["kind"],
            operand=_operand_from_dict(o["kind"], o["operand"]),
            target=o.get("target"),
        )
        for o in d["operations"]
    )
    unk = d["unknown"]
    unknown = Unknown(entity=unk.get("entity"), unit=unk["unit"])
    return MathProblemGraph(
        entities=entities,
        initial_state=initial_state,
        operations=operations,
        unknown=unknown,
    )


def _operand_from_dict(kind: str, operand: Mapping[str, Any]) -> Quantity | Rate:
    """Reconstruct an Operation.operand from its canonical JSON form.

    Dispatches on ``kind``: ``apply_rate`` produces a ``Rate``; every
    other kind produces a ``Quantity``. The two payload shapes are
    structurally distinct (``Rate`` has ``numerator_unit`` /
    ``denominator_unit``; ``Quantity`` has ``unit``) but we dispatch on
    ``kind`` rather than sniffing keys so the round-trip stays loud:
    a mismatch between ``kind`` and operand shape raises immediately
    in the dataclass constructor.
    """
    if not isinstance(operand, Mapping):
        raise MathGraphError(
            f"Operation.operand must be a mapping; got {type(operand).__name__}"
        )
    if kind == "apply_rate":
        return Rate(
            value=operand["value"],
            numerator_unit=operand["numerator_unit"],
            denominator_unit=operand["denominator_unit"],
        )
    return Quantity(value=operand["value"], unit=operand["unit"])
