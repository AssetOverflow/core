"""Trace-safe evidence records for vision compilation units."""

from __future__ import annotations

from sensorium.vision.types import VisionCompilationUnit


def vision_evidence_trace(unit: VisionCompilationUnit) -> dict[str, object]:
    return {
        "modality": "vision",
        "pack_id": unit.pack_id,
        "canonical_sha256": unit.canonical_sha256,
        "ir_sha256": unit.ir_sha256,
        "pack_manifest_sha256": unit.pack_manifest_sha256,
        "projection_sha256": unit.projection_sha256,
        "merge_key": list(unit.merge_key),
        "coord": {
            "scale_level": unit.coord.scale_level,
            "tile_row": unit.coord.tile_row,
            "tile_col": unit.coord.tile_col,
        },
        "versor_condition": unit.versor_condition,
    }
