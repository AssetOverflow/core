"""Afferent sensorimotor / proprioceptive compiler contract."""

from sensorium.sensorimotor.arena import (
    SensorimotorArena,
    SensorimotorDelta,
    merge_sensorimotor_deltas,
    sensorimotor_merge_trace_hash,
)
from sensorium.sensorimotor.compiler import SensorimotorCompiler, canonicalize_proprioception
from sensorium.sensorimotor.trace import sensorimotor_evidence_trace
from sensorium.sensorimotor.types import (
    ProprioceptiveSignal,
    SensorimotorCompilationUnit,
    SensorimotorEvent,
    SensorimotorIR,
)

__all__ = [
    "ProprioceptiveSignal",
    "SensorimotorArena",
    "SensorimotorCompilationUnit",
    "SensorimotorCompiler",
    "SensorimotorDelta",
    "SensorimotorEvent",
    "SensorimotorIR",
    "canonicalize_proprioception",
    "merge_sensorimotor_deltas",
    "sensorimotor_evidence_trace",
    "sensorimotor_merge_trace_hash",
]
