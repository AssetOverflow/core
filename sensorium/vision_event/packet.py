"""Canonical construction for synthetic event-stream vision packets."""

from __future__ import annotations

from collections.abc import Iterable

from sensorium.vision.checksum import sha256_json
from sensorium.vision_event.types import Event, EventPacket


def _event_from_tuple(raw: Event | tuple[int, int, int, int]) -> Event:
    if isinstance(raw, Event):
        return raw
    x, y, polarity, t_q = raw
    return Event(int(x), int(y), int(polarity), int(t_q))


def build_event_packet(
    *,
    grid_w: int,
    grid_h: int,
    packet_tick: int,
    events: Iterable[Event | tuple[int, int, int, int]],
    source_id: str = "synthetic-event-fixture",
) -> EventPacket:
    if grid_w <= 0 or grid_h <= 0:
        raise ValueError("event packet grid dimensions must be positive")
    if packet_tick < 0:
        raise ValueError("event packet tick must be non-negative")
    canonical_events = tuple(sorted(_event_from_tuple(event) for event in events))
    if not canonical_events:
        raise ValueError("event packet requires at least one event")
    for event in canonical_events:
        if not (0 <= event.x < grid_w and 0 <= event.y < grid_h):
            raise ValueError("event coordinate outside canonical sensor grid")
        if event.polarity not in {-1, 1}:
            raise ValueError("event polarity must be -1 or 1")
        if event.t_q < 0:
            raise ValueError("event time quantum must be non-negative")
    source_sha256 = sha256_json({
        "kind": "EventPacket.source",
        "source_id": str(source_id),
        "grid_w": int(grid_w),
        "grid_h": int(grid_h),
    })
    payload = {
        "kind": "EventPacket",
        "grid_w": int(grid_w),
        "grid_h": int(grid_h),
        "packet_tick": int(packet_tick),
        "source_sha256": source_sha256,
        "events": [
            {"x": e.x, "y": e.y, "polarity": e.polarity, "t_q": e.t_q}
            for e in canonical_events
        ],
    }
    return EventPacket(
        grid_w=int(grid_w),
        grid_h=int(grid_h),
        packet_tick=int(packet_tick),
        events=canonical_events,
        source_sha256=source_sha256,
        canonical_sha256=sha256_json(payload),
    )


__all__ = ["build_event_packet"]
