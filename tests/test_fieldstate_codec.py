"""FieldState round-trip — Shape B+ Phase A.

The restored field must be BIT-EXACT (so versor_condition < 1e-6 survives and the
replayed turn keeps its trace_hash) and FAITHFUL (node/step/holonomy/energy/
valence all preserved). Scalar floats and strings round-trip exactly through
JSON; only the multivector arrays use the byte-exact codec.
"""

from __future__ import annotations

import json

import numpy as np

from algebra.versor import versor_condition
from core.physics.energy import EnergyClass, EnergyProfile
from core.physics.valence import EmphasisProfile, ForceClass, ValenceBundle
from field.state import FieldState


def _identity_versor() -> np.ndarray:
    # Scalar 1, rest 0 — a valid unit versor (versor_condition == 0 exactly).
    f = np.zeros(32, dtype=np.float32)
    f[0] = 1.0
    return f


def _populated_fieldstate(dtype=np.float32) -> FieldState:
    return FieldState(
        F=_identity_versor().astype(dtype),
        node=5,
        step=3,
        holonomy=np.full(32, 0.0123456789, dtype=dtype),
        energy=EnergyProfile(
            raw=1.5,
            energy_class=EnergyClass.E2,
            activation_count=2,
            coherence_residual=3.5e-7,
            anchor_adjacent=True,
        ),
        valence=ValenceBundle(
            affective=frozenset({"joy", "calm"}),
            force=ForceClass.INTERROGATIVE,
            emphasis=EmphasisProfile(focus_element="x", mechanism="cleft", degree="high"),
        ),
    )


def test_fieldstate_round_trips_bit_exact_and_preserves_closure() -> None:
    fs = _populated_fieldstate()
    restored = FieldState.from_dict(fs.to_dict())
    # Bit-exact arrays.
    assert restored.F.tobytes() == fs.F.tobytes()
    assert restored.F.dtype == fs.F.dtype
    assert restored.holonomy is not None
    assert restored.holonomy.tobytes() == fs.holonomy.tobytes()
    # Faithful scalars / nested objects (frozen dataclass equality).
    assert restored.node == fs.node
    assert restored.step == fs.step
    assert restored.energy == fs.energy
    assert restored.valence == fs.valence
    # Closure preserved EXACTLY (the load-bearing property).
    assert versor_condition(restored.F) == versor_condition(fs.F)
    assert versor_condition(restored.F) < 1e-6


def test_fieldstate_round_trip_is_json_safe() -> None:
    fs = _populated_fieldstate()
    restored = FieldState.from_dict(json.loads(json.dumps(fs.to_dict())))
    assert restored.F.tobytes() == fs.F.tobytes()
    assert restored.valence == fs.valence


def test_fieldstate_preserves_float64_dtype() -> None:
    fs = _populated_fieldstate(dtype=np.float64)
    restored = FieldState.from_dict(fs.to_dict())
    assert restored.F.dtype == np.float64  # float32 must never be conflated
    assert restored.F.tobytes() == fs.F.tobytes()


def test_fieldstate_round_trips_with_none_optionals() -> None:
    fs = FieldState(F=_identity_versor(), node=0, step=0)
    restored = FieldState.from_dict(fs.to_dict())
    assert restored.holonomy is None
    assert restored.energy is None
    assert restored.valence is None
    assert restored.F.tobytes() == fs.F.tobytes()
