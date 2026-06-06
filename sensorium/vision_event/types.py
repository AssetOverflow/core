"""Typed event-stream vision packets, IR, and compilation units."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from sensorium.vision.types import TileCoord


@dataclass(frozen=True, slots=True, order=True)
class Event:
    x: int
    y: int
    polarity: int
    t_q: int


@dataclass(frozen=True, slots=True)
class EventPacket:
    grid_w: int
    grid_h: int
    packet_tick: int
    events: tuple[Event, ...]
    source_sha256: str
    canonical_sha256: str


@dataclass(frozen=True, slots=True)
class EventAtom:
    event_type: str
    coord: TileCoord
    attrs: tuple[tuple[str, int | str], ...]
    evidence_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class EventIR:
    onset_events: tuple[EventAtom, ...]
    decay_events: tuple[EventAtom, ...]
    motion_bins: tuple[EventAtom, ...]
    ir_sha256: str


@dataclass(frozen=True, slots=True)
class EventCompilationUnit:
    canonical_sha256: str
    ir_sha256: str
    pack_id: str
    pack_manifest_sha256: str
    projection_sha256: str
    packet_tick: int
    grid_shape: tuple[int, int]
    versor: np.ndarray
    versor_condition: float
    event_ir: EventIR

    @property
    def merge_key(self) -> tuple[str, str, str]:
        return (self.canonical_sha256, self.ir_sha256, self.projection_sha256)


__all__ = [
    "Event",
    "EventAtom",
    "EventCompilationUnit",
    "EventIR",
    "EventPacket",
]
