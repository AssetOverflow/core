from __future__ import annotations

import numpy as np

from sensorium.protocol import Modality
from sensorium.sensorimotor import (
    SensorimotorCompiler,
    SensorimotorDelta,
    canonicalize_proprioception,
    merge_sensorimotor_deltas,
    sensorimotor_evidence_trace,
    sensorimotor_merge_trace_hash,
)


def _signal():
    return canonicalize_proprioception(
        pose_q=(10, -4, 3),
        velocity_q=(1, 0, -1),
        force_torque_q=(2, 3, 5),
        contact_q=(1, 0, 1, 0),
        actuator_state_q=(7, 8),
        source_id="test-sensor",
    )


def test_sensorimotor_is_afferent_modality_label():
    assert Modality.SENSORIMOTOR.value == "sensorimotor"


def test_same_proprioceptive_signal_produces_identical_unit():
    compiler = SensorimotorCompiler()
    u1 = compiler.compile_signal(_signal())
    u2 = compiler.compile_signal(_signal())
    assert np.array_equal(u1.versor, u2.versor)
    assert u1.merge_key == u2.merge_key
    assert u1.versor.shape == (32,)
    assert u1.versor.dtype == np.float32
    assert u1.versor_condition < 1e-6


def test_sensorimotor_ir_replay_is_deterministic():
    compiler = SensorimotorCompiler()
    unit = compiler.compile_signal(_signal())
    replay = compiler.compile_ir(unit.sensorimotor_ir)
    assert np.array_equal(unit.versor, replay.versor)
    assert unit.ir_sha256 == replay.ir_sha256
    assert unit.projection_sha256 == replay.projection_sha256


def test_sensorimotor_delta_merge_is_idempotent():
    compiler = SensorimotorCompiler()
    unit = compiler.compile_signal(_signal())
    delta = SensorimotorDelta.from_units([unit])
    merged = merge_sensorimotor_deltas([delta, delta])
    assert merged.merge_keys == delta.merge_keys
    assert sensorimotor_merge_trace_hash(merged) == sensorimotor_merge_trace_hash(delta)


def test_sensorimotor_trace_has_no_actuator_command_payload():
    unit = SensorimotorCompiler().compile_signal(_signal())
    trace = sensorimotor_evidence_trace(unit)
    assert trace["modality"] == "sensorimotor"
    assert "command" not in trace
    assert "trajectory" not in trace
    for value in trace.values():
        assert not isinstance(value, (np.ndarray, bytes, bytearray))


def test_sensorimotor_compiler_exposes_no_decode_path():
    compiler = SensorimotorCompiler()
    assert not hasattr(compiler, "decode")
    assert not hasattr(compiler, "decode_batch")
