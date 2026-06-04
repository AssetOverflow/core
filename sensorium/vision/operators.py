"""Operator registry and rotor lowering for vision_core_v1."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from sensorium.vision.checksum import sha256_json
from sensorium.vision.types import VisualEvent

CL41_DIM = 32
ELLIPTIC_PLANES: tuple[int, ...] = (6, 7, 8, 10, 11, 13)
THETA_STEP = math.pi / 512.0


@dataclass(frozen=True, slots=True)
class VisionOperatorSpec:
    operator_id: str
    event_type: str
    blade_alias: str
    blade_index: int
    base_theta_q: int
    gain_rules: tuple[tuple[str, int], ...]
    theta_clip_q: int
    version: str = "1"

    def __post_init__(self) -> None:
        if self.blade_index not in ELLIPTIC_PLANES:
            raise ValueError(
                f"operator '{self.operator_id}' uses non-elliptic blade "
                f"{self.blade_index}; v1 permits only {ELLIPTIC_PLANES}"
            )

    def theta_q_from_event(self, event: VisualEvent) -> int:
        attrs = dict(event.attrs)
        theta_q = self.base_theta_q
        # Position modulates theta in v1; it is not a separate CGA generator.
        theta_q += 2 * event.coord.scale_level + event.coord.tile_row + event.coord.tile_col
        for attr_name, gain in self.gain_rules:
            value = attrs.get(attr_name, 0)
            if isinstance(value, int):
                theta_q += gain * value
        return max(0, min(self.theta_clip_q, theta_q))


def build_elliptic_rotor(blade_index: int, theta_q: int) -> np.ndarray:
    if blade_index not in ELLIPTIC_PLANES:
        raise ValueError(f"non-elliptic blade {blade_index}")
    out = np.zeros(CL41_DIM, dtype=np.float64)
    half = (theta_q * THETA_STEP) / 2.0
    out[0] = math.cos(half)
    out[blade_index] = math.sin(half)
    return out


@dataclass(frozen=True, slots=True)
class VisionOperatorRegistry:
    specs: dict[str, VisionOperatorSpec] = field(default_factory=dict)
    basis_version: str = "vision-basis-v1"

    def __getitem__(self, event_type: str) -> VisionOperatorSpec:
        return self.specs[event_type]

    def __contains__(self, event_type: str) -> bool:
        return event_type in self.specs

    def manifest_sha256(self) -> str:
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
        return sha256_json({"basis_version": self.basis_version, "operators": payload})


def _spec(op_id, etype, alias, blade, base, gains, clip=768) -> VisionOperatorSpec:
    return VisionOperatorSpec(op_id, etype, alias, blade, base, tuple(gains), clip)


DEFAULT_OPERATOR_REGISTRY = VisionOperatorRegistry({
    "region.flat": _spec("vision.region.flat.v1", "region.flat", "B_CONTRAST", 6, 24, [("contrast_q", 1)]),
    "region.contrast": _spec("vision.region.contrast.v1", "region.contrast", "B_CONTRAST", 6, 64, [("contrast_q", 4)]),
    "orient.edge_energy": _spec("vision.orient.edge_energy.v1", "orient.edge_energy", "B_ORIENT", 7, 48, [("orient_q", 3), ("energy_q", 4)]),
    "texture.regularity": _spec("vision.texture.regularity.v1", "texture.regularity", "B_TEXTURE", 8, 40, [("texture_q", 5)]),
    "salient.figure_ground": _spec("vision.salient.figure_ground.v1", "salient.figure_ground", "B_SALIENCE", 10, 56, [("salience_q", 4)]),
    "region.chroma": _spec("vision.region.chroma.v1", "region.chroma", "B_CHROMA", 11, 36, [("chroma_q", 4)]),
    "region.corner": _spec("vision.region.corner.v1", "region.corner", "B_CORNER", 13, 72, [("corner_q", 5)]),
    "region.blob": _spec("vision.region.blob.v1", "region.blob", "B_BLOB", 10, 88, [("blob_q", 4)]),
    "contour.closure": _spec("vision.contour.closure.v1", "contour.closure", "B_CONTOUR", 13, 104, [("closure_q", 3)]),
})
