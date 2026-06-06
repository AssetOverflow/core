"""Trace-safe evidence records for event-stream vision compilation units."""

from __future__ import annotations

from sensorium.vision_event.types import EventCompilationUnit


def event_vision_evidence_trace(unit: EventCompilationUnit) -> dict[str, object]:
    return {
        "modality": "vision",
        "sensorium_lane": "event-vision",
        "pack_id": unit.pack_id,
        "canonical_sha256": unit.canonical_sha256,
        "ir_sha256": unit.ir_sha256,
        "pack_manifest_sha256": unit.pack_manifest_sha256,
        "projection_sha256": unit.projection_sha256,
        "merge_key": list(unit.merge_key),
        "packet_tick": unit.packet_tick,
        "grid_shape": list(unit.grid_shape),
        "versor_condition": unit.versor_condition,
    }


__all__ = ["event_vision_evidence_trace"]
