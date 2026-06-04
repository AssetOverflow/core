from __future__ import annotations

import numpy as np
import pytest

from sensorium.adapters.vision import VisionProjectionHead, make_vision_pack
from sensorium.protocol import CL41_DIM, Modality
from sensorium.registry import ModalityRegistry
from sensorium.vision import canonicalize_image
from sensorium.vision.grid import iter_tile_signals


def _tile():
    img = np.zeros((32, 32, 3), dtype=np.float32)
    img[:, 16:, 0] = 1.0
    return iter_tile_signals(canonicalize_image(img))[0]


def test_vision_pack_ships_gate_closed():
    pack = make_vision_pack("vision_core_v1")
    assert pack.modality_type is Modality.VISION
    assert pack.gate_engaged is False
    assert pack.projection is not None


def test_mount_runs_unitarity_and_closed_gate_refuses_projection():
    reg = ModalityRegistry()
    reg.mount(make_vision_pack("vision_core_v1"), sample=_tile())
    with pytest.raises(RuntimeError, match="gate is not engaged"):
        reg.project("vision_core_v1", _tile())


def test_engaging_gate_requires_checksum_verified():
    with pytest.raises(ValueError, match="checksum_verified"):
        make_vision_pack("vision_core_v1", gate_engaged=True, checksum_verified=False)


def test_engaged_pack_projects_tile_32_float32():
    reg = ModalityRegistry()
    reg.mount(
        make_vision_pack("vision_core_v1", gate_engaged=True, checksum_verified=True),
        sample=_tile(),
    )
    mv = reg.project("vision_core_v1", _tile())
    assert mv.shape == (CL41_DIM,)
    assert mv.dtype == np.float32


def test_projection_head_compiles_whole_image_to_tile_units():
    head: VisionProjectionHead = make_vision_pack("vision_core_v1").projection
    image = _tile().image
    units = head.compile_image(image)
    assert len(units) == 5
