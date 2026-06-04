from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pytest

from sensorium.environment import build_observation_frame


@dataclass(frozen=True, slots=True)
class _Unit:
    canonical_sha256: str
    ir_sha256: str
    pack_id: str
    pack_manifest_sha256: str
    projection_sha256: str
    versor: np.ndarray
    versor_condition: float = 0.0

    @property
    def merge_key(self) -> tuple[str, str, str]:
        return (self.canonical_sha256, self.ir_sha256, self.projection_sha256)


def _unit(name: str, pack_id: str) -> _Unit:
    v = np.zeros(32, dtype=np.float32)
    v[0] = 1.0
    return _Unit(name, f"ir-{name}", pack_id, "manifest", f"proj-{name}", v)


def test_observation_frame_is_order_invariant_and_deduped():
    audio = _unit("a", "audio_core_v1")
    vision = _unit("v", "vision_core_v1")
    text = _unit("t", "en")
    f1 = build_observation_frame(monotonic_tick=7, source_clock="local", units=[audio, vision, text, audio])
    f2 = build_observation_frame(monotonic_tick=7, source_clock="local", units=[text, audio, vision])
    assert f1.trace_hash == f2.trace_hash
    assert f1.environment_sha256 == f2.environment_sha256
    assert len(f1.units) == 3
    assert tuple(unit.merge_key for unit in f1.units) == tuple(sorted(unit.merge_key for unit in f1.units))


def test_mixed_units_remain_content_addressed():
    frame = build_observation_frame(
        monotonic_tick=1,
        source_clock="edge",
        causal_parent_ids=("parent",),
        units=[_unit("audio", "audio_core_v1"), _unit("vision", "vision_core_v1")],
    )
    assert frame.frame_id
    assert frame.causal_parent_ids == ("parent",)
    assert frame.units[0].merge_key < frame.units[1].merge_key


def test_unsafe_payloads_are_rejected_from_frame_trace():
    @dataclass(frozen=True, slots=True)
    class BadUnit(_Unit):
        samples: bytes = b"pcm"

    with pytest.raises(TypeError, match="unsafe observation payload"):
        build_observation_frame(monotonic_tick=0, source_clock="local", units=[BadUnit(
            "a", "ir-a", "audio_core_v1", "manifest", "proj-a", np.zeros(32, dtype=np.float32)
        )])


def test_efferent_action_trace_is_not_an_afferent_unit():
    @dataclass(frozen=True, slots=True)
    class ActionUnit(_Unit):
        efferent: bool = True

    with pytest.raises(ValueError, match="efferent"):
        build_observation_frame(monotonic_tick=0, source_clock="local", units=[ActionUnit(
            "m", "ir-m", "motor_test", "manifest", "proj-m", np.zeros(32, dtype=np.float32)
        )])
