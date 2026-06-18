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
from typing import Any, Final, Literal, Mapping


# Operation kinds correspond to math-pack lemma vocabulary (en_mathematics_logic_v1).
# A future solver under ADR-0116 dispatches on this string.
VALID_OPERATION_KINDS: Final[frozenset[str]] = frozenset(
    {
        "add",
        "subtract",
        "transfer",
        "multiply",
        "divide",
        "apply_rate",
        "compare_additive",
        "compare_multiplicative",
        "unit_partition",
    }
)


VALID_COMPARISON_DIRECTIONS: Final[frozenset[str]] = frozenset(
    {"more", "fewer", "times", "fraction"}
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
class PartitionChunk:
    """Fixed-size chunk measure for unit_partition (Gate A2a).

    ``PartitionChunk(25, "feet", "sections")`` means "split the actor's
    total in ``unit`` into chunks of size 25, writing the integer chunk
    count under ``result_unit``". ``value`` is the chunk size (divisor);
    ``unit`` is the measure unit shared with the prior total; ``result_unit``
    is the count noun for the quotient (not the dividend unit).
    """

    value: int | float
    unit: str
    result_unit: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, (int, float)) or isinstance(self.value, bool):
            raise MathGraphError(
                f"PartitionChunk.value must be int or float, got "
                f"{type(self.value).__name__}"
            )
        if self.value <= 0:
            raise MathGraphError(
                f"PartitionChunk.value must be strictly positive; got {self.value!r}"
            )
        if not isinstance(self.unit, str) or not self.unit:
            raise MathGraphError(
                f"PartitionChunk.unit must be a non-empty string, got {self.unit!r}"
            )
        if not isinstance(self.result_unit, str) or not self.result_unit:
            raise MathGraphError(
                f"PartitionChunk.result_unit must be a non-empty string, got "
                f"{self.result_unit!r}"
            )
        if self.unit == self.result_unit:
            raise MathGraphError(
                f"PartitionChunk.unit and PartitionChunk.result_unit must differ; "
                f"got {self.unit!r} for both"
            )

    def as_json(self) -> dict[str, Any]:
        return {
            "result_unit": self.result_unit,
            "unit": self.unit,
            "value": self.value,
        }


@dataclass(frozen=True, slots=True)
class Comparison:
    """A comparison between two actors' quantities (ADR-0123).

    Two modes, discriminated by ``direction``:

    - ``direction='more'`` / ``direction='fewer'``: additive — actor's
      quantity is ``reference_actor``'s quantity ± ``delta`` (Quantity).
      ``factor`` must be ``None``.
    - ``direction='times'`` / ``direction='fraction'``: multiplicative —
      actor's quantity is ``factor`` × ``reference_actor``'s quantity.
      ``delta`` must be ``None``. ``factor`` must be strictly positive.

    Self-reference is refused at the Operation boundary, not here.
    """

    reference_actor: str
    delta: "Quantity | None"
    factor: float | None
    direction: Literal["more", "fewer", "times", "fraction"]

    def __post_init__(self) -> None:
        if not isinstance(self.reference_actor, str) or not self.reference_actor:
            raise MathGraphError(
                "Comparison.reference_actor must be a non-empty string"
            )
        if self.direction not in VALID_COMPARISON_DIRECTIONS:
            raise MathGraphError(
                f"Comparison.direction must be one of "
                f"{sorted(VALID_COMPARISON_DIRECTIONS)}; got {self.direction!r}"
            )
        if self.direction in ("more", "fewer"):
            if not isinstance(self.delta, Quantity):
                raise MathGraphError(
                    "Comparison.delta must be a Quantity when "
                    f"direction={self.direction!r}; got "
                    f"{type(self.delta).__name__}"
                )
            if self.factor is not None:
                raise MathGraphError(
                    "Comparison.factor must be None when "
                    f"direction={self.direction!r}; got {self.factor!r}"
                )
        else:
            if self.delta is not None:
                raise MathGraphError(
                    "Comparison.delta must be None when "
                    f"direction={self.direction!r}; got {self.delta!r}"
                )
            if not isinstance(self.factor, (int, float)) or isinstance(
                self.factor, bool
            ):
                raise MathGraphError(
                    "Comparison.factor must be int or float when "
                    f"direction={self.direction!r}; got "
                    f"{type(self.factor).__name__}"
                )
            if self.factor <= 0:
                raise MathGraphError(
                    f"Comparison.factor must be strictly positive; "
                    f"got {self.factor!r}"
                )

    def as_json(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "direction": self.direction,
            "reference_actor": self.reference_actor,
        }
        if self.delta is not None:
            d["delta"] = self.delta.as_json()
        if self.factor is not None:
            d["factor"] = self.factor
        return d


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
    operand: "Quantity | Rate | Comparison | PartitionChunk"
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
        elif self.kind == "unit_partition":
            if not isinstance(self.operand, PartitionChunk):
                raise MathGraphError(
                    "Operation.operand must be a PartitionChunk when "
                    f"kind='unit_partition'; got {type(self.operand).__name__}"
                )
        elif self.kind in ("compare_additive", "compare_multiplicative"):
            if not isinstance(self.operand, Comparison):
                raise MathGraphError(
                    "Operation.operand must be a Comparison when "
                    f"kind={self.kind!r}; got {type(self.operand).__name__}"
                )
            if self.kind == "compare_additive" and self.operand.direction not in (
                "more",
                "fewer",
            ):
                raise MathGraphError(
                    "Operation.kind='compare_additive' requires "
                    "Comparison.direction in {'more','fewer'}; got "
                    f"{self.operand.direction!r}"
                )
            if self.kind == "compare_multiplicative" and self.operand.direction not in (
                "times",
                "fraction",
            ):
                raise MathGraphError(
                    "Operation.kind='compare_multiplicative' requires "
                    "Comparison.direction in {'times','fraction'}; got "
                    f"{self.operand.direction!r}"
                )
            if self.operand.reference_actor == self.actor:
                raise MathGraphError(
                    "Operation.operand.reference_actor must differ from "
                    f"Operation.actor; both are {self.actor!r}"
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
        # ADR-0174 Phase 3 diagnostic — refuse contradictory initial
        # possessions for the same (entity, unit). Surfaced 2026-05-28
        # by post-merge diagnostic: prior behavior silently overwrote
        # earlier with later in math_solver.solve()'s state dict, so
        # 'Sam has 5 marbles. Sam has 3 marbles.' returned 3.0 — a
        # wrong=0 violation (definite answer from contradictory input).
        # Refuse at construction; admit duplicates only when the value
        # matches (redundant but not contradictory).
        seen_initial: dict[tuple[str, str], int | float] = {}
        for p in self.initial_state:
            if p.entity not in entity_set:
                raise MathGraphError(
                    f"initial_state references unknown entity {p.entity!r}"
                )
            key = (p.entity, p.quantity.unit)
            if key in seen_initial and seen_initial[key] != p.quantity.value:
                raise MathGraphError(
                    f"initial_state contains contradictory possessions for "
                    f"({p.entity!r}, {p.quantity.unit!r}): "
                    f"{seen_initial[key]} vs {p.quantity.value}"
                )
            seen_initial[key] = p.quantity.value
        for op in self.operations:
            if op.actor not in entity_set:
                raise MathGraphError(
                    f"operation references unknown actor {op.actor!r}"
                )
            if op.target is not None and op.target not in entity_set:
                raise MathGraphError(
                    f"operation references unknown target {op.target!r}"
                )
            if isinstance(op.operand, Comparison):
                if op.operand.reference_actor not in entity_set:
                    raise MathGraphError(
                        "operation Comparison references unknown "
                        f"reference_actor {op.operand.reference_actor!r}"
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


def _operand_from_dict(
    kind: str, operand: Mapping[str, Any]
) -> "Quantity | Rate | Comparison | PartitionChunk":
    """Reconstruct an Operation.operand from its canonical JSON form.

    Dispatches on ``kind``:

    - ``apply_rate`` → ``Rate`` (ADR-0122)
    - ``compare_additive`` / ``compare_multiplicative`` → ``Comparison`` (ADR-0123)
    - ``unit_partition`` → ``PartitionChunk`` (Gate A2a)
    - every other kind → ``Quantity``

    Payload shapes are structurally distinct (``Rate`` has
    ``numerator_unit``/``denominator_unit``; ``Comparison`` has
    ``reference_actor``/``direction``; ``Quantity`` has ``unit``) but
    we dispatch on ``kind`` rather than sniffing keys so a mismatch
    between ``kind`` and operand shape raises loudly in the dataclass
    constructor.
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
    if kind in ("compare_additive", "compare_multiplicative"):
        delta_payload = operand.get("delta")
        delta = (
            Quantity(value=delta_payload["value"], unit=delta_payload["unit"])
            if delta_payload is not None
            else None
        )
        return Comparison(
            reference_actor=operand["reference_actor"],
            delta=delta,
            factor=operand.get("factor"),
            direction=operand["direction"],
        )
    if kind == "unit_partition":
        return PartitionChunk(
            value=operand["value"],
            unit=operand["unit"],
            result_unit=operand["result_unit"],
        )
    return Quantity(value=operand["value"], unit=operand["unit"])
