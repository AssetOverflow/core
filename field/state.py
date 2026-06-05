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
from typing import TYPE_CHECKING, Any
import numpy as np

from core.array_codec import (
    decode_array,
    decode_optional_array,
    encode_array,
    encode_optional_array,
)

if TYPE_CHECKING:
    from core.physics.energy import EnergyProfile
    from core.physics.valence import ValenceBundle

_EXPECTED_COMPONENTS = 32


def _encode_energy(energy: "EnergyProfile | None") -> dict[str, Any] | None:
    if energy is None:
        return None
    return {
        "raw": float(energy.raw),
        "energy_class": energy.energy_class.value,
        "convergence_density": int(energy.convergence_density),
        "activation_count": int(energy.activation_count),
        "last_activation_cycle": int(energy.last_activation_cycle),
        "coherence_residual": float(energy.coherence_residual),
        "aspect_weight": float(energy.aspect_weight),
        "anchor_adjacent": bool(energy.anchor_adjacent),
    }


def _decode_energy(payload: dict[str, Any] | None) -> "EnergyProfile | None":
    if payload is None:
        return None
    from core.physics.energy import EnergyClass, EnergyProfile

    return EnergyProfile(
        raw=payload["raw"],
        energy_class=EnergyClass(payload["energy_class"]),
        convergence_density=payload["convergence_density"],
        activation_count=payload["activation_count"],
        last_activation_cycle=payload["last_activation_cycle"],
        coherence_residual=payload["coherence_residual"],
        aspect_weight=payload["aspect_weight"],
        anchor_adjacent=payload["anchor_adjacent"],
    )


def _encode_valence(valence: "ValenceBundle | None") -> dict[str, Any] | None:
    if valence is None:
        return None
    return {
        # sorted for deterministic serialization of the unordered frozenset
        "affective": sorted(valence.affective),
        "force": valence.force.value,
        "emphasis": {
            "focus_element": valence.emphasis.focus_element,
            "mechanism": valence.emphasis.mechanism,
            "degree": valence.emphasis.degree,
        },
        "polarity": {
            "value": valence.polarity.value,
            "kind": valence.polarity.kind,
        },
        "orientation": {
            "direction": valence.orientation.direction,
            "target": valence.orientation.target,
            "preposition_source": valence.orientation.preposition_source,
        },
    }


def _decode_valence(payload: dict[str, Any] | None) -> "ValenceBundle | None":
    if payload is None:
        return None
    from core.physics.valence import (
        EmphasisProfile,
        ForceClass,
        OrientationSpec,
        PolaritySpec,
        ValenceBundle,
    )

    return ValenceBundle(
        affective=frozenset(payload["affective"]),
        force=ForceClass(payload["force"]),
        emphasis=EmphasisProfile(**payload["emphasis"]),
        polarity=PolaritySpec(**payload["polarity"]),
        orientation=OrientationSpec(**payload["orientation"]),
    )


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

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a bit-exact, JSON-safe dict (Shape B+ persistence).

        The multivector arrays (``F``, ``holonomy``) go through the byte-exact
        array codec so ``versor_condition`` and ``trace_hash`` survive a
        save/load cycle unchanged; scalar floats/strings on the energy/valence
        side round-trip exactly through JSON.
        """
        return {
            "F": encode_array(self.F),
            "node": int(self.node),
            "step": int(self.step),
            "holonomy": encode_optional_array(self.holonomy),
            "energy": _encode_energy(self.energy),
            "valence": _encode_valence(self.valence),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> FieldState:
        """Reconstruct a FieldState from ``to_dict`` output (exact round-trip)."""
        return cls(
            F=decode_array(payload["F"]),
            node=int(payload["node"]),
            step=int(payload["step"]),
            holonomy=decode_optional_array(payload.get("holonomy")),
            energy=_decode_energy(payload.get("energy")),
            valence=_decode_valence(payload.get("valence")),
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
