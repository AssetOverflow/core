"""Synthetic event-stream vision compiler surface."""

from sensorium.vision_event.compiler import (
    EventVisionCompiler,
    canonical_event_atom_order,
    compile_event_atoms,
)
from sensorium.vision_event.packet import build_event_packet
from sensorium.vision_event.trace import event_vision_evidence_trace
from sensorium.vision_event.types import (
    Event,
    EventAtom,
    EventCompilationUnit,
    EventIR,
    EventPacket,
)

__all__ = [
    "Event",
    "EventAtom",
    "EventCompilationUnit",
    "EventIR",
    "EventPacket",
    "EventVisionCompiler",
    "build_event_packet",
    "canonical_event_atom_order",
    "compile_event_atoms",
    "event_vision_evidence_trace",
]
