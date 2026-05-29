"""
sensorium/audio/operators.py — operator registry + rotor lowering (spec §6).

Each auditory event lowers to a *declared rotor specification*, not an opaque
vector. v1 uses **elliptic bivector operators only** (square = -1), so every
rotor is the numerically well-behaved R = cos(θ/2) + B·sin(θ/2) and the
composition of any sequence is a unit versor (versor_condition < 1e-6 holds
without weakening the threshold — CLAUDE.md §Non-Negotiable Field Invariant).

Elliptic planes in Cl(4,1) signature (+,+,+,+,-): a grade-2 blade e_a e_b
squares to -1 iff both a,b ∈ {e1..e4}. With the algebra's blade ordering
(combinations(range(5),2)), the elliptic grade-2 indices are:

    6=(e1e2) 7=(e1e3) 8=(e1e4) 10=(e2e3) 11=(e2e4) 13=(e3e4)

Indices 9,12,14,15 involve e5 and are hyperbolic — excluded from v1. The
alias→index assignment below is versioned pack data (frozen in PR-3's
manifest); here it is the in-code default the compiler ships with.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from sensorium.audio.checksum import sha256_json
from sensorium.audio.types import AuditoryEvent

CL41_DIM = 32

# The six elliptic grade-2 planes (square = -1).
ELLIPTIC_PLANES: tuple[int, ...] = (6, 7, 8, 10, 11, 13)

# θ_q is an integer; the radian angle is θ_q * THETA_STEP. 1024 steps span
# [0, 2π), so a rotor angle is always representable and bounded.
THETA_STEP = math.pi / 512.0


@dataclass(frozen=True, slots=True)
class OperatorSpec:
    """Declared elliptic rotor spec for one event type (spec §6.2)."""
    operator_id: str
    event_type: str
    blade_alias: str
    blade_index: int
    base_theta_q: int
    gain_rules: tuple[tuple[str, int], ...]   # (attr_name, gain) pairs
    theta_clip_q: int
    version: str = "1"

    def __post_init__(self) -> None:
        if self.blade_index not in ELLIPTIC_PLANES:
            raise ValueError(
                f"operator '{self.operator_id}' uses non-elliptic blade "
                f"{self.blade_index}; v1 permits only {ELLIPTIC_PLANES}"
            )

    def theta_q_from_event(self, event: AuditoryEvent) -> int:
        """Deterministic θ_q from quantized event attrs. Inputs are ints
        only (spec §7: quantized inputs only), so the result is an int."""
        attrs = dict(event.attrs)
        theta_q = self.base_theta_q
        for attr_name, gain in self.gain_rules:
            value = attrs.get(attr_name, 0)
            if isinstance(value, int):
                theta_q += gain * value
        return max(0, min(self.theta_clip_q, theta_q))


def build_elliptic_rotor(blade_index: int, theta_q: int) -> np.ndarray:
    """R = cos(θ/2) + B·sin(θ/2) for an elliptic plane B. θ = θ_q·THETA_STEP.

    Returns a float64 unit versor of shape (32,)."""
    if blade_index not in ELLIPTIC_PLANES:
        raise ValueError(f"non-elliptic blade {blade_index}")
    out = np.zeros(CL41_DIM, dtype=np.float64)
    half = (theta_q * THETA_STEP) / 2.0
    out[0] = math.cos(half)
    out[blade_index] = math.sin(half)
    return out


@dataclass(frozen=True, slots=True)
class AudioOperatorRegistry:
    """Maps event_type → OperatorSpec. Frozen and content-addressable."""
    specs: dict[str, OperatorSpec] = field(default_factory=dict)

    def __getitem__(self, event_type: str) -> OperatorSpec:
        return self.specs[event_type]

    def __contains__(self, event_type: str) -> bool:
        return event_type in self.specs

    def manifest_sha256(self) -> str:
        """Content hash over the registry's canonical serialization — the
        ``pack_manifest_sha256`` link of the checksum chain (spec §6)."""
        payload = [
            {
                "operator_id": s.operator_id,
                "event_type": s.event_type,
                "blade_alias": s.blade_alias,
                "blade_index": s.blade_index,
                "base_theta_q": s.base_theta_q,
                "gain_rules": [list(g) for g in s.gain_rules],
                "theta_clip_q": s.theta_clip_q,
                "version": s.version,
            }
            for s in sorted(self.specs.values(), key=lambda x: x.operator_id)
        ]
        return sha256_json({"basis_version": "audio-basis-v1", "operators": payload})


def _spec(op_id, etype, alias, blade, base, gains, clip=768) -> OperatorSpec:
    return OperatorSpec(op_id, etype, alias, blade, base, tuple(gains), clip)


# In-code default registry (PR-3 externalises this to operators.jsonl). Each
# atom family maps to one elliptic plane; planes are reused across families
# (only six exist) with distinct base angles. Full orthogonality is a later
# concern — lawfulness (elliptic, unit) is the PR-2 invariant.
DEFAULT_OPERATOR_REGISTRY = AudioOperatorRegistry({
    "pause.short":      _spec("audio.pause.short.v1",   "pause.short",      "B_PAUSE_SHORT", 6,  48, [("dur_hops", 2)]),
    "pause.long":       _spec("audio.pause.long.v1",    "pause.long",       "B_PAUSE_LONG",  7,  96, [("dur_hops", 2)]),
    "speech.voiced":    _spec("audio.speech.voiced.v1", "speech.voiced",    "B_SPEECH",      8,  64, [("dur_hops", 1)]),
    "prosody.rise":     _spec("audio.prosody.rise.v1",  "prosody.rise",     "B_PITCH_RISE",  10, 64, [("slope_q", 3)]),
    "prosody.fall":     _spec("audio.prosody.fall.v1",  "prosody.fall",     "B_PITCH_FALL",  11, 64, [("slope_q", 3)]),
    "prosody.emphasis": _spec("audio.prosody.emph.v1",  "prosody.emphasis", "B_EMPHASIS",    13, 32, [("delta_db_q", 4)]),
    "turn.boundary":    _spec("audio.turn.boundary.v1", "turn.boundary",    "B_TURN",        6,  160, [("boundary_q", 2)]),
    "nonspeech.noise":  _spec("audio.nonspeech.noise.v1", "nonspeech.noise", "B_NOISE",      7,  200, [("noise_q", 2)]),
})
