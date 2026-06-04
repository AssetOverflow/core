"""Fixture conversion for quantized sensorimotor eval specs."""

from __future__ import annotations

from sensorium.sensorimotor import ProprioceptiveSignal, canonicalize_proprioception


def synthesize(spec: dict) -> ProprioceptiveSignal:
    return canonicalize_proprioception(
        pose_q=tuple(int(v) for v in spec.get("pose_q", ())),
        velocity_q=tuple(int(v) for v in spec.get("velocity_q", ())),
        force_torque_q=tuple(int(v) for v in spec.get("force_torque_q", ())),
        contact_q=tuple(int(v) for v in spec.get("contact_q", ())),
        actuator_state_q=tuple(int(v) for v in spec.get("actuator_state_q", ())),
        source_id=str(spec["id"]),
    )
