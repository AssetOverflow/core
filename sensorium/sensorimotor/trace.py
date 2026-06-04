"""Trace-safe sensorimotor evidence."""

from __future__ import annotations

from sensorium.sensorimotor.types import SensorimotorCompilationUnit


def sensorimotor_evidence_trace(unit: SensorimotorCompilationUnit) -> dict[str, object]:
    return {
        "modality": "sensorimotor",
        "pack_id": unit.pack_id,
        "canonical_sha256": unit.canonical_sha256,
        "ir_sha256": unit.ir_sha256,
        "pack_manifest_sha256": unit.pack_manifest_sha256,
        "projection_sha256": unit.projection_sha256,
        "merge_key": list(unit.merge_key),
        "versor_condition": unit.versor_condition,
    }
