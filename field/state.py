"""
FieldState — the complete cognitive field at one moment.

Invariant: versor_condition(F) < 1e-6 always.
This is checked at injection and maintained structurally by versor_apply().

FieldState is immutable by design (frozen=True).
The np.ndarray F is copied and validated at construction — the copy() call
is the explicit contract boundary. Callers must not retain a mutable
reference to the array passed in and expect coherence.
"""

from __future__ import annotations
from dataclasses import dataclass
import numpy as np

_EXPECTED_COMPONENTS = 32


@dataclass(frozen=True)
class FieldState:
    F: np.ndarray   # shape (32,) float32 — Cl(4,1) multivector on the versor manifold
    node: int = 0   # current node index in the vocabulary manifold
    step: int = 0   # number of propagation steps taken
    holonomy: np.ndarray | None = None

    def __post_init__(self) -> None:
        # Enforce copy + dtype + shape at the construction boundary.
        # frozen=True prevents reassignment, but ndarray contents are still
        # mutable via the array object; copy() here is the defence.
        F = np.array(self.F, dtype=np.float32).copy()
        if F.shape != (_EXPECTED_COMPONENTS,):
            raise ValueError(
                f"FieldState.F must have shape ({_EXPECTED_COMPONENTS},), "
                f"got {F.shape}."
            )
        # Bypass frozen to store the validated copy.
        object.__setattr__(self, "F", F)
        if self.holonomy is not None:
            H = np.array(self.holonomy, dtype=np.float32).copy()
            if H.shape != (_EXPECTED_COMPONENTS,):
                raise ValueError(
                    f"FieldState.holonomy must have shape ({_EXPECTED_COMPONENTS},), "
                    f"got {H.shape}."
                )
            object.__setattr__(self, "holonomy", H)

    def advance(self, new_F: np.ndarray, new_node: int) -> FieldState:
        """Return a new FieldState after one propagation step."""
        return FieldState(F=new_F, node=new_node, step=self.step + 1, holonomy=self.holonomy)
