"""Deterministic afferent sensorimotor compiler."""

from __future__ import annotations

import math

import numpy as np

from algebra.cl41 import geometric_product
from algebra.versor import unitize_versor, versor_condition
from sensorium.audio.checksum import sha256_array, sha256_json
from sensorium.sensorimotor.types import (
    ProprioceptiveSignal,
    SensorimotorCompilationUnit,
    SensorimotorEvent,
    SensorimotorIR,
)

CL41_DIM = 32
VERSOR_CONDITION_MAX = 1e-6
THETA_STEP = math.pi / 512.0
_EVENT_ORDER = (
    "proprio.pose",
    "proprio.velocity",
    "haptic.force_torque",
    "haptic.contact",
    "actuator.state",
)
_BLADE_BY_EVENT = {
    "proprio.pose": 6,
    "proprio.velocity": 7,
    "haptic.force_torque": 8,
    "haptic.contact": 10,
    "actuator.state": 11,
}
_BASE_BY_EVENT = {
    "proprio.pose": 48,
    "proprio.velocity": 64,
    "haptic.force_torque": 80,
    "haptic.contact": 96,
    "actuator.state": 112,
}


def canonicalize_proprioception(
    *,
    pose_q: tuple[int, ...] = (),
    velocity_q: tuple[int, ...] = (),
    force_torque_q: tuple[int, ...] = (),
    contact_q: tuple[int, ...] = (),
    actuator_state_q: tuple[int, ...] = (),
    source_id: str = "",
) -> ProprioceptiveSignal:
    payload = {
        "pose_q": list(pose_q),
        "velocity_q": list(velocity_q),
        "force_torque_q": list(force_torque_q),
        "contact_q": list(contact_q),
        "actuator_state_q": list(actuator_state_q),
        "source_id": source_id,
    }
    source_sha256 = sha256_json(payload)
    canonical_payload = {k: payload[k] for k in payload if k != "source_id"}
    return ProprioceptiveSignal(
        pose_q=tuple(int(v) for v in pose_q),
        velocity_q=tuple(int(v) for v in velocity_q),
        force_torque_q=tuple(int(v) for v in force_torque_q),
        contact_q=tuple(int(v) for v in contact_q),
        actuator_state_q=tuple(int(v) for v in actuator_state_q),
        source_sha256=source_sha256,
        canonical_sha256=sha256_json(canonical_payload),
    )


def _event(event_type: str, values: tuple[int, ...]) -> SensorimotorEvent:
    attrs = tuple((f"q{idx}", int(value)) for idx, value in enumerate(values))
    return SensorimotorEvent(event_type, attrs, ())


def _parse(signal: ProprioceptiveSignal) -> SensorimotorIR:
    events = (
        _event("proprio.pose", signal.pose_q),
        _event("proprio.velocity", signal.velocity_q),
        _event("haptic.force_torque", signal.force_torque_q),
        _event("haptic.contact", signal.contact_q),
        _event("actuator.state", signal.actuator_state_q),
    )
    payload = [
        {
            "event_type": ev.event_type,
            "attrs": [list(pair) for pair in ev.attrs],
            "evidence_ids": list(ev.evidence_ids),
        }
        for ev in events
    ]
    return SensorimotorIR(events, sha256_json({"events": payload}))


def _build_rotor(blade_index: int, theta_q: int) -> np.ndarray:
    out = np.zeros(CL41_DIM, dtype=np.float64)
    half = (theta_q * THETA_STEP) / 2.0
    out[0] = math.cos(half)
    out[blade_index] = math.sin(half)
    return out


def _theta_q(event: SensorimotorEvent) -> int:
    total = sum(abs(int(value)) for _, value in event.attrs if isinstance(value, int))
    return max(0, min(768, _BASE_BY_EVENT[event.event_type] + total))


def compile_events(events: tuple[SensorimotorEvent, ...]) -> tuple[np.ndarray, float]:
    rank = {name: idx for idx, name in enumerate(_EVENT_ORDER)}
    v = np.zeros(CL41_DIM, dtype=np.float64)
    v[0] = 1.0
    for event in sorted(events, key=lambda ev: rank[ev.event_type]):
        r = _build_rotor(_BLADE_BY_EVENT[event.event_type], _theta_q(event))
        v = geometric_product(v, r)
        v = unitize_versor(v)
    vc = float(versor_condition(v))
    if vc >= VERSOR_CONDITION_MAX:
        raise ValueError(
            f"sensorimotor compilation failed versor check: {vc:.3e} >= {VERSOR_CONDITION_MAX:.0e}"
        )
    return v.astype(np.float32), vc


class SensorimotorCompiler:
    """Compiler for afferent proprioceptive feedback only."""

    modality = "sensorimotor"

    def __init__(
        self,
        pack_id: str = "sensorimotor_core_v1",
        *,
        pack_manifest_sha256: str | None = None,
    ) -> None:
        self._pack_id = pack_id
        self._manifest_sha256 = pack_manifest_sha256 or sha256_json({
            "pack_id": pack_id,
            "basis_version": "sensorimotor-basis-v1",
            "events": list(_EVENT_ORDER),
        })

    def compile_signal(self, signal: ProprioceptiveSignal) -> SensorimotorCompilationUnit:
        ir = _parse(signal)
        versor, vc = compile_events(ir.events)
        return SensorimotorCompilationUnit(
            canonical_sha256=signal.canonical_sha256,
            ir_sha256=ir.ir_sha256,
            pack_id=self._pack_id,
            pack_manifest_sha256=self._manifest_sha256,
            projection_sha256=sha256_array(versor),
            versor=versor,
            versor_condition=vc,
            sensorimotor_ir=ir,
        )

    def compile_ir(self, ir: SensorimotorIR) -> SensorimotorCompilationUnit:
        versor, vc = compile_events(ir.events)
        return SensorimotorCompilationUnit(
            canonical_sha256="",
            ir_sha256=ir.ir_sha256,
            pack_id=self._pack_id,
            pack_manifest_sha256=self._manifest_sha256,
            projection_sha256=sha256_array(versor),
            versor=versor,
            versor_condition=vc,
            sensorimotor_ir=ir,
        )
