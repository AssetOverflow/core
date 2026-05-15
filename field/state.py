"""
FieldState — the complete cognitive field at one moment.

Invariant: versor_condition(F) < 1e-6 always.
This is checked at injection and maintained structurally by versor_apply().

FieldState is immutable by design (frozen=True, slots=True).
The np.ndarray F is copied and validated at construction — the copy() call
is the explicit contract boundary. Callers must not retain a mutable
reference to the array passed in and expect coherence.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING
import numpy as np

if TYPE_CHECKING:
    from core.physics.energy import EnergyProfile
    from core.physics.valence import ValenceBundle

_EXPECTED_COMPONENTS = 32


@dataclass(frozen=True, slots=True)
class FieldState:
    F: np.ndarray   # shape (32,) float32/float64 — Cl(4,1) multivector on the versor manifold
    node: int = 0   # current node index in the vocabulary manifold
    step: int = 0   # number of propagation steps taken
    holonomy: np.ndarray | None = None
    energy: EnergyProfile | None = None
    valence: ValenceBundle | None = None

    def __post_init__(self) -> None:
        # Enforce copy + dtype + shape at the construction boundary.
        # frozen=True prevents reassignment, but ndarray contents are still
        # mutable via the array object; copy() here is the defence.
        # slots=True closes __dict__ so no incidental attributes can be added.
        f_dtype = np.asarray(self.F).dtype
        if f_dtype not in (np.dtype(np.float32), np.dtype(np.float64)):
            f_dtype = np.dtype(np.float32)
        F = np.array(self.F, dtype=f_dtype).copy()
        if F.shape != (_EXPECTED_COMPONENTS,):
            raise ValueError(
                f"FieldState.F must have shape ({_EXPECTED_COMPONENTS},), "
                f"got {F.shape}."
            )
        # Bypass frozen to store the validated copy.
        object.__setattr__(self, "F", F)
        if self.holonomy is not None:
            h_dtype = np.asarray(self.holonomy).dtype
            if h_dtype not in (np.dtype(np.float32), np.dtype(np.float64)):
                h_dtype = np.dtype(np.float32)
            H = np.array(self.holonomy, dtype=h_dtype).copy()
            if H.shape != (_EXPECTED_COMPONENTS,):
                raise ValueError(
                    f"FieldState.holonomy must have shape ({_EXPECTED_COMPONENTS},), "
                    f"got {H.shape}."
                )
            object.__setattr__(self, "holonomy", H)

    def advance(self, new_F: np.ndarray, new_node: int) -> FieldState:
        """Return a new FieldState after one propagation step."""
        return FieldState(
            F=new_F,
            node=new_node,
            step=self.step + 1,
            holonomy=self.holonomy,
            energy=self.energy,
            valence=self.valence,
        )


@dataclass(frozen=True, slots=True)
class ManifoldState:
    """Field over a graph topology — one versor per node, with edge connectivity.

    Invariant: versor_condition(fields[i]) < 1e-6 for every node i.
    """

    fields: np.ndarray  # (N, 32) float32 — one Cl(4,1) versor per node
    edges: np.ndarray   # (E, 2) int32 — directed edge list
    step: int = 0

    def __post_init__(self) -> None:
        from algebra.backend import versor_condition

        F = np.array(self.fields, dtype=np.float32).copy()
        if F.ndim != 2 or F.shape[1] != _EXPECTED_COMPONENTS:
            raise ValueError(
                f"ManifoldState.fields must have shape (N, {_EXPECTED_COMPONENTS}), "
                f"got {F.shape}."
            )
        object.__setattr__(self, "fields", F)

        E = np.array(self.edges, dtype=np.int32).copy()
        if E.ndim != 2 or E.shape[1] != 2:
            raise ValueError(
                f"ManifoldState.edges must have shape (E, 2), got {E.shape}."
            )
        n_nodes = F.shape[0]
        if E.size > 0 and (E.min() < 0 or E.max() >= n_nodes):
            raise ValueError(
                f"Edge indices must be in [0, {n_nodes}), "
                f"got range [{E.min()}, {E.max()}]."
            )
        object.__setattr__(self, "edges", E)

        for i in range(n_nodes):
            vc = versor_condition(F[i])
            if vc >= 1e-6:
                raise ValueError(
                    f"ManifoldState.fields[{i}] violates versor_condition: {vc:.2e} >= 1e-6."
                )

    def with_fields(self, new_fields: np.ndarray) -> ManifoldState:
        """Return a new ManifoldState with updated field values."""
        return ManifoldState(fields=new_fields, edges=self.edges, step=self.step)

    def advance(self) -> ManifoldState:
        """Return a new ManifoldState one step forward."""
        return ManifoldState(fields=self.fields, edges=self.edges, step=self.step + 1)
