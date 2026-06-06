"""Deterministic synthetic EventPacket fixtures."""

from __future__ import annotations

from typing import Any

from sensorium.vision_event import EventPacket, build_event_packet


def synthesize(spec: dict[str, Any]) -> EventPacket:
    return build_event_packet(
        grid_w=int(spec["grid_w"]),
        grid_h=int(spec["grid_h"]),
        packet_tick=int(spec["packet_tick"]),
        events=tuple(tuple(event) for event in spec["events"]),
        source_id=str(spec["id"]),
    )


__all__ = ["synthesize"]
