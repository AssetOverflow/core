"""ADR-0164 — immutable partial-comprehension state skeleton.

This module defines the typed state container the incremental
comprehension reader will accumulate. It is intentionally pure data:
frozen dataclasses, refusal-first validation, and canonical-bytes
serialization for deterministic replay and trace hashing.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Final, Literal

VALID_GENDERS: Final[frozenset[str]] = frozenset(
    {"female", "male", "neuter", "unknown"}
)

VALID_QUESTION_KINDS: Final[frozenset[str]] = frozenset(
    {"continuous_quantity", "discrete_quantity", "difference", "aggregate"}
)

VALID_EXPECTATION_KINDS: Final[frozenset[str]] = frozenset(
    {
        "accumulation_verb",
        "depletion_verb",
        "transfer_verb",
        "residual_modifier",
        "aggregate_modifier",
        "state_continuation_verb",
        "unit_noun",
        "entity",
        "quantity",
    }
)


class ComprehensionStateError(ValueError):
    """Raised on invalid comprehension-state construction."""


def _require_non_empty_str(value: object, field_name: str) -> None:
    if not isinstance(value, str) or value == "":
        raise ComprehensionStateError(
            f"{field_name} must be a non-empty str; got {value!r}"
        )


def _require_optional_str(value: object, field_name: str) -> None:
    if value is not None and (not isinstance(value, str) or value == ""):
        raise ComprehensionStateError(
            f"{field_name} must be None or a non-empty str; got {value!r}"
        )


def _require_int(value: object, field_name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ComprehensionStateError(
            f"{field_name} must be int; got {type(value).__name__}"
        )


def _require_non_negative_int(value: object, field_name: str) -> None:
    _require_int(value, field_name)
    if value < 0:
        raise ComprehensionStateError(f"{field_name} must be >= 0; got {value}")


def _require_decimal(value: object, field_name: str) -> None:
    if not isinstance(value, Decimal):
        raise ComprehensionStateError(
            f"{field_name} must be Decimal; got {type(value).__name__}"
        )
    if not value.is_finite():
        raise ComprehensionStateError(
            f"{field_name} must be finite; got {value!r}"
        )


def _canonical_decimal(value: Decimal) -> str:
    normalized = value.normalize()
    if normalized == normalized.to_integral():
        return format(normalized.quantize(Decimal("1")), "f")
    return format(normalized, "f")


@dataclass(frozen=True, slots=True)
class EntityRef:
    canonical_name: str
    gender: Literal["female", "male", "neuter", "unknown"]
    first_mention_position: int

    def __post_init__(self) -> None:
        _require_non_empty_str(self.canonical_name, "EntityRef.canonical_name")
        if self.gender not in VALID_GENDERS:
            raise ComprehensionStateError(
                "EntityRef.gender must be one of "
                f"{sorted(VALID_GENDERS)}; got {self.gender!r}"
            )
        _require_non_negative_int(
            self.first_mention_position, "EntityRef.first_mention_position"
        )

    def as_canonical(self) -> dict[str, Any]:
        return {
            "canonical_name": self.canonical_name,
            "first_mention_position": self.first_mention_position,
            "gender": self.gender,
        }


@dataclass(frozen=True, slots=True)
class QuantityRef:
    value: Decimal
    unit: str | None
    unit_class: str | None
    owner_entity: str | None
    mention_position: int

    def __post_init__(self) -> None:
        _require_decimal(self.value, "QuantityRef.value")
        _require_optional_str(self.unit, "QuantityRef.unit")
        _require_optional_str(self.unit_class, "QuantityRef.unit_class")
        _require_optional_str(self.owner_entity, "QuantityRef.owner_entity")
        _require_non_negative_int(
            self.mention_position, "QuantityRef.mention_position"
        )
        if self.unit is None and self.unit_class is None:
            raise ComprehensionStateError(
                "QuantityRef.unit and QuantityRef.unit_class cannot both be None"
            )

    def as_canonical(self) -> dict[str, Any]:
        return {
            "mention_position": self.mention_position,
            "owner_entity": self.owner_entity,
            "unit": self.unit,
            "unit_class": self.unit_class,
            "value": _canonical_decimal(self.value),
        }


@dataclass(frozen=True, slots=True)
class PartialOp:
    operator_kind: str
    subject_entity: str | None
    object_entity: str | None
    quantity_index: int | None
    position: int

    def __post_init__(self) -> None:
        _require_non_empty_str(self.operator_kind, "PartialOp.operator_kind")
        _require_optional_str(self.subject_entity, "PartialOp.subject_entity")
        _require_optional_str(self.object_entity, "PartialOp.object_entity")
        if self.quantity_index is not None:
            _require_non_negative_int(self.quantity_index, "PartialOp.quantity_index")
        _require_non_negative_int(self.position, "PartialOp.position")

    def as_canonical(self) -> dict[str, Any]:
        return {
            "object_entity": self.object_entity,
            "operator_kind": self.operator_kind,
            "position": self.position,
            "quantity_index": self.quantity_index,
            "subject_entity": self.subject_entity,
        }


@dataclass(frozen=True, slots=True)
class QuestionTargetSlot:
    kind: Literal[
        "continuous_quantity",
        "discrete_quantity",
        "difference",
        "aggregate",
    ]
    entity: str | None
    unit_class: str | None
    position: int

    def __post_init__(self) -> None:
        if self.kind not in VALID_QUESTION_KINDS:
            raise ComprehensionStateError(
                "QuestionTargetSlot.kind must be one of "
                f"{sorted(VALID_QUESTION_KINDS)}; got {self.kind!r}"
            )
        _require_optional_str(self.entity, "QuestionTargetSlot.entity")
        _require_optional_str(self.unit_class, "QuestionTargetSlot.unit_class")
        _require_non_negative_int(self.position, "QuestionTargetSlot.position")

    def as_canonical(self) -> dict[str, Any]:
        return {
            "entity": self.entity,
            "kind": self.kind,
            "position": self.position,
            "unit_class": self.unit_class,
        }


@dataclass(frozen=True, slots=True)
class ExpectationFrame:
    allowed_categories: tuple[str, ...]
    reason: str

    def __post_init__(self) -> None:
        if not isinstance(self.allowed_categories, tuple):
            raise ComprehensionStateError(
                "ExpectationFrame.allowed_categories must be tuple[str, ...]"
            )
        if not self.allowed_categories:
            raise ComprehensionStateError(
                "ExpectationFrame.allowed_categories must not be empty"
            )
        for idx, category in enumerate(self.allowed_categories):
            if category not in VALID_EXPECTATION_KINDS:
                raise ComprehensionStateError(
                    "ExpectationFrame.allowed_categories must contain only "
                    f"{sorted(VALID_EXPECTATION_KINDS)}; got "
                    f"{category!r} at index {idx}"
                )
        _require_non_empty_str(self.reason, "ExpectationFrame.reason")

    def as_canonical(self) -> dict[str, Any]:
        return {
            "allowed_categories": list(self.allowed_categories),
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class ComprehensionState:
    entities: tuple[EntityRef, ...]
    quantities: tuple[QuantityRef, ...]
    operations: tuple[PartialOp, ...]
    question_target: QuestionTargetSlot | None = None
    expectation: ExpectationFrame | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.entities, tuple):
            raise ComprehensionStateError(
                "ComprehensionState.entities must be tuple[EntityRef, ...]"
            )
        if not isinstance(self.quantities, tuple):
            raise ComprehensionStateError(
                "ComprehensionState.quantities must be tuple[QuantityRef, ...]"
            )
        if not isinstance(self.operations, tuple):
            raise ComprehensionStateError(
                "ComprehensionState.operations must be tuple[PartialOp, ...]"
            )
        for idx, entity in enumerate(self.entities):
            if not isinstance(entity, EntityRef):
                raise ComprehensionStateError(
                    f"ComprehensionState.entities[{idx}] must be EntityRef; "
                    f"got {type(entity).__name__}"
                )
        for idx, quantity in enumerate(self.quantities):
            if not isinstance(quantity, QuantityRef):
                raise ComprehensionStateError(
                    f"ComprehensionState.quantities[{idx}] must be QuantityRef; "
                    f"got {type(quantity).__name__}"
                )
        for idx, operation in enumerate(self.operations):
            if not isinstance(operation, PartialOp):
                raise ComprehensionStateError(
                    f"ComprehensionState.operations[{idx}] must be PartialOp; "
                    f"got {type(operation).__name__}"
                )
        if self.question_target is not None and not isinstance(
            self.question_target, QuestionTargetSlot
        ):
            raise ComprehensionStateError(
                "ComprehensionState.question_target must be "
                f"QuestionTargetSlot | None; got {type(self.question_target).__name__}"
            )
        if self.expectation is not None and not isinstance(
            self.expectation, ExpectationFrame
        ):
            raise ComprehensionStateError(
                "ComprehensionState.expectation must be "
                f"ExpectationFrame | None; got {type(self.expectation).__name__}"
            )

    def as_canonical(self) -> dict[str, Any]:
        return {
            "entities": [entity.as_canonical() for entity in self.entities],
            "expectation": (
                self.expectation.as_canonical()
                if self.expectation is not None
                else None
            ),
            "operations": [
                operation.as_canonical() for operation in self.operations
            ],
            "quantities": [
                quantity.as_canonical() for quantity in self.quantities
            ],
            "question_target": (
                self.question_target.as_canonical()
                if self.question_target is not None
                else None
            ),
        }

    def canonical_bytes(self) -> bytes:
        return json.dumps(
            self.as_canonical(),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")

    def canonical_hash(self) -> str:
        return hashlib.sha256(self.canonical_bytes()).hexdigest()

