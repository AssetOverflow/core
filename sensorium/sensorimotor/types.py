"""Typed sensorimotor IR for afferent proprioceptive feedback."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True, slots=True)
class ProprioceptiveSignal:
    pose_q: tuple[int, ...]
    velocity_q: tuple[int, ...]
    force_torque_q: tuple[int, ...]
    contact_q: tuple[int, ...]
    actuator_state_q: tuple[int, ...]
    source_sha256: str
    canonical_sha256: str


@dataclass(frozen=True, slots=True)
class SensorimotorEvent:
    event_type: str
    attrs: tuple[tuple[str, int | str], ...]
    evidence_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SensorimotorIR:
    events: tuple[SensorimotorEvent, ...]
    ir_sha256: str


@dataclass(frozen=True, slots=True)
class SensorimotorCompilationUnit:
    canonical_sha256: str
    ir_sha256: str
    pack_id: str
    pack_manifest_sha256: str
    projection_sha256: str
    versor: np.ndarray
    versor_condition: float
    sensorimotor_ir: SensorimotorIR

    @property
    def merge_key(self) -> tuple[str, str, str]:
        return (self.canonical_sha256, self.ir_sha256, self.projection_sha256)
