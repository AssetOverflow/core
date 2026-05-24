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
    }
)

VALID_COMPARISON_DIRECTIONS: Final[frozenset[str]] = frozenset(
    {"more", "fewer", "times", "fraction"}
)

VALID_TARGET_AGGREGATIONS: Final[frozenset[str]] = frozenset(
    {"single", "sum", "difference", "multiplicative_total"}
)


class MathGraphError(ValueError):
    """Raised on schema violations in math-problem-graph construction."""


@dataclass(frozen=True, slots=True)
class Quantity:
    value: int | float
    unit: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, (int, float)) or isinstance(self.value, bool):
            raise MathGraphError(f"Quantity.value must be int or float, got {type(self.value).__name__}")
        if not isinstance(self.unit, str) or not self.unit:
            raise MathGraphError(f"Quantity.unit must be a non-empty string, got {self.unit!r}")

    def as_json(self) -> dict[str, Any]:
        return {"unit": self.unit, "value": self.value}


@dataclass(frozen=True, slots=True)
class Rate:
    value: int | float
    numerator_unit: str
    denominator_unit: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, (int, float)) or isinstance(self.value, bool):
            raise MathGraphError(f"Rate.value must be int or float, got {type(self.value).__name__}")
        if self.value <= 0:
            raise MathGraphError(f"Rate.value must be strictly positive; got {self.value!r}")
        if not isinstance(self.numerator_unit, str) or not self.numerator_unit:
            raise MathGraphError(f"Rate.numerator_unit must be a non-empty string, got {self.numerator_unit!r}")
        if not isinstance(self.denominator_unit, str) or not self.denominator_unit:
            raise MathGraphError(f"Rate.denominator_unit must be a non-empty string, got {self.denominator_unit!r}")
        if self.numerator_unit == self.denominator_unit:
            raise MathGraphError(f"Rate.numerator_unit and Rate.denominator_unit must differ; got {self.numerator_unit!r} for both")

    def as_json(self) -> dict[str, Any]:
        return {"denominator_unit": self.denominator_unit, "numerator_unit": self.numerator_unit, "value": self.value}


@dataclass(frozen=True, slots=True)
class Comparison:
    reference_actor: str
    delta: "Quantity | None"
    factor: float | None
    direction: Literal["more", "fewer", "times", "fraction"]

    def __post_init__(self) -> None:
        if not isinstance(self.reference_actor, str) or not self.reference_actor:
            raise MathGraphError("Comparison.reference_actor must be a non-empty string")
        if self.direction not in VALID_COMPARISON_DIRECTIONS:
            raise MathGraphError(f"Comparison.direction must be one of {sorted(VALID_COMPARISON_DIRECTIONS)}; got {self.direction!r}")
        if self.direction in ("more", "fewer"):
            if not isinstance(self.delta, Quantity):
                raise MathGraphError(f"Comparison.delta must be a Quantity when direction={self.direction!r}; got {type(self.delta).__name__}")
            if self.factor is not None:
                raise MathGraphError(f"Comparison.factor must be None when direction={self.direction!r}; got {self.factor!r}")
        else:
            if self.delta is not None:
                raise MathGraphError(f"Comparison.delta must be None when direction={self.direction!r}; got {self.delta!r}")
            if not isinstance(self.factor, (int, float)) or isinstance(self.factor, bool):
                raise MathGraphError(f"Comparison.factor must be int or float when direction={self.direction!r}; got {type(self.factor).__name__}")
            if self.factor <= 0:
                raise MathGraphError(f"Comparison.factor must be strictly positive; got {self.factor!r}")

    def as_json(self) -> dict[str, Any]:
        d: dict[str, Any] = {"direction": self.direction, "reference_actor": self.reference_actor}
        if self.delta is not None:
            d["delta"] = self.delta.as_json()
        if self.factor is not None:
            d["factor"] = self.factor
        return d


@dataclass(frozen=True, slots=True)
class InitialPossession:
    entity: str
    quantity: Quantity

    def __post_init__(self) -> None:
        if not isinstance(self.entity, str) or not self.entity:
            raise MathGraphError("InitialPossession.entity must be a non-empty string")

    def as_json(self) -> dict[str, Any]:
        return {"entity": self.entity, "quantity": self.quantity.as_json()}


@dataclass(frozen=True, slots=True)
class Operation:
    actor: str
    kind: str
    operand: "Quantity | Rate | Comparison"
    target: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.actor, str) or not self.actor:
            raise MathGraphError("Operation.actor must be a non-empty string")
        if self.kind not in VALID_OPERATION_KINDS:
            raise MathGraphError(f"Operation.kind must be one of {sorted(VALID_OPERATION_KINDS)}, got {self.kind!r}")
        if self.kind == "apply_rate":
            if not isinstance(self.operand, Rate):
                raise MathGraphError(f"Operation.operand must be a Rate when kind='apply_rate'; got {type(self.operand).__name__}")
        elif self.kind in ("compare_additive", "compare_multiplicative"):
            if not isinstance(self.operand, Comparison):
                raise MathGraphError(f"Operation.operand must be a Comparison when kind={self.kind!r}; got {type(self.operand).__name__}")
            if self.kind == "compare_additive" and self.operand.direction not in ("more", "fewer"):
                raise MathGraphError(f"Operation.kind='compare_additive' requires Comparison.direction in {{'more','fewer'}}; got {self.operand.direction!r}")
            if self.kind == "compare_multiplicative" and self.operand.direction not in ("times", "fraction"):
                raise MathGraphError(f"Operation.kind='compare_multiplicative' requires Comparison.direction in {{'times','fraction'}}; got {self.operand.direction!r}")
            if self.operand.reference_actor == self.actor:
                raise MathGraphError(f"Operation.operand.reference_actor must differ from Operation.actor; both are {self.actor!r}")
        else:
            if not isinstance(self.operand, Quantity):
                raise MathGraphError(f"Operation.operand must be a Quantity when kind={self.kind!r}; got {type(self.operand).__name__}")
        if self.kind == "transfer":
            if not self.target:
                raise MathGraphError("Operation.target required when kind='transfer'")
            if self.target == self.actor:
                raise MathGraphError("Operation.target must differ from Operation.actor for kind='transfer'")
        elif self.target is not None:
            raise MathGraphError(f"Operation.target only valid for kind='transfer'; got kind={self.kind!r}")

    def as_json(self) -> dict[str, Any]:
        d: dict[str, Any] = {"actor": self.actor, "kind": self.kind, "operand": self.operand.as_json()}
        if self.target is not None:
            d["target"] = self.target
        return d


@dataclass(frozen=True, slots=True)
class Unknown:
    entity: str | None
    unit: str

    def __post_init__(self) -> None:
        if not isinstance(self.unit, str) or not self.unit:
            raise MathGraphError("Unknown.unit must be a non-empty string")
        if self.entity is not None and (not isinstance(self.entity, str) or not self.entity):
            raise MathGraphError("Unknown.entity must be a non-empty string or None")

    def as_json(self) -> dict[str, Any]:
        return {"entity": self.entity, "unit": self.unit}


@dataclass(frozen=True, slots=True)
class TargetBinding:
    """Question-target binding substrate for ADR-G5.

    This does not replace ``Unknown`` yet. It records how a question's
    requested quantity is intended to bind against the graph: a single
    entity/unit, a sum over entities, a difference target, or a future
    multiplicative total. Solver semantics remain unchanged until the
    G.5 implementation lane explicitly consumes this node.
    """

    entity_scope: tuple[str, ...]
    unit: str
    aggregation_kind: Literal["single", "sum", "difference", "multiplicative_total"]
    provenance_edges: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.aggregation_kind not in VALID_TARGET_AGGREGATIONS:
            raise MathGraphError(f"TargetBinding.aggregation_kind must be one of {sorted(VALID_TARGET_AGGREGATIONS)}; got {self.aggregation_kind!r}")
        if not isinstance(self.unit, str) or not self.unit:
            raise MathGraphError("TargetBinding.unit must be a non-empty string")
        if not isinstance(self.entity_scope, tuple):
            raise MathGraphError("TargetBinding.entity_scope must be a tuple")
        if self.aggregation_kind == "single" and len(self.entity_scope) != 1:
            raise MathGraphError("TargetBinding single aggregation requires exactly one entity")
        if self.aggregation_kind in ("sum", "difference", "multiplicative_total") and not self.entity_scope:
            raise MathGraphError(f"TargetBinding {self.aggregation_kind!r} aggregation requires at least one entity")
        seen: set[str] = set()
        for entity in self.entity_scope:
            if not isinstance(entity, str) or not entity:
                raise MathGraphError("TargetBinding.entity_scope entries must be non-empty strings")
            if entity in seen:
                raise MathGraphError(f"TargetBinding.entity_scope contains duplicate {entity!r}")
            seen.add(entity)
        if not isinstance(self.provenance_edges, tuple):
            raise MathGraphError("TargetBinding.provenance_edges must be a tuple")
        for edge in self.provenance_edges:
            if not isinstance(edge, str) or not edge:
                raise MathGraphError("TargetBinding.provenance_edges entries must be non-empty strings")

    def as_json(self) -> dict[str, Any]:
        return {
            "aggregation_kind": self.aggregation_kind,
            "entity_scope": list(self.entity_scope),
            "provenance_edges": list(self.provenance_edges),
            "unit": self.unit,
        }


@dataclass(frozen=True, slots=True)
class MathProblemGraph:
    entities: tuple[str, ...]
    initial_state: tuple[InitialPossession, ...]
    operations: tuple[Operation, ...]
    unknown: Unknown
    target_binding: TargetBinding | None = None

    def __post_init__(self) -> None:
        if not self.entities:
            raise MathGraphError("MathProblemGraph.entities must contain at least one entity")
        seen: set[str] = set()
        for e in self.entities:
            if not isinstance(e, str) or not e:
                raise MathGraphError("MathProblemGraph.entities must be non-empty strings")
            if e in seen:
                raise MathGraphError(f"MathProblemGraph.entities contains duplicate {e!r}")
            seen.add(e)
        entity_set = set(self.entities)
        for p in self.initial_state:
            if p.entity not in entity_set:
                raise MathGraphError(f"initial_state references unknown entity {p.entity!r}")
        for op in self.operations:
            if op.actor not in entity_set:
                raise MathGraphError(f"operation references unknown actor {op.actor!r}")
            if op.target is not None and op.target not in entity_set:
                raise MathGraphError(f"operation references unknown target {op.target!r}")
            if isinstance(op.operand, Comparison) and op.operand.reference_actor not in entity_set:
                raise MathGraphError(f"operation Comparison references unknown reference_actor {op.operand.reference_actor!r}")
        if self.unknown.entity is not None and self.unknown.entity not in entity_set:
            raise MathGraphError(f"unknown references unknown entity {self.unknown.entity!r}")
        if self.target_binding is not None:
            for entity in self.target_binding.entity_scope:
                if entity not in entity_set:
                    raise MathGraphError(f"target_binding references unknown entity {entity!r}")
            if self.target_binding.aggregation_kind == "single":
                expected_entity = self.target_binding.entity_scope[0]
                if self.unknown.entity not in (None, expected_entity):
                    raise MathGraphError("target_binding single scope conflicts with unknown.entity")
            if self.target_binding.unit != self.unknown.unit:
                raise MathGraphError("target_binding unit conflicts with unknown.unit")

    def as_json(self) -> dict[str, Any]:
        payload = {
            "entities": list(self.entities),
            "initial_state": [p.as_json() for p in self.initial_state],
            "operations": [o.as_json() for o in self.operations],
            "unknown": self.unknown.as_json(),
        }
        if self.target_binding is not None:
            payload["target_binding"] = self.target_binding.as_json()
        return payload

    def canonical_bytes(self) -> bytes:
        return json.dumps(self.as_json(), sort_keys=True, separators=(",", ":")).encode("utf-8")


def graph_from_dict(d: Mapping[str, Any]) -> MathProblemGraph:
    if not isinstance(d, Mapping):
        raise MathGraphError(f"graph payload must be a mapping; got {type(d).__name__}")
    for required in ("entities", "initial_state", "operations", "unknown"):
        if required not in d:
            raise MathGraphError(f"graph payload missing required field {required!r}")

    entities = tuple(d["entities"])
    initial_state = tuple(
        InitialPossession(entity=p["entity"], quantity=Quantity(value=p["quantity"]["value"], unit=p["quantity"]["unit"]))
        for p in d["initial_state"]
    )
    operations = tuple(
        Operation(actor=o["actor"], kind=o["kind"], operand=_operand_from_dict(o["kind"], o["operand"]), target=o.get("target"))
        for o in d["operations"]
    )
    unk = d["unknown"]
    unknown = Unknown(entity=unk.get("entity"), unit=unk["unit"])
    target_payload = d.get("target_binding")
    target_binding = _target_binding_from_dict(target_payload) if target_payload is not None else None
    return MathProblemGraph(entities=entities, initial_state=initial_state, operations=operations, unknown=unknown, target_binding=target_binding)


def _target_binding_from_dict(payload: Mapping[str, Any]) -> TargetBinding:
    if not isinstance(payload, Mapping):
        raise MathGraphError(f"target_binding payload must be a mapping; got {type(payload).__name__}")
    return TargetBinding(
        entity_scope=tuple(payload["entity_scope"]),
        unit=payload["unit"],
        aggregation_kind=payload["aggregation_kind"],
        provenance_edges=tuple(payload.get("provenance_edges", ())),
    )


def _operand_from_dict(kind: str, operand: Mapping[str, Any]) -> "Quantity | Rate | Comparison":
    if not isinstance(operand, Mapping):
        raise MathGraphError(f"Operation.operand must be a mapping; got {type(operand).__name__}")
    if kind == "apply_rate":
        return Rate(value=operand["value"], numerator_unit=operand["numerator_unit"], denominator_unit=operand["denominator_unit"])
    if kind in ("compare_additive", "compare_multiplicative"):
        delta_payload = operand.get("delta")
        delta = Quantity(value=delta_payload["value"], unit=delta_payload["unit"]) if delta_payload is not None else None
        return Comparison(reference_actor=operand["reference_actor"], delta=delta, factor=operand.get("factor"), direction=operand["direction"])
    return Quantity(value=operand["value"], unit=operand["unit"])
