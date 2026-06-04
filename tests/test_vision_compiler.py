from __future__ import annotations

import numpy as np
import pytest

from algebra.versor import versor_condition
from sensorium.vision import (
    DEFAULT_OPERATOR_REGISTRY,
    ELLIPTIC_PLANES,
    VisionCompiler,
    VisionOperatorSpec,
    canonical_event_order,
    canonicalize_image,
    compile_events,
    vision_evidence_trace,
)
from sensorium.vision.grid import iter_tile_signals
from sensorium.vision.types import VisualEvent


def _image() -> np.ndarray:
    x = np.linspace(0.0, 1.0, 32, dtype=np.float32)
    y = np.linspace(0.0, 1.0, 32, dtype=np.float32)
    xx, yy = np.meshgrid(x, y)
    return np.stack([xx, yy, 1.0 - xx], axis=2).astype(np.float32)


def _tile():
    image = canonicalize_image(_image())
    return iter_tile_signals(image)[0]


def test_tile_projection_is_deterministic_shape_dtype_and_closed():
    compiler = VisionCompiler()
    tile = _tile()
    u1 = compiler.compile_tile(tile)
    u2 = compiler.compile_tile(tile)
    assert np.array_equal(u1.versor, u2.versor)
    assert u1.merge_key == u2.merge_key
    assert u1.versor.shape == (32,)
    assert u1.versor.dtype == np.float32
    assert u1.versor_condition < 1e-6


def test_compile_image_expands_to_tile_units_not_whole_image_projection():
    image = canonicalize_image(_image())
    units = VisionCompiler().compile_image(image)
    assert len(units) == 5  # 2x2 finest scale + 1 coarser scale
    assert {u.coord.scale_level for u in units} == {0, 1}
    assert len({u.merge_key for u in units}) == len(units)


def test_ir_replay_matches_original_tile_projection():
    unit = VisionCompiler().compile_tile(_tile())
    replay = VisionCompiler().compile_ir(unit.vision_ir)
    assert np.array_equal(unit.versor, replay.versor)
    assert unit.ir_sha256 == replay.ir_sha256
    assert unit.projection_sha256 == replay.projection_sha256


def test_canonical_event_order_uses_spatial_morton_order():
    unit = VisionCompiler().compile_tile(_tile())
    ordered = canonical_event_order(unit.vision_ir)
    assert ordered == sorted(
        ordered,
        key=lambda e: (e.coord.scale_level, e.coord.morton),
    )


def test_compile_events_is_order_sensitive():
    tile = _tile()
    a = VisualEvent("region.contrast", tile.coord, (("contrast_q", 5),), ())
    b = VisualEvent("orient.edge_energy", tile.coord, (("orient_q", 3), ("energy_q", 4)), ())
    ab, _ = compile_events([a, b], DEFAULT_OPERATOR_REGISTRY)
    ba, _ = compile_events([b, a], DEFAULT_OPERATOR_REGISTRY)
    assert not np.array_equal(ab, ba)


def test_default_registry_uses_only_elliptic_planes():
    for spec in DEFAULT_OPERATOR_REGISTRY.specs.values():
        assert spec.blade_index in ELLIPTIC_PLANES
    with pytest.raises(ValueError):
        VisionOperatorSpec("bad", "bad", "B_BAD", 9, 1, (), 2)


def test_vision_trace_has_no_pixels():
    unit = VisionCompiler().compile_tile(_tile())
    trace = vision_evidence_trace(unit)
    assert "pixels" not in trace
    for value in trace.values():
        assert not isinstance(value, (np.ndarray, bytes, bytearray))
    assert versor_condition(unit.versor) < 1e-6
