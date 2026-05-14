"""
GenerationResult — the complete output of one generation pass.

Generate() must return the evolved field state, not only surface tokens.
The field state after generation is semantically different from the
field state before generation; discarding it means the vault stores
the prompt field, not the assistant response field.

Contracts:
  tokens       — the decoded token sequence in emission order
  final_state  — FieldState after the last propagation step
  trajectory   — optional ordered list of intermediate FieldStates;
                 None unless the caller explicitly requests it (expensive)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from field.state import FieldState


@dataclass(frozen=True, slots=True)
class GenerationResult:
    tokens: tuple          # decoded token sequence, immutable
    final_state: FieldState
    trajectory: tuple | None = None  # (FieldState, ...) or None
    salience_top_k: int | None = None
    candidates_used: int | None = None

    def __post_init__(self) -> None:
        # Coerce list inputs to tuple for immutability.
        object.__setattr__(self, "tokens", tuple(self.tokens))
        if self.trajectory is not None:
            object.__setattr__(self, "trajectory", tuple(self.trajectory))

    def text(self, sep: str = " ") -> str:
        """Join tokens into a string for display."""
        return sep.join(self.tokens)
