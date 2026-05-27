"""ADR-0164 / ADR-0164.3 — two-level immutable comprehension-state types.

This module defines the typed state containers the incremental comprehension
reader accumulates. It is intentionally pure data: frozen dataclasses,
refusal-first validation, and canonical-bytes serialisation for deterministic
replay and trace hashing.

Two levels (ADR-0164.3 §Decision):
  - ``ProblemReadingState`` — outer, problem-scoped. Persists across sentence
    boundaries. Mutated only by ``end_sentence``.
  - ``SentenceReadingState`` — inner, sentence-scoped. Lifetime = one sentence.
    Created by ``begin_sentence``, mutated by ``apply_word``.

``ComprehensionState`` is a backward-compatibility alias for
``SentenceReadingState``; existing importers need not change.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Final, Literal

# ---------------------------------------------------------------------------
# Closed-set constants
# ---------------------------------------------------------------------------

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

VALID_SENTENCE_FRAME_KINDS: Final[frozenset[str]] = frozenset(
    {
        "initial_state_frame",
        "operation_frame",
        "question_frame",
        "descriptive_frame",
    }
)

# ADR-0164.3 §ReaderRefusal — closed, ADR-tracked.
# New reasons require an ADR amendment.
READER_REFUSAL_REASONS: Final[frozenset[str]] = frozenset(
    {
        # apply_word — token-level
        "unknown_word",
        "unexpected_category",
        "expectation_collision",
        "unresolved_pronoun",
        "ambiguous_pronoun_referent",
        # end_sentence — sentence-level
        "unfinished_frame",
        "unattached_quantity",
        "incomplete_operation",
        # finalization predicate — problem-level
        "no_question_target",
        "dangling_entity",
        "graph_construction_failure",
    }
)

# SentenceFrame is a Literal over the four discriminator values.
SentenceFrame = Literal[
    "initial_state_frame",
    "operation_frame",
    "question_frame",
    "descriptive_frame",
]

_LOOKBACK_MAX: Final[int] = 8

# ---------------------------------------------------------------------------
# Error
# ---------------------------------------------------------------------------


class ComprehensionStateError(ValueError):
    """Raised on invalid comprehension-state construction."""


# ---------------------------------------------------------------------------
# Internal validators (unchanged from #321)
# ---------------------------------------------------------------------------

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
    if value < 0:  # type: ignore[operator]
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


# ---------------------------------------------------------------------------
# Shared leaf types (unchanged from #321)
# ---------------------------------------------------------------------------

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
    unit: str | None = None

    def __post_init__(self) -> None:
        if self.kind not in VALID_QUESTION_KINDS:
            raise ComprehensionStateError(
                "QuestionTargetSlot.kind must be one of "
                f"{sorted(VALID_QUESTION_KINDS)}; got {self.kind!r}"
            )
        _require_optional_str(self.entity, "QuestionTargetSlot.entity")
        _require_optional_str(self.unit_class, "QuestionTargetSlot.unit_class")
        _require_non_negative_int(self.position, "QuestionTargetSlot.position")
        _require_optional_str(self.unit, "QuestionTargetSlot.unit")

    def as_canonical(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "entity": self.entity,
            "kind": self.kind,
            "position": self.position,
            "unit_class": self.unit_class,
        }
        if self.unit is not None:
            d["unit"] = self.unit
        return d


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


# ---------------------------------------------------------------------------
# New leaf types for SentenceReadingState (ADR-0164.3)
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class VerbReference:
    """The verb captured at frame-determining position, awaiting completion."""

    surface: str
    kind: str
    position: int

    def __post_init__(self) -> None:
        _require_non_empty_str(self.surface, "VerbReference.surface")
        _require_non_empty_str(self.kind, "VerbReference.kind")
        _require_non_negative_int(self.position, "VerbReference.position")

    def as_canonical(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "position": self.position,
            "surface": self.surface,
        }


@dataclass(frozen=True, slots=True)
class AppliedCategory:
    """One entry in the lookback window: a category applied at a position."""

    category: str
    position: int

    def __post_init__(self) -> None:
        _require_non_empty_str(self.category, "AppliedCategory.category")
        _require_non_negative_int(self.position, "AppliedCategory.position")

    def as_canonical(self) -> dict[str, Any]:
        return {"category": self.category, "position": self.position}


@dataclass(frozen=True, slots=True)
class FramePayload:
    """Stub container for the in-construction frame payload.

    The reader (Brief 5 Phase 1) populates sub-fields specific to each
    frame kind. This stub carries only the frame_kind discriminator so
    the two-level state model can be typed and tested without coupling
    to the reader implementation.
    """

    frame_kind: str

    def __post_init__(self) -> None:
        if self.frame_kind not in VALID_SENTENCE_FRAME_KINDS:
            raise ComprehensionStateError(
                "FramePayload.frame_kind must be one of "
                f"{sorted(VALID_SENTENCE_FRAME_KINDS)}; got {self.frame_kind!r}"
            )

    def as_canonical(self) -> dict[str, Any]:
        return {"frame_kind": self.frame_kind}


# ---------------------------------------------------------------------------
# New leaf types for ProblemReadingState (ADR-0164.3)
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class PartialInitialPossession:
    """Precursor to ADR-0115 InitialPossession during reader construction.

    Every field is nullable: the reader builds this incrementally as
    tokens arrive. A fully-specified instance (no None fields) projects
    to a strict ``InitialPossession`` at ``end_sentence``.
    """

    entity: str | None
    quantity: QuantityRef | None

    def __post_init__(self) -> None:
        if self.entity is not None:
            _require_non_empty_str(self.entity, "PartialInitialPossession.entity")
        if self.quantity is not None and not isinstance(self.quantity, QuantityRef):
            raise ComprehensionStateError(
                "PartialInitialPossession.quantity must be QuantityRef | None; "
                f"got {type(self.quantity).__name__}"
            )

    def as_canonical(self) -> dict[str, Any]:
        d: dict[str, Any] = {}
        if self.entity is not None:
            d["entity"] = self.entity
        if self.quantity is not None:
            d["quantity"] = self.quantity.as_canonical()
        return d


@dataclass(frozen=True, slots=True)
class PartialOperation:
    """Precursor to ADR-0115 Operation during reader construction.

    Every field is nullable: the reader builds this incrementally as
    tokens arrive. A fully-specified instance projects to a strict
    ``Operation`` at ``end_sentence``.
    """

    actor: str | None
    kind: str | None
    operand: QuantityRef | None
    target: str | None

    def __post_init__(self) -> None:
        if self.actor is not None:
            _require_non_empty_str(self.actor, "PartialOperation.actor")
        if self.kind is not None:
            _require_non_empty_str(self.kind, "PartialOperation.kind")
        if self.target is not None:
            _require_non_empty_str(self.target, "PartialOperation.target")
        if self.operand is not None and not isinstance(self.operand, QuantityRef):
            raise ComprehensionStateError(
                "PartialOperation.operand must be QuantityRef | None; "
                f"got {type(self.operand).__name__}"
            )

    def as_canonical(self) -> dict[str, Any]:
        d: dict[str, Any] = {}
        if self.actor is not None:
            d["actor"] = self.actor
        if self.kind is not None:
            d["kind"] = self.kind
        if self.operand is not None:
            d["operand"] = self.operand.as_canonical()
        if self.target is not None:
            d["target"] = self.target
        return d


@dataclass(frozen=True, slots=True)
class PronounResolution:
    """Replay-deterministic record of one pronoun resolution event.

    Per ADR-0164.2. Appended to ``ProblemReadingState.pronoun_resolution_history``
    only when the containing sentence closes successfully.
    """

    pronoun: str
    resolved_to: str
    at_sentence: int
    at_position: int

    def __post_init__(self) -> None:
        _require_non_empty_str(self.pronoun, "PronounResolution.pronoun")
        _require_non_empty_str(self.resolved_to, "PronounResolution.resolved_to")
        _require_non_negative_int(self.at_sentence, "PronounResolution.at_sentence")
        _require_non_negative_int(self.at_position, "PronounResolution.at_position")

    def as_canonical(self) -> dict[str, Any]:
        return {
            "at_position": self.at_position,
            "at_sentence": self.at_sentence,
            "pronoun": self.pronoun,
            "resolved_to": self.resolved_to,
        }


# ---------------------------------------------------------------------------
# ReaderRefusal (ADR-0164.3 §ReaderRefusal)
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class ReaderRefusal:
    """Typed refusal record. Carries one of the closed READER_REFUSAL_REASONS.

    ``token_text`` may be empty string for sentence-level or problem-level
    refusals where no single token is in question.
    """

    reason: str
    detail: str
    sentence_index: int
    token_index: int
    token_text: str

    def __post_init__(self) -> None:
        if self.reason not in READER_REFUSAL_REASONS:
            raise ComprehensionStateError(
                "ReaderRefusal.reason must be a member of READER_REFUSAL_REASONS; "
                f"got {self.reason!r}"
            )
        _require_non_empty_str(self.detail, "ReaderRefusal.detail")
        _require_non_negative_int(self.sentence_index, "ReaderRefusal.sentence_index")
        _require_non_negative_int(self.token_index, "ReaderRefusal.token_index")
        if not isinstance(self.token_text, str):
            raise ComprehensionStateError(
                "ReaderRefusal.token_text must be str; "
                f"got {type(self.token_text).__name__}"
            )

    def as_canonical(self) -> dict[str, Any]:
        return {
            "detail": self.detail,
            "reason": self.reason,
            "sentence_index": self.sentence_index,
            "token_index": self.token_index,
            "token_text": self.token_text,
        }

    def canonical_bytes(self) -> bytes:
        return to_canonical_bytes(self)

    def canonical_hash(self) -> str:
        return hashlib.sha256(self.canonical_bytes()).hexdigest()


# ---------------------------------------------------------------------------
# SentenceReadingState (inner, sentence-scoped) — ADR-0164.3 §Decision
# Renamed from ComprehensionState (#321). Original five fields stay verbatim.
# Seven new fields added (all with defaults) per ADR-0164.3 §SentenceReadingState.
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class SentenceReadingState:
    # --- original five fields (verbatim from #321) ---
    entities: tuple[EntityRef, ...]
    quantities: tuple[QuantityRef, ...]
    operations: tuple[PartialOp, ...]
    question_target: QuestionTargetSlot | None = None
    expectation: ExpectationFrame | None = None

    # --- ADR-0164.3 §SentenceReadingState new fields ---
    frame: SentenceFrame | None = None
    pending_quantities: tuple[QuantityRef, ...] = ()
    pending_entity_ref: EntityRef | None = None
    pending_verb: VerbReference | None = None
    token_index: int = 0
    lookback: tuple[AppliedCategory, ...] = ()
    partial_frame_payload: FramePayload | None = None

    def __post_init__(self) -> None:
        # --- validate original fields ---
        if not isinstance(self.entities, tuple):
            raise ComprehensionStateError(
                "SentenceReadingState.entities must be tuple[EntityRef, ...]"
            )
        if not isinstance(self.quantities, tuple):
            raise ComprehensionStateError(
                "SentenceReadingState.quantities must be tuple[QuantityRef, ...]"
            )
        if not isinstance(self.operations, tuple):
            raise ComprehensionStateError(
                "SentenceReadingState.operations must be tuple[PartialOp, ...]"
            )
        for idx, entity in enumerate(self.entities):
            if not isinstance(entity, EntityRef):
                raise ComprehensionStateError(
                    f"SentenceReadingState.entities[{idx}] must be EntityRef; "
                    f"got {type(entity).__name__}"
                )
        for idx, quantity in enumerate(self.quantities):
            if not isinstance(quantity, QuantityRef):
                raise ComprehensionStateError(
                    f"SentenceReadingState.quantities[{idx}] must be QuantityRef; "
                    f"got {type(quantity).__name__}"
                )
        for idx, operation in enumerate(self.operations):
            if not isinstance(operation, PartialOp):
                raise ComprehensionStateError(
                    f"SentenceReadingState.operations[{idx}] must be PartialOp; "
                    f"got {type(operation).__name__}"
                )
        if self.question_target is not None and not isinstance(
            self.question_target, QuestionTargetSlot
        ):
            raise ComprehensionStateError(
                "SentenceReadingState.question_target must be "
                f"QuestionTargetSlot | None; got {type(self.question_target).__name__}"
            )
        if self.expectation is not None and not isinstance(
            self.expectation, ExpectationFrame
        ):
            raise ComprehensionStateError(
                "SentenceReadingState.expectation must be "
                f"ExpectationFrame | None; got {type(self.expectation).__name__}"
            )

        # --- validate new fields ---
        if self.frame is not None and self.frame not in VALID_SENTENCE_FRAME_KINDS:
            raise ComprehensionStateError(
                "SentenceReadingState.frame must be a SentenceFrame literal or None; "
                f"got {self.frame!r}"
            )
        if not isinstance(self.pending_quantities, tuple):
            raise ComprehensionStateError(
                "SentenceReadingState.pending_quantities must be tuple[QuantityRef, ...]"
            )
        for idx, pq in enumerate(self.pending_quantities):
            if not isinstance(pq, QuantityRef):
                raise ComprehensionStateError(
                    f"SentenceReadingState.pending_quantities[{idx}] must be "
                    f"QuantityRef; got {type(pq).__name__}"
                )
        if self.pending_entity_ref is not None and not isinstance(
            self.pending_entity_ref, EntityRef
        ):
            raise ComprehensionStateError(
                "SentenceReadingState.pending_entity_ref must be EntityRef | None; "
                f"got {type(self.pending_entity_ref).__name__}"
            )
        if self.pending_verb is not None and not isinstance(
            self.pending_verb, VerbReference
        ):
            raise ComprehensionStateError(
                "SentenceReadingState.pending_verb must be VerbReference | None; "
                f"got {type(self.pending_verb).__name__}"
            )
        _require_non_negative_int(self.token_index, "SentenceReadingState.token_index")
        if not isinstance(self.lookback, tuple):
            raise ComprehensionStateError(
                "SentenceReadingState.lookback must be tuple[AppliedCategory, ...]"
            )
        if len(self.lookback) > _LOOKBACK_MAX:
            raise ComprehensionStateError(
                f"SentenceReadingState.lookback must be ≤{_LOOKBACK_MAX} entries; "
                f"got {len(self.lookback)}"
            )
        for idx, ac in enumerate(self.lookback):
            if not isinstance(ac, AppliedCategory):
                raise ComprehensionStateError(
                    f"SentenceReadingState.lookback[{idx}] must be AppliedCategory; "
                    f"got {type(ac).__name__}"
                )
        if self.partial_frame_payload is not None and not isinstance(
            self.partial_frame_payload, FramePayload
        ):
            raise ComprehensionStateError(
                "SentenceReadingState.partial_frame_payload must be "
                f"FramePayload | None; got {type(self.partial_frame_payload).__name__}"
            )

    # --- backward-compatible serialisation (original 5 fields only, null for None) ---

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


# ---------------------------------------------------------------------------
# ProblemReadingState (outer, problem-scoped) — ADR-0164.3 §Decision
# Field order matches ADR-0164.3 §ProblemReadingState table exactly.
# All fields required (no defaults) — initial construction is explicit.
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class ProblemReadingState:
    entity_registry: tuple[EntityRef, ...]
    accumulated_initial_state: tuple[PartialInitialPossession, ...]
    accumulated_operations: tuple[PartialOperation, ...]
    unknown_target_slot: QuestionTargetSlot | None
    pronoun_resolution_history: tuple[PronounResolution, ...]
    sentence_index: int
    source_text_offset: int

    def __post_init__(self) -> None:
        if not isinstance(self.entity_registry, tuple):
            raise ComprehensionStateError(
                "ProblemReadingState.entity_registry must be tuple[EntityRef, ...]"
            )
        for idx, e in enumerate(self.entity_registry):
            if not isinstance(e, EntityRef):
                raise ComprehensionStateError(
                    f"ProblemReadingState.entity_registry[{idx}] must be EntityRef; "
                    f"got {type(e).__name__}"
                )
        if not isinstance(self.accumulated_initial_state, tuple):
            raise ComprehensionStateError(
                "ProblemReadingState.accumulated_initial_state must be "
                "tuple[PartialInitialPossession, ...]"
            )
        for idx, pip in enumerate(self.accumulated_initial_state):
            if not isinstance(pip, PartialInitialPossession):
                raise ComprehensionStateError(
                    f"ProblemReadingState.accumulated_initial_state[{idx}] must be "
                    f"PartialInitialPossession; got {type(pip).__name__}"
                )
        if not isinstance(self.accumulated_operations, tuple):
            raise ComprehensionStateError(
                "ProblemReadingState.accumulated_operations must be "
                "tuple[PartialOperation, ...]"
            )
        for idx, po in enumerate(self.accumulated_operations):
            if not isinstance(po, PartialOperation):
                raise ComprehensionStateError(
                    f"ProblemReadingState.accumulated_operations[{idx}] must be "
                    f"PartialOperation; got {type(po).__name__}"
                )
        if self.unknown_target_slot is not None and not isinstance(
            self.unknown_target_slot, QuestionTargetSlot
        ):
            raise ComprehensionStateError(
                "ProblemReadingState.unknown_target_slot must be "
                f"QuestionTargetSlot | None; got {type(self.unknown_target_slot).__name__}"
            )
        if not isinstance(self.pronoun_resolution_history, tuple):
            raise ComprehensionStateError(
                "ProblemReadingState.pronoun_resolution_history must be "
                "tuple[PronounResolution, ...]"
            )
        for idx, pr in enumerate(self.pronoun_resolution_history):
            if not isinstance(pr, PronounResolution):
                raise ComprehensionStateError(
                    f"ProblemReadingState.pronoun_resolution_history[{idx}] must be "
                    f"PronounResolution; got {type(pr).__name__}"
                )
        _require_non_negative_int(
            self.sentence_index, "ProblemReadingState.sentence_index"
        )
        _require_non_negative_int(
            self.source_text_offset, "ProblemReadingState.source_text_offset"
        )

    def canonical_bytes(self) -> bytes:
        return to_canonical_bytes(self)

    def canonical_hash(self) -> str:
        return hashlib.sha256(self.canonical_bytes()).hexdigest()


# ---------------------------------------------------------------------------
# Canonical-bytes serialisation — ADR-0164.3 §Canonical-bytes
# Handles ProblemReadingState, SentenceReadingState, and ReaderRefusal.
# Rules: sort keys, compact separators, tuple→list, Decimal→str,
#        None→OMITTED (not null), dataclass→sorted-key dict.
# ---------------------------------------------------------------------------

def _canonical_dict_omit_none(obj: Any) -> Any:
    """Recursively convert to a canonical JSON-serialisable value.

    None values are returned as the sentinel _OMIT; callers drop them
    from dict outputs. This matches ADR-0164.3 §Canonical-bytes rule 7.
    """
    if obj is None:
        return _OMIT
    if isinstance(obj, bool):
        return obj
    if isinstance(obj, int):
        return obj
    if isinstance(obj, Decimal):
        return _canonical_decimal(obj)
    if isinstance(obj, str):
        return obj
    if isinstance(obj, (tuple, list)):
        return [_canonical_dict_omit_none(item) for item in obj]
    if hasattr(obj, "__dataclass_fields__"):
        out: dict[str, Any] = {}
        for key in sorted(obj.__dataclass_fields__.keys()):
            val = _canonical_dict_omit_none(getattr(obj, key))
            if val is not _OMIT:
                out[key] = val
        return out
    raise ComprehensionStateError(
        f"to_canonical_bytes: cannot serialise {type(obj).__name__}"
    )


class _OmitSentinel:
    """Sentinel returned by _canonical_dict_omit_none for None values."""
    __slots__ = ()


_OMIT = _OmitSentinel()


def to_canonical_bytes(
    state: ProblemReadingState | SentenceReadingState | ReaderRefusal,
) -> bytes:
    """Sorted-keys, compact-separators JSON per ADR-0164.3 §Canonical-bytes.

    Optional fields whose value is None are OMITTED from the output
    (not serialised as ``null``). Tuples become JSON arrays. Decimal
    values are serialised as strings to preserve precision.

    Identical state → byte-identical output (determinism gate).
    """
    d = _canonical_dict_omit_none(state)
    return json.dumps(
        d,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


# ---------------------------------------------------------------------------
# Backward-compatibility alias
# ---------------------------------------------------------------------------

#: Alias for code that imported ComprehensionState from #321.
#: ``SentenceReadingState`` is the canonical name per ADR-0164.3.
ComprehensionState = SentenceReadingState
