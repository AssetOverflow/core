from __future__ import annotations

import numpy as np

from sensorium.adapters.vision_event import make_event_vision_pack
from sensorium.protocol import Modality
from sensorium.vision_event import (
    EventVisionCompiler,
    build_event_packet,
    event_vision_evidence_trace,
)


def _packet():
    return build_event_packet(
        grid_w=32,
        grid_h=24,
        packet_tick=1,
        events=(
            (4, 8, 1, 0),
            (6, 8, -1, 2),
            (5, 8, 1, 1),
            (7, 8, 1, 3),
        ),
        source_id="test-event-vision",
    )


def test_event_packet_hash_is_order_invariant():
    p1 = _packet()
    p2 = build_event_packet(
        grid_w=32,
        grid_h=24,
        packet_tick=1,
        events=tuple(reversed(tuple((e.x, e.y, e.polarity, e.t_q) for e in p1.events))),
        source_id="test-event-vision",
    )
    assert p1.events == p2.events
    assert p1.canonical_sha256 == p2.canonical_sha256


def test_event_vision_compiler_outputs_unit_contract():
    unit = EventVisionCompiler().compile_packet(_packet())
    replay = EventVisionCompiler().compile_ir(
        unit.event_ir,
        canonical_sha256=unit.canonical_sha256,
        packet_tick=unit.packet_tick,
        grid_shape=unit.grid_shape,
    )
    assert unit.pack_id == "vision_event_core_v1"
    assert unit.versor.shape == (32,)
    assert unit.versor.dtype == np.float32
    assert unit.versor_condition < 1e-6
    assert unit.merge_key == (unit.canonical_sha256, unit.ir_sha256, unit.projection_sha256)
    assert np.array_equal(unit.versor, replay.versor)


def test_event_vision_trace_has_no_raw_events():
    unit = EventVisionCompiler().compile_packet(_packet())
    trace = event_vision_evidence_trace(unit)
    text = str(trace)
    assert trace["modality"] == "vision"
    assert trace["sensorium_lane"] == "event-vision"
    assert "raw_events" not in text
    assert "event_ir" not in text
    assert "raw" not in text
    assert "reference_versor" not in text


def test_event_vision_pack_uses_vision_modality():
    pack = make_event_vision_pack("vision_event_core_v1")
    assert pack.modality_type is Modality.VISION
    assert pack.projection is not None
