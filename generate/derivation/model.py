"""ADR-0175 Phase 3a — grounded-derivation value model.

A derivation is a left-fold over text-sourced quantities: a ``start`` quantity
followed by ordered ``Step``s. Each step names the operation, its operand, and
the **licensing cue** — the surface lexeme the search claims licenses that
operation. The cue is verified against the problem text by the gate
(:mod:`generate.derivation.verify`); the model itself only computes the value.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

VALID_OPS: Final[frozenset[str]] = frozenset({"multiply", "divide", "add", "subtract"})


@dataclass(frozen=True, slots=True)
class Quantity:
    """A quantity drawn from the problem. ``source_token`` is the surface token
    as it appears in the text (used by the gate to prove the value is grounded)."""

    value: float
    unit: str
    source_token: str


@dataclass(frozen=True, slots=True)
class Step:
    """One operation applied to the running value.

    ``cue`` is the surface lexeme the search asserts licenses ``op`` here; the
    gate refuses to self-verify unless ``cue`` actually appears in the text.
    """

    op: str
    operand: Quantity
    cue: str
    # ADR-0176 MS-2: when True the operand is a comparative scalar (twice -> x2,
    # 'N times' -> xN). It is grounded by ``cue`` (the comparative lexeme), not by a
    # text value token, and it does not count as a body quantity for completeness.
    comparative: bool = False

    def __post_init__(self) -> None:
        if self.op not in VALID_OPS:
            raise ValueError(f"op must be one of {sorted(VALID_OPS)}, got {self.op!r}")


@dataclass(frozen=True, slots=True)
class GroundedDerivation:
    start: Quantity
    steps: tuple[Step, ...]

    @property
    def answer(self) -> float:
        """Left-fold the steps over ``start``. Raises on divide-by-zero (the gate
        rejects such derivations before this is relied upon)."""
        value = self.start.value
        for step in self.steps:
            operand = step.operand.value
            if step.op == "multiply":
                value = value * operand
            elif step.op == "divide":
                value = value / operand  # ZeroDivisionError surfaces; gate guards
            elif step.op == "add":
                value = value + operand
            else:  # subtract
                value = value - operand
        return value

    @property
    def answer_unit(self) -> str:
        """The aggregate keeps the primary (``start``) unit. Multiply/divide
        compose across units onto the primary; add/subtract require (and the gate
        enforces) a shared unit, so the primary is correct in every admitted case."""
        return self.start.unit
