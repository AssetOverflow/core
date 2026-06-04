"""Tile-first deterministic vision compiler."""

from sensorium.vision.arena import (
    VisionArena,
    VisionDelta,
    merge_vision_deltas,
    reset_thread_local_vision_arena,
    thread_local_vision_arena,
    vision_merge_trace_hash,
)
from sensorium.vision.canonical import canonicalize_image
from sensorium.vision.compiler import VisionCompiler, canonical_event_order, compile_events
from sensorium.vision.operators import (
    DEFAULT_OPERATOR_REGISTRY,
    ELLIPTIC_PLANES,
    VisionOperatorRegistry,
    VisionOperatorSpec,
    build_elliptic_rotor,
)
from sensorium.vision.trace import vision_evidence_trace
from sensorium.vision.types import (
    TileCoord,
    VisionCompilationUnit,
    VisionImage,
    VisionIR,
    VisionTileSignal,
    VisualEvent,
)

__all__ = [
    "DEFAULT_OPERATOR_REGISTRY",
    "ELLIPTIC_PLANES",
    "TileCoord",
    "VisionArena",
    "VisionCompilationUnit",
    "VisionCompiler",
    "VisionDelta",
    "VisionIR",
    "VisionImage",
    "VisionOperatorRegistry",
    "VisionOperatorSpec",
    "VisionTileSignal",
    "VisualEvent",
    "build_elliptic_rotor",
    "canonical_event_order",
    "canonicalize_image",
    "compile_events",
    "merge_vision_deltas",
    "reset_thread_local_vision_arena",
    "thread_local_vision_arena",
    "vision_evidence_trace",
    "vision_merge_trace_hash",
]
