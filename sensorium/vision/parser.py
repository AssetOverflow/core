"""Parser and canonical hash for VisionIR."""

from __future__ import annotations

from sensorium.vision.checksum import sha256_json
from sensorium.vision.types import VisionIR, VisualEvent


def _event_payload(event: VisualEvent) -> dict[str, object]:
    return {
        "event_type": event.event_type,
        "coord": {
            "scale_level": event.coord.scale_level,
            "tile_row": event.coord.tile_row,
            "tile_col": event.coord.tile_col,
        },
        "attrs": [list(pair) for pair in event.attrs],
        "evidence_ids": list(event.evidence_ids),
    }


def ir_sha256_of(ir: VisionIR) -> str:
    payload = {
        "regions": [_event_payload(e) for e in ir.regions],
        "contour_arcs": [_event_payload(e) for e in ir.contour_arcs],
        "orient_events": [_event_payload(e) for e in ir.orient_events],
        "texture_atoms": [_event_payload(e) for e in ir.texture_atoms],
        "salient_events": [_event_payload(e) for e in ir.salient_events],
        "content_anchors": [_event_payload(e) for e in ir.content_anchors],
    }
    return sha256_json(payload)


def parse(events: tuple[VisualEvent, ...]) -> VisionIR:
    regions = tuple(e for e in events if e.event_type.startswith("region."))
    contour_arcs = tuple(e for e in events if e.event_type.startswith("contour."))
    orient_events = tuple(e for e in events if e.event_type.startswith("orient."))
    texture_atoms = tuple(e for e in events if e.event_type.startswith("texture."))
    salient_events = tuple(e for e in events if e.event_type.startswith("salient."))
    content_anchors = tuple(e for e in events if e.event_type.startswith("content."))
    ir = VisionIR(regions, contour_arcs, orient_events, texture_atoms, salient_events, content_anchors, "")
    return VisionIR(
        ir.regions,
        ir.contour_arcs,
        ir.orient_events,
        ir.texture_atoms,
        ir.salient_events,
        ir.content_anchors,
        ir_sha256_of(ir),
    )
