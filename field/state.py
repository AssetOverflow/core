"""
FieldState — the complete cognitive field at one moment.

Invariant: versor_condition(F) < 1e-6 always.
This is checked at injection and maintained structurally by versor_apply().
"""

from dataclasses import dataclass
import numpy as np


@dataclass
class FieldState:
    F: np.ndarray   # shape (32,) — Cl(4,1) multivector on the versor manifold
    node: int = 0   # current node index in the vocabulary manifold
    step: int = 0   # number of propagation steps taken

    def advance(self, new_F: np.ndarray, new_node: int) -> "FieldState":
        """Return a new FieldState after one propagation step."""
        return FieldState(F=new_F, node=new_node, step=self.step + 1)
