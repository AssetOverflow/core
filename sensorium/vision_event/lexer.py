"""Event-packet lexer for sparse asynchronous vision deltas."""

from __future__ import annotations

from collections import defaultdict

from sensorium.vision.checksum import sha256_json
from sensorium.vision.types import TileCoord
from sensorium.vision_event.types import EventAtom, EventPacket

_TILE_PX = 8
_TIME_BIN_Q = 8


def _coord(packet: EventPacket, x: int, y: int) -> TileCoord:
    max_row = max(0, (packet.grid_h - 1) // _TILE_PX)
    max_col = max(0, (packet.grid_w - 1) // _TILE_PX)
    return TileCoord(
        scale_level=0,
        tile_row=min(max_row, y // _TILE_PX),
        tile_col=min(max_col, x // _TILE_PX),
    )


def _event_evidence_id(packet: EventPacket, *, x: int, y: int, polarity: int, t_q: int) -> str:
    return sha256_json({
        "kind": "EventPacket.event",
        "packet": packet.canonical_sha256,
        "x": x,
        "y": y,
        "polarity": polarity,
        "t_q": t_q,
    })


def lex_event_packet(packet: EventPacket) -> tuple[EventAtom, ...]:
    atoms: list[EventAtom] = []
    bins: dict[tuple[int, int, int], list[int]] = defaultdict(list)
    for event in packet.events:
        coord = _coord(packet, event.x, event.y)
        t_bin = event.t_q // _TIME_BIN_Q
        event_type = "event.onset" if event.polarity > 0 else "event.decay"
        evidence_id = _event_evidence_id(
            packet,
            x=event.x,
            y=event.y,
            polarity=event.polarity,
            t_q=event.t_q,
        )
        atoms.append(EventAtom(
            event_type=event_type,
            coord=coord,
            attrs=(
                ("polarity_q", event.polarity),
                ("t_bin", t_bin),
                ("x_q", event.x),
                ("y_q", event.y),
            ),
            evidence_ids=(evidence_id,),
        ))
        bins[(coord.tile_row, coord.tile_col, t_bin)].append(event.polarity)

    for (tile_row, tile_col, t_bin), polarities in sorted(bins.items()):
        count = len(polarities)
        balance = sum(polarities)
        if count < 2 and abs(balance) == count:
            continue
        atoms.append(EventAtom(
            event_type="event.motion_delta",
            coord=TileCoord(scale_level=1, tile_row=tile_row, tile_col=tile_col),
            attrs=(
                ("balance_q", balance),
                ("count_q", count),
                ("t_bin", t_bin),
            ),
            evidence_ids=tuple(
                sha256_json({
                    "kind": "EventPacket.motion_bin",
                    "packet": packet.canonical_sha256,
                    "tile_row": tile_row,
                    "tile_col": tile_col,
                    "t_bin": t_bin,
                    "index": idx,
                    "polarity": polarity,
                })
                for idx, polarity in enumerate(sorted(polarities))
            ),
        ))
    return tuple(atoms)


__all__ = ["lex_event_packet"]
