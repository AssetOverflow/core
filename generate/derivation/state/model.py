"""ADR-0184 S2 — minimal semantic-state model.

The S2 model represents the first scoped state-transition substrate used by the
accumulation composer.  It is intentionally narrow: SET_STATE plus GAIN/LOSS over
one entity/unit key.  Arithmetic commitment still happens only after replay into
``GroundedDerivation`` and the existing verifier/pool.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from generate.derivation.model import Quantity

VALID_TRANSITION_OPS: Final[frozenset[str]] = frozenset({"set", "gain", "loss"})


class SemanticStateError(ValueError):
    """Raised when a semantic-state object is structurally invalid."""


def _require_optional_str(value: object, field_name: str) -> None:
    if value is not None and (not isinstance(value, str) or value == ""):
        raise SemanticStateError(f"{field_name} must be None or a non-empty str; got {value!r}")


def _require_unit_str(value: object, field_name: str) -> None:
    # Units mirror the extractor's ``Quantity.unit`` contract exactly: a ``str``,
    # with ``""`` denoting unitless (the extractor never yields ``None``). Keeping
    # the substrate's unit type identical to the arithmetic layer avoids a latent
    # ``None``-vs-``""`` key-identity split in :func:`StateKey` equality.
    if not isinstance(value, str):
        raise SemanticStateError(f"{field_name} must be a str ('' = unitless); got {value!r}")


def _require_non_empty_str(value: object, field_name: str) -> None:
    if not isinstance(value, str) or value == "":
        raise SemanticStateError(f"{field_name} must be a non-empty str; got {value!r}")


def _require_non_negative_int(value: object, field_name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise SemanticStateError(f"{field_name} must be an int >= 0; got {value!r}")


@dataclass(frozen=True, slots=True)
class SemanticQuantity:
    """A quantity mention attached to a semantic transition.

    ``unit`` is a ``str`` (``""`` = unitless), identical to the extractor's
    ``Quantity.unit`` contract.  Replay can override the operand unit with the ledger
    key's running unit, matching the existing accumulation behavior ("9 more"
    inherits the anchor unit).
    """

    value: float
    unit: str
    source_token: str
    clause_index: int

    def __post_init__(self) -> None:
        if not isinstance(self.value, int | float) or isinstance(self.value, bool):
            raise SemanticStateError(
                f"SemanticQuantity.value must be numeric; got {type(self.value).__name__}"
            )
        _require_unit_str(self.unit, "SemanticQuantity.unit")
        _require_non_empty_str(self.source_token, "SemanticQuantity.source_token")
        _require_non_negative_int(self.clause_index, "SemanticQuantity.clause_index")

    @classmethod
    def from_quantity(cls, quantity: Quantity, *, clause_index: int) -> "SemanticQuantity":
        """Lift a derivation ``Quantity`` into a semantic quantity mention."""

        return cls(
            value=float(quantity.value),
            unit=quantity.unit,
            source_token=quantity.source_token,
            clause_index=clause_index,
        )

    def to_quantity(self, *, unit_override: str | None = None) -> Quantity:
        """Project back to the arithmetic proof object's ``Quantity`` type."""

        return Quantity(
            value=self.value,
            unit=self.unit if unit_override is None else unit_override,
            source_token=self.source_token,
        )


@dataclass(frozen=True, slots=True)
class StateKey:
    """Entity-owned quantity dimension.

    ``entity`` remains optional in S2 (``None`` when the loose leading subject is
    absent, mirroring :func:`generate.derivation.state.bind.leading_subject_token`);
    later ADR-0184 phases can tighten this once explicit entity binding exists.
    ``unit`` is a ``str`` (``""`` = unitless), identical to the extractor contract.
    """

    entity: str | None
    unit: str

    def __post_init__(self) -> None:
        _require_optional_str(self.entity, "StateKey.entity")
        _require_unit_str(self.unit, "StateKey.unit")


@dataclass(frozen=True, slots=True)
class StateTransition:
    """One semantic mutation over a ``StateKey``."""

    key: StateKey
    op: str
    quantity: SemanticQuantity
    cue: str
    clause_index: int

    def __post_init__(self) -> None:
        if not isinstance(self.key, StateKey):
            raise SemanticStateError(
                f"StateTransition.key must be StateKey; got {type(self.key).__name__}"
            )
        if self.op not in VALID_TRANSITION_OPS:
            raise SemanticStateError(
                f"StateTransition.op must be one of {sorted(VALID_TRANSITION_OPS)}; got {self.op!r}"
            )
        if not isinstance(self.quantity, SemanticQuantity):
            raise SemanticStateError(
                "StateTransition.quantity must be SemanticQuantity; "
                f"got {type(self.quantity).__name__}"
            )
        _require_non_empty_str(self.cue, "StateTransition.cue")
        _require_non_negative_int(self.clause_index, "StateTransition.clause_index")


@dataclass(frozen=True, slots=True)
class SemanticLedger:
    """Ordered semantic transitions for one candidate world."""

    transitions: tuple[StateTransition, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.transitions, tuple):
            raise SemanticStateError("SemanticLedger.transitions must be a tuple")
        for idx, transition in enumerate(self.transitions):
            if not isinstance(transition, StateTransition):
                raise SemanticStateError(
                    "SemanticLedger.transitions entries must be StateTransition; "
                    f"got {type(transition).__name__} at index {idx}"
                )
